# SPDX-FileCopyrightText: Copyright (c) 2024-2025, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""Objects to represent Kubernetes resources.

This module provides classes that represent Kubernetes resources.
These classes are used to interact with resources in the Kubernetes API server.
"""

# Disable missing docstrings, these are inherited from the async version of the objects
# ruff: noqa: D102
from __future__ import annotations

import pathlib
from collections.abc import Generator
from typing import TYPE_CHECKING, Any, BinaryIO, cast

import httpx

from ._async_utils import as_sync_func, as_sync_generator
from ._exec import CompletedExec
from ._objects import APIObjectSyncMixin
from ._objects import (
    Binding as _Binding,
)
from ._objects import (
    ClusterRole as _ClusterRole,
)
from ._objects import (
    ClusterRoleBinding as _ClusterRoleBinding,
)
from ._objects import (
    ComponentStatus as _ComponentStatus,
)
from ._objects import (
    ConfigMap as _ConfigMap,
)
from ._objects import (
    ControllerRevision as _ControllerRevision,
)
from ._objects import (
    CronJob as _CronJob,
)
from ._objects import (
    CustomResourceDefinition as _CustomResourceDefinition,
)
from ._objects import (
    DaemonSet as _DaemonSet,
)
from ._objects import (
    Deployment as _Deployment,
)
from ._objects import (
    Endpoints as _Endpoints,
)
from ._objects import (
    Event as _Event,
)
from ._objects import (
    HorizontalPodAutoscaler as _HorizontalPodAutoscaler,
)
from ._objects import (
    Ingress as _Ingress,
)
from ._objects import (
    IngressClass as _IngressClass,
)
from ._objects import (
    IPAddress as _IPAddress,
)
from ._objects import (
    Job as _Job,
)
from ._objects import (
    LimitRange as _LimitRange,
)
from ._objects import (
    Namespace as _Namespace,
)
from ._objects import (
    NetworkPolicy as _NetworkPolicy,
)
from ._objects import (
    Node as _Node,
)
from ._objects import (
    PersistentVolume as _PersistentVolume,
)
from ._objects import (
    PersistentVolumeClaim as _PersistentVolumeClaim,
)
from ._objects import (
    Pod as _Pod,
)
from ._objects import (
    PodDisruptionBudget as _PodDisruptionBudget,
)
from ._objects import (
    PodTemplate as _PodTemplate,
)
from ._objects import (
    ReplicaSet as _ReplicaSet,
)
from ._objects import (
    ReplicationController as _ReplicationController,
)
from ._objects import (
    ResourceQuota as _ResourceQuota,
)
from ._objects import (
    Role as _Role,
)
from ._objects import (
    RoleBinding as _RoleBinding,
)
from ._objects import (
    Secret as _Secret,
)
from ._objects import (
    Service as _Service,
)
from ._objects import (
    ServiceAccount as _ServiceAccount,
)
from ._objects import (
    ServiceCIDR as _ServiceCIDR,
)
from ._objects import (
    StatefulSet as _StatefulSet,
)
from ._objects import (
    Table as _Table,
)
from ._objects import (
    get_class as _get_class,
)
from ._objects import (
    new_class as _new_class,
)

# noqa
from ._objects import object_from_name_type as _object_from_name_type
from ._objects import (
    object_from_spec as _object_from_spec,
)
from ._objects import objects_from_files as _objects_from_files
from .portforward import PortForward

if TYPE_CHECKING:
    from kr8s import Api


class APIObject(APIObjectSyncMixin):
    __doc__ = APIObjectSyncMixin.__doc__


class Binding(APIObjectSyncMixin, _Binding):
    __doc__ = _Binding.__doc__


class ComponentStatus(APIObjectSyncMixin, _ComponentStatus):
    __doc__ = _ComponentStatus.__doc__


class ConfigMap(APIObjectSyncMixin, _ConfigMap):
    __doc__ = _ConfigMap.__doc__


class Endpoints(APIObjectSyncMixin, _Endpoints):
    __doc__ = _Endpoints.__doc__


class Event(APIObjectSyncMixin, _Event):
    __doc__ = _Event.__doc__


class LimitRange(APIObjectSyncMixin, _LimitRange):
    __doc__ = _LimitRange.__doc__


class Namespace(APIObjectSyncMixin, _Namespace):
    __doc__ = _Namespace.__doc__


class Node(APIObjectSyncMixin, _Node):

    def cordon(self):
        return as_sync_func(self.async_cordon)()

    def uncordon(self):
        return as_sync_func(self.async_uncordon)()

    def taint(self, key, value, *, effect):
        return as_sync_func(self.async_taint)(key, value, effect=effect)


class PersistentVolume(APIObjectSyncMixin, _PersistentVolume):
    __doc__ = _PersistentVolume.__doc__


class PersistentVolumeClaim(APIObjectSyncMixin, _PersistentVolumeClaim):
    __doc__ = _PersistentVolumeClaim.__doc__


class Pod(APIObjectSyncMixin, _Pod):
    def ready(self) -> bool:  # type: ignore[override]
        return as_sync_func(self.async_ready)()

    def logs(  # type: ignore[override]
        self,
        container=None,
        pretty=None,
        previous=False,
        since_seconds=None,
        since_time=None,
        timestamps=False,
        tail_lines=None,
        limit_bytes=None,
        follow=False,
        timeout=3600,
    ) -> Generator[str]:
        yield from as_sync_generator(self.async_logs)(
            container,
            pretty,
            previous,
            since_seconds,
            since_time,
            timestamps,
            tail_lines,
            limit_bytes,
            follow,
            timeout,
        )

    def exec(  # type: ignore[override]
        self,
        command: list[str],
        *,
        container: str | None = None,
        stdin: str | BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        check: bool = True,
        capture_output: bool = True,
    ) -> CompletedExec:
        return as_sync_func(self.async_exec)(
            command,
            container=container,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            check=check,
            capture_output=capture_output,
        )

    def tolerate(  # type: ignore[override]
        self,
        key: str,
        *,
        operator: str,
        effect: str,
        value: str | None = None,
        toleration_seconds: int | None = None,
    ):
        return as_sync_func(self.async_tolerate)(
            key,
            operator=operator,
            effect=effect,
            value=value,
            toleration_seconds=toleration_seconds,
        )

    def portforward(
        self, remote_port, local_port="match", address="127.0.0.1"
    ) -> PortForward:
        pf = super().portforward(remote_port, local_port, address)
        assert isinstance(pf, PortForward)
        return pf


class PodTemplate(APIObjectSyncMixin, _PodTemplate):
    __doc__ = _PodTemplate.__doc__


class ReplicationController(APIObjectSyncMixin, _ReplicationController):

    def ready(self):
        return as_sync_func(self.async_ready)()


class ResourceQuota(APIObjectSyncMixin, _ResourceQuota):
    __doc__ = _ResourceQuota.__doc__


class Secret(APIObjectSyncMixin, _Secret):
    __doc__ = _Secret.__doc__


class ServiceAccount(APIObjectSyncMixin, _ServiceAccount):
    __doc__ = _ServiceAccount.__doc__


class Service(APIObjectSyncMixin, _Service):
    def proxy_http_request(  # type: ignore[override]
        self, method: str, path: str, port: int | None = None, **kwargs: Any
    ) -> httpx.Response:
        return as_sync_func(self.async_proxy_http_request)(
            method, path, port=port, **kwargs
        )

    def proxy_http_get(  # type: ignore[override]
        self, path: str, port: int | None = None, **kwargs
    ) -> httpx.Response:
        return as_sync_func(self.async_proxy_http_request)("GET", path, port, **kwargs)

    def proxy_http_post(  # type: ignore[override]
        self, path: str, port: int | None = None, **kwargs
    ) -> httpx.Response:
        return as_sync_func(self.async_proxy_http_request)("POST", path, port, **kwargs)

    def proxy_http_put(  # type: ignore[override]
        self, path: str, port: int | None = None, **kwargs
    ) -> httpx.Response:
        return as_sync_func(self.async_proxy_http_request)("PUT", path, port, **kwargs)

    def proxy_http_delete(  # type: ignore[override]
        self, path: str, port: int | None = None, **kwargs
    ) -> httpx.Response:
        return as_sync_func(self.async_proxy_http_request)(
            "DELETE", path, port, **kwargs
        )

    def ready_pods(self) -> list[Pod]:  # type: ignore[override]
        return cast(list[Pod], as_sync_func(self.async_ready_pods)())

    def ready(self):
        return as_sync_func(self.async_ready)()

    def portforward(
        self, remote_port, local_port="match", address="127.0.0.1"
    ) -> PortForward:
        pf = super().portforward(remote_port, local_port, address)
        assert isinstance(pf, PortForward)
        return pf


class ControllerRevision(APIObjectSyncMixin, _ControllerRevision):
    __doc__ = _ControllerRevision.__doc__


class DaemonSet(APIObjectSyncMixin, _DaemonSet):
    __doc__ = _DaemonSet.__doc__


class Deployment(APIObjectSyncMixin, _Deployment):

    def pods(self) -> list[Pod]:  # type: ignore[override]
        return cast(list[Pod], as_sync_func(self.async_pods)())

    def ready(self) -> bool:  # type: ignore[override]
        return as_sync_func(self.async_ready)()


class ReplicaSet(APIObjectSyncMixin, _ReplicaSet):
    __doc__ = _ReplicaSet.__doc__


class StatefulSet(APIObjectSyncMixin, _StatefulSet):
    __doc__ = _StatefulSet.__doc__


class HorizontalPodAutoscaler(APIObjectSyncMixin, _HorizontalPodAutoscaler):
    __doc__ = _HorizontalPodAutoscaler.__doc__


class CronJob(APIObjectSyncMixin, _CronJob):
    __doc__ = _CronJob.__doc__


class Job(APIObjectSyncMixin, _Job):
    __doc__ = _Job.__doc__


class Ingress(APIObjectSyncMixin, _Ingress):
    __doc__ = _Ingress.__doc__


class IngressClass(APIObjectSyncMixin, _IngressClass):
    __doc__ = _IngressClass.__doc__


class NetworkPolicy(APIObjectSyncMixin, _NetworkPolicy):
    __doc__ = _NetworkPolicy.__doc__


class PodDisruptionBudget(APIObjectSyncMixin, _PodDisruptionBudget):
    __doc__ = _PodDisruptionBudget.__doc__


class ClusterRoleBinding(APIObjectSyncMixin, _ClusterRoleBinding):
    __doc__ = _ClusterRoleBinding.__doc__


class ClusterRole(APIObjectSyncMixin, _ClusterRole):
    __doc__ = _ClusterRole.__doc__


class RoleBinding(APIObjectSyncMixin, _RoleBinding):
    __doc__ = _RoleBinding.__doc__


class Role(APIObjectSyncMixin, _Role):
    __doc__ = _Role.__doc__


class CustomResourceDefinition(APIObjectSyncMixin, _CustomResourceDefinition):
    __doc__ = _CustomResourceDefinition.__doc__


class Table(APIObjectSyncMixin, _Table):
    __doc__ = _Table.__doc__


class IPAddress(APIObjectSyncMixin, _IPAddress):
    __doc__ = _IPAddress.__doc__


class ServiceCIDR(APIObjectSyncMixin, _ServiceCIDR):
    __doc__ = _ServiceCIDR.__doc__


def new_class(
    kind: str,
    version: str | None = None,
    asyncio: bool = False,
    namespaced=True,
    scalable: bool | None = None,
    scalable_spec: str | None = None,
    plural: str | None = None,
) -> type[APIObject]:
    """Create a new APIObject subclass.

    Args:
        kind: The Kubernetes resource kind.
        version: The Kubernetes API version.
        asyncio: Whether to use asyncio or not.
        namespaced: Whether the resource is namespaced or not.
        scalable: Whether the resource is scalable or not.
        scalable_spec: The name of the field to use for scaling.
        plural: The plural form of the resource.

    Returns:
        A new APIObject subclass.
    """
    return cast(
        type[APIObject],
        _new_class(kind, version, asyncio, namespaced, scalable, scalable_spec, plural),
    )


def object_from_name_type(
    name: str,
    namespace: str | None = None,
    api: Api | None = None,
) -> APIObject:
    """Create an APIObject from a Kubernetes resource name.

    Args:
        name: A Kubernetes resource name.
        namespace: The namespace of the resource.
        api: An optional API instance to use.

    Returns:
        A corresponding APIObject subclass instance.

    Raises:
        ValueError: If the resource kind or API version is not supported.
    """
    return cast(
        APIObject,
        as_sync_func(_object_from_name_type)(name, namespace, api, _asyncio=False),
    )


def objects_from_files(
    path: str | pathlib.Path,
    api: Api | None = None,
    recursive: bool = False,
) -> list[APIObject]:
    """Create APIObjects from Kubernetes resource files.

    Args:
        path: A path to a Kubernetes resource file or directory of resource files.
        api: An optional API instance to use.
        recursive: Whether to recursively search for resource files in subdirectories.

    Returns:
        A list of APIObject subclass instances.

    Raises:
        ValueError: If the resource kind or API version is not supported.
    """
    return cast(
        list[APIObject],
        as_sync_func(_objects_from_files)(path, api, recursive, _asyncio=False),
    )


def get_class(kind: str, version: str) -> type[APIObject]:
    """Get an APIObject subclass by kind and version.

    Args:
        kind: The Kubernetes resource kind.
        version: The Kubernetes API group/version.

    Returns:
        An APIObject subclass.

    Raises:
        KeyError: If no object is registered for the given kind and version.
    """
    return cast(type[APIObject], _get_class(kind, version, _asyncio=False))


def object_from_spec(
    spec: dict, api: Api | None = None, allow_unknown_type: bool = False
) -> APIObject:
    """Create an APIObject from a Kubernetes resource spec.

    Args:
        spec: A Kubernetes resource spec.
        api: An optional API instance to use.
        allow_unknown_type: Whether to allow unknown resource types.

    Returns:
        A corresponding APIObject subclass instance.

    Raises:
        ValueError: If the resource kind or API version is not supported.
    """
    return cast(
        APIObject, _object_from_spec(spec, api, allow_unknown_type, _asyncio=False)
    )
