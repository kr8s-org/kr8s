# SPDX-FileCopyrightText: Copyright (c) 2018 hephex
# SPDX-License-Identifier: MIT License
# Original-Source: https://github.com/hephex/asyncache/blob/35c7966101f3b0c61c9254a03fb02cca6a9b2f50/asyncache/tests/test_asyncache_cachedmethod.py
import operator
import unittest

from cachetools import LRUCache, keys

from kr8s._vendored.asyncache import cachedmethod


class Cached:
    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

    @cachedmethod(operator.attrgetter("cache"))
    def get(self, value):
        count = self.count
        self.count += 1
        return count

    @cachedmethod(operator.attrgetter("cache"), key=keys.typedkey)
    def get_typed(self, value):
        count = self.count
        self.count += 1
        return count


class Locked:
    def __init__(self, cache):
        self.cache = cache
        self.count = 0

    @cachedmethod(operator.attrgetter("cache"), lock=lambda self: self)
    def get(self, value):
        return self.count

    def __enter__(self):
        self.count += 1

    def __exit__(self, *exc):
        pass


class AsyncCached:
    def __init__(self, cache, count=0):
        self.cache = cache
        self.count = count

    @cachedmethod(operator.attrgetter("cache"))
    async def get(self, value):
        count = self.count
        self.count += 1
        return count

    @cachedmethod(operator.attrgetter("cache"), key=keys.typedkey)
    async def get_typed(self, value):
        count = self.count
        self.count += 1
        return count


class AsyncLocked:
    def __init__(self, cache):
        self.cache = cache
        self.count = 0

    @cachedmethod(operator.attrgetter("cache"), lock=lambda self: self)
    async def get(self, value):
        return self.count

    async def __aenter__(self):
        self.count += 1

    async def __aexit__(self, *exc):
        pass


