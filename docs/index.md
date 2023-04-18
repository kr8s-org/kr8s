# <img alt="kr8s" title="kr8s" src="_static/branding/text-trimmed.png" style="max-height: 100px" />

[![PyPI](https://img.shields.io/pypi/v/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - License](https://img.shields.io/pypi/l/kr8s)](https://pypi.org/project/kr8s/)

```{warning}
This is beta software and might not be ready for prime time.
```

A Kubernetes API for Python. Inspired by `kubectl`.

## Quickstart

### Installation

```console
$ pip install kr8s
```

### Client API

```python
import kr8s

api = kr8s.api()
pods = await api.get("pods")
```

### Object API

```python
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

