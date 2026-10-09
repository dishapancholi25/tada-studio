"""Databricks OAuth Machine-to-Machine handler for service principal authentication.

Implements the OAuth2 client_credentials grant flow for Databricks service principals.
Token endpoint: https://<workspace>/oidc/v1/token
"""

import base64
import logging
import time
from typing import Dict, Optional, Tuple

import httpx

from backend.services.guardrails.ssrf import validate_url

logger = logging.getLogger(__name__)
LOG_PREFIX = "[DATABRICKS-OAUTH]"

# Module-level cache: (workspace_hostname, client_id) -> (access_token, expires_at_timestamp)
_token_cache: Dict[Tuple[str, str], Tuple[str, float]] = {}

# Refresh buffer: fetch a new token 5 minutes before expiry
_REFRESH_BUFFER_SECONDS = 300

# Constant OIDC token endpoint path (used with base_url to avoid full-URL SSRF taint)
_OIDC_TOKEN_PATH = "/oidc/v1/token"

# Known Databricks workspace domain suffixes (SSRF allowlist)
_ALLOWED_DATABRICKS_DOMAINS = (
    ".azuredatabricks.net",
    ".cloud.databricks.com",
    ".gcp.databricks.com",
    ".databricks.com",
)


def _validate_databricks_hostname(hostname: str) -> None:
    """Validate that the hostname is a known Databricks domain and passes SSRF checks.

    Raises:
        ValueError: If hostname is not on the Databricks domain allowlist or fails SSRF checks.
    """
    hostname_lower = hostname.lower()
    if not any(
        hostname_lower.endswith(domain) for domain in _ALLOWED_DATABRICKS_DOMAINS
    ):
        raise ValueError(
            f"Databricks workspace hostname '{hostname}' is not on the allowed domain list. "
            f"Expected a hostname ending with one of: {', '.join(_ALLOWED_DATABRICKS_DOMAINS)}"
        )

    # Additional SSRF protection: validate against blocked IP ranges
    url = f"https://{hostname}/oidc/v1/token"
    ssrf_result = validate_url(url)
    if not ssrf_result.passed:
        violation_msg = (
            ssrf_result.violations[0].message
            if ssrf_result.violations
            else "URL validation failed"
        )
        raise ValueError(
            f"Databricks workspace hostname rejected by SSRF policy: {violation_msg}"
        )


