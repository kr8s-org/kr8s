import aiohttp
import tempfile
import ssl


from ._auth import KubeAuth


class Kr8sApi:
    """A kr8s object for interacting with the Kubernetes API"""

    def __init__(self, url=None, kubeconfig=None, serviceaccount=None) -> None:
        from . import __version__

        self.auth = KubeAuth(
            url=url, kubeconfig=kubeconfig, serviceaccount=serviceaccount
        )
        self.sslcontext = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        headers = {"User-Agent": f"kr8s/{__version__}"}
        if self.auth.client_key_file:
            self.sslcontext.load_cert_chain(
                certfile=self.auth.client_cert_file,
                keyfile=self.auth.client_key_file,
                password=None,
            )

        if self.auth.server_ca_file:
            self.sslcontext.load_verify_locations(cafile=self.auth.server_ca_file)
        if self.auth.token:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        userauth = None
        if self.auth.username and self.auth.password:
            userauth = aiohttp.BasicAuth(self.auth.username, self.auth.password)
        self.session = aiohttp.ClientSession(
            base_url=self.auth.server,
            headers=headers,
            auth=userauth,
        )

    async def get_version(self) -> dict:
        """Get the Kubernetes version"""
        return await self.call_api(method="GET", base="/version")

    async def call_api(self, method, version: str = "", base: str = "") -> dict:
        """Make a Kubernetes API request."""
        async with self.session.request(
            method=method, url=f"{base}", ssl=self.sslcontext
        ) as response:
            return await response.json()
