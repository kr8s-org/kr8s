# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from kubectl_ng.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_api_resources():
    result = runner.invoke(app, ["api-resources"])
    assert result.exit_code == 0
    assert "pod" in result.stdout
