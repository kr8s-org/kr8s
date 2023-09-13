# Listing resources

## List Nodes

Print out all of the node names in the cluster.

`````{tab-set}

````{tab-item} Sync
```python
import kr8s

for node in kr8s.get("nodes"):
    print(node.name)
```
````

````{tab-item} Async
```python
import kr8s.asyncio

for node in await kr8s.asyncio.get("nodes"):
    print(node.name)
```
````

`````

## List Pods in all Namespaces

List all Pods in all namespaces and print their IP, namespace and name.

`````{tab-set}

````{tab-item} Sync
```python
import kr8s

for pod in kr8s.get("pods", namespace=kr8s.ALL):
    print(pod.status.podIP, pod.metadata.namespace, pod.metadata.name)
```
````

````{tab-item} Async
```python
import kr8s

for pod in await kr8s.asyncio.get("pods", namespace=kr8s.ALL):
    print(pod.status.podIP, pod.metadata.namespace, pod.metadata.name)
```
````

`````

## List Ready Pods

Get a list of Pod resources that have the `Ready=True` condition.

`````{tab-set}

````{tab-item} Sync
```python
import kr8s

for pod in kr8s.get("pods", namespace="kube-system"):
    if pod.ready():
        print(pod.name)
```
````

````{tab-item} Async
```python
import kr8s

for pod in await kr8s.asyncio.get("pods", namespace="kube-system"):
    if await pod.ready():
        print(pod.name)
```
````

`````

## List Pods by label selector

Starting from a dictionary containing a label selector get all Pods from all Namespaces matching that label.

`````{tab-set}

````{tab-item} Sync
```python
import kr8s

selector = {'component': 'kube-scheduler'}

for pod in kr8s.get("pods", namespace=kr8s.ALL, label_selector=selector):
    print(pod.namespace, pod.name)
```
````

````{tab-item} Async
```python
import kr8s

selector = {'component': 'kube-scheduler'}

for pod in await kr8s.asyncio.get("pods", namespace=kr8s.ALL, label_selector=selector):
    print(pod.namespace, pod.name)
```
````

`````

## List Running Pods

Get a list of Pod resources that have `status.phase=Running` using a field selector.

`````{tab-set}

````{tab-item} Sync
```python
import kr8s

for pod in kr8s.get("pods", namespace="kube-system", field_selector="status.phase=Running"):
    print(pod.name)
```
````

````{tab-item} Async
```python
import kr8s

for pod in await kr8s.asyncio.get("pods", namespace="kube-system", field_selector="status.phase=Running"):
    print(pod.name)
```
````

`````

## List Pods sorted by restart count

List Pods and sort them by their restart count.

`````{tab-set}

````{tab-item} Sync
```python
import kr8s

pods = kr8s.get("pods", namespace=kr8s.ALL)
pods.sort(key=lambda pod: pod.status.containerStatuses[0].restartCount, reverse=True)

for pod in pods:
    print(pod.name, pod.status.containerStatuses[0].restartCount)
```
````

````{tab-item} Async
```python
import kr8s

pods = await kr8s.asyncio.get("pods", namespace=kr8s.ALL)
pods.sort(key=lambda pod: pod.status.containerStatuses[0].restartCount, reverse=True)

for pod in pods:
    print(pod.name, pod.status.containerStatuses[0].restartCount)
```
````

`````
