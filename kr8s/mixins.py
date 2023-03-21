import asyncio
import functools

from pykube.mixins import ScalableMixin as _ScalableMixin


class AsyncMixin:
    async def _sync(self, func, *args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            None, functools.partial(func, *args, **kwargs)
        )


class AsyncScalableMixin(_ScalableMixin):
    async def scale(self, replicas=None):
        count = self.scalable if replicas is None else replicas
        await self.exists(ensure=True)
        if self.scalable != count:
            self.scalable = count
            await self.update()
            while True:
                await self.reload()
                if self.scalable == count:
                    break
                await asyncio.sleep(1)
