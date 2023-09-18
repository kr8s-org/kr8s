class NotFoundError(Exception):
    """Unable to find the requested resource."""


class ConnectionClosedError(Exception):
    """A connection has been closed."""


class ServerStatusError(Exception):
    """The server returned an error status code."""

    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(message)
