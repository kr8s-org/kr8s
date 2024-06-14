# Client API

To interact with the Kubernetes API `kr8s` uses an {py:func}`API Client <kr8s.api>`. In most uses of `kr8s` you wont need to interact with this object yourself. Calling functions that communicate with Kubernetes will generate a client for you if one doesn't exist already or will use the existing client from the cache.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

version = kr8s.version()  # Look ma no client needed!
print(version)
```
````

````{tab-item} Async
:sync: async
```python
import kr8s

version = await kr8s.asyncio.version()  # Look ma no client needed!
print(version)
```
````

`````

However if you wish to be explicit you can handle the client yourself. To do this you would construct an API client object first and call methods on it.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

api = kr8s.api()
version = api.version()
print(version)
```
````

````{tab-item} Async
:sync: async
```python
import kr8s

api = await kr8s.asyncio.api()
version = await api.version()
print(version)
```
````

`````

```{tip}
Calling {py:func}`kr8s.api() <kr8s.api>` returns a cached instance of the {py:class}`API Client <kr8s.Api>`. In most use cases {py:func}`API Client <kr8s.api>` should be thought of as a singleton due to this [client caching](#client-caching).
```

You can also explicitly pass the client to new objects when you create them. Again this is optional.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s
from kr8s.objects import Pod

api = kr8s.api(kubeconfig="/foo/bar")

pod = Pod({...}, api=api)
```
````

````{tab-item} Async
:sync: async
```python
import kr8s
from kr8s.asyncio.objects import Pod

api = await kr8s.api(kubeconfig="/foo/bar")

pod = Pod({...}, api=api)
```
````

`````

## Low-level API calls

For situations where there may not be an appropriate method to call or you want to call the Kubernetes API directly you can use the {py:func}`.call_api() <kr8s.Api.call_api>` context manager.

To make API requests for resources more convenient `call_api` allows building the url via various kwargs.

```{warning}
The `call_api` method is only available via the [asynchronous API](asyncio). This is because it yields async objects from `httpx`.
```

For example to get all pods you could make the following low-level call.

```python
import kr8s.asyncio

api = await kr8s.asyncio.api()
async with api.call_api("GET", url="pods", namespace="") as r:
    pods_response = r.json()

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

## Timeouts

All API calls are made by `httpx` under the hood. There may be cases where you want to manually control the timeout of these requests, especially when interacting with clusters under a heavy load or are some distance away.

To set the timeout you can set the `.timeout` attribute on the API object. This value can be set to anything that the `timeout` keyword argument in `httpx` accepts.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

api = kr8s.api()
api.timeout = 10  # Set the default timeout for all calls to 10 seconds
```
````

````{tab-item} Async
:sync: async
```python
import kr8s

api = await kr8s.asyncio.api()
api.timeout = 10  # Set the default timeout for all calls to 10 seconds
```
````

`````

(client-caching)=

## Client caching

It is always recommended to create client objects via the {py:func}`kr8s.api() <kr8s.api>` or {py:func}`kr8s.asyncio.api() <kr8s.asyncio.api>` factory functions. In most use cases where you are interacting with a single Kubernetes cluster you can think of them as a singleton.

However, the factory function does support creating multiple clients and will only cache client objects that are created with the same arguments.


`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

api = kr8s.api(kubeconfig="/foo/bar")
api2 = kr8s.api(kubeconfig="/foo/bar")
# api2 is a pointer to api due to caching

api3 = kr8s.api(kubeconfig="/fizz/buzz")
# api3 is a new kr8s.Api instance as it was created with different arguments
```
````

````{tab-item} Async
:sync: async
```python
import kr8s

api = await kr8s.asyncio.api(kubeconfig="/foo/bar")
api2 = await kr8s.asyncio.api(kubeconfig="/foo/bar")
# api2 is a pointer to api due to caching

api3 = await kr8s.asyncio.api(kubeconfig="/fizz/buzz")
# api3 is a new kr8s.Api instance as it was created with different arguments
```
````

`````

Calling {py:func}`kr8s.api() <kr8s.api>` with no arguments will also return the first client from the cache if one exists. This is useful as you may want to explicitly create a client with custom auth at the start of your code and treat it like a singleton. The `kr8s` API makes use of this whenever instantiating objects with `api=None`.


`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
import kr8s

api = kr8s.api(kubeconfig="/foo/bar")
api2 = kr8s.api()
# api2 is a pointer to api due to caching

from kr8s.objects import Pod

pod = Pod.get("some-pod")
# pod.api is a pointer to api despite not being passed a reference due to caching
```
````

````{tab-item} Async
:sync: async
```python
import kr8s

api = await kr8s.asyncio.api(kubeconfig="/foo/bar")
api2 = await kr8s.asyncio.api()
# api2 is a pointer to api due to caching

from kr8s.asyncio.objects import Pod

pod = await Pod.get("some-pod")
# pod.api is a pointer to api despite not being passed a reference due to caching
```
````

`````

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
