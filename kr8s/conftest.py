# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import os
import subprocess
import time

import pytest
from pytest_kind.cluster import KindCluster


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
    yield "http://localhost:8001"
    proxy.kill()
