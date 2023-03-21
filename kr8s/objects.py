# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from typing import Optional

from pykube.http import HTTPClient
from pykube.objects import APIObject as _APIObject
from pykube.objects import ClusterRole as _ClusterRole
from pykube.objects import ClusterRoleBinding as _ClusterRoleBinding
from pykube.objects import ConfigMap as _ConfigMap
from pykube.objects import CronJob as _CronJob
from pykube.objects import CustomResourceDefinition as _CustomResourceDefinition
from pykube.objects import DaemonSet as _DaemonSet
from pykube.objects import Deployment as _Deployment
from pykube.objects import Endpoint as _Endpoint
from pykube.objects import Event as _Event
from pykube.objects import HorizontalPodAutoscaler as _HorizontalPodAutoscaler
from pykube.objects import Ingress as _Ingress
from pykube.objects import Job as _Job
from pykube.objects import LimitRange as _LimitRange
from pykube.objects import Namespace as _Namespace
from pykube.objects import NamespacedAPIObject as _NamespacedAPIObject
from pykube.objects import Node as _Node
from pykube.objects import ObjectManager
from pykube.objects import PersistentVolume as _PersistentVolume
from pykube.objects import PersistentVolumeClaim as _PersistentVolumeClaim
from pykube.objects import Pod as _Pod
from pykube.objects import PodDisruptionBudget as _PodDisruptionBudget
from pykube.objects import PodSecurityPolicy as _PodSecurityPolicy
from pykube.objects import ReplicaSet as _ReplicaSet
from pykube.objects import ReplicationController as _ReplicationController
from pykube.objects import ResourceQuota as _ResourceQuota
from pykube.objects import Role as _Role
from pykube.objects import RoleBinding as _RoleBinding
from pykube.objects import Secret as _Secret
from pykube.objects import Service as _Service
from pykube.objects import ServiceAccount as _ServiceAccount
from pykube.objects import StatefulSet as _StatefulSet
from requests import Response

from kr8s.mixins import AsyncMixin, AsyncScalableMixin
from kr8s.query import Query


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
