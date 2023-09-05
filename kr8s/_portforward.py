# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import asyncio
import random
import socket
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, BinaryIO

import anyio
import httpx_ws

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
        self.running = True
        self.server = None
        self.remote_port = remote_port
        self.local_port = local_port if local_port is not None else 0
        self._resource = resource
        from ._objects import Pod

        self.pod = None
        if isinstance(resource, Pod):
            self.pod = resource
        else:
            if not hasattr(resource, "ready_pods"):
                raise ValueError(
                    "resource must be a Pod or a resource with a ready_pods method"
                )

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

        self._bg_task = asyncio.create_task(f())
        while self.local_port == 0:
            await asyncio.sleep(0.1)
        return self.local_port

    async def stop(self) -> None:
        """Stop the background task."""
        self._bg_future.set_result(None)
        self._bg_task = None

    @asynccontextmanager
    async def _run(self) -> int:
        """Start the port forward and yield the local port."""
        if not self.pod:
            try:
                self.pod = random.choice(await self._resource.ready_pods())
            except IndexError:
                raise RuntimeError("No ready pods found")
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

    async def _sync_sockets(self, reader: BinaryIO, writer: BinaryIO) -> None:
        """Start two tasks to copy bytes from tcp=>websocket and websocket=>tcp."""
        try:
            async with httpx_ws.aconnect_ws(
                f"/api/v1/namespaces/{self.pod.namespace}/pods/{self.pod.name}/portforward?ports={self.remote_port}",
                self.pod.api._session,
            ) as ws:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self._tcp_to_ws, ws, reader)
                    tg.start_soon(self._ws_to_tcp, ws, writer)
        except ConnectionClosedError as e:
            self.running = False
            raise e
        finally:
            writer.close()

    async def _tcp_to_ws(
        self, ws: httpx_ws.AsyncWebSocketSession, reader: BinaryIO
    ) -> None:
        while True:
            data = await reader.read(1024 * 1024)
            if not data:
                raise ConnectionClosedError("TCP socket closed")
            else:
                await ws.send_bytes(b"\x00" + data)

    async def _ws_to_tcp(
        self, ws: httpx_ws.AsyncWebSocketSession, writer: BinaryIO
    ) -> None:
        channels = []
        while True:
            event = await ws.receive_bytes()
            # Kubernetes portforward protocol prefixes all frames with a byte to represent
            # the channel. Channel 0 is rw for data and channel 1 is ro for errors.
            if event[0] not in channels:
                # Keep track of our channels. Could be useful later for listening to multiple ports.
                channels.append(event[0])
            else:
                writer.write(event[1:])
                await writer.drain()
