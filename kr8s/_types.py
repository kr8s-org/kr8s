# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import pathlib
from typing import Union

import anyio

PathType = Union[str, bytes, pathlib.Path, anyio.Path]
