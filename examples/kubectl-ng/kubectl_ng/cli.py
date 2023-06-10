# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
from functools import wraps

import typer

from ._api_resources import api_resources
from ._get import get
from ._version import version
from ._wait import wait


def _typer_async(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def register(app, func):
    if asyncio.iscoroutinefunction(func):
        func = _typer_async(func)
    app.command()(func)


app = typer.Typer()
register(app, api_resources)
register(app, get)
register(app, version)
register(app, wait)


def go():
    app()


if __name__ == "__main__":
    go()
