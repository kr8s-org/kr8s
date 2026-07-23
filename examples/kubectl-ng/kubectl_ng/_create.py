# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from typing import Any

import typer
from rich.console import Console

import kr8s.asyncio
from kr8s import ValidateOption
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
# TODO --windows-line-endings='false'


def parse_validate(validate: str) -> ValidateOption:
    normalised = validate.lower()
    if normalised in {"true", "false"}:
        return bool(normalised == "true")
    elif normalised in {"strict", "warn", "ignore"}:
        return normalised
    else:
        raise typer.BadParameter(
            f"Invalid validate option: {validate}. It must be one of strict, warn, ignore.",
            param_hint="validate",
        )


async def create(
    filename: str = typer.Option(
        "",
        "--filename",
        "-f",
        help="Filename, directory, or URL to files identifying the resources to create",
    ),
    validate: Any = typer.Option(
        "strict",
        "--validate",
        help="Must be one of strict, warn, ignore."
        ' "strict" will perform server side validation.'
        ' "warn" will warn about unknown or duplicate fields without blocking the request.'
        ' "ignore" will not perform any schema validation.',
        parser=parse_validate,
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
            await obj.create(validate=validate)
        except Exception as e:
            console.print(f"[red]Error creating {obj}[/red]: {e}")
            raise typer.Exit(1)
        console.print(f'[green]{obj.singular} "{obj}" created [/green]')
