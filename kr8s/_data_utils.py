# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
"""Utilities for working with Kubernetes data structures."""
from typing import Dict, List


def list_dict_unpack(
    input_list: List[Dict], key: str = "key", value: str = "value"
) -> Dict:
    return {i[key]: i[value] for i in input_list}
