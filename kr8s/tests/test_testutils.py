# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import os

from kr8s._testutils import set_env


def test_set_env():
    assert "FOO" not in os.environ
    with set_env(FOO="bar"):
        assert "FOO" in os.environ
    assert "FOO" not in os.environ

    os.environ["FOO"] = "bar"
    assert "FOO" in os.environ
    assert os.environ["FOO"] == "bar"
    with set_env(FOO="baz"):
        assert "FOO" in os.environ
        assert os.environ["FOO"] == "baz"
    assert "FOO" in os.environ
    assert os.environ["FOO"] == "bar"
    del os.environ["FOO"]
