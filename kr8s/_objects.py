# SPDX-FileCopyrightText: Copyright (c) 2023-2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from __future__ import annotations

import contextlib
import json
import pathlib
import re
import time
from typing import (
    Any,
    AsyncGenerator,
    BinaryIO,
    List,
    Literal,
    cast,
)

import anyio
import httpx
import jsonpath
import yaml
from box import Box

import kr8s
import kr8s.asyncio
from kr8s._api import Api
from kr8s._async_utils import sync
from kr8s._data_utils import (
    dict_to_selector,
    dot_to_nested_dict,
    list_dict_unpack,
    xdict,
)
from kr8s._exceptions import NotFoundError, ServerError
from kr8s._exec import Exec
from kr8s._types import SpecType, SupportsKeysAndGetItem
from kr8s.asyncio.portforward import PortForward as AsyncPortForward
from kr8s.portforward import PortForward as SyncPortForward

JSONPATH_CONDITION_EXPRESSION = r"jsonpath='{(?P<expression>.*?)}'=(?P<condition>.*)"


class APIObject:
    """Base class for Kubernetes objects."""

    version: str
    endpoint: str
    kind: str
    plural: str
    singular: str
    namespaced: bool = False
    scalable: bool = False
    scalable_spec: str = "replicas"
    _asyncio: bool = True

    def __init__(
        self, resource: SpecType, namespace: str | None = None, api: Api | None = None
    ) -> None:
        """Initialize an APIObject."""
        if isinstance(resource, dict):
            self.raw = resource
        elif isinstance(resource, SupportsKeysAndGetItem):
            self.raw = dict(resource)
        elif isinstance(resource, str):
            self.raw = {"metadata": {"name": resource}}
        elif hasattr(resource, "to_dict"):
            self.raw = resource.to_dict()
        elif hasattr(resource, "obj") and isinstance(resource.obj, dict):
            self.raw = resource.obj
        else:
            raise ValueError(
                "resource must be a dict, string, have a to_dict method or an obj attribute containing a dict"
            )
        if namespace is not None:
            self.raw["metadata"]["namespace"] = namespace  # type: ignore
        self._api = api
        if self._api is None and not self._asyncio:
            self._api = kr8s.api()

    def __await__(self):
        async def f():
            if self._api is None:
                self._api = await kr8s.asyncio.api()
            return self

        return f().__await__()

    def __repr__(self):
        """Return a string representation of the Kubernetes resource."""
        if "name" in self.metadata:
            return f"<{self.kind} {self.name}>"
        if "generateName" in self.metadata:
            return f"<{self.kind} generateName({self.metadata.generateName})>"
        return f"<{self.kind} UNKNOWN>"

    def __str__(self):
        """Return a string representation of the Kubernetes resource."""
        return self.name

    def __eq__(self, other):
        if self.version != other.version:
            return False
        if self.kind != other.kind:
            return False
        if self.name != other.name:
            return False
        if self.namespaced and self.namespace != other.namespace:
            return False
        return True

    @property
    def api(self):
        if self._api is None and self._asyncio:
            raise RuntimeError(
                f"{self.__repr__()} has not been initialized with an API object. "
                "Did you forget to await it?"
            )
        return self._api

    @api.setter
    def api(self, value):
        self._api = value

    @property
    def raw(self) -> Any:
        """Raw object returned from the Kubernetes API."""
        self._raw.update({"kind": self.kind, "apiVersion": self.version})
        return self._raw

    @raw.setter
    def raw(self, value: Any) -> None:
        self._raw = Box(value)

    @property
    def name(self) -> str:
        """Name of the Kubernetes resource."""
        if "name" in self.metadata:
            return self.metadata.name
        if "generateName" in self.metadata:
            raise ValueError("Resource has a generateName that has not been resolved")
        raise ValueError("Resource does not have a name")

    @name.setter
    def name(self, value: str) -> None:
        self.raw["metadata"]["name"] = value

    @property
    def namespace(self) -> str | None:
        """Namespace of the Kubernetes resource."""
        if self.namespaced:
            assert self.api
            return self.raw.get("metadata", {}).get("namespace", self.api.namespace)
        return None

    @namespace.setter
    def namespace(self, value: str) -> None:
        if self.namespaced:
            self.raw["metadata"]["namespace"] = value

    @property
    def metadata(self) -> Box:
        """Metadata of the Kubernetes resource."""
        return self.raw["metadata"]

    @metadata.setter
    def metadata(self, value: dict) -> None:
        self.raw["metadata"] = value

    @property
    def spec(self) -> Box:
        """Spec of the Kubernetes resource."""
        return self.raw["spec"]

    @spec.setter
    def spec(self, value: dict) -> None:
        self.raw["spec"] = value

    @property
    def status(self) -> Box:
        """Status of the Kubernetes resource."""
        return self.raw["status"]

    @status.setter
    def status(self, value: dict) -> None:
        self.raw["status"] = value

    @property
    def labels(self) -> Box:
        """Labels of the Kubernetes resource."""
        try:
            return self.raw["metadata"]["labels"]
        except KeyError:
            return Box({})

    @labels.setter
    def labels(self, value: dict) -> None:
        self.raw["metadata"]["labels"] = value

    @property
    def annotations(self) -> Box:
        """Annotations of the Kubernetes resource."""
        try:
            return self.raw["metadata"]["annotations"]
        except KeyError:
            return Box({})

    @annotations.setter
    def annotations(self, value: dict) -> None:
        self.raw["metadata"]["annotations"] = value

    @property
    def replicas(self) -> int:
        """Replicas of the Kubernetes resource."""
        if self.scalable:
            keys = self.scalable_spec.split(".")
            spec = self.raw["spec"]
            for key in keys:
                spec = spec[key]
            return spec
        raise NotImplementedError(f"{self.kind} is not scalable")

    @replicas.setter
    def replicas(self, value: int) -> None:
        if self.scalable:
            raise NotImplementedError(
                f"Use scale() method to set replicas for {self.kind}"
            )
        else:
            raise NotImplementedError(f"{self.kind} is not scalable")

    @classmethod
    async def get(
        cls,
        name: str | None = None,
        namespace: str | None = None,
        api: Api | None = None,
        label_selector: str | dict[str, str] | None = None,
        field_selector: str | dict[str, str] | None = None,
        timeout: int = 2,
        **kwargs,
    ) -> APIObject:
        """Get a Kubernetes resource by name or via selectors."""
        if api is None:
            if cls._asyncio:
                api = await kr8s.asyncio.api()
            else:
                api = await kr8s.asyncio.api(_asyncio=False)
        namespace = namespace if namespace else api.namespace
        start = time.time()
        backoff = 0.1
        while start + timeout > time.time():
            if name:
                try:
                    resources = await api.async_get(
                        cls,
                        name,
                        namespace=namespace,
                        field_selector={"metadata.name": name},
                        **kwargs,
                    )
                except ServerError as e:
                    if e.response and e.response.status_code == 404:
                        continue
                    raise e
            elif label_selector or field_selector:
                resources = await api.async_get(
                    cls,
                    namespace=namespace,
                    label_selector=label_selector,
                    field_selector=field_selector,
                    **kwargs,
                )
            else:
                raise ValueError("Must specify name or selector")
            if not isinstance(resources, list):
                resources = [resources]
            if len(resources) == 0:
                await anyio.sleep(backoff)
                backoff = min(backoff * 2, 1)
                continue
            if len(resources) > 1:
                raise ValueError(
                    f"Expected exactly one {cls.kind} object. Use selectors to narrow down the search."
                )
            return resources[0]
        raise NotFoundError(
            f"Could not find {cls.kind} {name} in namespace {namespace}."
        )

    async def exists(self, ensure=False) -> bool:
        """Check if this object exists in Kubernetes."""
        return await self.async_exists(ensure=ensure)

    async def async_exists(self, ensure=False) -> bool:
        """Check if this object exists in Kubernetes."""
        try:
            assert self.api
            async with self.api.call_api(
                "GET",
                version=self.version,
                url=f"{self.endpoint}/{self.name}",
                namespace=self.namespace,
                raise_for_status=False,
            ) as resp:
                status = resp.status_code
        except ValueError:
            status = 400
        if status == 200:
            return True
        if ensure:
            raise NotFoundError(
                f"Object {self.name} does not exist in {self.namespace}"
            )
        return False

    async def create(self) -> None:
        """Create this object in Kubernetes."""
        assert self.api
        async with self.api.call_api(
            "POST",
            version=self.version,
            url=self.endpoint,
            namespace=self.namespace,
            data=json.dumps(self.raw),
        ) as resp:
            self.raw = resp.json()

    async def delete(self, propagation_policy: str | None = None) -> None:
        """Delete this object from Kubernetes."""
        data = {}
        if propagation_policy:
            data["propagationPolicy"] = propagation_policy
        try:
            assert self.api
            async with self.api.call_api(
                "DELETE",
                version=self.version,
                url=f"{self.endpoint}/{self.name}",
                namespace=self.namespace,
                data=json.dumps(data),
            ):
                pass
        except ServerError as e:
            if e.response and e.response.status_code == 404:
                raise NotFoundError(
                    f"Object {self.name} does not exist in {self.namespace}"
                ) from e
            raise e

    async def refresh(self) -> None:
        """Refresh this object from Kubernetes."""
        await self.async_refresh()

    async def async_refresh(self) -> None:
        """Refresh this object from Kubernetes."""
        try:
            assert self.api
            async with self.api.call_api(
                "GET",
                version=self.version,
                url=f"{self.endpoint}/{self.name}",
                namespace=self.namespace,
            ) as resp:
                self.raw = resp.json()
        except ServerError as e:
            if e.response and e.response.status_code == 404:
                raise NotFoundError(
                    f"Object {self.name} does not exist in {self.namespace}"
                ) from e
            raise e

    async def patch(self, patch, *, subresource=None, type=None) -> None:
        """Patch this object in Kubernetes."""
        await self.async_patch(patch, subresource=subresource, type=type)

    async def async_patch(self, patch: dict, *, subresource=None, type=None) -> None:
        """Patch this object in Kubernetes."""
        url = f"{self.endpoint}/{self.name}"
        if type == "json":
            headers = {"Content-Type": "application/json-patch+json"}
        else:
            headers = {"Content-Type": "application/merge-patch+json"}
        if subresource:
            url = f"{url}/{subresource}"
        try:
            assert self.api
            async with self.api.call_api(
                "PATCH",
                version=self.version,
                url=url,
                namespace=self.namespace,
                data=json.dumps(patch),
                headers=headers,
            ) as resp:
                self.raw = resp.json()
        except ServerError as e:
            if e.response and e.response.status_code == 404:
                raise NotFoundError(
                    f"Object {self.name} does not exist in {self.namespace}"
                ) from e
            raise e

    async def scale(self, replicas: int | None = None) -> None:
        """Scale this object in Kubernetes."""
        if not self.scalable:
            raise NotImplementedError(f"{self.kind} is not scalable")
        await self.async_exists(ensure=True)
        await self.async_patch(
            {"spec": dot_to_nested_dict(self.scalable_spec, replicas)}
        )
        while self.replicas != replicas:
            await self.async_refresh()
            await anyio.sleep(0.1)

    async def async_watch(self):
        """Watch this object in Kubernetes."""
        since = self.metadata.get("resourceVersion")
        assert self.api
        async for event, obj in self.api.async_watch(
            self.endpoint,
            namespace=self.namespace,
            field_selector=f"metadata.name={self.name}",
            since=since,
        ):
            self.raw = obj.raw
            yield event, self

    async def watch(self):
        """Watch this object in Kubernetes."""
        async for event, obj in self.async_watch():
            yield event, obj

    async def _test_conditions(
        self, conditions: list, mode: Literal["any", "all"] = "any"
    ) -> bool:
        """Test if conditions are met.

        Args:
            conditions: A list of conditions to test.
            mode: Match any condition with "any" or all conditions with "all". Defaults to "any".

        Returns:
            bool: True if any condition is met, False otherwise.
        """
        results = []
        for condition in conditions:
            if condition.startswith("condition"):
                condition = "=".join(condition.split("=")[1:])
                if "=" in condition:
                    field, value = condition.split("=")
                    value = str(value)
                else:
                    field = condition
                    value = str(True)
                if value == "true" or value == "false":
                    value = value.title()
                status_conditions = list_dict_unpack(
                    self.status.get("conditions", []), "type", "status"
                )
                results.append(status_conditions.get(field, None) == value)
            elif condition == "delete":
                results.append(not await self.async_exists())
            elif condition.startswith("jsonpath"):
                matches = re.search(JSONPATH_CONDITION_EXPRESSION, condition)
                if not matches:
                    raise ValueError(
                        f"Invalid jsonpath condition expression '{condition}'"
                    )
                expression = matches.group("expression")
                condition = matches.group("condition")
                [value] = jsonpath.findall(expression, self.raw)
                results.append(str(value) == str(condition))
            else:
                raise ValueError(f"Unknown condition type {condition}")
        if mode == "any":
            return any(results)
        elif mode == "all":
            return all(results)
        else:
            raise ValueError(f"Unknown wait mode '{mode}', must be 'any' or 'all'")

    async def wait(
        self,
        conditions: list[str] | str,
        mode: Literal["any", "all"] = "any",
        timeout: int | None = None,
    ):
        """Wait for conditions to be met.

        Args:
            conditions: A list of conditions to wait for.
            mode: Match any condition with "any" or all conditions with "all". Defaults to "any".
            timeout: Timeout in seconds.

        Example:
            Wait for a Pod to be ready.

            >>> from kr8s.objects import Pod
            >>> pod = Pod.get("my-pod")
            >>> pod.wait("condition=Ready")

            Wait for a Job to either succeed or fail.

            >>> from kr8s.objects import Job
            >>> job = Job.get("my-jod")
            >>> job.wait(["condition=Complete", "condition=Failed"])

            Wait for a Pod to be initialized and ready to start containers.

            >>> from kr8s.objects import Pod
            >>> pod = Pod.get("my-pod")
            >>> pod.wait(["condition=Initialized", "condition=PodReadyToStartContainers"], mode="all")

        Note:
            As of the current Kubertenetes release when this function was written (1.29) kubectl doesn't support
            multiple conditions. There is a PR to implement this but it hasn't been merged yet
            https://github.com/kubernetes/kubernetes/pull/119205.

            Given that ``for`` is a reserved word anyway we can't exactly match the kubectl API so
            we use ``condition`` in combination with a ``mode`` instead.
        """
        if isinstance(conditions, str):
            conditions = [conditions]

        with anyio.fail_after(timeout):
            try:
                await self.async_refresh()
            except NotFoundError:
                if set(conditions) == {"delete"}:
                    return
            if await self._test_conditions(conditions, mode=mode):
                return
            async for _ in self.async_watch():
                if await self._test_conditions(conditions, mode=mode):
                    return

    async def annotate(self, annotations: dict | None = None, **kwargs) -> None:
        """Annotate this object in Kubernetes."""
        if annotations is None:
            annotations = kwargs
        if not annotations:
            raise ValueError("No annotations provided")
        await self.async_patch({"metadata": {"annotations": annotations}})

    async def label(self, labels: dict | None = None, **kwargs) -> None:
        """Add labels to this object in Kubernetes.

        Labels can be passed as a dictionary or as keyword arguments.

        Args:
            labels:
                A dictionary of labels to set.
            **kwargs:
                Labels to set.

        Example:
            >>> from kr8s.objects import Deployment
            >>> deployment = Deployment.get("my-deployment")
            >>> # Both of these are equivalent
            >>> deployment.label({"app": "my-app"})
            >>> deployment.label(app="my-app")
        """
        if labels is None:
            labels = kwargs
        if not labels:
            raise ValueError("No labels provided")
        await self.async_patch({"metadata": {"labels": labels}})

    def keys(self) -> list:
        """Return the keys of this object."""
        return self.raw.keys()

    def __getitem__(self, key: str) -> Any:
        """Get an item from this object."""
        return self.raw[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set an item in this object."""
        self.raw[key] = value

    async def set_owner(self, owner: APIObject) -> None:
        """Set the owner reference of this object.

        See https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/

        Args:
            owner: The owner object to set a reference to.

        Example:
            >>> from kr8s.objects import Deployment, Pod
            >>> deployment = Deployment.get("my-deployment")
            >>> pod = Pod.get("my-pod")
            >>> pod.set_owner(deployment)
        """
        await self.async_set_owner(owner)

    async def async_set_owner(self, owner: APIObject) -> None:
        """Set the owner of this object."""
        await self.async_patch(
            {
                "metadata": {
                    "ownerReferences": [
                        {
                            "controller": True,
                            "blockOwnerDeletion": True,
                            "apiVersion": owner.version,
                            "kind": owner.kind,
                            "name": owner.name,
                            "uid": owner.metadata.uid,
                        }
                    ],
                }
            }
        )

    async def adopt(self, child: APIObject) -> None:
        """Adopt this object.

        This will set the owner reference of the child object to this object.

        See https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/

        Args:
            child: The child object to adopt.

        Example:
            >>> from kr8s.objects import Deployment, Pod
            >>> deployment = Deployment.get("my-deployment")
            >>> pod = Pod.get("my-pod")
            >>> deployment.adopt(pod)

        """
        await child.async_set_owner(self)

    def to_dict(self) -> dict:
        """Return a dictionary representation of this object."""
        return self.raw

    def to_lightkube(self) -> Any:
        """Return a lightkube representation of this object."""
        try:
            from lightkube import codecs
        except ImportError as e:
            raise ImportError("lightkube is not installed") from e
        return codecs.from_dict(self.raw)

    def to_pykube(self, api) -> Any:
        """Return a pykube representation of this object.

        Args:
            api: A pykube API object.

        Example:
            >>> from kr8s.objects import Deployment
            >>> deployment = Deployment.get("my-deployment")
            >>> # Create a pykube API object
            >>> from pykube import HTTPClient
            >>> api = HTTPClient()
            >>> pykube_deployment = deployment.to_pykube(api)

        """
        try:
            import pykube  # type: ignore
        except ImportError as e:
            raise ImportError("pykube is not installed") from e
        try:
            pykube_cls = getattr(pykube.objects, self.kind)
        except AttributeError:
            base = (
                pykube.objects.NamespacedAPIObject
                if self.namespaced
                else pykube.objects.APIObject
            )
            pykube_cls = type(
                self.kind,
                (base,),
                {"version": self.version, "endpoint": self.endpoint, "kind": self.kind},
            )
        return pykube_cls(api, self.raw)

    @classmethod
    def gen(cls, *args, **kwargs):
        raise NotImplementedError("gen is not implemented for this object")

    # Must be the last method defined due to https://github.com/python/mypy/issues/17517
    @classmethod
    async def list(cls, **kwargs) -> APIObject | list[APIObject]:
        """List objects in Kubernetes.

        Args:
            **kwargs: Keyword arguments to pass to :func:`kr8s.get`.

        Returns:
            A list of objects.
        """
        api = await kr8s.asyncio.api()
        return await api.async_get(kind=cls, **kwargs)


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

    @property
    def data(self) -> Box:
        """Data of the ConfigMap."""
        return self.raw["data"]

    @data.setter
    def data(self, value: dict) -> None:
        self.raw["data"] = value


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
        """Cordon the node.

        This will mark the node as unschedulable.
        """
        await self.async_patch({"spec": {"unschedulable": True}})

    async def uncordon(self) -> None:
        """Uncordon the node.

        This will mark the node as schedulable.
        """
        await self.async_patch({"spec": {"unschedulable": False}})


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

    async def async_ready(self) -> bool:
        """Check if the pod is ready."""
        await self.async_refresh()
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

    async def ready(self) -> bool:
        """Check if the pod is ready."""
        return await self.async_ready()

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
        follow=False,
        timeout=3600,
    ) -> AsyncGenerator[str]:
        """Streams logs from a Pod.

        Args:
            container:
                The container to get logs from. Defaults to the first container in the Pod.
            pretty:
                If True, return pretty logs. Defaults to False.
            previous:
                If True, return previous terminated container logs. Defaults to False.
            since_seconds:
                If set, return logs since this many seconds ago.
            since_time:
                If set, return logs since this time.
            timestamps:
                If True, prepend each log line with a timestamp. Defaults to False.
            tail_lines:
                If set, return this many lines from the end of the logs.
            limit_bytes:
                If set, return this many bytes from the end of the logs.
            follow:
                If True, follow the logs until the timeout is reached. Defaults to False.
            timeout:
                If following timeout after this many seconds. Set to None to disable timeout.

        Returns:
            An async generator yielding log lines.


        Example:
            >>> from kr8s.objects import Pod
            >>> pod = Pod.get("my-pod")
            >>> for line in pod.logs():
            ...     print(line)

            We can also follow logs as they are generated, the generator will yield a new log line as
            it is generated by the Pod. This blocks indefinitely so we can set a timeout to break
            after some period of time, the default is ``3600`` (1hr) but can be set to ``None`` to
            disable the timeout.

            >>> from kr8s.objects import Pod
            >>> pod = Pod.get("my-pod", namespace="ns")
            >>> for line in pod.logs(follow=True, timeout=60):
            ...     # Will continue streaming logs until 60 seconds or the Pod is terminated
            ...     print(line)

        """
        params: dict[Any, Any] = {}
        if follow:
            params["follow"] = "true"
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

        with contextlib.suppress(httpx.ReadTimeout):
            assert self.api
            async with self.api.call_api(
                "GET",
                version=self.version,
                url=f"{self.endpoint}/{self.name}/log",
                namespace=self.namespace,
                params=params,
                stream=True,
                timeout=timeout,
            ) as resp:
                async for line in resp.aiter_lines():
                    yield line

    def portforward(
        self,
        remote_port: int,
        local_port: int | None = None,
        address: list[str] | str = "127.0.0.1",
    ) -> SyncPortForward | AsyncPortForward:
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

            Explict bind address:

            >>> async with pod.PortForward(8888, address=["127.0.0.1", "10.20.0.1"]) as port:
            ...     print(f"Forwarding to port {port}")
            ...     # Do something with port 8888 on the Pod, port will be bind to 127.0.0.1 and 10.20.0.1

        """
        if isinstance(address, str):
            address = [address]
        if self._asyncio:
            return AsyncPortForward(self, remote_port, local_port, address)
        return SyncPortForward(self, remote_port, local_port, address)

    async def async_exec(
        self,
        command: list[str],
        *,
        container: str | None = None,
        stdin: str | BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        check: bool = True,
        capture_output: bool = True,
    ):
        while not await self.async_ready():
            await anyio.sleep(0.1)

        ex = Exec(
            self,
            command,
            container=container,
            stdout=stdout,
            stderr=stderr,
            stdin=stdin,
            check=check,
            capture_output=capture_output,
        )
        async with ex.run() as process:
            await process.wait()
            return process.as_completed()

    async def exec(
        self,
        command: list[str],
        *,
        container: str | None = None,
        stdin: str | BinaryIO | None = None,
        stdout: BinaryIO | None = None,
        stderr: BinaryIO | None = None,
        check: bool = True,
        capture_output: bool = True,
    ):
        """Run a command in a container and wait until it completes.

        Behaves like :func:`subprocess.run`.

        Args:
            command:
                Command to execute.
            container:
                Container to execute the command in.
            stdin:
                If set, read stdin to the container.
            stdout:
                If set, write stdout to the provided writable stream object.
            stderr:
                If set, write stderr to the provided writable stream object.
            check:
                If True, raise an exception if the command fails.
            capture_output:
                If True, store stdout and stderr from the container in an attribute.

        Returns:
            A :class:`kr8s._exec.CompletedExec` object.

        Example:
            >>> from kr8s.objects import Pod
            >>> pod = Pod.get("my-pod")
            >>> ex = await pod.exec(["ls", "-l"])
            >>> print(ex.stdout)
            >>> print(ex.stderr)
        """
        return await self.async_exec(
            command,
            container=container,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            check=check,
            capture_output=capture_output,
        )

    @classmethod
    def gen(
        cls,
        *,
        name=None,
        generate_name=None,
        image=None,
        namespace=None,
        annotations=None,
        command=None,
        env=None,
        resources=None,
        image_pull_policy=None,
        labels=None,
        ports=None,
        restart="Always",
    ):
        """Generate a pod definition.

        Args:
            name (str): The name of the pod.
            generate_name (str): Template for generating the name of the pod.
            namespace (str): The namespace of the pod.
            image (str): The image to use.
            annotations (dict): Annotations to add to the pod.
            command (list): Command to run in the container.
            env (dict): Environment variables to set in the container.
            resources (dict): Resources to set in the container.
            image_pull_policy (str): Image pull policy to use.
            labels (dict): Labels to add to the pod.
            ports (list|int): Ports to expose.
            restart (str): Restart policy to use.

        Returns:
            A :class:`kr8s.objects.Pod` object.

        Example:
            >>> from kr8s.objects import Pod
            >>> pod = Pod.gen(name="my-pod", image="my-image")
            >>> pod.create()

            Create an nginx Pod that exposes port 80.
            >>> from kr8s.objects import Pod
            >>> pod = Pod.gen(name="nginx", image="nginx:latest", ports=[80])
            >>> pod.create()

            Create an wordpress Pod that exposes port 80.
            >>> from kr8s.objects import Pod
            >>> pod = Pod.gen(name="wordpress", image="wordpress:latest", ports=[{"containerPort": 80}])
            >>> pod.create()

            Create a Pod that requires a GPU
            >>> from kr8s.objects import Pod
            >>> pod = Pod.gen(name="cuda-vectoradd",
            ...               image="nvidia/samples:vectoradd-cuda11.6.0-ubuntu18.04",
            ...               resources={"limits": {"nvidia.com/gpu": 1}})
        """
        if not image:
            raise ValueError("Image must be specified")
        if not name and not generate_name:
            raise ValueError("Name or generate_name must be specified")
        if ports:
            if isinstance(ports, int):
                ports = [ports]
            # Convert any integer ports to valid v1.ContainerPort format
            ports = [
                {"containerPort": port} if isinstance(port, int) else port
                for port in ports
            ]

        return cls(
            xdict(
                apiVersion="v1",
                kind="Pod",
                metadata=xdict(
                    name=name,
                    generateName=generate_name,
                    namespace=namespace,
                    annotations=annotations,
                    labels=labels,
                ),
                spec=xdict(
                    containers=[
                        xdict(
                            name=name if name else "container",
                            image=image,
                            command=command,
                            env=env,
                            resources=resources,
                            imagePullPolicy=image_pull_policy,
                            ports=ports,
                        )
                    ],
                    restartPolicy=restart,
                ),
            )
        )


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
        await self.async_refresh()
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

    @property
    def data(self) -> Box:
        """Data of the Secret."""
        return self.raw["data"]

    @data.setter
    def data(self, value: dict) -> None:
        self.raw["data"] = value


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
        self, method: str, path: str, port: int | None = None, **kwargs: Any
    ) -> httpx.Response:
        """Issue a HTTP request with specific HTTP method to proxy of a Service.

        Args:
            method: HTTP method to use.
            path: Path to proxy.
            port: Port to proxy to. If not specified, the first port in the
                Service's spec will be used.
            **kwargs: Additional keyword arguments to pass to the API call.
        """
        return await self.async_proxy_http_request(method, path, port, **kwargs)

    async def async_proxy_http_request(
        self, method: str, path: str, port: int | None = None, **kwargs: Any
    ) -> httpx.Response:
        if port is None:
            port = self.raw["spec"]["ports"][0]["port"]
        assert self.api
        async with self.api.call_api(
            method,
            version=self.version,
            url=f"{self.endpoint}/{self.name}:{port}/proxy/{path}",
            namespace=self.namespace,
            **kwargs,
        ) as response:
            return response

    async def proxy_http_get(
        self, path: str, port: int | None = None, **kwargs
    ) -> httpx.Response:
        return await self.async_proxy_http_request("GET", path, port, **kwargs)

    async def proxy_http_post(
        self, path: str, port: int | None = None, **kwargs
    ) -> None:
        await self.async_proxy_http_request("POST", path, port, **kwargs)

    async def proxy_http_put(
        self, path: str, port: int | None = None, **kwargs
    ) -> httpx.Response:
        return await self.async_proxy_http_request("PUT", path, port, **kwargs)

    async def proxy_http_delete(
        self, path: str, port: int | None = None, **kwargs
    ) -> httpx.Response:
        return await self.async_proxy_http_request("DELETE", path, port, **kwargs)

    async def ready_pods(self) -> list[Pod]:
        """Return a list of ready Pods for this Service."""
        return await self.async_ready_pods()

    async def async_ready_pods(self) -> list[Pod]:
        """Return a list of ready Pods for this Service."""
        assert self.api
        pods = await self.api.async_get(
            "pods",
            label_selector=dict_to_selector(self.spec["selector"]),
            namespace=self.namespace,
        )
        if isinstance(pods, Pod):
            pods = [pods]
        elif isinstance(pods, List) and all(isinstance(pod, Pod) for pod in pods):
            # The all(isinstance(...) for ...) check doesn't seem to narrow the type
            # correctly in pyright so we need to explicitly use cast
            pods = cast(List[Pod], pods)
        else:
            raise TypeError(f"Unexpected type {type(pods)} returned from API")
        return [pod for pod in pods if await pod.async_ready()]

    async def ready(self) -> bool:
        """Check if the service is ready."""
        await self.async_refresh()

        # If the service is of type LoadBalancer, check if it has endpoints
        if (
            self.spec.type == "LoadBalancer"
            and len(self.status.loadBalancer.ingress or []) == 0
        ):
            return False

        # Check there is at least one Pod in service
        pods = await self.async_ready_pods()
        return len(pods) > 0

    def portforward(
        self,
        remote_port: int,
        local_port: int | None = None,
        address: str | list[str] = "127.0.0.1",
    ) -> SyncPortForward | AsyncPortForward:
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
        if isinstance(address, str):
            address = [address]
        if self._asyncio:
            return AsyncPortForward(self, remote_port, local_port, address)
        return SyncPortForward(self, remote_port, local_port, address)


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

    async def pods(self) -> list[Pod]:
        """Return a list of Pods for this Deployment."""
        assert self.api
        pods = await self.api.async_get(
            "pods",
            label_selector=dict_to_selector(self.spec["selector"]["matchLabels"]),
            namespace=self.namespace,
        )
        if isinstance(pods, Pod):
            return [pods]
        if isinstance(pods, List) and all(isinstance(pod, Pod) for pod in pods):
            # The all(isinstance(...) for ...) check doesn't seem to narrow the type
            # correctly in pyright so we need to explicitly use cast
            return cast(List[Pod], pods)
        raise TypeError(f"Unexpected type {type(pods)} returned from API")

    async def ready(self):
        """Check if the deployment is ready."""
        await self.async_refresh()
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
    def rows(self) -> list[dict]:
        """Table rows."""
        return self.raw["rows"]

    @property
    def column_definitions(self) -> list[dict]:
        """Table column definitions."""
        return self.raw["columnDefinitions"]


