# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import contextlib
import json
import ssl
import threading
import warnings
import weakref
from typing import Dict, List, Tuple, Union

import aiohttp
import httpx
from cryptography import x509

from ._auth import KubeAuth
from ._data_utils import dict_to_selector
from ._exceptions import APITimeoutError, ServerError

ALL = "all"


class Api(object):
    """A kr8s object for interacting with the Kubernetes API.

    .. warning::
        This class is not intended to be instantiated directly. Instead, use the
        :func:`kr8s.api` function to get a singleton instance of the API.

        See https://docs.kr8s.org/en/stable/client.html#client-caching.

    """

    _asyncio = True
    _instances = {}

    def __init__(self, **kwargs) -> None:
        if not kwargs.pop("bypass_factory", False):
            raise ValueError(
                "Use kr8s.api() to get an instance of Api. "
                "See https://docs.kr8s.org/en/stable/client.html#client-caching."
            )

        self._url = kwargs.get("url")
        self._kubeconfig = kwargs.get("kubeconfig")
        self._serviceaccount = kwargs.get("serviceaccount")
        self._session = None
        self.auth = KubeAuth(
            url=self._url,
            kubeconfig=self._kubeconfig,
            serviceaccount=self._serviceaccount,
            namespace=kwargs.get("namespace"),
            context=kwargs.get("context"),
        )
        thread_id = threading.get_ident()
        if thread_id not in Api._instances:
            Api._instances[thread_id] = weakref.WeakValueDictionary()
        Api._instances[thread_id][frozenset(kwargs.items())] = self

    def __await__(self):
        async def f():
            await self.auth
            return self

        return f().__await__()

    async def _create_session(self) -> None:
        headers = {"User-Agent": self.__version__, "content-type": "application/json"}
        if self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        if self._session:
            with contextlib.suppress(RuntimeError):
                await self._session.aclose()
            self._session = None
        userauth = None
        if self.auth.username and self.auth.password:
            userauth = httpx.BasicAuth(self.auth.username, self.auth.password)
        self._session = httpx.AsyncClient(
            base_url=self.auth.server,
            headers=headers,
            auth=userauth,
            verify=await self.auth.ssl_context(),
        )

    def _construct_url(
        self,
        version: str = "v1",
        base: str = "",
        namespace: str = None,
        url: str = "",
    ) -> str:
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
        return "/".join(parts)

    @contextlib.asynccontextmanager
    async def call_api(
        self,
        method: str = "GET",
        version: str = "v1",
        base: str = "",
        namespace: str = None,
        url: str = "",
        raise_for_status: bool = True,
        stream: bool = False,
        **kwargs,
    ) -> httpx.Response:
        """Make a Kubernetes API request."""
        if not self._session or self._session.is_closed:
            await self._create_session()
        url = self._construct_url(version, base, namespace, url)
        kwargs.update(url=url, method=method)
        auth_attempts = 0
        ssl_attempts = 0
        while True:
            try:
                if stream:
                    async with self._session.stream(**kwargs) as response:
                        if raise_for_status:
                            response.raise_for_status()
                        yield response
                else:
                    response = await self._session.request(**kwargs)
                    if raise_for_status:
                        response.raise_for_status()
                    yield response
            except httpx.HTTPStatusError as e:
                # If we get a 401 or 403 our credentials may have expired so we
                # reauthenticate and try again a few times before giving up.
                if e.response.status_code in (401, 403) and auth_attempts < 3:
                    auth_attempts += 1
                    await self.auth.reauthenticate()
                    await self._create_session()
                    continue
                else:
                    if e.response.status_code >= 400 and e.response.status_code < 500:
                        error = e.response.json()
                        raise ServerError(
                            error["message"], status=error, response=e.response
                        ) from e
                    elif e.response.status_code >= 500:
                        raise ServerError(
                            str(e), status=e.response.status_code, response=e.response
                        ) from e
                    raise
            except ssl.SSLCertVerificationError:
                # In some rare edge cases the SSL verification fails, so we try again
                # a few times before giving up.
                if ssl_attempts < 3:
                    ssl_attempts += 1
                    await self.auth.reauthenticate()
                    await self._create_session()
                    continue
                else:
                    raise
            except httpx.ReadTimeout as e:
                raise APITimeoutError(
                    "Timeout while waiting for the Kubernetes API server"
                ) from e
            break

    @contextlib.asynccontextmanager
    async def open_websocket(
        self,
        version: str = "v1",
        base: str = "",
        namespace: str = None,
        url: str = "",
        **kwargs,
    ) -> aiohttp.ClientResponse:
        """Open a websocket connection to a Kubernetes API endpoint."""
        headers = {"User-Agent": self.__version__, "content-type": "application/json"}
        if self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        userauth = None
        if self.auth.username and self.auth.password:
            userauth = aiohttp.BasicAuth(self.auth.username, self.auth.password)
        url = self._construct_url(version, base, namespace, url)
        kwargs.update(url=url, ssl=await self.auth.ssl_context())
        auth_attempts = 0
        while True:
            try:
                async with aiohttp.ClientSession(
                    base_url=self.auth.server,
                    headers=headers,
                    auth=userauth,
                ) as session:
                    async with session.ws_connect(**kwargs) as response:
                        yield response
            except aiohttp.ClientResponseError as e:
                if e.status in (401, 403) and auth_attempts < 3:
                    auth_attempts += 1
                    await self.auth.reauthenticate()
                    continue
                else:
                    raise
            break

    async def version(self) -> dict:
        """Get the Kubernetes version information from the API.

        Returns
        -------
        dict
            The Kubernetes version information.

        """
        return await self._version()

    async def _version(self) -> dict:
        async with self.call_api(method="GET", version="", base="/version") as response:
            return response.json()

    async def reauthenticate(self) -> None:
        """Reauthenticate the API."""
        await self.auth.reauthenticate()

    async def whoami(self):
        """Retrieve the subject that's currently authenticated.

        Inspired by `kubectl whoami`.

        Returns:
            str: The subject that's currently authenticated.
        """
        if self.auth.token:
            payload = {
                "apiVersion": "authentication.k8s.io/v1",
                "kind": "TokenReview",
                "spec": {"token": self.auth.token},
            }
            async with self.call_api(
                "POST",
                version="authentication.k8s.io/v1",
                url="tokenreviews",
                data=json.dumps(payload),
            ) as r:
                data = r.json()
                return data["status"]["user"]["username"]
        elif self.auth.username:
            return f"kubecfg:basicauth:{self.auth.username}"
        elif self.auth.client_cert_file:
            with open(self.auth.client_cert_file, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
                [name] = cert.subject.get_attributes_for_oid(x509.OID_COMMON_NAME)
                return name.value

    @contextlib.asynccontextmanager
    async def _get_kind(
        self,
        kind: str,
        namespace: str = None,
        label_selector: Union[str, Dict] = None,
        field_selector: Union[str, Dict] = None,
        params: dict = None,
        watch: bool = False,
        **kwargs,
    ) -> dict:
        """Get a Kubernetes resource."""
        from ._objects import get_class

        if not namespace:
            namespace = self.namespace
        if namespace is ALL:
            namespace = ""
        if params is None:
            params = {}
        if label_selector:
            if isinstance(label_selector, dict):
                label_selector = dict_to_selector(label_selector)
            params["labelSelector"] = label_selector
        if field_selector:
            if isinstance(field_selector, dict):
                field_selector = dict_to_selector(field_selector)
            params["fieldSelector"] = field_selector
        if watch:
            params["watch"] = "true" if watch else "false"
            kwargs["stream"] = True
        try:
            resources = await self._api_resources()
            for resource in resources:
                if "shortNames" in resource and kind in resource["shortNames"]:
                    kind = resource["name"]
                    break
        except ServerError as e:
            warnings.warn(str(e))
        params = params or None
        obj_cls = get_class(kind, _asyncio=self._asyncio)
        async with self.call_api(
            method="GET",
            url=obj_cls.endpoint,
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
        label_selector: Union[str, Dict] = None,
        field_selector: Union[str, Dict] = None,
        as_object: object = None,
        **kwargs,
    ) -> List[object]:
        """
        Get Kubernetes resources.

        Parameters
        ----------
        kind : str
            The kind of resource to get.
        *names : List[str], optional
            The names of specific resources to get.
        namespace : str, optional
            The namespace to get the resource from.
        label_selector : Union[str, Dict], optional
            The label selector to filter the resources by.
        field_selector : Union[str, Dict], optional
            The field selector to filter the resources by.
        as_object : object, optional
            The object to return the resources as.
        **kwargs
            Additional keyword arguments to pass to the API call.

        Returns
        -------
        List[object]
            The resources.
        """
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
        label_selector: Union[str, Dict] = None,
        field_selector: Union[str, Dict] = None,
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
            resourcelist = response.json()
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
        label_selector: Union[str, Dict] = None,
        field_selector: Union[str, Dict] = None,
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
        label_selector: Union[str, Dict] = None,
        field_selector: Union[str, Dict] = None,
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
            timeout=None,
        ) as (obj_cls, response):
            async for line in response.aiter_lines():
                event = json.loads(line)
                yield event["type"], obj_cls(event["object"], api=self)

    async def api_resources(self) -> dict:
        """Get the Kubernetes API resources."""
        return await self._api_resources()

    async def _api_resources(self) -> dict:
        """Get the Kubernetes API resources."""
        resources = []
        async with self.call_api(method="GET", version="", base="/api") as response:
            core_api_list = response.json()

        for version in core_api_list["versions"]:
            async with self.call_api(
                method="GET", version="", base="/api", url=version
            ) as response:
                resource = response.json()
            resources.extend(
                [
                    {"version": version, **r}
                    for r in resource["resources"]
                    if "/" not in r["name"]
                ]
            )
        async with self.call_api(method="GET", version="", base="/apis") as response:
            api_list = response.json()
        for api in sorted(api_list["groups"], key=lambda d: d["name"]):
            version = api["versions"][0]["groupVersion"]
            async with self.call_api(
                method="GET", version="", base="/apis", url=version
            ) as response:
                resource = response.json()
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

    @property
    def namespace(self) -> str:
        """Get the default namespace."""
        return self.auth.namespace

    @namespace.setter
    def namespace(self, value):
        self.auth.namespace = value
