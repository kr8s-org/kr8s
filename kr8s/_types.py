# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from os import PathLike
from typing import (
    TYPE_CHECKING,
    Iterable,
    List,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

_KT = TypeVar("_KT")
_VT_co = TypeVar("_VT_co", covariant=True)
PathType = Union[
    str,
    "PathLike[str]",  # Can remove quotes when Python 3.9 is the minimum version.
]

if TYPE_CHECKING:
    from ._objects import Pod


@runtime_checkable
class APIObjectWithPods(Protocol):
    """An APIObject subclass that contains other Pod objects."""

    async def async_ready_pods(self) -> List["Pod"]: ...


@runtime_checkable
class SupportsKeysAndGetItem(Protocol[_KT, _VT_co]):
    """Copied from _typeshed.SupportsKeysAndGetItem to avoid importing it and make runtime checkable."""

    def keys(self) -> Iterable[_KT]: ...
    def __getitem__(self, key: _KT, /) -> _VT_co: ...


class SupportsToDict(Protocol):
    """An object that can be converted to a dictionary."""

    def to_dict(self) -> dict: ...


class SupportsObjAttr(Protocol):
    """An object that has an `obj` dict attribute."""

    obj: dict


# Type that can be converted to a Kubernetes spec.
SpecType = Union[dict, str, SupportsKeysAndGetItem, SupportsToDict, SupportsObjAttr]
