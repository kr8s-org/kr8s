# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, Yuvi Panda, Anaconda Inc, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import json
from typing import Optional

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
    def namespace(self) -> Optional[str]:
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

    async def update(self) -> None:
        """Update this object in Kubernetes."""
        raise NotImplementedError("Updating is not yet implemented")

    async def patch(self, patch: dict) -> None:
        """Patch this object in Kubernetes."""
        raise NotImplementedError("Patching is not yet implemented")

    async def watch(self, timeout: int = None):
        """Watch this object in Kubernetes."""
        raise NotImplementedError("Watching is not yet implemented")


class NamespacedAPIObject(APIObject):
    @property
    def namespace(self) -> str:
        """Namespace of the Kubernetes resource."""
        return self.raw.get("metadata", {}).get("namespace", self.api.auth.namespace)


class Pod(NamespacedAPIObject):
    """A Kubernetes Pod."""

    version = "v1"
    endpoint = "pods"
    kind = "Pod"
    plural = "pods"
    singular = "pod"

    async def ready(self):
        await self.refresh()
        conditions = list_dict_unpack(
            self.status.get("conditions", []),
            key="type",
            value="status",
        )
        return "Ready" in conditions and conditions.get("Ready", "False") == "True"


OBJECT_REGISTRY.register(Pod)
