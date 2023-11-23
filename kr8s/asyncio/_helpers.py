# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from typing import Dict, List, Union

from kr8s._api import Api

from ._api import api as _api


async def get(
    kind: str,
    *names: List[str],
    namespace: str = None,
    label_selector: Union[str, Dict] = None,
    field_selector: Union[str, Dict] = None,
    as_object: object = None,
    api=None,
    _asyncio=True,
    **kwargs,
):
    """Get a resource by name.

    Parameters
    ----------
    kind : str
        The kind of resource to get
    *names : List[str]
        The names of the resources to get
    namespace : str, optional
        The namespace to get the resource from
    label_selector : Union[str, Dict], optional
        The label selector to filter the resources by
    field_selector : Union[str, Dict], optional
        The field selector to filter the resources by
    as_object : object, optional
        The object to populate with the resource data
    api : Api, optional
        The api to use to get the resource

    Returns
    -------
    object
        The populated object

    Raises
    ------
    ValueError
        If the resource is not found

    Examples
    --------

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
    return await api._get(
        kind,
        *names,
        namespace=namespace,
        label_selector=label_selector,
        field_selector=field_selector,
        as_object=as_object,
        **kwargs,
    )


async def version(api=None, _asyncio=True):
    if api is None:
        api = await _api(_asyncio=_asyncio)
    return await api._version()


async def watch(
    kind: str,
    namespace: str = None,
    label_selector: Union[str, Dict] = None,
    field_selector: Union[str, Dict] = None,
    since: str = None,
    api=None,
    _asyncio=True,
):
    if api is None:
        api = await _api(_asyncio=_asyncio)
    async for (t, o) in api._watch(
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
    return await api._api_resources()


get.__doc__ = Api.get.__doc__
version.__doc__ = Api.version.__doc__
watch.__doc__ = Api.watch.__doc__
api_resources.__doc__ = Api.api_resources.__doc__
