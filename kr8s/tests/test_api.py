# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import pytest

import kr8s
from kr8s.objects import Pod


async def test_version():
    kubernetes = kr8s.Kr8sApi()
    version = await kubernetes.version()
    assert "major" in version


@pytest.mark.parametrize("namespace", [kr8s.ALL, "kube-system"])
async def test_get_pods(namespace):
    kubernetes = kr8s.Kr8sApi()
    pods = await kubernetes.get("pods", namespace=namespace)
    assert isinstance(pods, list)
    assert len(pods) > 0
    assert isinstance(pods[0], Pod)
