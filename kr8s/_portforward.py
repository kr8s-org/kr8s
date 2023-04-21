# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio

import aiohttp

from ._exceptions import ConnectionClosedError


class PortForward:
    def __init__(self, pod, local_port, remote_port):
        self.pod = pod
        self.local_port = local_port
        self.remote_port = remote_port
        self.server = None
        self.channels = []
        self._run_task = None

    def __await__(self):
        async def _f():
            await self.run()
            return self

        return _f().__await__()

    async def __aenter__(self):
        await self
        return self.local_port

    async def __aexit__(self, *args):
        await self.close()

    async def run(self):
        """Start a server on a local port and sync it with the websocket."""
        self.server = await asyncio.start_server(
            self.sync_sockets, port=self.local_port
        )
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
        ) as response, self.server:
            self.websocket = response
            await self.server.start_serving()

    async def close(self):
        """Close the websocket and server."""
        if self._run_task:
            self._run_task.cancel()
        if self.websocket:
            await self.websocket.close()
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def sync_sockets(self, reader, writer):
        """Start two tasks to copy bytes from tcp=>websocket and websocket=>tcp."""
        try:
            tasks = [
                asyncio.create_task(self.tcp_to_ws(reader)),
                asyncio.create_task(self.ws_to_tcp(writer)),
            ]
            await asyncio.gather(*tasks)
        except ConnectionClosedError:
            for task in tasks:
                task.cancel()
        finally:
            writer.close()
            self.server.close()

    async def tcp_to_ws(self, reader):
        while self.server.is_serving():
            data = await reader.read(1024 * 1024)
            # TODO Figure out why `data` is empty the first time this is called
            # This indicates the socket is cloed, but it isn't and on the second read it works fine.
            if not data:
                raise ConnectionClosedError("TCP socket closed")
            else:
                # Send data to channel 0 of the websocket.
                await self.websocket.send_bytes(b"\x00" + data)

    async def ws_to_tcp(self, writer):
        while self.server.is_serving():
            message = await self.websocket.receive()
            if message.type == aiohttp.WSMsgType.CLOSED:
                # TODO Figure out why this websocket closes after 4 messages.
                raise ConnectionClosedError("Websocket closed")
            elif message.type == aiohttp.WSMsgType.BINARY:
                # Kubernetes portforward protocol prefixes all frames with a byte to represent
                # the channel. Channel 0 is rw for data and channel 1 is ro for errors.
                if message.data[0] not in self.channels:
                    # Keep track of our channels. Could be useful later for listening to multiple ports.
                    self.channels.append(message.data[0])
                else:
                    writer.write(message.data[1:])
                    await writer.drain()
