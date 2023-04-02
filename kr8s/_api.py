import ssl

import aiohttp
import asyncio_atexit

from ._auth import KubeAuth


class Kr8sApi:
    """A kr8s object for interacting with the Kubernetes API"""

    def __init__(self, url=None, kubeconfig=None, serviceaccount=None) -> None:
        self._url = url
        self._kubeconfig = kubeconfig
        self._serviceaccount = serviceaccount
        self._sslcontext = None
        self._session = None
        self.auth = None

    async def _create_session(self):
        from . import __version__

        self.auth = KubeAuth(
            url=self._url,
            kubeconfig=self._kubeconfig,
            serviceaccount=self._serviceaccount,
        )

        self._sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        headers = {"User-Agent": f"kr8s/{__version__}"}
        if self.auth.client_key_file:
            self._sslcontext.load_cert_chain(
                certfile=self.auth.client_cert_file,
                keyfile=self.auth.client_key_file,
                password=None,
            )

        if self.auth.server_ca_file:
            self._sslcontext.load_verify_locations(cafile=self.auth.server_ca_file)
        if self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        userauth = None
        if self.auth.username and self.auth.password:
            userauth = aiohttp.BasicAuth(self.auth.username, self.auth.password)
        if self._session:
            asyncio_atexit.unregister(self._session.close)
            await self._session.close()
            self._session = None
        self._session = aiohttp.ClientSession(
            base_url=self.auth.server,
            headers=headers,
            auth=userauth,
        )
        asyncio_atexit.register(self._session.close)

    async def get_version(self) -> dict:
        """Get the Kubernetes version"""
        return await self.call_api(method="GET", base="/version")

    async def call_api(self, method, version: str = "", base: str = "") -> dict:
        """Make a Kubernetes API request."""
        if not self._session:
            await self._create_session()
        async with self._session.request(
            method=method, url=f"{base}", ssl=self._sslcontext
        ) as response:
            # TODO catch self.auth error and reauth a couple of times before giving up
            return await response.json()
