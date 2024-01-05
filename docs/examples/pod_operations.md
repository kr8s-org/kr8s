# Pod Operations

## Exec a command

Exec a command in a {py:class}`Pod <kr8s.objects.Pod>` using {py:func}`Pod.exec() <kr8s.objects.Pod.exec()>`.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod.get("my-pod")

command = pod.exec(["uptime"])
print(command.stdout.decode())
# 13:49:05 up 23:03,  0 users,  load average: 0.66, 0.87, 0.85
```
````

````{tab-item} Async
:sync: async
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

Run a command in a {py:class}`Pod <kr8s.objects.Pod>` using {py:func}`Pod.exec() <kr8s.objects.Pod.exec()>` and write the output to `sys.stdout` and `sys.stderr`.


`````{tab-set}

````{tab-item} Sync
:sync: sync
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
:sync: async
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

## Open a port forward and communicate with the Pod

Open a port forward with {py:class}`Pod <kr8s.objects.Pod>` using {py:func}`Pod.portforward() <kr8s.objects.Pod.portforward()>` and communicate with the application on the other side.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import requests
from kr8s.objects import Pod

pod = Pod.get("my-pod")

with pod.portforward(remote_port=1234) as local_port:
    # Make an API request
    resp = requests.get(f"http://localhost:{local_port}")
    # Do something with the response

# Listen on port 8888 on all addresses, forwarding to 5000 in the pod
with pod.portforward(remote_port=5000, local_port=8888, address=["0.0.0.0"])
    # Make an API request
    resp = requests.get(f"http://0.0.0.0:{local_port}")
    # Do something with the response
  
# Listen on port 8888 on localhost and selected IP, forwarding to 5000 in the pod
pf = pod.portforward(port=5000, local_port=8888, address=["127.0.0.1", "10.19.21.1"])
    # Make an API request
    resp = requests.get(f"http://10.19.21.1:{local_port}")
    # Do something with the response
    
```
````

````{tab-item} Async
:sync: async
```python
import httpx
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod")

async with pod.portforward(remote_port=1234) as local_port, httpx.AsyncClient() as client:
    # Make an API request
    resp = await client.get(f"http://localhost:{local_port}")
    # Do something with the response
```
````

`````

```{tip}
This also works with {py:class}`Service <kr8s.objects.Service>` objects.
```

## Open a port forward permanently

Open a port forward with {py:class}`Pod <kr8s.objects.Pod>` using {py:func}`Pod.portforward() <kr8s.objects.Pod.portforward()>` and block. This is useful when you need to access the port forward from another process, like you would with `kubectl`.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod.get("my-pod")
pod.portforward(1234, local_port=5678).run_forever()
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod")
await pod.portforward(1234, local_port=5678).run_forever()
```
````

`````

```{tip}
This also works with {py:class}`Service <kr8s.objects.Service>` objects.
```

## Open a port forward in the background

Open a port forward with {py:class}`Pod <kr8s.objects.Pod>` using {py:func}`Pod.portforward() <kr8s.objects.Pod.portforward()>` as a background task/thread.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
from kr8s.objects import Pod

pod = Pod.get("my-pod")
pf = pod.portforward(remote_port=1234, local_port=5678)

# Starts the port forward in a background thread
pf.start()

# Your other code goes here

# Optionally stop the port forward thread (it will exit with Python anyway)
pf.stop()
```
````

````{tab-item} Async
:sync: async
```python
from kr8s.asyncio.objects import Pod

pod = await Pod.get("my-pod")
pf = pod.portforward(remote_port=1234, local_port=5678)

# Starts the port forward in a background task
await pf.start()

# Your other code goes here
# WARNING: Your code must be async and non-blocking as the port forward and your code are sharing the same event loop

# Optionally stop the port forward task (it will exit with Python anyway)
await pf.stop()
```
````

`````

```{tip}
This also works with {py:class}`Service <kr8s.objects.Service>` objects.
```
