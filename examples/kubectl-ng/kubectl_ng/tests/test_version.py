# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import json

import yaml
from kubectl_ng.cli import app
from typer.testing import CliRunner

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Client Version" in result.stdout
    assert "Server Version" in result.stdout


def test_version_yaml():
    result = runner.invoke(app, ["version", "-o", "yaml"])
    assert result.exit_code == 0
    data = yaml.safe_load(result.stdout)
    assert "clientVersion" in data


def test_version_json():
    result = runner.invoke(app, ["version", "-o", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "clientVersion" in data


def test_version_invalid_output():
    result = runner.invoke(app, ["version", "-o", "foo"])
    assert result.exit_code == 1
