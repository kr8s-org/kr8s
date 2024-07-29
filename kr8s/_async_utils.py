# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
#
# Utilities for running async code in a sync context. This is how kr8s is able to provide a sync API.
#
# The sync API in kr8s needs to wrap all async functions in a way that allows them to be run in a sync context.
# However, the sync API may be used within an async context, so we need to be able to run async code nested in
# a sync context that is itself nested in an async context. This is a bit of a tricky problem, but it can be
# solved by running the nested async code in a separate thread.
#
# This file was originally based on universalasync (commit d397911) and jupyter-core (commit 98b9a1a).
# Both projects attempt to solve the same problem: how to run nested async tasks.
# Neither solution quite fit in here, so we forked them and combined them. Things have evolved a lot
# since then, but the licenses and links are included here for historical reasons.
#
# universalasync License: https://github.com/bitcartcc/universalasync/blob/d397911/LICENSE
# jupyter-core License: https://github.com/jupyter/jupyter_core/blob/98b9a1a/COPYING.md
#
# This implementation now uses anyio to simplify dispatching to a loop in a thread using either
# asyncio or trio.
from __future__ import annotations

import inspect
import subprocess
import sys
import tempfile
from contextlib import asynccontextmanager
from functools import partial, wraps
from threading import Thread
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    TypeVar,
)

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

import anyio
import anyio.from_thread
import anyio.to_thread

T = TypeVar("T")
C = TypeVar("C")
P = ParamSpec("P")


class Portal:
    """A class that manages a thread running an anyio loop.

    This class is a singleton that manages a thread running an anyio loop and provides
    an anyio portal to communicate with the loop from a sync context.

    See https://anyio.readthedocs.io/en/stable/api.html#anyio.from_thread.start_blocking_portal for more info.

    It's important to start the loop in a separate thread because the sync code may be
    running in a context where an event loop is already running, and we can't run two
    event loops in the same thread. This commonly happens when running in IPython, a Jupyter
    notebook or when running async tests with pytest.

    """

    _instance: Portal
    _portal: anyio.from_thread.BlockingPortal
    thread: Thread

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
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

    def call(self, func: Callable[P, Awaitable[T]], *args, **kwargs) -> T:
        """Call a coroutine in the runner loop and return the result."""
        # On first call the thread has to start the loop, so we need to wait for it
        while not hasattr(self, "_portal"):
            pass
        return self._portal.call(func, *args, **kwargs)


def run_sync(
    coro: Callable[P, AsyncGenerator | Awaitable[T]]
) -> Callable[P, Generator | T]:
    """Wraps a coroutine in a function that blocks until it has executed.

    Args:
        coro (Awaitable): A coroutine.

    Returns:
        Callable: A sync function that executes the coroutine via the :class`Portal`.
    """
    if inspect.isasyncgenfunction(coro):

        @wraps(coro)
        def run_gen_inner(*args: P.args, **kwargs: P.kwargs) -> Generator:
            wrapped = partial(coro, *args, **kwargs)
            return iter_over_async(wrapped())

        return run_gen_inner

    if inspect.iscoroutinefunction(coro):

        @wraps(coro)
        def run_sync_inner(*args: P.args, **kwargs: P.kwargs) -> T:
            wrapped = partial(coro, *args, **kwargs)
            portal = Portal()
            return portal.call(wrapped)

        return run_sync_inner

    raise TypeError(f"Expected coroutine function, got {coro.__class__.__name__}")


def iter_over_async(agen: AsyncGenerator) -> Generator:
    """Convert an async generator to a sync generator.

    Args:
        agen (AsyncGenerator): async generator to convert

    Yields:
        Any: object from async generator
    """
    ait = agen.__aiter__()

    async def get_next() -> tuple[bool, Any]:
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


def sync(source: C) -> C:
    """Convert all public async methods/properties of an object to universal methods.

    Private methods or methods starting with "async_" are ignored.
    See :func:`run_sync` for more info on how the conversion works.

    Args:
        source (C): object with coroutines to convert

    Returns:
        C: converted object with sync methods

    Examples:
        It's common to implement a coroutine and name it with async_ and then wrap that
        in another corotine that calls it. That way the method can be called from both
        sync and async contexts as function allows you to convert the outer coroutine
        to a sync method. But other async methods or other async objects can call the
        inner coroutine directly.

        >>> class Foo:
        ...     async def async_bar(self):
        ...         return 42
        ...     async def bar(self):
        ...         return await self.async_bar()
        ...     async def baz(self):
        ...         # If you want to calll self.bar() from another async method
        ...         # you can't when it gets wrapped with sync, so you can call
        ...         # self.async_bar() directly instead.
        ...         return (await self.async_bar()) + 1
        ...
        >>> SyncFoo = sync(Foo)
        >>> inst = SyncFoo()
        >>> inst.bar()
        42
        >>> inst.async_bar()
        <coroutine object Foo.async_bar at 0x7fbe0442b940>
        >>> inst.baz()
        43

    """
    setattr(source, "_asyncio", False)  # noqa: B010
    for name in dir(source):
        method = getattr(source, name)

        if not name.startswith("_") and not name.startswith("async_"):
            if inspect.iscoroutinefunction(method) or inspect.isasyncgenfunction(
                method
            ):
                function = getattr(source, name)
                setattr(source, name, run_sync(function))

        elif name == "__aenter__" and not hasattr(source, "__enter__"):
            setattr(source, "__enter__", run_sync(method))  # noqa: B010

        elif name == "__aexit__" and not hasattr(source, "__exit__"):
            setattr(source, "__exit__", run_sync(method))  # noqa: B010

    return source


async def check_output(*args, **kwargs) -> str:
    """Run a command and return its output."""
    completed_process = await anyio.run_process(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        **kwargs,
    )
    if completed_process.returncode == 0:
        return completed_process.stdout.decode()
    else:
        raise RuntimeError(
            f"Process exited with non-zero code {completed_process.returncode}:\n{completed_process.stderr.decode()}"
        )


@asynccontextmanager
async def NamedTemporaryFile(  # noqa: N802
    *args, delete: bool = True, **kwargs
) -> AsyncGenerator[anyio.Path]:
    """Create a temporary file that is deleted when the context exits."""
    kwargs.update(delete=False)

    def f():
        return tempfile.NamedTemporaryFile(*args, **kwargs)

    tmp = await anyio.to_thread.run_sync(f)
    fh = anyio.Path(tmp.name)
    yield fh
    if delete:
        await fh.unlink()
