# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import base64
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

import kr8s
from kr8s._config import KubeConfig
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
async def kubeconfig_with_decoded_certs(k8s_cluster):
    kubeconfig = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
    kubeconfig["clusters"][0]["cluster"]["certificate-authority-data"] = (
        base64.b64decode(
            kubeconfig["clusters"][0]["cluster"]["certificate-authority-data"]
        )
    ).decode()
    kubeconfig["users"][0]["user"]["client-certificate-data"] = (
        base64.b64decode(kubeconfig["users"][0]["user"]["client-certificate-data"])
    ).decode()
    kubeconfig["users"][0]["user"]["client-key-data"] = (
        base64.b64decode(kubeconfig["users"][0]["user"]["client-key-data"])
    ).decode()
    with tempfile.NamedTemporaryFile() as f:
        f.write(yaml.safe_dump(kubeconfig).encode())
        f.flush()
        yield f.name


@pytest.fixture
async def kubeconfig_with_line_breaks_in_certs(k8s_cluster):
    def insert_every(instring: str, substring: str, interval: int) -> str:
        """Insert a substring every interval characters in instring.

        Example:
            >>> insert_every("abcdefghi", ".", 3)
            "abc.def.ghi"
        """
        return substring.join(
            instring[i : i + interval] for i in range(0, len(instring), interval)
        )

    kubeconfig = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
    kubeconfig["clusters"][0]["cluster"]["certificate-authority-data"] = insert_every(
        kubeconfig["clusters"][0]["cluster"]["certificate-authority-data"], "\n", 64
    )
    kubeconfig["users"][0]["user"]["client-certificate-data"] = insert_every(
        kubeconfig["users"][0]["user"]["client-certificate-data"], "\n", 64
    )
    kubeconfig["users"][0]["user"]["client-key-data"] = insert_every(
        kubeconfig["users"][0]["user"]["client-key-data"], "\n", 64
    )
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


@pytest.fixture
async def kubeconfig_with_certs_on_disk(k8s_cluster):
    @contextmanager
    def f(absolute=True):
        # Open kubeconfig and dump certs to disk, then write new kubeconfig with paths to certs
        kubeconfig = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
        user = kubeconfig["users"][0]["user"]
        ca = kubeconfig["clusters"][0]["cluster"].pop("certificate-authority-data")
        with tempfile.TemporaryDirectory() as d:
            kubeconfig["users"][0]["user"] = {
                "client-certificate": f"{d}/client.crt" if absolute else "client.crt",
                "client-key": f"{d}/client.key" if absolute else "client.key",
            }
            kubeconfig["clusters"][0]["cluster"]["certificate-authority"] = (
                f"{d}/ca.crt" if absolute else "ca.crt"
            )
            with open(f"{d}/client.crt", "wb") as f:
                f.write(base64.b64decode(user["client-certificate-data"]))
            with open(f"{d}/client.key", "wb") as f:
                f.write(base64.b64decode(user["client-key-data"]))
            with open(f"{d}/ca.crt", "wb") as f:
                f.write(base64.b64decode(ca))
            with open(f"{d}/config", "wb") as f:
                f.write(yaml.safe_dump(kubeconfig).encode())
                f.flush()
            yield f"{d}/config"

    return f


async def test_kubeconfig(k8s_cluster):
    api = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    assert await api.get("pods", namespace=kr8s.ALL)
    assert await api.whoami() == "kubernetes-admin"


async def test_kubeconfig_multi_paths_same(k8s_cluster):
    kubeconfig_multi_str = (
        f"{k8s_cluster.kubeconfig_path}:{k8s_cluster.kubeconfig_path}"
    )
    api = await kr8s.asyncio.api(kubeconfig=kubeconfig_multi_str)
    assert await api.get("pods", namespace=kr8s.ALL)
    assert await api.whoami() == "kubernetes-admin"


async def test_kubeconfig_multi_paths_diff(k8s_cluster, tmp_path):
    kubeconfig1 = k8s_cluster.kubeconfig_path
    kubeconfig2 = Path(tmp_path / "kubeconfig").write_bytes(kubeconfig1.read_bytes())
    kubeconfig_multi_str = f"{kubeconfig1}:{kubeconfig2}"
    api = await kr8s.asyncio.api(kubeconfig=kubeconfig_multi_str)
    assert await api.get("pods", namespace=kr8s.ALL)
    assert await api.whoami() == "kubernetes-admin"


async def test_kubeconfig_dict(k8s_cluster):
    config = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
    assert isinstance(config, dict)
    api = await kr8s.asyncio.api(kubeconfig=config)
    assert await api.get("pods", namespace=kr8s.ALL)
    assert await api.whoami() == "kubernetes-admin"


def test_kubeconfig_dict_sync(k8s_cluster):
    config = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
    assert isinstance(config, dict)
    api = kr8s.api(kubeconfig=config)
    assert api.get("pods", namespace=kr8s.ALL)
    assert api.whoami() == "kubernetes-admin"


