# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""Utilities for working with Kubernetes data structures."""
from typing import Any, Dict, List


def list_dict_unpack(
    input_list: List[Dict], key: str = "key", value: str = "value"
) -> Dict:
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
    input_dict: Dict, key: str = "key", value: str = "value"
) -> List[Dict]:
    """Convert a dictionary to a list of dictionaries.

    Args:
        input_dict: The dictionary to convert to a list of dictionaries.
        key: The key to use for the input dictionary's keys. Defaults to "key".
        value: The key to use for the input dictionary's values. Defaults to "value".

    Returns:
        A list of dictionaries with the keys and values from the input dictionary.
    """
    return [{key: k, value: v} for k, v in input_dict.items()]


def dot_to_nested_dict(dot_notated_key: str, value: Any) -> Dict:
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


def dict_to_selector(selector_dict: Dict) -> str:
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
