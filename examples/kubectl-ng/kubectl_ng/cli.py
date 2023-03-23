# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
from functools import wraps
from typing import List

import typer

from kr8s import HTTPClient, KubeConfig
from kr8s.objects import Pod

from ._get import get


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
register(app, get)


def go():
    app()


if __name__ == "__main__":
    go()