class CachedMethodTestSync(unittest.TestCase):
    def test_dict(self):
        cached = Cached({})

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_typed_dict(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)
        self.assertEqual(cached.get_typed(0), 4)

    def test_lru(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1.0), 1)
        self.assertEqual(cached.get(1.0), 1)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 2)

    def test_typed_lru(self):
        cached = Cached(LRUCache(maxsize=2))

        self.assertEqual(cached.get_typed(0), 0)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1), 1)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(1.0), 2)
        self.assertEqual(cached.get_typed(0.0), 3)
        self.assertEqual(cached.get_typed(0), 4)

    def test_nospace(self):
        cached = Cached(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(1.0), 4)

    def test_nocache(self):
        cached = Cached(None)

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 1)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(1.0), 4)

    def test_weakref(self):
        import fractions
        import gc
        import weakref

        # in Python 3.7, `int` does not support weak references even
        # when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):
                return Int(fractions.Fraction.__add__(self, other))

        cached = Cached(weakref.WeakValueDictionary(), count=Int(0))

        self.assertEqual(cached.get(0), 0)
        gc.collect()
        self.assertEqual(cached.get(0), 1)

        ref = cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual(cached.get(1), 2)
        self.assertEqual(cached.get(1.0), 2)

        ref = cached.get_typed(1)
        self.assertEqual(ref, 3)
        self.assertEqual(cached.get_typed(1), 3)
        self.assertEqual(cached.get_typed(1.0), 4)

        cached.cache.clear()
        self.assertEqual(cached.get(1), 5)

    def test_locked_dict(self):
        cached = Locked({})

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.get(1.0), 3)
        self.assertEqual(cached.get(2.0), 7)

    def test_locked_nocache(self):
        cached = Locked(None)

        self.assertEqual(cached.get(0), 0)
        self.assertEqual(cached.get(1), 0)
        self.assertEqual(cached.get(1), 0)
        self.assertEqual(cached.get(1.0), 0)
        self.assertEqual(cached.get(1.0), 0)

    def test_locked_nospace(self):
        cached = Locked(LRUCache(maxsize=0))

        self.assertEqual(cached.get(0), 1)
        self.assertEqual(cached.get(1), 3)
        self.assertEqual(cached.get(1), 5)
        self.assertEqual(cached.get(1.0), 7)
        self.assertEqual(cached.get(1.0), 9)

    def test_wrapped(self):
        cache = {}
        cached = Cached(cache)

        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.get.__wrapped__(cached, 0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(cached.get(0), 1)
        self.assertEqual(len(cache), 1)


class CachedMethodTestAsync(unittest.IsolatedAsyncioTestCase):
    async def test_dict(self):
        cached = AsyncCached({})

        self.assertEqual((await cached.get(0)), 0)
        self.assertEqual((await cached.get(1)), 1)
        self.assertEqual((await cached.get(1)), 1)
        self.assertEqual((await cached.get(1.0)), 1)
        self.assertEqual((await cached.get(1.0)), 1)

        cached.cache.clear()
        self.assertEqual((await cached.get(1)), 2)

    async def test_typed_dict(self):
        cached = AsyncCached(LRUCache(maxsize=2))

        self.assertEqual((await cached.get_typed(0)), 0)
        self.assertEqual((await cached.get_typed(1)), 1)
        self.assertEqual((await cached.get_typed(1)), 1)
        self.assertEqual((await cached.get_typed(1.0)), 2)
        self.assertEqual((await cached.get_typed(1.0)), 2)
        self.assertEqual((await cached.get_typed(0.0)), 3)
        self.assertEqual((await cached.get_typed(0)), 4)

    async def test_lru(self):
        cached = AsyncCached(LRUCache(maxsize=2))

        self.assertEqual((await cached.get(0)), 0)
        self.assertEqual((await cached.get(1)), 1)
        self.assertEqual((await cached.get(1)), 1)
        self.assertEqual((await cached.get(1.0)), 1)
        self.assertEqual((await cached.get(1.0)), 1)

        cached.cache.clear()
        self.assertEqual((await cached.get(1)), 2)

    async def test_typed_lru(self):
        cached = AsyncCached(LRUCache(maxsize=2))

        self.assertEqual((await cached.get_typed(0)), 0)
        self.assertEqual((await cached.get_typed(1)), 1)
        self.assertEqual((await cached.get_typed(1)), 1)
        self.assertEqual((await cached.get_typed(1.0)), 2)
        self.assertEqual((await cached.get_typed(1.0)), 2)
        self.assertEqual((await cached.get_typed(0.0)), 3)
        self.assertEqual((await cached.get_typed(0)), 4)

    async def test_nospace(self):
        cached = AsyncCached(LRUCache(maxsize=0))

        self.assertEqual((await cached.get(0)), 0)
        self.assertEqual((await cached.get(1)), 1)
        self.assertEqual((await cached.get(1)), 2)
        self.assertEqual((await cached.get(1.0)), 3)
        self.assertEqual((await cached.get(1.0)), 4)

    async def test_nocache(self):
        cached = AsyncCached(None)

        self.assertEqual((await cached.get(0)), 0)
        self.assertEqual((await cached.get(1)), 1)
        self.assertEqual((await cached.get(1)), 2)
        self.assertEqual((await cached.get(1.0)), 3)
        self.assertEqual((await cached.get(1.0)), 4)

    async def test_weakref(self):
        import fractions
        import gc
        import weakref

        # in Python 3.7, `int` does not support weak references even
        # when subclassed, but Fraction apparently does...
        class Int(fractions.Fraction):
            def __add__(self, other):
                return Int(fractions.Fraction.__add__(self, other))

        cached = AsyncCached(weakref.WeakValueDictionary(), count=Int(0))

        self.assertEqual((await cached.get(0)), 0)
        gc.collect()
        self.assertEqual((await cached.get(0)), 1)

        ref = await cached.get(1)
        self.assertEqual(ref, 2)
        self.assertEqual((await cached.get(1)), 2)
        self.assertEqual((await cached.get(1.0)), 2)

        ref = await cached.get_typed(1)
        self.assertEqual(ref, 3)
        self.assertEqual((await cached.get_typed(1)), 3)
        self.assertEqual((await cached.get_typed(1.0)), 4)

        cached.cache.clear()
        self.assertEqual((await cached.get(1)), 5)

    async def test_locked_dict(self):
        cached = AsyncLocked({})

        self.assertEqual((await cached.get(0)), 1)
        self.assertEqual((await cached.get(1)), 3)
        self.assertEqual((await cached.get(1)), 3)
        self.assertEqual((await cached.get(1.0)), 3)
        self.assertEqual((await cached.get(2.0)), 7)

    async def test_locked_nocache(self):
        cached = AsyncLocked(None)

        self.assertEqual((await cached.get(0)), 0)
        self.assertEqual((await cached.get(1)), 0)
        self.assertEqual((await cached.get(1)), 0)
        self.assertEqual((await cached.get(1.0)), 0)
        self.assertEqual((await cached.get(1.0)), 0)

    async def test_locked_nospace(self):
        cached = AsyncLocked(LRUCache(maxsize=0))

        self.assertEqual((await cached.get(0)), 1)
        self.assertEqual((await cached.get(1)), 3)
        self.assertEqual((await cached.get(1)), 5)
        self.assertEqual((await cached.get(1.0)), 7)
        self.assertEqual((await cached.get(1.0)), 9)

    async def test_wrapped(self):
        cache = {}
        cached = AsyncCached(cache)

        self.assertEqual(len(cache), 0)
        self.assertEqual(await cached.get.__wrapped__(cached, 0), 0)
        self.assertEqual(len(cache), 0)
        self.assertEqual(await cached.get(0), 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(await cached.get(0), 1)
        self.assertEqual(len(cache), 1)
