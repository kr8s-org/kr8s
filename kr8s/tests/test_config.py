# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from kr8s._config import KubeConfig, KubeConfigSet


async def test_load_kubeconfig(k8s_cluster):
    path = str(k8s_cluster.kubeconfig_path)
    config = await KubeConfig(path)
    assert config.path == path
    assert config._raw
    assert "current-context" in config._raw
    assert config.current_context
    assert len(config.clusters) > 0
    assert "name" in config.clusters[0]
    assert len(config.users) > 0
    assert len(config.contexts) > 0


async def test_load_kubeconfig_set(k8s_cluster):
    path = str(k8s_cluster.kubeconfig_path)
    configs = await KubeConfigSet(path)
    assert len(configs._configs) == 1
    assert configs._configs[0].path == path
    assert configs._configs[0]._raw
    assert "current-context" in configs._configs[0]._raw
    assert configs.current_context
    assert len(configs.clusters) > 0
    assert "name" in configs.clusters[0]
    assert len(configs.users) > 0
    assert len(configs.contexts) > 0
