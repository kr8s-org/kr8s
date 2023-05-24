from asyncio import Lock

LOCK = Lock()


async def api(
    url=None, kubeconfig=None, serviceaccount=None, namespace=None, _asyncio=True
):
    """Create a :class:`kr8s.Api` object for interacting with the Kubernetes API.

    If a kr8s object already exists with the same arguments, it will be returned.
    """

    from kr8s import Api as _SyncApi
    from kr8s._api import Api as _AsyncApi

    if _asyncio:
        _cls = _AsyncApi
    else:
        _cls = _SyncApi

    async def _f(**kwargs):
        key = frozenset(kwargs.items())
        if key in _cls._instances:
            return _cls._instances[key]
        if all(k is None for k in kwargs.values()) and list(_cls._instances.values()):
            return list(_cls._instances.values())[0]
        return await _cls(**kwargs, bypass_factory=True)

    async with LOCK:
        return await _f(
            url=url,
            kubeconfig=kubeconfig,
            serviceaccount=serviceaccount,
            namespace=namespace,
        )