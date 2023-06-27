import pytest
import trio

import kr8s


@pytest.mark.xfail(reason="trio support is not yet implemented")
def test_trio_runs():
    async def main():
        kubernetes = await kr8s.asyncio.api()
        version = await kubernetes.version()
        assert "major" in version

    trio.run(main)
