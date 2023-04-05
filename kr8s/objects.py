# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import json

from ._api import Kr8sApi
from ._data_utils import list_dict_unpack
from ._exceptions import NotFoundError


class _ObjectRegistry:
    """A registry of Kubernetes objects."""

    def __init__(self):
        self.objects = {}

    def register(self, cls):
        if not issubclass(cls, APIObject):
            raise TypeError(f"{cls} must be a subclass of APIObject")
        self.objects[f"{cls.version}/{cls.kind}"] = cls
        return cls

    def unregister(self, cls):
        del self.objects[f"{cls.version}/{cls.kind}"]

    def get(self, kind, version=None):
        for cls in self.objects.values():
            if cls.kind == kind and (version is None or cls.version == version):
                return cls
        raise KeyError(f"Unknown object {version}/{kind}")


OBJECT_REGISTRY = _ObjectRegistry()


class APIObject:
    """Base class for Kubernetes objects."""

    namespaced = False

    def __init__(self, resource: dict, api: Kr8sApi = None) -> None:
        """Initialize an APIObject."""
        # TODO support passing pykube or kubernetes objects in addition to dicts
        self.raw = resource
        self.api = api or Kr8sApi()

    def __repr__(self):
        """Return a string representation of the Kubernetes resource."""
        return f"<{self.kind} {self.name}>"

    def __str__(self):
        """Return a string representation of the Kubernetes resource."""
        return self.name

    @property
    def name(self) -> str:
        """Name of the Kubernetes resource."""
        return self.raw["metadata"]["name"]

    @property
    def namespace(self) -> str:
        """Namespace of the Kubernetes resource."""
        if self.namespaced:
            return self.raw.get("metadata", {}).get(
                "namespace", self.api.auth.namespace
            )
        return None

    @property
    def metadata(self) -> dict:
        """Metadata of the Kubernetes resource."""
        return self.raw["metadata"]

    @property
    def spec(self) -> dict:
        """Spec of the Kubernetes resource."""
        return self.raw["spec"]

    @property
    def status(self) -> dict:
        """Status of the Kubernetes resource."""
        return self.raw["status"]

    @property
    def labels(self) -> dict:
        """Labels of the Kubernetes resource."""
        return self.raw["metadata"]["labels"]

    @property
    def annotations(self) -> dict:
        """Annotations of the Kubernetes resource."""
        return self.raw["metadata"]["annotations"]

    async def exists(self, ensure=False) -> bool:
        """Check if this object exists in Kubernetes."""
        status, _ = await self.api.call_api(
            "GET",
            version=self.version,
            url=f"{self.endpoint}/{self.name}",
            namespace=self.namespace,
            raise_for_status=False,
        )
        if status == 200:
            return True
        if ensure:
            raise NotFoundError(f"Object {self.name} does not exist")
        return False

    async def create(self) -> None:
        """Create this object in Kubernetes."""
        _, self.raw = await self.api.call_api(
            "POST",
            version=self.version,
            url=self.endpoint,
            namespace=self.namespace,
            data=json.dumps(self.raw),
        )

    async def delete(self, propagation_policy: str = None) -> None:
        """Delete this object from Kubernetes."""
        data = {}
        if propagation_policy:
            data["propagationPolicy"] = propagation_policy
        await self.api.call_api(
            "DELETE",
            version=self.version,
            url=f"{self.endpoint}/{self.name}",
            namespace=self.namespace,
            data=json.dumps(data),
        )

    async def refresh(self) -> None:
        """Refresh this object from Kubernetes."""
        _, self.raw = await self.api.call_api(
            "GET",
            version=self.version,
            url=f"{self.endpoint}/{self.name}",
            namespace=self.namespace,
        )

    async def patch(self, patch, *, subresource=None) -> None:
        """Patch this object in Kubernetes."""
        url = f"{self.endpoint}/{self.name}"
        if subresource:
            url = f"{url}/{subresource}"
        _, self.raw = await self.api.call_api(
            "PATCH",
            version=self.version,
            url=url,
            namespace=self.namespace,
            data=json.dumps(patch),
            headers={"Content-Type": "application/merge-patch+json"},
        )

    async def watch(self, timeout: int = None):
        """Watch this object in Kubernetes."""
        raise NotImplementedError("Watching is not yet implemented")


## v1 objects


class Binding(APIObject):
    """A Kubernetes Binding."""

    version = "v1"
    endpoint = "bindings"
    kind = "Binding"
    plural = "bindings"
    singular = "binding"
    namespaced = True


class ComponentStatus(APIObject):
    """A Kubernetes ComponentStatus."""

    version = "v1"
    endpoint = "componentstatuses"
    kind = "ComponentStatus"
    plural = "componentstatuses"
    singular = "componentstatus"
    namespaced = False


class ConfigMap(APIObject):
    """A Kubernetes ConfigMap."""

    version = "v1"
    endpoint = "configmaps"
    kind = "ConfigMap"
    plural = "configmaps"
    singular = "configmap"
    namespaced = True


