import pytest

from kr8s import HTTPClient, KubeConfig
from kr8s.query import Query
from kr8s.objects import Pod


async def test_pod_query():
    api = HTTPClient(KubeConfig.from_env())
    async for pod in Query(api, Pod, namespace="kube-system"):
        assert isinstance(pod, Pod)


async def test_pod_objects():
    api = HTTPClient(KubeConfig.from_env())
    async for pod in Pod.objects(api).filter(namespace="kube-system"):
        assert isinstance(pod, Pod)
