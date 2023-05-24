# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio

import pytest

import kr8s
import kr8s.asyncio
from kr8s.asyncio.objects import Pod, Table


async def test_factory_bypass():
    with pytest.raises(ValueError, match="kr8s.api()"):
        _ = kr8s.Api()
    assert not kr8s.Api._instances
    _ = kr8s.api()
    assert kr8s.Api._instances


async def test_api_factory(serviceaccount):
    k1 = await kr8s.asyncio.api()
    k2 = await kr8s.asyncio.api()
    assert k1 is k2

    k3 = await kr8s.asyncio.api(serviceaccount=serviceaccount)
    k4 = await kr8s.asyncio.api(serviceaccount=serviceaccount)
    assert k1 is not k3
    assert k3 is k4

    p = await Pod({})
    assert p.api is k1
    assert p.api is not k3


async def test_api_factory_with_kubeconfig(k8s_cluster, serviceaccount):
    k1 = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    k2 = await kr8s.asyncio.api(serviceaccount=serviceaccount)
    k3 = await kr8s.asyncio.api()
    assert k1 is not k2
    assert k3 is k1
    assert k3 is not k2

    p = await Pod({})
    assert p.api is k1

    p2 = await Pod({}, api=k2)
    assert p2.api is k2

    p3 = await Pod({}, api=k3)
    assert p3.api is k3
    assert p3.api is not k2


def test_version_sync():
    kubernetes = kr8s.api()
    version = kubernetes.version()
    assert "major" in version


async def test_version_sync_in_async():
    kubernetes = kr8s.api()
    version = kubernetes.version()
    assert "major" in version


async def test_version():
    kubernetes = await kr8s.asyncio.api()
    version = await kubernetes.version()
    assert "major" in version


async def test_concurrent_api_creation():
    async def get_api():
        api = await kr8s.asyncio.api()
        await api.version()
        return api

    apis = await asyncio.gather(*[get_api() for _ in range(10)])
    assert len(set(apis)) == 1


async def test_bad_api_version():
    kubernetes = await kr8s.asyncio.api()
    with pytest.raises(ValueError):
        async with kubernetes.call_api("GET", version="foo"):
            pass  # pragma: no cover


@pytest.mark.parametrize("namespace", [kr8s.ALL, "kube-system"])
async def test_get_pods(namespace):
    kubernetes = await kr8s.asyncio.api()
    pods = await kubernetes.get("pods", namespace=namespace)
    assert isinstance(pods, list)
    assert len(pods) > 0
    assert isinstance(pods[0], Pod)


async def test_get_pods_as_table():
    kubernetes = await kr8s.asyncio.api()
    pods = await kubernetes.get("pods", namespace="kube-system", as_object=Table)
    assert isinstance(pods, Table)
    assert len(pods.rows) > 0


async def test_watch_pods(example_pod_spec):
    kubernetes = await kr8s.asyncio.api()
    pod = await Pod(example_pod_spec)
    await pod.create()
    while not await pod.ready():
        await asyncio.sleep(0.1)
    async for event, obj in kubernetes.watch("pods"):
        assert event in ["ADDED", "MODIFIED", "DELETED"]
        assert isinstance(obj, Pod)
        if obj.name == pod.name:
            if event == "ADDED":
                await obj.patch({"metadata": {"labels": {"test": "test"}}})
            elif event == "MODIFIED" and "test" in obj.labels and await obj.exists():
                await obj.delete()
                while await obj.exists():
                    await asyncio.sleep(0.1)
            elif event == "DELETED":
                break


async def test_get_deployments():
    kubernetes = await kr8s.asyncio.api()
    deployments = await kubernetes.get("deployments")
    assert isinstance(deployments, list)


async def test_api_resources():
    kubernetes = await kr8s.asyncio.api()
    resources = await kubernetes.api_resources()

    names = [r["name"] for r in resources]
    assert "nodes" in names
    assert "pods" in names
    assert "services" in names
    assert "namespaces" in names

    [pods] = [r for r in resources if r["name"] == "pods"]
    assert pods["namespaced"]
    assert pods["kind"] == "Pod"
    assert pods["version"] == "v1"
    assert "get" in pods["verbs"]

    [deployment] = [d for d in resources if d["name"] == "deployments"]
    assert deployment["namespaced"]
    assert deployment["kind"] == "Deployment"
    assert deployment["version"] == "apps/v1"
    assert "get" in deployment["verbs"]
    assert "deploy" in deployment["shortNames"]
