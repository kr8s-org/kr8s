# SPDX-FileCopyrightText: Copyright (c) 2018 hephex
# SPDX-License-Identifier: MIT License
# Original-Source: https://github.com/hephex/asyncache/blob/35c7966101f3b0c61c9254a03fb02cca6a9b2f50/asyncache/__init__.py
"""
Helpers to use [cachetools](https://github.com/tkem/cachetools) with
asyncio.

This implementation is a fork of the original asyncache implementation by hephex
which is licensed under the included MIT License.

The original implementation became unmaintained and ran into dependency resolution issues.
Vendoring in this tiny wrapper allows us to depend on cachetools directly.
See https://github.com/kr8s-org/kr8s/issues/681 for more details.

If the cachetools package gets support for asyncio then we can remove these helpers and
use cachetools directly. See https://github.com/tkem/cachetools/issues/222 for status on this.
"""

import asyncio
import functools
from collections.abc import MutableMapping
from contextlib import AbstractContextManager
from typing import Any, Callable, Optional, Protocol, TypeVar

from cachetools import keys

__all__ = ["cached"]


_KT = TypeVar("_KT")
_T = TypeVar("_T")


class IdentityFunction(Protocol):  # pylint: disable=too-few-public-methods
    """
    Type for a function returning the same type as the one it received.
    """

    def __call__(self, __x: _T) -> _T: ...


class NullContext:
    """A class for noop context managers."""

    def __enter__(self):
        """Return ``self`` upon entering the runtime context."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Raise any exception triggered within the runtime context."""
        return None

    async def __aenter__(self):
        """Return ``self`` upon entering the runtime context."""
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Raise any exception triggered within the runtime context."""
        return None


def cached(
    cache: Optional[MutableMapping[_KT, Any]],
    # ignoring the mypy error to be consistent with the type used
    # in https://github.com/python/typeshed/tree/master/stubs/cachetools
    key: Callable[..., _KT] = keys.hashkey,  # type:ignore
    lock: Optional["AbstractContextManager[Any]"] = None,
) -> IdentityFunction:
    """
    Decorator to wrap a function or a coroutine with a memoizing callable
    that saves results in a cache.

    When ``lock`` is provided for a standard function, it's expected to
    implement ``__enter__`` and ``__exit__`` that will be used to lock
    the cache when gets updated. If it wraps a coroutine, ``lock``
    must implement ``__aenter__`` and ``__aexit__``.
    """
    lock = lock or NullContext()

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            async def wrapper(*args, **kwargs):
                k = key(*args, **kwargs)
                try:
                    async with lock:
                        return cache[k]

                except KeyError:
                    pass  # key not found

                val = await func(*args, **kwargs)

                try:
                    async with lock:
                        cache[k] = val

                except ValueError:
                    pass  # val too large

                return val

        else:

            def wrapper(*args, **kwargs):
                k = key(*args, **kwargs)
                try:
                    with lock:
                        return cache[k]

                except KeyError:
                    pass  # key not found

                val = func(*args, **kwargs)

                try:
                    with lock:
                        cache[k] = val

                except ValueError:
                    pass  # val too large

                return val

        return functools.wraps(func)(wrapper)

    return decorator


def cachedmethod(
    cache: Callable[[Any], Optional[MutableMapping[_KT, Any]]],
    # ignoring the mypy error to be consistent with the type used
    # in https://github.com/python/typeshed/tree/master/stubs/cachetools
    key: Callable[..., _KT] = keys.hashkey,  # type:ignore
    lock: Optional[Callable[[Any], "AbstractContextManager[Any]"]] = None,
) -> IdentityFunction:
    """Decorator to wrap a class or instance method with a memoizing
    callable that saves results in a cache. This works similarly to
    `cached`, but the arguments `cache` and `lock` are callables that
    return the cache object and the lock respectively.
    """
    lock = lock or (lambda _: NullContext())

    def decorator(method):
        if asyncio.iscoroutinefunction(method):

            async def wrapper(self, *args, **kwargs):
                method_cache = cache(self)
                if method_cache is None:
                    return await method(self, *args, **kwargs)

                k = key(self, *args, **kwargs)
                try:
                    async with lock(self):
                        return method_cache[k]

                except KeyError:
                    pass  # key not found

                val = await method(self, *args, **kwargs)

                try:
                    async with lock(self):
                        method_cache[k] = val

                except ValueError:
                    pass  # val too large

                return val

        else:

            def wrapper(self, *args, **kwargs):
                method_cache = cache(self)
                if method_cache is None:
                    return method(self, *args, **kwargs)

                k = key(*args, **kwargs)
                try:
                    with lock(self):
                        return method_cache[k]

                except KeyError:
                    pass  # key not found

                val = method(self, *args, **kwargs)

                try:
                    with lock(self):
                        method_cache[k] = val

                except ValueError:
                    pass  # val too large

                return val

        return functools.wraps(method)(wrapper)

    return decorator
