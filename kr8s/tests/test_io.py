# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import anyio
import pytest
import trio

import kr8s
from kr8s._io import NamedTemporaryFile


@pytest.mark.xfail(reason="trio support is not yet implemented")
def test_trio_runs():
    async def main():
        kubernetes = await kr8s.asyncio.api()
        version = await kubernetes.version()
        assert "major" in version

    trio.run(main)


async def test_tempfiles():
    async with NamedTemporaryFile() as f:
        assert await f.exists()
        assert isinstance(f, anyio.Path)
    assert not await f.exists()


async def test_anyio_sync_in_async():
    def foo():
        async def bar():
            return "hello"

        try:
            return anyio.run(bar)
        except RuntimeError:
            with anyio.from_thread.start_blocking_portal() as portal:
                return portal.call(bar)

    assert await anyio.to_thread.run_sync(foo) == "hello"
    assert foo() == "hello"


def test_anyio_sync_in_sync():
    def foo():
        async def bar():
            return "hello"

        try:
            return anyio.run(bar)
        except RuntimeError:
            with anyio.from_thread.start_blocking_portal() as portal:
                return portal.call(bar)

    assert foo() == "hello"


def test_anyio_awaitable():
    async def main():
        pass

    anyio.run(main)
