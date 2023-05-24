# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import time

import aiohttp
import pytest

import kr8s
from kr8s._objects import get_class, object_from_spec
from kr8s.asyncio.objects import (
    APIObject,
    Deployment,
    PersistentVolume,
    Pod,
    Service,
)
from kr8s.asyncio.portforward import PortForward
from kr8s.objects import Pod as SyncPod

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(30)


@pytest.fixture
async def nginx_pod(k8s_cluster, example_pod_spec):
    example_pod_spec["metadata"]["name"] = (
        "nginx-" + example_pod_spec["metadata"]["name"]
    )
    example_pod_spec["spec"]["containers"][0]["image"] = "nginx:latest"
    example_pod_spec["spec"]["containers"][0]["ports"] = [{"containerPort": 80}]
    example_pod_spec["spec"]["containers"][0]["readinessProbe"] = {
        "httpGet": {"path": "/", "port": 80},
        "initialDelaySeconds": 0,
        "periodSeconds": 1,
        "timeoutSeconds": 1,
        "successThreshold": 2,
    }
    example_pod_spec["metadata"]["labels"]["app"] = example_pod_spec["metadata"]["name"]
    pod = await Pod(example_pod_spec)
    await pod.create()
    while not await pod.ready():
        await asyncio.sleep(0.1)
    # TODO replace with pod.exec() once implemented
    k8s_cluster.kubectl(
        "exec",
        example_pod_spec["metadata"]["name"],
        "--",
        "dd",
        "if=/dev/random",
        "of=/usr/share/nginx/html/foo.dat",
        "bs=4M",
        "count=10",
    )
    yield pod
    await pod.delete()


@pytest.fixture
async def nginx_service(example_service_spec, nginx_pod):
    example_service_spec["metadata"]["name"] = nginx_pod.name
    example_service_spec["spec"]["selector"] = nginx_pod.labels
    service = await Service(example_service_spec)
    await service.create()
    while not await service.ready():
        await asyncio.sleep(0.1)  # pragma: no cover
    yield service
    await service.delete()


