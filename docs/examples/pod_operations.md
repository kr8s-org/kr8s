# Pod Operations

## Exec a command

Exec a command in a Pod.

`````{tab-set}

````{tab-item} Sync
```python
from kr8s.objects import Pod

pod = Pod.get("my-pod")

command = pod.exec(["uptime"])
print(command.stdout.decode())
# 13:49:05 up 23:03,  0 users,  load average: 0.66, 0.87, 0.85
```
````

````{tab-item} Async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod")

command = await pod.exec(["uptime"])
print(command.stdout.decode())
# 13:49:05 up 23:03,  0 users,  load average: 0.66, 0.87, 0.85
```
````

`````
