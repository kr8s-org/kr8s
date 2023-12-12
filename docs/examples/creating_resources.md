# Creating Resources

## Create a Pod

Create a new {py:class}`Pod <kr8s.objects.Pod>`.

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

## Create a Pod and wait for it to be ready

Create a new {py:class}`Pod <kr8s.objects.Pod>` and wait for it to be ready. There are two common patterns for implementing this.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod(...)
pod.create()

# Option 1: Block until ready, similar to kubectl wait
pod.wait("condition=Ready")

# Option 2: Poll readiness
import time
while not pod.ready():
    time.sleep(1)
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod(...)
await pod.create()

# Option 1: Block until ready, similar to kubectl wait
await pod.wait("condition=Ready")

# Option 2: Poll readiness
import asyncio
while not await pod.ready():
    await asyncio.sleep(1)
```
````

`````

## Create a Secret

Create a {py:class}`Secret <kr8s.objects.Secret>` with several keys.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from base64 import b64encode
from kr8s.objects import Secret

secret = Secret({
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": "mysecret",
        },
        "type": "Opaque",
        "data": {
            "password": b64encode("s33msi4".encode()).decode(),
            "username": b64encode("jane".encode()).decode(),
        },
    })

secret.create()
```
````

````{tab-item} Async
:sync: async
```python
from base64 import b64encode
from kr8s.asyncio.objects import Secret

secret = await Secret({
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {
            "name": "mysecret",
        },
        "type": "Opaque",
        "data": {
            "password": b64encode("s33msi4".encode()).decode(),
            "username": b64encode("jane".encode()).decode(),
        },
    })

await secret.create()
```
````

`````

## Validate a Pod

Validate the schema of a {py:class}`Pod <kr8s.objects.Pod>` before creating it.

```{hint}
`kr8s` does not perform client-side validation of object schemas, instead it behaves like `kubectl` and relies on server-side validation. However, if you have the [`kubernetes-validate>=1.28.1`](https://pypi.org/project/kubernetes-validate/) package installed you can easily check it yourself.
```

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kubernetes_validate
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

kubernetes_validate.validate(pod, "1.28")
pod.create()
```
````

````{tab-item} Async
:sync: async
```python
import kubernetes_validate
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

kubernetes_validate.validate(pod, "1.28")
await pod.create()
```
````

`````
