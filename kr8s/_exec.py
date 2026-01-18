# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import functools
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO

import anyio

from kr8s._exceptions import ExecError

if TYPE_CHECKING:
    from kr8s._objects import APIObject


class Exec:
    """Executes a command in a running container."""

    def __init__(
        self,
        resource: APIObject,
        command: str | list[str],
        container: str | None = None,
        stdin: bytes | str | BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        check: bool = True,
        capture_output: bool = True,
        timeout: int | None = None,
    ) -> None:
        self._resource = resource
        self._container = container

        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self._capture_output = capture_output
        self._timeout = timeout

        self.args: str | list[str] = command
        self.stdout: bytes = b""
        self.stderr: bytes = b""
        self.returncode: int | None = None
        self.check: bool = check

    @asynccontextmanager
    async def run(
        self,
    ) -> AsyncGenerator[Exec, CompletedExec]:
        assert self._resource.api

        async with self._resource.async_popen(
            *self.args,
            container=self._container,
            stdin=self._stdin is not None,
            stdout=bool(self._capture_output or self._stdout),
            stderr=bool(self._capture_output or self._stderr),
            timeout=self._timeout,
        ) as popen:
            stdin = self._stdin
            if stdin is not None and popen.stdin:
                if isinstance(stdin, str):
                    stdin = stdin.encode()
                elif isinstance(stdin, BinaryIO):
                    stdin = stdin.read()
                await popen.stdin.send(stdin)
                await popen.stdin.aclose()
            output = bytearray()
            error = bytearray()

            async def receive(stream, output, buffer):
                async for chunk in stream:
                    if output:
                        output.write(chunk)
                    if buffer is not None:
                        buffer.extend(chunk)

            stdout_receive = functools.partial(
                receive,
                popen.stdout,
                self._stdout,
                output if self._capture_output else None,
            )
            stderr_receive = functools.partial(
                receive,
                popen.stderr,
                self._stderr,
                error if self._capture_output else None,
            )
            if self._capture_output or (self._stdout and self._stderr):
                async with anyio.create_task_group() as group:
                    group.start_soon(stdout_receive)
                    group.start_soon(stderr_receive)
            elif self._stdout:
                await stdout_receive()
            elif self._stderr:
                await stderr_receive()
            await popen.wait()
            self.stdout = bytes(output)
            self.stderr = bytes(error)
            self.returncode = popen.returncode
            if self.returncode:
                if self.returncode < 0:
                    self.returncode = 1
                if self.check:
                    if isinstance(popen.result, dict) and "message" in popen.result:
                        raise ExecError(popen.result["message"])
                    raise ExecError(popen.result)
            yield self

    async def wait(self) -> CompletedExec:
        return self.as_completed()

    def as_completed(self) -> CompletedExec:
        return CompletedExec(
            args=self.args,
            stdout=self.stdout,
            stderr=self.stderr,
            returncode=self.returncode,
        )


@dataclass
class CompletedExec:
    """Result of an Exec command.

    Similar to subprocess.CompletedProcess.
    """

    args: str | list[str]
    stdout: bytes
    stderr: bytes
    returncode: int | None

    def check_returncode(self) -> None:
        if self.returncode != 0:
            raise ExecError(f"Command {self.args} exited with status {self.returncode}")