class DatabricksM2MHandler:
    """Handles OAuth2 client_credentials flow for Databricks service principals.

    Unlike the MCP OAuth handler (which uses RFC 9728 discovery and PKCE),
    this handler calls the Databricks OIDC token endpoint directly with
    client_id and client_secret to obtain a short-lived access token.
    """

    def __init__(
        self,
        workspace_hostname: str,
        client_id: str,
        client_secret: str,
    ):
        """Initialize the Databricks M2M handler.

        Args:
            workspace_hostname: Databricks workspace hostname
                (e.g., adb-123.3.azuredatabricks.net).
            client_id: Service principal client ID.
            client_secret: Service principal client secret.
        """
        hostname = workspace_hostname.strip()
        if hostname.startswith("https://"):
            hostname = hostname[8:]
        elif hostname.startswith("http://"):
            hostname = hostname[7:]
        # Strip any URL path — we only need the hostname for the OIDC endpoint
        hostname = hostname.split("/")[0]
        hostname = hostname.rstrip("/")

        # SSRF protection: validate hostname against Databricks domain allowlist
        _validate_databricks_hostname(hostname)

        self.workspace_hostname = hostname
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = f"https://{hostname}/oidc/v1/token"
        self._cache_key = (hostname, client_id)

    async def get_valid_token(self) -> str:
        """Get a valid access token, fetching a new one if needed.

        Returns cached token if still valid, otherwise requests a new one
        from the Databricks OIDC token endpoint.

        Returns:
            Valid access token string.

        Raises:
            ValueError: If token request fails.
        """
        cached = _token_cache.get(self._cache_key)
        if cached:
            token, expires_at = cached
            if time.time() < (expires_at - _REFRESH_BUFFER_SECONDS):
                logger.debug(
                    "%s Using cached token for workspace=%s (expires in %ds)",
                    LOG_PREFIX,
                    self.workspace_hostname,
                    int(expires_at - time.time()),
                )
                return token

        logger.info(
            "%s Requesting new token from %s",
            LOG_PREFIX,
            self.token_url,
        )

        return await self._fetch_token()

    async def _fetch_token(self) -> str:
        """Fetch a new access token from the Databricks OIDC endpoint.

        Tries form-body credentials first, then falls back to HTTP Basic Auth
        if the server responds with 401. Per RFC 6749 Section 2.3.1, some
        OAuth2 servers require Basic Auth for client_credentials grants.

        Returns:
            Access token string.

        Raises:
            ValueError: If the token request fails with both methods.
        """
        async with httpx.AsyncClient(
            base_url=f"https://{self.workspace_hostname}", timeout=30
        ) as client:
            # Attempt 1: Form-body credentials (most common for Databricks)
            try:
                response = await client.post(
                    _OIDC_TOKEN_PATH,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "all-apis",
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code != 401:
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
                        f"Databricks OAuth token request failed (HTTP {e.response.status_code}): {error_detail}"
                    ) from e

                # Attempt 2: HTTP Basic Auth fallback (RFC 6749 Section 2.3.1)
                logger.warning(
                    "%s Form-body auth returned 401, retrying with HTTP Basic Auth for %s",
                    LOG_PREFIX,
                    self.token_url,
                )
                credentials = base64.b64encode(
                    f"{self.client_id}:{self.client_secret}".encode()
                ).decode()
                try:
                    response = await client.post(
                        _OIDC_TOKEN_PATH,
                        data={
                            "grant_type": "client_credentials",
                            "scope": "all-apis",
                        },
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Authorization": f"Basic {credentials}",
                        },
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as basic_err:
                    error_detail = ""
                    try:
                        error_detail = basic_err.response.text
                    except Exception:
                        pass
                    logger.error(
                        "%s Token request failed with both form-body and Basic Auth: HTTP %s - %s",
                        LOG_PREFIX,
                        basic_err.response.status_code,
                        error_detail,
                    )
                    raise ValueError(
                        f"Databricks OAuth token request failed with both auth methods. "
                        f"Last error (HTTP {basic_err.response.status_code}): {error_detail}"
                    ) from basic_err
            except httpx.RequestError as e:
                logger.error(
                    "%s Token request connection error: %s",
                    LOG_PREFIX,
                    e,
                )
                raise ValueError(
                    f"Failed to connect to Databricks token endpoint: {e}"
                ) from e

        token_data = response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Databricks token response missing access_token")

        expires_in = token_data.get("expires_in", 3600)
        expires_at = time.time() + expires_in

        # Cache the token
        _token_cache[self._cache_key] = (access_token, expires_at)

        logger.info(
            "%s Token obtained for workspace=%s (expires in %ds)",
            LOG_PREFIX,
            self.workspace_hostname,
            expires_in,
        )

        return access_token


def clear_cached_tokens(workspace_hostname: Optional[str] = None) -> None:
    """Clear cached tokens, optionally filtered by workspace.

    Args:
        workspace_hostname: If provided, only clear tokens for this workspace.
            If None, clears all cached tokens.
    """
    if workspace_hostname is None:
        _token_cache.clear()
        logger.info("%s Cleared all cached tokens", LOG_PREFIX)
    else:
        hostname = workspace_hostname.strip().rstrip("/")
        if hostname.startswith("https://"):
            hostname = hostname[8:]
        elif hostname.startswith("http://"):
            hostname = hostname[7:]

        keys_to_remove = [k for k in _token_cache if k[0] == hostname]
        for key in keys_to_remove:
            del _token_cache[key]
        logger.info(
            "%s Cleared %d cached token(s) for workspace=%s",
            LOG_PREFIX,
            len(keys_to_remove),
            hostname,
        )
