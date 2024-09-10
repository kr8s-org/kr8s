# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import asyncio
import contextlib
import copy
import json
import logging
import ssl
import threading
import warnings
import weakref
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
)

import httpx
import httpx_ws
from asyncache import cached  # type: ignore
from cachetools import TTLCache  # type: ignore
from cryptography import x509

from ._auth import KubeAuth
from ._data_utils import dict_to_selector, sort_versions
from ._exceptions import APITimeoutError, ServerError

if TYPE_CHECKING:
    from ._objects import APIObject

ALL = "all"
logger = logging.getLogger(__name__)


class Api:
    """A kr8s object for interacting with the Kubernetes API.

    .. warning::
        This class is not intended to be instantiated directly. Instead, use the
        :func:`kr8s.api` function to get a singleton instance of the API.

        See https://docs.kr8s.org/en/stable/client.html#client-caching.

    """

    _asyncio = True
    _instances: dict[str, weakref.WeakValueDictionary] = {}

    def __init__(self, **kwargs) -> None:
        if not kwargs.pop("bypass_factory", False):
            raise ValueError(
                "Use kr8s.api() to get an instance of Api. "
                "See https://docs.kr8s.org/en/stable/client.html#client-caching."
            )

        self._url = kwargs.get("url")
        self._kubeconfig = kwargs.get("kubeconfig")
        self._serviceaccount = kwargs.get("serviceaccount")
        self._session: httpx.AsyncClient | None = None
        self._timeout = None
        self.auth = KubeAuth(
            url=self._url,
            kubeconfig=self._kubeconfig,
            serviceaccount=self._serviceaccount,
            namespace=kwargs.get("namespace"),
            context=kwargs.get("context"),
        )
        thread_id = threading.get_ident()
        try:
            loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            loop_id = 0
        thread_loop_id = f"{thread_id}.{loop_id}"
        if thread_loop_id not in Api._instances:
            Api._instances[thread_loop_id] = weakref.WeakValueDictionary()
        key = hash_kwargs(kwargs)
        Api._instances[thread_loop_id][key] = self

    def __await__(self):
        async def f():
            await self.auth
            return self

        return f().__await__()

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = value
        if self._session:
            self._session.timeout = value

    async def _create_session(self) -> None:
        headers = {"User-Agent": self.__version__, "content-type": "application/json"}
        if self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        if self._session:
            with contextlib.suppress(RuntimeError):
                await self._session.aclose()
            self._session = None
        self._session = httpx.AsyncClient(
            base_url=self.auth.server,
            headers=headers,
            verify=await self.auth.ssl_context(),
            timeout=self._timeout,
            follow_redirects=True,
        )

    def _construct_url(
        self,
        version: str = "v1",
        base: str = "",
        namespace: str | None = None,
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
        if namespace:
            parts.extend(["namespaces", namespace])
        parts.append(url)
        return "/".join(parts)

    @contextlib.asynccontextmanager
    async def call_api(
        self,
        method: str = "GET",
        version: str = "v1",
        base: str = "",
        namespace: str | None = None,
        url: str = "",
        raise_for_status: bool = True,
        stream: bool = False,
        **kwargs,
    ) -> AsyncGenerator[httpx.Response]:
        """Make a Kubernetes API request."""
        if not self._session or self._session.is_closed:
            await self._create_session()
        url = self._construct_url(version, base, namespace, url)
        kwargs.update(url=url, method=method)
        if self.auth.tls_server_name:
            kwargs["extensions"] = {"sni_hostname": self.auth.tls_server_name}
        auth_attempts = 0
        ssl_attempts = 0
        while True:
            try:
                if stream:
                    assert self._session
                    async with self._session.stream(**kwargs) as response:
                        if raise_for_status:
                            response.raise_for_status()
                        yield response
                else:
                    assert self._session
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
                        try:
                            error = e.response.json()
                            error_message = error["message"]
                        except json.JSONDecodeError:
                            error = e.response.text
                            error_message = str(e)
                        raise ServerError(
                            error_message, status=error, response=e.response
                        ) from e
                    elif e.response.status_code >= 500:
                        raise ServerError(
                            str(e),
                            status=str(e.response.status_code),
                            response=e.response,
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
            except httpx.TimeoutException as e:
                raise APITimeoutError(
                    "Timeout while waiting for the Kubernetes API server"
                ) from e
            break

    @contextlib.asynccontextmanager
    async def open_websocket(
        self,
        version: str = "v1",
        base: str = "",
        namespace: str | None = None,
        url: str = "",
        **kwargs,
    ) -> AsyncGenerator[httpx_ws.AsyncWebSocketSession]:
        """Open a websocket connection to a Kubernetes API endpoint."""
        if not self._session or self._session.is_closed:
            await self._create_session()
        url = self._construct_url(version, base, namespace, url)
        kwargs.update(url=url)
        if self.auth.tls_server_name:
            kwargs["extensions"] = {"sni_hostname": self.auth.tls_server_name}
        auth_attempts = 0
        while True:
            try:
                async with httpx_ws.aconnect_ws(
                    client=self._session, **kwargs
                ) as response:
                    yield response
            except httpx_ws.WebSocketDisconnect as e:
                if e.code and e.code != 1000:
                    if e.code in (401, 403) and auth_attempts < 3:
                        auth_attempts += 1
                        await self.auth.reauthenticate()
                        continue
                    else:
                        raise
            break

    async def version(self) -> dict:
        """Get the Kubernetes version information from the API.

        Returns:
            The Kubernetes version information.

        """
        return await self.async_version()

    async def async_version(self) -> dict:
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
        return await self.async_whoami()

    async def async_whoami(self):
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
        elif self.auth.client_cert_file:
            with open(self.auth.client_cert_file, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
                [name] = cert.subject.get_attributes_for_oid(x509.OID_COMMON_NAME)
                return name.value

    async def async_lookup_kind(self, kind) -> tuple[str, str, bool]:
        """Lookup a Kubernetes resource kind."""
        from ._objects import parse_kind

        resources = await self.async_api_resources()
        kind, group, version = parse_kind(kind)
        if group:
            version = f"{group}/{version}"
        for resource in resources:
            if (not version or version in resource["version"]) and (
                kind == resource["name"]
                or kind == resource["kind"]
                or kind == resource["singularName"]
                or ("shortNames" in resource and kind in resource["shortNames"])
            ):
                if "/" in resource["version"]:
                    return (
                        f"{resource['singularName']}.{resource['version']}",
                        resource["name"],
                        resource["namespaced"],
                    )
                return (
                    f"{resource['singularName']}/{resource['version']}",
                    resource["name"],
                    resource["namespaced"],
                )
        raise ValueError(f"Kind {kind} not found.")

    async def lookup_kind(self, kind) -> tuple[str, str, bool]:
        """Lookup a Kubernetes resource kind.

        Check whether a resource kind exists on the remote server.

        Args:
            kind: The kind of resource to lookup.

        Returns:
            The kind of resource, the plural form and whether the resource is namespaced

        Raises:
            ValueError: If the kind is not found.
        """
        return await self.async_lookup_kind(kind)

    @contextlib.asynccontextmanager
    async def async_get_kind(
        self,
        kind: str | type[APIObject],
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        params: dict | None = None,
        watch: bool = False,
        allow_unknown_type: bool = True,
        **kwargs,
    ) -> AsyncGenerator[tuple[type[APIObject], httpx.Response]]:
        """Get a Kubernetes resource."""
        from ._objects import get_class, new_class

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
        if isinstance(kind, type):
            obj_cls = kind
        else:
            namespaced: bool | None = None
            try:
                kind, plural, namespaced = await self.async_lookup_kind(kind)
            except ServerError as e:
                warnings.warn(str(e), stacklevel=1)
            if isinstance(kind, str):
                try:
                    obj_cls = get_class(kind, _asyncio=self._asyncio)
                except KeyError as e:
                    if allow_unknown_type:
                        if namespaced is not None:
                            obj_cls = new_class(
                                kind,
                                namespaced=namespaced,
                                asyncio=self._asyncio,
                                plural=plural,
                            )
                        else:
                            obj_cls = new_class(
                                kind, asyncio=self._asyncio, plural=plural
                            )
                    else:
                        raise e
        params = params or None
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
        kind: str | type,
        *names: str,
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        as_object: type[APIObject] | None = None,
        allow_unknown_type: bool = True,
        **kwargs,
    ) -> APIObject | list[APIObject]:
        """Get Kubernetes resources.

        Args:
            kind: The kind of resource to get.
            *names: The names of specific resources to get.
            namespace: The namespace to get the resource from.
            label_selector: The label selector to filter the resources by.
            field_selector: The field selector to filter the resources by.
            as_object: The object to return the resources as.
            allow_unknown_type: Automatically create a class for the resource if none exists, default True.
            **kwargs: Additional keyword arguments to pass to the API call.

        Returns:
            The resources.
        """
        return await self.async_get(
            kind,
            *names,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
            as_object=as_object,
            allow_unknown_type=allow_unknown_type,
            **kwargs,
        )

    async def async_get(
        self,
        kind: str | type,
        *names: str,
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        as_object: type[APIObject] | None = None,
        allow_unknown_type: bool = True,
        **kwargs,
    ) -> APIObject | list[APIObject]:
        headers = {}
        if as_object:
            group, version = as_object.version.split("/")
            headers["Accept"] = (
                f"application/json;as={as_object.kind};v={version};g={group}"
            )
        async with self.async_get_kind(
            kind,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
            headers=headers or None,
            allow_unknown_type=allow_unknown_type,
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
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        since: str | None = None,
    ):
        """Watch a Kubernetes resource."""
        async for t, object in self.async_watch(
            kind,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
            since=since,
        ):
            yield t, object

    async def async_watch(
        self,
        kind: str,
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        since: str | None = None,
        allow_unknown_type: bool = True,
    ) -> AsyncGenerator[tuple[str, APIObject]]:
        """Watch a Kubernetes resource."""
        while True:
            restart_watch = False
            async with self.async_get_kind(
                kind,
                namespace=namespace,
                label_selector=label_selector,
                field_selector=field_selector,
                params={"resourceVersion": since} if since else None,
                watch=True,
                timeout=None,
                allow_unknown_type=allow_unknown_type,
            ) as (obj_cls, response):
                logger.debug(
                    f"Starting watch of {kind}{' at resourceVersion ' + since if since else ''}"
                )
                async for line in response.aiter_lines():
                    event = json.loads(line)
                    if (
                        event["object"]["kind"] == "Status"
                        and event["object"].get("code") == 410
                    ):
                        restart_watch = True
                        logger.debug(
                            f"Got 410 Gone: Restarting watch of {kind} at resourceVersion {since}"
                        )
                        break
                    obj = obj_cls(event["object"], api=self)
                    since = obj.metadata.resourceVersion
                    yield event["type"], obj
            if not restart_watch:
                return

    async def api_resources(self) -> list[dict]:
        """Get the Kubernetes API resources."""
        return await self.async_api_resources()

    # Cache for 6 hours because kubectl does
    # https://github.com/kubernetes/cli-runtime/blob/980bedf450ab21617b33d68331786942227fe93a/pkg/genericclioptions/config_flags.go#L297
    @cached(TTLCache(1, 60 * 60 * 6))
    async def async_api_resources(self) -> list[dict]:
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
            for api_version in sort_versions(
                api["versions"], key=lambda x: x["groupVersion"]
            ):
                version = api_version["groupVersion"]
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

    async def api_versions(self) -> AsyncGenerator[str]:
        """Get the Kubernetes API versions."""
        async for version in self.async_api_versions():
            yield version

    async def async_api_versions(self) -> AsyncGenerator[str]:
        async with self.call_api(method="GET", version="", base="/api") as response:
            core_api_list = response.json()
        for version in core_api_list["versions"]:
            yield version

        async with self.call_api(method="GET", version="", base="/apis") as response:
            api_list = response.json()
        for group in api_list["groups"]:
            for version in group["versions"]:
                yield version["groupVersion"]

    @property
    def __version__(self) -> str:
        from . import __version__

        return f"kr8s/{__version__}"

    @property
    def namespace(self) -> str:
        """Get the default namespace."""
        assert self.auth.namespace
        return self.auth.namespace

    @namespace.setter
    def namespace(self, value):
        self.auth.namespace = value


def hash_kwargs(kwargs: dict):
    key_kwargs = copy.copy(kwargs)
    for key in key_kwargs:
        if isinstance(key_kwargs[key], dict):
            key_kwargs[key] = json.dumps(key_kwargs[key])
    return frozenset(key_kwargs.items())
