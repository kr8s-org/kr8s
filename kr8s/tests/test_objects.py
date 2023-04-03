# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import uuid

import pytest

import kr8s
from kr8s.objects import Pod


async def test_pod_create_and_delete():
    name = "test-" + uuid.uuid4().hex[:10]
    pod = Pod(
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": name},
            "spec": {
                "containers": [
                    {"name": "pause", "image": "gcr.io/google_containers/pause"}
                ]
            },
        },
    )

    await pod.create()
    assert await pod.exists()
    await pod.delete()
    while await pod.exists():
        await asyncio.sleep(0.1)
    assert not await pod.exists()


async def test_list_and_ensure():
    kubernetes = kr8s.Kr8sApi()
    pods = await kubernetes.get("pods", namespace=kr8s.ALL)
    assert len(pods) > 0
    for pod in pods:
        assert await pod.exists(ensure=True)


async def test_nonexistant():
    pod = Pod(
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": "nonexistant",
                "namespace": "nonexistant",
            },
        }
    )
    assert not await pod.exists()
    with pytest.raises(kr8s.NotFoundError):
        await pod.exists(ensure=True)
