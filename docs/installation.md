# Installation

## Pip

You can install `kr8s` from PyPI using `pip`.

```console
$ pip install kr8s
```

## Conda

You can also install `kr8s` from conda-forge.

```console
$ conda install -c conda-forge kr8s
```

## Supported Kubernetes Versions

We endeavor to support all Kubernetes versions that are [actively supported by the Kubernetes community](https://kubernetes.io/releases/) and popular cloud hosted Kubernetes platforms.

For each version of Kubernetes we check the following end of life dates:
- [Open Source Kubernetes Maintenance Support](https://endoflife.date/kubernetes)
- [Google Kubernetes Engine Maintenance Support](https://endoflife.date/google-kubernetes-engine)
- [Amazon EKS End of Support](https://endoflife.date/amazon-eks)
- [Azure Kubernetes Service End of Support (not including LTS extensions)](https://endoflife.date/azure-kubernetes-service)

Once a version has reached end of life from all providers we remove it from our CI/testing matrix.

Typically new versions are released 3-4 times a year and each version receives 12-15 months of support.
