# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import typer
from rich.console import Console

import kr8s

console = Console()


async def version(
    client: bool = typer.Option(
        False,
        "--client",
        help="If true, shows client version only (no server required).",
    ),
):
    """Print the client and server version information for the current context.

    Examples:
        # Print the client and server versions for the current context
        kubectl version
    """
    console.print(f"Client Version: [magenta][bold]v{kr8s.__version__}")
    if not client:
        api = kr8s.asyncio.api()
        server_version = await api.version()
        console.print(f"Server Version: [magenta][bold]{server_version['gitVersion']}")
