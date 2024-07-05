# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
"""Objects to represent Kubernetes resources.

This module provides classes that represent Kubernetes resources.
These classes are used to interact with resources in the Kubernetes API server.
"""
from functools import partial

from ._async_utils import run_sync, sync
from ._objects import (
    APIObject as _APIObject,
)
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


@sync
class APIObject(_APIObject):
    __doc__ = _APIObject.__doc__
    _asyncio = False


@sync
class Binding(_Binding):
    __doc__ = _Binding.__doc__
    _asyncio = False


@sync
class ComponentStatus(_ComponentStatus):
    __doc__ = _ComponentStatus.__doc__
    _asyncio = False


@sync
class ConfigMap(_ConfigMap):
    __doc__ = _ConfigMap.__doc__
    _asyncio = False


@sync
class Endpoints(_Endpoints):
    __doc__ = _Endpoints.__doc__
    _asyncio = False


@sync
class Event(_Event):
    __doc__ = _Event.__doc__
    _asyncio = False


@sync
class LimitRange(_LimitRange):
    __doc__ = _LimitRange.__doc__
    _asyncio = False


@sync
class Namespace(_Namespace):
    __doc__ = _Namespace.__doc__
    _asyncio = False


@sync
class Node(_Node):
    __doc__ = _Node.__doc__
    _asyncio = False


@sync
class PersistentVolume(_PersistentVolume):
    __doc__ = _PersistentVolume.__doc__
    _asyncio = False


@sync
class PersistentVolumeClaim(_PersistentVolumeClaim):
    __doc__ = _PersistentVolumeClaim.__doc__
    _asyncio = False


@sync
class Pod(_Pod):
    __doc__ = _Pod.__doc__
    _asyncio = False


@sync
class PodTemplate(_PodTemplate):
    __doc__ = _PodTemplate.__doc__
    _asyncio = False


@sync
class ReplicationController(_ReplicationController):
    __doc__ = _ReplicationController.__doc__
    _asyncio = False


@sync
class ResourceQuota(_ResourceQuota):
    __doc__ = _ResourceQuota.__doc__
    _asyncio = False


@sync
class Secret(_Secret):
    __doc__ = _Secret.__doc__
    _asyncio = False


@sync
class Service(_Service):
    __doc__ = _Service.__doc__
    _asyncio = False


@sync
class ServiceAccount(_ServiceAccount):
    __doc__ = _ServiceAccount.__doc__
    _asyncio = False


@sync
class ControllerRevision(_ControllerRevision):
    __doc__ = _ControllerRevision.__doc__
    _asyncio = False


@sync
class DaemonSet(_DaemonSet):
    __doc__ = _DaemonSet.__doc__
    _asyncio = False


@sync
class Deployment(_Deployment):
    __doc__ = _Deployment.__doc__
    _asyncio = False


@sync
class ReplicaSet(_ReplicaSet):
    __doc__ = _ReplicaSet.__doc__
    _asyncio = False


@sync
class StatefulSet(_StatefulSet):
    __doc__ = _StatefulSet.__doc__
    _asyncio = False


@sync
class HorizontalPodAutoscaler(_HorizontalPodAutoscaler):
    __doc__ = _HorizontalPodAutoscaler.__doc__
    _asyncio = False


@sync
class CronJob(_CronJob):
    __doc__ = _CronJob.__doc__
    _asyncio = False


@sync
class Job(_Job):
    __doc__ = _Job.__doc__
    _asyncio = False


@sync
class Ingress(_Ingress):
    __doc__ = _Ingress.__doc__
    _asyncio = False


@sync
class IngressClass(_IngressClass):
    __doc__ = _IngressClass.__doc__
    _asyncio = False


@sync
class NetworkPolicy(_NetworkPolicy):
    __doc__ = _NetworkPolicy.__doc__
    _asyncio = False


@sync
class PodDisruptionBudget(_PodDisruptionBudget):
    __doc__ = _PodDisruptionBudget.__doc__
    _asyncio = False


@sync
class ClusterRoleBinding(_ClusterRoleBinding):
    __doc__ = _ClusterRoleBinding.__doc__
    _asyncio = False


@sync
class ClusterRole(_ClusterRole):
    __doc__ = _ClusterRole.__doc__
    _asyncio = False


@sync
class RoleBinding(_RoleBinding):
    __doc__ = _RoleBinding.__doc__
    _asyncio = False


@sync
class Role(_Role):
    __doc__ = _Role.__doc__
    _asyncio = False


@sync
class CustomResourceDefinition(_CustomResourceDefinition):
    __doc__ = _CustomResourceDefinition.__doc__
    _asyncio = False


@sync
class Table(_Table):
    __doc__ = _Table.__doc__
    _asyncio = False


object_from_name_type = run_sync(partial(_object_from_name_type, _asyncio=False))
objects_from_files = run_sync(partial(_objects_from_files, _asyncio=False))
get_class = partial(_get_class, _asyncio=False)
new_class = partial(_new_class, asyncio=False)
object_from_spec = partial(_object_from_spec, _asyncio=False)
