# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import os
import socket
import subprocess
import time
from contextlib import closing

import pytest
from pytest_kind.cluster import KindCluster


def check_socket(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex((host, port)) == 0


@pytest.fixture(scope="session", autouse=True)
def k8s_cluster(request):
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
