# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import base64
import os
import socket
import subprocess
import tempfile
import time
from contextlib import closing
from pathlib import Path

import pytest
import yaml
from pytest_kind.cluster import KindCluster

from kr8s._testutils import set_env

HERE = Path(__file__).parent.resolve()


def check_socket(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0


@pytest.fixture(scope="session", autouse=True)
def k8s_cluster(request) -> KindCluster:
    image = None
    if version := os.environ.get("KUBERNETES_VERSION"):
        image = f"kindest/node:v{version}"

    kind_cluster = KindCluster(
        name="pytest-kind",
        image=image,
    )
    kind_cluster.create()
    os.environ["KUBECONFIG"] = str(kind_cluster.kubeconfig_path)
    # CI fix, wait for default service account to be created before continuing
    while True:
        try:
            kind_cluster.kubectl("get", "serviceaccount", "default")
            break
        except Exception:
            time.sleep(1)
    yield kind_cluster
    del os.environ["KUBECONFIG"]
    if not request.config.getoption("keep_cluster"):
        kind_cluster.delete()


@pytest.fixture(scope="session")
def ns(k8s_cluster) -> str:
    # Ideally we want to generate a random namespace for each test or suite, but
    # this can make teardown very slow. So we just use the default namespace for now.

    yield "default"

    # name = "kr8s-pytest-" + uuid.uuid4().hex[:4]
    # k8s_cluster.kubectl("create", "namespace", name)
    # yield name
    # k8s_cluster.kubectl("delete", "namespace", name)


@pytest.fixture
async def kubectl_proxy(k8s_cluster):
    proxy = subprocess.Popen(
        [k8s_cluster.kubectl_path, "proxy"],
        env={**os.environ, "KUBECONFIG": str(k8s_cluster.kubeconfig_path)},
    )
    host = "localhost"
    port = 8001
    while not check_socket(host, port):
        await asyncio.sleep(0.1)
    yield f"http://{host}:{port}"
    proxy.kill()


@pytest.fixture
def serviceaccount(k8s_cluster):
    # Load kubeconfig
    kubeconfig = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())

    # Get the server host and port from the kubeconfig
    _hostport = kubeconfig["clusters"][0]["cluster"]["server"].split("//")[1]
    host, port = _hostport.split(":")

    # Apply the serviceaccount.yaml
    k8s_cluster.kubectl(
        "apply", "-f", str(HERE / "tests" / "resources" / "serviceaccount.yaml")
    )

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
        token = k8s_cluster.kubectl("create", "token", "pytest")
        namespace = "default"
        (tempdir / "token").write_text(token)
        (tempdir / "namespace").write_text(namespace)
        yield str(tempdir)

    # Delete the serviceaccount.yaml
    k8s_cluster.kubectl(
        "delete", "-f", str(HERE / "tests" / "resources" / "serviceaccount.yaml")
    )
