# SPDX-FileCopyrightText: Copyright (c) 2023-2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""
This module contains `kr8s`, a simple, extensible Python client library for Kubernetes.

At the top level, `kr8s` provides a synchronous API that wraps the asynchronous API provided by `kr8s.asyncio`.
Both APIs are functionally identical with the same objects, method signatures and return values.
"""
# Disable missing docstrings, these are inherited from the async version of the objects
# ruff: noqa: D102
from __future__ import annotations

from collections.abc import Generator
from functools import partial, update_wrapper
from typing import cast

from . import asyncio, objects, portforward
from ._api import ALL
from ._api import Api as _AsyncApi
from ._async_utils import as_sync_func as _as_sync_func
from ._async_utils import as_sync_generator as _as_sync_generator
from ._exceptions import (
    APITimeoutError,
    ConnectionClosedError,
    ExecError,
    NotFoundError,
    ServerError,
)
from ._objects import APIObject
from .asyncio import (
    api as _api,
)
from .asyncio import (
    api_resources as _api_resources,
)
from .asyncio import (
    get as _get,
)
from .asyncio import (
    version as _k8s_version,
)
from .asyncio import (
    watch as _watch,
)
from .asyncio import (
    whoami as _whoami,
)

try:
    from ._version import version as __version__  # noqa
    from ._version import version_tuple as __version_tuple__  # noqa
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)


class Api(_AsyncApi):
    _asyncio = False

    def version(self) -> dict:  # type: ignore[override]
        return _as_sync_func(self.async_version)()

    def reauthenticate(self):  # type: ignore[override]
        return _as_sync_func(self.async_reauthenticate)()

    def whoami(self):  # type: ignore[override]
        return _as_sync_func(self.async_whoami)()

    def lookup_kind(self, kind) -> tuple[str, str, bool]:  # type: ignore[override]
        return _as_sync_func(self.async_lookup_kind)(kind)

    def get(  # type: ignore[override]
        self,
        kind: str | type,
        *names: str,
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        as_object: type[APIObject] | None = None,
        allow_unknown_type: bool = True,
        **kwargs,
    ) -> Generator[objects.APIObject]:
        yield from cast(
            Generator[objects.APIObject],
            _as_sync_generator(self.async_get)(
                kind,
                *names,
                namespace=namespace,
                label_selector=label_selector,
                field_selector=field_selector,
                as_object=as_object,
                allow_unknown_type=allow_unknown_type,
                **kwargs,
            ),
        )

    def watch(  # type: ignore[override]
        self,
        kind: str,
        namespace: str | None = None,
        label_selector: str | dict | None = None,
        field_selector: str | dict | None = None,
        since: str | None = None,
    ) -> Generator[tuple[str, objects.APIObject]]:
        yield from cast(
            Generator[tuple[str, objects.APIObject]],
            _as_sync_generator(self.async_watch)(
                kind,
                namespace=namespace,
                label_selector=label_selector,
                field_selector=field_selector,
                since=since,
            ),
        )

    def api_resources(self) -> list[dict]:  # type: ignore[override]
        return _as_sync_func(self.async_api_resources)()

    def api_versions(self) -> Generator[str]:  # type: ignore[override]
        yield from _as_sync_generator(self.async_api_versions)()

    def create(self, resources: list[objects.APIObject]):  # type: ignore[override]
        return _as_sync_func(self.async_create)(
            cast(list[asyncio.objects.APIObject], resources)
        )


def get(
    kind: str,
    *names: str,
    namespace: str | None = None,
    label_selector: str | dict | None = None,
    field_selector: str | dict | None = None,
    as_object: type | None = None,
    allow_unknown_type: bool = True,
    api=None,
    **kwargs,
):
    """Get a resource by name.

    Args:
        kind: The kind of resource to get
        *names: The names of the resources to get
        namespace: The namespace to get the resource from
        label_selector: The label selector to filter the resources by
        field_selector: The field selector to filter the resources by
        as_object: The object to populate with the resource data
        allow_unknown_type: Whether to allow unknown types
        api: The api to use to get the resource
        **kwargs: Additional arguments to pass to the API

    Returns:
        The populated object

    Raises:
        ValueError: If the resource is not found

    Examples:
        >>> import kr8s
        >>> # All of these are equivalent
        >>> ings = kr8s.get("ing")                           # Short name
        >>> ings = kr8s.get("ingress")                       # Singular
        >>> ings = kr8s.get("ingresses")                     # Plural
        >>> ings = kr8s.get("Ingress")                       # Title
        >>> ings = kr8s.get("ingress.networking.k8s.io")     # Full group name
        >>> ings = kr8s.get("ingress.v1.networking.k8s.io")  # Full with explicit version
        >>> ings = kr8s.get("ingress.networking.k8s.io/v1")  # Full with explicit version alt.
    """
    return _as_sync_generator(_get)(
        kind,
        *names,
        namespace=namespace,
        label_selector=label_selector,
        field_selector=field_selector,
        as_object=as_object,
        allow_unknown_type=allow_unknown_type,
        api=api,
        _asyncio=False,
        **kwargs,
    )


def api(
    url: str | None = None,
    kubeconfig: str | None = None,
    serviceaccount: str | None = None,
    namespace: str | None = None,
    context: str | None = None,
) -> Api:
    """Create a :class:`kr8s.Api` object for interacting with the Kubernetes API.

    If a kr8s object already exists with the same arguments in this thread, it will be returned.

    Args:
        url: The URL of the Kubernetes API server
        kubeconfig: The path to a kubeconfig file to use
        serviceaccount: The path of a service account to use
        namespace: The namespace to use
        context: The context to use

    Returns:
        The API object

    Examples:
        >>> import kr8s
        >>> api = kr8s.api()  # Uses the default kubeconfig
        >>> print(api.version())  # Get the Kubernetes version
    """
    ret = _as_sync_func(_api)(
        url=url,
        kubeconfig=kubeconfig,
        serviceaccount=serviceaccount,
        namespace=namespace,
        context=context,
        _asyncio=False,
    )
    assert isinstance(ret, Api)
    return ret


def whoami():
    """Get the current user's identity.

    Returns:
        The user's identity

    Examples:
        >>> import kr8s
        >>> print(kr8s.whoami())
    """
    return _as_sync_func(_whoami)(_asyncio=False)


def create(resources: list[type[APIObject]], api=None):
    """Creates resources in the Kubernetes cluster."""
    if api is None:
        api = _as_sync_func(_api)(_asyncio=False)
    api.create(cast(list[asyncio.objects.APIObject], resources))


version = _as_sync_func(partial(_k8s_version, _asyncio=False))
update_wrapper(version, _k8s_version)
watch = _as_sync_generator(partial(_watch, _asyncio=False))
update_wrapper(watch, _watch)
api_resources = _as_sync_func(partial(_api_resources, _asyncio=False))
update_wrapper(api_resources, _api_resources)

__all__ = [
    "__version__",
    "__version_tuple__",
    "ALL",
    "api",
    "api_resources",
    "asyncio",
    "create",
    "get",
    "objects",
    "portforward",
    "version",
    "watch",
    "whoami",
    "Api",
    "APITimeoutError",
    "ConnectionClosedError",
    "ExecError",
    "NotFoundError",
    "ServerError",
]
