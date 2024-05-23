# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
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
        help="Output format. One of: (wide, name).",
    ),
    api_group: str = typer.Option(
        "", "--api-group", help="Limit to resources in the specified API group."
    ),
    categories: str = typer.Option(
        "",
        "--categories",
        help="Limit to resources that belong the the specified categories. Comma separated list of categories.",
    ),
    namespaced: str = typer.Option(
        None,
        "--namespaced",
        help="If false, non-namespaced resources will be returned, "
        "otherwise returning namespaced resources by default.",
    ),
    headers: bool = typer.Option(
        True,
        help="When using the default or custom-column output format, don't print headers (default print headers).",
    ),
    sort_by: str = typer.Option(
        None,
        "--sort-by",
        help="If non-empty, sort list of resources using specified field. The field can be either 'name' or 'kind'.",
    ),
    verbs: str = typer.Option(
        "",
        "--verbs",
        help="Limit to resources that support the specified verbs. Comma separated list of verbs.",
    ),
):
    """Print the supported API resources on the server.

    Examples:
        # Print the supported API resources
        kubectl-ng api-resources

        # Print the supported API resources with more information
        kubectl-ng api-resources -o wide

        # Print the supported API resources sorted by a column
        kubectl-ng api-resources --sort-by=name

        # Print the supported namespaced resources
        kubectl-ng api-resources --namespaced=true

        # Print the supported non-namespaced resources
        kubectl-ng api-resources --namespaced=false

        # Print the supported API resources with a specific APIGroup
        kubectl-ng api-resources --api-group=rbac.authorization.k8s.io

    """
    kubernetes = await kr8s.asyncio.api()
    categories = [c.strip() for c in categories.split(",")] if categories else None
    verbs = [v.strip() for v in verbs.split(",")] if verbs else None

    resources = await kubernetes.api_resources()

    table = Table(box=box.SIMPLE, show_header=headers)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Short Names")
    table.add_column("API Version")
    table.add_column("Namespaced")
    table.add_column("Kind")
    if output == "wide":
        table.add_column("Verbs", no_wrap=True)
        table.add_column("Categories", no_wrap=True)

    if output == "name":
        for resource in resources:
            if resource["version"] != "v1":
                console.print(f"{resource['name']}.{resource['version'].split('/')[0]}")
            else:
                console.print(resource["name"])
        return

    if sort_by == "name":
        resources = sorted(resources, key=lambda r: r["name"])
    elif sort_by == "kind":
        resources = sorted(resources, key=lambda r: r["kind"])

    for resource in resources:
        if (
            (not api_group or resource["version"].startswith(api_group))
            and (
                categories is None
                or set(categories).issubset(set(resource.get("categories", [])))
            )
            and (
                namespaced is None or str(resource["namespaced"]).lower() == namespaced
            )
            and (verbs is None or set(verbs).issubset(set(resource.get("verbs", []))))
        ):
            if output == "name":
                if resource["version"] != "v1":
                    console.print(
                        f"{resource['name']}.{resource['version'].split('/')[0]}"
                    )
                else:
                    console.print(resource["name"])
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

    if output != "name":
        console.print(table)
