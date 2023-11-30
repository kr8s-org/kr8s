# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import asyncio
import contextlib
import random
import socket
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, BinaryIO

import aiohttp
import anyio
import sniffio

from ._exceptions import ConnectionClosedError

if TYPE_CHECKING:
    from .objects import APIObject


class PortForward:
    """Start a tcp server and forward all connections to a Pod port.

    You can either pass a :class:`kr8s.objects.Pod` or any resource with a ``ready_pods`` method
    such as a :class:`kr8s.objects.Service`.

    .. note::
        The ``ready_pods`` method should return a list of Pods that are ready to accept connections.

    .. warning:
        Currently Port Forwards only work when using ``asyncio`` and not ``trio``.

    Args:
        ``resource`` (Pod or Resource): The Pod or Resource to forward to.

        ``remote_port`` (int): The port on the Pod to forward to.

        ``local_port`` (int, optional): The local port to listen on. Defaults to 0, which will choose a random port.

    Example:
        This class can be used as a an async context manager or with explicit start/stop methods.

        Context manager:

        >>> async with PortForward(pod, 8888) as port:
        ...     print(f"Forwarding to port {port}")
        ...     # Do something with port 8888 on the Pod


        Explict start/stop:

        >>> pf = PortForward(pod, 8888)
        >>> await pf.start()
        >>> print(f"Forwarding to port {pf.local_port}")
        >>> # Do something with port 8888 on the Pod
        >>> await pf.stop()


    """

    def __init__(
        self, resource: APIObject, remote_port: int, local_port: int = None
    ) -> None:
        with suppress(sniffio.AsyncLibraryNotFoundError):
            if sniffio.current_async_library() != "asyncio":
                raise RuntimeError(
                    "PortForward only works with asyncio, "
                    "see https://github.com/kr8s-org/kr8s/issues/104"
                )
        self.server = None
        self.remote_port = remote_port
        self.local_port = local_port if local_port is not None else 0
        from ._objects import Pod

        if not isinstance(resource, Pod) and not hasattr(resource, "ready_pods"):
            raise ValueError(
                "resource must be a Pod or a resource with a ready_pods method"
            )
        self._resource = resource
        self.pod = None
        self._loop = asyncio.get_event_loop()
        self._tasks = []
        self._run_task = None
        self._bg_future = None
        self._bg_task = None

    async def __aenter__(self, *args, **kwargs):
        self._run_task = self._run()
        return await self._run_task.__aenter__(*args, **kwargs)

    async def __aexit__(self, *args, **kwargs):
        return await self._run_task.__aexit__(*args, **kwargs)

    async def start(self) -> int:
        """Start a background task with the port forward running."""
        if self._bg_task is not None:
            return

        async def f():
            self._bg_future = self._loop.create_future()
            async with self as port:
                self.local_port = port
                await self._bg_future

        self._bg_task = self._loop.create_task(f())
        while self.local_port == 0:
            await asyncio.sleep(0.1)
        return self.local_port

    async def stop(self) -> None:
        """Stop the background task."""
        self._bg_future.set_result(None)
        self._bg_task = None

    async def run_forever(self) -> None:
        """Run the port forward forever.

        Example:
            >>> pf = pod.portforward(remote_port=8888, local_port=8889)
            >>> # or
            >>> pf = PortForward(pod, remote_port=8888, local_port=8889)
            >>> await pf.run_forever()
        """
        async with self:
            with contextlib.suppress(asyncio.CancelledError):
                await self.server.serve_forever()

    @asynccontextmanager
    async def _run(self) -> int:
        """Start the port forward and yield the local port."""
        self.server = await asyncio.start_server(
            self._sync_sockets, port=self.local_port, host="0.0.0.0"
        )
        async with self.server:
            await self.server.start_serving()
            for sock in self.server.sockets:
                if sock.family == socket.AF_INET:
                    yield sock.getsockname()[1]
            self.server.close()
            await self.server.wait_closed()

    async def _select_pod(self) -> object:
        """Select a Pod to forward to."""
        from ._objects import Pod

        if isinstance(self._resource, Pod):
            return self._resource

        if hasattr(self._resource, "ready_pods"):
            try:
                return random.choice(await self._resource.ready_pods())
            except IndexError:
                raise RuntimeError("No ready pods found")

    @asynccontextmanager
    async def _connect_websocket(self) -> None:
        """Connect to the Kubernetes portforward websocket."""
        connection_attempts = 0
        while True:
            if not self.pod:
                self.pod = await self._select_pod()
            try:
                async with self.pod.api.open_websocket(
                    version=self.pod.version,
                    url=f"{self.pod.endpoint}/{self.pod.name}/portforward",
                    namespace=self.pod.namespace,
                    params={
                        "name": self.pod.name,
                        "namespace": self.pod.namespace,
                        "ports": f"{self.remote_port}",
                        "_preload_content": "false",
                    },
                ) as websocket:
                    yield websocket
            except aiohttp.client_exceptions.WSServerHandshakeError as e:
                self.pod = None
                if connection_attempts > 5:
                    raise ConnectionClosedError("Unable to connect to Pod") from e
                await asyncio.sleep(0.1 * connection_attempts)

    async def _sync_sockets(self, reader: BinaryIO, writer: BinaryIO) -> None:
        """Start two tasks to copy bytes from tcp=>websocket and websocket=>tcp."""
        try:
            async with self._connect_websocket() as ws:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._tcp_to_ws, ws, reader)
                    tg.start_soon(self._ws_to_tcp, ws, writer)
        except ConnectionClosedError:
            pass
        finally:
            writer.close()

    async def _tcp_to_ws(self, ws, reader: BinaryIO) -> None:
        while True:
            data = await reader.read(1024 * 1024)
            if not data:
                raise ConnectionClosedError("TCP socket closed")
            else:
                # Send data to channel 0 of the websocket.
                # TODO Support multiple channels for multiple ports.
                try:
                    await ws.send_bytes(b"\x00" + data)
                except ConnectionResetError:
                    raise ConnectionClosedError("Websocket closed")

    async def _ws_to_tcp(self, ws, writer: BinaryIO) -> None:
        channels = []
        while True:
            message = await ws.receive()
            if message.type == aiohttp.WSMsgType.CLOSED:
                await asyncio.sleep(0.1)
                continue
            elif message.type == aiohttp.WSMsgType.BINARY:
                # Kubernetes portforward protocol prefixes all frames with a byte to represent
                # the channel. Channel 0 is rw for data and channel 1 is ro for errors.
                if message.data[0] not in channels:
                    # Keep track of our channels. Could be useful later for listening to multiple ports.
                    channels.append(message.data[0])
                else:
                    if message.data[0] % 2 == 1:  # pragma: no cover
                        # Odd channels are for errors.
                        raise ConnectionClosedError(message.data[1:].decode())
                    writer.write(message.data[1:])
                    await writer.drain()
