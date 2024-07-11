# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from typing import Dict, Optional, Type, Union

from kr8s._api import Api
from kr8s._objects import APIObject

from ._api import api as _api


async def get(
    kind: str,
    *names: str,
    namespace: Optional[str] = None,
    label_selector: Optional[Union[str, Dict]] = None,
    field_selector: Optional[Union[str, Dict]] = None,
    as_object: Optional[Type[APIObject]] = None,
    allow_unknown_type: bool = True,
    api=None,
    _asyncio=True,
    **kwargs,
):
    """Get a resource by name.

    This function retrieves a resource from the Kubernetes cluster based on its kind and name(s).
    It supports various options for filtering and customization.

    Args:
        kind: The kind of resource to get.
        *names: The names of the resources to get.
        namespace: The namespace to get the resource from.
        label_selector: The label selector to filter the resources by.
        field_selector: The field selector to filter the resources by.
        as_object: The object to populate with the resource data.
        allow_unknown_type: Automatically create a class for the resource if none exists.
        api: The api to use to get the resource.
        **kwargs: Additional keyword arguments to pass to the `httpx` API call.

    Returns:
        List[APIObject]: The Kubernetes resource objects.

    Raises:
        ValueError: If the resource is not found.

    Examples:
        >>> import kr8s
        >>> # All of these are equivalent
        >>> ings = await kr8s.asyncio.get("ing")                           # Short name
        >>> ings = await kr8s.asyncio.get("ingress")                       # Singular
        >>> ings = await kr8s.asyncio.get("ingresses")                     # Plural
        >>> ings = await kr8s.asyncio.get("Ingress")                       # Title
        >>> ings = await kr8s.asyncio.get("ingress.networking.k8s.io")     # Full group name
        >>> ings = await kr8s.asyncio.get("ingress.v1.networking.k8s.io")  # Full with explicit version
        >>> ings = await kr8s.asyncio.get("ingress.networking.k8s.io/v1")  # Full with explicit version alt.
    """
    if api is None:
        api = await _api(_asyncio=_asyncio)
    return await api.async_get(
        kind,
        *names,
        namespace=namespace,
        label_selector=label_selector,
        field_selector=field_selector,
        as_object=as_object,
        allow_unknown_type=allow_unknown_type,
        **kwargs,
    )


async def version(api=None, _asyncio=True):
    if api is None:
        api = await _api(_asyncio=_asyncio)
    return await api.async_version()


async def watch(
    kind: str,
    namespace: Optional[str] = None,
    label_selector: Optional[Union[str, Dict]] = None,
    field_selector: Optional[Union[str, Dict]] = None,
    since: Optional[str] = None,
    api=None,
    _asyncio=True,
):
    if api is None:
        api = await _api(_asyncio=_asyncio)
    async for t, o in api.async_watch(
        kind=kind,
        namespace=namespace,
        label_selector=label_selector,
        field_selector=field_selector,
        since=since,
    ):
        yield (t, o)


async def api_resources(api=None, _asyncio=True):
    if api is None:
        api = await _api(_asyncio=_asyncio)
    return await api.async_api_resources()


async def whoami(api=None, _asyncio=True):
    if api is None:
        api = await _api(_asyncio=_asyncio)
    return await api.async_whoami()


get.__doc__ = Api.get.__doc__
version.__doc__ = Api.version.__doc__
watch.__doc__ = Api.watch.__doc__
api_resources.__doc__ = Api.api_resources.__doc__
whoami.__doc__ = Api.whoami.__doc__
