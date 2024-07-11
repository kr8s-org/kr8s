# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""
This module contains `kr8s`, a simple, extensible Python client library for Kubernetes.

At the top level, `kr8s` provides a synchronous API that wraps the asynchronous API provided by `kr8s.asyncio`.
Both APIs are functionally identical with the same objects, method signatures and return values.
"""
from functools import partial, update_wrapper
from typing import Dict, Optional, Type, Union

from . import asyncio, objects, portforward
from ._api import ALL
from ._api import Api as _AsyncApi
from ._async_utils import run_sync as _run_sync
from ._async_utils import sync as _sync
from ._exceptions import (
    APITimeoutError,
    ConnectionClosedError,
    ExecError,
    NotFoundError,
    ServerError,
)
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


@_sync
class Api(_AsyncApi):
    __doc__ = _AsyncApi.__doc__


def get(
    kind: str,
    *names: str,
    namespace: Optional[str] = None,
    label_selector: Optional[Union[str, Dict]] = None,
    field_selector: Optional[Union[str, Dict]] = None,
    as_object: Optional[Type] = None,
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
    return _run_sync(_get)(
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
    url: Optional[str] = None,
    kubeconfig: Optional[str] = None,
    serviceaccount: Optional[str] = None,
    namespace: Optional[str] = None,
    context: Optional[str] = None,
) -> Union[Api, _AsyncApi]:
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
    ret = _run_sync(_api)(
        url=url,
        kubeconfig=kubeconfig,
        serviceaccount=serviceaccount,
        namespace=namespace,
        context=context,
        _asyncio=False,
    )
    assert isinstance(ret, (Api, _AsyncApi))
    return ret


def whoami():
    """Get the current user's identity.

    Returns:
        The user's identity

    Examples:
        >>> import kr8s
        >>> print(kr8s.whoami())
    """
    return _run_sync(_whoami)(_asyncio=False)


version = _run_sync(partial(_k8s_version, _asyncio=False))
update_wrapper(version, _k8s_version)
watch = _run_sync(partial(_watch, _asyncio=False))
update_wrapper(watch, _watch)
api_resources = _run_sync(partial(_api_resources, _asyncio=False))
update_wrapper(api_resources, _api_resources)

__all__ = [
    "__version__",
    "__version_tuple__",
    "ALL",
    "api",
    "api_resources",
    "asyncio",
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
