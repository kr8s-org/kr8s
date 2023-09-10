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
