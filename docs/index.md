# <img alt="kr8s" title="kr8s" src="_static/branding/text-trimmed.png" style="max-height: 100px" />

[![PyPI](https://img.shields.io/pypi/v/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kr8s)](https://pypi.org/project/kr8s/)
[![Kubernetes Version Support](https://img.shields.io/badge/Kubernetes%20support-1.26%7C1.27%7C1.28-blue)](https://docs.kr8s.org/en/stable/installation.html#supported-kubernetes-versions)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - License](https://img.shields.io/pypi/l/kr8s)](https://pypi.org/project/kr8s/)
<iframe src="https://ghbtns.com/github-btn.html?user=kr8s-org&repo=kr8s&type=star&count=true" frameborder="0" scrolling="0" width="150" height="20" title="GitHub"></iframe>

A simple, extensible Python client library for Kubernetes that feels familiar for folks who already know how to use `kubectl`.

## Highlights

- API inspired by `kubectl` to reduce developer learning curve.
- [Sensible defaults](https://docs.kr8s.org/en/stable/authentication.html) to reduce boiler plate.
- No swagger generated code, human readable code only.
- Also has an [asynchronous API](https://docs.kr8s.org/en/stable/asyncio.html) that can be used with `asyncio` and `trio`.
- [Client caching](https://docs.kr8s.org/en/stable/client.html#client-caching) to reduce passing API objects around.
- Batteries included by providing [useful utilities and methods](https://docs.kr8s.org/en/stable/examples/pod_operations.html) inspired by `kubectl`.

## Quickstart

### Installation

```console
$ pip install kr8s
```

## Examples

See the [Examples Documentation](https://docs.kr8s.org/en/stable/examples) for a full set of examples including `asyncio` examples.

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

### Cordon a Node

Cordon a Node to mark it as unschedulable.

```python
from kr8s.objects import Node

node = Node("k8s-node-1")

node.cordon()
# Is equivalent to
# node.patch({"spec": {"unschedulable": True}})
```

```{toctree}
:maxdepth: 2
:caption: Getting Started
:hidden: true
installation
examples/index
```

```{toctree}
:maxdepth: 2
:caption: Foundations
:hidden: true
authentication
client
object
asyncio
```

```{toctree}
:maxdepth: 2
:caption: Development
:hidden: true
contributing
releasing
```

```{toctree}
:maxdepth: 2
:caption: Misc
:hidden: true
alternatives
branding
history
```


```{toctree}
:maxdepth: 2
:caption: API Reference
:hidden: true
autoapi/kr8s/index
```

