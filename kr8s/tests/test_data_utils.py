# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License

from kr8s._data_utils import (
    dict_to_selector,
    diff_nested_dicts,
    dot_to_nested_dict,
    list_dict_unpack,
)


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


def test_diff_nested_dicts():
    assert diff_nested_dicts({"foo": "bar"}, {"foo": "bar"}) == {}
    assert diff_nested_dicts({"foo": "bar"}, {"foo": "baz"}) == {"foo": "baz"}
    assert diff_nested_dicts({"foo": "bar"}, {"foo": "bar", "baz": "qux"}) == {
        "baz": "qux"
    }
    assert diff_nested_dicts({"foo": [{"bar": "baz"}]}, {"foo": [{"bar": "qux"}]}) == {
        "foo": [{"bar": "qux"}]
    }
    assert diff_nested_dicts(
        {"foo": [{"bar": "baz"}, {"fizz": "buzz"}]},
        {"foo": [{"bar": "qux"}, {"fizz": "buzz"}]},
    ) == {"foo": [{"bar": "qux"}, {"fizz": "buzz"}]}
