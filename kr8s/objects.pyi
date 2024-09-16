from _typesched import Incomplete

from ._async_utils import run_sync as run_sync
from ._async_utils import sync as sync
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

class APIObject(_APIObject):
    @classmethod
    def list(cls, **kwargs) -> list[APIObject]: ...  # type: ignore[override]

class Binding(_Binding):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Binding]: ...  # type: ignore[override]

class ComponentStatus(_ComponentStatus):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ComponentStatus]: ...  # type: ignore[override]

class ConfigMap(_ConfigMap):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ConfigMap]: ...  # type: ignore[override]

class Endpoints(_Endpoints):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Endpoints]: ...  # type: ignore[override]

class Event(_Event):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Event]: ...  # type: ignore[override]

class LimitRange(_LimitRange):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[LimitRange]: ...  # type: ignore[override]

class Namespace(_Namespace):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Namespace]: ...  # type: ignore[override]

class Node(_Node):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Node]: ...  # type: ignore[override]

class PersistentVolume(_PersistentVolume):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[PersistentVolume]: ...  # type: ignore[override]

class PersistentVolumeClaim(_PersistentVolumeClaim):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[PersistentVolumeClaim]: ...  # type: ignore[override]

class Pod(_Pod):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Pod]: ...  # type: ignore[override]

class PodTemplate(_PodTemplate):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[PodTemplate]: ...  # type: ignore[override]

class ReplicationController(_ReplicationController):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ReplicationController]: ...  # type: ignore[override]

class ResourceQuota(_ResourceQuota):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ResourceQuota]: ...  # type: ignore[override]

class Secret(_Secret):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Secret]: ...  # type: ignore[override]

class Service(_Service):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Service]: ...  # type: ignore[override]

class ServiceAccount(_ServiceAccount):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ServiceAccount]: ...  # type: ignore[override]

class ControllerRevision(_ControllerRevision):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ControllerRevision]: ...  # type: ignore[override]

class DaemonSet(_DaemonSet):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[DaemonSet]: ...  # type: ignore[override]

class Deployment(_Deployment):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Deployment]: ...  # type: ignore[override]

class ReplicaSet(_ReplicaSet):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ReplicaSet]: ...  # type: ignore[override]

class StatefulSet(_StatefulSet):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[StatefulSet]: ...  # type: ignore[override]

class HorizontalPodAutoscaler(_HorizontalPodAutoscaler):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[HorizontalPodAutoscaler]: ...  # type: ignore[override]

class CronJob(_CronJob):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[CronJob]: ...  # type: ignore[override]

class Job(_Job):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Job]: ...  # type: ignore[override]

class Ingress(_Ingress):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Ingress]: ...  # type: ignore[override]

class IngressClass(_IngressClass):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[IngressClass]: ...  # type: ignore[override]

class NetworkPolicy(_NetworkPolicy):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[NetworkPolicy]: ...  # type: ignore[override]

class PodDisruptionBudget(_PodDisruptionBudget):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[PodDisruptionBudget]: ...  # type: ignore[override]

class ClusterRoleBinding(_ClusterRoleBinding):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ClusterRoleBinding]: ...  # type: ignore[override]

class ClusterRole(_ClusterRole):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[ClusterRole]: ...  # type: ignore[override]

class RoleBinding(_RoleBinding):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[RoleBinding]: ...  # type: ignore[override]

class Role(_Role):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Role]: ...  # type: ignore[override]

class CustomResourceDefinition(_CustomResourceDefinition):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[CustomResourceDefinition]: ...  # type: ignore[override]

class Table(_Table):
    __doc__: Incomplete

    @classmethod
    def list(cls, **kwargs) -> list[Table]: ...  # type: ignore[override]

object_from_name_type: Incomplete
objects_from_files: Incomplete
get_class: Incomplete
new_class: Incomplete
object_from_spec: Incomplete
