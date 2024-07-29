# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import asyncio
import contextlib
import random
import socket
import sys
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, AsyncGenerator

import anyio
import httpx_ws
import sniffio

from ._exceptions import ConnectionClosedError
from ._types import APIObjectWithPods

if TYPE_CHECKING:
    from ._objects import APIObject

if sys.version_info < (3, 12, 1):
    # contextlib.supress() in Python 3.12.1 supprts ExceptionGroups
    # For older versions, we use the exceptiongroup backport
    from exceptiongroup import suppress  # type: ignore # noqa: F811


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

        ``address``(List[str] | str, optional): List of addresses or address to listen on. Defaults to ["127.0.0.1"],
         will listen only on 127.0.0.1

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

        Explict bind address:

        >>> async with PortForward(pod, 8888, address=["127.0.0.1", "10.20.0.1"]) as port:
        ...     print(f"Forwarding to port {port}")
        ...     # Do something with port 8888 on the Pod, port will be bind to 127.0.0.1 and 10.20.0.1

    """

    def __init__(
        self,
        resource: APIObject,
        remote_port: int,
        local_port: int | None = None,
        address: list[str] | str = "127.0.0.1",
    ) -> None:
        with suppress(sniffio.AsyncLibraryNotFoundError):
            if sniffio.current_async_library() != "asyncio":
                raise RuntimeError(
                    "PortForward only works with asyncio, "
                    "see https://github.com/kr8s-org/kr8s/issues/104"
                )
        self.server = None
        self.servers: list[asyncio.Server] = []
        self.remote_port = remote_port
        self.local_port = local_port if local_port is not None else 0
        if isinstance(address, str):
            address = [address]
        self.address = address
        from ._objects import Pod

        if not isinstance(resource, Pod) and not hasattr(resource, "ready_pods"):
            raise ValueError(
                "resource must be a Pod or a resource with a ready_pods method"
            )
        self._resource = resource
        self.pod = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tasks: list[asyncio.Task] = []
        self._run_task = None
        self._bg_future: asyncio.Future | None = None
        self._bg_task: asyncio.Task | None = None

    async def __aenter__(self, *args, **kwargs):
        self._run_task = self._run()
        return await self._run_task.__aenter__(*args, **kwargs)

    async def __aexit__(self, *args, **kwargs):
        assert self._run_task
        return await self._run_task.__aexit__(*args, **kwargs)

    async def start(self) -> int:
        """Start a background task with the port forward running."""
        if self._loop is None:
            self._loop = asyncio.get_event_loop()
        if self._bg_task is not None:
            return self.local_port

        async def f():
            self._bg_future = self._loop.create_future()
            async with self as port:
                self.local_port = port
                await self._bg_future

        self._bg_task = self._loop.create_task(f())
        while self.local_port == 0:
            await anyio.sleep(0.1)
        return self.local_port

    async def stop(self) -> None:
        """Stop the background task."""
        if self._bg_future:
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
                for server in self.servers:
                    await server.serve_forever()

    @asynccontextmanager
    async def _run(self) -> AsyncGenerator[int]:
        """Start the port forward for multiple bind addresses and yield the local port."""
        if self.local_port == 0:
            self.local_port = self._find_available_port()

        for address in self.address:
            server = await asyncio.start_server(
                self._sync_sockets, port=self.local_port, host=address
            )
            self.servers.append(server)

        try:
            for server in self.servers:
                await server.start_serving()
            yield self.local_port

        finally:
            # Ensure all servers are closed properly
            for server in self.servers:
                server.close()
                await server.wait_closed()
                self.servers.remove(server)

    async def _select_pod(self) -> APIObject:
        """Select a Pod to forward to."""
        from ._objects import Pod

        if isinstance(self._resource, Pod):
            return self._resource

        if isinstance(self._resource, APIObjectWithPods):
            try:
                return random.choice(await self._resource.async_ready_pods())
            except IndexError:
                pass
        raise RuntimeError("No ready pods found")

    @asynccontextmanager
    async def _connect_websocket(self):
        """Connect to the Kubernetes portforward websocket."""
        connection_attempts = 0
        while True:
            if not self.pod:
                self.pod = await self._select_pod()
            try:
                assert self.pod.api
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
                    break
            except httpx_ws.HTTPXWSException as e:
                self.pod = None
                if connection_attempts > 5:
                    raise ConnectionClosedError("Unable to connect to Pod") from e
                await anyio.sleep(0.1 * connection_attempts)

    async def _sync_sockets(self, reader, writer) -> None:
        """Start two tasks to copy bytes from tcp=>websocket and websocket=>tcp."""
        try:
            async with self._connect_websocket() as ws:
                with suppress(ConnectionClosedError, httpx_ws.WebSocketDisconnect):
                    async with anyio.create_task_group() as tg:
                        tg.start_soon(self._tcp_to_ws, ws, reader)
                        tg.start_soon(self._ws_to_tcp, ws, writer)
        finally:
            writer.close()

    async def _tcp_to_ws(self, ws, reader) -> None:
        while True:
            data = await reader.read(1024 * 1024)
            if not data:
                raise ConnectionClosedError("TCP socket closed")
            else:
                # Send data to channel 0 of the websocket.
                # TODO Support multiple channels for multiple ports.
                try:
                    await ws.send_bytes(b"\x00" + data)
                except ConnectionResetError as e:
                    raise ConnectionClosedError("Websocket closed") from e

    async def _ws_to_tcp(self, ws, writer) -> None:
        channels = []
        while True:
            message = await ws.receive_bytes()
            # Kubernetes portforward protocol prefixes all frames with a byte to represent
            # the channel. Channel 0 is rw for data and channel 1 is ro for errors.
            if message[0] not in channels:
                # Keep track of our channels. Could be useful later for listening to multiple ports.
                channels.append(message[0])
            else:
                if message[0] % 2 == 1:  # pragma: no cover
                    # Odd channels are for errors.
                    raise ConnectionClosedError(message[1:].decode())
                writer.write(message[1:])
                await writer.drain()

    def _is_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a given port is in use on a specified host.

        Args:
            port: Port number to check.
            host: Host address to check the port on. Default is localhost.

        Returns:
            bool: True if the port is in use, False otherwise.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0

    def _find_available_port(self):
        """Find a random port that is not in use on any of the given addresses.

        Returns:
            An available port number.
        """
        while True:
            port = random.randint(10000, 60000)
            if not any(self._is_port_in_use(port, address) for address in self.address):
                return port
