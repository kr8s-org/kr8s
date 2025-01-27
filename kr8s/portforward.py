# SPDX-FileCopyrightText: Copyright (c) 2024-2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""Objects for managing a port forward connection.

This module provides a class for managing a port forward connection to a Kubernetes Pod or Service.
"""
# Disable missing docstrings, these are inherited from the async version of the objects
# ruff: noqa: D102, D105
from __future__ import annotations

import threading
import time

from ._async_utils import run_sync
from ._portforward import LocalPortType
from ._portforward import PortForward as _PortForward

__all__ = ["PortForward", "LocalPortType"]


class PortForward(_PortForward):
    _bg_thread = None

    def __enter__(self, *args, **kwargs):
        return run_sync(self.__aenter__)(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        return run_sync(self.__aexit__)(*args, **kwargs)

    def run_forever(self):
        return run_sync(self.async_run_forever)()  # type: ignore

    def start(self):
        """Start a background thread with the port forward running."""
        self._bg_thread = threading.Thread(target=self.run_forever, daemon=True)
        self._bg_thread.start()

    def stop(self):
        """Stop the background thread."""
        for server in self.servers:
            while server is None:
                time.sleep(0.1)
            server.close()
