# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import rich.table
import typer
from rich import box
from rich.console import Console

import kr8s

console = Console()

config = typer.Typer(
    no_args_is_help=True,
    name="config",
    help="Modify kubeconfig files.",
)


@config.command(name="current-context", help="Display the current-context")
def config_current_context():
    """Display the current context."""
    try:
        typer.echo(kr8s.api().auth.kubeconfig.current_context)
    except KeyError:
        typer.echo("error: current-context is not set")


@config.command(name="get-clusters", help="Display clusters defined in the kubeconfig")
def config_get_clusters():
    """Display clusters defined in the kubeconfig."""
    try:
        clusters = [cluster["name"] for cluster in kr8s.api().auth.kubeconfig.clusters]
    except:  # noqa
        clusters = []

    table = rich.table.Table(box=box.SIMPLE)
    table.add_column("Name", style="magenta", no_wrap=True)
    for cluster in clusters:
        table.add_row(cluster)

    console.print(table)


@config.command(name="get-users", help="Display users defined in the kubeconfig")
def config_get_users():
    """Display users defined in the kubeconfig."""
    try:
        users = [user["name"] for user in kr8s.api().auth.kubeconfig.users]
    except:  # noqa
        users = []

    table = rich.table.Table(box=box.SIMPLE)
    table.add_column("Name", style="magenta", no_wrap=True)
    for user in users:
        table.add_row(user)

    console.print(table)
