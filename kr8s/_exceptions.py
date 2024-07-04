# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License

from typing import Optional

import httpx


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

    Attributes:
        status: The Status object from the Kubernetes API server
        response: The httpx response object
    """

    def __init__(
        self,
        message: str,
        status: Optional[str] = None,
        response: Optional[httpx.Response] = None,
    ) -> None:
        self.status = status
        self.response = response
        super().__init__(message)
