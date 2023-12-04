class NotFoundError(Exception):
    """Unable to find the requested resource."""


class ConnectionClosedError(Exception):
    """A connection has been closed."""


class APITimeoutError(Exception):
    """A timeout has occurred while waiting for a response from the Kubernetes API server."""


class ExecError(Exception):
    """Internal error in the exec protocol."""


class ServerError(Exception):
    """Error from the Kubernetes API server.

    Attributes
    ----------
    status : str
        The Status object from the Kubernetes API server
    response : httpx.Response
        The httpx response object
    """

    def __init__(self, message, status=None, response=None):
        self.status = status
        self.response = response
        super().__init__(message)
