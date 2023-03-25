# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License

from kr8s import Kr8sApi


async def test_api():
    kubernetes = Kr8sApi()
    version = await kubernetes.get_version()
    assert "major" in version
