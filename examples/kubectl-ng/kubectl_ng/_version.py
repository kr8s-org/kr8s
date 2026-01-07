# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import json
import sys

import typer
import yaml
from rich.console import Console
from rich.syntax import Syntax

import kr8s

console = Console()

try:
    from .__version import version as __version__  # noqa
    from .__version import version_tuple as __version_tuple__  # noqa
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)


async def version(
    client: bool = typer.Option(
        False,
        "--client",
        help="If true, shows client version only (no server required).",
    ),
    output: str = typer.Option(
        "",
        "-o",
        "--output",
        help="One of 'yaml' or 'json'.",
    ),
):
    """Print the client and server version information for the current context.

    Examples:
        # Print the client and server versions for the current context
        kubectl version
    """
    versions = {}
    versions["clientVersion"] = {
        "client": "kubectl-ng",
        "gitVersion": __version__,
        "major": __version_tuple__[0],
        "minor": __version_tuple__[1],
        "pythonVersion": sys.version,
    }
    if not client:
        api = await kr8s.asyncio.api()
        versions["serverVersion"] = await api.version()

    if output == "":
        style = "[magenta][bold]"
        client_version = versions["clientVersion"]["gitVersion"]
        console.print(f"Client Version: {style}v{client_version}")
        server_version = versions["serverVersion"]["gitVersion"]
        console.print(f"Server Version: {style}{server_version}")

    elif output == "yaml":
        console.print(
            Syntax(
                yaml.dump(versions),
                "yaml",
                background_color="default",
            )
        )

    elif output == "json":
        console.print(
            Syntax(
                json.dumps(versions, indent=2),
                "json",
                background_color="default",
            )
        )

    else:
        console.print("error: --output must be 'yaml' or 'json'")
        raise typer.Exit(code=1)
