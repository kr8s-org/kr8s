# Generating resources

With `kubectl` you can call commands like `kubectl run nginx --image=nginx` which will generate the spec for a Pod and create it. Or you can generate a service with `kubectl create service clusterip my-cs --tcp=5678:8080`.

In `kr8s` we aim to provide similar functionality with a `.gen()` method on some objects which allow you to generate the spec of an object with a few keyword arguments.

## Generating a Pod

`````{tab-set}

````{tab-item} Sync
```python
from kr8s.objects import Pod

pod = Pod.gen(name="example-1", image="nginx:latest")
pod.create()
```
````

````{tab-item} Async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.gen(name="example-1", image="nginx:latest")
await pod.create()
```
````

`````
