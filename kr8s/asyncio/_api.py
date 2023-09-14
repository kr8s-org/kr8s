# SPDX-FileCopyrightText: Copyright (c) 2023, Dask Developers, NVIDIA
# SPDX-License-Identifier: BSD 3-Clause License
import threading

from kr8s._api import Api as _AsyncApi


async def api(
    url: str = None,
    kubeconfig: str = None,
    serviceaccount: str = None,
    namespace: str = None,
    context: str = None,
    _asyncio: bool = True,
) -> _AsyncApi:
    """Create a :class:`kr8s.Api` object for interacting with the Kubernetes API.

    If a kr8s object already exists with the same arguments in this thread, it will be returned.
    """

    from kr8s import Api as _SyncApi

    if _asyncio:
        _cls = _AsyncApi
    else:
        _cls = _SyncApi

    async def _f(**kwargs):
        key = frozenset(kwargs.items())
        thread_id = threading.get_ident()
        if (
            _cls._instances
            and thread_id in _cls._instances
            and key in _cls._instances[thread_id]
        ):
            return await _cls._instances[thread_id][key]
        if (
            all(k is None for k in kwargs.values())
            and thread_id in _cls._instances
            and list(_cls._instances[thread_id].values())
        ):
            return await list(_cls._instances[thread_id].values())[0]
        return await _cls(**kwargs, bypass_factory=True)

    return await _f(
        url=url,
        kubeconfig=kubeconfig,
        serviceaccount=serviceaccount,
        namespace=namespace,
        context=context,
    )
