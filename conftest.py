# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import gc
import logging
import os
import time
from collections.abc import Generator
from pathlib import Path
from typing import Optional

import pytest
import yaml
from pytest_kind.cluster import KindCluster


def get_github_actions_default_kubernetes_version() -> Optional[str]:
    try:
        workflow_file = Path(".github/workflows/test-kr8s.yaml")
        if not workflow_file.exists():
            return None
        workflow = yaml.safe_load(workflow_file.read_text())
        return workflow["jobs"]["test"]["strategy"]["matrix"]["kubernetes-version"][0]
    except Exception:
        return None


@pytest.fixture
def ensure_gc():
    """Ensure garbage collection is run before and after the test."""
    gc.collect()
    yield
    gc.collect()


@pytest.fixture(scope="session", autouse=True)
def k8s_cluster(request) -> Generator[KindCluster, None, None]:
    image = None
    if version := os.environ.get("KUBERNETES_VERSION"):
        image = f"kindest/node:v{version}"
    elif version := get_github_actions_default_kubernetes_version():
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


@pytest.fixture(scope="session")
def kubectl_api_cache(k8s_cluster) -> Generator[KindCluster, None, None]:
    """Ensure that kubectl has written its api cache to disk."""
    logging.basicConfig(level=logging.DEBUG)
    k8s_cluster.kubectl("get", "--raw", "/api/v1")
    yield k8s_cluster
