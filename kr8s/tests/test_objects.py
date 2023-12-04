# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import datetime
import pathlib
import tempfile
import time

import httpx
import pytest

import kr8s
from kr8s._exec import CompletedExec, ExecError
from kr8s.asyncio.objects import (
    APIObject,
    Deployment,
    Ingress,
    PersistentVolume,
    Pod,
    Service,
    object_from_name_type,
    objects_from_files,
)
from kr8s.asyncio.portforward import PortForward
from kr8s.objects import Pod as SyncPod
from kr8s.objects import get_class, new_class, object_from_spec

DEFAULT_TIMEOUT = httpx.Timeout(30)
CURRENT_DIR = pathlib.Path(__file__).parent


@pytest.fixture
async def nginx_pod(k8s_cluster, example_pod_spec, ns):
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
        "-n",
        ns,
        "--",
        "dd",
        "if=/dev/random",
        "of=/usr/share/nginx/html/foo.dat",
        "bs=4M",
        "count=10",
    )
    yield pod
    try:
        await pod.delete()
    except kr8s.NotFoundError:
        pass


@pytest.fixture
async def ubuntu_pod(k8s_cluster, example_pod_spec, ns):
    example_pod_spec["spec"]["containers"][0]["name"] = "ubuntu"
    example_pod_spec["spec"]["containers"][0]["image"] = "ubuntu:latest"
    example_pod_spec["spec"]["containers"][0]["command"] = ["sleep", "3600"]
    pod = await Pod(example_pod_spec)
    await pod.create()
    while not await pod.ready():
        await asyncio.sleep(0.1)
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
    try:
        await service.delete()
    except kr8s.NotFoundError:
        pass


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


