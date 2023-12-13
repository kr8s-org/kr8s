# Generating Resources

With `kubectl` you can call commands like `kubectl run nginx --image=nginx` which will generate the spec for a Pod and create it. Or you can generate a service with `kubectl create service clusterip my-cs --tcp=5678:8080`.

In `kr8s` we aim to provide similar functionality with a `.gen()` method on some objects which allow you to generate the spec of an object with a few keyword arguments.

## Generate a Pod

Generate a simple {py:class}`Pod <kr8s.objects.Pod>` with a couple of keyword arguments using {py:func}`Pod.gen() <kr8s.objects.Pod.gen()>` and create it.

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
