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

## Exec a command and redirect stdout/stderr

Exec a command in a Pod and write the output to `sys.stdout` and `sys.stderr`.


`````{tab-set}

````{tab-item} Sync
```python
import sys
from kr8s.objects import Pod

pod = Pod.get("my-pod")

# Call `ls /` and direct stdout/stderr to the current process
# Also skip checking the return code of the command to avoid raising an exception
pod.exec(["ls", "/"], stdout=sys.stdout.buffer, stderr=sys.stderr.buffer, check=False)
```
````

````{tab-item} Async
```python
import sys
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod")

# Call `ls /` and direct stdout/stderr to the current process
# Also skip checking the return code of the command to avoid raising an exception
await pod.exec(["ls", "/"], stdout=sys.stdout.buffer, stderr=sys.stderr.buffer, check=False)
```
````

`````
