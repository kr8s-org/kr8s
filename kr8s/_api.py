# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import ssl
from typing import List, Tuple, Union

import aiohttp
import asyncio_atexit

from ._auth import KubeAuth

ALL = "all"


class Kr8sApi:
    """A kr8s object for interacting with the Kubernetes API"""

    def __init__(
        self, url=None, kubeconfig=None, serviceaccount=None, namespace=None
    ) -> None:
        self._url = url
        self._kubeconfig = kubeconfig
        self._serviceaccount = serviceaccount
        self._sslcontext = None
        self._session = None
        self.auth = KubeAuth(
            url=self._url,
            kubeconfig=self._kubeconfig,
            serviceaccount=self._serviceaccount,
            namespace=namespace,
        )

    async def _create_session(self):
        headers = {"User-Agent": self.__version__, "content-type": "application/json"}
        self._sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        if self.auth.client_key_file:
            self._sslcontext.load_cert_chain(
                certfile=self.auth.client_cert_file,
                keyfile=self.auth.client_key_file,
                password=None,
            )

        if self.auth.server_ca_file:
            self._sslcontext.load_verify_locations(cafile=self.auth.server_ca_file)
        if self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        userauth = None
        if self.auth.username and self.auth.password:
            userauth = aiohttp.BasicAuth(self.auth.username, self.auth.password)
        if self._session:
            asyncio_atexit.unregister(self._session.close)
            await self._session.close()
            self._session = None
        self._session = aiohttp.ClientSession(
            base_url=self.auth.server,
            headers=headers,
            auth=userauth,
        )
        asyncio_atexit.register(self._session.close)

    async def version(self) -> dict:
        """Get the Kubernetes version"""
        _, version = await self.call_api(method="GET", version="", base="/version")
        return version

    async def call_api(
        self,
        method,
        version: str = "v1",
        base: str = "",
        namespace: str = None,
        url: str = "",
        raise_for_status: bool = True,
        raw: bool = False,
        **kwargs,
    ) -> Tuple[int, Union[dict, str]]:
        """Make a Kubernetes API request."""
        if not self._session:
            await self._create_session()

        if not base:
            if version == "v1":
                base = "/api"
            elif "/" in version:
                base = "/apis"
            else:
                raise ValueError("Unknown API version, base must be specified.")
        parts = [base]
        if version:
            parts.append(version)
        if namespace is not None:
            parts.extend(["namespaces", namespace])
        parts.append(url)
        url = "/".join(parts)

        async with self._session.request(
            method=method,
            url=url,
            ssl=self._sslcontext,
            raise_for_status=raise_for_status,
            **kwargs,
        ) as response:
            # TODO catch self.auth error and reauth a couple of times before giving up
            if raw:
                return response.status, response
            if response.content_type == "application/json":
                return response.status, await response.json()
            return response.status, await response.text()

    async def get(
        self,
        kind: str,
        *names: List[str],
        namespace: str = None,
        label_selector: str = None,
        field_selector: str = None,
    ) -> dict:
        """Get a Kubernetes resource."""
        from .objects import get_class

        if not namespace:
            namespace = self.auth.namespace
        if namespace is ALL:
            namespace = ""

        params = {}
        if label_selector:
            params["labelSelector"] = label_selector
        if field_selector:
            params["fieldSelector"] = field_selector
        params = params or None
        obj_cls = get_class(kind)
        _, resourcelist = await self.call_api(
            method="GET",
            url=kind,
            namespace=namespace if obj_cls.namespaced else None,
            params=params,
        )
        if "items" in resourcelist:
            return [obj_cls(item, api=self) for item in resourcelist["items"]]

    async def api_resources(self) -> dict:
        """Get the Kubernetes API resources."""
        resources = []
        _, core_api_list = await self.call_api(method="GET", version="", base="/api")
        for version in core_api_list["versions"]:
            _, resource = await self.call_api(
                method="GET", version="", base="/api", url=version
            )
            resources.extend(
                [
                    {"version": version, **r}
                    for r in resource["resources"]
                    if "/" not in r["name"]
                ]
            )
        _, api_list = await self.call_api(method="GET", version="", base="/apis")
        for api in sorted(api_list["groups"], key=lambda d: d["name"]):
            version = api["versions"][0]["groupVersion"]
            _, resource = await self.call_api(
                method="GET", version="", base="/apis", url=version
            )
            resources.extend(
                [
                    {"version": version, **r}
                    for r in resource["resources"]
                    if "/" not in r["name"]
                ]
            )
        return resources

    @property
    def __version__(self):
        from . import __version__

        return f"kr8s/{__version__}"
