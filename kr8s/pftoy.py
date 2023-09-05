"""This is a toy port forward."""

import base64
import contextlib
import os

import anyio
import httpx
import rich
import wsproto

from kr8s._auth import KubeAuth
from kr8s.asyncio.objects import Pod

console = rich.console.Console()
channels = []


class ConnectionClosed(Exception):
    pass


class WebsocketConnection:
    def __init__(self, network_steam):
        self._ws_connection_state = wsproto.Connection(wsproto.ConnectionType.CLIENT)
        self._network_stream = network_steam
        self._events = []
        self.__lock = anyio.Lock()

    async def ping(self):
        """
        Send a ping frame over the websocket connection.
        """
        event = wsproto.events.Ping()
        data = self._ws_connection_state.send(event)
        await self._network_stream.write(data)

    async def send(self, data):
        """
        Send a byte frame over the websocket connection.
        """
        async with self.__lock:
            event = wsproto.events.BytesMessage(data)
            data = self._ws_connection_state.send(event)
            await self._network_stream.write(data)

    async def recv(self):
        """
        Receive the next byte frame from the websocket connection.
        """
        while not self._events:
            data = await self._network_stream.read(max_bytes=4096)
            self._ws_connection_state.receive_data(data)
            self._events = list(self._ws_connection_state.events())

        event = self._events.pop(0)
        if isinstance(event, wsproto.events.CloseConnection):
            raise ConnectionClosed()
        else:
            return event


@contextlib.asynccontextmanager
async def ws_connect(client, url):
    headers = {
        "connection": "upgrade",
        "upgrade": "websocket",
        "sec-websocket-key": base64.b64encode(os.urandom(16)),
        "sec-websocket-version": "13",
    }

    async with client.stream("GET", url, headers=headers) as response:
        if response.status_code != 101:
            raise ValueError(f"Unexpected status code: {response.status_code}")
        network_steam = response.extensions["network_stream"]
        yield WebsocketConnection(network_steam)


async def gen_pod():
    pod = await Pod(
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "foo",
            },
            "spec": {
                "containers": [
                    {
                        "name": "wordpress",
                        "image": "wordpress",
                        "ports": [{"containerPort": 80, "name": "http-web-svc"}],
                    }
                ]
            },
        }
    )
    if not await pod.exists():
        await pod.create()
    return pod


async def get_bytes(ws):
    while True:
        try:
            event = await ws.recv()
        except ConnectionClosed:
            console.log("Connection closed when receiving")
            return
        if isinstance(event, wsproto.events.BytesMessage):
            console.log(f"Got message {event.data[1:]} on channel {event.data[0]}")
            if event.data[0] not in channels:
                channels.append(event.data[0])
                console.log(f"Got new channel {event.data[0]}")
        elif isinstance(event, wsproto.events.Pong):
            console.log("Got pong")
        else:
            console.log("Got event", event)


async def send_bytes(ws):
    """Send an HTTP request through the websocket connection."""
    while not len(channels) == 2:
        await anyio.sleep(0.1)
    request = b"\x00GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
    await ws.send(request)
    console.log(f"Sent request {request[1:]} to channel {request[0]}")


async def ping(ws):
    while True:
        try:
            await ws.ping()
            console.log("Sent ping")
        except wsproto.utilities.LocalProtocolError:
            console.log("Connection closed when pinging")
            return
        await anyio.sleep(10)


async def full_transaction(client, pod):
    async with ws_connect(
        client,
        f"/api/v1/namespaces/{pod.namespace}/pods/{pod.name}/portforward?ports=80",
    ) as ws:
        async with anyio.create_task_group() as tg:
            tg.start_soon(get_bytes, ws)
            tg.start_soon(send_bytes, ws)


async def main():
    pod = await gen_pod()
    auth = await KubeAuth()
    client = httpx.AsyncClient(
        base_url=auth.server,
        headers={"content-type": "application/json"},
        verify=await auth.ssl_context(),
    )

    async with anyio.create_task_group() as tg:
        tg.start_soon(full_transaction, client, pod)
        tg.start_soon(full_transaction, client, pod)
        tg.start_soon(full_transaction, client, pod)
        tg.start_soon(full_transaction, client, pod)
        tg.start_soon(full_transaction, client, pod)


if __name__ == "__main__":
    anyio.run(main)
