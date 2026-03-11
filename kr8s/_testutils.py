# SPDX-FileCopyrightText: Copyright (c) 2023-2026, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import contextlib
import os
from collections.abc import Generator


@contextlib.contextmanager
def set_env(**environ: str) -> Generator[None, None, None]:
    """Temporarily sets the process environment variables.

    This context manager allows you to temporarily set the process environment variables
    within a specific scope. It saves the current environment variables, updates them with
    the provided values, and restores the original environment variables when the scope
    is exited.

    Args:
        **environ: Keyword arguments representing the environment variables to set.

    Yields:
        None

    Examples:
        >>> with set_env(PLUGINS_DIR='test/plugins'):
        ...     "PLUGINS_DIR" in os.environ
        True

        >>> "PLUGINS_DIR" in os.environ
        False

    """
    old_environ = dict(os.environ)
    os.environ.update(environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


@contextlib.contextmanager
def unset_env(*environ: str) -> Generator[None, None, None]:
    """Temporarily unsets the process environment variables.

    This context manager allows you to temporarily unset the process environment variables
    within a specific scope. It saves the current environment variables, removes the specified
    ones, and restores the original environment variables when the scope is exited.

    Args:
        *environ: Names of the environment variables to unset.

    Yields:
        None

    Examples:
        >>> with unset_env("PLUGINS_DIR"):
        ...     "PLUGINS_DIR" in os.environ
        False

        >>> "PLUGINS_DIR" in os.environ
        True

    """
    old_environ = dict(os.environ)
    for var in environ:
        os.environ.pop(var, None)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)
