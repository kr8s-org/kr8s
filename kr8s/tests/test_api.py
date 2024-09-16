# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import queue
import threading

import anyio
import pytest

import kr8s
import kr8s.asyncio
from kr8s._exceptions import APITimeoutError
from kr8s.asyncio.objects import Pod, Table


async def test_factory_bypass() -> None:
    with pytest.raises(ValueError, match="kr8s.api()"):
        _ = kr8s.Api()
    assert not kr8s.Api._instances
    _ = kr8s.api()
    assert kr8s.Api._instances


async def test_api_factory(serviceaccount) -> None:
    k1 = await kr8s.asyncio.api()
    k2 = await kr8s.asyncio.api()
    assert k1 is k2

    k3 = await kr8s.asyncio.api(serviceaccount=serviceaccount)
    k4 = await kr8s.asyncio.api(serviceaccount=serviceaccount)
    assert k1 is not k3
    assert k3 is k4

    p = await Pod({"metadata": {"name": "foo"}})
    assert p.api is k1
    assert p.api is not k3


def test_api_factory_threaded():
    assert len(kr8s.Api._instances) == 0

    q = queue.Queue()

    def run_in_thread(q):
        async def create_api(q):
            k = await kr8s.asyncio.api()
            q.put(k)

        anyio.run(create_api, q)

    t1 = threading.Thread(
        target=run_in_thread,
        args=(q,),
    )
    t2 = threading.Thread(
        target=run_in_thread,
        args=(q,),
    )
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    k1 = q.get()
    k2 = q.get()

    assert k1 is not k2
    assert type(k1) is type(k2)


def test_api_factory_multi_event_loop() -> None:
    assert len(kr8s.Api._instances) == 0

    async def create_api():
        return await kr8s.asyncio.api()

    k1 = anyio.run(create_api)
    k2 = anyio.run(create_api)
    assert k1 is not k2


async def test_api_factory_with_kubeconfig(k8s_cluster, serviceaccount) -> None:
    k1 = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    k2 = await kr8s.asyncio.api(serviceaccount=serviceaccount)
    k3 = await kr8s.asyncio.api()
    assert k1 is not k2
    assert k3 is k1
    assert k3 is not k2

    p = await Pod({"metadata": {"name": "foo"}})
    assert p.api is k1

    p2 = await Pod({"metadata": {"name": "bar"}}, api=k2)
    assert p2.api is k2

    p3 = await Pod({"metadata": {"name": "baz"}}, api=k3)
    assert p3.api is k3
    assert p3.api is not k2


def test_version_sync():
    api = kr8s.api()
    version = api.version()
    assert "major" in version


async def test_version_sync_in_async():
    api = kr8s.api()
    version = api.version()
    assert "major" in version


async def test_version() -> None:
    api = await kr8s.asyncio.api()
    version = await api.version()
    assert "major" in version


def test_helper_version() -> None:
    version = kr8s.version()
    assert "major" in version


async def test_concurrent_api_creation() -> None:
    async def get_api():
        api = await kr8s.asyncio.api()
        await api.version()

    async with anyio.create_task_group() as tg:
        for _ in range(10):
            tg.start_soon(get_api)


async def test_both_api_creation_methods_together():
    async_api = await kr8s.asyncio.api()
    api = kr8s.api()

    assert await kr8s.asyncio.api() is async_api
    assert kr8s.api() is api
    assert async_api is not api

    assert await async_api.version() == api.version()
    assert await async_api.whoami() == api.whoami()

    assert (await async_api.get("ns"))[0]._asyncio is True
    assert api.get("ns")[0]._asyncio is False


async def test_bad_api_version() -> None:
    api = await kr8s.asyncio.api()
    with pytest.raises(ValueError):
        async with api.call_api("GET", version="foo"):
            pass  # pragma: no cover


@pytest.mark.parametrize("namespace", [kr8s.ALL, "kube-system"])
async def test_get_pods(namespace) -> None:
    pods = await kr8s.asyncio.get("pods", namespace=namespace)
    assert isinstance(pods, list)
    assert len(pods) > 0
    assert isinstance(pods[0], Pod)


async def test_get_pods_as_table() -> None:
    api = await kr8s.asyncio.api()
    pods = await api.get("pods", namespace="kube-system", as_object=Table)
    assert isinstance(pods, Table)
    assert len(pods.rows) > 0
    assert not await pods.exists()  # Cannot exist in the Kubernetes API


async def test_watch_pods(example_pod_spec, ns) -> None:
    pod = await Pod(example_pod_spec)
    await pod.create()
    while not await pod.ready():
        await anyio.sleep(0.1)
    async for event, obj in kr8s.asyncio.watch("pods", namespace=ns):
        assert event in ["ADDED", "MODIFIED", "DELETED"]
        assert isinstance(obj, Pod)
        if obj.name == pod.name:
            if event == "ADDED":
                await obj.patch({"metadata": {"labels": {"test": "test"}}})
            elif event == "MODIFIED" and "test" in obj.labels and await obj.exists():
                await obj.delete()
                while await obj.exists():
                    await anyio.sleep(0.1)
            elif event == "DELETED":
                break


async def test_get_deployments() -> None:
    api = await kr8s.asyncio.api()
    deployments = await api.get("deployments")
    assert isinstance(deployments, list)


async def test_get_class() -> None:
    api = await kr8s.asyncio.api()
    pods = await api.get(Pod, namespace=kr8s.ALL)
    assert isinstance(pods, list)
    assert len(pods) > 0
    assert isinstance(pods[0], Pod)


async def test_api_versions() -> None:
    api = await kr8s.asyncio.api()
    versions = [version async for version in api.api_versions()]
    assert "apps/v1" in versions


