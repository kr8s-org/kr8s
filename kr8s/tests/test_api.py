# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import queue
import threading
import warnings
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import anyio
import pytest

import kr8s
import kr8s.asyncio
from kr8s._async_utils import anext
from kr8s._constants import (
    KUBERNETES_MAXIMUM_SUPPORTED_VERSION,
    KUBERNETES_MINIMUM_SUPPORTED_VERSION,
)
from kr8s._exceptions import APITimeoutError, ServerError
from kr8s.asyncio.objects import Pod, Service, Table
from kr8s.objects import Pod as SyncPod
from kr8s.objects import Service as SyncService


@pytest.fixture
async def example_crd(example_crd_spec):
    async with create_delete_crd(example_crd_spec) as example:
        yield example


@asynccontextmanager
async def create_delete_crd(spec):
    example = await kr8s.asyncio.objects.CustomResourceDefinition(spec)

    # Clean up any existing CRD if it exists from a previous failed test run
    if await example.exists():
        await example.delete()
    while await example.exists():
        await anyio.sleep(0.1)

    # Create the CRD
    if not await example.exists():
        await example.create()
    while not await example.exists():
        await anyio.sleep(0.1)

    # Check that the CRD gets returned
    assert example in [
        crd async for crd in kr8s.asyncio.get("customresourcedefinitions")
    ]
    yield example

    # Clean up the CRD
    await example.delete()
    while await example.exists():
        await anyio.sleep(0.1)


async def test_factory_bypass() -> None:
    with pytest.raises(ValueError, match="kr8s.api()"):
        _ = kr8s.Api()
    _ = kr8s.api()


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

    assert (await anext(async_api.get("ns")))._asyncio is True
    assert next(api.get("ns"))._asyncio is False


async def test_bad_api_version() -> None:
    api = await kr8s.asyncio.api()
    with pytest.raises(ValueError):
        async with api.call_api("GET", version="foo"):
            pass  # pragma: no cover


@pytest.mark.parametrize("namespace", [kr8s.ALL, "kube-system"])
async def test_get_pods(namespace) -> None:
    pods = [po async for po in kr8s.asyncio.get("pods", namespace=namespace)]
    assert isinstance(pods, list)
    assert len(pods) > 0
    assert isinstance(pods[0], Pod)


async def test_get_custom_resouces(example_crd) -> None:
    async for shirt in kr8s.asyncio.get(example_crd.name):
        assert shirt


async def test_get_pods_as_table() -> None:
    api = await kr8s.asyncio.api()
    async for pods in api.get("pods", namespace="kube-system", as_object=Table):
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
    deployments = [dply async for dply in api.get("deployments")]
    assert isinstance(deployments, list)


async def test_get_class() -> None:
    api = await kr8s.asyncio.api()
    pods = [pod async for pod in api.get(Pod, namespace=kr8s.ALL)]
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
    pods = [po async for po in kr8s.asyncio.get("pods", namespace=kr8s.ALL)]
    assert pods[0]._asyncio is True


def test_sync_get_returns_sync_objects() -> None:
    pods = list(kr8s.get("pods", namespace=kr8s.ALL))
    assert pods[0]._asyncio is False
    pods[0].refresh()


def test_sync_api_returns_sync_objects():
    api = kr8s.api()
    pods = api.get("pods", namespace=kr8s.ALL)
    pod = next(pods)
    assert pod._asyncio is False
    pod.refresh()


async def test_api_names(example_pod_spec: dict, ns: str) -> None:
    pod = await Pod(example_pod_spec)
    await pod.create()
    assert pod in [pod async for pod in kr8s.asyncio.get("pods", namespace=ns)]
    assert pod in [pod async for pod in kr8s.asyncio.get("pods/v1", namespace=ns)]
    assert pod in [pod async for pod in kr8s.asyncio.get("Pod", namespace=ns)]
    assert pod in [pod async for pod in kr8s.asyncio.get("pod", namespace=ns)]
    assert pod in [pod async for pod in kr8s.asyncio.get("po", namespace=ns)]
    await pod.delete()

    [role async for role in kr8s.asyncio.get("roles", namespace=ns)]
    [
        role
        async for role in kr8s.asyncio.get(
            "roles.rbac.authorization.k8s.io", namespace=ns
        )
    ]
    [
        role
        async for role in kr8s.asyncio.get(
            "roles.v1.rbac.authorization.k8s.io", namespace=ns
        )
    ]
    [
        role
        async for role in kr8s.asyncio.get(
            "roles.rbac.authorization.k8s.io/v1", namespace=ns
        )
    ]


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
        async for _ in api.get("foo.bar.baz/v1"):
            pass


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
        async for _ in api.get(kind, allow_unknown_type=False):
            pass

    async for _ in api.get(kind):
        pass


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
    assert isinstance([resource async for resource in api.get(kind)], list)


