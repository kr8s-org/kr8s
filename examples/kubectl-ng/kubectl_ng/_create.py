# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License

import typer
from rich.console import Console

import kr8s.asyncio
from kr8s.asyncio.objects import objects_from_files

console = Console()


# Missing Options
# TODO --allow-missing-template-keys='true'
# TODO --dry-run='none'
# TODO --edit='false'
# TODO --field-manager=''
# TODO -k, --kustomize=''
# TODO -o, --output=''
# TODO --raw='false'
# TODO -R, --recursive='false'
# TODO --save-config='false'
# TODO -l, --selector=''
# TODO --show-managed-fields='false'
# TODO --template=''
# TODO --validate='true'
# TODO --windows-line-endings='false'


async def create(
    filename: str = typer.Option(
        "",
        "--filename",
        "-f",
        help="Filename, directory, or URL to files identifying the resources to create",
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
            await obj.create()
        except Exception as e:
            console.print(f"[red]Error creating {obj}[/red]: {e}")
            raise typer.Exit(1)
        console.print(f'[green]{obj.singular} "{obj}" created [/green]')
