# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""The `kr8s` asynchronous API.

This module provides an asynchronous API for interacting with a Kubernetes cluster.
"""
from kr8s._api import Api

from . import objects, portforward
from ._api import api
from ._helpers import api_resources, get, version, watch, whoami

__all__ = [
    "api",
    "api_resources",
    "get",
    "objects",
    "portforward",
    "version",
    "watch",
    "whoami",
    "Api",
]
