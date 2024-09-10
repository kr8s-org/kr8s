# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""Utilities for working with Kubernetes data structures."""
from __future__ import annotations

import re
from typing import Any, Callable


def list_dict_unpack(
    input_list: list[dict], key: str = "key", value: str = "value"
) -> dict:
    """Convert a list of dictionaries to a single dictionary.

    Args:
        input_list: The list of dictionaries to convert to a single dictionary.
        key: The key to use for the new dictionary's keys. Defaults to "key".
        value: The key to use for the new dictionary's values. Defaults to "value".

    Returns:
        A dictionary with the keys and values from the input list.
    """
    return {i[key]: i[value] for i in input_list}


def dict_list_pack(
    input_dict: dict, key: str = "key", value: str = "value"
) -> list[dict]:
    """Convert a dictionary to a list of dictionaries.

    Args:
        input_dict: The dictionary to convert to a list of dictionaries.
        key: The key to use for the input dictionary's keys. Defaults to "key".
        value: The key to use for the input dictionary's values. Defaults to "value".

    Returns:
        A list of dictionaries with the keys and values from the input dictionary.
    """
    return [{key: k, value: v} for k, v in input_dict.items()]


def dot_to_nested_dict(dot_notated_key: str, value: Any) -> dict:
    """Convert a dot notated key to a nested dictionary.

    Args:
        dot_notated_key: The dot notated key to convert to a nested dictionary.
        value: The value to assign to the innermost key.

    Returns:
        A nested dictionary with the innermost key being the value of the
        dot notated key.
    """
    keys = dot_notated_key.split(".")
    nested_dict: dict = {}
    for key in reversed(keys):
        if not nested_dict:
            nested_dict[key] = value
        else:
            nested_dict = {key: nested_dict}
    return nested_dict


def dict_to_selector(selector_dict: dict) -> str:
    """Convert a dictionary to a Kubernetes selector.

    Args:
        selector_dict: The dictionary to convert to a Kubernetes selector.

    Returns:
        A Kubernetes selector string.
    """
    return ",".join(f"{k}={v}" for k, v in selector_dict.items())


def xdict(*in_dict, **kwargs):
    """Dictionary constructor that ignores None values.

    Args:
        in_dict: A dict to convert. Only one is allowed.
        **kwargs: Keyword arguments to be converted to a dict.

    Returns:
        A dict with None values removed.

    Raises:
        ValueError
            If more than one positional argument is passed, or if both a positional
            argument and keyword arguments are passed.

    Examples:
        >>> xdict(foo="bar", baz=None)
        {"foo": "bar"}

        >>> xdict({"foo": "bar", "baz": None})
        {"foo": "bar"}
    """
    if len(in_dict) > 1:
        raise ValueError(
            f"xdict expected at most 1 positional argument, got {len(in_dict)}"
        )
    if len(in_dict) == 1 and kwargs:
        raise ValueError(
            "xdict expected at most 1 positional argument, or multiple keyword arguments, got both"
        )
    if len(in_dict) == 1:
        [kwargs] = in_dict
    return {k: v for k, v in kwargs.items() if v is not None}


def sort_versions(
    versions: list[Any], key: Callable = lambda x: x, reverse: bool = False
) -> list[Any]:
    """Sort a list of Kubernetes versions by priority.

    Follows the spcification
    https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/#version-priority

    Args:
        versions: A list of Kubernetes versions to sort.
        key: A function to extract the version string from each element in the list.
            Defaults to the identity function
        reverse: If True, sort in descending order. Defaults to False

    Returns:
        A list of Kubernetes versions sorted by priority.

    Examples:
        >>> sort_versions(["v1", "v2", "v2beta1"])
        ["v2", "v1", "v2beta1"]

        >>> sort_versions(["v1beta2", "foo1", "foo10", "v1"])
        ["v1", "v1beta2", "foo1", "foo10"]
    """
    pattern = r"^v\d+((alpha|beta)\d+)?$"
    stable = []
    alphas = []
    betas = []
    others = []
    for version in versions:
        if re.match(pattern, key(version)) is not None:
            if "alpha" in key(version):
                alphas.append(version)
            elif "beta" in key(version):
                betas.append(version)
            else:
                stable.append(version)
        else:
            others.append(version)

    stable = sorted(stable, key=lambda v: int(key(v)[1:]), reverse=True)
    betas = sorted(
        betas, key=lambda v: tuple(map(int, key(v)[1:].split("beta"))), reverse=True
    )
    alphas = sorted(
        alphas, key=lambda v: tuple(map(int, key(v)[1:].split("alpha"))), reverse=True
    )
    others = sorted(others, key=lambda v: key(v))

    output = stable + betas + alphas + others
    if reverse:
        output.reverse()
    return output