async def test_two_pods(ns):
    gen_kwargs = {
        "generate_name": "example-",
        "image": "gcr.io/google_containers/pause",
        "namespace": ns,
    }
    pods = [await Pod.gen(**gen_kwargs), await Pod.gen(**gen_kwargs)]

    async with anyio.create_task_group() as tg:
        for pod in pods:
            tg.start_soon(pod.create)

    async with anyio.create_task_group() as tg:
        for pod in pods:
            tg.start_soon(pod.wait, "condition=Ready")

    pods_api = [
        pod
        async for pod in kr8s.asyncio.get(
            "Pod", pods[0].name, pods[1].name, namespace=ns
        )
    ]
    assert len(pods_api) == 2

    async with anyio.create_task_group() as tg:
        for pod in pods:
            tg.start_soon(pod.delete)


async def test_create(example_pod_spec, example_service_spec):
    pod = await Pod(example_pod_spec)
    service = await Service(example_service_spec)
    resources = [pod, service]
    await kr8s.asyncio.create(resources)
    assert await pod.exists(), "Pod should exist after creation"
    assert await service.exists(), "Service should exist after creation"
    await pod.delete()
    await service.delete()


def test_create_sync(example_pod_spec, example_service_spec):
    pod = SyncPod(example_pod_spec)
    service = SyncService(example_service_spec)
    assert pod._asyncio is False
    assert service._asyncio is False
    resources = [pod, service]
    kr8s.create(resources)
    assert pod.exists(), "Pod should exist after creation"
    assert service.exists(), "Service should exist after creation"
    pod.delete()
    service.delete()


async def test_create_with_apply(example_pod_spec, example_service_spec):
    pod = await Pod(example_pod_spec)
    service = await Service(example_service_spec)
    resources = [pod, service]
    await kr8s.asyncio.apply(resources)
    assert pod.exists(), "Pod should exist after creation"
    assert service.exists(), "Service should exist after creation"
    await pod.delete()
    await service.delete()


async def test_update_with_apply(example_pod_spec, example_service_spec):
    pod = await Pod(example_pod_spec)
    service = await Service(example_service_spec)
    resources = [pod, service]
    await kr8s.asyncio.create(resources)
    pod.labels["foo"] = "bar"
    await kr8s.asyncio.apply([pod])
    assert pod.labels["foo"] == "bar", "Apply should send updated resource"
    updated_pod = await Pod.get(pod.name, namespace=pod.namespace)
    assert (
        updated_pod.labels["foo"] == "bar"
    ), "Pod we got by re-fetching should have updated labels"
    await pod.delete()


async def test_update_with_ssa(example_pod_spec, example_service_spec):
    pod = await Pod(example_pod_spec)
    service = await Service(example_service_spec)
    resources = [pod, service]
    await kr8s.asyncio.apply(resources, server_side=True)

    pod.labels["foo"] = "bar"
    await pod.apply(server_side=True)
    assert pod.labels["foo"] == "bar", "SSA update should send updated resource"
    assert pod.exists(), "Pod should exist after creation"
    assert pod.labels["foo"] == "bar", "SSA update should send updated resource"


async def test_update_with_ssa_force(example_pod_spec, example_service_spec):
    """
    SSA has semantics about modifying fields owned by other managers.

    We would need to use the force option to override this.
    """
    pod = await Pod(example_pod_spec)
    pod.labels["my_field"] = "other-manager"
    service = await Service(example_service_spec)
    resources = [pod, service]

    other_api = await kr8s.asyncio.api(field_manager="other-manager")
    pod.api = other_api  # api param in helpers is ignored
    await kr8s.asyncio.apply(resources, server_side=True)
    assert pod.exists(), "Pod should exist after creation"

    api = await kr8s.asyncio.api(field_manager="kr8s")
    pod.api = api  # api param in helpers is ignored
    with pytest.RaisesGroup(ServerError):
        pod.labels["my_field"] = "changed"
        await kr8s.asyncio.apply([pod], server_side=True)

    await kr8s.asyncio.apply([pod], server_side=True, force_conflicts=True)
    assert pod.exists(), "Pod should exist after creation"
    assert (
        pod.labels["my_field"] == "changed"
    ), "SSA update should send updated resource"


