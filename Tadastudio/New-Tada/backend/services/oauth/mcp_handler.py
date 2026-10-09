"""Generic MCP OAuth handler implementing the MCP Authorization spec.

This module implements the complete OAuth flow for any MCP server that follows:
- RFC 9728 (Protected Resource Metadata)
- RFC 8414 (OAuth Authorization Server Metadata discovery)
- RFC 7591 (Dynamic Client Registration)
- OAuth2 PKCE (RFC 7636)
- RFC 8707 (Resource Indicators)
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse, urlencode

import httpx
from mcp.shared.auth import OAuthMetadata, ProtectedResourceMetadata

from .storage import OAuthStorageService, oauth_storage

logger = logging.getLogger(__name__)
LOG_PREFIX = "[MCP-OAUTH]"


def _resource_url_from_server_url(url: str) -> str:
    """Convert server URL to canonical resource URL per RFC 8707.

    Removes fragment, lowercases scheme and host.
    """
    parsed = urlparse(url)
    canonical = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    ).geturl()
    return canonical


def _generate_pkce() -> Tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    import base64

    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


class McpOAuthHandler:
    """Handles OAuth flow for any MCP server implementing the MCP Authorization spec.

    Unlike NotionOAuthHandler, this handler discovers endpoints dynamically
    from the MCP server and is instantiated per-request with specific
    server_url and server_name.
    """

    def __init__(
        self,
        server_url: str,
        server_name: str,
        storage: Optional[OAuthStorageService] = None,
        redirect_uri: Optional[str] = None,
    ):
        """Initialize the MCP OAuth handler.

        Args:
            server_url: The MCP server URL to authenticate against.
            server_name: A user-friendly name for this server (used as provider key).
            storage: Storage service for OAuth data (defaults to global instance).
            redirect_uri: OAuth callback URI (defaults to env or localhost).
        """
        self.server_url = server_url
        self.server_name = server_name
        self.provider = f"mcp:{server_name}"
        self.storage = storage or oauth_storage
        self.redirect_uri = redirect_uri or os.getenv(
            "MCP_OAUTH_REDIRECT_URI",
            "http://localhost:8000/api/mcp-oauth/callback",
        )

    async def discover_oauth_metadata(
        self,
    ) -> Tuple[Optional[ProtectedResourceMetadata], OAuthMetadata]:
        """Discover OAuth metadata from the MCP server.

        1. Tries /.well-known/oauth-protected-resource (RFC 9728)
        2. If found, uses authorization_servers[0] for OAuth metadata discovery
        3. If not found (404), falls back to discovering OAuth metadata directly
           from the server URL (treating it as its own authorization server)

        Returns:
            Tuple of (ProtectedResourceMetadata or None, OAuthMetadata).

        Raises:
            httpx.HTTPStatusError: If discovery requests fail.
            ValueError: If metadata is invalid or missing.
        """
        parsed = urlparse(self.server_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        prm: Optional[ProtectedResourceMetadata] = None

        async with httpx.AsyncClient() as client:
            # Step 1: Try Protected Resource Metadata (RFC 9728)
            prm_url = urljoin(base_url, "/.well-known/oauth-protected-resource")
            logger.info(
                "%s Fetching Protected Resource Metadata from %s",
                LOG_PREFIX,
                prm_url,
            )
            try:
                prm_response = await client.get(prm_url, timeout=30.0)
                prm_response.raise_for_status()
                prm = ProtectedResourceMetadata.model_validate(prm_response.json())
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.info(
                        "%s Protected Resource Metadata not found (404), "
                        "falling back to direct OAuth discovery on %s",
                        LOG_PREFIX,
                        base_url,
                    )
                else:
                    raise

            if prm and prm.authorization_servers:
                # Step 2a: Use authorization server from PRM
                auth_server_url = str(prm.authorization_servers[0])
            else:
                # Step 2b: Fall back to the server URL itself
                auth_server_url = base_url

            # Step 3: Discover OAuth metadata using RFC 8414 discovery URLs
            oauth_metadata = await self._discover_oauth_from_auth_server(
                client, auth_server_url
            )

        return prm, oauth_metadata

    async def _discover_oauth_from_auth_server(
        self, client: httpx.AsyncClient, auth_server_url: str
    ) -> OAuthMetadata:
        """Try RFC 8414 discovery URLs in order to find OAuth metadata.

        Follows the same logic as the MCP SDK's _get_discovery_urls().

        Args:
            client: HTTP client to use.
            auth_server_url: The authorization server base URL.

        Returns:
            OAuthMetadata from the first successful discovery URL.

        Raises:
            ValueError: If no discovery URL succeeds.
        """
        parsed = urlparse(auth_server_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        discovery_urls = []

        # RFC 8414: Path-aware OAuth discovery
        if parsed.path and parsed.path != "/":
            oauth_path = (
                f"/.well-known/oauth-authorization-server{parsed.path.rstrip('/')}"
            )
            discovery_urls.append(urljoin(base_url, oauth_path))

        # OAuth root fallback
        discovery_urls.append(
            urljoin(base_url, "/.well-known/oauth-authorization-server")
        )

        # RFC 8414 section 5: Path-aware OIDC discovery
        if parsed.path and parsed.path != "/":
            oidc_path = f"/.well-known/openid-configuration{parsed.path.rstrip('/')}"
            discovery_urls.append(urljoin(base_url, oidc_path))

        # OIDC 1.0 fallback
        oidc_fallback = (
            f"{auth_server_url.rstrip('/')}/.well-known/openid-configuration"
        )
        discovery_urls.append(oidc_fallback)

        last_error = None
        for url in discovery_urls:
            try:
                logger.debug("%s Trying OAuth discovery URL: %s", LOG_PREFIX, url)
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                metadata = OAuthMetadata.model_validate(response.json())
                logger.info("%s OAuth metadata discovered from %s", LOG_PREFIX, url)
                return metadata
            except Exception as e:
                logger.debug("%s Discovery URL %s failed: %s", LOG_PREFIX, url, e)
                last_error = e
                continue

        raise ValueError(
            f"Failed to discover OAuth metadata from auth server {auth_server_url}. "
            f"Tried URLs: {discovery_urls}. Last error: {last_error}"
        )

    async def _register_client(
        self,
        oauth_metadata: OAuthMetadata,
        scope: str,
    ) -> Dict[str, Any]:
        """Dynamically register an OAuth client (RFC 7591).

        Args:
            oauth_metadata: Discovered OAuth metadata.
            scope: Requested scope.

        Returns:
            Registration response dict.

        Raises:
            ValueError: If no registration endpoint found.
            httpx.HTTPStatusError: If registration fails.
        """
        if not oauth_metadata.registration_endpoint:
            raise ValueError(
                "OAuth server does not support dynamic client registration "
                "(no registration_endpoint in metadata)"
            )

        registration_request = {
            "client_name": f"Agentic Studio ({self.server_name})",
            "redirect_uris": [self.redirect_uri],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": scope,
        }

        register_url = str(oauth_metadata.registration_endpoint)
        logger.info("%s Registering OAuth client at %s", LOG_PREFIX, register_url)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                register_url,
                json=registration_request,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()

        registration_data = response.json()
        logger.info(
            "%s Client registered, client_id=%s",
            LOG_PREFIX,
            str(registration_data.get("client_id", ""))[:8] + "...",
        )
        return registration_data

    async def initiate_flow(self, user_id: str) -> Tuple[str, str]:
        """Initiate OAuth flow for a user.

        Steps:
        1. Discover OAuth metadata from the MCP server
        2. Register a new OAuth client dynamically
        3. Generate PKCE verifier/challenge
        4. Store registration with metadata (including code_verifier)
        5. Generate authorization URL with PKCE + resource param

        Args:
            user_id: Unique identifier for the user (email).

        Returns:
            Tuple of (authorization_url, state).
        """
        logger.info(
            "%s Initiating flow for user=%s server=%s",
            LOG_PREFIX,
            user_id,
            self.server_name,
        )

        # Step 1: Discover
        prm, oauth_metadata = await self.discover_oauth_metadata()

        # Determine scope
        scope = "mcp.tools"
        if prm and prm.scopes_supported:
            scope = " ".join(prm.scopes_supported)
        elif oauth_metadata.scopes_supported:
            scope = " ".join(oauth_metadata.scopes_supported)

        # Step 2: Register client
        registration = await self._register_client(oauth_metadata, scope)

        # Step 3: Generate PKCE
        code_verifier, code_challenge = _generate_pkce()

        # Step 4: Store registration with metadata
        resource_url = _resource_url_from_server_url(self.server_url)
        self.storage.store_client_registration(
            user_id=user_id,
            provider=self.provider,
            client_id=registration["client_id"],
            client_secret=registration.get("client_secret"),
            registration_access_token=registration.get("registration_access_token"),
            metadata={
                "oauth_metadata": oauth_metadata.model_dump(mode="json"),
                "prm": prm.model_dump(mode="json") if prm else None,
                "code_verifier": code_verifier,
                "server_url": self.server_url,
                "resource_url": resource_url,
                "redirect_uri": self.redirect_uri,
                "scope": scope,
                "redirect_uris": registration.get("redirect_uris", []),
                "token_endpoint_auth_method": registration.get(
                    "token_endpoint_auth_method", "none"
                ),
                "grant_types": registration.get("grant_types", []),
            },
        )

        # Step 5: Generate state and authorization URL
        state = self.storage.store_state(user_id, self.provider)

        auth_params = {
            "client_id": registration["client_id"],
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "resource": resource_url,
        }

        authorization_url = (
            f"{oauth_metadata.authorization_endpoint}?{urlencode(auth_params)}"
        )

        logger.info(
            "%s Authorization URL generated for user=%s server=%s",
            LOG_PREFIX,
            user_id,
            self.server_name,
        )

        return authorization_url, state

    async def handle_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth callback and exchange code for tokens.

        Args:
            code: Authorization code from callback.
            state: State parameter for CSRF verification.

        Returns:
            Dict with status, user_id, and token info.

        Raises:
            ValueError: If state is invalid or client registration not found.
            httpx.HTTPStatusError: If token exchange fails.
        """
        # Verify state and get user_id
        user_id = self.storage.verify_and_delete_state(state, self.provider)
        if not user_id:
            raise ValueError("Invalid or expired state - possible CSRF attack")

        logger.info(
            "%s Handling callback for user=%s provider=%s",
            LOG_PREFIX,
            user_id,
            self.provider,
        )

        # Get client registration with stored metadata
        client_reg = self.storage.get_client_registration(user_id, self.provider)
        if not client_reg:
            raise ValueError("Client registration not found for user")

        reg_metadata = client_reg.metadata_ or {}
        code_verifier = reg_metadata.get("code_verifier")
        if not code_verifier:
            raise ValueError("PKCE code_verifier not found in registration metadata")

        # Get token endpoint from stored OAuth metadata
        oauth_meta = reg_metadata.get("oauth_metadata", {})
        token_endpoint = oauth_meta.get("token_endpoint")
        if not token_endpoint:
            raise ValueError("Token endpoint not found in stored OAuth metadata")

        resource_url = reg_metadata.get("resource_url", "")

        # Use the redirect_uri that was registered during initiation
        # (must match exactly for the token exchange to succeed)
        callback_redirect_uri = reg_metadata.get("redirect_uri", self.redirect_uri)

        # Exchange code for token with PKCE
        token_request = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": callback_redirect_uri,
            "client_id": client_reg.client_id,
            "code_verifier": code_verifier,
        }
        if resource_url:
            token_request["resource"] = resource_url

        logger.debug(
            "%s Exchanging code for token for provider=%s", LOG_PREFIX, self.provider
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data=token_request,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            response.raise_for_status()

        token_data = response.json()

        # Calculate expiry
        expires_at = None
        if token_data.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])

        # Store tokens
        self.storage.store_token(
            user_id=user_id,
            provider=self.provider,
            client_id=client_reg.client_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=expires_at,
            scope=token_data.get("scope"),
        )

        # Remove code_verifier from stored metadata (no longer needed)
        cleaned_metadata = {
            k: v for k, v in reg_metadata.items() if k != "code_verifier"
        }
        self.storage.store_client_registration(
            user_id=user_id,
            provider=self.provider,
            client_id=client_reg.client_id,
            client_secret=client_reg.client_secret,
            registration_access_token=client_reg.registration_access_token,
            metadata=cleaned_metadata,
        )

        logger.info(
            "%s Token exchange successful for user=%s provider=%s",
            LOG_PREFIX,
            user_id,
            self.provider,
        )

        return {
            "status": "success",
            "user_id": user_id,
            "scope": token_data.get("scope"),
            "expires_in": token_data.get("expires_in"),
        }

    async def refresh_token(self, user_id: str) -> str:
        """Refresh access token using refresh token.

        Args:
            user_id: User identifier.

        Returns:
            New access token.

        Raises:
            ValueError: If token or client registration not found.
            httpx.HTTPStatusError: If refresh fails.
        """
        token = self.storage.get_token(user_id, self.provider)
        if not token or not token.refresh_token:
            raise ValueError("No refresh token found for user")

        client_reg = self.storage.get_client_registration(user_id, self.provider)
        if not client_reg:
            raise ValueError("Client registration not found for user")

        reg_metadata = client_reg.metadata_ or {}
        oauth_meta = reg_metadata.get("oauth_metadata", {})
        token_endpoint = oauth_meta.get("token_endpoint")
        if not token_endpoint:
            raise ValueError("Token endpoint not found in stored OAuth metadata")

        resource_url = reg_metadata.get("resource_url", "")

        logger.info("%s Refreshing token", LOG_PREFIX)

        refresh_request = {
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "client_id": client_reg.client_id,
        }
        if resource_url:
            refresh_request["resource"] = resource_url

        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_endpoint,
                data=refresh_request,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30.0,
            )
            response.raise_for_status()

        new_token_data = response.json()

        expires_at = None
        if new_token_data.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(
                seconds=new_token_data["expires_in"]
            )

        self.storage.update_token(
            user_id=user_id,
            provider=self.provider,
            access_token=new_token_data["access_token"],
            refresh_token=new_token_data.get("refresh_token"),
            expires_at=expires_at,
        )

        logger.info(
            "%s Token refreshed successfully",
            LOG_PREFIX,
        )

        return new_token_data["access_token"]

    async def get_valid_token(self, user_id: str) -> str:
        """Get a valid access token, refreshing if necessary.

        Args:
            user_id: User identifier.

        Returns:
            Valid access token.

        Raises:
            ValueError: If no token found or refresh fails.
        """
        token = self.storage.get_token(user_id, self.provider)
        if not token:
            raise ValueError(
                f"No MCP OAuth token found for user {user_id} "
                f"(provider={self.provider})"
            )

        # Check if token is expired (with 5 minute buffer)
        if token.is_expired(buffer_seconds=300):
            logger.info("%s Token expired, refreshing", LOG_PREFIX)
            return await self.refresh_token(user_id)

        return token.access_token

    def get_status(self, user_id: str) -> Dict[str, Any]:
        """Get OAuth status for a user.

        Args:
            user_id: User identifier.

        Returns:
            Dict with authentication status information.
        """
        token = self.storage.get_token(user_id, self.provider)
        client_reg = self.storage.get_client_registration(user_id, self.provider)

        if not token:
            return {
                "is_authenticated": False,
                "has_token": False,
                "has_client_registration": client_reg is not None,
                "token_expired": False,
                "expires_at": None,
                "scope": None,
            }

        return {
            "is_authenticated": True,
            "has_token": True,
            "has_client_registration": client_reg is not None,
            "token_expired": token.is_expired(buffer_seconds=0),
            "expires_at": (token.expires_at.isoformat() if token.expires_at else None),
            "scope": token.scope,
        }

    def revoke(self, user_id: str) -> bool:
        """Revoke OAuth access for a user.

        Deletes all stored OAuth data (registration, tokens, state).

        Args:
            user_id: User identifier.

        Returns:
            True if data was deleted, False if nothing to delete.
        """
        logger.info(
            "%s Revoking OAuth access for user=%s provider=%s",
            LOG_PREFIX,
            user_id,
            self.provider,
        )

        had_token = self.storage.get_token(user_id, self.provider) is not None
        self.storage.delete_all_for_user(user_id, self.provider)

        return had_token
