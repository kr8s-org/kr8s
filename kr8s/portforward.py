import threading

from ._io import sync
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
        self.server.close()
