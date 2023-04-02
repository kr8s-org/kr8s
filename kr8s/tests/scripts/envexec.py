#!/usr/bin/env python
# Produce a valid client.authentication.k8s.io/v1beta1 ExecCredential from
# environment variables.

import json
import os

print(
    json.dumps(
        {
            "apiVersion": "client.authentication.k8s.io/v1beta1",
            "kind": "ExecCredential",
            "status": {
                "clientCertificateData": os.environ["KUBE_CLIENT_CERTIFICATE_DATA"],
                "clientKeyData": os.environ["KUBE_CLIENT_KEY_DATA"],
            },
        }
    )
)
