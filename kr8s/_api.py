# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import asyncio
import contextlib
import copy
import json
import logging
import os
import pathlib
import re
import ssl
import threading
import warnings
import weakref
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import anyio
import httpx
import httpx_ws
from cryptography import x509
from packaging.version import InvalidVersion
from packaging.version import parse as parse_version

from ._auth import KubeAuth
from ._constants import (
    KUBERNETES_MAXIMUM_SUPPORTED_VERSION,
    KUBERNETES_MINIMUM_SUPPORTED_VERSION,
)
from ._data_utils import dict_to_selector, sort_versions
from ._exceptions import APITimeoutError, ServerError
from ._version import __version__

if TYPE_CHECKING:
    from ._objects import APIObject

ALL = "all"
logger = logging.getLogger(__name__)


overly_cautious_illegal_file_characters = re.compile(r"[^\w/.]")


def compute_discovery_cache_dir(parent_dir: pathlib.Path, host: str) -> pathlib.Path:
    """Port of kubectl's discovery cache dir."""
    schemeless_host = host.replace("https://", "", 1).replace("http://", "", 1)
    safe_host = re.sub(overly_cautious_illegal_file_characters, "_", schemeless_host)
    return parent_dir / safe_host


def get_default_cache_dir() -> pathlib.Path:
    """
    Get the default cache directory for kubectl discovery cache.

    Port from kubectl https://github.com/kubernetes/cli-runtime/blob/980bedf450ab21617b33d68331786942227fe93a/pkg/genericclioptions/config_flags.go#L303-L309
    """
    if os.environ.get("KUBECACHEDIR"):
        return pathlib.Path(os.environ["KUBECACHEDIR"])
    else:
        return pathlib.Path.home() / ".kube" / "cache"


class KubectlDiscoveryCache:
    """Cache for API resources kinds on disk."""

    def __init__(self, cache_dir: pathlib.Path):
        self.cache_dir = cache_dir

    @classmethod
    def from_api(
        cls, api: Api, kubectl_cache_dir: pathlib.Path | None = None
    ) -> KubectlDiscoveryCache:
        if not kubectl_cache_dir:
            kubectl_cache_dir = get_default_cache_dir()

        cache_dir = pathlib.Path(
            compute_discovery_cache_dir(
                kubectl_cache_dir / "discovery", api.auth.server
            )
        )
        logger.debug(f"Loading API resources from kubectl cache in {cache_dir}")
        if not cache_dir.exists():
            logger.debug("Cache directory does not exist, creating")
            cache_dir.mkdir(parents=True, exist_ok=True)

        return cls(cache_dir)

    def load_file(self, file: pathlib.Path) -> dict:
        """Load a file from kubectl's discovery cache."""
        with open(self.cache_dir / file, encoding="utf-8") as f:
            return json.load(f)

    def write_file(self, file: pathlib.Path, data: dict) -> None:
        """Write a file to kubectl's discovery cache."""
        cache_file = self.cache_dir / file
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def check_exists(self, file: pathlib.Path) -> bool:
        return (self.cache_dir / file).exists()

    def list_all_files(self, glob: str = "*.json") -> list[pathlib.Path]:
        return list(self.cache_dir.rglob(glob))


class KindFetcherCached:
    """Fetch API resources from the Kubernetes API, caching results."""

    def __init__(
        self,
        api: Api,
        disk_cache: KubectlDiscoveryCache,
        save_cache: bool = True,
    ):
        self.api = api
        self.disk_cache = disk_cache
        self.save_cache = save_cache

    def save_file(self, file: pathlib.Path, data):
        if self.save_cache:
            logger.debug("saving to discovery cache %s", file)
            self.disk_cache.write_file(file, data)

    async def fetch_kind(self, group_version: str):
        try:
            return self.disk_cache.load_file(
                pathlib.Path(group_version, "serverresources.json")
            )
        except FileNotFoundError:
            async with self.api.call_api(
                method="GET", version="", base="/apis", url=group_version
            ) as response:
                v = response.json()
            self.save_file(pathlib.Path(group_version, "serverresources.json"), v)
            return v

    async def fetch_apis(self):
        try:
            return self.disk_cache.load_file(pathlib.Path("serverresources.json"))
        except FileNotFoundError:
            async with self.api.call_api(
                method="GET", version="", base="/apis"
            ) as response:
                v = response.json()
            self.save_file(pathlib.Path("servergroups.json"), v)
            return v

    async def fetch_core_kinds(self, version):
        try:
            return self.disk_cache.load_file(
                pathlib.Path(version, "serverresources.json")
            )
        except FileNotFoundError:
            async with self.api.call_api(
                method="GET", version="", base="/api", url=version
            ) as response:
                v = response.json()
            self.save_file(pathlib.Path(version, "serverresources.json"), v)
            return v

    async def fetch_core_versions(self):
        async with self.api.call_api(method="GET", version="", base="/api") as response:
            return response.json()

    @staticmethod
    def collect_api_resources(resource, version):
        """Add an API resource to the list of resources."""
        return [
            {"version": version, **r}
            for r in resource["resources"]
            if "/" not in r["name"]
        ]

    async def async_api_resources_uncached(self) -> list[dict]:
        """Get the Kubernetes API resources."""
        resources = []
        core_api_list = await self.fetch_core_versions()

        for version in core_api_list["versions"]:
            resource = await self.fetch_core_kinds(version)
            resources.extend(self.collect_api_resources(resource, version))
        api_list = await self.fetch_apis()
        for api in sorted(api_list["groups"], key=lambda d: d["name"]):
            for api_version in sort_versions(
                api["versions"], key=lambda x: x["groupVersion"]
            ):
                version = api_version["groupVersion"]
                resource = await self.fetch_kind(version)
                resources.extend(self.collect_api_resources(resource, version))
        return resources


