# <img alt="kr8s" title="kr8s" src="_static/branding/text-trimmed.png" style="max-height: 100px" />

[![EffVer Versioning](https://img.shields.io/badge/version_scheme-EffVer-0097a7)](https://jacobtomlinson.dev/effver)
[![PyPI](https://img.shields.io/pypi/v/kr8s)](https://pypi.org/project/kr8s/)
[![Python Version Support](https://img.shields.io/badge/Python%20support-3.8%7C3.9%7C3.10%7C3.11%7C3.12-blue)](https://pypi.org/project/kr8s/)
[![Kubernetes Version Support](https://img.shields.io/badge/Kubernetes%20support-1.28%7C1.29%7C1.30%7C1.31-blue)](https://docs.kr8s.org/en/stable/installation.html#supported-kubernetes-versions)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - License](https://img.shields.io/pypi/l/kr8s)](https://pypi.org/project/kr8s/)
<iframe src="https://ghbtns.com/github-btn.html?user=kr8s-org&repo=kr8s&type=star&count=true" frameborder="0" scrolling="0" width="150" height="20" title="GitHub"></iframe>

A simple, extensible Python client library for Kubernetes that feels familiar for folks who already know how to use `kubectl`.

## Highlights

- API inspired by `kubectl` for a shallow learning curve.
- [Sensible defaults](authentication) to reduce boiler plate.
- No swagger generated code, human readable code only.
- Has both a standard and an [async API](asyncio) that can be used with `asyncio` and `trio`.
- [Client caching](#client-caching) to reduce passing API objects around.
- Batteries included by providing [useful utilities and methods](examples/pod_operations) inspired by `kubectl`.

## Quickstart

### Installation

```console
$ pip install kr8s
```

## Examples

```{seealso}
See the [Examples Documentation](examples/index) for a full set of examples.
```

### List Nodes

Print out all of the node names in the cluster.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

for node in kr8s.get("nodes"):
    print(node.name)
```
````

````{tab-item} Async
:sync: async
```python
import kr8s.asyncio

for node in await kr8s.asyncio.get("nodes"):
    print(node.name)
```
````

`````

### Create a Pod

Create a new Pod.

`````{tab-set}

````{tab-item} Sync
:sync: sync
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
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "my-pod",
        },
        "spec": {
            "containers": [{"name": "pause", "image": "gcr.io/google_containers/pause",}]
        },
    })

await pod.create()
```
````

`````

### Scale a Deployment

Scale the Deployment `metrics-server` in the Namespace `kube-system` to `1` replica.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Deployment

deploy = Deployment.get("metrics-server", namespace="kube-system")
deploy.scale(1)
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Deployment

deploy = await Deployment.get("metrics-server", namespace="kube-system")
await deploy.scale(1)
```
````

`````

### List Pods by label selector

Get all Pods from all Namespaces matching a label selector.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

selector = {'component': 'kube-scheduler'}

for pod in kr8s.get("pods", namespace=kr8s.ALL, label_selector=selector):
    print(pod.namespace, pod.name)
```
````

````{tab-item} Async
:sync: async
```python
import kr8s

selector = {'component': 'kube-scheduler'}

for pod in await kr8s.asyncio.get("pods", namespace=kr8s.ALL, label_selector=selector):
    print(pod.namespace, pod.name)
```
````

`````

### Add a label to a Pod

Add the label `foo` with the value `bar` to an existing Pod.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod("kube-apiserver", namespace="kube-system")
pod.label({"foo": "bar"})
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod("kube-apiserver", namespace="kube-system")
await pod.label({"foo": "bar"})
```
````

`````
### Generate a Pod

Generate a simple Pod with a couple of keyword arguments.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod.gen(name="example-1", image="nginx:latest")
pod.create()
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.gen(name="example-1", image="nginx:latest")
await pod.create()
```
````

`````

### Cordon a Node

Cordon a Node to mark it as unschedulable.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Node

node = Node("k8s-node-1")

node.cordon()
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Node

node = await Node("k8s-node-1")

await node.cordon()
```
````

`````

### Pod Exec

Exec a command in a Pod.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod.get("my-pod")

command = pod.exec(["uptime"])
print(command.stdout.decode())
# 13:49:05 up 23:03,  0 users,  load average: 0.66, 0.87, 0.85
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod")

command = await pod.exec(["uptime"])
print(command.stdout.decode())
# 13:49:05 up 23:03,  0 users,  load average: 0.66, 0.87, 0.85
```
````

`````

### Port forward a Pod

Open a port forward to a Pod as a background task/thread.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod.get("my-pod")
# Listen on port 5678 on 127.0.0.1, forwarding to 5000 in the pod
pf = pod.portforward(remote_port=5000, local_port=5678)


# Starts the port forward in a background thread
pf.start()

# Your other code goes here

# Optionally stop the port forward thread (it will exit with Python anyway)
pf.stop()
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod")
pf = pod.portforward(remote_port=1234, local_port=5678)

# Starts the port forward in a background task
await pf.start()

# Your other code goes here
# WARNING: Your code must be async and non-blocking as the port forward and your code are sharing the same event loop

# Optionally stop the port forward task (it will exit with Python anyway)
await pf.stop()
```
````

`````

### More examples

See the [Examples Documentation](examples/index) for a full set of examples.


```{toctree}
:maxdepth: 2
:caption: Getting Started
:hidden: true
Overview <self>
installation
examples/index
guides/index
```

```{toctree}
:maxdepth: 2
:caption: Foundations
:hidden: true
authentication
object
client
asyncio
```

```{toctree}
:maxdepth: 2
:caption: API Reference
:hidden: true
autoapi/kr8s/index
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
:caption: Development
:hidden: true
contributing
releasing
```
