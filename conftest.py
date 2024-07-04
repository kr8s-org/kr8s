# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import gc
import os
import time

import pytest
from pytest_kind.cluster import KindCluster


@pytest.fixture
def ensure_gc():
    """Ensure garbage collection is run before and after the test."""
    gc.collect()
    yield
    gc.collect()


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
    if not request.config.getoption("keep_cluster"):  # pragma: no cover
        kind_cluster.delete()
