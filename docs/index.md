# <img alt="kr8s" title="kr8s" src="_static/branding/text-trimmed.png" style="max-height: 100px" />

[![PyPI](https://img.shields.io/pypi/v/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - License](https://img.shields.io/pypi/l/kr8s)](https://pypi.org/project/kr8s/)

A simple, extensible Python client library for Kubernetes that feels familiar for folks who already know how to use `kubectl`.

## Highlights

- API inspired by `kubectl` to reduce developer learning curve.
- [Sensible defaults](https://docs.kr8s.org/en/latest/authentication.html) to reduce boiler plate.
- No swagger generated code, human readable code only.
- Supports both [async/await](https://docs.kr8s.org/en/latest/asyncio.html) and sync APIs.
- [Client caching](https://docs.kr8s.org/en/latest/client.html#client-caching) to reduce passing API objects around.
- Batteries included by providing useful utilities and methods inspired by `kubectl`.

## Quickstart

### Installation

```console
$ pip install kr8s
```

### Client API

```python
import kr8s

api = kr8s.api()
pods = api.get("pods")
```

See the [Client API docs](https://docs.kr8s.org/en/latest/client.html) for more examples.

### Object API

```python
from kr8s.objects import Pod

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

See the [Object API docs](https://docs.kr8s.org/en/latest/object.html) for more examples.


```{toctree}
:maxdepth: 2
:caption: Getting Started
:hidden: true
installation
```

```{toctree}
:maxdepth: 2
:caption: Foundations
:hidden: true
authentication
client
object
asyncio
```

```{toctree}
:maxdepth: 2
:caption: Development
:hidden: true
contributing
releasing
```

```{toctree}
:maxdepth: 2
:caption: Misc
:hidden: true
branding
history
```


```{toctree}
:maxdepth: 2
:caption: API Reference
:hidden: true
autoapi/kr8s/index
```

