# SPDX-FileCopyrightText: Copyright (c) 2023, MrNaif2018, Dask Developers, NVIDIA
# SPDX-License-Identifier: MIT License
# SPDX-License-URL: https://github.com/bitcartcc/universalasync/blob/d3979113316431a24f0260804442d29a38e414a2/LICENSE
# Forked from https://github.com/bitcartcc/universalasync/tree/d3979113316431a24f0260804442d29a38e414a2
import asyncio
import functools
import inspect
from typing import Any, AsyncGenerator, Callable, Generator, Tuple

# import nest_asyncio

# nest_asyncio.apply()


def _get_event_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Useful utility for getting event loop. Acts like get_event_loop(), but also creates new event loop if needed

    This will return a working event loop in 100% of cases.

    Returns:
        asyncio.AbstractEventLoop: event loop
    """
    loop = _get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


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


def run_sync_ctx(coroutine: Any, loop: asyncio.AbstractEventLoop) -> Any:
    if inspect.isawaitable(coroutine):
        return asyncio.run(coroutine)

    if inspect.isasyncgen(coroutine):
        return iter_over_async(coroutine, lambda coro: asyncio.run(coro))


def async_to_sync_wraps(function: Callable) -> Callable:
    """Wrap an async method/property to universal method.

    This allows to run wrapped methods in both async and sync contexts transparently without any additional code

    When run from another thread, it runs coroutines in new thread's event loop

    See :ref:`Example <example>` for full example

    Args:
        function (Callable): function/property to wrap

    Returns:
        Callable: modified function
    """

    @functools.wraps(function)
    def async_to_sync_wrap(*args: Any, **kwargs: Any) -> Any:
        loop = get_event_loop()
        coroutine = function(*args, **kwargs)

        return run_sync_ctx(coroutine, loop)

    result = async_to_sync_wrap
    return result


def sync(source: object) -> object:
    """Convert all public async methods/properties of an object to universal methods.

    See :func:`async_to_sync_wraps` for more info

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
                setattr(source, name, async_to_sync_wraps(function))

        elif name == "__aenter__" and not hasattr(source, "__enter__"):
            setattr(source, "__enter__", async_to_sync_wraps(method))

        elif name == "__aexit__" and not hasattr(source, "__exit__"):
            setattr(source, "__exit__", async_to_sync_wraps(method))

    return source
