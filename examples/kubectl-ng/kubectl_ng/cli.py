# SPDX-FileCopyrightText: Copyright (c) 2023-2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import typer

from ._api_resources import api_resources
from ._api_versions import api_versions
from ._config import config
from ._cordon_uncordon import cordon, uncordon
from ._create import create
from ._delete import delete
from ._exec import kexec
from ._get import get
from ._typer_utils import register
from ._version import version
from ._wait import wait

app = typer.Typer(no_args_is_help=True)
register(app, api_resources)
register(app, api_versions)
register(app, cordon)
register(app, uncordon)
register(app, create)
register(app, delete)
register(app, get)
register(app, version)
register(app, wait)
register(app, kexec, "exec")
register(app, config, "config")


def go():
    app()


if __name__ == "__main__":
    go()
