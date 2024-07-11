# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from os import PathLike
from typing import TYPE_CHECKING, List, Protocol, Union, runtime_checkable

PathType = Union[str, PathLike[str]]

if TYPE_CHECKING:
    from ._objects import Pod


@runtime_checkable
class APIObjectWithPods(Protocol):
    """An APIObject subclass that contains other Pod objects."""

    async def async_ready_pods(self) -> List["Pod"]: ...
