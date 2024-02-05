# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import sys
from typing import List

import typer
from rich.console import Console

from kr8s.asyncio.objects import Pod

console = Console()


async def kexec(
    resource: str = typer.Argument(..., help="POD | TYPE/NAME"),
    namespace: str = typer.Option(
        None,
        "-n",
        "--namespace",
    ),
    container: str = typer.Option(
        None,
        "-c",
        "--container",
        help="Container name. "
        "If omitted, use the kubectl.kubernetes.io/default-container annotation "
        "for selecting the container to be attached or the first container in the "
        "pod will be chosen",
    ),
    command: List[str] = typer.Argument(..., help="COMMAND [args...]"),
):
    """Execute a command in a container."""
    pod = await Pod.get(resource, namespace=namespace)
    await pod.exec(
        command,
        container=container,
        stdout=sys.stdout.buffer,
        stderr=sys.stderr.buffer,
        check=False,
    )
