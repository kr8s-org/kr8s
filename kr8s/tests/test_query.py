import pytest

from dask_kubernetes.aiopykube import HTTPClient, KubeConfig
from dask_kubernetes.aiopykube.query import Query
from dask_kubernetes.aiopykube.objects import Pod


@pytest.mark.asyncio
async def test_pod_query(k8s_cluster):
    api = HTTPClient(KubeConfig.from_env())
    async for pod in Query(api, Pod, namespace="kube-system"):
        assert isinstance(pod, Pod)


@pytest.mark.asyncio
async def test_pod_objects(k8s_cluster):
    api = HTTPClient(KubeConfig.from_env())
    async for pod in Pod.objects(api).filter(namespace="kube-system"):
        assert isinstance(pod, Pod)
