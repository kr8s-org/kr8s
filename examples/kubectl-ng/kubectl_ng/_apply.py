# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License

import json

import typer
from rich.console import Console

import kr8s.asyncio
from kr8s.asyncio.objects import objects_from_files

console = Console()


async def apply(
    filename: str = typer.Option(
        "",
        "--filename",
        "-f",
        help="Filename, directory, or URL to files identifying the resource to wait on",
    ),
):
    api = await kr8s.asyncio.api()
    try:
        objs = await objects_from_files(filename, api)
    except Exception as e:
        console.print(f"[red]Error loading objects from {filename}[/red]: {e}")
        raise typer.Exit(1)
    successful = True
    for obj in objs:
        if not obj.annotations:
            obj.raw["metadata"]["annotations"] = {}
        obj.raw["metadata"]["annotations"][
            "kubectl.kubernetes.io/last-applied-configuration"
        ] = json.dumps(obj.raw)
        try:
            await obj.apply()
            # TODO detect if created, modified or unchanged
            console.print(f"[green]{obj.singular}/{obj.name} applied[/green]")
        except Exception as e:
            console.print(f"[red]{obj.singular}/{obj.name} failed[/red]: {e}")
            successful = False
            continue
    if not successful:
        raise typer.Exit(1)
