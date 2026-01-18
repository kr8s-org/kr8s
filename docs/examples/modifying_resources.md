# Modifying Resources

## Modify fields with Apply

Apply changes to a resource using {py:func}`Resource.apply() <kr8s.objects.Resource.apply()>`. For example, updating the resource limits of a deployment.

`````{tab-set}

````{tab-item} Sync
:sync:
```python
from kr8s.objects import Deployment

deploy = Deployment.get("my-deployment")
deploy.apply({"spec": { "template": {"spec": {"containers": [{"resources": {"limits": {"memory": "5Gi"}}}]}}}})
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Deployment

deploy = await Deployment.get("my-deployment")
await deploy.apply({"spec": { "template": {"spec": {"containers": [{"resources": {"limits": {"memory": "5Gi"}}}]}}}})
```
````

`````

## Manage specific fields with Server-Side Apply

[Server-Side Apply](https://kubernetes.io/docs/reference/using-api/server-side-apply/) allows for fine-grained management of specific fields. 

## Patch Resources

Use {py:func}`Resource.patch() <kr8s.objects.Resource.patch()>` to patch a resource with a JSON 6902 patch. This is useful for making small changes to a resource, such as updating the image of a deployment.

`````{tab-set}

````{tab-item} Sync
:sync:

```python
import kr8s
from kr8s.objects import Deployment

deploy = Deployment.get("my-deployment")
deploy.patch([{"op": "replace", "path": "/spec/template/spec/containers/0/image", "value": "my-app:latest"}])
```
````

````{tab-item} Async
:sync: async
```python
import kr8s
from kr8s.asyncio.objects import Deployment

deploy = await Deployment.get("my-deployment")
await deploy.patch([{"op": "replace", "path": "/spec/template/spec/containers/0/image", "value": "my-app:latest"}])
```
````

`````

## Scale a Deployment

Scale the {py:class}`Depoyment <kr8s.objects.Deployment>` `metrics-server` using {py:func}`Deployment.scale() <kr8s.objects.Deployment.scale()>`
in the Namespace `kube-system` to `1` replica.

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

## Add Pod label

Add the label `foo` with the value `bar` to an existing {py:class}`Pod <kr8s.objects.Pod>` using {py:func}`Pod.label() <kr8s.objects.Pod.label()>`.

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

## Replace all Pod labels

Using the [JSON 6902](https://jsonpatch.com/) style patching replace all {py:class}`Pod <kr8s.objects.Pod>` labels with `{"patched": "true"}` using {py:func}`Pod.patch() <kr8s.objects.Pod.patch()>`.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod("my-pod", namespace="kube-system")
pod.patch(
    [{"op": "replace", "path": "/metadata/labels", "value": {"patched": "true"}}],
    type="json",
)
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod("my-pod", namespace="kube-system")
await pod.patch(
    [{"op": "replace", "path": "/metadata/labels", "value": {"patched": "true"}}],
    type="json",
)
```
````

`````

## Cordon a Node

Cordon a {py:class}`Node <kr8s.objects.Node>` to mark it as unschedulable with {py:func}`Node.cordon() <kr8s.objects.Node.cordon()>`.

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
