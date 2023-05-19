# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import contextlib
import json
import ssl
import weakref
from typing import List, Tuple

import aiohttp
import asyncio_atexit

from ._auth import KubeAuth

ALL = "all"


class Api(object):
    """A kr8s object for interacting with the Kubernetes API.

    .. warning::
        This class is not intended to be instantiated directly. Instead, use the
        :func:`kr8s.api` function to get a singleton instance of the API.

        See https://docs.kr8s.org/en/latest/client.html#client-caching.

    """

    _asyncio = True
    _instances = weakref.WeakValueDictionary()

    def __init__(self, **kwargs) -> None:
        if not kwargs.pop("bypass_factory", False):
            raise ValueError(
                "Use kr8s.api() to get an instance of Api. "
                "See https://docs.kr8s.org/en/latest/client.html#client-caching."
            )

        self._url = kwargs.get("url")
        self._kubeconfig = kwargs.get("kubeconfig")
        self._serviceaccount = kwargs.get("serviceaccount")
        self._sslcontext = None
        self._session = None
        self.auth = KubeAuth(
            url=self._url,
            kubeconfig=self._kubeconfig,
            serviceaccount=self._serviceaccount,
            namespace=kwargs.get("namespace"),
        )
        Api._instances[frozenset(kwargs.items())] = self

    def __await__(self):
        async def f():
            await self.auth
            return self

        return f().__await__()

    async def _create_session(self) -> None:
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
        async with self.call_api(method="GET", version="", base="/version") as response:
            return await response.json()

    @contextlib.asynccontextmanager
    async def call_api(
        self,
        method: str = "GET",
        version: str = "v1",
        base: str = "",
        namespace: str = None,
        url: str = "",
        raise_for_status: bool = True,
        websocket: bool = False,
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Make a Kubernetes API request."""
        if not self._session or self._session.closed:
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

        call_method = self._session.ws_connect if websocket else self._session.request
        kwargs.update(url=url, ssl=self._sslcontext)
        if not websocket:
            kwargs.update(method=method, raise_for_status=raise_for_status)

        auth_attempts = 0
        while True:
            try:
                async with call_method(**kwargs) as response:
                    yield response
            except aiohttp.ClientResponseError as e:
                if e.status in (401, 403) and auth_attempts < 3:
                    auth_attempts += 1
                    await self.auth.reauthenticate()
                    continue
                else:
                    raise
            break

    async def reauthenticate(self) -> None:
        """Reauthenticate the API."""
        await self.auth.reauthenticate()

    @contextlib.asynccontextmanager
    async def _get_kind(
        self,
        kind: str,
        namespace: str = None,
        label_selector: str = None,
        field_selector: str = None,
        params: dict = None,
        watch: bool = False,
        **kwargs,
    ) -> dict:
        """Get a Kubernetes resource."""
        from ._objects import get_class

        if not namespace:
            namespace = self.auth.namespace
        if namespace is ALL:
            namespace = ""
        if params is None:
            params = {}
        if label_selector:
            params["labelSelector"] = label_selector
        if field_selector:
            params["fieldSelector"] = field_selector
        if watch:
            params["watch"] = "true" if watch else "false"
        params = params or None
        obj_cls = get_class(kind)
        async with self.call_api(
            method="GET",
            url=kind,
            version=obj_cls.version,
            namespace=namespace if obj_cls.namespaced else None,
            params=params,
            **kwargs,
        ) as response:
            yield obj_cls, response

    async def get(
        self,
        kind: str,
        *names: List[str],
        namespace: str = None,
        label_selector: str = None,
        field_selector: str = None,
        as_object: object = None,
        **kwargs,
    ) -> List[object]:
        """Get a Kubernetes resource."""
        return await self._get(
            kind,
            *names,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
            as_object=as_object,
            **kwargs,
        )

    async def _get(
        self,
        kind: str,
        *names: List[str],
        namespace: str = None,
        label_selector: str = None,
        field_selector: str = None,
        as_object: object = None,
        **kwargs,
    ) -> List[object]:
        headers = {}
        if as_object:
            group, version = as_object.version.split("/")
            headers[
                "Accept"
            ] = f"application/json;as={as_object.kind};v={version};g={group}"
        async with self._get_kind(
            kind,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
            headers=headers or None,
            **kwargs,
        ) as (obj_cls, response):
            resourcelist = await response.json()
            if (
                as_object
                and "kind" in resourcelist
                and resourcelist["kind"] == as_object.kind
            ):
                return as_object(resourcelist, api=self)
            else:
                if "items" in resourcelist:
                    return [
                        obj_cls(item, api=self)
                        for item in resourcelist["items"]
                        if not names or item["metadata"]["name"] in names
                    ]
                return []

    async def watch(
        self,
        kind: str,
        namespace: str = None,
        label_selector: str = None,
        field_selector: str = None,
        since: str = None,
    ):
        """Watch a Kubernetes resource."""
        async for t, object in self._watch(
            kind,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
            since=since,
        ):
            yield t, object

    async def _watch(
        self,
        kind: str,
        namespace: str = None,
        label_selector: str = None,
        field_selector: str = None,
        since: str = None,
    ) -> Tuple[str, object]:
        """Watch a Kubernetes resource."""
        async with self._get_kind(
            kind,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
            params={"resourceVersion": since} if since else None,
            watch=True,
        ) as (obj_cls, response):
            async for line in response.content:
                event = json.loads(line)
                yield event["type"], obj_cls(event["object"], api=self)

    async def api_resources(self) -> dict:
        """Get the Kubernetes API resources."""
        resources = []
        async with self.call_api(method="GET", version="", base="/api") as response:
            core_api_list = await response.json()

        for version in core_api_list["versions"]:
            async with self.call_api(
                method="GET", version="", base="/api", url=version
            ) as response:
                resource = await response.json()
            resources.extend(
                [
                    {"version": version, **r}
                    for r in resource["resources"]
                    if "/" not in r["name"]
                ]
            )
        async with self.call_api(method="GET", version="", base="/apis") as response:
            api_list = await response.json()
        for api in sorted(api_list["groups"], key=lambda d: d["name"]):
            version = api["versions"][0]["groupVersion"]
            async with self.call_api(
                method="GET", version="", base="/apis", url=version
            ) as response:
                resource = await response.json()
            resources.extend(
                [
                    {"version": version, **r}
                    for r in resource["resources"]
                    if "/" not in r["name"]
                ]
            )
        return resources

    @property
    def __version__(self) -> str:
        from . import __version__

        return f"kr8s/{__version__}"
