#!/usr/bin/env python
# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
#
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
