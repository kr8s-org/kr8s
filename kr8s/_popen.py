# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import collections
import enum
import functools
import json
import queue
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import anyio.abc
import anyio.streams.buffered
import anyio.streams.text
import httpx_ws

from kr8s._exceptions import ConnectionClosedError, ExecError

if TYPE_CHECKING:
    from kr8s._objects import APIObject, Pod


STDIN_CHANNEL: bytes = bytes([0])
STDOUT_CHANNEL: int = 1
STDERR_CHANNEL: int = 2
ERROR_CHANNEL: int = 3
RESIZE_CHANNEL: bytes = bytes([4])
CLOSE_CHANNEL: bytes = bytes([255])


class _NotSet(enum.Enum):
    NOT_SET = object()


_NOT_SET = _NotSet.NOT_SET


class Popen:
    """Executes a command in a running container returning a subprocess.Popen like object."""

    def __init__(
        self,
        resource: APIObject,
        *command: str,
        container: str | None = None,
        tty: bool | None = None,
        buffer: bool | None = None,
        text: bool | None = None,
        encoding: str | None = None,
        errors: str | None = None,
        stdin: bool | int | None = None,
        stdout: bool | None = None,
        stderr: bool | None = None,
        stderr2out: bool | None = None,
        timeout: int | None = None,
    ):
        self.resource: APIObject = resource
        self.pod: Pod | None = None
        self._container: str | None = container
        self.container: str | None = None
        self.command: tuple[str, ...] = command
        self.tty: bool = bool(tty)
        self.buffer: bool = bool(buffer)
        self.text: bool = bool(text)
        self.encoding: str | None = encoding
        self.error: str | None = errors
        self.stdin: anyio.abc.ByteSendStream | None = None
        self.stdout: anyio.abc.ByteReceiveStream | None = None
        self.stderr: anyio.abc.ByteReceiveStream | None = None
        self.result: dict | str | None = None
        self.returncode: int | None = None

        text_kwargs = {}
        if encoding:
            text_kwargs["encoding"] = encoding
        if errors:
            text_kwargs["errors"] = errors
        if stdin:
            self.stdin = self._Stdin(self)
            if self.text:
                self.stdin = anyio.streams.text.TextSendStream(
                    self.stdin, **text_kwargs
                )

        self._stdout_raw = None
        self._stderr_raw = None
        if stdout or stderr2out:
            self.stdout = self._stdout_raw = self._Stdout(self)
            if self.buffer:
                self.stdout = anyio.streams.buffered.BufferedByteReceiveStream(
                    self.stdout
                )
            if self.text:
                self.stdout = anyio.streams.text.TextReceiveStream(
                    self.stdout, **text_kwargs
                )
            if stderr2out:
                self._stderr_raw = self._stdout_raw
                if not stdout:
                    self._stdout_raw = None
        if stderr:
            if stderr2out:
                raise ValueError("stderr and stderr2out cannot be specified")
            self.stderr = self._stderr_raw = self._Stdout(self)
            if self.buffer:
                self.stderr = anyio.streams.buffered.BufferedByteReceiveStream(
                    self.stderr
                )
            if self.text:
                self.stderr = anyio.streams.text.TextReceiveStream(
                    self.stderr, **text_kwargs
                )
        self.timeout: int | None = timeout
        self._enter_task = None
        self._websocket = None
        self._recv_data_lock = anyio.Lock()
        self._frame_count = 0

    @property
    def timeout(self) -> float | None:
        """Timeout from now of all subsequest reads of stdout and stderr.

        Returns 0 for non-blocking reads and returns None for blocking reads.
        """
        if self._timeout is None:
            return None
        now = time.time()
        if now >= self._timeout:
            return 0.1
        return self._timeout - now

    @timeout.setter
    def timeout(self, timeout: int | float | None):
        if timeout is None:
            self._timeout = None
        else:
            if not isinstance(timeout, (int, float)):
                raise TypeError("timeout is not a number")
            self._timeout = time.time() + timeout

    @property
    def closed(self):
        return not self._websocket

    async def __aenter__(self):
        self._enter_task = self._async_enter()
        return await self._enter_task.__aenter__()

    async def __aexit__(self, *args, **kwargs) -> None:
        assert self._enter_task
        return await self._enter_task.__aexit__(*args, **kwargs)

    async def resize(self, width: int, height: int):
        """Inform the remote process the size of the TTY screen."""
        if self._websocket:
            resize = f'{{"Width":{width},"Height":{height}}}'.encode()
            await self._websocket.send_bytes(RESIZE_CHANNEL + resize)

    async def communicate(
        self,
        input: bytes | str | None = None,
        timeout: int | float | None | _NotSet = _NOT_SET,
    ) -> list[bytes | str | None]:
        """Interact with process: Send data to stdin and close it.

        Read data from stdout and stderr, until end-of-file is
        reached. Wait for process to terminate.

        The optional "input" argument should be data to be sent to the
        child process, or None, if no data should be sent to the child.
        communicate() returns a list [stdout, stderr].

        By default, all communication is in bytes, and therefore any
        "input" should be bytes, and the (stdout, stderr) will be bytes.
        If in text mode (indicated by self.text), any "input" should
        be a string, and [stdout, stderr] will be strings decoded
        according to locale encoding, or by "encoding" if set.
        """
        if self.closed:
            raise ValueError("Cannot call communicate after websocket close")
        if timeout is not _NOT_SET:
            self.timeout = timeout
        try:
            if self.stdin:
                if input:
                    await self.stdin.send(input)
                await self.stdin.aclose()
            results = [None, None]
            if self.stdout or self.stderr:
                if self.text:
                    initialize = list  # type: ignore
                    append = "append"

                    def finalize(result):
                        return "".join(result)

                else:
                    initialize = bytearray  # type: ignore
                    append = "extend"
                    finalize = bytes

                async def receive(initialize, append, finalize, results, ix, stream):
                    result = initialize()
                    append = getattr(result, append)
                    async for chunk in stream:
                        append(chunk)
                    results[ix] = finalize(result)

                receive = functools.partial(
                    receive, initialize, append, finalize, results
                )
                stdout_receive = functools.partial(receive, 0, self.stdout)
                stderr_receive = functools.partial(receive, 1, self.stderr)
                if self.stdout:
                    if self.stderr:
                        async with anyio.create_task_group() as group:
                            group.start_soon(stdout_receive)
                            group.start_soon(stderr_receive)
                    else:
                        await stdout_receive()
                elif self.stderr:
                    await stderr_receive()
            await self.wait()
            return results  # type: ignore
        finally:
            await self.close()

    async def wait(
        self, timeout: int | float | None | _NotSet = _NOT_SET
    ) -> int | None:
        """Wait for child process to terminate; returns self.returncode."""
        if self.closed:
            return None
        if timeout is not _NOT_SET:
            self.timeout = timeout
        try:
            if self.stdin:
                await self.stdin.aclose()
            if self.stdout:
                await self.stdout.aclose()
            if self.stderr:
                await self.stderr.aclose()
            while True:
                status = await self._recv_data_frame()
                if not status:
                    if status is None:
                        raise TimeoutError()
                    return self.returncode
        finally:
            await self.close()

    async def close(self):
        if self._websocket:
            await self._websocket.close()
            self._websocket = None

    @asynccontextmanager
    async def _async_enter(self) -> AsyncGenerator[Popen]:
        from kr8s._objects import Pod

        stdin = bool(self.stdin)
        # kubelet thinks at least one stream must be specified
        if not stdin and not self._stdout_raw and not self._stderr_raw:
            stdin = True
        connection_attempts = 0
        while True:
            if isinstance(self.resource, Pod):
                self.pod = self.resource
            else:
                if not hasattr(self.resource, "async_ready_pods"):
                    raise NotImplementedError(
                        f"{self.resource.kind} does not support exec"
                    )
                pods = await self.resource.async_ready_pods()  # type: ignore
                if not pods:
                    raise RuntimeError("No ready pods found")
                self.pod = pods[connection_attempts % len(pods)]
            if self._container:
                self.container = self._container
            else:
                try:
                    self.container = self.pod.annotations[
                        "kubectl.kubernetes.io/default-container"
                    ]
                except KeyError:
                    self.container = self.pod.spec.containers[0].name
            try:
                assert self.pod.api
                async with self.pod.api.async_open_websocket(
                    version=self.pod.version,
                    url=f"{self.pod.endpoint}/{self.pod.name}/exec",
                    subprotocols=(
                        "v5.channel.k8s.io",
                        "v4.channel.k8s.io",
                    ),
                    namespace=self.pod.namespace,
                    params={
                        "container": self.container,
                        "command": self.command,
                        "tty": str(self.tty).lower(),
                        "stdin": str(stdin).lower(),
                        "stdout": str(bool(self._stdout_raw)).lower(),
                        "stderr": str(bool(self._stderr_raw)).lower(),
                    },
                ) as websocket:
                    if stdin:
                        if self.stdin:
                            if websocket.subprotocol != "v5.channel.k8s.io":
                                raise ExecError(
                                    "stdin is not supported with Kubernetes versions less than 1.30"
                                )
                        else:
                            if websocket.subprotocol == "v5.channel.k8s.io":
                                await websocket.send_bytes(
                                    CLOSE_CHANNEL + STDIN_CHANNEL
                                )
                    self._websocket = websocket
                    yield self
                    await self.close()
                    return
            except httpx_ws.HTTPXWSException as ex:
                self.pod = None
                self.container = None
                connection_attempts += 1
                if connection_attempts > 5:
                    raise ConnectionClosedError("Unable to connect to Pod") from ex
                await anyio.sleep(0.2 * connection_attempts)

    class _Stdin(anyio.abc.ByteSendStream):
        def __init__(self, popen):
            self.closed = False
            self._popen = popen

        async def send(self, item: bytes) -> None:
            if not self.closed and not self._popen.closed:
                await self._popen._websocket.send_bytes(STDIN_CHANNEL + item)

        async def aclose(self) -> None:
            if not self.closed:
                self.closed = True
                if (
                    not self._popen.closed
                    and self._popen._websocket.subprotocol == "v5.channel.k8s.io"
                ):
                    await self._popen._websocket.send_bytes(
                        CLOSE_CHANNEL + STDIN_CHANNEL
                    )

    class _Stdout(anyio.abc.ByteReceiveStream):
        def __init__(self, popen):
            self.closed = False
            self._popen = popen
            self._frames = collections.deque()
            self._ix = 1

        async def receive(self, max_size: int = 65536) -> bytes:
            if self.closed:
                raise anyio.EndOfStream()
            while not self._frames:
                status = await self._popen._recv_data_frame()
                if not status:
                    if status is None:
                        raise TimeoutError()
                    raise anyio.EndOfStream()
            if len(self._frames[0]) - self._ix <= max_size:
                data = self._frames[0][self._ix :]
                self._frames.popleft()
                self._ix = 1
            else:
                data = self._frames[0][self._ix : self._ix + max_size]
                self._ix += max_size
            return data

        async def aclose(self) -> None:
            self.closed = True
            self._frames.clear()
            self._ix = 1

    async def _recv_data_frame(self):
        # Returns True if frame read, False if websocket is closed,
        # and None if timeed out with no frames read.
        count = self._frame_count
        async with self._recv_data_lock:
            if count != self._frame_count:
                return True
            if self.closed:
                return False
            try:
                frame = await self._websocket.receive_bytes(timeout=self.timeout)
            except (TimeoutError, queue.Empty):
                return None
            except httpx_ws.WebSocketDisconnect:
                await self.close()
                if self.returncode is None:
                    self.returncode = -4
                return False
            channel = frame[0]
            if channel == STDOUT_CHANNEL:
                if self._stdout_raw and not self._stdout_raw.closed and len(frame) > 1:
                    self._stdout_raw._frames.append(frame)
                self._frame_count += 1
                return True
            if channel == STDERR_CHANNEL:
                if self._stderr_raw and not self._stderr_raw.closed and len(frame) > 1:
                    self._stderr_raw._frames.append(frame)
                self._frame_count += 1
                return True
            if channel == ERROR_CHANNEL:
                if len(frame) > 2 and frame[1] == ord("{") and frame[-1] == ord("}"):
                    self.result = json.loads(frame[1:])
                    if self.result.get("status") == "Success":
                        self.returncode = 0
                    else:
                        for cause in self.result.get("details", {}).get("causes", []):
                            if cause.get("reason") == "ExitCode":
                                self.returncode = int(cause.get("message", -3))
                                break
                        else:
                            self.returncode = -2
                else:
                    self.result = frame[1:].decode()
                    self.returncode = -1
                await self.close()
                return False
