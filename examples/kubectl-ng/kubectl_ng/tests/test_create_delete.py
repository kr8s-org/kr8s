# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import pathlib

from kubectl_ng.cli import app
from typer.testing import CliRunner

from kr8s.objects import objects_from_files

runner = CliRunner()

HERE = pathlib.Path(__file__).parent.absolute()


def test_create_and_delete():
    spec = str(HERE / "resources" / "simple" / "nginx_pod_service.yaml")

    objs = objects_from_files(spec)
    for obj in objs:
        assert not obj.exists()

    result = runner.invoke(app, ["create", "-f", spec])
    assert result.exit_code == 0
    for obj in objs:
        assert obj.name in result.stdout

    for obj in objs:
        assert obj.exists()

    result = runner.invoke(app, ["delete", "-f", spec])
    assert result.exit_code == 0
    for obj in objs:
        assert obj.name in result.stdout

    for obj in objs:
        assert not obj.exists()
