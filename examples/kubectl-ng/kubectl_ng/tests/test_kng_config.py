# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from kubectl_ng.cli import app
from typer.testing import CliRunner

import kr8s

runner = CliRunner()


def test_current_context():
    current_context = kr8s.api().auth.kubeconfig.current_context
    result = runner.invoke(app, ["config", "current-context"])
    assert result.exit_code == 0
    assert current_context in result.stdout


def test_get_clusters(k8s_cluster):
    result = runner.invoke(app, ["config", "get-clusters"])
    assert result.exit_code == 0
    assert k8s_cluster.name in result.stdout


def test_get_users(k8s_cluster):
    result = runner.invoke(app, ["config", "get-users"])
    assert result.exit_code == 0
    assert k8s_cluster.name in result.stdout


def test_get_contexts(k8s_cluster):
    result = runner.invoke(app, ["config", "get-contexts"])
    assert result.exit_code == 0
    assert k8s_cluster.name in result.stdout

    result = runner.invoke(app, ["config", "get-contexts", f"kind-{k8s_cluster.name}"])
    assert result.exit_code == 0
    assert k8s_cluster.name in result.stdout

    result = runner.invoke(app, ["config", "get-contexts", "foo"])
    assert result.exit_code == 1
    assert "foo not found" in result.stdout


def test_use_context():
    current_context = kr8s.api().auth.kubeconfig.current_context
    result = runner.invoke(app, ["config", "use-context", current_context])
    assert result.exit_code == 0
    assert current_context in result.stdout


def test_rename_context():
    # Get current context
    current_context = kr8s.api().auth.kubeconfig.current_context
    result = runner.invoke(app, ["config", "current-context"])
    assert result.exit_code == 0
    assert current_context in result.stdout

    # Rename current context to foo
    result = runner.invoke(app, ["config", "rename-context", current_context, "foo"])
    assert result.exit_code == 0
    assert current_context in result.stdout
    assert "foo" in result.stdout

    # Check the context rename was successful
    result = runner.invoke(app, ["config", "current-context"])
    assert result.exit_code == 0
    assert "foo" in result.stdout

    # Rename foo back to the original name
    result = runner.invoke(app, ["config", "rename-context", "foo", current_context])
    assert result.exit_code == 0
    assert current_context in result.stdout
    assert "foo" in result.stdout

    # Check the context revert was successful
    result = runner.invoke(app, ["config", "current-context"])
    assert result.exit_code == 0
    assert current_context in result.stdout
