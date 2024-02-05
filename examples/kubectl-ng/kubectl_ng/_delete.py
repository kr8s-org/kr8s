# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License

import anyio
import typer
from rich.console import Console

import kr8s.asyncio
from kr8s.asyncio.objects import objects_from_files

console = Console()


# Missing Options
# TODO --all=false
# TODO -A, --all-namespaces=false
# TODO --cascade='background'
# TODO --dry-run='none'
# TODO --field-selector=''
# TODO --force=false
# TODO --grace-period=-1
# TODO --ignore-not-found=false
# TODO -k, --kustomize=''
# TODO --now='false'
# TODO -o, --output=''
# TODO --raw='false'
# TODO -R, --recursive='false'
# TODO -l, --selector=''
# TODO --timeout='0s'
# TODO --wait='true'


async def delete(
    filename: str = typer.Option(
        "",
        "--filename",
        "-f",
        help="Filename, directory, or URL to files identifying the resources to delete",
    ),
    wait: bool = typer.Option(
        True,
        "--wait",
        help="If true, wait for resources to be gone before returning. This waits for finalizers.",
    ),
):
    api = await kr8s.asyncio.api()
    try:
        objs = await objects_from_files(filename, api)
    except Exception as e:
        console.print(f"[red]Error loading objects from {filename}[/red]: {e}")
        raise typer.Exit(1)
    for obj in objs:
        try:
            await obj.delete()
        except Exception as e:
            console.print(f"[red]Error deleting {obj}[/red]: {e}")
            raise typer.Exit(1)
        console.print(f'[green]{obj.singular} "{obj}" deleted [/green]')
    async with anyio.create_task_group() as tg:
        for obj in objs:
            if wait:
                tg.start_soon(obj.wait, "delete")
