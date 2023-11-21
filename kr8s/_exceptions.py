class NotFoundError(Exception):
    """Unable to find the requested resource."""


class ConnectionClosedError(Exception):
    """A connection has been closed."""


class APITimeoutError(Exception):
    """A timeout has occurred while waiting for a response from the Kubernetes API server."""


class ExecError(Exception):
    """Internal error in the exec protocol."""
