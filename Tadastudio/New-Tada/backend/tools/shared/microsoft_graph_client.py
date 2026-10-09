"""Microsoft Graph API client with OAuth2 token management.

Supports two authentication modes:
1. Delegated (OAuth) — pre-obtained user token passed via access_token param
2. Client credentials — app-level token fetched from Azure AD (fallback)
"""

import asyncio
import base64
import json
import logging
import random
import time
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)
LOG_PREFIX = "[MS-GRAPH]"

# Module-level cache: (tenant_id, client_id) -> (access_token, expires_at_timestamp)
_token_cache: Dict[Tuple[str, str], Tuple[str, float]] = {}
# Module-level lock: prevents concurrent token fetches across all instances with the same cache key
_token_lock = asyncio.Lock()

# Refresh buffer: fetch a new token 5 minutes before expiry
_REFRESH_BUFFER_SECONDS = 300

# Retry configuration
_MAX_RETRIES = 3
_RETRYABLE_STATUS_CODES = {429, 503, 504}
_BASE_BACKOFF_SECONDS = 1.0

# HTTP client configuration
_DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
_CONTENT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
_DEFAULT_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)

# Pagination safety limit
_MAX_PAGES = 10


class GraphAPIError(Exception):
    """Structured error from Microsoft Graph API."""

    def __init__(
        self, status_code: int, error_code: str, message: str, request_id: str = ""
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.request_id = request_id
        super().__init__(f"[{status_code}] {error_code}: {message}")


def _parse_error_response(response: httpx.Response) -> GraphAPIError:
    """Parse a Microsoft Graph API error response into a structured error."""
    try:
        body = response.json()
        error = body.get("error", {})
        return GraphAPIError(
            status_code=response.status_code,
            error_code=error.get("code", "UnknownError"),
            message=error.get("message", response.text),
            request_id=response.headers.get("request-id", ""),
        )
    except Exception:
        return GraphAPIError(
            status_code=response.status_code,
            error_code="UnknownError",
            message=response.text or f"HTTP {response.status_code}",
        )


def _check_delegated_token_expiry(token: str) -> None:
    """Raise ValueError if the delegated JWT token has expired.

    Decodes the JWT payload (no signature verification — we trust the token
    was issued by Microsoft) to extract the 'exp' claim and give callers a
    clear error rather than a silent 401 from the Graph API.
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return  # Not a standard JWT; skip expiry check
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8"))
        exp = payload.get("exp")
        if exp and time.time() > float(exp):
            raise ValueError(
                "Microsoft OAuth token has expired — please re-authenticate to continue."
            )
    except ValueError:
        raise
    except Exception:
        pass  # Can't decode JWT; let the Graph API return a 401 if truly expired


class MicrosoftGraphClient:
    """Microsoft Graph API client.

    Provides authenticated access to Microsoft Graph REST API resources
    (SharePoint, OneDrive, etc.). Supports delegated (user) tokens
    and client_credentials (app) tokens.
    """

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        tenant_id: str = "",
        client_id: str = "",
        client_secret: str = "",
        access_token: Optional[str] = None,
    ):
        self.tenant_id = tenant_id.strip() if tenant_id else ""
        self.client_id = client_id.strip() if client_id else ""
        self.client_secret = client_secret.strip() if client_secret else ""
        self.token_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            if self.tenant_id
            else ""
        )
        self._cache_key = (
            (self.tenant_id, self.client_id)
            if self.tenant_id and self.client_id
            else None
        )
        # Pre-obtained delegated token (from OAuth flow)
        self._delegated_token = access_token
        # Lazy-initialized HTTP clients (connection pooling)
        self._client: Optional[httpx.AsyncClient] = None
        self._content_client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """Return the shared HTTP client, creating it on first use."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=_DEFAULT_TIMEOUT, limits=_DEFAULT_LIMITS
            )
        return self._client

    def _get_content_client(self) -> httpx.AsyncClient:
        """Return the shared content-download HTTP client (longer timeout, follows redirects)."""
        if self._content_client is None or self._content_client.is_closed:
            self._content_client = httpx.AsyncClient(
                timeout=_CONTENT_TIMEOUT, limits=_DEFAULT_LIMITS, follow_redirects=True
            )
        return self._content_client

    async def close(self) -> None:
        """Close underlying HTTP clients. Call on shutdown."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._content_client and not self._content_client.is_closed:
            await self._content_client.aclose()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        *,
        use_content_client: bool = False,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic for transient errors.

        Retries on HTTP 429, 503, 504 with exponential backoff + jitter.
        Respects Retry-After header on 429 responses.
        """
        client = (
            self._get_content_client() if use_content_client else self._get_client()
        )
        last_exception: Optional[Exception] = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await client.request(method, url, **kwargs)

                if response.status_code not in _RETRYABLE_STATUS_CODES:
                    return response

                # Retryable status — return on last attempt
                if attempt == _MAX_RETRIES:
                    return response

                # Calculate wait time
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = (
                        float(retry_after)
                        if retry_after
                        else _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                    )
                else:
                    wait = _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))

                jitter = random.uniform(0, wait * 0.25)
                total_wait = wait + jitter

                logger.warning(
                    "%s HTTP %d on attempt %d/%d, retrying in %.1fs",
                    LOG_PREFIX,
                    response.status_code,
                    attempt,
                    _MAX_RETRIES,
                    total_wait,
                )
                await asyncio.sleep(total_wait)

            except httpx.RequestError as e:
                last_exception = e
                if attempt == _MAX_RETRIES:
                    raise
                wait = _BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                jitter = random.uniform(0, wait * 0.25)
                logger.warning(
                    "%s Connection error on attempt %d/%d: %s, retrying in %.1fs",
                    LOG_PREFIX,
                    attempt,
                    _MAX_RETRIES,
                    e,
                    wait + jitter,
                )
                await asyncio.sleep(wait + jitter)

        raise last_exception or RuntimeError("Retry loop exited unexpectedly")

    async def get_valid_token(self) -> str:
        """Get a valid access token.

        If a delegated token was provided, returns it directly.
        Otherwise falls back to client_credentials with caching.
        Uses double-check locking to prevent concurrent token refreshes.
        """
        if self._delegated_token:
            logger.debug("%s Using delegated (user) token", LOG_PREFIX)
            _check_delegated_token_expiry(self._delegated_token)
            return self._delegated_token

        # Fast path: check cache without lock
        cached = _token_cache.get(self._cache_key)
        if cached:
            token, expires_at = cached
            if time.time() < (expires_at - _REFRESH_BUFFER_SECONDS):
                logger.debug(
                    "%s Using cached token for tenant=%s (expires in %ds)",
                    LOG_PREFIX,
                    self.tenant_id,
                    int(expires_at - time.time()),
                )
                return token

        # Slow path: acquire module-level lock and double-check before refreshing
        async with _token_lock:
            cached = _token_cache.get(self._cache_key)
            if cached:
                token, expires_at = cached
                if time.time() < (expires_at - _REFRESH_BUFFER_SECONDS):
                    return token

            logger.info("%s Requesting new token from %s", LOG_PREFIX, self.token_url)
            return await self._fetch_token()

    async def _fetch_token(self) -> str:
        """Fetch a new access token via client_credentials grant."""
        client = self._get_client()
        try:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_detail = e.response.text
            except Exception:
                pass
            logger.error(
                "%s Token request failed: HTTP %s - %s",
                LOG_PREFIX,
                e.response.status_code,
                error_detail,
            )
            raise ValueError(
                f"OAuth token request failed (HTTP {e.response.status_code}): {error_detail}"
            ) from e
        except httpx.RequestError as e:
            logger.error("%s Token request connection error: %s", LOG_PREFIX, e)
            raise ValueError(
                f"Failed to connect to Azure AD token endpoint: {e}"
            ) from e

        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Azure AD token response missing access_token")

        expires_in = token_data.get("expires_in", 3600)
        expires_at = time.time() + expires_in
        _token_cache[self._cache_key] = (access_token, expires_at)

        logger.info(
            "%s Token obtained for tenant=%s (expires in %ds)",
            LOG_PREFIX,
            self.tenant_id,
            expires_in,
        )
        return access_token

    async def graph_get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated GET request to Microsoft Graph API."""
        token = await self.get_valid_token()
        response = await self._request_with_retry(
            "GET",
            f"{self.GRAPH_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        if not response.is_success:
            raise _parse_error_response(response)
        return response.json()

    async def graph_post(self, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated POST request to Microsoft Graph API."""
        token = await self.get_valid_token()
        response = await self._request_with_retry(
            "POST",
            f"{self.GRAPH_BASE_URL}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=json_body,
        )
        if not response.is_success:
            raise _parse_error_response(response)
        return response.json()

    async def graph_patch(
        self,
        path: str,
        json_body: Dict[str, Any],
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make authenticated PATCH request to Microsoft Graph API."""
        token = await self.get_valid_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        response = await self._request_with_retry(
            "PATCH",
            f"{self.GRAPH_BASE_URL}{path}",
            headers=headers,
            json=json_body,
        )
        if not response.is_success:
            raise _parse_error_response(response)
        return response.json()

    async def graph_delete(
        self,
        path: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Make authenticated DELETE request to Microsoft Graph API."""
        token = await self.get_valid_token()
        headers: Dict[str, str] = {"Authorization": f"Bearer {token}"}
        if extra_headers:
            headers.update(extra_headers)
        response = await self._request_with_retry(
            "DELETE",
            f"{self.GRAPH_BASE_URL}{path}",
            headers=headers,
        )
        if not response.is_success:
            raise _parse_error_response(response)

    async def graph_put(
        self, path: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """Make authenticated PUT request with binary content to Microsoft Graph API."""
        token = await self.get_valid_token()
        response = await self._request_with_retry(
            "PUT",
            f"{self.GRAPH_BASE_URL}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": content_type,
            },
            content=content,
            use_content_client=True,
        )
        if not response.is_success:
            raise _parse_error_response(response)
        return response.json()

    async def graph_put_chunk(
        self, url: str, content: bytes, content_range: str
    ) -> Dict[str, Any]:
        """Upload a chunk to an upload session (for large file uploads).

        Note: Upload session URLs are absolute (not relative to GRAPH_BASE_URL).
        """
        response = await self._request_with_retry(
            "PUT",
            url,
            headers={
                "Content-Length": str(len(content)),
                "Content-Range": content_range,
            },
            content=content,
            use_content_client=True,
        )
        if not response.is_success:
            raise _parse_error_response(response)
        return response.json()

    async def graph_get_content(self, path: str) -> bytes:
        """Download binary content from Microsoft Graph API."""
        token = await self.get_valid_token()
        response = await self._request_with_retry(
            "GET",
            f"{self.GRAPH_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            use_content_client=True,
        )
        if not response.is_success:
            raise _parse_error_response(response)
        return response.content

    async def graph_get_all_pages(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        max_pages: int = _MAX_PAGES,
    ) -> Tuple[list, bool]:
        """GET with automatic @odata.nextLink pagination.

        Returns a tuple of (items, truncated) where:
        - items: flat list of all 'value' items across pages
        - truncated: True if max_pages was reached with more results still available
        """
        all_items: list = []
        token = await self.get_valid_token()
        url = f"{self.GRAPH_BASE_URL}{path}"
        headers = {"Authorization": f"Bearer {token}"}
        next_link: Optional[str] = None

        for page in range(max_pages):
            if page == 0:
                response = await self._request_with_retry(
                    "GET", url, headers=headers, params=params
                )
            else:
                # nextLink is an absolute URL with params already embedded
                response = await self._request_with_retry("GET", url, headers=headers)

            if not response.is_success:
                raise _parse_error_response(response)

            data = response.json()
            all_items.extend(data.get("value", []))

            next_link = data.get("@odata.nextLink")
            if not next_link:
                break
            url = next_link
        else:
            # for-else: loop exhausted max_pages without breaking
            if next_link:
                logger.warning(
                    "%s Pagination limit (%d pages) reached for %s — results may be incomplete",
                    LOG_PREFIX,
                    max_pages,
                    path,
                )
                return all_items, True

        return all_items, False


def clear_cached_tokens(tenant_id: Optional[str] = None) -> None:
    """Clear cached tokens, optionally filtered by tenant."""
    if tenant_id is None:
        _token_cache.clear()
        logger.info("%s Cleared all cached tokens", LOG_PREFIX)
    else:
        keys_to_remove = [k for k in _token_cache if k[0] == tenant_id.strip()]
        for key in keys_to_remove:
            del _token_cache[key]
        logger.info(
            "%s Cleared %d cached token(s) for tenant=%s",
            LOG_PREFIX,
            len(keys_to_remove),
            tenant_id,
        )
