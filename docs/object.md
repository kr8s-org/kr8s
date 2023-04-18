# Object API

Responses from the Client API are usually objects from `kr8s.object` which represent Kubernetes resources.

```python
import kr8s

api = kr8s.api()
pods = await api.get("pods", namespace=kr8s.ALL)
pod = pods[0]
print(type(pod))
# <class 'kr8s.objects.Pod'>
```

These objects contain the raw response at `Object.raw`.

```python
print(pod.raw)
# {'metadata': ..., 'spec': ..., 'status': ...}
```

Objects also have helper methods for interacting with Kubernetes resources.

```python
# Patch the Pod
await pod.patch({"metadata": {"labels": {"foo": "bar"}}})

# Check the Pod exists
await pod.exists()
# True

# Update the object with the latest state from the API
await pod.refresh()

# Delete the Pod
await pod.delete()
```

Some objects also have additional methods that are unique to them.

```python
# Get Pod logs
logs = await pod.logs()

# Check if Pod containers are ready
await pod.ready()
# True
```

## Client references

All objects returned from client methods will have a reference to the client that created it at `Object.api`.

You can also create objects yourself from a spec or partial-spec. You don't necessarily need to create an API client first to do this.

```python
# Create a new Pod
from kr8s.object import Pod

pod = Pod({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "my-pod",
        },
        "spec": {
            "containers": [{"name": "pause", "image": "gcr.io/google_containers/pause",}]
        },
    })

await pod.create()
```

Get a Pod reference from the metadata.

```python
from kr8s.object import Pod

pod = Pod({
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "my-pod",
            "namespace": "default",
        },
    })

await pod.refresh()
```

When creating new objects they will not have a client reference because they are created directly. In this case the object will call the `kr8s.api()` factory function which will either create a new client if none exists or will grab the first client from the cache if one was created somewhere else in your code.

```python
import kr8s
from kr8s.object import Pod

api = kr8s.api(kubeconfig="/foo/bar")

pod = Pod({...})
# pod.api is api due to client caching
```

You can also explicitly pass an API client to the object when you create it.

```python
import kr8s
from kr8s.object import Pod

api = kr8s.api(kubeconfig="/foo/bar")

pod = Pod({...}, api=api)
```

## Creating new objects

We have provided common Kubernetes objects like `Pod`, `Service`, `Deployment`, etc in the `kr8s.objects` submodule but not all objects are represented. This helps to keep the library lightweight and also reduces maintenance overhead in the future as resources are added/removed. There is also no way we can represent everything as custom resources extend the Kubernetes API almost infinitely.

Instead we have focused on making the API extensible so that if there isn't a built-in object for the resource you want to work with it is quick to add in your own code.


### Extending the objects API

To create your own objects you can subclass `kr8s.objects.APIObject` and at a minimum set the API `version`, API `endpoint`, the `kind` and whether it is `namespaced`. These will be used when constructing API calls by the API client.

```python
from kr8s.objects import APIObject

class CustomObject(APIObject):
    """A Kubernetes CustomObject."""

    version = "example.org"
    endpoint = "customobject"
    kind = "CustomObject"
    namespaced = True
```

The `APIObject` base class contains helper methods such as `.create()`, `.delete()`, `.patch()`, `.exists()`, etc.

There are also optional helpers that can be enabled for resources that support them. For example you can enable `.scale()` for resources which support updating the number of replicas.

```python
from kr8s.objects import APIObject

class CustomScalableObject(APIObject):
    """A Kubernetes CustomScalableObject."""

    version = "example.org"
    endpoint = "customscalableobject"
    kind = "CustomScalableObject"
    namespaced = True
    scalable = True
    scalable_spec = "replicas"  # The spec key to patch when scaling
```

Some objects such as `Pod`, `Node`, `Service` and `Deployment` have additional custom methods such as `Pod.logs()` and `Deployment.ready()` which have been implemented for convenience. It might make sense for you to implement your own utilities on your custom classes.

### Using custom objects with the client API

When making API calls with the [client API](client) some methods such as `api.get("pods")` will want to return kr8s objects, in this case a `Pod`. The client handles this by looking up all of the subclasses of `APIObject` and matching the `kind` against the kind returned by the API. If the API returns a kind of object that there is no kr8s object to deserialize into it will raise an exception.

When you create your own custom objects that subclass `APIObject` the client is then able to use those objects in its response.

```python
import kr8s
from kr8s.objects import APIObject

class CustomObject(APIObject):
    """A Kubernetes CustomObject."""

    version = "example.org"
    endpoint = "customobject"
    kind = "CustomObject"
    namespaced = True

api = kr8s.api()

cos = await api.get("customobjects")  # Will return a list of CustomObject instances
```

```{note}
If multiple subclasses of `APIObject` are created with the same API version and kind the first one registered will be used.
```

