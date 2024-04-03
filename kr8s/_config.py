# SPDX-FileCopyrightText: Copyright (c) 2024, Kr8s Developers (See LICENSE for list)
# SPDX-License-Identifier: BSD 3-Clause License
import anyio
import yaml

# TODO Implement raw
# TODO Implement set
# TODO Implement unset
# TODO Implement set cluster
# TODO Implement delete cluster
# TODO Implement set context
# TODO Implement rename context
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
    def raw(self):
        raise NotImplementedError("raw not implemented")

    @property
    def current_context(self):
        """Return the current context from the first kubeconfig.

        Context configuration from multiples files are ignored.
        """
        return self._configs[0].current_context

    async def use_context(self, context: str):
        """Set the current context."""
        await self._configs[0].use_context(context)

    @property
    def preferences(self):
        raise NotImplementedError("preferences not implemented")

    @property
    def clusters(self):
        return [cluster for config in self._configs for cluster in config.clusters]

    @property
    def users(self):
        return [user for config in self._configs for user in config.users]

    @property
    def contexts(self):
        return [context for config in self._configs for context in config.contexts]


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

    async def save(self):
        async with self.__write_lock:
            async with await anyio.open_file(self.path, "w") as fh:
                await fh.write(yaml.safe_dump(self._raw))

    @property
    def current_context(self):
        return self._raw["current-context"]

    async def use_context(self, context: str):
        """Set the current context."""
        self._raw["current-context"] = context
        await self.save()

    @property
    def raw(self):
        return self._raw

    @property
    def preferences(self):
        return self._raw["preferences"]

    @property
    def clusters(self):
        return self._raw["clusters"]

    @property
    def users(self):
        return self._raw["users"]

    @property
    def contexts(self):
        return self._raw["contexts"]
