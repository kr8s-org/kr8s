# SPDX-FileCopyrightText: Copyright (c) 2023-2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""kubectl-ng."""

try:
    from .__version import version as __version__  # noqa
    from .__version import version_tuple as __version_tuple__  # noqa
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)
