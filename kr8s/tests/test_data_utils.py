# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import pytest

from kr8s._data_utils import (
    dict_to_selector,
    dot_to_nested_dict,
    list_dict_unpack,
    xdict,
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


def test_xdict():
    assert xdict(foo="bar") == {"foo": "bar"}
    assert xdict(foo="bar", baz=None) == {"foo": "bar"}
    assert xdict(foo="bar", baz="qux") == {"foo": "bar", "baz": "qux"}
    assert xdict(foo="bar", baz="qux", quux=None) == {"foo": "bar", "baz": "qux"}
    assert xdict({"foo": "bar", "baz": "qux"}) == {"foo": "bar", "baz": "qux"}
    assert xdict({"foo": "bar", "baz": None}) == {"foo": "bar"}
    with pytest.raises(ValueError):
        xdict({}, {})
    with pytest.raises(ValueError):
        assert xdict({}, quux=None) == {
            "foo": "bar",
            "baz": "qux",
        }
