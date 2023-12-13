# Asyncio

`kr8s` is built using async/await under the hood when interacting with the Kubernetes API. However, it exposes a standard synchronous API by default.

```python
import kr8s

pods = kr8s.get("pods")
```

The standard API works by creating a background thread with it's own event loop running. Then internally the `kr8s` sync API submits all coroutine calls to this external event loop for execution and then returns the result.

```{note}
Running a separate event loop allows you to use the sync API even when already inside an async context without blocking up the existing event loop. The most common situation this happens is when using [IPython](https://ipython.org/) or [Jupyter](https://jupyter.org/) which places your REPL inside a running event loop, but this doesn't mean everyone wants to do async programming in those environments.
```

## `kr8s.asyncio` submodule

For users that want to use `kr8s` with `asyncio` or `trio` you can find the async API is directly available via `kr8s.asyncio`.

```python
import kr8s.asyncio

pods = await kr8s.asyncio.get("pods")
```

Submodules including `kr8s.objects` and `kr8s.portforward` also have `asyncio` equivalents at `kr8s.asyncio.objects` and `kr8s.asyncio.portforward`.

## Documentation examples

Throughout the `kr8s` documentation we strive to provide code examples using both the sync and async APIs, you will see tab selectors like this which allows you to easily compare the two APIs and choose the one you wish to use.

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
