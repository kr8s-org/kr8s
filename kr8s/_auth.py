# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import base64
import json
import os

import aiofiles
import aiofiles.os
import yaml

from ._asyncio import check_output


class KubeAuth:
    """Load kubernetes auth from kubeconfig, service account, or url."""

    def __init__(
        self,
        kubeconfig=None,
        url=None,
        serviceaccount="/var/run/secrets/kubernetes.io/serviceaccount",
        namespace=None,
    ) -> None:
        self.server = None
        self.client_cert_file = None
        self.client_key_file = None
        self.server_ca_file = None
        self.token = None
        self.username = None
        self.password = None
        self.namespace = namespace
        self._context = None
        self._cluster = None
        self._user = None
        self._serviceaccount = serviceaccount
        self._kubeconfig = os.path.expanduser(
            kubeconfig or os.environ.get("KUBECONFIG", "~/.kube/config")
        )
        if url:
            self.server = url

    def __await__(self):
        async def f():
            await self.reauthenticate()
            return self

        return f().__await__()

    async def reauthenticate(self) -> None:
        """Reauthenticate with the server."""
        if self._serviceaccount and not self.server:
            await self._load_service_account()
        if self._kubeconfig is not False and not self.server:
            await self._load_kubeconfig()
        if not self.server:
            raise ValueError("Unable to find valid credentials")

    async def _load_kubeconfig(self) -> None:
        """Load kubernetes auth from kubeconfig."""
        if not await aiofiles.os.path.isfile(self._kubeconfig):
            return
        async with aiofiles.open(self._kubeconfig, mode="r") as f:
            config = yaml.safe_load(await f.read())
        if "current-context" in config:
            [self._context] = [
                c["context"]
                for c in config["contexts"]
                if c["name"] == config["current-context"]
            ]
        else:
            self.context = config["contexts"][0]["context"]

        [self._cluster] = [
            c["cluster"]
            for c in config["clusters"]
            if c["name"] == self._context["cluster"]
        ]
        [self._user] = [
            u["user"] for u in config["users"] if u["name"] == self._context["user"]
        ]

        self.server = self._cluster["server"]

        if "exec" in self._user:
            if (
                self._user["exec"]["apiVersion"]
                != "client.authentication.k8s.io/v1beta1"
            ):
                raise ValueError(
                    "Only client.authentication.k8s.io/v1beta1 is supported for exec auth"
                )
            command = self._user["exec"]["command"]
            args = self._user["exec"].get("args", [])
            env = os.environ.copy()
            env.update(
                **{e["name"]: e["value"] for e in self._user["exec"].get("env", [])}
            )
            data = json.loads(await check_output(command, *args, env=env))["status"]
            if "token" in data:
                self._user["token"] = data["token"]
            elif "clientCertificateData" in data and "clientKeyData" in data:
                self._user["client-certificate-data"] = data["clientCertificateData"]
                self._user["client-key-data"] = data["clientKeyData"]
            else:
                raise KeyError(f"Did not find credentials in {command} output.")

        if "client-key-data" in self._user:
            async with aiofiles.tempfile.NamedTemporaryFile(delete=False) as key_file:
                await key_file.write(base64.b64decode(self._user["client-key-data"]))
                await key_file.flush()
                self.client_key_file = key_file.name
        if "client-certificate-data" in self._user:
            async with aiofiles.tempfile.NamedTemporaryFile(delete=False) as cert_file:
                await cert_file.write(
                    base64.b64decode(self._user["client-certificate-data"])
                )
                await cert_file.flush()
                self.client_cert_file = cert_file.name
        if "certificate-authority-data" in self._cluster:
            async with aiofiles.tempfile.NamedTemporaryFile(delete=False) as ca_file:
                await ca_file.write(
                    base64.b64decode(self._cluster["certificate-authority-data"])
                )
                await ca_file.flush()
                self.server_ca_file = ca_file.name
        if "token" in self._user:
            self.token = self._user["token"]
        if "username" in self._user:
            self.username = self._user["username"]
        if "password" in self._user:
            self.password = self._user["password"]
        if self.namespace is None:
            self.namespace = self._context.get("namespace", "default")
        # TODO: Handle auth-provider oidc auth

    async def _load_service_account(self) -> None:
        """Load credentials from service account."""
        if not await aiofiles.os.path.isdir(self._serviceaccount):
            return
        host = os.environ["KUBERNETES_SERVICE_HOST"]
        port = os.environ["KUBERNETES_SERVICE_PORT"]
        self.server = f"https://{host}:{port}"
        async with aiofiles.open(
            os.path.join(self._serviceaccount, "token"), mode="r"
        ) as f:
            self.token = await f.read()
        self.server_ca_file = os.path.join(self._serviceaccount, "ca.crt")
        if self.namespace is None:
            async with aiofiles.open(
                os.path.join(self._serviceaccount, "namespace"), mode="r"
            ) as f:
                self.namespace = await f.read()
