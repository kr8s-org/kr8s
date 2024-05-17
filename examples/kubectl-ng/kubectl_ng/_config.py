# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from typing import Optional

import rich.table
import typer
from rich import box
from rich.console import Console
from typing_extensions import Annotated

import kr8s

from ._typer_utils import register

console = Console()

config = typer.Typer(
    no_args_is_help=True,
    name="config",
    help="Modify kubeconfig files.",
)


def config_current_context():
    """Display the current context."""
    try:
        typer.echo(kr8s.api().auth.kubeconfig.current_context)
    except KeyError:
        typer.echo("error: current-context is not set")
        raise typer.Exit(code=1)


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


def config_get_contexts(name: Annotated[Optional[str], typer.Argument()] = None):
    """Display users defined in the kubeconfig."""
    try:
        kubeconfig = kr8s.api().auth.kubeconfig
        contexts = kubeconfig.contexts
    except:  # noqa
        contexts = []

    table = rich.table.Table(box=box.SIMPLE)
    table.add_column("Current", no_wrap=True)
    table.add_column("Name", style="magenta", no_wrap=True)
    table.add_column("Cluster", style="blue", no_wrap=True)
    table.add_column("Auth Info", style="orange3", no_wrap=True)
    table.add_column("Namespace", style="yellow", no_wrap=True)
    for context in contexts:
        if name and context["name"] != name:
            continue
        table.add_row(
            "*" if context["name"] == kubeconfig.current_context else "",
            context["name"],
            context["context"]["cluster"],
            context["context"]["user"],
            context["context"].get("namespace", ""),
        )
    if name and not table.rows:
        typer.echo(f"error: context {name} not found")
        raise typer.Exit(code=1)

    console.print(table)


async def config_use_context(context: Annotated[str, typer.Argument()]):
    """Set the current-context in a kubeconfig file."""
    try:
        api = await kr8s.asyncio.api()
        await api.auth.kubeconfig.use_context(context)
    except (ValueError, KeyError):
        typer.echo(f"error: context {context} not found")
        raise typer.Exit(code=1)

    console.print(f'Switched to context "{context}".')


async def config_rename_context(
    old_name: Annotated[str, typer.Argument()],
    new_name: Annotated[str, typer.Argument()],
):
    """Renames a context from the kubeconfig file."""
    try:
        api = await kr8s.asyncio.api()
        await api.auth.kubeconfig.rename_context(old_name, new_name)
    except (ValueError, KeyError):
        typer.echo(f"error: context {old_name} not found")
        raise typer.Exit(code=1)

    console.print(f'Context "{old_name}" renamed to "{new_name}".')


register(config, config_current_context, "current-context")
register(config, config_get_clusters, "get-clusters")
register(config, config_get_users, "get-users")
register(config, config_get_contexts, "get-contexts")
register(config, config_use_context, "use-context")
register(config, config_rename_context, "rename-context")
