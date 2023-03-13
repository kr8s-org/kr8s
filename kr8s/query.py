"""An asyncio shim for pykube-ng."""
from pykube.query import now, Table, Query as _Query, WatchQuery as _WatchQuery
from dask_kubernetes.aiopykube.mixins import AsyncMixin


class Query(_Query, AsyncMixin):
    async def execute(self, **kwargs):
        return await self._sync(super().execute, **kwargs)

    async def iterator(self):
        response = await self.execute()
        for obj in response.json().get("items") or []:
            yield self.api_obj_class(self.api, obj)

    def __aiter__(self):
        return self.iterator()

    async def get_by_name(self, name: str):
        return await self._sync(super().get_by_name, name=name)

    async def get(self, *args, **kwargs):
        return await self._sync(super().get, *args, **kwargs)

    async def get_or_none(self, *args, **kwargs):
        return await self._sync(super().get_or_none, *args, **kwargs)

    async def as_table(self) -> Table:
        response = await self.execute(
            headers={"Accept": "application/json;as=Table;v=v1beta1;g=meta.k8s.io"}
        )
        return Table(self.api_obj_class, response.json())

    def watch(self, since=None, *, params=None):
        query = self._clone(WatchQuery)
        query.params = params
        if since is now:
            raise ValueError("now is not a supported since value in async version")
        elif since is not None:
            query.resource_version = since
        return query

    @property
    def query_cache(self):
        raise NotImplementedError(
            "Properties cannot make async HTTP requests to populate the cache. "
            "Also the shim currently does not implement a cache at all."
        )

    @property
    def response(self):
        raise NotImplementedError(
            "Properties cannot make HTTP requests. Use ``response = (await Query.execute()).json()`` instead."
        )

    def __len__(self):
        raise TypeError(
            "Cannot call len directly on async objects. "
            "Instead you can use ``len([_ async for _ in Query(...)])``."
        )


class WatchQuery(_WatchQuery, AsyncMixin):
    async def object_stream(self):
        f = super().object_stream
        object_stream = await self._sync(lambda: iter(f()))
        while True:
            try:
                yield await self._sync(next, object_stream)
            except StopIteration:
                break

    def __aiter__(self):
        return self.object_stream()