async def test_kubeconfig_context(kubeconfig_with_second_context):
    kubeconfig_path, context_name = kubeconfig_with_second_context
    api = await kr8s.asyncio.api(kubeconfig=kubeconfig_path, context=context_name)
    assert api.auth.active_context == context_name
    assert await api.get("pods", namespace=kr8s.ALL)


async def test_default_service_account(k8s_cluster):
    api = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    assert (
        str(api.auth._serviceaccount) == "/var/run/secrets/kubernetes.io/serviceaccount"
    )


async def test_reauthenticate(k8s_cluster):
    api = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    await api.reauthenticate()
    assert await api.get("pods", namespace=kr8s.ALL)


def test_reauthenticate_sync(k8s_cluster):
    api = kr8s.api(kubeconfig=k8s_cluster.kubeconfig_path)
    api.reauthenticate()
    assert api.get("pods", namespace=kr8s.ALL)


async def test_bad_auth(serviceaccount):
    (Path(serviceaccount) / "token").write_text("abc123")
    api = await kr8s.asyncio.api(
        serviceaccount=serviceaccount, kubeconfig="/no/file/here"
    )
    serviceaccount = Path(serviceaccount)
    with pytest.raises(kr8s.ServerError, match="Unauthorized"):
        await api.version()


async def test_url(kubectl_proxy):
    api = await kr8s.asyncio.api(url=kubectl_proxy)
    assert await api.get("pods", namespace="kube-system")
    assert api.auth.server == kubectl_proxy

    # Ensure reauthentication works
    api.auth.server = None
    await api.reauthenticate()
    assert await api.get("pods", namespace="kube-system")
    assert api.auth.server == kubectl_proxy


def test_no_config():
    with pytest.raises(ValueError):
        kr8s.api(kubeconfig="/no/file/here")


def test_kubeconfig_isdir_fail(tmp_path):
    with pytest.raises(IsADirectoryError):
        kr8s.api(kubeconfig=tmp_path)


async def test_service_account(serviceaccount):
    api = await kr8s.asyncio.api(
        serviceaccount=serviceaccount, kubeconfig="/no/file/here"
    )
    await api.version()

    serviceaccount = Path(serviceaccount)
    assert api.auth.server
    assert api.auth.token == (serviceaccount / "token").read_text()
    assert str(serviceaccount) in api.auth.server_ca_file
    assert "BEGIN CERTIFICATE" in Path(api.auth.server_ca_file).read_text()
    assert api.auth.namespace == (serviceaccount / "namespace").read_text()


async def test_service_account_with_kubeconfig_namespace(serviceaccount):
    kubeconfig = await KubeConfig(
        {
            "apiVersion": "v1",
            "clusters": None,
            "contexts": [
                {
                    "context": {"cluster": "", "namespace": "bar", "user": ""},
                    "name": "foo",
                }
            ],
            "current-context": "foo",
            "kind": "Config",
            "preferences": {},
            "users": None,
        }
    )
    kubeconfig_path = str(Path(serviceaccount) / "kubeconfig")
    await kubeconfig.save(path=kubeconfig_path)
    api = await kr8s.asyncio.api(
        serviceaccount=serviceaccount, kubeconfig=kubeconfig_path
    )

    assert api.auth.server
    assert api.namespace == "bar"


async def test_exec(kubeconfig_with_exec):
    api = await kr8s.asyncio.api(kubeconfig=kubeconfig_with_exec)
    assert await api.get("pods", namespace=kr8s.ALL)
    assert api.auth.server
    assert api.auth.server_ca_file

    # Test reauthentication
    api.auth.server = None
    api.auth.server_ca_file = None
    await api.reauthenticate()
    assert api.auth.server
    assert api.auth.server_ca_file


async def test_token(kubeconfig_with_token):
    api = await kr8s.asyncio.api(kubeconfig=kubeconfig_with_token)
    assert await api.whoami() == "system:serviceaccount:default:pytest"
    assert await api.get("pods", namespace=kr8s.ALL)


@pytest.mark.parametrize("absolute", [True, False])
async def test_certs_on_disk(kubeconfig_with_certs_on_disk, absolute):
    with kubeconfig_with_certs_on_disk(absolute=absolute) as kubeconfig:
        api = await kr8s.asyncio.api(kubeconfig=kubeconfig)
        assert await api.get("pods", namespace=kr8s.ALL)


async def test_certs_not_encoded(kubeconfig_with_decoded_certs):
    api = await kr8s.asyncio.api(kubeconfig=kubeconfig_with_decoded_certs)
    assert await api.get("pods", namespace=kr8s.ALL)


async def test_certs_with_encoded_line_breaks(kubeconfig_with_line_breaks_in_certs):
    api = await kr8s.asyncio.api(kubeconfig=kubeconfig_with_line_breaks_in_certs)
    assert await api.get("pods", namespace=kr8s.ALL)
