# Asyncio

`kr8s` is built using async/await under the hood when interacting with the Kubernetes API. However, it exposes a standard synchronous API by default.

```python
import kr8s

pods = kr8s.get("pods")
```

For users that want to use it with `asyncio` or `trio` you can find the async API is also available via `kr8s.asyncio`.

```python
import kr8s.asyncio

pods = await kr8s.asyncio.get("pods")
```

Submodules including `kr8s.objects` and `kr8s.portforward` also have `asyncio` equivalents at `kr8s.asyncio.objects` and `kr8s.asyncio.portforward`.

```python
from kr8s.asyncio.object import Pod

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
