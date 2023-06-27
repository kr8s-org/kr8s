from kr8s._asyncio import NamedTemporaryFile


async def test_tempfiles():
    async with NamedTemporaryFile() as f:
        assert await f.exists()
    assert not await f.exists()
