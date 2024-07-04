# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""Objects for managing a port forward connection.

This module provides a class for managing a port forward connection to a Kubernetes Pod or Service.
"""
import threading
import time

from ._async_utils import sync
from ._portforward import PortForward as _PortForward


@sync
class PortForward(_PortForward):
    __doc__ = _PortForward.__doc__
    _bg_thread = None

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
