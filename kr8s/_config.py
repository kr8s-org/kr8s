# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import pathlib
import typing
from typing import Any, Dict, List, Optional, Protocol, Union

import anyio
import jsonpath
import yaml

from kr8s._data_utils import dict_list_pack, list_dict_unpack
from kr8s._types import PathType

# TODO Implement set cluster
# TODO Implement delete cluster
# TODO Implement set context
# TODO Implement delete context
# TODO Implement set user
# TODO Implement delete user


class KubeConfigProtocol(Protocol):
    @property
    def raw(self) -> dict: ...


class KubeConfigMixin:

    def get(
        self: KubeConfigProtocol,
        path: Optional[str] = None,
        pointer: Optional[str] = None,
    ) -> Any:
        """Get a value from the config using a JSON Path or JSON Pointer."""
        if not path and not pointer:
            raise ValueError("No path or pointer provided")
        if path:
            return jsonpath.findall(path, self.raw)
        if pointer:
            return jsonpath.pointer.resolve(pointer, self.raw)


class KubeConfigSet(KubeConfigMixin):
    def __init__(self, *paths_or_dicts: Union[PathType, Dict]):
        self._configs = []
        for path_or_dict in paths_or_dicts:
            try:
                self._configs.append(KubeConfig(path_or_dict))
            except ValueError:
                pass
        if not self._configs:
            raise ValueError("No valid kubeconfig provided")

    def __await__(self):
        async def f():
            for config in self._configs:
                await config
            return self

        return f().__await__()

    async def save(self):
        for config in self._configs:
            await config.save()

    @property
    def path(self) -> PathType:
        return self.get_path()

    def get_path(self, context: Optional[str] = None) -> PathType:
        """Return the path of the config for the current context.

        Args:
            context (str): Override the context to use. If not provided, the current context is used.
        """
        if not context:
            context = self.current_context
        if context:
            for config in self._configs:
                if context in [c["name"] for c in config.contexts]:
                    return config.path
        return self._configs[0].path

    @property
    def raw(self) -> Dict:
        """Merge all kubeconfig data into a single kubeconfig."""
        data = {
            "apiVersion": "v1",
            "kind": "Config",
            "preferences": self.preferences,
            "clusters": self.clusters,
            "users": self.users,
            "contexts": self.contexts,
            "current-context": self.current_context,
        }
        if self.extensions:
            data["extensions"] = self.extensions
        return data

    @property
    def current_context(self) -> str:
        """Return the current context from the first kubeconfig.

        Context configuration from multiples files are ignored.
        """
        return self._configs[0].current_context

    @property
    def current_namespace(self) -> str:
        """Return the current namespace from the current context."""
        return self.get_context(self.current_context).get("namespace", "default")

    async def use_namespace(self, namespace: str) -> None:
        for config in self._configs:
            for context in config._raw["contexts"]:
                if context["name"] == self.current_context:
                    context["context"]["namespace"] = namespace
            await config.save()

    async def use_context(self, context: str) -> None:
        """Set the current context."""
        if context not in [c["name"] for c in self.contexts]:
            raise ValueError(f"Context {context} not found")
        await self._configs[0].use_context(context, allow_unknown=True)

    async def rename_context(self, old: str, new: str) -> None:
        """Rename a context."""
        for config in self._configs:
            if old in [c["name"] for c in config.contexts]:
                await config.rename_context(old, new)
                if self.current_context == old:
                    await self.use_context(new)
                return
        raise ValueError(f"Context {old} not found")

    def get_context(self, context_name: str) -> Dict:
        """Get a context by name."""
        for context in self.contexts:
            if context["name"] == context_name:
                return context["context"]
        raise ValueError(f"Context {context_name} not found")

    def get_cluster(self, cluster_name: str) -> Dict:
        """Get a cluster by name."""
        for cluster in self.clusters:
            if cluster["name"] == cluster_name:
                return cluster["cluster"]
        raise ValueError(f"Cluster {cluster_name} not found")

    def get_user(self, user_name: str) -> Dict:
        """Get a user by name."""
        for user in self.users:
            if user["name"] == user_name:
                return user["user"]
        raise ValueError(f"User {user_name} not found")

    async def set(self, pointer: str, value) -> None:
        """Replace a value using a JSON Pointer.

        Set only applies to the first kubeconfig.
        """
        await self._configs[0].set(pointer=pointer, value=value)
        await anyio.sleep(0)

    async def unset(self, pointer: str) -> None:
        """Remove a value using a JSON Pointer.

        Unset applies to all kubeconfigs.
        """
        for config in self._configs:
            try:
                await config.unset(pointer=pointer)
            except Exception:
                pass

    @property
    def preferences(self) -> List[Dict]:
        return self._configs[0].preferences

    @property
    def clusters(self) -> List[Dict]:
        clusters = []
        for config in self._configs:
            if config.clusters:
                clusters.extend(config.clusters)
        # Unpack and repack to remove duplicates
        unpacked = list_dict_unpack(clusters, "name", "cluster")
        repacked = dict_list_pack(unpacked, "name", "cluster")
        return repacked

    @property
    def users(self) -> List[Dict]:
        users = []
        for config in self._configs:
            if config.users:
                users.extend(config.users)
        # Unpack and repack to remove duplicates
        unpacked = list_dict_unpack(users, "name", "user")
        repacked = dict_list_pack(unpacked, "name", "user")
        return repacked

    @property
    def contexts(self) -> List[Dict]:
        contexts = []
        for config in self._configs:
            if config.contexts:
                contexts.extend(config.contexts)
        # Unpack and repack to remove duplicates
        unpacked = list_dict_unpack(contexts, "name", "context")
        repacked = dict_list_pack(unpacked, "name", "context")
        return repacked

    @property
    def extensions(self) -> List[Dict]:
        extensions = []
        for config in self._configs:
            if config.extensions:
                extensions.extend(config.extensions)
        return extensions


