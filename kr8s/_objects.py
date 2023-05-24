# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Type

import aiohttp
from aiohttp import ClientResponse

import kr8s
import kr8s.asyncio
from kr8s._api import Api
from kr8s._data_utils import list_dict_unpack
from kr8s._exceptions import NotFoundError
from kr8s.asyncio.portforward import PortForward as AsyncPortForward
from kr8s.portforward import PortForward as SyncPortForward


class APIObject:
    """Base class for Kubernetes objects."""

    namespaced = False
    scalable = False
    scalable_spec = "replicas"
    _asyncio = True

    def __init__(self, resource: dict, api: Api = None) -> None:
        """Initialize an APIObject."""
        # TODO support passing pykube or kubernetes objects in addition to dicts
        self._raw = resource
        self.api = api
        if self.api is None and not self._asyncio:
            self.api = kr8s.api()

    def __await__(self):
        async def f():
            if self.api is None:
                self.api = await kr8s.asyncio.api()
            return self

        return f().__await__()

    def __repr__(self):
        """Return a string representation of the Kubernetes resource."""
        return f"<{self.kind} {self.name}>"

    def __str__(self):
        """Return a string representation of the Kubernetes resource."""
        return self.name

    @property
    def raw(self) -> str:
        """Raw object returned from the Kubernetes API."""
        return self._raw

    @raw.setter
    def raw(self, value: Any) -> None:
        self._raw = value

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
        try:
            return self.raw["metadata"]["labels"]
        except KeyError:
            return {}

    @property
    def annotations(self) -> dict:
        """Annotations of the Kubernetes resource."""
        try:
            return self.raw["metadata"]["annotations"]
        except KeyError:
            return {}

    @property
    def replicas(self) -> int:
        """Replicas of the Kubernetes resource."""
        if self.scalable:
            return self.raw["spec"][self.scalable_spec]
        raise NotImplementedError(f"{self.kind} is not scalable")

    @classmethod
    async def get(
        cls,
        name: str,
        namespace: str = None,
        api: Api = None,
        timeout: int = 2,
        **kwargs,
    ) -> APIObject:
        """Get a Kubernetes resource by name."""

        if api is None:
            if cls._asyncio:
                api = await kr8s.asyncio.api()
            else:
                api = kr8s.api()
        start = time.time()
        backoff = 0.1
        while start + timeout > time.time():
            resources = await api._get(
                cls.endpoint, name, namespace=namespace, **kwargs
            )
            if len(resources) == 0:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 1)
                continue
            if len(resources) > 1:
                raise ValueError(
                    f"Expected exactly one {cls.kind} object. Use selectors to narrow down the search."
                )
            return resources[0]
        raise NotFoundError(f"Could not find {cls.kind} {name}.")

    async def exists(self, ensure=False) -> bool:
        """Check if this object exists in Kubernetes."""
        return await self._exists(ensure=ensure)

    async def _exists(self, ensure=False) -> bool:
        """Check if this object exists in Kubernetes."""
        async with self.api.call_api(
            "GET",
            version=self.version,
            url=f"{self.endpoint}/{self.name}",
            namespace=self.namespace,
            raise_for_status=False,
        ) as resp:
            status = resp.status
        if status == 200:
            return True
        if ensure:
            raise NotFoundError(f"Object {self.name} does not exist")
        return False

    async def create(self) -> None:
        """Create this object in Kubernetes."""
        async with self.api.call_api(
            "POST",
            version=self.version,
            url=self.endpoint,
            namespace=self.namespace,
            data=json.dumps(self.raw),
        ) as resp:
            self.raw = await resp.json()

    async def delete(self, propagation_policy: str = None) -> None:
        """Delete this object from Kubernetes."""
        data = {}
        if propagation_policy:
            data["propagationPolicy"] = propagation_policy
        try:
            async with self.api.call_api(
                "DELETE",
                version=self.version,
                url=f"{self.endpoint}/{self.name}",
                namespace=self.namespace,
                data=json.dumps(data),
            ) as resp:
                self.raw = await resp.json()
        except aiohttp.ClientResponseError as e:
            raise NotFoundError(f"Object {self.name} does not exist") from e

    async def refresh(self) -> None:
        """Refresh this object from Kubernetes."""
        await self._refresh()

    async def _refresh(self) -> None:
        """Refresh this object from Kubernetes."""
        async with self.api.call_api(
            "GET",
            version=self.version,
            url=f"{self.endpoint}/{self.name}",
            namespace=self.namespace,
        ) as resp:
            self.raw = await resp.json()

    async def patch(self, patch, *, subresource=None) -> None:
        """Patch this object in Kubernetes."""
        return await self._patch(patch, subresource=subresource)

    async def _patch(self, patch: Dict, *, subresource=None) -> None:
        """Patch this object in Kubernetes."""
        url = f"{self.endpoint}/{self.name}"
        if subresource:
            url = f"{url}/{subresource}"
        async with self.api.call_api(
            "PATCH",
            version=self.version,
            url=url,
            namespace=self.namespace,
            data=json.dumps(patch),
            headers={"Content-Type": "application/merge-patch+json"},
        ) as resp:
            self.raw = await resp.json()

    async def scale(self, replicas: int = None) -> None:
        """Scale this object in Kubernetes."""
        if not self.scalable:
            raise NotImplementedError(f"{self.kind} is not scalable")
        await self._exists(ensure=True)
        # TODO support dot notation in self.scalable_spec to support nested fields
        await self._patch({"spec": {self.scalable_spec: replicas}})
        while self.replicas != replicas:
            await self._refresh()
            await asyncio.sleep(0.1)

    async def watch(self):
        """Watch this object in Kubernetes."""
        since = self.metadata.get("resourceVersion")
        async for event, obj in self.api._watch(
            self.endpoint,
            namespace=self.namespace,
            field_selector=f"metadata.name={self.name}",
            since=since,
        ):
            self.raw = obj.raw
            yield event, self


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

    @property
    def unschedulable(self):
        if "unschedulable" in self.raw["spec"]:
            return self.raw["spec"]["unschedulable"]
        return False

    async def cordon(self) -> None:
        await self._patch({"spec": {"unschedulable": True}})

    async def uncordon(self) -> None:
        await self._patch({"spec": {"unschedulable": False}})


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

    async def ready(self) -> bool:
        """Check if the pod is ready."""
        await self._refresh()
        conditions = list_dict_unpack(
            self.status.get("conditions", []),
            key="type",
            value="status",
        )
        return (
            "Ready" in conditions
            and "ContainersReady" in conditions
            and conditions.get("Ready", "False") == "True"
            and conditions.get("ContainersReady", "False") == "True"
        )

    async def logs(
        self,
        container=None,
        pretty=None,
        previous=False,
        since_seconds=None,
        since_time=None,
        timestamps=False,
        tail_lines=None,
        limit_bytes=None,
    ) -> str:
        params = {}
        if container is not None:
            params["container"] = container
        if pretty is not None:
            params["pretty"] = pretty
        if previous:
            params["previous"] = "true"
        if since_seconds is not None and since_time is None:
            params["sinceSeconds"] = int(since_seconds)
        elif since_time is not None and since_seconds is None:
            params["sinceTime"] = since_time
        if timestamps:
            params["timestamps"] = "true"
        if tail_lines is not None:
            params["tailLines"] = int(tail_lines)
        if limit_bytes is not None:
            params["limitBytes"] = int(limit_bytes)

        async with self.api.call_api(
            "GET",
            version=self.version,
            url=f"{self.endpoint}/{self.name}/log",
            namespace=self.namespace,
            params=params,
        ) as resp:
            return await resp.text()

    def portforward(self, remote_port: int, local_port: int = None) -> int:
        """Port forward a pod.

        Returns an instance of :class:`kr8s.portforward.PortForward` for this Pod.

        Example:
            This can be used as a an async context manager or with explicit start/stop methods.

            Context manager:

            >>> async with pod.portforward(8888) as port:
            ...     print(f"Forwarding to port {port}")
            ...     # Do something with port 8888


            Explict start/stop:

            >>> pf = pod.portforward(8888)
            >>> await pf.start()
            >>> print(f"Forwarding to port {pf.local_port}")
            >>> # Do something with port 8888
            >>> await pf.stop()
        """
        if self._asyncio:
            return AsyncPortForward(self, remote_port, local_port)
        return SyncPortForward(self, remote_port, local_port)


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
    scalable = True

    async def ready(self):
        """Check if the deployment is ready."""
        await self._refresh()
        return (
            self.raw["status"].get("observedGeneration", 0)
            >= self.raw["metadata"]["generation"]
            and self.raw["status"].get("readyReplicas", 0) == self.replicas
        )


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

    async def proxy_http_request(
        self, method: str, path: str, port: Optional[int] = None, **kwargs: Any
    ) -> ClientResponse:
        """Issue a HTTP request with specific HTTP method to proxy of a Service.

        Args:
            method: HTTP method to use.
            path: Path to proxy.
            port: Port to proxy to. If not specified, the first port in the
                Service's spec will be used.
            **kwargs: Additional keyword arguments to pass to the API call.
        """
        return await self._proxy_http_request(method, path, port, **kwargs)

    async def _proxy_http_request(
        self, method: str, path: str, port: Optional[int] = None, **kwargs: Any
    ) -> ClientResponse:
        if port is None:
            port = self.raw["spec"]["ports"][0]["port"]
        async with self.api.call_api(
            method,
            version=self.version,
            url=f"{self.endpoint}/{self.name}:{port}/proxy/{path}",
            namespace=self.namespace,
            **kwargs,
        ) as response:
            return response

    async def proxy_http_get(
        self, path: str, port: Optional[int] = None, **kwargs
    ) -> None:
        return await self._proxy_http_request("GET", path, port, **kwargs)

    async def proxy_http_post(
        self, path: str, port: Optional[int] = None, **kwargs
    ) -> None:
        return await self._proxy_http_request("POST", path, port, **kwargs)

    async def proxy_http_put(
        self, path: str, port: Optional[int] = None, **kwargs
    ) -> None:
        return await self._proxy_http_request("PUT", path, port, **kwargs)

    async def proxy_http_delete(
        self, path: str, port: Optional[int] = None, **kwargs
    ) -> None:
        return await self._proxy_http_request("DELETE", path, port, **kwargs)

    async def ready_pods(self) -> List[Pod]:
        """Return a list of ready pods for this service."""
        return await self._ready_pods()

    async def _ready_pods(self) -> List[Pod]:
        """Return a list of ready pods for this service."""
        pod_selector = ",".join([f"{k}={v}" for k, v in self.labels.items()])
        pods = await self.api._get("pods", label_selector=pod_selector)
        return [pod for pod in pods if await pod.ready()]

    async def ready(self) -> bool:
        """Check if the service is ready."""
        pods = await self._ready_pods()
        return len(pods) > 0

    def portforward(self, remote_port: int, local_port: int = None) -> int:
        """Port forward a service.

        Returns an instance of :class:`kr8s.portforward.PortForward` for this Service.

        Example:
            This can be used as a an async context manager or with explicit start/stop methods.

            Context manager:

            >>> async with service.portforward(8888) as port:
            ...     print(f"Forwarding to port {port}")
            ...     # Do something with port 8888


            Explict start/stop:

            >>> pf = service.portforward(8888)
            >>> await pf.start()
            >>> print(f"Forwarding to port {pf.local_port}")
            >>> # Do something with port 8888
            >>> await pf.stop()

        """
        if self._asyncio:
            return AsyncPortForward(self, remote_port, local_port)
        return SyncPortForward(self, remote_port, local_port)


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
    scalable = True

    async def ready(self):
        """Check if the deployment is ready."""
        await self._refresh()
        return (
            self.raw["status"].get("observedGeneration", 0)
            >= self.raw["metadata"]["generation"]
            and self.raw["status"].get("readyReplicas", 0) == self.replicas
        )