class Endpoints(APIObject):
    """A Kubernetes Endpoints."""

    version = "v1"
    endpoint = "endpoints"
    kind = "Endpoints"
    plural = "endpoints"
    singular = "endpoint"
    namespaced = True


class Event(APIObject):
    """A Kubernetes Event."""

    version = "v1"
    endpoint = "events"
    kind = "Event"
    plural = "events"
    singular = "event"
    namespaced = True


class LimitRange(APIObject):
    """A Kubernetes LimitRange."""

    version = "v1"
    endpoint = "limitranges"
    kind = "LimitRange"
    plural = "limitranges"
    singular = "limitrange"
    namespaced = True


class Namespace(APIObject):
    """A Kubernetes Namespace."""

    version = "v1"
    endpoint = "namespaces"
    kind = "Namespace"
    plural = "namespaces"
    singular = "namespace"
    namespaced = False


class Node(APIObject):
    """A Kubernetes Node."""

    version = "v1"
    endpoint = "nodes"
    kind = "Node"
    plural = "nodes"
    singular = "node"
    namespaced = False


class PersistentVolumeClaim(APIObject):
    """A Kubernetes PersistentVolumeClaim."""

    version = "v1"
    endpoint = "persistentvolumeclaims"
    kind = "PersistentVolumeClaim"
    plural = "persistentvolumeclaims"
    singular = "persistentvolumeclaim"
    namespaced = True


class PersistentVolume(APIObject):
    """A Kubernetes PersistentVolume."""

    version = "v1"
    endpoint = "persistentvolumes"
    kind = "PersistentVolume"
    plural = "persistentvolumes"
    singular = "persistentvolume"
    namespaced = False


class Pod(APIObject):
    """A Kubernetes Pod."""

    version = "v1"
    endpoint = "pods"
    kind = "Pod"
    plural = "pods"
    singular = "pod"
    namespaced = True

    async def ready(self):
        await self.refresh()
        conditions = list_dict_unpack(
            self.status.get("conditions", []),
            key="type",
            value="status",
        )
        return "Ready" in conditions and conditions.get("Ready", "False") == "True"


class PodTemplate(APIObject):
    """A Kubernetes PodTemplate."""

    version = "v1"
    endpoint = "podtemplates"
    kind = "PodTemplate"
    plural = "podtemplates"
    singular = "podtemplate"
    namespaced = True


class ReplicationController(APIObject):
    """A Kubernetes ReplicationController."""

    version = "v1"
    endpoint = "replicationcontrollers"
    kind = "ReplicationController"
    plural = "replicationcontrollers"
    singular = "replicationcontroller"
    namespaced = True


class ResourceQuota(APIObject):
    """A Kubernetes ResourceQuota."""

    version = "v1"
    endpoint = "resourcequotas"
    kind = "ResourceQuota"
    plural = "resourcequotas"
    singular = "resourcequota"
    namespaced = True


class Secret(APIObject):
    """A Kubernetes Secret."""

    version = "v1"
    endpoint = "secrets"
    kind = "Secret"
    plural = "secrets"
    singular = "secret"
    namespaced = True


class ServiceAccount(APIObject):
    """A Kubernetes ServiceAccount."""

    version = "v1"
    endpoint = "serviceaccounts"
    kind = "ServiceAccount"
    plural = "serviceaccounts"
    singular = "serviceaccount"
    namespaced = True


class Service(APIObject):
    """A Kubernetes Service."""

    version = "v1"
    endpoint = "services"
    kind = "Service"
    plural = "services"
    singular = "service"
    namespaced = True


OBJECT_REGISTRY.register(Binding)
OBJECT_REGISTRY.register(ComponentStatus)
OBJECT_REGISTRY.register(ConfigMap)
OBJECT_REGISTRY.register(Endpoints)
OBJECT_REGISTRY.register(Event)
OBJECT_REGISTRY.register(LimitRange)
OBJECT_REGISTRY.register(Namespace)
OBJECT_REGISTRY.register(Node)
OBJECT_REGISTRY.register(PersistentVolumeClaim)
OBJECT_REGISTRY.register(PersistentVolume)
OBJECT_REGISTRY.register(Pod)
OBJECT_REGISTRY.register(PodTemplate)
OBJECT_REGISTRY.register(ReplicationController)
OBJECT_REGISTRY.register(ResourceQuota)
OBJECT_REGISTRY.register(Secret)
OBJECT_REGISTRY.register(ServiceAccount)
OBJECT_REGISTRY.register(Service)

## apps/v1 objects


class ControllerRevision(APIObject):
    """A Kubernetes ControllerRevision."""

    version = "apps/v1"
    endpoint = "controllerrevisions"
    kind = "ControllerRevision"
    plural = "controllerrevisions"
    singular = "controllerrevision"
    namespaced = True


class DaemonSet(APIObject):
    """A Kubernetes DaemonSet."""

    version = "apps/v1"
    endpoint = "daemonsets"
    kind = "DaemonSet"
    plural = "daemonsets"
    singular = "daemonset"
    namespaced = True


class Deployment(APIObject):
    """A Kubernetes Deployment."""

    version = "apps/v1"
    endpoint = "deployments"
    kind = "Deployment"
    plural = "deployments"
    singular = "deployment"
    namespaced = True


