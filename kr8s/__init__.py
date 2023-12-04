# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from functools import partial, update_wrapper

import kr8s.objects  # noqa

from ._api import ALL  # noqa
from ._api import Api as _AsyncApi
from ._exceptions import (
    APITimeoutError,  # noqa
    ConnectionClosedError,  # noqa
    ExecError,  # noqa
    NotFoundError,  # noqa
    ServerError,  # noqa
)
from ._io import run_sync as _run_sync
from ._io import sync as _sync  # noqa
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

try:
    from ._version import version as __version__  # noqa
    from ._version import version_tuple as __version_tuple__  # noqa
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)


@_sync
class Api(_AsyncApi):
    __doc__ = _AsyncApi.__doc__


def get(*args, **kwargs):
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
        >>> ings = kr8s.get("ing")                           # Short name
        >>> ings = kr8s.get("ingress")                       # Singular
        >>> ings = kr8s.get("ingresses")                     # Plural
        >>> ings = kr8s.get("Ingress")                       # Title
        >>> ings = kr8s.get("ingress.networking.k8s.io")     # Full group name
        >>> ings = kr8s.get("ingress.v1.networking.k8s.io")  # Full with explicit version
        >>> ings = kr8s.get("ingress.networking.k8s.io/v1")  # Full with explicit version alt.
    """
    return _run_sync(partial(_get, _asyncio=False))(*args, **kwargs)


api = _run_sync(partial(_api, _asyncio=False))
version = _run_sync(partial(_k8s_version, _asyncio=False))
update_wrapper(version, _k8s_version)
watch = _run_sync(partial(_watch, _asyncio=False))
update_wrapper(watch, _watch)
api_resources = _run_sync(partial(_api_resources, _asyncio=False))
update_wrapper(api_resources, _api_resources)
