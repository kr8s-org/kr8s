# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
from typing import Dict, List

import anyio
import yaml

# TODO Implement set
# TODO Implement unset
# TODO Implement set cluster
# TODO Implement delete cluster
# TODO Implement set context
# TODO Implement delete context
# TODO Implement set user
# TODO Implement delete user


class KubeConfigSet(object):
    def __init__(self, *paths):
        self._configs = [KubeConfig(path) for path in paths]

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

    @property
    def preferences(self) -> Dict:
        return self._configs[0].preferences

    @property
    def clusters(self) -> List[Dict]:
        return [cluster for config in self._configs for cluster in config.clusters]

    @property
    def users(self) -> List[Dict]:
        return [user for config in self._configs for user in config.users]

    @property
    def contexts(self) -> List[Dict]:
        return [context for config in self._configs for context in config.contexts]

    @property
    def extensions(self) -> List[Dict]:
        return [
            extension for config in self._configs for extension in config.extensions
        ]


class KubeConfig(object):
    def __init__(self, path):
        self.path = path
        self._raw = None
        self.__write_lock = anyio.Lock()

    def __await__(self):
        async def f():
            async with await anyio.open_file(self.path) as fh:
                self._raw = yaml.safe_load(await fh.read())
            return self

        return f().__await__()

    async def save(self) -> None:
        async with self.__write_lock:
            async with await anyio.open_file(self.path, "w") as fh:
                await fh.write(yaml.safe_dump(self._raw))

    @property
    def current_context(self) -> str:
        return self._raw["current-context"]

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
        return self._raw["extensions"]
