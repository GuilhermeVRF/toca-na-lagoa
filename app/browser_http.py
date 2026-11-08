"""HTTP transport that makes requests look like they come from a real Chrome.

The listing sites sit behind Cloudflare, which rejects requests from
datacenter IPs whose TLS/HTTP2 fingerprint is not a browser's (as httpx's is
not). curl_cffi reproduces Chrome's fingerprint, and plugging it in as an
httpx transport keeps the sources and their respx-based tests unchanged.
"""

import httpx
from curl_cffi import CurlError
from curl_cffi.requests import AsyncSession

IMPERSONATE = "chrome"
# The impersonated browser sends its own User-Agent; a different one would contradict its fingerprint.
DROPPED_HEADERS = {"user-agent", "host", "content-length", "accept-encoding", "connection"}


class BrowserTransport(httpx.AsyncBaseTransport):
    """Sends httpx requests through curl_cffi impersonating Chrome."""

    def __init__(self, timeout: float) -> None:
        """Open a curl_cffi session that times requests out after ``timeout`` seconds."""
        self._session = AsyncSession(impersonate=IMPERSONATE, timeout=timeout)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Perform ``request`` and wrap curl_cffi's answer in an httpx response."""
        headers = {name: value for name, value in request.headers.items() if name.lower() not in DROPPED_HEADERS}
        try:
            response = await self._session.request(
                request.method,
                str(request.url),
                headers=headers,
                data=await request.aread() or None,
                allow_redirects=False,
            )
        except CurlError as error:
            raise httpx.TransportError(str(error), request=request) from error
        return httpx.Response(
            response.status_code,
            headers=[(name, value) for name, value in response.headers.multi_items() if name.lower() not in {"content-encoding", "content-length"}],
            content=response.content,
            request=request,
        )

    async def aclose(self) -> None:
        """Close the underlying curl_cffi session."""
        await self._session.close()


def browser_client(timeout: float) -> httpx.AsyncClient:
    """An httpx client whose requests are sent with Chrome's fingerprint."""
    return httpx.AsyncClient(transport=BrowserTransport(timeout), timeout=timeout, follow_redirects=True)
