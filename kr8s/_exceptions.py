class NotFoundError(Exception):
    """Unable to find the requested resource."""


class ConnectionClosedError(Exception):
    """A connection has been closed."""
