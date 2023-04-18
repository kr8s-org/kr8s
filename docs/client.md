# Client API

The [kr8s API client](#kr8s.api) can be used to interact directly with the Kubernetes API.

```python
import kr8s

api = kr8s.api()

version = await api.version()
print(version)
```

```{note}
Calling [](#kr8s.api) returns an instance of [](#kr8s._api.Kr8sApi). We do not recommend instantiating this object directly and encourage you to use the [](#kr8s.api) factory function in order to benefit from [client caching](#client-caching).
```

The client API is inspired by `kubectl` rather than the Kubernetes API directly as it's more likely that developers will be familiar with `kubectl`.

```python
import kr8s

api = kr8s.api()
pods = await api.get("pods", namespace=kr8s.ALL)

for pod in pods:
    print(pod.name)
```

## Low-level API calls

For situations where there may not be an appropriate method to call or you want to call the Kubernetes API directly you can use the [`api.call_api`](#kr8s.Kr8sApi.call_api) context manager.

To make API requests for resources more convenience `call_api` allows building the url via various kwargs.

For example to get all pods you could make the following low-level call.

```python
import kr8s

api = kr8s.api()
async with api.call_api("GET", url="pods", namespace="") as r:
    pods_response = await r.json()

for pod in pods_response["items"]:
    print(pod["metadata"]["name"])
```

You can also just set the `base` kwarg with an empty `version` if you want to build the URL yourself.

```python
import kr8s

api = kr8s.api()
async with api.call_api("GET", base="/version", version="") as r:
    version = await r.json()
print(version)
```

## Client caching

It is always recommended to create client objects via the [](#kr8s.api) factory function.

This function will cache client objects that are created with the same arguments.

```python
import kr8s

api = kr8s.api(kubeconfig="/foo/bar")
api2 = kr8s.api(kubeconfig="/foo/bar")
# api2 is api due to caching

api3 = kr8s.api(kubeconfig="/fizz/buzz")
# api3 is not api or api2 because it was created with different arguments
```

Calling [](#kr8s.api) with no arguments will also return the first client from the cache if one exists. This is useful as you may want to explicitly create a client with custom auth at the start of your code and treat it like a singleton. The Object API makes use of this when instantiating objects.

```python
import kr8s

api = kr8s.api(kubeconfig="/foo/bar")
api2 = kr8s.api()
# api2 is api due to caching
```