class KubeConfig(KubeConfigMixin):
    def __init__(self, path_or_config: Union[PathType, Dict]):
        self.path: PathType
        self._raw: dict = {}

        if not path_or_config:
            raise ValueError("KubeConfig path_or_config is None or empty string.")
        if isinstance(path_or_config, str) or isinstance(path_or_config, pathlib.Path):
            self.path = pathlib.Path(path_or_config).expanduser()
            if not self.path.exists():
                raise ValueError(f"File {self.path} does not exist")
            if self.path.is_dir():
                raise IsADirectoryError(
                    f'Error loading config file "{self.path}": is a directory.'
                )
        elif isinstance(path_or_config, dict):
            self._raw = path_or_config
        else:
            raise TypeError("KubeConfig path_or_config must be a string, path or dict.")

        self.__write_lock = anyio.Lock()

    def __await__(self):
        async def f():
            if not self._raw:
                async with await anyio.open_file(self.path) as fh:
                    self._raw = yaml.safe_load(await fh.read())
            return self

        return f().__await__()

    async def save(self, path=None) -> None:
        path = self.path if not path else path
        if not path:
            raise ValueError("No path provided")
        async with self.__write_lock:
            async with await anyio.open_file(path, "w") as fh:
                await fh.write(yaml.safe_dump(self._raw))

    @property
    def current_context(self) -> str:
        return self._raw["current-context"]

    @property
    def current_namespace(self) -> str:
        return self.get_context(self.current_context).get("namespace", "default")

    async def use_namespace(self, namespace: str) -> None:
        for context in self._raw["contexts"]:
            if context["name"] == self.current_context:
                context["context"]["namespace"] = namespace
        await self.save()

    async def use_context(self, context: str, allow_unknown: bool = False) -> None:
        """Set the current context."""
        if not allow_unknown and context not in [c["name"] for c in self.contexts]:
            raise ValueError(f"Context {context} not found")
        self._raw["current-context"] = context
        await self.save()

    async def rename_context(self, old: str, new: str) -> None:
        """Rename a context."""
        for context in self._raw["contexts"]:
            if context["name"] == old:
                context["name"] = new
                if self.current_context == old:
                    await self.use_context(new)
                await self.save()
                return
        raise ValueError(f"Context {old} not found")

    def get_context(self, context_name: str) -> Dict:
        """Get a context by name."""
        for context in self.contexts:
            if context["name"] == context_name:
                return context["context"]
        raise ValueError(f"Context {context_name} not found")

    def get_cluster(self, cluster_name: str) -> Dict:
        """Get a cluster by name."""
        for cluster in self.clusters:
            if cluster["name"] == cluster_name:
                return cluster["cluster"]
        raise ValueError(f"Cluster {cluster_name} not found")

    def get_user(self, user_name: str) -> Dict:
        """Get a user by name."""
        for user in self.users:
            if user["name"] == user_name:
                return user["user"]
        raise ValueError(f"User {user_name} not found")

    async def set(
        self, pointer: str, value: Optional[Any] = None, strict: bool = False
    ) -> None:
        """Replace a value using a JSON Pointer."""
        if strict:
            patch = jsonpath.JSONPatch().replace(pointer, value)
        else:
            patch = jsonpath.JSONPatch().add(pointer, value)
        self._raw = typing.cast(dict, patch.apply(self._raw))
        await self.save()

    async def unset(self, pointer: str) -> Any:
        """Remove a value using a JSON Pointer."""
        patch = jsonpath.JSONPatch().remove(pointer)
        self._raw = typing.cast(dict, patch.apply(self._raw))
        await self.save()

    @property
    def raw(self) -> Dict:
        return self._raw

    @property
    def preferences(self) -> List[Dict]:
        return self._raw["preferences"]

    @property
    def clusters(self) -> List[Dict]:
        return self._raw["clusters"]

    @property
    def users(self) -> List[Dict]:
        return self._raw["users"]

    @property
    def contexts(self) -> List[Dict]:
        return self._raw["contexts"]

    @property
    def extensions(self) -> List[Dict]:
        return self._raw["extensions"] if "extensions" in self._raw else []
