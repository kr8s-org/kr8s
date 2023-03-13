from typing import Optional

from requests import Response


from pykube.http import HTTPClient
from pykube.objects import (
    ObjectManager,
    APIObject as _APIObject,
    NamespacedAPIObject as _NamespacedAPIObject,
    ConfigMap as _ConfigMap,
    CronJob as _CronJob,
    DaemonSet as _DaemonSet,
    Deployment as _Deployment,
    Endpoint as _Endpoint,
    Event as _Event,
    LimitRange as _LimitRange,
    ResourceQuota as _ResourceQuota,
    ServiceAccount as _ServiceAccount,
    Ingress as _Ingress,
    Job as _Job,
    Namespace as _Namespace,
    Node as _Node,
    Pod as _Pod,
    ReplicationController as _ReplicationController,
    ReplicaSet as _ReplicaSet,
    Secret as _Secret,
    Service as _Service,
    PersistentVolume as _PersistentVolume,
    PersistentVolumeClaim as _PersistentVolumeClaim,
    HorizontalPodAutoscaler as _HorizontalPodAutoscaler,
    StatefulSet as _StatefulSet,
    Role as _Role,
    RoleBinding as _RoleBinding,
    ClusterRole as _ClusterRole,
    ClusterRoleBinding as _ClusterRoleBinding,
    PodSecurityPolicy as _PodSecurityPolicy,
    PodDisruptionBudget as _PodDisruptionBudget,
    CustomResourceDefinition as _CustomResourceDefinition,
)
from dask_kubernetes.aiopykube.query import Query
from dask_kubernetes.aiopykube.mixins import AsyncScalableMixin, AsyncMixin


class AsyncObjectManager(ObjectManager):
    def __call__(self, api: HTTPClient, namespace: str = None):
        query = super().__call__(api=api, namespace=namespace)
        return query._clone(Query)


class AsyncObjectMixin(AsyncMixin):
    objects = AsyncObjectManager()

    async def exists(self, ensure=False):
        return await self._sync(super().exists, ensure=ensure)

    async def create(self):
        return await self._sync(super().create)

    async def reload(self):
        return await self._sync(super().reload)

    def watch(self):
        return super().watch()

    async def patch(self, strategic_merge_patch, *, subresource=None):
        return await self._sync(
            super().patch, strategic_merge_patch, subresource=subresource
        )

    async def update(self, is_strategic=True, *, subresource=None):
        return await self._sync(super().update, is_strategic, subresource=subresource)

    async def delete(self, propagation_policy: str = None):
        return await self._sync(super().delete, propagation_policy=propagation_policy)

    exists.__doc__ = _APIObject.exists.__doc__
    create.__doc__ = _APIObject.create.__doc__
    reload.__doc__ = _APIObject.reload.__doc__
    watch.__doc__ = _APIObject.watch.__doc__
    patch.__doc__ = _APIObject.patch.__doc__
    update.__doc__ = _APIObject.update.__doc__
    delete.__doc__ = _APIObject.delete.__doc__


class APIObject(AsyncObjectMixin, _APIObject):
    """APIObject."""


class NamespacedAPIObject(AsyncObjectMixin, _NamespacedAPIObject):
    """APIObject."""


class ConfigMap(AsyncObjectMixin, _ConfigMap):
    """ConfigMap."""


class CronJob(AsyncObjectMixin, _CronJob):
    """CronJob."""


class DaemonSet(AsyncObjectMixin, _DaemonSet):
    """DaemonSet."""


class Deployment(AsyncScalableMixin, AsyncObjectMixin, _Deployment):
    """Deployment."""

    async def rollout_undo(self, target_revision=None):
        return await self._sync(super().rollout_undo, target_revision)

    rollout_undo.__doc__ = _Deployment.rollout_undo.__doc__


class Endpoint(AsyncObjectMixin, _Endpoint):
    """Endpoint."""


