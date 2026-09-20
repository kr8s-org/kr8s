# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""Objects for managing a subprocess.Popen like pod exec functionality.

This module provides a class for exec'ing processes on clusters using a subprocess.Popen like object.
"""

from kr8s._popen import Popen

__all__ = ["Popen"]
