# kr8s

[![PyPI](https://img.shields.io/pypi/v/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - Wheel](https://img.shields.io/pypi/wheel/kr8s)](https://pypi.org/project/kr8s/)
[![PyPI - License](https://img.shields.io/pypi/l/kr8s)](https://pypi.org/project/kr8s/)

```{warning}
This is beta software and might not be ready for prime time.
```

A Kubernetes API for Python.

## Quickstart

```console
$ pip install kr8s
```

```python
import kr8s

api = kr8s.api()
pods = await api.get("pods")
```

## History

This project was originally spun out from [dask-kubernetes](https://github.com/dask/dask-kubernetes) which provides utilities for deploying [Dask](https://www.dask.org/) clusters on Kubernetes.

The `dask-kubernetes` project used a mix of [kubernetes](https://github.com/kubernetes-client/python), [kubernetes-asyncio](https://github.com/tomplus/kubernetes_asyncio) and [pykube-ng](https://codeberg.org/hjacobs/pykube-ng) (and some subprocess calls to [kubectl](https://kubernetes.io/docs/reference/kubectl/)) to interact with the Kubernetes API. It also contained a whole load of glue code to work around missing features and get everything working together.

To improve maintenance and code reuse `kr8s` was born to extract the Kubernetes library code in `dask-kubernetes` and replace it with something simpler and more complete. Thank you to everyone who contributed to `dask-kubernetes` and we hope you contribute to `kr8s` too.


```{toctree}
:maxdepth: 2
:caption: Contents:
```
