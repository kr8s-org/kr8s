# Asyncio

`kr8s` uses `asyncio` under the hood when interacting with the Kubernetes API. However, it exposes a standard synchronous API by default.

```python
import kr8s

api = kr8s.api()
pods = api.get("pods")
```

For users that want it the `asyncio` API is also available via `kr8s.asyncio`.

```python
import kr8s.asyncio

api = kr8s.asyncio.api()
pods = await api.get("pods")
```

Submodules including `kr8s.objects` and `kr8s.portforward` also have `asyncio` equivalents at `kr8s.asyncio.objects` and `kr8s.asyncio.portforward`.

```python
from kr8s.asyncio.object import Pod

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

await pod.create()
```
