# SPDX-FileCopyrightText: Copyright (c) 2023, Jupyter Development Team., MrNaif2018, Dask Developers, NVIDIA
# SPDX-License-Identifier: MIT License, BSD 3-Clause License
#
# This file was originally based on universalasync (commit d397911) and jupyter-core (commit 98b9a1a).
# Both projects attempt to solve the same problem: how to run nested async tasks.
# Neither solution quite fit in here, so we forked them and combined them.
#
# universalasync License: https://github.com/bitcartcc/universalasync/blob/d397911/LICENSE
# jupyter-core License: https://github.com/jupyter/jupyter_core/blob/98b9a1a/COPYING.md
#
# This implementation now uses anyio to simplify dispatching to a loop in a thread using either
# asyncio or trio.
from __future__ import annotations

import asyncio
import inspect
import tempfile
from contextlib import asynccontextmanager
from functools import partial, wraps
from threading import Thread
from typing import Any, AsyncGenerator, Awaitable, Callable, Generator, Tuple, TypeVar

import anyio

T = TypeVar("T")


class Portal:
    _instance = None
    _portal = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Portal, cls).__new__(cls)
            cls._instance.thread = Thread(
                target=anyio.run, args=[cls._instance._run], name="Kr8sSyncRunnerThread"
            )
            cls._instance.thread.daemon = True
            cls._instance.thread.start()
        return cls._instance

    async def _run(self):
        async with anyio.from_thread.BlockingPortal() as portal:
            self._portal = portal
            await portal.sleep_until_stopped()

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        while not self._portal:
            pass
        return self._portal.call(func, *args, **kwargs)


def run_sync(coro: Callable[..., Awaitable[T]]) -> Callable[..., T]:
    """Wraps coroutine in a function that blocks until it has executed.

    Parameters
    ----------
    coro : coroutine-function
        The coroutine-function to be executed.

    Returns
    -------
    result :
        Whatever the coroutine-function returns.
    """

    @wraps(coro)
    def wrapped(*args, **kwargs):
        wrapped = partial(coro, *args, **kwargs)
        wrapped.__doc__ = coro.__doc__
        if inspect.isasyncgenfunction(coro):
            return iter_over_async(wrapped)
        portal = Portal()
        if inspect.iscoroutinefunction(coro):
            return portal.call(wrapped)
        raise TypeError(f"Expected coroutine function, got {coro.__class__.__name__}")

    wrapped.__doc__ = coro.__doc__
    return wrapped


def iter_over_async(agen: AsyncGenerator) -> Generator:
    ait = agen().__aiter__()

    async def get_next() -> Tuple[bool, Any]:
        try:
            obj = await ait.__anext__()
            return False, obj
        except StopAsyncIteration:
            return True, None

    portal = Portal()
    while True:
        done, obj = portal.call(get_next)
        if done:
            break
        yield obj


def sync(source: object) -> object:
    """Convert all public async methods/properties of an object to universal methods.

    See :func:`run_sync` for more info

    Args:
        source (object): object to convert

    Returns:
        object: converted object. Note that parameter passed is being modified anyway
    """
    setattr(source, "_asyncio", False)
    for name in dir(source):
        method = getattr(source, name)

        if not name.startswith("_"):
            if inspect.iscoroutinefunction(method) or inspect.isasyncgenfunction(
                method
            ):
                function = getattr(source, name)
                setattr(source, name, run_sync(function))

        elif name == "__aenter__" and not hasattr(source, "__enter__"):
            setattr(source, "__enter__", run_sync(method))

        elif name == "__aexit__" and not hasattr(source, "__exit__"):
            setattr(source, "__exit__", run_sync(method))

    return source


async def check_output(*args, **kwargs) -> str:
    """Run a command and return its output."""
    p = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **kwargs,
    )
    stdout_data, stderr_data = await p.communicate()
    if p.returncode == 0:
        return stdout_data.decode()
    else:
        raise RuntimeError(
            f"Process exited with non-zero code {p.returncode}:\n{stderr_data.decode()}"
        )


@asynccontextmanager
async def NamedTemporaryFile(
    *args, delete: bool = True, **kwargs
) -> AsyncGenerator[anyio.Path, None]:
    """Create a temporary file that is deleted when the context exits."""
    kwargs.update(delete=False)

    def f() -> tempfile.NamedTemporaryFile:
        return tempfile.NamedTemporaryFile(*args, **kwargs)

    tmp = await anyio.to_thread.run_sync(f)
    fh = anyio.Path(tmp.name)
    yield fh
    if delete:
        await fh.unlink()
