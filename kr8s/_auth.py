# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import base64
import json
import os
import pathlib
import ssl
from typing import Optional, Union

import anyio

from ._async_utils import NamedTemporaryFile, check_output
from ._config import KubeConfigSet
from ._types import PathType


class KubeAuth:
    """Load kubernetes auth from kubeconfig, service account, or url."""

    def __init__(
        self,
        kubeconfig: Optional[PathType] = None,
        url: Optional[str] = None,
        serviceaccount: Optional[str] = None,
        namespace: Optional[str] = None,
        context: Optional[str] = None,
    ) -> None:
        self.server: str = ""
        self.client_cert_file: Optional[PathType] = None
        self.client_key_file: Optional[PathType] = None
        self.server_ca_file: Optional[PathType] = None
        self.token: Optional[str] = None
        self._namespace: Optional[str] = namespace
        self.active_context: str = ""
        self.kubeconfig: KubeConfigSet
        self.tls_server_name: Optional[str] = None
        self._url: str = ""
        if url:
            self._url = url
        self._insecure_skip_tls_verify: bool = False
        self._use_context: Optional[str] = context
        self._context: dict = {}
        self._cluster: dict = {}
        self._user: dict = {}
        self._serviceaccount: str = (
            serviceaccount
            if serviceaccount is not None
            else "/var/run/secrets/kubernetes.io/serviceaccount"
        )
        self._kubeconfig_path_or_dict: Union[dict, PathType]
        if kubeconfig:
            self._kubeconfig_path_or_dict = kubeconfig
        else:
            self._kubeconfig_path_or_dict = os.environ.get(
                "KUBECONFIG", "~/.kube/config"
            )

        self.__auth_lock: anyio.Lock = anyio.Lock()

    def __await__(self):
        async def f():
            await self.reauthenticate()
            return self

        return f().__await__()

    async def reauthenticate(self) -> None:
        """Reauthenticate with the server."""
        async with self.__auth_lock:
            if self._url:
                self.server = self._url
            else:
                if self._kubeconfig_path_or_dict is not False:
                    await self._load_kubeconfig()
                if self._serviceaccount and not self.server:
                    await self._load_service_account()
            if not self.server:
                raise ValueError("Unable to find valid credentials")

    async def ssl_context(self):
        if self._insecure_skip_tls_verify:
            return False
        async with self.__auth_lock:
            if (
                not self.client_key_file
                and not self.client_cert_file
                and not self.server_ca_file
            ):
                # If no cert information is provided, fall back to default verification
                return True
            sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if self.client_key_file and self.client_cert_file:
                sslcontext.load_cert_chain(
                    certfile=self.client_cert_file,
                    keyfile=self.client_key_file,
                    password=None,
                )
            if self.server_ca_file:
                sslcontext.load_verify_locations(cafile=self.server_ca_file)
            return sslcontext

    @property
    def namespace(self) -> str:
        return self._namespace if self._namespace else "default"

    @namespace.setter
    def namespace(self, value: str):
        self._namespace = value

    async def _load_kubeconfig(self) -> None:
        """Load kubernetes auth from kubeconfig."""
        if isinstance(self._kubeconfig_path_or_dict, str) or isinstance(
            self._kubeconfig_path_or_dict, pathlib.Path
        ):
            try:
                if os.name != "nt":
                    self.kubeconfig = await KubeConfigSet(
                        *str(self._kubeconfig_path_or_dict).split(":")
                    )
                else:
                    # Windows doesn't support multiple configs in a path
                    self.kubeconfig = await KubeConfigSet(self._kubeconfig_path_or_dict)
            except ValueError:
                return
        else:
            self.kubeconfig = await KubeConfigSet(self._kubeconfig_path_or_dict)
        if self._use_context:
            try:
                self._context = self.kubeconfig.get_context(self._use_context)
                self.active_context = self._use_context
            except ValueError as e:
                raise ValueError(f"No such context {self._use_context}") from e
        elif self.kubeconfig.current_context:
            self._context = self.kubeconfig.get_context(self.kubeconfig.current_context)
            self.active_context = self.kubeconfig.current_context
        else:
            self._context = self.kubeconfig.contexts[0]["context"]
            self.active_context = self.kubeconfig.contexts[0]["name"]

        # Load configuration options from the context
        if self._namespace is None:
            self._namespace = self.kubeconfig.current_namespace

        # If no cluster is found in the context, assume it's a service account
        if not self._context["cluster"]:
            return

        self._cluster = self.kubeconfig.get_cluster(self._context["cluster"])
        self._user = self.kubeconfig.get_user(self._context["user"])
        self.server = self._cluster["server"]

        if (
            "insecure-skip-tls-verify" in self._cluster
            and self._cluster["insecure-skip-tls-verify"]
        ):
            self._insecure_skip_tls_verify = True

        if "tls-server-name" in self._cluster:
            self.tls_server_name = self._cluster["tls-server-name"]

        if "exec" in self._user:
            if (
                self._user["exec"]["apiVersion"]
                == "client.authentication.k8s.io/v1alpha1"
            ):
                raise ValueError(
                    "client.authentication.k8s.io/v1alpha1 is not supported for exec auth"
                )
            command = self._user["exec"]["command"]
            args = self._user["exec"].get("args") or []
            env = os.environ.copy()
            env.update(
                **{e["name"]: e["value"] for e in self._user["exec"].get("env") or []}
            )
            data = json.loads(await check_output(command, *args, env=env))["status"]
            if "token" in data:
                self._user["token"] = data["token"]
            elif "clientCertificateData" in data and "clientKeyData" in data:
                self._user["client-certificate-data"] = data["clientCertificateData"]
                self._user["client-key-data"] = data["clientKeyData"]
            else:
                raise KeyError(f"Did not find credentials in {command} output.")

        if "client-key" in self._user:
            client_key_path = anyio.Path(self._user["client-key"])
            if await client_key_path.exists():
                self.client_key_file = self._user["client-key"]
            else:
                self.client_key_file = (
                    anyio.Path(self.kubeconfig.get_path(self._use_context)).parent
                    / client_key_path
                )
        if "client-key-data" in self._user:
            async with NamedTemporaryFile(delete=False) as key_file:
                if "-----" in self._user["client-key-data"]:
                    key_data = self._user["client-key-data"].encode()
                else:
                    key_data = base64.b64decode(self._user["client-key-data"])
                await key_file.write_bytes(key_data)
                self.client_key_file = str(key_file)
        if "client-certificate" in self._user:
            client_cert_path = anyio.Path(self._user["client-certificate"])
            if await client_cert_path.exists():
                self.client_cert_file = self._user["client-certificate"]
            else:
                self.client_cert_file = (
                    anyio.Path(self.kubeconfig.get_path(self._use_context)).parent
                    / client_cert_path
                )
        if "client-certificate-data" in self._user:
            async with NamedTemporaryFile(delete=False) as cert_file:
                if "-----" in self._user["client-certificate-data"]:
                    cert_data = self._user["client-certificate-data"].encode()
                else:
                    cert_data = base64.b64decode(self._user["client-certificate-data"])
                await cert_file.write_bytes(cert_data)
                self.client_cert_file = str(cert_file)
        if "certificate-authority" in self._cluster:
            server_ca_path = anyio.Path(self._cluster["certificate-authority"])
            if await server_ca_path.exists():
                self.server_ca_file = self._cluster["certificate-authority"]
            else:
                self.server_ca_file = (
                    anyio.Path(self.kubeconfig.get_path(self._use_context)).parent
                    / server_ca_path
                )
        if "certificate-authority-data" in self._cluster:
            async with NamedTemporaryFile(delete=False) as ca_file:
                if "-----" in self._cluster["certificate-authority-data"]:
                    ca_data = self._cluster["certificate-authority-data"].encode()
                else:
                    ca_data = base64.b64decode(
                        self._cluster["certificate-authority-data"]
                    )

                await ca_file.write_bytes(ca_data)
                self.server_ca_file = str(ca_file)
        if "token" in self._user:
            self.token = self._user["token"]
        if "username" in self._user or "password" in self._user:
            raise ValueError(
                "username/password authentication was removed in Kubernetes 1.19, "
                "kr8s doesn't not support this Kubernetes version"
            )
        if "auth-provider" in self._user:
            if p := self._user["auth-provider"]["name"] != "oidc":
                raise ValueError(
                    f"auth-provider {p} was deprecated in Kubernetes 1.21 "
                    "and is not supported by kr8s"
                )
            # TODO: Handle refreshing OIDC token if missing or expired
            self.token = self._user["auth-provider"]["config"]["id-token"]

    async def _load_service_account(self) -> None:
        """Load credentials from service account."""
        self._serviceaccount = os.path.expanduser(self._serviceaccount)
        if not os.path.isdir(self._serviceaccount):
            return
        host = os.environ["KUBERNETES_SERVICE_HOST"]
        port = os.environ["KUBERNETES_SERVICE_PORT"]
        self.server = f"https://{host}:{port}"
        async with await anyio.open_file(
            os.path.join(self._serviceaccount, "token")
        ) as f:
            self.token = await f.read()
        self.server_ca_file = os.path.join(self._serviceaccount, "ca.crt")
        if self.namespace is None:
            async with await anyio.open_file(
                os.path.join(self._serviceaccount, "namespace")
            ) as f:
                self.namespace = await f.read()
