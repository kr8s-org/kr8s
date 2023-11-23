# Creating Resources

## Create a Pod

Create a new {py:class}`Pod <kr8s.objects.Pod>`.

`````{tab-set}

````{tab-item} Sync
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

## Create a Secret

Create a {py:class}`Secret <kr8s.objects.Secret>` with several keys.

`````{tab-set}

````{tab-item} Sync
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
