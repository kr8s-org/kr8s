# SPDX-FileCopyrightText: Copyright (c) 2024-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""Objects for managing a port forward connection.

This module provides a class for managing a port forward connection to a Kubernetes Pod or Service.
"""

# Disable missing docstrings, these are inherited from the async version of the objects
# ruff: noqa: D102, D105
from __future__ import annotations

import io
import json
import queue
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import httpx_ws

from kr8s._exceptions import ConnectionClosedError, ExecError
from kr8s._popen import (
    _NOT_SET,
    CLOSE_CHANNEL,
    ERROR_CHANNEL,
    RESIZE_CHANNEL,
    STDERR_CHANNEL,
    STDIN_CHANNEL,
    STDOUT_CHANNEL,
    _NotSet,
)

if TYPE_CHECKING:
    from kr8s._objects import APIObject
    from kr8s.objects import Pod


__all__ = ["Popen"]


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
        """Executes a command in a running container returning a subprocess.Popen like object."""
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
        self.stdin: io.RawIOBase | None = None
        self.stdout: io.RawIOBase | None = None
        self.stderr: io.RawIOBase | None = None
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
                self.stdin = io.TextIOWrapper(  # type: ignore
                    self.stdin,
                    encoding=encoding,
                    errors=errors,
                    line_buffering=self.buffer,
                    write_through=True,
                )
        self._stdout_raw = None
        self._stderr_raw = None
        if stdout or stderr2out:
            self.stdout = self._stdout_raw = self._Stdout(self)
            if self.buffer:
                self.stdout = io.BufferedReader(self._stdout_raw)  # type: ignore
            if self.text:
                self.stdout = io.TextIOWrapper(  # type: ignore
                    self.stdout, encoding=encoding, errors=errors
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
                self.stderr = io.BufferedReader(self._stderr_raw)  # type: ignore
            if self.text:
                self.stderr = io.TextIOWrapper(  # type: ignore
                    self.stderr, encoding=encoding, errors=errors
                )
        self.timeout = timeout
        self._enter_task = None
        self._websocket = None
        self._recv_data_lock = threading.Lock()
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

    def __enter__(self):
        self._enter_task = self._enter()
        return self._enter_task.__enter__()

    def __exit__(self, *args, **kwargs) -> None:
        assert self._enter_task
        return self._enter_task.__exit__(*args, **kwargs)

    def resize(self, width: int, height: int):
        """Inform the remote process the size of the TTY screen."""
        if self._websocket:
            resize = f'{{"Width":{width},"Height":{height}}}'.encode()
            self._websocket.send_bytes(RESIZE_CHANNEL + resize)

    def communicate(
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
                    self.stdin.write(input)  # type: ignore
                self.stdin.close()
            if self.stdout:
                stdout = self.stdout.read()
                self.stdout.close()
            else:
                stdout = None
            if self.stderr:
                stderr = self.stderr.read()
                self.stderr.close()
            else:
                stderr = None
            self.wait()
            return [stdout, stderr]
        finally:
            self.close()

    def wait(self, timeout: int | float | None | _NotSet = _NOT_SET) -> int | None:
        """Wait for child process to terminate; returns self.returncode."""
        if self.closed:
            return None
        if timeout is not _NOT_SET:
            self.timeout = timeout
        try:
            if self.stdout:
                self.stdout.close()
            if self.stderr:
                self.stderr.close()
            while True:
                status = self._recv_data_frame()
                if not status:
                    if status is None:
                        raise TimeoutError()
                    return self.returncode
        finally:
            self.close()

    def close(self):
        if self._websocket:
            self._websocket.close()
            self._websocket = None

    @contextmanager
    def _enter(self) -> Generator[Popen]:
        from kr8s.objects import Pod

        stdin = bool(self.stdin)
        # kubelet thinks at least one stream must be specified
        if not stdin and not self._stdout_raw and not self._stderr_raw:
            stdin = True
        connection_attempts = 0
        while True:
            if isinstance(self.resource, Pod):
                self.pod = self.resource
            else:
                if not hasattr(self.resource, "ready_pods"):
                    raise NotImplementedError(
                        f"{self.resource.kind} does not support exec"
                    )
                pods = self.resource.ready_pods()  # type: ignore
                if not pods:
                    raise RuntimeError("No ready pods found")
                self.pod = pods[connection_attempts % len(pods)]
            if self._container:
                self.container = self._container
            else:
                try:
                    assert self.pod
                    self.container = self.pod.annotations[
                        "kubectl.kubernetes.io/default-container"
                    ]
                except KeyError:
                    self.container = self.pod.spec.containers[0].name
            try:
                assert self.pod.api
                with self.pod.api.open_websocket(
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
                                websocket.send_bytes(CLOSE_CHANNEL + STDIN_CHANNEL)
                    self._websocket = websocket
                    yield self
                    self.close()
                    return
            except httpx_ws.HTTPXWSException as ex:
                self.pod = None
                self.container = None
                connection_attempts += 1
                if connection_attempts > 5:
                    raise ConnectionClosedError("Unable to connect to Pod") from ex
                time.sleep(0.2 * connection_attempts)

    class _Stdin(io.RawIOBase):
        def __init__(self, popen):
            super().__init__()
            self._popen = popen

        def writable(self):
            return True

        def write(self, b):
            if self._popen.closed:
                return 0
            self._popen._websocket.send_bytes(STDIN_CHANNEL + b)
            return len(b)

        def close(self):
            super().close()
            if (
                not self._popen.closed
                and self._popen._websocket.subprotocol == "v5.channel.k8s.io"
            ):
                self._popen._websocket.send_bytes(CLOSE_CHANNEL + STDIN_CHANNEL)

    class _Stdout(io.RawIOBase):
        def __init__(self, popen):
            super().__init__()
            self._popen = popen
            self._frames = []
            self._ix = 1

        def readable(self):
            return True

        def readinto(self, b):
            while not self._frames:
                status = self._popen._recv_data_frame()
                if not status:
                    if status is None:
                        raise TimeoutError()
                    return 0
            size = len(self._frames[0]) - self._ix
            if size <= len(b):
                b[:size] = self._frames[0][self._ix :]
                del self._frames[0]
                self._ix = 1
            else:
                size = len(b)
                b[:] = self._frames[0][self._ix : self._ix + size]
                self._ix += size
            return size

        def close(self):
            super().close()
            self._frames = []
            self._ix = 1

    def _recv_data_frame(self):
        # Returns True if frame read, False if websocket is closed,
        # and None if timeed out with no frames read.
        count = self._frame_count
        with self._recv_data_lock:
            if count != self._frame_count:
                return True
            if self.closed:
                return False
            try:
                frame = self._websocket.receive_bytes(timeout=self.timeout)
            except (TimeoutError, queue.Empty):
                return None
            except httpx_ws.WebSocketDisconnect:
                self.close()
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
                self.close()
                return False
