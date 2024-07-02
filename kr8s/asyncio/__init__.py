# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from kr8s._api import Api

from ._api import api
from ._helpers import api_resources, get, version, watch, whoami

__all__ = ["api", "api_resources", "get", "version", "watch", "whoami", "Api"]
