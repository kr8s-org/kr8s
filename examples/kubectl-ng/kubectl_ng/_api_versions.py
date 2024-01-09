# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from rich.console import Console

import kr8s

console = Console()


async def api_versions():
    """Print the supported API versions on the server, in the form of "group/version".

    Examples:
        # Print the supported API versions
        kubectl-ng api-versions

    """
    api = kr8s.api()
    for version in sorted(api.api_versions()):
        console.print(version)
