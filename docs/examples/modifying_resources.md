# Modifying Resources

## Scale a Deployment

Scale the Deployment `metrics-server` in the Namespace `kube-system` to `1` replica.

`````{tab-set}

````{tab-item} Sync
```python
from kr8s.objects import Deployment

deploy = Deployment.get("metrics-server", namespace="kube-system")
deploy.scale(1)
```
````

````{tab-item} Async
```python
from kr8s.asyncio.objects import Deployment

deploy = await Deployment.get("metrics-server", namespace="kube-system")
await deploy.scale(1)
```
````

`````

## Add a label to a Pod

Add the label `foo` with the value `bar` to an existing Pod.

`````{tab-set}

````{tab-item} Sync
```python
from kr8s.objects import Pod

pod = Pod("kube-apiserver", namespace="kube-system")
pod.label({"foo": "bar"})
```
````

````{tab-item} Async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod("kube-apiserver", namespace="kube-system")
await pod.label({"foo": "bar"})
```
````

`````

## Cordon a Node

Cordon a Node to mark it as unschedulable.

`````{tab-set}

````{tab-item} Sync
```python
from kr8s.objects import Node

node = Node("k8s-node-1")

node.cordon()
# Is equivalent to
# node.patch({"spec": {"unschedulable": True}})
```
````

````{tab-item} Async
```python
from kr8s.asyncio.objects import Node

node = await Node("k8s-node-1")

await node.cordon()
# Is equivalent to
# await node.patch({"spec": {"unschedulable": True}})
```
````

`````
