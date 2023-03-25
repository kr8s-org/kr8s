# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from kr8s import Kr8sApi


async def test_kubeconfig(k8s_cluster):
    kubernetes = Kr8sApi(kubeconfig=k8s_cluster.kubeconfig_path)
    version = await kubernetes.get_version()
    assert "major" in version


async def test_url(kubectl_proxy):
    kubernetes = Kr8sApi(url=kubectl_proxy)
    version = await kubernetes.get_version()
    assert "major" in version
