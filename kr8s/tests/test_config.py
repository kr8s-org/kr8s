# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from tempfile import NamedTemporaryFile

import pytest
import yaml

from kr8s._config import KubeConfig, KubeConfigSet


@pytest.fixture
def temp_kubeconfig(k8s_cluster):
    """Create a temporary kubeconfig by copying the one from k8s_cluster."""
    with open(k8s_cluster.kubeconfig_path, "rb") as f:
        kubeconfig = f.read()
    with NamedTemporaryFile() as f:
        f.write(kubeconfig)
        f.flush()
        yield f.name


async def test_load_kubeconfig(temp_kubeconfig):
    config = await KubeConfig(temp_kubeconfig)
    assert str(config.path) == temp_kubeconfig
    assert config._raw
    assert "current-context" in config._raw
    assert config.current_context
    assert len(config.clusters) > 0
    assert "name" in config.clusters[0]
    assert len(config.users) > 0
    assert len(config.contexts) > 0


async def test_load_kubeconfig_set(temp_kubeconfig):
    configs = await KubeConfigSet(temp_kubeconfig)
    assert len(configs._configs) == 1
    assert str(configs._configs[0].path) == temp_kubeconfig
    assert configs._configs[0]._raw
    assert "current-context" in configs._configs[0]._raw
    assert configs.current_context
    assert len(configs.clusters) > 0
    assert "name" in configs.clusters[0]
    assert len(configs.users) > 0
    assert len(configs.contexts) > 0


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_kubeconfig_from_dict(temp_kubeconfig, cls):
    with open(temp_kubeconfig) as fh:
        config = yaml.safe_load(fh)
    kubeconfig = await cls(config)
    assert kubeconfig.raw == config


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_rename_context(temp_kubeconfig, cls):
    config = await cls(temp_kubeconfig)
    context = config.current_context
    new_context = f"{context}-new"
    assert context in [c["name"] for c in config.contexts]
    await config.rename_context(context, new_context)
    # Load again from disk to ensure the change was saved
    config = await cls(temp_kubeconfig)
    assert new_context in [c["name"] for c in config.contexts]
    assert context not in [c["name"] for c in config.contexts]
    assert config.current_context == new_context
    await config.rename_context(new_context, context)
    assert new_context not in [c["name"] for c in config.contexts]
    assert context in [c["name"] for c in config.contexts]
    assert config.current_context == context
    with pytest.raises(ValueError):
        await config.rename_context("foobar", new_context)


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_get_context(temp_kubeconfig, cls):
    config = await cls(temp_kubeconfig)
    context = config.current_context
    assert "cluster" in config.get_context(context)
    with pytest.raises(ValueError):
        config.get_context("foobar")
    with pytest.raises(ValueError):
        config.get_context("")


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_get_cluster(temp_kubeconfig, cls):
    config = await cls(temp_kubeconfig)
    context = config.get_context(config.current_context)
    assert "server" in config.get_cluster(context["cluster"])
    with pytest.raises(ValueError):
        config.get_cluster("foobar")
    with pytest.raises(ValueError):
        config.get_cluster("")


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_get_user(temp_kubeconfig, cls):
    config = await cls(temp_kubeconfig)
    context = config.get_context(config.current_context)
    assert config.get_user(context["user"])
    with pytest.raises(ValueError):
        config.get_user("foobar")
    with pytest.raises(ValueError):
        config.get_user("")


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_use_namespace(temp_kubeconfig, cls):
    config = await cls(temp_kubeconfig)
    current_namespace = config.current_namespace
    await config.use_namespace("default")
    assert config.current_namespace == "default"
    await config.use_namespace("kube-system")
    assert config.current_namespace == "kube-system"
    await config.use_namespace(current_namespace)
