# Inspecting Resources

## Read Pod logs

Print out the logs from a {py:class}`Pod <kr8s.objects.Pod>` using {py:func}`Pod.logs() <kr8s.objects.Pod.logs()>`.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod.get("my-pod", namespace="ns")
for line in pod.logs():
    print(line)
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod", namespace="ns")
async for line in pod.logs():
    print(line)
```
````

`````


## Follow Pod logs until a timeout

Print out all the logs from a {py:class}`Pod <kr8s.objects.Pod>` using {py:func}`Pod.logs() <kr8s.objects.Pod.logs()>` and keep following until a timeout or the Pod is deleted.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod.get("my-pod", namespace="ns")
for line in pod.logs(follow=True, timeout=3600):
    print(line)
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod", namespace="ns")
async for line in pod.logs(follow=True, timeout=3600):
    print(line)
```
````

`````
