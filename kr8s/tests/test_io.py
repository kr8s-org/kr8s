# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import anyio
import pytest
import trio

import kr8s
from kr8s._async_utils import NamedTemporaryFile
from kr8s.asyncio.objects import Pod


def test_trio_runs():
    async def main():
        api = await kr8s.asyncio.api()
        version = await api.version()
        assert "major" in version
        api_resources = await api.api_resources()
        assert api_resources

    trio.run(main)


def test_trio_pod_wait_ready(example_pod_spec):
    async def main():
        pod = await Pod(example_pod_spec)
        await pod.create()
        await pod.wait("condition=Ready")
        with pytest.raises(TimeoutError):
            await pod.wait("jsonpath='{.status.phase}'=Foo", timeout=0.1)
        await pod.wait("condition=Ready=true")
        await pod.wait("condition=Ready=True")
        await pod.wait("jsonpath='{.status.phase}'=Running")
        with pytest.raises(ValueError):
            await pod.wait("foo=NotARealCondition")
        await pod.delete()
        await pod.wait("condition=Ready=False")
        await pod.wait("delete")

    trio.run(main)


@pytest.mark.xfail(
    reason="Port forwarding is not yet implemented for trio", raises=RuntimeError
)
def test_trio_port_forward(example_pod_spec):
    async def main():
        pod = await Pod(example_pod_spec)
        await pod.create()
        await pod.wait("condition=Ready")
        async with pod.portforward(80) as port:
            assert isinstance(port, int)
        await pod.delete()

    trio.run(main)


async def test_tempfiles():
    async with NamedTemporaryFile() as f:
        assert await f.exists()
        assert isinstance(f, anyio.Path)
    assert not await f.exists()


async def test_check_output():
    output = await kr8s._async_utils.check_output("echo", "hello")
    assert output == "hello\n"

    with pytest.raises(RuntimeError, match="non-zero code"):
        await kr8s._async_utils.check_output("false")
