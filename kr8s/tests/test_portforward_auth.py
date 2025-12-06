# SPDX-FileCopyrightText: Copyright (c) 2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import yaml

import kr8s
from kr8s._exceptions import ServerError


# Override the k8s_cluster fixture to avoid creating a Kind cluster
@pytest.fixture
def k8s_cluster():
    class MockCluster:
        @property
        def kubeconfig_path(self):
            return Path(os.environ.get("KUBECONFIG", "~/.kube/config")).expanduser()

    return MockCluster()


@pytest.mark.asyncio
async def test_portforward_invalid_token(k8s_cluster):
    # Connect with admin kubeconfig to create a real pod
    try:
        api_admin = await kr8s.asyncio.api(kubeconfig=k8s_cluster.kubeconfig_path)
    except Exception as e:
        pytest.skip(f"Skipping: cannot connect to cluster: {e}")

    # Simple connectivity check
    try:
        async for _ in api_admin.get("pods", namespace="default"):
            break
    except Exception as e:
        pytest.skip(f"Skipping test: Could not list pods (check kubeconfig): {e}")

    # Create a dummy pod object for testing
    pod = kr8s.asyncio.objects.Pod(
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {"name": "test-portforward-auth", "namespace": "default"},
            "spec": {
                "containers": [
                    {
                        "name": "nginx",
                        "image": "nginx:latest",
                        "ports": [{"containerPort": 80}],
                    }
                ]
            },
        },
        api=api_admin,
    )

    # Delete if exists
    if await pod.exists():
        await pod.delete()
        await pod.wait("condition=Deleted")

    await pod.create()
    await pod.wait("condition=Ready")

        # 2. Create a temporary kubeconfig with an INVALID token
        # We read the current kubeconfig
        if k8s_cluster.kubeconfig_path.exists():
            kubeconfig_data = yaml.safe_load(k8s_cluster.kubeconfig_path.read_text())
        else:
            pytest.skip("Kubeconfig file not found.")

        # Find the user and change the token/certs to an invalid token
        # We replace the user entry with a simple token user
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
            # Fallback if no context structure
            pass

        # Write invalid kubeconfig to a temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml") as tmp_kubeconfig:
            yaml.dump(kubeconfig_data, tmp_kubeconfig)
            tmp_kubeconfig.flush()

            # 3. Initialize a new API with the invalid kubeconfig
            from kr8s._api import Api

            original_check_version = Api._check_version

            async def mock_check_version(self):
                return

            Api._check_version = mock_check_version

            try:
                api_invalid = await kr8s.asyncio.api(kubeconfig=tmp_kubeconfig.name)
            finally:
                Api._check_version = original_check_version

            # 4. Create a Pod object bound to this invalid API
            # We use the same name/namespace, but bound to the invalid API
            pod_invalid = kr8s.asyncio.objects.Pod(
                pod.name, namespace=pod.namespace, api=api_invalid
            )

            # 5. Attempt portforward and expect ServerError (Unauthorized)
            pf = pod_invalid.portforward(80, local_port=None)

            print("Attempting portforward with invalid token...")
            # We need to connect to the local port to trigger the websocket connection to the API server
            # The ServerError will be raised in the background task or when we try to read/write?
            # Actually, _sync_sockets runs in the server loop.
            # If it fails, it might log an error or close the connection.
            # But verify_real.py caught ServerError.

            # In verify_real.py:
            # async with pf as port:
            #    ...
            #    reader, writer = await asyncio.open_connection("127.0.0.1", port)

            # The ServerError in verify_real.py was caught because it was raised from _connect_websocket?
            # But _connect_websocket is called from _sync_sockets.

            # Let's try to connect and see if it raises.

            with pytest.raises(ServerError) as excinfo:
                async with pf._connect_websocket() as _:
                    pass

            # Verify it is a 401 or 403 (likely 401 for invalid token)
            assert excinfo.value.response.status_code in (401, 403)

    finally:
        await pod.delete()


if __name__ == "__main__":

    class MockCluster:
        @property
        def kubeconfig_path(self):
            return Path(os.environ.get("KUBECONFIG", "~/.kube/config")).expanduser()

    asyncio.run(test_portforward_invalid_token(MockCluster()))