def test_api_versions_sync():
    api = kr8s.api()
    versions = [version for version in api.api_versions()]
    assert "apps/v1" in versions


async def test_api_resources() -> None:
    resources = await kr8s.asyncio.api_resources()

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


async def test_ns(ns) -> None:
    api = await kr8s.asyncio.api(namespace=ns)
    assert ns == api.namespace

    api.namespace = "foo"
    assert api.namespace == "foo"


async def test_async_get_returns_async_objects() -> None:
    pods = await kr8s.asyncio.get("pods", namespace=kr8s.ALL)
    assert pods[0]._asyncio is True


def test_sync_get_returns_sync_objects() -> None:
    pods = kr8s.get("pods", namespace=kr8s.ALL)
    assert pods[0]._asyncio is False


def test_sync_api_returns_sync_objects():
    api = kr8s.api()
    pods = api.get("pods", namespace=kr8s.ALL)
    assert pods[0]._asyncio is False


async def test_api_names(example_pod_spec: dict, ns: str) -> None:
    pod = await Pod(example_pod_spec)
    await pod.create()
    assert pod in await kr8s.asyncio.get("pods", namespace=ns)
    assert pod in await kr8s.asyncio.get("pods/v1", namespace=ns)
    assert pod in await kr8s.asyncio.get("Pod", namespace=ns)
    assert pod in await kr8s.asyncio.get("pod", namespace=ns)
    assert pod in await kr8s.asyncio.get("po", namespace=ns)
    await pod.delete()

    await kr8s.asyncio.get("roles", namespace=ns)
    await kr8s.asyncio.get("roles.rbac.authorization.k8s.io", namespace=ns)
    await kr8s.asyncio.get("roles.v1.rbac.authorization.k8s.io", namespace=ns)
    await kr8s.asyncio.get("roles.rbac.authorization.k8s.io/v1", namespace=ns)


async def test_whoami() -> None:
    api = await kr8s.asyncio.api()
    assert await kr8s.asyncio.whoami() == await api.whoami()


async def test_whoami_sync() -> None:
    api = kr8s.api()
    assert kr8s.whoami() == api.whoami()


async def test_api_resources_cache(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO")
    api = await kr8s.asyncio.api()
    await api.api_resources()
    assert caplog.text.count('/apis/ "HTTP/1.1 200 OK"') == 1
    await api.api_resources()
    assert caplog.text.count('/apis/ "HTTP/1.1 200 OK"') == 1


async def test_api_timeout() -> None:
    from httpx import Timeout

    api = await kr8s.asyncio.api()
    api.timeout = 10
    await api.version()
    assert api._session
    assert api._session.timeout.read == 10
    api.timeout = 20
    await api.version()
    assert api._session.timeout.read == 20
    api.timeout = Timeout(30)
    await api.version()
    assert api._session.timeout.read == 30

    api.timeout = 0.00001
    with pytest.raises(APITimeoutError):
        await api.version()


async def test_lookup_kind():
    api = await kr8s.asyncio.api()

    assert await api.lookup_kind("no") == ("node/v1", "nodes", False)
    assert await api.lookup_kind("nodes") == ("node/v1", "nodes", False)
    assert await api.lookup_kind("po") == ("pod/v1", "pods", True)
    assert await api.lookup_kind("pods/v1") == ("pod/v1", "pods", True)
    assert await api.lookup_kind("CSIStorageCapacity") == (
        "csistoragecapacity.storage.k8s.io/v1",
        "csistoragecapacities",
        True,
    )
    assert await api.lookup_kind("role") == (
        "role.rbac.authorization.k8s.io/v1",
        "roles",
        True,
    )
    assert await api.lookup_kind("roles") == (
        "role.rbac.authorization.k8s.io/v1",
        "roles",
        True,
    )
    assert await api.lookup_kind("roles.v1.rbac.authorization.k8s.io") == (
        "role.rbac.authorization.k8s.io/v1",
        "roles",
        True,
    )
    assert await api.lookup_kind("roles.rbac.authorization.k8s.io") == (
        "role.rbac.authorization.k8s.io/v1",
        "roles",
        True,
    )


async def test_nonexisting_resource_type():
    api = await kr8s.asyncio.api()

    with pytest.raises(ValueError):
        await api.get("foo.bar.baz/v1")


@pytest.mark.parametrize(
    "kind",
    [
        "csr",
        "certificatesigningrequest",
        "certificatesigningrequests",
        "certificatesigningrequest.certificates.k8s.io",
        "certificatesigningrequests.certificates.k8s.io",
        "certificatesigningrequest.v1.certificates.k8s.io",
        "certificatesigningrequests.v1.certificates.k8s.io",
        "certificatesigningrequest.certificates.k8s.io/v1",
        "certificatesigningrequests.certificates.k8s.io/v1",
    ],
)
async def test_dynamic_classes(kind, ensure_gc):
    from kr8s.asyncio.objects import get_class

    api = await kr8s.asyncio.api()

    with pytest.raises(KeyError):
        get_class("certificatesigningrequest", "certificates.k8s.io/v1")

    with pytest.raises(KeyError):
        await api.get(kind, allow_unknown_type=False)

    await api.get(kind)


@pytest.mark.parametrize(
    "kind",
    [
        "ingress.networking.k8s.io",
        "networkpolicies.networking.k8s.io",
        "csistoragecapacities.storage.k8s.io",
        "CSIStorageCapacity",
    ],
)
async def test_get_dynamic_plurals(kind, ensure_gc):
    api = await kr8s.asyncio.api()
    assert isinstance(await api.get(kind), list)
