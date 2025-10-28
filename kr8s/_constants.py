# SPDX-FileCopyrightText: Copyright (c) 2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from packaging.version import parse as parse_version

KUBERNETES_MINIMUM_SUPPORTED_VERSION = parse_version("1.28")
KUBERNETES_MAXIMUM_SUPPORTED_VERSION = parse_version("1.34")
