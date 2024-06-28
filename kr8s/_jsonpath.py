# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from io import IOBase
from typing import MutableMapping, MutableSequence, TypeVar, Union

from jsonpath import JSONPatch as _JSONPatch
from jsonpath import findall, pointer  # noqa

T = TypeVar("T")


class JSONPatch(_JSONPatch):

    def apply(
        self,
        data: Union[str, IOBase, MutableSequence[T], MutableMapping[str, T]],
    ) -> T:
        return super().apply(data)  # type: ignore
