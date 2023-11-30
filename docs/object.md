# Object API

Responses from the Client API are usually objects from {py:func}`kr8s.objects <kr8s.objects>` which represent Kubernetes resources.

```python
import kr8s

pods = kr8s.get("pods", namespace=kr8s.ALL)
pod = pods[0]
print(type(pod))
# <class 'kr8s.objects.Pod'>
```

In the above example the {py:func}`kr8s.get()` function returns a list of [](#kr8s.objects.Pod) objects.

## Attributes

These objects contain the raw response at {py:func}`.raw <kr8s.objects.APIObject.raw>`.

```python
print(pod.raw)
# {'metadata': ..., 'spec': ..., 'status': ...}
```

There are also a selection of other properties including {py:func}`.name <kr8s.objects.APIObject.name>`, {py:func}`.namespace <kr8s.objects.APIObject.namespace>`, {py:func}`.metadata <kr8s.objects.APIObject.metadata>`, {py:func}`.labels <kr8s.objects.APIObject.labels>`, {py:func}`.annotations <kr8s.objects.APIObject.annotations>` and more to make it convenient to access sections of this raw data.

```python
print(pod.name)
# 'foo'

print(pod.namespace)
# 'default'

print(pod.metadata)
# {...}

print(pod.labels)
# {...}

print(pod.annotations)
# {...}

# See the API reference for a complete list
```

## Methods

Objects also have helper methods like {py:func}`.patch() <kr8s.objects.APIObject.patch()>`, {py:func}`.exists() <kr8s.objects.APIObject.exists()>`, {py:func}`.refresh() <kr8s.objects.APIObject.refresh()>` and {py:func}`.delete() <kr8s.objects.APIObject.delete()>` for interacting with Kubernetes resources.

```python
# Patch the Pod
pod.patch({"metadata": {"labels": {"foo": "bar"}}})

# Check the Pod exists
pod.exists()
# True

# Update the object with the latest state from the API
pod.refresh()

# Delete the Pod
pod.delete()
```

Some objects also have additional methods that are unique to them. For example {py:class}`Pod <kr8s.objects.Pod>` has {py:func}`.logs() <kr8s.objects.Pod.logs()>`, {py:func}`.ready() <kr8s.objects.Pod.ready()>` and {py:func}`.exec() <kr8s.objects.Pod.exec()>`.

```python
# Get Pod logs
logs = [line for line in pod.logs()]

# Check if Pod containers are ready
pod.ready()
# True

# Exec a command in a Pod
pod.exec(["uptime"])
# CompletedExec(args=['uptime'], stdout=..., stderr=..., returncode=0)
```

## Client references

All objects returned by `kr8s` will have a reference to the API client that created it at `Object.api`.

You can also create objects yourself from a spec or get existing ones by name with {py:func}`.create() <kr8s.objects.APIObject.create()>`. 

Methods on objects that require communicating with Kubernetes will create an API client or retrieve one from the cache automatically.

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

pod.create()
```

Get a {py:class}`Pod <kr8s.objects.Pod>` reference by name with {py:func}`.get() <kr8s.objects.APIObject.get()>`.

```python
from kr8s.object import Pod

pod = Pod.get("my-pod")
```

When creating new objects they will not have a client reference because they are created directly. In this case the object will call the [](#kr8s.api) factory function which will either create a new client if none exists or will grab the first client from the cache if one was created somewhere else in your code.

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

We have provided common Kubernetes objects like [`Pod`](#kr8s.objects.Pod), [`Service`](#kr8s.objects.Service), [`Deployment`](#kr8s.objects.Deployment), etc in the [](#kr8s.objects) submodule but not all objects are represented. This helps to keep the library lightweight and also reduces maintenance overhead in the future as resources are added/removed. There is also no way we can represent everything as custom resources extend the Kubernetes API almost infinitely.

Instead we have focused on making the API extensible so that if there isn't a built-in object for the resource you want to work with it is quick to add in your own code.


### Extending the objects API

To create your own objects you can subclass [](#kr8s.objects.APIObject) and at a minimum set the API `version`, API `endpoint`, the `kind` and whether it is `namespaced`. These will be used when constructing API calls by the API client.

```python
from kr8s.objects import APIObject

class CustomObject(APIObject):
    """A Kubernetes CustomObject."""

    version = "example.org"
    endpoint = "customobject"
    kind = "CustomObject"
    namespaced = True
```

The [](#kr8s.objects.APIObject) base class contains helper methods such as `.create()`, `.delete()`, `.patch()`, `.exists()`, etc.

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

### Using custom objects with other `kr8s` functions

When using the [`kr8s` API](client) some methods such as `kr8s.get("pods")` will want to return kr8s objects, in this case a `Pod`. The API client handles this by looking up all of the subclasses of [`APIObject`](#kr8s.objects.APIObject) and matching the `kind` against the kind returned by the API. If the API returns a kind of object that there is no kr8s object to deserialize into it will raise an exception.

When you create your own custom objects that subclass [`APIObject`](#kr8s.objects.APIObject) the client is then able to use those objects in its response.

```python
import kr8s
from kr8s.objects import APIObject

class CustomObject(APIObject):
    """A Kubernetes CustomObject."""

    version = "example.org"
    endpoint = "customobject"
    kind = "CustomObject"
    namespaced = True

cos = kr8s.get("customobjects")  # Will return a list of CustomObject instances
```

```{note}
If multiple subclasses of [`APIObject`](#kr8s.objects.APIObject) are created with the same API version and kind the first one registered will be used.
```

## Interoperability with other libraries

If you are also using other Kubernetes client libraries including `kubernetes`, `kubernetes-asyncio`, `pykube-ng` or `lightkube` you can easily convert resource objects from those libraries to `kr8s` objects.

```python
import pykube

api = pykube.HTTPClient(pykube.KubeConfig.from_file())
pykube_pod = pykube.Pod.objects(api).filter(namespace="gondor-system").get(name="my-pod")
```

Objects from other libraries can be cast directly to `kr8s` objects.

```python
import kr8s

kr8s_pod = kr8s.objects.Pod(pykube_pod)
```

For some libraries including `pykube-ng` and `lightkube` we also have utility methods that support casting back again.

```python
pykube_pod = kr8s_pod.to_pykube(api)  # Pykube requires you to provide every object with an instance of HTTPClient so we pass it here
```
