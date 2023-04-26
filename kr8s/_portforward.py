# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import socket
from contextlib import asynccontextmanager

import aiohttp

from ._exceptions import ConnectionClosedError


class PortForward:
    """Start a tcp server and forward all connections to a Pod port."""

    def __init__(self, pod, remote_port, local_port=None) -> None:
        self.running = True
        self.server = None
        self.websocket = None
        self.remote_port = remote_port
        self.local_port = local_port if local_port is not None else 0
        self.pod = pod
        self.connection_attempts = 0
        self._loop = asyncio.get_event_loop()
        self._tasks = []
        self._run = None
        self._bg_future = None
        self._bg_task = None

    async def __aenter__(self, *args, **kwargs):
        self._run = self.run()
        return await self._run.__aenter__(*args, **kwargs)

    async def __aexit__(self, *args, **kwargs):
        return await self._run.__aexit__(*args, **kwargs)

    async def start(self):
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

    async def stop(self):
        self._bg_future.set_result(None)
        self._bg_task = None

    @asynccontextmanager
    async def run(self):
        self.server = await asyncio.start_server(
            self.sync_sockets, port=self.local_port, host="0.0.0.0"
        )
        async with self.server:
            await self.server.start_serving()
            for sock in self.server.sockets:
                if sock.family == socket.AF_INET:
                    yield sock.getsockname()[1]
            self.server.close()
            await self.server.wait_closed()

    async def connect_websocket(self):
        while self.running:
            self.connection_attempts += 1
            try:
                async with self.pod.api.call_api(
                    version=self.pod.version,
                    url=f"{self.pod.endpoint}/{self.pod.name}/portforward",
                    namespace=self.pod.namespace,
                    websocket=True,
                    params={
                        "name": self.pod.name,
                        "namespace": self.pod.namespace,
                        "ports": f"{self.remote_port}",
                        "_preload_content": "false",
                    },
                ) as websocket:
                    self.websocket = websocket
                    while not self.websocket.closed:
                        await asyncio.sleep(0.1)
            except (aiohttp.WSServerHandshakeError, aiohttp.ServerDisconnectedError):
                await asyncio.sleep(0.1)

    async def sync_sockets(self, reader, writer):
        """Start two tasks to copy bytes from tcp=>websocket and websocket=>tcp."""
        try:
            self.tasks = [
                asyncio.create_task(self.connect_websocket()),
                asyncio.create_task(self.tcp_to_ws(reader)),
                asyncio.create_task(self.ws_to_tcp(writer)),
            ]
            await asyncio.gather(*self.tasks)
        except ConnectionClosedError as e:
            self.running = False
            for task in self.tasks:
                task.cancel()
            raise e
        finally:
            writer.close()

    async def tcp_to_ws(self, reader):
        while True:
            data = await reader.read(1024 * 1024)
            if not data:
                raise ConnectionClosedError("TCP socket closed")
            else:
                # Send data to channel 0 of the websocket.
                # TODO Support multiple channels for multiple ports.
                while self.websocket is None or self.websocket.closed:
                    await asyncio.sleep(0.1)
                await self.websocket.send_bytes(b"\x00" + data)

    async def ws_to_tcp(self, writer):
        channels = []
        while True:
            if self.websocket and not self.websocket.closed:
                message = await self.websocket.receive()
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
                        if message.data[0] % 2 == 1:
                            # Odd channels are for errors.
                            raise ConnectionClosedError(message.data[1:].decode())
                        writer.write(message.data[1:])
                        await writer.drain()
            else:
                await asyncio.sleep(0.1)
