# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import pathlib
from typing import TypeVar

import anyio

PathType = TypeVar("PathType", str, bytes, pathlib.Path, anyio.Path)