class ReplicaSet(APIObject):
    """A Kubernetes ReplicaSet."""

    version = "apps/v1"
    endpoint = "replicasets"
    kind = "ReplicaSet"
    plural = "replicasets"
    singular = "replicaset"
    namespaced = True


class StatefulSet(APIObject):
    """A Kubernetes StatefulSet."""

    version = "apps/v1"
    endpoint = "statefulsets"
    kind = "StatefulSet"
    plural = "statefulsets"
    singular = "statefulset"
    namespaced = True


OBJECT_REGISTRY.register(ControllerRevision)
OBJECT_REGISTRY.register(DaemonSet)
OBJECT_REGISTRY.register(Deployment)
OBJECT_REGISTRY.register(ReplicaSet)
OBJECT_REGISTRY.register(StatefulSet)

## autoscaling/v1 objects


class HorizontalPodAutoscaler(APIObject):
    """A Kubernetes HorizontalPodAutoscaler."""

    version = "autoscaling/v2"
    endpoint = "horizontalpodautoscalers"
    kind = "HorizontalPodAutoscaler"
    plural = "horizontalpodautoscalers"
    singular = "horizontalpodautoscaler"
    namespaced = True


OBJECT_REGISTRY.register(HorizontalPodAutoscaler)

## batch/v1 objects


class CronJob(APIObject):
    """A Kubernetes CronJob."""

    version = "batch/v1"
    endpoint = "cronjobs"
    kind = "CronJob"
    plural = "cronjobs"
    singular = "cronjob"
    namespaced = True


class Job(APIObject):
    """A Kubernetes Job."""

    version = "batch/v1"
    endpoint = "jobs"
    kind = "Job"
    plural = "jobs"
    singular = "job"
    namespaced = True


OBJECT_REGISTRY.register(CronJob)
OBJECT_REGISTRY.register(Job)

## events.k8s.io/v1 objects


class Event(APIObject):
    """A Kubernetes Event."""

    version = "events.k8s.io/v1"
    endpoint = "events"
    kind = "Event"
    plural = "events"
    singular = "event"
    namespaced = True


OBJECT_REGISTRY.register(Event)


## networking.k8s.io/v1 objects


class IngressClass(APIObject):
    """A Kubernetes IngressClass."""

    version = "networking.k8s.io/v1"
    endpoint = "ingressclasses"
    kind = "IngressClass"
    plural = "ingressclasses"
    singular = "ingressclass"
    namespaced = False


class Ingress(APIObject):
    """A Kubernetes Ingress."""

    version = "networking.k8s.io/v1"
    endpoint = "ingresses"
    kind = "Ingress"
    plural = "ingresses"
    singular = "ingress"
    namespaced = True


class NetworkPolicy(APIObject):
    """A Kubernetes NetworkPolicy."""

    version = "networking.k8s.io/v1"
    endpoint = "networkpolicies"
    kind = "NetworkPolicy"
    plural = "networkpolicies"
    singular = "networkpolicy"
    namespaced = True


OBJECT_REGISTRY.register(IngressClass)
OBJECT_REGISTRY.register(Ingress)
OBJECT_REGISTRY.register(NetworkPolicy)

## policy/v1 objects


class PodDisruptionBudget(APIObject):
    """A Kubernetes PodDisruptionBudget."""

    version = "policy/v1"
    endpoint = "poddisruptionbudgets"
    kind = "PodDisruptionBudget"
    plural = "poddisruptionbudgets"
    singular = "poddisruptionbudget"
    namespaced = True


OBJECT_REGISTRY.register(PodDisruptionBudget)

## rbac.authorization.k8s.io/v1 objects


class ClusterRoleBinding(APIObject):
    """A Kubernetes ClusterRoleBinding."""

    version = "rbac.authorization.k8s.io/v1"
    endpoint = "clusterrolebindings"
    kind = "ClusterRoleBinding"
    plural = "clusterrolebindings"
    singular = "clusterrolebinding"
    namespaced = False


class ClusterRole(APIObject):
    """A Kubernetes ClusterRole."""

    version = "rbac.authorization.k8s.io/v1"
    endpoint = "clusterroles"
    kind = "ClusterRole"
    plural = "clusterroles"
    singular = "clusterrole"
    namespaced = False


class RoleBinding(APIObject):
    """A Kubernetes RoleBinding."""

    version = "rbac.authorization.k8s.io/v1"
    endpoint = "rolebindings"
    kind = "RoleBinding"
    plural = "rolebindings"
    singular = "rolebinding"
    namespaced = True


class Role(APIObject):
    """A Kubernetes Role."""

    version = "rbac.authorization.k8s.io/v1"
    endpoint = "roles"
    kind = "Role"
    plural = "roles"
    singular = "role"
    namespaced = True


OBJECT_REGISTRY.register(ClusterRoleBinding)
OBJECT_REGISTRY.register(ClusterRole)
OBJECT_REGISTRY.register(RoleBinding)
OBJECT_REGISTRY.register(Role)
