# SPDX-FileCopyrightText: Copyright (c) 2023, Jupyter Development Team., MrNaif2018, Dask Developers, NVIDIA
# SPDX-License-Identifier: MIT License, BSD 3-Clause License
#
# This file contains a fork of universalasync (commit d397911) and jupyter-core (commit 98b9a1a).
# Both projects attempt to solve the same problem: how to run nested asyncio tasks.
# Neither solution quite fit in here, so we forked them and combined them.
#
# universalasync License: https://github.com/bitcartcc/universalasync/blob/d397911/LICENSE
# jupyter-core License: https://github.com/jupyter/jupyter_core/blob/98b9a1a/COPYING.md
#
# This implementation uses the _TaskRunner from jupyter-core, but with a modified version of the wraps
# decorator from universalasync.

import asyncio
import atexit
import inspect
import threading
from functools import wraps
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    Optional,
    Tuple,
    TypeVar,
)

T = TypeVar("T")


class _TaskRunner:
    """A task runner that runs an asyncio event loop on a background thread."""

    def __init__(self):
        self.__io_loop: Optional[asyncio.AbstractEventLoop] = None
        self.__runner_thread: Optional[threading.Thread] = None
        self.__lock = threading.Lock()
        atexit.register(self._close)

    def _close(self) -> None:
        if self.__io_loop:
            self.__io_loop.stop()

    def _runner(self) -> None:
        loop = self.__io_loop
        assert loop is not None  # noqa
        try:
            loop.run_forever()
        finally:
            loop.close()

    def run(self, coro: Awaitable[T]) -> T:
        """Synchronously run a coroutine on a background thread."""
        with self.__lock:
            name = f"{threading.current_thread().name} - runner"
            if self.__io_loop is None:
                self.__io_loop = asyncio.new_event_loop()
                self.__runner_thread = threading.Thread(
                    target=self._runner, daemon=True, name=name
                )
                self.__runner_thread.start()
        fut = asyncio.run_coroutine_threadsafe(coro, self.__io_loop)
        return fut.result(None)


_runner_map = {}


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
        name = threading.current_thread().name
        inner = coro(*args, **kwargs)
        try:
            # If a loop is currently running use a task runner to
            # run in a new loop in a separate thread.
            asyncio.get_running_loop()
            if name not in _runner_map:
                _runner_map[name] = _TaskRunner()
            handler = _runner_map[name].run
        except RuntimeError:
            # Otherwise just run in a new loop.
            handler = asyncio.run

        if inspect.isawaitable(inner):
            return handler(inner)
        if inspect.isasyncgen(inner):
            return iter_over_async(inner, lambda inner: handler(inner))

    wrapped.__doc__ = coro.__doc__
    return wrapped


def iter_over_async(agen: AsyncGenerator, run_func: Callable) -> Generator:
    ait = agen.__aiter__()

    async def get_next() -> Tuple[bool, Any]:
        try:
            obj = await ait.__anext__()
            return False, obj
        except StopAsyncIteration:
            return True, None

    while True:
        done, obj = run_func(get_next())
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
