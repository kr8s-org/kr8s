# Build an operator with `kopf`

In this guide we will build a controller using `kr8s` and [`kopf`](https://kopf.readthedocs.io/en/stable/) to read the operating system information from a {py:class}`Pod <kr8s.objects.Pod>` and add that metadata as labels.

[Kopf](https://kopf.readthedocs.io/en/stable/) is an excellent framework for building event driven controllers and it can work hand-in-hand with `kr8s` when you want to interact with Kubernetes resources directly.

## Controller

To create a controller with `kopf` we are going to create a Python file called `controller.py` and implement a single event-handler that will be called on new and existing Pods.

### Creating an event handler

To build our event-handler we are doing to define a function and use the `@kopf.on.resume` and `@kopf.on.create` decorators to set up listeners to trigger our function.

- `@kopf.on.create("pods")` will trigger our function when a new Pod is created.
- `@kopf.on.resume("pods")` will run on all existing Pods when the controller starts.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
# controller.py
import kopf


@kopf.on.resume("pods")
@kopf.on.create("pods")
def add_os_labels(body, logger, **kwargs):
    pass
```
````

````{tab-item} Async
:sync: async
```python
# controller.py
import kopf


@kopf.on.resume("pods")
@kopf.on.create("pods")
async def add_os_labels(body, logger, **kwargs):
    pass
```
````

`````

### Get a `kr8s` object for the resource being handled

Now we can import `kr8s` and convert the body of the resource that `kopf` gives us into a {py:class}`Pod <kr8s.objects.Pod>` object.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
# controller.py
import kopf
import kr8s
from kr8s.objects import Pod


@kopf.on.resume("pods")
@kopf.on.create("pods")
def add_os_labels(body, logger, **kwargs):
    pod = Pod(body)
```
````

````{tab-item} Async
:sync: async
```python
# controller.py
import kopf
import kr8s
from kr8s.asyncio.objects import Pod


@kopf.on.resume("pods")
@kopf.on.create("pods")
async def add_os_labels(body, logger, **kwargs):
    pod = await Pod(body)
```
````

`````

### Error checking

Now we can use `kr8s` to do some basic error checking:

- If the Pod does not exist it may have been deleted while our handler was being called, so we can just return.
- If the `os-release/id` label already exists for the Pod we can skip over applying it. The controller probably already applied this and then restarted at some point.
- If the Pod is not ready yet we can tell `kopf` to try again later by raising a `kopf.TemporaryError` exception.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
# controller.py
import kopf
import kr8s
from kr8s.objects import Pod


@kopf.on.resume("pods")
@kopf.on.create("pods")
def add_os_labels(body, logger, **kwargs):
    pod = Pod(body)

    # Pod was deleted while trying to add OS labels, give up
    if not pod.exists():
        return

    # Pod already has OS labels, skip
    if "os-release/id" in pod.labels:
        return

    # Pod is not ready yet, retry in a bit
    if not pod.ready():
        raise kopf.TemporaryError(f"Pod {pod.name} is not ready yet", delay=10)

    # TODO Add OS labels
```
````

````{tab-item} Async
:sync: async
```python
# controller.py
import kopf
import kr8s
from kr8s.asyncio.objects import Pod


@kopf.on.resume("pods")
@kopf.on.create("pods")
async def add_os_labels(body, logger, **kwargs):
    pod = await Pod(body)

    # Pod was deleted while trying to add OS labels, give up
    if not await pod.exists():
        return

    # Pod already has OS labels, skip
    if "os-release/id" in pod.labels:
        return

    # Pod is not ready yet, retry in a bit
    if not await pod.ready():
        raise kopf.TemporaryError(f"Pod {pod.name} is not ready yet", delay=10)

    # TODO Add OS labels
```
````

`````

### Get info from `/etc/os-release`

Now we can use {py:func}`Pod.exec() <kr8s.objects.Pod.exec()>` to get the operating system info from our Pod by calling `cat /etc/os-release`. If we can't do this then either `cat` or `/etc/os-release` may be missing from the image, in which case we can set the `os-release/id` to `unknown` and return.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
# controller.py
...

    # Get OS info
    try:
        output = pod.exec(["cat", "/etc/os-release"])
        os_info = output.stdout.decode()
    except kr8s.ExecError:
        logger.error(
            f"Failed to exec in pod {pod.name}, "
            "either cat is not included in the image or /etc/os-release is missing."
        )
        pod.label({"os-release/id": "unknown"})
        return

```
````

````{tab-item} Async
:sync: async
```python
# controller.py
...

    # Get OS info
    try:
        output = await pod.exec(["cat", "/etc/os-release"])
        os_info = output.stdout.decode()
    except kr8s.ExecError:
        logger.error(
            f"Failed to exec in pod {pod.name}, "
            "either cat is not included in the image or /etc/os-release is missing."
        )
        await pod.label({"os-release/id": "unknown"})
        return

```
````

`````

### Clean up labels and apply them

Lastly we can convert the contents of `/etc/os-release` into a dictionary of labels and apply them.

```{note}
Kubernetes has some constraints around valid keys/values in labels so we will need to clean things up a little with the Regex library `re`.
``````

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
# controller.py
import re

...

    # Clean OS labels
    labels = {}
    for label in os_info.splitlines():
        key, value = label.split("=")
        key = f"os-release/{key.lower().replace('_', '-')}"
        # Kubernetes only accepts label values with alphanumeric characters,
        # dots, dashes and underscores and a maximum length of 63 characters.
        value = re.sub("[^0-9a-zA-Z_.-]+", "", value)[:63]
        labels[key] = value

    # Apply OS labels
    pod.label(labels)
```
````

````{tab-item} Async
:sync: async
```python
# controller.py
import re

...

    # Clean OS labels
    labels = {}
    for label in os_info.splitlines():
        key, value = label.split("=")
        key = f"os-release/{key.lower().replace('_', '-')}"
        # Kubernetes only accepts label values with alphanumeric characters,
        # dots, dashes and underscores and a maximum length of 63 characters.
        value = re.sub("[^0-9a-zA-Z_.-]+", "", value)[:63]
        labels[key] = value

    # Apply OS labels
    await pod.label(labels)
```
````

`````

### Complete example

Now we can put this all together into our complete `controller.py`.

`````{tab-set}

````{tab-item} Sync
:sync: sync
```python
# controller.py
import re

import kopf
import kr8s
from kr8s.objects import Pod


@kopf.on.resume("pods")
@kopf.on.create("pods")
def add_os_labels(body, logger, **kwargs):
    pod = Pod(body)

    # Pod was deleted while trying to add OS labels, give up
    if not pod.exists():
        return

    # Pod already has OS labels, skip
    if "os-release/id" in pod.labels:
        return

    # Pod is not ready yet, retry in a bit
    if not pod.ready():
        raise kopf.TemporaryError(f"Pod {pod.name} is not ready yet", delay=10)

    # Get OS info
    try:
        output = pod.exec(["cat", "/etc/os-release"])
        os_info = output.stdout.decode()
    except kr8s.ExecError:
        logger.error(
            f"Failed to exec in pod {pod.name}, "
            "either cat is not included in the image or /etc/os-release is missing."
        )
        pod.label({"os-release/id": "unknown"})
        return

    # Clean OS labels
    labels = {}
    for label in os_info.splitlines():
        key, value = label.split("=")
        key = f"os-release/{key.lower().replace('_', '-')}"
        # Kubernetes only accepts label values with alphanumeric characters,
        # dots, dashes and underscores and a maximum length of 63 characters.
        value = re.sub("[^0-9a-zA-Z_.-]+", "", value)[:63]
        labels[key] = value

    # Apply OS labels
    pod.label(labels)
```
````

````{tab-item} Async
:sync: async
```python
# controller.py
import re

import kopf
import kr8s
from kr8s.asyncio.objects import Pod


@kopf.on.resume("pods")
@kopf.on.create("pods")
async def add_os_labels(body, logger, **kwargs):
    pod = await Pod(body)

    # Pod was deleted while trying to add OS labels, give up
    if not await pod.exists():
        return

    # Pod already has OS labels, skip
    if "os-release/id" in pod.labels:
        return

    # Pod is not ready yet, retry in a bit
    if not await pod.ready():
        raise kopf.TemporaryError(f"Pod {pod.name} is not ready yet", delay=10)

    # Get OS info
    try:
        output = await pod.exec(["cat", "/etc/os-release"])
        os_info = output.stdout.decode()
    except kr8s.ExecError:
        logger.error(
            f"Failed to exec in pod {pod.name}, "
            "either cat is not included in the image or /etc/os-release is missing."
        )
        await pod.label({"os-release/id": "unknown"})
        return

    # Clean OS labels
    labels = {}
    for label in os_info.splitlines():
        key, value = label.split("=")
        key = f"os-release/{key.lower().replace('_', '-')}"
        # Kubernetes only accepts label values with alphanumeric characters,
        # dots, dashes and underscores and a maximum length of 63 characters.
        value = re.sub("[^0-9a-zA-Z_.-]+", "", value)[:63]
        labels[key] = value

    # Apply OS labels
    await pod.label(labels)
```
````

`````

That's it! Our simple controller is implemented in less than 50 lines of Python and thanks to `kopf` and `kr8s` working hand-in-hand is very readable.

## Running

You can run the controller locally for development using the `kopf` module.

```console
$ python -m kopf run controller.py
kopf._core.engines.a [INFO    ] Initial authentication has been initiated.
kopf._core.engines.a [INFO    ] Initial authentication has finished.
...
```

## Testing

Now let's open a new Python session and create a Pod with {py:func}`Pod.gen() <kr8s.objects.Pod.gen()>` to test things out.

```python
>>> from kr8s.objects import Pod
>>> pod = Pod.gen(name="test-pod", image="nginx:latest")
>>> pod.create()
```

Now if we watch the logs of our controller we can see things happening.

```console
$ python -m kopf run controller.py
...
[ERROR   ] [default/test-pod] Handler 'add_os_labels' failed temporarily: Pod test-pod is not ready yet
[ERROR   ] [default/test-pod] Handler 'add_os_labels' failed temporarily: Pod test-pod is not ready yet
[INFO    ] [default/test-pod] Handler 'add_os_labels' succeeded.
[INFO    ] [default/test-pod] Creation is processed: 1 succeeded; 0 failed.
```

Then in our Python session we can refresh the object and have a look at the labels.

```python
>>> pod.refresh()
>>> print(pod.labels)
{'os-release/bug-report-url': 'httpsbugs.debian.org',
 'os-release/home-url': 'httpswww.debian.org',
 'os-release/id': 'debian',
 'os-release/name': 'DebianGNULinux',
 'os-release/pretty-name': 'DebianGNULinux12bookworm',
 'os-release/support-url': 'httpswww.debian.orgsupport',
 'os-release/version': '12bookworm',
 'os-release/version-codename': 'bookworm',
 'os-release/version-id': '12'}
```

## Deploying

Once you are finished developing and are ready to deploy your controller to your Kubernetes cluster persistently follow the [kopf documentation on packaging and deploying your controller](https://kopf.readthedocs.io/en/stable/deployment/). Just be sure to `pip install kr8s` in the container too!

```dockerfile
FROM python:3.11
ADD controller.py /src
RUN pip install kopf kr8s
CMD kopf run /src/controller.py --verbose
```
