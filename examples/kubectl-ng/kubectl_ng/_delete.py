# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License

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
