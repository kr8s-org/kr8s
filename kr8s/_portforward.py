# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import socket
from contextlib import asynccontextmanager

import aiohttp

from ._exceptions import ConnectionClosedError


class PortForward:
    def __init__(self, pod, remote_port) -> None:
        self.running = True
        self.websocket = None
        self.remote_port = remote_port
        self.pod = pod
        self._tasks = []

    async def connect_websocket(self):
        while self.running:
            async with self.pod.api.call_api(
                version=self.pod.version,
                url=f"{self.pod.endpoint}/{self.pod.name}/portforward",
                namespace=self.pod.namespace,
                websocket=True,
                params={
                    "name": self.pod.name,
                    "namespace": self.pod.namespace,
                    "ports": f"{self.remote_port}",
                },
            ) as websocket:
                self.websocket = websocket
                while not self.websocket.closed:
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
                        writer.write(message.data[1:])
                        await writer.drain()
            else:
                await asyncio.sleep(0.1)


@asynccontextmanager
async def ws_sync(pod, remote_port, local_port=None):
    """Start a tcp server and forward all connections to a websocket."""
    if local_port is None:
        local_port = 0
    pf = PortForward(pod, remote_port)
    server = await asyncio.start_server(pf.sync_sockets, port=local_port)
    async with server:
        await server.start_serving()
        for sock in server.sockets:
            if sock.family == socket.AF_INET:
                yield sock.getsockname()[1]
        server.close()
        await server.wait_closed()