class Event(AsyncObjectMixin, _Event):
    """Event."""


class LimitRange(AsyncObjectMixin, _LimitRange):
    """LimitRange."""


class ResourceQuota(AsyncObjectMixin, _ResourceQuota):
    """ResourceQuota."""


class ServiceAccount(AsyncObjectMixin, _ServiceAccount):
    """ServiceAccount."""


class Ingress(AsyncObjectMixin, _Ingress):
    """Ingress."""


class Job(AsyncScalableMixin, AsyncObjectMixin, _Job):
    """Job."""


class Namespace(AsyncObjectMixin, _Namespace):
    """Namespace."""


class Node(AsyncObjectMixin, _Node):
    """Node."""


class Pod(AsyncObjectMixin, _Pod):
    """Pod"""

    async def logs(self, *args, **kwargs):
        return await self._sync(super().logs, *args, **kwargs)

    logs.__doc__ = _Pod.logs.__doc__


class ReplicationController(
    AsyncScalableMixin, AsyncObjectMixin, _ReplicationController
):
    """ReplicationController."""


class ReplicaSet(AsyncScalableMixin, AsyncObjectMixin, _ReplicaSet):
    """ReplicaSet."""


class Secret(AsyncObjectMixin, _Secret):
    """Secret."""


class Service(AsyncObjectMixin, _Service):
    """Service."""

    async def proxy_http_request(self, *args, **kwargs):
        return await self._sync(super().proxy_http_request, *args, **kwargs)

    async def proxy_http_get(
        self, path: str, port: Optional[int] = None, **kwargs
    ) -> Response:
        return await self.proxy_http_request("GET", path, port, **kwargs)

    async def proxy_http_post(
        self, path: str, port: Optional[int] = None, **kwargs
    ) -> Response:
        return await self.proxy_http_request("POST", path, port, **kwargs)

    async def proxy_http_put(
        self, path: str, port: Optional[int] = None, **kwargs
    ) -> Response:
        return await self.proxy_http_request("PUT", path, port, **kwargs)

    async def proxy_http_delete(
        self, path: str, port: Optional[int] = None, **kwargs
    ) -> Response:
        return await self.proxy_http_request("DELETE", path, port, **kwargs)

    proxy_http_request.__doc__ = _Service.proxy_http_request.__doc__
    proxy_http_get.__doc__ = _Service.proxy_http_get.__doc__
    proxy_http_post.__doc__ = _Service.proxy_http_post.__doc__
    proxy_http_put.__doc__ = _Service.proxy_http_put.__doc__
    proxy_http_delete.__doc__ = _Service.proxy_http_delete.__doc__


class PersistentVolume(AsyncObjectMixin, _PersistentVolume):
    """PersistentVolume."""


class PersistentVolumeClaim(AsyncObjectMixin, _PersistentVolumeClaim):
    """PersistentVolumeClaim."""


class HorizontalPodAutoscaler(AsyncObjectMixin, _HorizontalPodAutoscaler):
    """HorizontalPodAutoscaler."""


class StatefulSet(AsyncScalableMixin, AsyncObjectMixin, _StatefulSet):
    """StatefulSet."""


class Role(AsyncObjectMixin, _Role):
    """Role."""


class RoleBinding(AsyncObjectMixin, _RoleBinding):
    """RoleBinding."""


class ClusterRole(AsyncObjectMixin, _ClusterRole):
    """ClusterRole."""


class ClusterRoleBinding(AsyncObjectMixin, _ClusterRoleBinding):
    """ClusterRoleBinding."""


class PodSecurityPolicy(AsyncObjectMixin, _PodSecurityPolicy):
    """PodSecurityPolicy."""


class PodDisruptionBudget(AsyncObjectMixin, _PodDisruptionBudget):
    """PodDisruptionBudget."""


class CustomResourceDefinition(AsyncObjectMixin, _CustomResourceDefinition):
    """CustomResourceDefinition."""
