# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import contextlib
import os
from typing import Generator


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
