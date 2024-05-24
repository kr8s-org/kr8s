# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License

import asyncio
from contextlib import suppress
from functools import wraps

import typer


def _typer_async(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with suppress(asyncio.CancelledError, KeyboardInterrupt):
            return asyncio.run(f(*args, **kwargs))

    return wrapper


def register(app, func, alias=None):
    if asyncio.iscoroutinefunction(func):
        func = _typer_async(func)
    if isinstance(func, typer.Typer):
        assert alias, "Typer subcommand must have an alias."
        app.add_typer(func, name=alias)
    else:
        if alias is not None:
            app.command(alias)(func)
        else:
            app.command()(func)
