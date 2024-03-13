# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO, List, Union

from kr8s._exceptions import ExecError

if TYPE_CHECKING:
    from kr8s._objects import APIObject

STDIN_CHANNEL = 0
STDOUT_CHANNEL = 1
STDERR_CHANNEL = 2
ERROR_CHANNEL = 3
RESIZE_CHANNEL = 4
CLOSE_CHANNEL = 255
EXEC_PROTOCOL = "v4.channel.k8s.io"


class Exec:
    """Executes a command in a running container."""

    def __init__(
        self,
        resource: APIObject,
        command: List[str],
        container: str = None,
        stdin: Union[str | BinaryIO] = None,
        stdout: Union[str | BinaryIO] = None,
        stderr: Union[str | BinaryIO] = None,
        check: bool = True,
        capture_output: bool = True,
    ) -> None:
        self._resource = resource
        self._container = container

        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self._capture_output = capture_output

        self.args = command
        self.stdout = b""
        self.stderr = b""
        self.returncode = None
        self.check = check

    @asynccontextmanager
    async def run(
        self,
    ) -> None:
        async with self._resource.api.open_websocket(
            version=self._resource.version,
            url=f"{self._resource.endpoint}/{self._resource.name}/exec",
            subprotocols=(EXEC_PROTOCOL,),
            namespace=self._resource.namespace,
            params={
                "command": self.args,
                "container": self._container or self._resource.spec.containers[0].name,
                "stdout": "true" if self._stdout or self._capture_output else "false",
                "stderr": "true" if self._stderr or self._capture_output else "false",
                "stdin": "true" if self._stdin is not None else "false",
            },
        ) as ws:
            if self._stdin:
                if ws.subprotocol != "v5.channel.k8s.io":
                    raise ExecError(
                        "Stdin is not supported with protocol "
                        f"{ws.protocol}, only with v5.channel.k8s.io"
                    )
                if isinstance(self._stdin, str):
                    await ws.send_bytes(STDIN_CHANNEL.to_bytes() + self._stdin.encode())
                else:
                    await ws.send_bytes(STDIN_CHANNEL.to_bytes() + self._stdin.read())
                await ws.send_bytes(CLOSE_CHANNEL.to_bytes() + STDIN_CHANNEL.to_bytes())
            while True:
                message = await ws.receive_bytes()
                channel, message = int(message[0]), message[1:]
                if message:
                    if channel == STDOUT_CHANNEL:
                        if self._capture_output:
                            self.stdout += message
                        if self._stdout:
                            self._stdout.write(message)
                    elif channel == STDERR_CHANNEL:
                        if self._capture_output:
                            self.stderr += message
                        if self._stderr:
                            self._stderr.write(message)
                    elif channel == ERROR_CHANNEL:
                        error = json.loads(message.decode())
                        if error["status"] == "Success":
                            self.returncode = 0
                            break
                        # Extract return code from details
                        if "details" in error and "causes" in error["details"]:
                            for cause in error["details"]["causes"]:
                                if "reason" in cause and cause["reason"] == "ExitCode":
                                    self.returncode = int(cause["message"])
                                    break
                        else:
                            self.returncode = 1
                        if self.check:
                            raise ExecError(error["message"])
                        break
                    else:
                        raise ExecError(
                            f"Unhandled message on channel {channel}: {message}"
                        )
            yield self

    async def wait(self) -> CompletedExec:
        return self.returncode

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

    args: Union(str | List[str])
    stdout: bytes
    stderr: bytes
    returncode: int

    def check_returncode(self) -> None:
        if self.returncode != 0:
            raise ExecError(f"Command {self.args} exited with status {self.returncode}")
