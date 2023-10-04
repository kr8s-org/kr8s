# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, List

import aiohttp

if TYPE_CHECKING:
    from kr8s._objects import APIObject

STDIN_CHANNEL = 0
STDOUT_CHANNEL = 1
STDERR_CHANNEL = 2
ERROR_CHANNEL = 3
RESIZE_CHANNEL = 4


class ExecError(Exception):
    """Internal error in the exec protocol."""


class Exec:
    """Executes a command in a running container."""

    def __init__(
        self,
        resource: APIObject,
        command: List[str],
        container: str = None,
        stdout: bool = True,
        stderr: bool = True,
    ) -> None:
        self._resource = resource
        self._command = command
        self._container = container
        self._stdout = stdout
        self._stderr = stderr
        self.stdout = ""
        self.stderr = ""

    @asynccontextmanager
    async def run(
        self,
    ) -> None:
        async with self._resource.api.open_websocket(
            version=self._resource.version,
            url=f"{self._resource.endpoint}/{self._resource.name}/exec",
            namespace=self._resource.namespace,
            params={
                "command": self._command,
                "container": self._container or self._resource.spec.containers[0].name,
                "stdout": str(self._stdout).lower(),
                "stderr": str(self._stderr).lower(),
            },
        ) as ws:
            async for message in ws:
                if message.type == aiohttp.WSMsgType.BINARY:
                    # Let's try to understand the exec protocol
                    channel, message = int(message.data[0]), message.data[1:].decode()
                    if message:
                        if channel == STDOUT_CHANNEL:
                            self.stdout(message)
                        elif channel == STDERR_CHANNEL:
                            self.stderr.append(message)
                        elif channel == ERROR_CHANNEL:
                            raise ExecError(message)
                        else:
                            raise RuntimeError(
                                f"Unhandled message on channel {channel}: {message}"
                            )
                elif message.type == aiohttp.WSMsgType.CLOSED:
                    if message["status"] != 0:
                        raise RuntimeError(
                            f"Command {self._command} exited with status {message['status']}"
                        )
            yield self
