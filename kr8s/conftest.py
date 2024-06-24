# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import base64
import os
import socket
import subprocess
import tempfile
import uuid
from contextlib import closing
from pathlib import Path

import anyio
import pytest
import yaml

from kr8s._api import Api
from kr8s._testutils import set_env

HERE = Path(__file__).parent.resolve()
DEFAULT_LABELS = {"created-by": "kr8s-tests"}


@pytest.fixture
async def example_pod_spec(ns):
    name = "example-" + uuid.uuid4().hex[:10]
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": name,
            "namespace": ns,
            "labels": {"hello": "world", **DEFAULT_LABELS},
            "annotations": {"foo": "bar"},
        },
        "spec": {
            "containers": [{"name": "pause", "image": "gcr.io/google_containers/pause"}]
        },
    }


@pytest.fixture
async def bad_pod_spec(ns):
    name = "example-" + uuid.uuid4().hex[:10]
    return {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": name,
            "namespace": ns,
        },
        "spec": {
            "containers": [
                {
                    "name1": "pause",  # This is bad
                    "image": "gcr.io/google_containers/pause",
                }
            ]
        },
    }


@pytest.fixture
async def example_service_spec(ns):
    name = "example-" + uuid.uuid4().hex[:10]
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": ns,
            "labels": {"hello": "world", **DEFAULT_LABELS},
            "annotations": {"foo": "bar"},
        },
        "spec": {
            "ports": [{"port": 80, "targetPort": 9376}],
            "selector": {"app": "MyApp"},
        },
    }


@pytest.fixture
async def example_deployment_spec(ns):
    name = "example-" + uuid.uuid4().hex[:10]
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": ns,
            "labels": {"hello": "world", **DEFAULT_LABELS},
            "annotations": {"foo": "bar"},
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": name}},
            "template": {
                "metadata": {"labels": {"app": name}},
                "spec": {
                    "containers": [
                        {
                            "name": "pause",
                            "image": "gcr.io/google_containers/pause",
                        }
                    ]
                },
            },
        },
    }


def check_socket(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0


@pytest.fixture(scope="session", autouse=True)
def run_id():
    return uuid.uuid4().hex[:4]


@pytest.fixture(autouse=True)
def ns(k8s_cluster, run_id):
    name = f"kr8s-pytest-{run_id}-{uuid.uuid4().hex[:4]}"
    k8s_cluster.kubectl("create", "namespace", name)
    yield name
    k8s_cluster.kubectl("delete", "namespace", name, "--wait=false")


@pytest.fixture
async def kubectl_proxy(k8s_cluster):
    proxy = subprocess.Popen(
        [k8s_cluster.kubectl_path, "proxy"],
        env={**os.environ, "KUBECONFIG": str(k8s_cluster.kubeconfig_path)},
    )
    host = "localhost"
    port = 8001
    while not check_socket(host, port):
        await anyio.sleep(0.1)
    yield f"http://{host}:{port}"
    proxy.kill()


@pytest.fixture(scope="session")
def k8s_token(k8s_cluster):
    # Apply the serviceaccount.yaml
    k8s_cluster.kubectl(
        "apply", "-f", str(HERE / "tests" / "resources" / "serviceaccount.yaml")
    )
    yield k8s_cluster.kubectl("create", "token", "pytest")
    # Delete the serviceaccount.yaml
    k8s_cluster.kubectl(
        "delete", "-f", str(HERE / "tests" / "resources" / "serviceaccount.yaml")
    )


@pytest.fixture
def serviceaccount(k8s_cluster, k8s_token):
    # Load kubeconfig
    kubeconfig = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())

    # Get the server host and port from the kubeconfig
    _hostport = kubeconfig["clusters"][0]["cluster"]["server"].split("//")[1]
    host, port = _hostport.split(":")

    # Create a temporary directory and populate it with the serviceaccount files
    with tempfile.TemporaryDirectory() as tempdir, set_env(
        KUBERNETES_SERVICE_HOST=host, KUBERNETES_SERVICE_PORT=port
    ):
        tempdir = Path(tempdir)
        # Create ca.crt in tempdir from the certificate-authority-data in kubeconfig
        (tempdir / "ca.crt").write_text(
            base64.b64decode(
                kubeconfig["clusters"][0]["cluster"]["certificate-authority-data"]
            ).decode()
        )
        namespace = "default"
        (tempdir / "token").write_text(k8s_token)
        (tempdir / "namespace").write_text(namespace)
        yield str(tempdir)


@pytest.fixture(autouse=True)
def ensure_new_api_between_tests():
    yield
    Api._instances.clear()
