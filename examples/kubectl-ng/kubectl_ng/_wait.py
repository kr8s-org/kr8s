# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import json
import sys
from typing import List, Optional

import typer
import yaml
from rich.console import Console
from rich.syntax import Syntax
from typing_extensions import Annotated

import kr8s

console = Console()


async def wait(
    resources: Annotated[
        Optional[List[str]], typer.Argument(..., help="TYPE[.VERSION][.GROUP]")
    ] = None,
    filename: str = typer.Option(
        "",
        "-f",
        "--filename",
        help="Filename, directory, or URL to files identifying the resource to wait on",
    ),
    label_selector: str = typer.Option(
        "",
        "-l",
        "--selector",
        help="Selector (label query) to filter on, supports '=', '==', and '!='. "
        "(e.g. -l key1=value1,key2=value2). "
        "Matching objects must satisfy all of the specified label constraints.",
    ),
):
    if filename:
        console.print("error: --filename is not supported yet")
        raise typer.Exit(code=1)
    console.print("Waiting...")
