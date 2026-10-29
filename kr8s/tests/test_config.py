# SPDX-FileCopyrightText: Copyright (c) 2024-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import os
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import httpx
import pytest
import yaml
from jsonpath import JSONPointerKeyError

import kr8s
import kr8s.asyncio
from kr8s._config import KubeConfig, KubeConfigSet


def config_with_entries(section, entries):
    return {
        "apiVersion": "v1",
        "kind": "Config",
        "current-context": "shared",
        "clusters": [],
        "users": [],
        "contexts": [],
        section: entries,
    }


@pytest.mark.parametrize(
    "section,value_key,first_value,later_value",
    [
        (
            "clusters",
            "cluster",
            {"server": "https://first.invalid"},
            {"server": "https://second.invalid", "insecure-skip-tls-verify": True},
        ),
        (
            "users",
            "user",
            {"token": "test-only-first"},
            {"token": "test-only-second", "username": "later-user"},
        ),
        (
            "contexts",
            "context",
            {"cluster": "first", "user": "first"},
            {"cluster": "second", "user": "second", "namespace": "later"},
        ),
    ],
)
async def test_kubeconfigset_first_named_definition_wins(
    section, value_key, first_value, later_value
):
    first = config_with_entries(section, [{"name": "shared", value_key: first_value}])
    later = config_with_entries(section, [{"name": "shared", value_key: later_value}])
    originals = deepcopy((first, later))

    config = await KubeConfigSet(first, later)

    assert getattr(config, section) == first[section]
    assert (first, later) == originals


@pytest.mark.parametrize(
    "section,value_key",
    [("clusters", "cluster"), ("users", "user"), ("contexts", "context")],
)
async def test_kubeconfigset_named_entry_order(section, value_key):
    shared = {"name": "shared", value_key: {}}
    first_only = {"name": "first-only", value_key: {}}
    last_only = {"name": "last-only", value_key: {}}
    first = config_with_entries(section, [shared, first_only])
    later = config_with_entries(section, [shared, last_only])

    config = await KubeConfigSet(first, later)

    assert getattr(config, section) == [shared, first_only, last_only]


@pytest.mark.parametrize(
    "section,value_key",
    [("clusters", "cluster"), ("users", "user"), ("contexts", "context")],
)
async def test_kubeconfigset_null_section(section, value_key):
    entries = [{"name": "later", value_key: {}}]
    config = await KubeConfigSet(
        config_with_entries(section, None), config_with_entries(section, entries)
    )

    assert getattr(config, section) == entries


@pytest.mark.skipif(
    os.name == "nt", reason="Multiple kubeconfig paths are not supported on Windows"
)
@pytest.mark.parametrize("asynchronous", [False, True])
async def test_kubeconfigset_api_uses_first_file(tmp_path, asynchronous):
    paths = []
    for label in ("first", "second"):
        data = {
            "apiVersion": "v1",
            "kind": "Config",
            "current-context": "shared",
            "clusters": [
                {"name": "shared", "cluster": {"server": f"https://{label}.invalid"}}
            ],
            "users": [{"name": "shared", "user": {"token": f"test-only-{label}"}}],
            "contexts": [
                {
                    "name": "shared",
                    "context": {
                        "cluster": "shared",
                        "user": "shared",
                        "namespace": label,
                    },
                }
            ],
        }
        path = tmp_path / f"{label}.yaml"
        path.write_text(yaml.safe_dump(data))
        paths.append(str(path))

    requests = []

    def handle_request(request):
        requests.append(request)
        return httpx.Response(200, json={"gitVersion": "v1.34.0"})

    original_client = httpx.AsyncClient

    def offline_client(*args, **kwargs):
        return original_client(
            *args, transport=httpx.MockTransport(handle_request), **kwargs
        )

    with patch.object(httpx, "AsyncClient", side_effect=offline_client):
        if asynchronous:
            client = await kr8s.asyncio.api(kubeconfig=os.pathsep.join(paths))
            await client.version()
        else:
            client = kr8s.api(kubeconfig=os.pathsep.join(paths))
            client.version()
    try:
        assert client.auth.server == "https://first.invalid"
        assert client.namespace == "first"
        assert client.auth.token == "test-only-first"
        assert requests
        assert all(request.url.host == "first.invalid" for request in requests)
        assert all(
            request.headers["Authorization"] == "Bearer test-only-first"
            for request in requests
        )
    finally:
        if client._session is not None:
            await client._session.aclose()


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
    assert kubeconfig.raw["clusters"] == config["clusters"]
    assert kubeconfig.raw["users"] == config["users"]
    assert kubeconfig.raw["contexts"] == config["contexts"]
    # Preferences and extensions are optional
    assert kubeconfig.raw.get("preferences", {}) == config.get("preferences", {})
    assert kubeconfig.raw.get("extensions", []) == config.get("extensions", [])


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


async def test_kubeconfigset_multi_paths(temp_kubeconfig, tmp_path):
    kubeconfig1 = Path(temp_kubeconfig)
    kubeconfig2 = Path(tmp_path / "kubeconfig")
    kubeconfig2.write_bytes(kubeconfig1.read_bytes())
    config = await KubeConfigSet(kubeconfig1, kubeconfig2)
    context = config.get_context(config.current_context)
    assert config.get_user(context["user"])


async def test_kubeconfigset_multi_paths_one_empty(temp_kubeconfig):
    config = await KubeConfigSet(temp_kubeconfig, "")
    context = config.get_context(config.current_context)
    assert config.get_user(context["user"])


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_kubeconfig_path_empty_fail(cls):
    with pytest.raises(ValueError):
        await cls("")


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_kubeconfig_path_isdir_fail(cls, tmp_path):
    with pytest.raises(IsADirectoryError):
        await cls(tmp_path)


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_get(temp_kubeconfig, cls):
    config = await cls(temp_kubeconfig)
    assert isinstance(config.get(path="contexts"), list)
    assert isinstance(config.get(pointer="/contexts/0/name"), str)
    assert isinstance(config.get(path="contexts[*].name"), list)


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_set(temp_kubeconfig, cls):
    config = await cls(temp_kubeconfig)
    first_context = config.get(pointer="/contexts/0/name")

    await config.set(pointer="/contexts/0/name", value="foo")
    assert config.get(pointer="/contexts/0/name") == "foo"
    assert config.get(path="contexts[0].name")[0] == "foo"

    await config.set(pointer="/contexts/0/name", value=first_context)
    assert config.get(pointer="/contexts/0/name") == first_context


@pytest.mark.parametrize("cls", [KubeConfig, KubeConfigSet])
async def test_unset(temp_kubeconfig, cls):
    config = await cls(temp_kubeconfig)
    with pytest.raises(JSONPointerKeyError):
        config.get(pointer="/contexts/0/context/foo")
    await config.set(pointer="/contexts/0/context/foo", value="bar")
    assert config.get(pointer="/contexts/0/context/foo") == "bar"
    await config.unset(pointer="/contexts/0/context/foo")
    with pytest.raises(JSONPointerKeyError):
        config.get(pointer="/contexts/0/context/foo")
