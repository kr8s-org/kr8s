# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from functools import partial

from ._api import ALL  # noqa
from ._api import Api as _AsyncApi
from ._asyncio import sync
from ._exceptions import NotFoundError  # noqa
from .asyncio import api as _api  # noqa

__version__ = "0.0.0"


@sync
class Api(_AsyncApi):
    __doc__ = _AsyncApi.__doc__


api = partial(_api, _asyncio=False)
