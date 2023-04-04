# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License

from kr8s._data_utils import list_dict_unpack


def test_list_dict_unpack():
    data = [{"key": "hello", "value": "world"}]
    assert list_dict_unpack(data) == {"hello": "world"}
