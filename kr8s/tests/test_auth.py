# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from pathlib import Path

import pytest

from kr8s import Kr8sApi


async def test_kubeconfig(k8s_cluster):
    kubernetes = Kr8sApi(kubeconfig=k8s_cluster.kubeconfig_path)
    version = await kubernetes.get_version()
    assert "major" in version


async def test_url(kubectl_proxy):
    kubernetes = Kr8sApi(url=kubectl_proxy)
    version = await kubernetes.get_version()
    assert "major" in version


async def test_no_config():
    with pytest.raises(ValueError):
        Kr8sApi(kubeconfig="/no/file/here")


async def test_service_account(serviceaccount):
    kubernetes = Kr8sApi(serviceaccount=serviceaccount, kubeconfig="/no/file/here")

    serviceaccount = Path(serviceaccount)
    assert kubernetes.auth.server
    assert kubernetes.auth.token == (serviceaccount / "token").read_text()
    assert str(serviceaccount) in kubernetes.auth.server_ca_file
    assert "BEGIN CERTIFICATE" in Path(kubernetes.auth.server_ca_file).read_text()
    assert kubernetes.auth.namespace == (serviceaccount / "namespace").read_text()
