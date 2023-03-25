"""An asyncio shim for pykube-ng."""
# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from pykube import HTTPClient, KubeConfig, all  # noqa
from ._api import Kr8sApi  # noqa

__version__ = "0.0.0"
