# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import typer
from rich import box
from rich.console import Console
from rich.table import Table

import kr8s

console = Console()


async def api_resources(
    output: str = typer.Option(
        None,
        "-o",
        "--output",
    ),
):
    """Print the supported API resources on the server."""
    kubernetes = kr8s.Kr8sApi()

    resources = await kubernetes.api_resources()

    if output == "name":
        for resource in resources:
            if "/" not in resource["name"]:
                if resource["version"] != "v1":
                    console.print(
                        f"{resource['name']}.{resource['version'].split('/')[0]}"
                    )
                else:
                    console.print(resource["name"])
        return

    table = Table(box=box.SIMPLE)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Short Names")
    table.add_column("API Version")
    table.add_column("Namespaced")
    table.add_column("Kind")
    if output == "wide":
        table.add_column("Verbs", no_wrap=True)
        table.add_column("Categories", no_wrap=True)

    for resource in resources:
        if "/" not in resource["name"]:
            data = [
                resource["name"],
                "[magenta]" + ",".join(resource.get("shortNames", [])),
                resource["version"],
                "[green]true" if resource["namespaced"] else "[indian_red1]false",
                resource["kind"],
            ]
            if output == "wide":
                data.append(",".join(resource["verbs"]))
                data.append(",".join(resource.get("categories", [])))
            table.add_row(*data)
    console.print(table)
