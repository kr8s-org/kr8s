# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from functools import partial, update_wrapper

from ._api import ALL  # noqa
from ._api import Api as _AsyncApi
from ._exceptions import NotFoundError  # noqa
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
    version as _version,
)
from .asyncio import (
    watch as _watch,
)

__version__ = "0.0.0"


@_sync
class Api(_AsyncApi):
    __doc__ = _AsyncApi.__doc__


api = _run_sync(partial(_api, _asyncio=False))
get = _run_sync(partial(_get, _asyncio=False))
update_wrapper(get, _get)
version = _run_sync(partial(_version, _asyncio=False))
update_wrapper(version, _version)
watch = _run_sync(partial(_watch, _asyncio=False))
update_wrapper(watch, _watch)
api_resources = _run_sync(partial(_api_resources, _asyncio=False))
update_wrapper(api_resources, _api_resources)
