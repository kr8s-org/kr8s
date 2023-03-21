# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import uuid

from kr8s import HTTPClient, KubeConfig
from kr8s.objects import Pod


async def test_pod_create_and_delete():
    api = HTTPClient(KubeConfig.from_env())
    name = "test-" + uuid.uuid4().hex[:10]
    pod = Pod(
        api,
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
