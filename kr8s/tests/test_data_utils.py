# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License

from kr8s._data_utils import dict_to_selector, dot_to_nested_dict, list_dict_unpack


def test_list_dict_unpack():
    data = [{"key": "hello", "value": "world"}]
    assert list_dict_unpack(data) == {"hello": "world"}


def test_dot_to_nested_dict():
    assert dot_to_nested_dict("hello", "world") == {"hello": "world"}
    assert dot_to_nested_dict("hello.world", "value") == {"hello": {"world": "value"}}
    assert dot_to_nested_dict("foo.bar.baz", "value") == {
        "foo": {
            "bar": {"baz": "value"},
        }
    }


def test_dict_to_selector():
    assert dict_to_selector({"foo": "bar"}) == "foo=bar"
    assert dict_to_selector({"foo": "bar", "baz": "qux"}) == "foo=bar,baz=qux"