async def test_pod_object_from_name_type(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    assert await pod.exists()
    pod2 = await object_from_name_type(f"pod/{pod.name}", namespace=pod.namespace)
    pod3 = await object_from_name_type(f"pod.v1/{pod.name}", namespace=pod.namespace)
    assert pod2.name == pod.name
    assert type(pod2) == type(pod)
    assert pod3.name == pod.name
    assert type(pod3) == type(pod)
    await pod.delete()


async def test_pod_wait_ready(example_pod_spec):
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


def test_pod_wait_ready_sync(example_pod_spec):
    pod = SyncPod(example_pod_spec)
    pod.create()
    pod.wait("condition=Ready")
    with pytest.raises(TimeoutError):
        pod.wait("jsonpath='{.status.phase}'=Foo", timeout=0.1)
    pod.wait("condition=Ready=true")
    pod.wait("condition=Ready=True")
    pod.wait("jsonpath='{.status.phase}'=Running")
    with pytest.raises(ValueError):
        pod.wait("foo=NotARealCondition")
    pod.delete()
    pod.wait("condition=Ready=False")
    pod.wait("delete")


def test_pod_refresh_sync(example_pod_spec):
    pod = SyncPod(example_pod_spec)
    pod.create()
    pod.refresh()
    pod.delete()


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


async def test_pod_metadata(example_pod_spec, ns):
    pod = await Pod(example_pod_spec)
    await pod.create()
    assert "name" in pod.metadata
    assert "hello" in pod.labels
    assert "foo" in pod.annotations
    assert ns == pod.namespace
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
    with pytest.raises(kr8s.NotFoundError):
        await Pod.get(f"{pod.name}-foo", namespace=pod.namespace, timeout=0.1)
    pod2 = await Pod.get(pod.name, namespace=pod.namespace)
    assert pod2.name == pod.name
    assert pod2.namespace == pod.namespace
    await pod.delete()
    while await pod.exists():
        await asyncio.sleep(0.1)
    with pytest.raises(kr8s.NotFoundError):
        await pod2.delete()


def test_pod_get_sync(example_pod_spec):
    pod = SyncPod(example_pod_spec)
    pod.create()
    with pytest.raises(kr8s.NotFoundError):
        SyncPod.get(f"{pod.name}-foo", namespace=pod.namespace, timeout=0.1)
    pod2 = SyncPod.get(pod.name, namespace=pod.namespace)
    assert pod2.name == pod.name
    assert pod2.namespace == pod.namespace
    pod.delete()
    while pod.exists():
        time.sleep(0.1)
    with pytest.raises(kr8s.NotFoundError):
        pod2.delete()


async def test_pod_from_name(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    pod2 = await Pod(
        pod.name, namespace=pod.namespace
    )  # Note: Does not call the Kubernetes API
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


@pytest.mark.parametrize("selector", ["abc=123def", {"abc": "123def"}])
async def test_label_selector(example_pod_spec, selector):
    example_pod_spec["metadata"]["labels"]["abc"] = "123def"
    pod = await Pod(example_pod_spec)
    await pod.create()

    kubernetes = await kr8s.asyncio.api()
    pods = await kubernetes.get("pods", namespace=kr8s.ALL, label_selector=selector)
    assert len(pods) >= 0

    await pod.delete()


async def test_field_selector(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()

    kubernetes = await kr8s.asyncio.api()
    pods = await kubernetes.get(
        "pods", namespace=kr8s.ALL, field_selector={"metadata.name": pod.name}
    )
    assert len(pods) == 1

    pods = await kubernetes.get(
        "pods", namespace=kr8s.ALL, field_selector="metadata.name=" + "foo-bar-baz"
    )
    assert len(pods) == 0

    await pod.delete()


async def test_get_with_label_selector(example_pod_spec, ns):
    pod = await Pod(example_pod_spec)
    await pod.create()
    await pod.label(test="test_get_with_label_selector")

    pod2 = await Pod.get(label_selector=pod.labels, namespace=ns)
    assert pod == pod2

    pod3 = await Pod.get(field_selector={"metadata.name": pod.name}, namespace=ns)
    assert pod == pod3

    await pod.delete()


async def test_pod_watch(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    async for event, obj in pod.watch():
        assert event in ("ADDED", "MODIFIED", "DELETED")
        assert obj.name == pod.name
        break
    await pod.delete()


async def test_pod_annotate(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    await pod.annotate({"foo": "bar"})
    assert "foo" in pod.annotations
    await pod.delete()


async def test_pod_label(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    await pod.label({"foo": "bar"})
    assert "foo" in pod.labels
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


async def test_patch_pod_json(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    assert "patched" not in pod.labels
    await pod.patch(
        [{"op": "replace", "path": "/metadata/labels", "value": {"patched": "true"}}],
        type="json",
    )
    assert set(pod.labels) == {"patched"}
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


async def test_new_class_registration():
    with pytest.raises(KeyError):
        get_class("MyOtherResource", "foo.kr8s.org/v1alpha1")

    MyOtherResource = new_class("MyOtherResource.foo.kr8s.org/v1alpha1")  # noqa: F841

    get_class("MyOtherResource", "foo.kr8s.org/v1alpha1")


async def test_deployment_scale(example_deployment_spec):
    deployment = await Deployment(example_deployment_spec)
    await deployment.create()
    assert deployment.replicas == 1
    await deployment.scale(2)
    assert deployment.replicas == 2
    while not await deployment.ready():
        await asyncio.sleep(0.1)
    pods = await deployment.pods()
    assert len(pods) == 2
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
    assert isinstance(data, httpx.Response)


async def test_pod_logs(example_pod_spec):
    pod = await Pod(example_pod_spec)
    await pod.create()
    while not await pod.ready():
        await asyncio.sleep(0.1)
    log = "\n".join([line async for line in pod.logs(container="pause")])
    assert isinstance(log, str)
    await pod.delete()


async def test_pod_port_forward_context_manager(nginx_service):
    [nginx_pod, *_] = await nginx_service.ready_pods()
    async with nginx_pod.portforward(80) as port:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as session:
            resp = await session.get(f"http://localhost:{port}/")
            assert resp.status_code == 200
            resp = await session.get(f"http://localhost:{port}/foo")
            assert resp.status_code == 404
            resp = await session.get(f"http://localhost:{port}/foo.dat")
            assert resp.status_code == 200
            resp.read()


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
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as session:
        resp = await session.get(f"http://localhost:{port}/")
        assert resp.status_code == 200
        resp = await session.get(f"http://localhost:{port}/foo")
        assert resp.status_code == 404
        resp = await session.get(f"http://localhost:{port}/foo.dat")
        assert resp.status_code == 200
        resp.read()
    await pf.stop()
    assert pf._bg_task is None


async def test_service_port_forward_context_manager(nginx_service):
    async with nginx_service.portforward(80) as port:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as session:
            resp = await session.get(f"http://localhost:{port}/")
            assert resp.status_code == 200
            resp = await session.get(f"http://localhost:{port}/foo")
            assert resp.status_code == 404


async def test_service_port_forward_start_stop(nginx_service):
    pf = nginx_service.portforward(80)
    assert pf._bg_task is None
    port = await pf.start()
    assert pf._bg_task is not None

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as session:
        resp = await session.get(f"http://localhost:{port}/")
        assert resp.status_code == 200
        resp = await session.get(f"http://localhost:{port}/foo")
        assert resp.status_code == 404

    await pf.stop()
    assert pf._bg_task is None


async def test_unsupported_port_forward():
    pv = await PersistentVolume({"metadata": {"name": "foo"}})
    with pytest.raises(AttributeError):
        await pv.portforward(80)
    with pytest.raises(ValueError):
        await PortForward(pv, 80).start()


async def test_scalable_dot_notation():
    class Foo(APIObject):
        version = "foo.kr8s.org/v1alpha1"
        endpoint = "foos"
        kind = "Foo"
        plural = "foos"
        singular = "foo"
        namespaced = True
        scalable = True
        scalable_spec = "nested.replicas"

    foo = await Foo({"metadata": {"name": "foo"}, "spec": {"nested": {"replicas": 1}}})
    assert foo.replicas == 1


async def test_object_from_file():
    api = await kr8s.asyncio.api()
    objects = await objects_from_files(
        CURRENT_DIR / "resources" / "simple" / "nginx_pod.yaml", api=api
    )
    assert len(objects) == 1
    assert isinstance(objects[0], Pod)
    assert objects[0].kind == "Pod"
    assert objects[0].name == "nginx"
    assert len(objects[0].spec.containers) == 1


async def test_objects_from_file():
    objects = await objects_from_files(
        CURRENT_DIR / "resources" / "simple" / "nginx_pod_service.yaml"
    )
    assert len(objects) == 2
    assert isinstance(objects[0], Pod)
    assert isinstance(objects[1], Service)
    assert len(objects[1].spec.ports) == 1


async def test_objects_from_files():
    simple_dir = CURRENT_DIR / "resources" / "simple"
    objects = await objects_from_files(simple_dir)
    assert len(objects) > 1


async def test_objects_from_files_nested():
    simple_dir = CURRENT_DIR / "resources" / "simple"

    objects = await objects_from_files(simple_dir)
    assert not any(isinstance(o, Ingress) for o in objects)

    objects = await objects_from_files(simple_dir, recursive=True)
    assert any(isinstance(o, Ingress) for o in objects)


async def test_custom_object_from_file():
    simple_dir = CURRENT_DIR / "resources" / "custom" / "evc.yaml"
    objects = await objects_from_files(simple_dir)
    assert len(objects) == 1


async def test_pod_to_dict(example_pod_spec):
    pod = Pod(example_pod_spec)
    assert dict(pod) == example_pod_spec
    assert dict(pod) == pod.raw


async def test_adoption(nginx_service):
    [nginx_pod, *_] = await nginx_service.ready_pods()
    await nginx_service.adopt(nginx_pod)
    assert "ownerReferences" in nginx_pod.metadata
    assert nginx_pod.metadata["ownerReferences"][0]["name"] == nginx_service.name
    await nginx_service.delete()
    while await nginx_pod.exists():
        await asyncio.sleep(0.1)


async def test_cast_to_from_lightkube(example_pod_spec):
    pytest.importorskip("lightkube")
    from lightkube import codecs
    from lightkube.resources.core_v1 import Pod as LightkubePod

    starting_pod = codecs.from_dict(example_pod_spec)

    kr8s_pod = await Pod(starting_pod)
    assert isinstance(kr8s_pod, Pod)
    assert kr8s_pod.name == example_pod_spec["metadata"]["name"]
    assert kr8s_pod.namespace == example_pod_spec["metadata"]["namespace"]
    assert kr8s_pod.kind == "Pod"
    assert kr8s_pod.version == "v1"

    lightkube_pod = kr8s_pod.to_lightkube()
    assert isinstance(lightkube_pod, LightkubePod)
    assert lightkube_pod.metadata.name == example_pod_spec["metadata"]["name"]
    assert lightkube_pod.metadata.namespace == example_pod_spec["metadata"]["namespace"]


async def test_cast_to_from_kubernetes(example_pod_spec):
    kubernetes = pytest.importorskip("kubernetes")

    starting_pod = kubernetes.client.models.v1_pod.V1Pod(
        api_version=example_pod_spec["apiVersion"],
        kind=example_pod_spec["kind"],
        metadata=example_pod_spec["metadata"],
        spec=example_pod_spec["spec"],
    )

    kr8s_pod = await Pod(starting_pod)
    assert isinstance(kr8s_pod, Pod)
    assert kr8s_pod.name == example_pod_spec["metadata"]["name"]
    assert kr8s_pod.namespace == example_pod_spec["metadata"]["namespace"]
    assert kr8s_pod.kind == "Pod"
    assert kr8s_pod.version == "v1"


async def test_cast_to_from_kubernetes_asyncio(example_pod_spec):
    kubernetes_asyncio = pytest.importorskip("kubernetes_asyncio")

    starting_pod = kubernetes_asyncio.client.models.v1_pod.V1Pod(
        api_version=example_pod_spec["apiVersion"],
        kind=example_pod_spec["kind"],
        metadata=example_pod_spec["metadata"],
        spec=example_pod_spec["spec"],
    )

    kr8s_pod = await Pod(starting_pod)
    assert isinstance(kr8s_pod, Pod)
    assert kr8s_pod.name == example_pod_spec["metadata"]["name"]
    assert kr8s_pod.namespace == example_pod_spec["metadata"]["namespace"]
    assert kr8s_pod.kind == "Pod"
    assert kr8s_pod.version == "v1"


async def test_cast_to_from_pykube_ng(example_pod_spec):
    pykube = pytest.importorskip("pykube")

    starting_pod = pykube.objects.Pod(None, example_pod_spec)

    kr8s_pod = await Pod(starting_pod)
    assert isinstance(kr8s_pod, Pod)
    assert kr8s_pod.name == example_pod_spec["metadata"]["name"]
    assert kr8s_pod.namespace == example_pod_spec["metadata"]["namespace"]
    assert kr8s_pod.kind == "Pod"
    assert kr8s_pod.version == "v1"

    pykube_pod = kr8s_pod.to_pykube(None)
    assert isinstance(pykube_pod, pykube.objects.Pod)
    assert pykube_pod.name == example_pod_spec["metadata"]["name"]
    assert pykube_pod.namespace == example_pod_spec["metadata"]["namespace"]


async def test_to_dict(example_pod_spec):
    pod = await Pod(example_pod_spec)
    to_spec = pod.to_dict()
    assert to_spec == example_pod_spec
    assert isinstance(to_spec, dict)


async def test_pod_exec(ubuntu_pod):
    ex = await ubuntu_pod.exec(["date"])
    assert isinstance(ex, CompletedExec)
    assert str(datetime.datetime.now().year) in ex.stdout.decode()
    assert ex.args == ["date"]
    assert ex.stderr == b""
    assert ex.returncode == 0


async def test_pod_exec_error(ubuntu_pod):
    with pytest.raises(ExecError):
        await ubuntu_pod.exec(["date", "foo"])

    ex = await ubuntu_pod.exec(["date", "foo"], check=False)
    assert ex.args == ["date", "foo"]
    assert b"invalid date" in ex.stderr
    assert ex.returncode == 1

    with pytest.raises(ExecError):
        ex.check_returncode()


async def test_pod_exec_to_file(ubuntu_pod):
    with tempfile.TemporaryFile(mode="w+b") as tmp:
        exc = await ubuntu_pod.exec(["date"], stdout=tmp, capture_output=False)
        tmp.seek(0)
        assert str(datetime.datetime.now().year) in tmp.read().decode()
        assert exc.stdout == b""

    with tempfile.TemporaryFile(mode="w+b") as tmp:
        with pytest.raises(ExecError):
            await ubuntu_pod.exec(["date", "foo"], stderr=tmp)
        tmp.seek(0)
        assert b"invalid date" in tmp.read()


@pytest.mark.skip("Closing stdin not supported so hangs forever")
async def test_pod_exec_stdin(ubuntu_pod):
    ex = await ubuntu_pod.exec(["cat"], stdin="foo")
    assert b"foo" in ex.stdout


async def test_configmap_data(ns):
    [cm] = await objects_from_files(CURRENT_DIR / "resources" / "configmap.yaml")
    cm.namespace = ns
    await cm.create()
    assert "game.properties" in cm.data
    assert cm.data.player_initial_lives == "3"
    assert "color.good=purple" in cm.data["user-interface.properties"]
    await cm.delete()


async def test_secret_data(ns):
    [secret] = await objects_from_files(CURRENT_DIR / "resources" / "secret.yaml")
    secret.namespace = ns
    await secret.create()
    assert "tls.crt" in secret.data
    await secret.delete()


async def test_validate_pod(example_pod_spec):
    kubernetes_validate = pytest.importorskip("kubernetes_validate")
    pod = await Pod(example_pod_spec)
    kubernetes_validate.validate(pod.raw, "1.28", strict=True)


async def test_validate_pod_fail(bad_pod_spec):
    kubernetes_validate = pytest.importorskip("kubernetes_validate")
    pod = await Pod(bad_pod_spec)
    with pytest.raises(kubernetes_validate.ValidationError):
        kubernetes_validate.validate(pod.raw, "1.28", strict=True)


async def test_pod_errors(bad_pod_spec):
    pod = await Pod(bad_pod_spec)
    with pytest.raises(kr8s.ServerError, match="Required value"):
        await pod.create()
