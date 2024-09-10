# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import random

import pytest

from kr8s._data_utils import (
    dict_list_pack,
    dict_to_selector,
    dot_to_nested_dict,
    list_dict_unpack,
    sort_versions,
    xdict,
)


def test_list_dict_unpack():
    data = [{"key": "hello", "value": "world"}]
    assert list_dict_unpack(data) == {"hello": "world"}


def test_dict_list_pack():
    data = {"hello": "world"}
    assert dict_list_pack(data) == [{"key": "hello", "value": "world"}]


def test_pack_unpack():
    data = [{"key": "hello", "value": "world"}]
    assert dict_list_pack(list_dict_unpack(data)) == data

    data = {"hello": "world"}
    assert list_dict_unpack(dict_list_pack(data)) == data


def test_unpack_pack_deduplicate():
    data = [
        {"key": "hello", "value": "world"},
        {"key": "hello", "value": "there"},
    ]
    unpacked = list_dict_unpack(data)
    assert unpacked["hello"] == "there"
    repacked = dict_list_pack(unpacked)
    assert len(repacked) == 1
    assert repacked == [{"key": "hello", "value": "there"}]


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


def test_sort_version_priorities():
    # Sample list based on list from Kubernetes documentation
    # https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/#version-priority
    versions = [
        "v200",
        "v10",
        "v2",
        "v1",
        "v11beta2",
        "v10beta3",
        "v3beta1",
        "v12alpha1",
        "v11alpha2",
        "v11alpha1",
        "v3alpha1",
        "12345",
        "foo1",
        "foo10",
        "helloworld",
        "vfoobaralpha1",
    ]

    # Select some random permutations of the above list and ensure they get correctly sorted
    sample = versions.copy()  # Create a copy that we can shuffle
    random.seed(42)  # Ensure the same random order each time for deterministic tests
    for _ in range(30):
        random.shuffle(sample)
        assert sort_versions(list(sample)) == versions


def test_sort_version_priorities_key():
    versions = [
        {"version": "v2"},
        {"version": "v1"},
        {"version": "v1beta2"},
        {"version": "v1beta1"},
        {"version": "v1alpha1"},
    ]

    # Select some random permutations of the above list and ensure they get correctly sorted
    sample = versions.copy()  # Create a copy that we can shuffle
    random.seed(42)  # Ensure the same random order each time for deterministic tests
    for _ in range(30):
        random.shuffle(sample)
        assert sort_versions(list(sample), key=lambda x: x["version"]) == versions
