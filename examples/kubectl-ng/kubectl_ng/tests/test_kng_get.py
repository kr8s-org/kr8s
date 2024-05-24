# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from kubectl_ng.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_get_pods():
    result = runner.invoke(app, ["get", "pods", "-A"])
    assert result.exit_code == 0
