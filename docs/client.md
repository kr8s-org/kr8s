# Client API

To interact with the Kubernetes API `kr8s` uses an [API client](#kr8s.api). When calling functions that communicate with Kubernetes a client will be created for you, unless you want to handle it explicitly yourself.

```python
import kr8s

version = kr8s.version()
print(version)  # Prints out the version information from the Kubernetes cluster
```

To do this explicitly you would construct an API client object first.

```python
import kr8s

api = kr8s.api()
version = api.version()
print(version)  # Prints out the version information from the Kubernetes cluster
```

```{tip}
Calling [](#kr8s.api) returns a cached instance of [](#kr8s.Api). In most use cases [](#kr8s.api) should be thought of as a singleton due to [client caching](#client-caching).
```

The `kr8s` API is inspired by `kubectl` rather than the Kubernetes API directly as it's more likely that developers will be familiar with `kubectl`.

```python
import kr8s

pods = kr8s.get("pods", namespace=kr8s.ALL)

for pod in pods:
    print(pod.name)
```

## Low-level API calls

For situations where there may not be an appropriate method to call or you want to call the Kubernetes API directly you can use the [`api.call_api`](#kr8s.Api.call_api) context manager.

To make API requests for resources more convenience `call_api` allows building the url via various kwargs.

```{note}
Note that `call_api` is only available via the [asynchronous API](asyncio).
```

For example to get all pods you could make the following low-level call.

```python
import kr8s.asyncio

api = await kr8s.asyncio.api()
async with api.call_api("GET", url="pods", namespace="") as r:
    pods_response = await r.json()

for pod in pods_response["items"]:
    print(pod["metadata"]["name"])
```

You can also just set the `base` kwarg with an empty `version` if you want to build the URL yourself.

```python
import kr8s.asyncio

api = await kr8s.asyncio.api()
async with api.call_api("GET", base="/version", version="") as r:
    version = await r.json()
print(version)
```

## Client caching

It is always recommended to create client objects via the [](#kr8s.api) factory function. In most use cases where you are interacting with a single Kubernetes cluster you can think of this as a singleton.

However, the factory function does support creating multiple clients and will only cache client objects that are created with the same arguments.

```python
import kr8s

api = kr8s.api(kubeconfig="/foo/bar")
api2 = kr8s.api(kubeconfig="/foo/bar")
# api2 is a pointer to api due to caching

api3 = kr8s.api(kubeconfig="/fizz/buzz")
# api3 is a new kr8s.Api instance as it was created with different arguments
```

Calling [](#kr8s.api) with no arguments will also return the first client from the cache if one exists. This is useful as you may want to explicitly create a client with custom auth at the start of your code and treat it like a singleton. The `kr8s` API makes use of this whenever instantiating objects with `api=None`.

```python
import kr8s

api = kr8s.api(kubeconfig="/foo/bar")
api2 = kr8s.api()
# api2 is a pointer to api due to caching
```

```python
from kr8s.objects import Pod

pod = Pod.get("some-pod")
# pod.api is a pointer to api despite not being passed a reference due to caching
```

````{danger}
If you have a strong requirement to avoid the cache, perhaps the `KUBECONFIG` env var gets modified between calls to `kr8s.api()` and you need it to return different clients, then you can bypass the factory and instantiate [](#kr8s.Api) directly.

However, **this is not recommend** and will likely break caching everywhere so you'll need to be sure to pass your API client around.

```python
import kr8s

api = kr8s.Api(bypass_factory=True)
api2 = kr8s.Api(bypass_factory=True)
# api and api2 are different instances of kr8s.Api
```

```python
from kr8s.objects import Pod

pod = Pod.get("some-pod", api=api2)
# be sure to pass a reference around as caching will no longer work
```

````
