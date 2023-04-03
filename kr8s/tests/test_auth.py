# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from kr8s import Kr8sApi
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


async def test_kubeconfig(k8s_cluster):
    kubernetes = Kr8sApi(kubeconfig=k8s_cluster.kubeconfig_path)
    version = await kubernetes.version()
    assert "major" in version


async def test_url(kubectl_proxy):
    kubernetes = Kr8sApi(url=kubectl_proxy)
    version = await kubernetes.version()
    assert "major" in version


async def test_no_config():
    with pytest.raises(ValueError):
        kubernetes = Kr8sApi(kubeconfig="/no/file/here")
        await kubernetes.version()


async def test_service_account(serviceaccount):
    kubernetes = Kr8sApi(serviceaccount=serviceaccount, kubeconfig="/no/file/here")
    await kubernetes.version()

    serviceaccount = Path(serviceaccount)
    assert kubernetes.auth.server
    assert kubernetes.auth.token == (serviceaccount / "token").read_text()
    assert str(serviceaccount) in kubernetes.auth.server_ca_file
    assert "BEGIN CERTIFICATE" in Path(kubernetes.auth.server_ca_file).read_text()
    assert kubernetes.auth.namespace == (serviceaccount / "namespace").read_text()


async def test_exec(kubeconfig_with_exec):
    kubernetes = Kr8sApi(kubeconfig=kubeconfig_with_exec)
    version = await kubernetes.version()
    assert "major" in version