async def test_pod_create_and_delete(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    with pytest.raises(NotImplementedError):
        pod.replicas
    assert await pod.exists()
    while not await pod.ready():
        await asyncio.sleep(0.1)
    await pod.delete()
    while await pod.exists():
        await asyncio.sleep(0.1)
    assert not await pod.exists()


def test_pod_create_and_delete_sync(example_pod_spec):
    pod = SyncPod(example_pod_spec)
    pod.create()
    with pytest.raises(NotImplementedError):
        pod.replicas
    assert pod.exists()
    while not pod.ready():
        time.sleep(0.1)
    pod.delete()
    while pod.exists():
        time.sleep(0.1)
    assert not pod.exists()


async def test_list_and_ensure():
    kubernetes = await kr8s.asyncio.api()
    pods = await kubernetes.get("pods", namespace=kr8s.ALL)
    assert len(pods) > 0
    for pod in pods:
        await pod.refresh()
        assert await pod.exists(ensure=True)


async def test_nonexistant():
    pod = await Pod(
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
    pod = await Pod(example_pod_spec)
    await pod.create()
    assert "name" in pod.metadata
    assert "hello" in pod.labels
    assert "foo" in pod.annotations
    assert "default" == pod.namespace
    assert "example-" in pod.name
    assert "containers" in pod.spec
    assert "phase" in pod.status
    await pod.delete()


async def test_pod_missing_labels_annotations(example_pod_spec):
    del example_pod_spec["metadata"]["labels"]
    del example_pod_spec["metadata"]["annotations"]
    pod = await Pod(example_pod_spec)
    await pod.create()
    assert not pod.labels
    assert not pod.annotations
    await pod.delete()


async def test_pod_get(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    pod2 = await Pod.get(pod.name, namespace=pod.namespace)
    assert pod2.name == pod.name
    assert pod2.namespace == pod.namespace
    await pod.delete()
    while await pod.exists():
        await asyncio.sleep(0.1)
    with pytest.raises(kr8s.NotFoundError):
        await pod2.delete()


async def test_pod_get_timeout(example_pod_spec):
    async def create_pod():
        await asyncio.sleep(0.1)
        pod = await Pod(example_pod_spec)
        await pod.create()
        return pod

    async def get_pod():
        pod = await Pod.get(
            example_pod_spec["metadata"]["name"],
            namespace=example_pod_spec["metadata"]["namespace"],
            timeout=1,
        )
        return pod

    pods = await asyncio.gather(create_pod(), get_pod())
    assert pods[0].name == pods[1].name
    await pods[0].delete()


async def test_missing_pod():
    with pytest.raises(kr8s.NotFoundError):
        await Pod.get("nonexistant", namespace="default")


async def test_selectors(example_pod_spec):
    example_pod_spec["metadata"]["labels"]["abc"] = "123def"
    pod = await Pod(example_pod_spec)
    await pod.create()

    kubernetes = await kr8s.asyncio.api()
    pods = await kubernetes.get("pods", namespace=kr8s.ALL, label_selector="abc=123def")
    assert len(pods) == 1

    pods = await kubernetes.get(
        "pods", namespace=kr8s.ALL, field_selector="metadata.name=" + pod.name
    )
    assert len(pods) == 1

    pods = await kubernetes.get(
        "pods", namespace=kr8s.ALL, field_selector="metadata.name=" + "foo-bar-baz"
    )
    assert len(pods) == 0

    await pod.delete()


async def test_pod_watch(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    async for event, obj in pod.watch():
        assert event in ("ADDED", "MODIFIED", "DELETED")
        assert obj.name == pod.name
        break
    await pod.delete()


def test_pod_watch_sync(example_pod_spec):
    pod = SyncPod(example_pod_spec)
    pod.create()
    for event, obj in pod.watch():
        assert event in ("ADDED", "MODIFIED", "DELETED")
        assert obj.name == pod.name
        break
    pod.delete()


async def test_patch_pod(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    assert "patched" not in pod.labels
    await pod.patch({"metadata": {"labels": {"patched": "true"}}})
    assert "patched" in pod.labels
    await pod.delete()


async def test_all_v1_objects_represented():
    kubernetes = await kr8s.asyncio.api()
    k8s_objects = await kubernetes.api_resources()
    supported_apis = (
        "v1",
        "apps/v1",
        "autoscaling/v2",
        "batch/v1",
        "networking.k8s.io/v1",
        "policy/v1",
        "rbac.authorization.k8s.io/v1",
        "apiextensions.k8s.io/v1",
    )
    # for supported_api in supported_apis:
    #     assert supported_api in [obj["version"] for obj in objects]
    objects = [obj for obj in k8s_objects if obj["version"] in supported_apis]
    for obj in objects:
        assert get_class(obj["kind"], obj["version"])


async def test_object_from_spec(example_pod_spec, example_service_spec):
    pod = object_from_spec(example_pod_spec)
    assert isinstance(pod, Pod)
    assert pod.name == example_pod_spec["metadata"]["name"]
    assert pod.spec == example_pod_spec["spec"]

    service = object_from_spec(example_service_spec)
    assert isinstance(service, Service)
    assert service.name == example_service_spec["metadata"]["name"]
    assert service.spec == example_service_spec["spec"]


async def test_subclass_registration():
    with pytest.raises(KeyError):
        get_class("MyResource", "foo.kr8s.org/v1alpha1")

    class MyResource(APIObject):
        version = "foo.kr8s.org/v1alpha1"
        endpoint = "myresources"
        kind = "MyResource"
        plural = "myresources"
        singular = "myresource"
        namespaced = True

    get_class("MyResource", "foo.kr8s.org/v1alpha1")


async def test_deployment_scale(example_deployment_spec):
    deployment = await Deployment(example_deployment_spec)
    await deployment.create()
    assert deployment.replicas == 1
    await deployment.scale(2)
    assert deployment.replicas == 2
    while not await deployment.ready():
        await asyncio.sleep(0.1)
    await deployment.scale(1)
    assert deployment.replicas == 1
    await deployment.delete()


async def test_node():
    kubernetes = await kr8s.asyncio.api()
    nodes = await kubernetes.get("nodes")
    assert len(nodes) > 0
    for node in nodes:
        assert node.unschedulable is False
        await node.cordon()
        assert node.unschedulable is True
        await node.uncordon()


async def test_service_proxy():
    kubernetes = await kr8s.asyncio.api()
    [service] = await kubernetes.get("services", "kubernetes")
    assert service.name == "kubernetes"
    data = await service.proxy_http_get("/version", raise_for_status=False)
    assert isinstance(data, aiohttp.ClientResponse)


async def test_pod_logs(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    while not await pod.ready():
        await asyncio.sleep(0.1)
    log = await pod.logs(container="pause")
    assert isinstance(log, str)
    await pod.delete()


async def test_pod_port_forward_context_manager(nginx_service):
    [nginx_pod, *_] = await nginx_service.ready_pods()
    async with nginx_pod.portforward(80) as port:
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.get(f"http://localhost:{port}/") as resp:
                assert resp.status == 200
            async with session.get(f"http://localhost:{port}/foo") as resp:
                assert resp.status == 404
            async with session.get(f"http://localhost:{port}/foo.dat") as resp:
                assert resp.status == 200
                await resp.read()


@pytest.mark.skip(reason="For manual testing only")
async def test_pod_port_forward_context_manager_manual(nginx_service):
    [nginx_pod, *_] = await nginx_service.ready_pods()
    pf = nginx_pod.portforward(80, 8184)
    async with pf:
        done = False
        while not done:
            # Put a breakpoint here and set done = True when you're finished.
            await asyncio.sleep(1)


async def test_pod_port_forward_start_stop(nginx_service):
    [nginx_pod, *_] = await nginx_service.ready_pods()
    pf = nginx_pod.portforward(80)
    assert pf._bg_task is None
    port = await pf.start()
    assert pf._bg_task is not None
    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        async with session.get(f"http://localhost:{port}/") as resp:
            assert resp.status == 200
        async with session.get(f"http://localhost:{port}/foo") as resp:
            assert resp.status == 404
        async with session.get(f"http://localhost:{port}/foo.dat") as resp:
            assert resp.status == 200
            await resp.read()
    await pf.stop()
    assert pf._bg_task is None


async def test_service_port_forward_context_manager(nginx_service):
    async with nginx_service.portforward(80) as port:
        async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
            async with session.get(f"http://localhost:{port}/") as resp:
                assert resp.status == 200
            async with session.get(f"http://localhost:{port}/foo") as resp:
                assert resp.status == 404


async def test_service_port_forward_start_stop(nginx_service):
    pf = nginx_service.portforward(80)
    assert pf._bg_task is None
    port = await pf.start()
    assert pf._bg_task is not None
    async with aiohttp.ClientSession(timeout=DEFAULT_TIMEOUT) as session:
        async with session.get(f"http://localhost:{port}/") as resp:
            assert resp.status == 200
        async with session.get(f"http://localhost:{port}/foo") as resp:
            assert resp.status == 404
    await pf.stop()
    assert pf._bg_task is None


async def test_unsupported_port_forward():
    pv = await PersistentVolume({})
    with pytest.raises(AttributeError):
        await pv.portforward(80)
    with pytest.raises(ValueError):
        await PortForward(pv, 80).start()
