<div style="text-align: center; width: 100%;"><img src="https://github.com/kr8s-org/kr8s/raw/v0.17.2/branding/logo-wide.png" style="max-height: 200px;" /></div>

[![Test](https://github.com/kr8s-org/kr8s/actions/workflows/test-kr8s.yaml/badge.svg)](https://github.com/kr8s-org/kr8s/actions/workflows/test.yaml)
[![Codecov](https://img.shields.io/codecov/c/gh/kr8s-org/kr8s?logo=codecov&logoColor=ffffff)](https://app.codecov.io/gh/kr8s-org/kr8s)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/kr8s-org/kr8s/main.svg)](https://results.pre-commit.ci/latest/github/kr8s-org/kr8s/main)
[![Read the Docs](https://img.shields.io/readthedocs/kr8s?logo=readthedocs&logoColor=white)](https://docs.kr8s.org/en/stable/)
[![EffVer Versioning](https://img.shields.io/badge/version_scheme-EffVer-0097a7)](https://jacobtomlinson.dev/effver)
[![PyPI](https://img.shields.io/pypi/v/kr8s)](https://pypi.org/project/kr8s/)
[![Python Version Support](https://img.shields.io/badge/Python%20support-3.8%7C3.9%7C3.10%7C3.11%7C3.12-blue)](https://pypi.org/project/kr8s/)
[![Kubernetes Version Support](https://img.shields.io/badge/Kubernetes%20support-1.28%7C1.29%7C1.30%7C1.31-blue)](https://docs.kr8s.org/en/stable/installation.html#supported-kubernetes-versions)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - License](https://img.shields.io/pypi/l/kr8s)](https://pypi.org/project/kr8s/)

A simple, extensible Python client library for Kubernetes that feels familiar for folks who already know how to use `kubectl`.

## Highlights

- API inspired by `kubectl` for a shallow learning curve.
- [Sensible defaults](https://docs.kr8s.org/en/stable/authentication.html) to reduce boiler plate.
- No swagger generated code, human readable code only.
- Has both a standard and an [async API](https://docs.kr8s.org/en/stable/asyncio.html) that can be used with `asyncio` and `trio`.
- [Client caching](https://docs.kr8s.org/en/stable/client.html#client-caching) to reduce passing API objects around.
- Batteries included by providing [useful utilities and methods](https://docs.kr8s.org/en/stable/examples/pod_operations.html) inspired by `kubectl`.

## Quickstart

### Installation

```console
$ pip install kr8s
```

## Examples

> [!TIP]
> See the [Examples Documentation](https://docs.kr8s.org/en/stable/examples/) for a full set of examples including `asyncio` examples.

### List Nodes

Print out all of the node names in the cluster.

```python
import kr8s

for node in kr8s.get("nodes"):
    print(node.name)
```

### Create a Pod

Create a new Pod.

```python
from kr8s.objects import Pod

pod = Pod({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "my-pod",
        },
        "spec": {
            "containers": [{"name": "pause", "image": "gcr.io/google_containers/pause",}]
        },
    })

pod.create()
```

### Scale a Deployment

Scale the Deployment `metrics-server` in the Namespace `kube-system` to `1` replica.

```python
from kr8s.objects import Deployment

deploy = Deployment.get("metrics-server", namespace="kube-system")
deploy.scale(1)
```

### List Pods by label selector

Get all Pods from all Namespaces matching a label selector.

```python
import kr8s

selector = {'component': 'kube-scheduler'}

for pod in kr8s.get("pods", namespace=kr8s.ALL, label_selector=selector):
    print(pod.namespace, pod.name)
```

### Add a label to a Pod

Add the label `foo` with the value `bar` to an existing Pod.

```python
from kr8s.objects import Pod

pod = Pod("kube-apiserver", namespace="kube-system")
pod.label({"foo": "bar"})
```

### Generate a Pod

Generate a simple Pod with a couple of keyword arguments.

```python
from kr8s.objects import Pod

pod = Pod.gen(name="example-1", image="nginx:latest")
pod.create()
```

### Cordon a Node

Cordon a Node to mark it as unschedulable.

```python
from kr8s.objects import Node

node = Node("k8s-node-1")

node.cordon()
```

### Pod Exec

Exec a command in a Pod.

```python
from kr8s.objects import Pod

pod = Pod.get("my-pod")

command = pod.exec(["uptime"])
print(command.stdout.decode())
# 13:49:05 up 23:03,  0 users,  load average: 0.66, 0.87, 0.85
```

### Port forward a Pod

Open a port forward to a Pod as a background task/thread.

```python
from kr8s.objects import Pod

pod = Pod.get("my-pod")
pf = pod.portforward(remote_port=1234, local_port=5678)

# Starts the port forward in a background thread
pf.start()

# Your other code goes here

# Optionally stop the port forward thread (it will exit with Python anyway)
pf.stop()
```

> [!TIP]
> See the [Examples Documentation](https://docs.kr8s.org/en/stable/examples/) for a full set of examples including `asyncio` examples.
