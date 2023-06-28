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
