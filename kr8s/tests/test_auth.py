# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

import kr8s
from kr8s._testutils import set_env

HERE = Path(__file__).parent.resolve()


@pytest.fixture
async def kubeconfig_with_exec(k8s_cluster):
    # Open kubeconfig and extract the certificates
    kubeconfig = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
    user = kubeconfig["users"][0]["user"]

    # Create exec command that produces the certificates
    with set_env(
        KUBE_CLIENT_CERTIFICATE_DATA=user["client-certificate-data"],
        KUBE_CLIENT_KEY_DATA=user["client-key-data"],
    ):
        kubeconfig["users"][0]["user"] = {
            "exec": {
                "apiVersion": "client.authentication.k8s.io/v1beta1",
                "command": sys.executable,
                "args": [str(HERE / "scripts" / "envexec.py")],
            }
        }
        with tempfile.NamedTemporaryFile() as f:
            f.write(yaml.safe_dump(kubeconfig).encode())
            f.flush()
            yield f.name


@pytest.fixture
async def kubeconfig_with_token(k8s_cluster, k8s_token):
    # Open kubeconfig and extract the certificates
    kubeconfig = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
    kubeconfig["users"][0]["user"] = {"token": k8s_token}
    with tempfile.NamedTemporaryFile() as f:
        f.write(yaml.safe_dump(kubeconfig).encode())
        f.flush()
        yield f.name


@pytest.fixture
async def kubeconfig_with_second_context(k8s_cluster):
    # Open kubeconfig and extract the certificates
    kubeconfig = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
    kubeconfig["contexts"].append(
        {"context": kubeconfig["contexts"][0]["context"], "name": "foo-context"}
    )
    with tempfile.NamedTemporaryFile() as f:
        f.write(yaml.safe_dump(kubeconfig).encode())
        f.flush()
        yield f.name, kubeconfig["contexts"][1]["name"]


async def test_kubeconfig(k8s_cluster):
    kubernetes = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    version = await kubernetes.version()
    assert "major" in version
    assert await kubernetes.whoami() == "kubernetes-admin"


async def test_kubeconfig_context(kubeconfig_with_second_context):
    kubeconfig_path, context_name = kubeconfig_with_second_context
    client = await kr8s.asyncio.api(kubeconfig=kubeconfig_path, context=context_name)
    assert client.auth.active_context == context_name
    version = await client.version()
    assert "major" in version


async def test_default_service_account(k8s_cluster):
    kubernetes = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    assert (
        str(kubernetes.auth._serviceaccount)
        == "/var/run/secrets/kubernetes.io/serviceaccount"
    )


async def test_reauthenticate(k8s_cluster):
    kubernetes = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    await kubernetes.reauthenticate()
    version = await kubernetes.version()
    assert "major" in version


def test_reauthenticate_sync(k8s_cluster):
    client = kr8s.api(kubeconfig=k8s_cluster.kubeconfig_path)
    client.reauthenticate()
    version = client.version()
    assert "major" in version


async def test_bad_auth(serviceaccount):
    (Path(serviceaccount) / "token").write_text("abc123")
    kubernetes = await kr8s.asyncio.api(
        serviceaccount=serviceaccount, kubeconfig="/no/file/here"
    )
    serviceaccount = Path(serviceaccount)
    with pytest.raises(kr8s.ServerError, match="Unauthorized"):
        await kubernetes.version()


async def test_url(kubectl_proxy):
    kubernetes = await kr8s.asyncio.api(url=kubectl_proxy)
    version = await kubernetes.version()
    assert "major" in version


def test_no_config():
    with pytest.raises(ValueError):
        kr8s.api(kubeconfig="/no/file/here")


async def test_service_account(serviceaccount):
    kubernetes = await kr8s.asyncio.api(
        serviceaccount=serviceaccount, kubeconfig="/no/file/here"
    )
    await kubernetes.version()

    serviceaccount = Path(serviceaccount)
    assert kubernetes.auth.server
    assert kubernetes.auth.token == (serviceaccount / "token").read_text()
    assert str(serviceaccount) in kubernetes.auth.server_ca_file
    assert "BEGIN CERTIFICATE" in Path(kubernetes.auth.server_ca_file).read_text()
    assert kubernetes.auth.namespace == (serviceaccount / "namespace").read_text()


async def test_exec(kubeconfig_with_exec):
    kubernetes = await kr8s.asyncio.api(kubeconfig=kubeconfig_with_exec)
    version = await kubernetes.version()
    assert "major" in version


async def test_token(kubeconfig_with_token):
    kubernetes = await kr8s.asyncio.api(kubeconfig=kubeconfig_with_token)
    assert await kubernetes.whoami() == "system:serviceaccount:default:pytest"
    version = await kubernetes.version()
    assert "major" in version