def get_class(
    kind: str,
    version: str | None = None,
    _asyncio: bool = True,
) -> type[APIObject]:
    """Get an APIObject subclass by kind and version.

    Args:
        kind: The Kubernetes resource kind.
        version: The Kubernetes API group/version.

    Returns:
        An APIObject subclass.

    Raises:
        KeyError: If no object is registered for the given kind and version.
    """
    result = None
    group = None
    if "/" in kind:
        kind, version = kind.split("/", 1)
    if "." in kind:
        kind, group = kind.split(".", 1)
    if version and "/" in version:
        if group:
            raise ValueError("Cannot specify group in both kind and version")
        group, version = version.split("/", 1)
    kind = kind.lower()

    def _walk_subclasses(cls):
        yield cls
        for subcls in cls.__subclasses__():
            yield from _walk_subclasses(subcls)

    for cls in _walk_subclasses(APIObject):
        if not hasattr(cls, "version"):
            continue
        if "/" in cls.version:
            cls_group, cls_version = cls.version.split("/")
        else:
            cls_group, cls_version = None, cls.version
        if (
            hasattr(cls, "kind")
            and cls._asyncio == _asyncio
            and (cls.kind == kind or cls.singular == kind or cls.plural == kind)
        ):
            if (group is None or cls_group == group) and (
                version is None or cls_version == version
            ):
                result = cls
            if (
                group
                and not version
                and "." in group
                and cls_group == group.split(".", 1)[1]
                and cls_version == group.split(".", 1)[0]
            ):
                result = cls

    if result:
        return result
    raise KeyError(
        f"No object registered for {kind}{'.' + group if group else ''}. "
        "See https://docs.kr8s.org/en/stable/object.html#extending-the-objects-api "
        "for more information on how to register a new object."
    )


