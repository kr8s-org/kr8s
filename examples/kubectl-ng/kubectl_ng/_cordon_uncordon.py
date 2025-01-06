# SPDX-FileCopyrightText: Copyright (c) 2024-2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License

import typer
from rich.console import Console

from kr8s.asyncio.objects import Node

console = Console()


# Missing Options
# TODO --dry-run='none'
# TODO -l, --selector=''


async def cordon(
    node: str = typer.Argument(..., help="NODE"),
):
    """Mark node as unschedulable.

    Examples:
        # Mark node "foo" as unschedulable
        kubectl-ng cordon foo
    """
    nodes = [await Node.get(node)]
    for node_instance in nodes:
        await node_instance.cordon()
        console.print(f"node/{node_instance.name} cordoned")


async def uncordon(
    node: str = typer.Argument(..., help="NODE"),
):
    """Mark node as schedulable.

    Examples:
        # Mark node "foo" as schedulable
        kubectl-ng uncordon foo
    """
    nodes = [await Node.get(node)]
    for node_instance in nodes:
        await node_instance.uncordon()
        console.print(f"node/{node_instance.name} uncordoned")
