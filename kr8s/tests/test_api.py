# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import pytest

import kr8s
from kr8s.objects import Pod


async def test_api_factory(serviceaccount):
    k1 = kr8s.api()
    k2 = kr8s.api()
    assert k1 is k2

    k3 = kr8s.api(serviceaccount=serviceaccount)
    k4 = kr8s.api(serviceaccount=serviceaccount)
    assert k1 is not k3
    assert k3 is k4

    p = Pod({})
    assert p.api is k1
    assert p.api is not k3


async def test_api_factory_with_kubeconfig(k8s_cluster, serviceaccount):
    k1 = kr8s.api(kubeconfig=k8s_cluster.kubeconfig_path)
    k2 = kr8s.api(serviceaccount=serviceaccount)
    k3 = kr8s.api()
    assert k1 is not k2
    assert k3 is k1
    assert k3 is not k2

    p = Pod({})
    assert p.api is k1

    p2 = Pod({}, api=k2)
    assert p2.api is k2

    p3 = Pod({}, api=k3)
    assert p3.api is k3
    assert p3.api is not k2


async def test_version():
    kubernetes = kr8s.api()
    version = await kubernetes.version()
    assert "major" in version


@pytest.mark.parametrize("namespace", [kr8s.ALL, "kube-system"])
async def test_get_pods(namespace):
    kubernetes = kr8s.api()
    pods = await kubernetes.get("pods", namespace=namespace)
    assert isinstance(pods, list)
    assert len(pods) > 0
    assert isinstance(pods[0], Pod)


async def test_get_deployments():
    kubernetes = kr8s.api()
    deployments = await kubernetes.get("deployments")
    assert isinstance(deployments, list)


async def test_api_resources():
    kubernetes = kr8s.api()
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
