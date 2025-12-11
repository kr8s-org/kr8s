# SPDX-FileCopyrightText: Copyright (c) 2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import pytest
import yaml
import kr8s
from kr8s._exceptions import ServerError

@pytest.mark.asyncio
async def test_portforward_invalid_token(k8s_cluster):
    # Create a temporary kubeconfig with an INVALID token
    if k8s_cluster.kubeconfig_path.exists():
        kubeconfig_data = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
    else:
        pytest.skip("Kubeconfig file not found.")

    # Replace the user entry with a simple token user
    kubeconfig_data["users"] = [
        {"name": "invalid-user", "user": {"token": "invalid-token-12345"}}
    ]
    # Update context to use this user
    current_context = kubeconfig_data.get("current-context")
    if not current_context and kubeconfig_data["contexts"]:
        current_context = kubeconfig_data["contexts"][0]["name"]

    if current_context:
        for ctx in kubeconfig_data["contexts"]:
            if ctx["name"] == current_context:
                ctx["context"]["user"] = "invalid-user"
                break
    else:
        pass

    # Initialize a new API with the invalid kubeconfig
    from kr8s._api import Api

    original_check_version = Api._check_version

    async def mock_check_version(self):
        return

    Api._check_version = mock_check_version

    try:
        api_invalid = await kr8s.asyncio.api(kubeconfig=kubeconfig_data)
    finally:
        Api._check_version = original_check_version

    # Create a Pod object bound to this invalid API
    pod_invalid = kr8s.asyncio.objects.Pod(
        {"metadata": {"name": "test-portforward-auth", "namespace": "default"}},
        api=api_invalid,
    )

    # Attempt portforward and expect ServerError (Unauthorized)
    pf = pod_invalid.portforward(80, local_port=None)

    with pytest.raises(ServerError) as excinfo:
        async with pf._connect_websocket() as _:
            pass

    # Verify it is a 401 or 403 (likely 401 for invalid token)
    assert excinfo.value.response.status_code in (401, 403)
