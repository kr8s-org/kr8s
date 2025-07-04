# SPDX-FileCopyrightText: Copyright (c) 2023-2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from kubectl_ng.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_help_default():
    result = runner.invoke(app, [])
    assert "Usage:" in result.stdout