class ReplicaSet(APIObject):
    """A Kubernetes ReplicaSet."""

    version = "apps/v1"
    endpoint = "replicasets"
    kind = "ReplicaSet"
    plural = "replicasets"
    singular = "replicaset"
    namespaced = True
    scalable = True


class StatefulSet(APIObject):
    """A Kubernetes StatefulSet."""

    version = "apps/v1"
    endpoint = "statefulsets"
    kind = "StatefulSet"
    plural = "statefulsets"
    singular = "statefulset"
    namespaced = True
    scalable = True


## autoscaling/v1 objects


class HorizontalPodAutoscaler(APIObject):
    """A Kubernetes HorizontalPodAutoscaler."""

    version = "autoscaling/v2"
    endpoint = "horizontalpodautoscalers"
    kind = "HorizontalPodAutoscaler"
    plural = "horizontalpodautoscalers"
    singular = "horizontalpodautoscaler"
    namespaced = True


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
    scalable = True
    scalable_spec = "parallelism"


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


## policy/v1 objects


class PodDisruptionBudget(APIObject):
    """A Kubernetes PodDisruptionBudget."""

    version = "policy/v1"
    endpoint = "poddisruptionbudgets"
    kind = "PodDisruptionBudget"
    plural = "poddisruptionbudgets"
    singular = "poddisruptionbudget"
    namespaced = True


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


