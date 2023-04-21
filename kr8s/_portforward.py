# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
from contextlib import asynccontextmanager
from functools import partial

import aiohttp

from ._exceptions import ConnectionClosedError


async def sync_sockets(websocket, reader, writer):
    """Start two tasks to copy bytes from tcp=>websocket and websocket=>tcp."""
    try:
        tasks = [
            asyncio.create_task(tcp_to_ws(websocket, reader)),
            asyncio.create_task(ws_to_tcp(websocket, writer)),
        ]
        await asyncio.gather(*tasks)
    except ConnectionClosedError:
        for task in tasks:
            task.cancel()
    finally:
        writer.close()


async def tcp_to_ws(websocket, reader):
    while True:
        data = await reader.read(1024 * 1024)
        if not data:
            raise ConnectionClosedError("TCP socket closed")
        else:
            # Send data to channel 0 of the websocket.
            await websocket.send_bytes(b"\x00" + data)


async def ws_to_tcp(websocket, writer):
    channels = []
    while True:
        message = await websocket.receive()
        if message.type == aiohttp.WSMsgType.CLOSED:
            raise ConnectionClosedError("Websocket closed")
        elif message.type == aiohttp.WSMsgType.BINARY:
            # Kubernetes portforward protocol prefixes all frames with a byte to represent
            # the channel. Channel 0 is rw for data and channel 1 is ro for errors.
            if message.data[0] not in channels:
                # Keep track of our channels. Could be useful later for listening to multiple ports.
                channels.append(message.data[0])
            else:
                writer.write(message.data[1:])
                await writer.drain()


@asynccontextmanager
async def portforward(pod, local_port, remote_port):
    async with pod.api.call_api(
        version=pod.version,
        url=f"{pod.endpoint}/{pod.name}/portforward",
        namespace=pod.namespace,
        websocket=True,
        params={
            "name": pod.name,
            "namespace": pod.namespace,
            "ports": f"{remote_port}",
        },
    ) as websocket:
        server = await asyncio.start_server(
            partial(sync_sockets, websocket), port=local_port
        )
        async with server:
            await server.start_serving()
            yield local_port
            server.close()
            await server.wait_closed()
