# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import typer

import kr8s

config = typer.Typer(
    no_args_is_help=True,
    name="config",
    help="Modify kubeconfig files.",
)


@config.command(name="current-context", help="Display the current-context")
def config_current_context():
    """Display the current context."""
    try:
        api = kr8s.api()
        typer.echo(api.auth.kubeconfig.current_context)
    except KeyError:
        typer.echo("error: current-context is not set")