## apiextensions.k8s.io/v1 objects


class CustomResourceDefinition(APIObject):
    """A Kubernetes CustomResourceDefinition."""

    version = "apiextensions.k8s.io/v1"
    endpoint = "customresourcedefinitions"
    kind = "CustomResourceDefinition"
    plural = "customresourcedefinitions"
    singular = "customresourcedefinition"
    namespaced = False


## meta.k8s.io/v1 objects


class Table(APIObject):
    """A Kubernetes Table."""

    version = "meta.k8s.io/v1"
    endpoint = "tables"
    kind = "Table"
    plural = "tables"
    singular = "table"
    namespaced = False

    @property
    def rows(self) -> List[Dict]:
        """Table rows."""
        return self._raw["rows"]

    @property
    def column_definitions(self) -> List[Dict]:
        """Table column definitions."""
        return self._raw["columnDefinitions"]


def get_class(kind: str, version: str = None, _asyncio: bool = True) -> Type[APIObject]:
    for cls in APIObject.__subclasses__():
        if (
            hasattr(cls, "kind")
            and (cls.kind == kind or cls.singular == kind or cls.plural == kind)
            and (version is None or cls.version == version)
            and cls._asyncio == _asyncio
        ):
            return cls
    raise KeyError(f"No object registered for {version}/{kind}")


def object_from_spec(spec: dict, api: Api = None) -> APIObject:
    """Create an APIObject from a Kubernetes resource spec.

    Args:
        spec: A Kubernetes resource spec.

    Returns:
        A corresponding APIObject subclass instance.

    Raises:
        ValueError: If the resource kind or API version is not supported.
    """
    cls = get_class(spec["kind"], spec["apiVersion"])
    return cls(spec, api=api)