async def test_apply_creates_if_not_exists(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.apply()
    assert pod.exists(), "Pod should exist after creation"


@pytest.mark.parametrize(
    "version",
    [
        "1.27.0",
        "v1.27.0",
        "1.27.0-eks-113cf36",
        "v1.27.0-eks-113cf36",
        f"{KUBERNETES_MAXIMUM_SUPPORTED_VERSION.major}.{KUBERNETES_MAXIMUM_SUPPORTED_VERSION.minor+1}",
        "asdkjhaskdjhasd",
    ],
)
async def test_bad_kubernetes_version(version):
    api = await kr8s.asyncio.api()
    keep = api.async_version
    api.async_version = AsyncMock(return_value={"gitVersion": version})
    with pytest.warns(UserWarning, match=version):
        await api._check_version()
    api.async_version = keep


@pytest.mark.parametrize(
    "version",
    [
        str(KUBERNETES_MINIMUM_SUPPORTED_VERSION),
        str(KUBERNETES_MAXIMUM_SUPPORTED_VERSION),
        f"{KUBERNETES_MAXIMUM_SUPPORTED_VERSION.major}.{KUBERNETES_MAXIMUM_SUPPORTED_VERSION.minor}.15",
        f"{KUBERNETES_MINIMUM_SUPPORTED_VERSION}-eks-113cf36",
    ],
)
async def test_good_kubernetes_version(version):
    api = await kr8s.asyncio.api()
    keep = api.async_version
    api.async_version = AsyncMock(return_value={"gitVersion": version})
    with warnings.catch_warnings(record=True) as w:
        await api._check_version()
        assert w == []
    api.async_version = keep


async def test_crd_caching(example_crd_spec):
    api = await kr8s.asyncio.api()

    # Populate the cache
    [r async for r in api.get("pods")]

    # Register a new CRD
    async with create_delete_crd(example_crd_spec) as example_crd:
        # Try to get the new CRD (which isn't in the cache, so the cache should be bypassed)
        [r async for r in api.get(example_crd.name)]


async def test_get_raw_basic() -> None:
    """Test getting resources with raw=True returns dictionaries, not APIObject instances."""
    api = await kr8s.asyncio.api()
    pods = [pod async for pod in api.get("pods", namespace="kube-system", raw=True)]
    assert isinstance(pods, list)
    assert len(pods) > 0
    # Should be dictionaries, not Pod objects
    assert isinstance(pods[0], dict)
    assert "metadata" in pods[0]
    assert "name" in pods[0]["metadata"]


async def test_get_raw_false_default() -> None:
    """Test that default behavior (without raw parameter) returns APIObject instances."""
    api = await kr8s.asyncio.api()
    pods = [pod async for pod in api.get("pods", namespace="kube-system")]
    assert isinstance(pods, list)
    assert len(pods) > 0
    # Should be Pod objects, not dictionaries
    assert isinstance(pods[0], Pod)
    assert not isinstance(pods[0], dict)


async def test_get_raw_with_as_object() -> None:
    """Test that when both as_object and raw=True are specified, yields the raw dictionary."""
    api = await kr8s.asyncio.api()
    async for result in api.get(
        "pods", namespace="kube-system", as_object=Table, raw=True
    ):
        # Should be a dictionary, not a Table object
        assert isinstance(result, dict)
        assert "kind" in result
        assert result["kind"] == "Table"
        # When as_object is specified, the API returns a single object (Table format)
        break


async def test_get_raw_with_label_selector() -> None:
    """Test that label selectors work with raw=True."""
    selector = {"component": "kube-apiserver"}
    pods = [
        pod
        async for pod in kr8s.asyncio.get(
            "pods", namespace="kube-system", label_selector=selector, raw=True
        )
    ]
    # Should get dictionaries
    for pod in pods:
        assert isinstance(pod, dict)
        assert "metadata" in pod
        if "labels" in pod["metadata"]:
            # If labels exist, verify the selector matches
            assert pod["metadata"]["labels"].get("component") == "kube-apiserver"


async def test_get_raw_with_field_selector() -> None:
    """Test that field selectors work with raw=True."""
    pods = [
        pod
        async for pod in kr8s.asyncio.get(
            "pods",
            namespace="kube-system",
            field_selector="status.phase=Running",
            raw=True,
        )
    ]
    # Should get dictionaries
    assert len(pods) > 0
    for pod in pods:
        assert isinstance(pod, dict)
        assert pod["status"]["phase"] == "Running"


def test_get_raw_sync() -> None:
    """Test the sync version (kr8s.get()) with raw=True."""
    pods = list(kr8s.get("pods", namespace="kube-system", raw=True))
    assert isinstance(pods, list)
    assert len(pods) > 0
    # Should be dictionaries, not Pod objects
    assert isinstance(pods[0], dict)
    assert "metadata" in pods[0]
    assert not isinstance(pods[0], SyncPod)


async def test_list_raw() -> None:
    """Test the APIObject.list() classmethod with raw=True returns dictionaries."""
    pods = [pod async for pod in Pod.list(namespace="kube-system", raw=True)]
    assert isinstance(pods, list)
    assert len(pods) > 0
    # Should be dictionaries, not Pod objects
    assert isinstance(pods[0], dict)
    assert "metadata" in pods[0]
    assert not isinstance(pods[0], Pod)