def new_class(
    kind: str,
    version: str | None = None,
    asyncio: bool = True,
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
    if "." in kind:
        kind, version = kind.split(".", 1)
    if version is None:
        version = "v1"
    plural = plural or kind.lower() + "s"
    newcls = type(
        kind,
        (APIObject,),
        {
            "kind": kind,
            "version": version,
            "_asyncio": asyncio,
            "endpoint": plural.lower(),
            "plural": plural.lower(),
            "singular": kind.lower(),
            "namespaced": namespaced,
            "scalable": scalable or False,
            "scalable_spec": scalable_spec or "replicas",
        },
    )
    if not asyncio:
        newcls = sync(newcls)
    return newcls


def object_from_spec(
    spec: dict,
    api: Api | None = None,
    allow_unknown_type: bool = False,
    _asyncio: bool = True,
) -> APIObject:
    """Create an APIObject from a Kubernetes resource spec.

    Args:
        spec: A Kubernetes resource spec.
        api: An optional API instance to use.
        allow_unknown_type: Whether to allow unknown resource types.
        _asyncio: Whether to use asyncio or not.

    Returns:
        A corresponding APIObject subclass instance.

    Raises:
        ValueError: If the resource kind or API version is not supported.
    """
    try:
        cls = get_class(spec["kind"], spec["apiVersion"], _asyncio=_asyncio)
    except KeyError:
        if allow_unknown_type:
            cls = new_class(spec["kind"], spec["apiVersion"], asyncio=_asyncio)
        else:
            raise
    return cls(spec, api=api)


async def object_from_name_type(
    name: str,
    namespace: str | None = None,
    api: Api | None = None,
    _asyncio: bool = True,
) -> APIObject:
    """Create an APIObject from a Kubernetes resource name.

    Args:
        name: A Kubernetes resource name.
        namespace: The namespace of the resource.
        api: An optional API instance to use.
        _asyncio: Whether to use asyncio or not.

    Returns:
        A corresponding APIObject subclass instance.

    Raises:
        ValueError: If the resource kind or API version is not supported.
    """
    if "/" not in name:
        raise ValueError(f"Invalid name: {name}. Expecting format of 'resource/name'.")
    resource_type, name = name.split("/")
    if "." in resource_type:
        kind = resource_type.split(".")[0]
        version = ".".join(resource_type.split(".")[1:])
    else:
        kind = resource_type
        version = None
    cls = get_class(kind, version, _asyncio=_asyncio)
    return await cls.get(name, namespace=namespace, api=api)


async def objects_from_files(
    path: str | pathlib.Path,
    api: Api | None = None,
    recursive: bool = False,
    _asyncio: bool = True,
) -> list[APIObject]:
    """Create APIObjects from Kubernetes resource files.

    Args:
        path: A path to a Kubernetes resource file or directory of resource files.
        api: An optional API instance to use.
        recursive: Whether to recursively search for resource files in subdirectories.
        _asyncio: Whether to use asyncio or not.

    Returns:
        A list of APIObject subclass instances.

    Raises:
        ValueError: If the resource kind or API version is not supported.
    """
    path = pathlib.Path(path)
    if path.is_dir():
        pattern = "**/*.yaml" if recursive else "*.yaml"
        files = [f for f in path.glob(pattern) if f.is_file()]
    else:
        files = [path]
    if not api:
        api = await kr8s.asyncio.api(_asyncio=_asyncio)
    objects = []
    for file in files:
        with open(file) as f:
            for doc in yaml.safe_load_all(f):
                if doc is not None:
                    obj = object_from_spec(
                        doc, api=api, allow_unknown_type=True, _asyncio=_asyncio
                    )
                    if _asyncio:
                        await obj
                    objects.append(obj)
    return objects


def parse_kind(kind: str) -> tuple[str, str, str]:
    """Parse a Kubernetes resource kind into a tuple of (kind, group, version).

    Args:
        kind: The Kubernetes resource kind.

    Returns:
        A tuple of (kind, group, version).

    Example:
        >>> parse_kind("Pod")
        ("pod", "", "")
        >>> parse_kind("deployment")
        ("deployment", "", "")
        >>> parse_kind("services/v1")
        ("services", "", "v1")
        >>> parse_kind("ingress.networking.k8s.io/v1")
        ("ingress", "networking.k8s.io", "v1")
        >>> parse_kind("role.v1.rbac.authorization.k8s.io")
        ("role", "rbac.authorization.k8s.io", "v1")
    """
    if "/" in kind:
        kind, version = kind.split("/", 1)
    else:
        version = ""
    if "." in kind:
        kind, group = kind.split(".", 1)
    else:
        group = ""
    if "." in group:
        first, potential_group = group.split(".", 1)
        if re.match(r"v\d[a-z0-9]*", first):
            version = first
            group = potential_group
    return kind.lower(), group.lower(), version.lower()