def load_api_resources_from_kubectl(_cache: KubectlDiscoveryCache):
    """
    Load API resources from kubectl's discovery cache.

    Kubernetes clients need to look up what resources are available on the server.
    Kubectl caches this information on disk.
    You can load this information and skip sending many requests to the server.
    """
    logger.debug(f"Loading API resources from kubectl cache in {_cache.cache_dir}")
    if not _cache.check_exists(pathlib.Path("servergroups.json")):
        logger.warning(
            f"Directory {_cache.cache_dir} does not contain `servergroups.json`, "
            "this may not be a standard kubectl cache directory",
        )

    out = []

    for file in _cache.list_all_files():
        try:
            data = _cache.load_file(file)
            group_version = data["groupVersion"]
            out.append(KindFetcherCached.collect_api_resources(data, group_version))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load API resources from {file}: {e}")
            continue
        except KeyError as e:
            logger.warning(
                f"Invalid API resources file {file}, expected key 'groupVersion': {e}"
            )
            continue

    logger.debug(f"Loaded {len(out)} API resources from kubectl cache")
    return out


class ResourceKindCache:
    """Cache for API resources kinds."""

    # TODO: Add TTL

    def __init__(
        self,
        kind_fetcher: KindFetcherCached,
        cache: list[dict] | None = None,
    ):
        self.kind_fetcher = kind_fetcher
        self.cache = [] if cache is None else cache
        self.loaded = cache is not None

    async def get(self) -> list[dict]:
        # TODO: break this up by resources
        if not self.loaded:
            await self.get_uncached()

        return self.cache

    async def get_uncached(self) -> list[dict]:
        await self.set(await self.kind_fetcher.async_api_resources_uncached())
        return self.cache

    async def set(self, resources: list[dict]):
        self.loaded = True
        self.cache = resources


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

        # TODO: make this injectable
        # TODO: fill from k8s
        self.resource_kind_cache = ResourceKindCache(
            KindFetcherCached(
                self,
                KubectlDiscoveryCache.from_api(self),
                save_cache=True,
            )
        )

    def __await__(self):
        async def f():
            await self.auth
            await self._check_version()
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
            proxy=self.auth.proxy,
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
                        if response.is_error and raise_for_status:
                            # NOTE: Avoid `httpx.ResponseNotRead` w/ streaming requests
                            # https://github.com/encode/httpx/discussions/1856#discussioncomment-1316674
                            await response.aread()
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
                    logger.debug(
                        f"Unauthorized {e.response.status_code} error, reauthenticating attempt {auth_attempts}"
                    )
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

    async def _check_version(self) -> None:
        version = await self.async_version()
        git_version = version["gitVersion"]

        supported_message = (
            f"Supported versions for kr8s {__version__} are "
            f"{KUBERNETES_MINIMUM_SUPPORTED_VERSION}"
            " to "
            f"{KUBERNETES_MAXIMUM_SUPPORTED_VERSION}."
        )

        try:
            # Remove variant suffix if present before parsing, e.g v1.32.9-eks-113cf36 -> v1.32.9
            version = parse_version(git_version.split("-")[0])
        except InvalidVersion:
            warnings.warn(
                f"Unable to parse Kubernetes version {git_version}. {supported_message}",
                UserWarning,
                stacklevel=2,
            )
            return

        # We only care about major/minor version differences, so we truncate the patch version
        version = parse_version(f"{version.major}.{version.minor}")
        if (
            version < KUBERNETES_MINIMUM_SUPPORTED_VERSION
            or version > KUBERNETES_MAXIMUM_SUPPORTED_VERSION
        ):
            warnings.warn(
                f"Kubernetes version {git_version} is not supported. {supported_message}",
                UserWarning,
                stacklevel=2,
            )

    async def reauthenticate(self) -> None:
        """Reauthenticate the API."""
        return await self.async_reauthenticate()

    async def async_reauthenticate(self) -> None:
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
                content=json.dumps(payload),
            ) as r:
                data = r.json()
                return data["status"]["user"]["username"]
        elif self.auth.client_cert_file:
            with open(self.auth.client_cert_file, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
                [name] = cert.subject.get_attributes_for_oid(x509.OID_COMMON_NAME)
                return name.value

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

    async def async_lookup_kind(
        self, kind, skip_cache: bool = False
    ) -> tuple[str, str, bool]:
        """Lookup a Kubernetes resource kind."""
        from ._objects import parse_kind

        if skip_cache:
            resources = await self.resource_kind_cache.get_uncached()
        else:
            resources = await self.resource_kind_cache.get()
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

        if not skip_cache:
            return await self.async_lookup_kind(kind, skip_cache=True)

        raise ValueError(f"Kind {kind} not found.")

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
        raw: bool = False,
        **kwargs,
    ) -> AsyncGenerator[APIObject | dict]:
        """Get Kubernetes resources.

        Args:
            kind: The kind of resource to get.
            *names: The names of specific resources to get.
            namespace: The namespace to get the resource from.
            label_selector: The label selector to filter the resources by.
            field_selector: The field selector to filter the resources by.
            as_object: The object to return the resources as.
            allow_unknown_type: Automatically create a class for the resource if none exists, default True.
            raw: If True, return raw dictionaries instead of APIObject instances, default False.
            **kwargs: Additional keyword arguments to pass to the API call.

        Returns:
            The resources.
        """
        async for resource in self.async_get(
            kind,
            *names,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
            as_object=as_object,
            allow_unknown_type=allow_unknown_type,
            raw=raw,
            **kwargs,
        ):
            yield resource

    async def async_get(
        self,
        kind: str | type,
        *names: str,
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        as_object: type[APIObject] | None = None,
        allow_unknown_type: bool = True,
        raw: bool = False,
        **kwargs,
    ) -> AsyncGenerator[APIObject | dict]:
        names_list = [None] if not names else names
        for name in names_list:
            async for resource in self._async_get_single(
                kind,
                name,
                namespace=namespace,
                label_selector=label_selector,
                field_selector=field_selector,
                as_object=as_object,
                allow_unknown_type=allow_unknown_type,
                raw=raw,
                **kwargs,
            ):
                yield resource

    async def _async_get_single(
        self,
        kind: str | type,
        name: str | None = None,
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        as_object: type[APIObject] | None = None,
        allow_unknown_type: bool = True,
        raw: bool = False,
        **kwargs,
    ) -> AsyncGenerator[APIObject | dict]:

        if name is not None:
            # Normalized field_selector to a string
            field_selector_str: str
            if isinstance(field_selector, dict):
                field_selector_str = dict_to_selector(field_selector)
            elif field_selector is None:
                field_selector_str = ""
            else:
                field_selector_str = field_selector
            field_selector = f"metadata.name={name},{field_selector_str}"

        headers = {}
        params = {}
        continue_paging = True
        if as_object:
            group, version = as_object.version.split("/")
            headers["Accept"] = (
                f"application/json;as={as_object.kind};v={version};g={group}"
            )
        else:
            params["limit"] = 100
        while continue_paging:
            async with self.async_get_kind(
                kind,
                namespace=namespace,
                label_selector=label_selector,
                field_selector=field_selector,
                headers=headers or None,
                allow_unknown_type=allow_unknown_type,
                params=params,
                **kwargs,
            ) as (obj_cls, response):
                resourcelist = response.json()
                if (
                    as_object
                    and "kind" in resourcelist
                    and resourcelist["kind"] == as_object.kind
                ):
                    if raw:
                        yield resourcelist
                    else:
                        yield as_object(resourcelist, api=self)
                else:
                    if "items" in resourcelist:
                        for item in resourcelist["items"]:
                            if name is None or item["metadata"]["name"] == name:
                                if raw:
                                    yield item
                                else:
                                    yield obj_cls(item, api=self)
                if (
                    "metadata" in resourcelist
                    and "continue" in resourcelist["metadata"]
                    and resourcelist["metadata"]["continue"]
                ):
                    continue_paging = True
                    params["continue"] = resourcelist["metadata"]["continue"]
                else:
                    continue_paging = False

    async def watch(
        self,
        kind: str,
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        since: str | None = None,
    ) -> AsyncGenerator[tuple[str, APIObject]]:
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

    async def async_api_resources(self) -> list[dict]:
        return await self.resource_kind_cache.get()

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

    async def async_create(self, resources: list[APIObject]):
        async with anyio.create_task_group() as tg:
            for resource in resources:
                tg.start_soon(resource.async_create)

    async def create(self, resources: list[APIObject]):
        return await self.async_create(resources)

    @property
    def __version__(self) -> str:
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
