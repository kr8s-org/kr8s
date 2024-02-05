# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import datetime
import pathlib

import pytest
from kubectl_ng.cli import app
from typer.testing import CliRunner

from kr8s.objects import objects_from_files

runner = CliRunner()

HERE = pathlib.Path(__file__).parent.absolute()


@pytest.fixture
def pod_service():
    spec = str(HERE / "resources" / "simple" / "nginx_pod_service.yaml")
    objs = objects_from_files(spec)
    for obj in objs:
        obj.create()
    yield [obj.name for obj in objs]
    for obj in objs:
        obj.delete()


def test_create_and_delete(pod_service):
    pod_name, _ = pod_service

    result = runner.invoke(app, ["exec", pod_name, "--", "date"])
    assert result.exit_code == 0
    assert str(datetime.datetime.now().year) in result.stdout
