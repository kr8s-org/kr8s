# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import uuid

import pytest

import kr8s
from kr8s.objects import OBJECT_REGISTRY, APIObject, Pod


@pytest.fixture
async def example_pod_spec():
    name = "example-" + uuid.uuid4().hex[:10]
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": name,
            "labels": {"hello": "world"},
            "annotations": {"foo": "bar"},
        },
        "spec": {
            "containers": [{"name": "pause", "image": "gcr.io/google_containers/pause"}]
        },
    }


async def test_pod_create_and_delete(example_pod_spec):
    pod = Pod(example_pod_spec)
    await pod.create()
    assert await pod.exists()
    while not await pod.ready():
        await asyncio.sleep(0.1)
    await pod.delete()
    while await pod.exists():
        await asyncio.sleep(0.1)
    assert not await pod.exists()


async def test_list_and_ensure():
    kubernetes = kr8s.Kr8sApi()
    pods = await kubernetes.get("pods", namespace=kr8s.ALL)
    assert len(pods) > 0
    for pod in pods:
        await pod.refresh()
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


async def test_pod_metadata(example_pod_spec):
    pod = Pod(example_pod_spec)
    await pod.create()
    assert "name" in pod.metadata
    assert "hello" in pod.labels
    assert "foo" in pod.annotations
    assert "default" == pod.namespace
    assert "example-" in pod.name
    assert "containers" in pod.spec
    assert "phase" in pod.status


async def test_patch_pod(example_pod_spec):
    pod = Pod(example_pod_spec)
    await pod.create()
    assert "patched" not in pod.labels
    await pod.patch({"metadata": {"labels": {"patched": "true"}}})
    assert "patched" in pod.labels


async def test_all_v1_objects_represented():
    kubernetes = kr8s.Kr8sApi()
    objects = await kubernetes.api_resources()
    objects = [
        obj
        for obj in objects
        if obj["version"] in ("v1", "apps/v1", "autoscaling/v2", "batch/v1")
    ]
    for obj in objects:
        assert issubclass(OBJECT_REGISTRY.get(obj["kind"], obj["version"]), APIObject)
