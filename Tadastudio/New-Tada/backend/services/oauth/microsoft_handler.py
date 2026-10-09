"""Microsoft OAuth handler for Azure AD delegated authentication.

Implements the OAuth 2.0 authorization code flow for Microsoft APIs.
Used by the SharePoint/OneDrive MCP servers (Graph API scopes) and the
Fabric MCP server (Fabric API scopes).

Unlike Notion, Microsoft uses pre-registered app registrations (no dynamic
client registration). Credentials come from environment variables:
AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET.

Two handler instances are created:
- ``microsoft_oauth_handler``  – Graph scopes (SharePoint / OneDrive)
- ``fabric_oauth_handler``     – Fabric scopes (workspaces, lakehouses, etc.)
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

from .storage import OAuthStorageService, oauth_storage

logger = logging.getLogger(__name__)
LOG_PREFIX = "[MICROSOFT-OAUTH]"


class MicrosoftOAuthHandler:
    """Handles OAuth flow for Microsoft Graph API via Azure AD.

    Uses the authorization code flow with a pre-registered Azure AD
    app registration. Tokens are stored per-user in the OAuth database.
    """

    # Default scopes for each provider
    GRAPH_SCOPE = "User.Read Sites.Read.All Files.Read.All offline_access"
    FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default offline_access"
    # Double forward slash is required per Microsoft docs for SQL endpoint access
    SQL_SCOPE = "https://database.windows.net//user_impersonation"

    def __init__(
        self,
        storage: Optional[OAuthStorageService] = None,
        redirect_uri: Optional[str] = None,
        scope: Optional[str] = None,
        provider: str = "microsoft",
    ):
        self.storage = storage or oauth_storage

        # Azure AD app registration (from env vars)
        self.tenant_id = os.getenv("AZURE_TENANT_ID", "")
        self.client_id = os.getenv("AZURE_CLIENT_ID", "")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

        # OAuth endpoints (tenant-specific)
        self.authorize_uri = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/authorize"
        )
        self.token_uri = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        )

        # Configuration
        self.redirect_uri = redirect_uri or os.getenv(
            "MICROSOFT_OAUTH_REDIRECT_URI",
            "http://localhost:8000/api/microsoft-oauth/callback",
        )
        # offline_access is required to get a refresh_token
        self.scope = scope or self.GRAPH_SCOPE
        self.provider = provider

    async def initiate_flow(self, user_id: str) -> Tuple[str, str]:
        """Initiate OAuth flow for a user.

        Unlike Notion, no dynamic client registration is needed. We use
        the pre-registered app credentials from environment variables.

        Args:
            user_id: Unique identifier for the user (email).

        Returns:
            Tuple of (authorization_url, state).
        """
        logger.info("%s Initiating OAuth flow for user=%s", LOG_PREFIX, user_id)

        if not self.client_id or not self.tenant_id:
            raise ValueError(
                "AZURE_CLIENT_ID and AZURE_TENANT_ID must be set in environment"
            )

        # Store a "client registration" for consistency with the storage model.
        # Microsoft doesn't use dynamic registration, but the storage layer
        # expects a client_id to be stored for token refresh.
        self.storage.store_client_registration(
            user_id=user_id,
            provider=self.provider,
            client_id=self.client_id,
            client_secret=self.client_secret,
            registration_access_token=None,
            metadata={
                "tenant_id": self.tenant_id,
                "token_endpoint_auth_method": "client_secret_post",
            },
        )

        # Generate state for CSRF protection
        state = self.storage.store_state(user_id, self.provider)

        auth_params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": state,
            "response_mode": "query",
        }

        authorization_url = f"{self.authorize_uri}?{urlencode(auth_params)}"

        logger.info("%s Authorization URL generated for user=%s", LOG_PREFIX, user_id)

        return authorization_url, state

    async def handle_callback(self, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth callback and exchange code for tokens.

        Args:
            code: Authorization code from callback.
            state: State parameter for CSRF verification.

        Returns:
            Dict with status, user_id, and token info.

        Raises:
            ValueError: If state doesn't match.
            httpx.HTTPStatusError: If token exchange fails.
        """
        # Verify state and get user_id
        user_id = self.storage.verify_and_delete_state(state, self.provider)
        if not user_id:
            raise ValueError("Invalid or expired state - possible CSRF attack")

        logger.info("%s Handling callback for user=%s", LOG_PREFIX, user_id)

        # Exchange code for token
        token_request = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_uri,
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
            client_id=self.client_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=expires_at,
            scope=token_data.get("scope"),
        )

        logger.info("%s Token exchange successful for user=%s", LOG_PREFIX, user_id)

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
            ValueError: If token not found.
            httpx.HTTPStatusError: If refresh fails.
        """
        token = self.storage.get_token(user_id, self.provider)
        if not token or not token.refresh_token:
            raise ValueError("No refresh token found for user")

        logger.info("%s Refreshing token for user=%s", LOG_PREFIX, user_id)

        refresh_request = {
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_uri,
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

        logger.info("%s Token refreshed successfully for user=%s", LOG_PREFIX, user_id)

        return new_token_data["access_token"]

    async def get_valid_token(self, user_id: str) -> str:
        """Get a valid access token, refreshing if necessary.

        Args:
            user_id: User identifier.

        Returns:
            Valid access token for Microsoft Graph API.

        Raises:
            ValueError: If no token found or refresh fails.
        """
        token = self.storage.get_token(user_id, self.provider)
        if not token:
            raise ValueError(f"No Microsoft OAuth token found for user {user_id}")

        # Check if token is expired (with 5 minute buffer)
        if token.is_expired(buffer_seconds=300):
            logger.info("%s Token expired for user=%s, refreshing", LOG_PREFIX, user_id)
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
            }

        return {
            "is_authenticated": True,
            "has_token": True,
            "has_client_registration": client_reg is not None,
            "token_expired": token.is_expired(buffer_seconds=0),
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
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
        logger.info("%s Revoking OAuth access for user=%s", LOG_PREFIX, user_id)

        had_token = self.storage.get_token(user_id, self.provider) is not None
        self.storage.delete_all_for_user(user_id, self.provider)

        return had_token

    async def acquire_cross_resource_token(
        self, user_id: str, target_scope: str, target_provider: str
    ) -> Optional[str]:
        """Acquire a token for a different resource using this handler's refresh token.

        Azure AD v2.0 refresh tokens are multi-resource. A refresh token obtained
        for one scope (e.g. Fabric API) can be exchanged for an access token
        targeting a different scope (e.g. database.windows.net) without additional
        user consent, provided the app registration has the required permissions.

        Args:
            user_id: User identifier.
            target_scope: The scope to acquire a token for
                          (e.g. ``SQL_SCOPE``).
            target_provider: Provider name to store the token under
                             (e.g. ``"fabric_sql"``).

        Returns:
            The new access token, or None if acquisition failed.
        """
        token = self.storage.get_token(user_id, self.provider)
        if not token or not token.refresh_token:
            logger.warning(
                "%s Cannot acquire cross-resource token for %s: no refresh token for provider %s",
                LOG_PREFIX,
                target_scope,
                self.provider,
            )
            return None

        logger.info(
            "%s Acquiring cross-resource token scope=%s target_provider=%s user=%s",
            LOG_PREFIX,
            target_scope,
            target_provider,
            user_id,
        )

        refresh_request = {
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": target_scope,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_uri,
                    data=refresh_request,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning(
                "%s Failed to acquire cross-resource token for %s: HTTP %s — %s",
                LOG_PREFIX,
                target_scope,
                e.response.status_code,
                e.response.text[:200],
            )
            return None
        except Exception as e:
            logger.warning(
                "%s Failed to acquire cross-resource token for %s: %s",
                LOG_PREFIX,
                target_scope,
                e,
            )
            return None

        new_token_data = response.json()

        expires_at = None
        if new_token_data.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(
                seconds=new_token_data["expires_in"]
            )

        self.storage.store_token(
            user_id=user_id,
            provider=target_provider,
            client_id=self.client_id,
            access_token=new_token_data["access_token"],
            refresh_token=new_token_data.get("refresh_token"),
            expires_at=expires_at,
            scope=target_scope,
        )

        # Azure AD may rotate the refresh token — propagate back to the source
        # provider so future refreshes don't use a stale token.
        if new_token_data.get("refresh_token"):
            self.storage.update_token(
                user_id=user_id,
                provider=self.provider,
                access_token=token.access_token,
                refresh_token=new_token_data["refresh_token"],
            )

        logger.info(
            "%s Cross-resource token acquired for %s user=%s",
            LOG_PREFIX,
            target_provider,
            user_id,
        )
        return new_token_data["access_token"]

    async def get_valid_cross_resource_token(
        self, user_id: str, target_scope: str, target_provider: str
    ) -> Optional[str]:
        """Get a valid cross-resource token, acquiring or refreshing if needed.

        Args:
            user_id: User identifier.
            target_scope: The scope for the token.
            target_provider: Provider name the token is stored under.

        Returns:
            Valid access token, or None if unavailable.
        """
        existing = self.storage.get_token(user_id, target_provider)
        if existing and not existing.is_expired(buffer_seconds=300):
            return existing.access_token

        return await self.acquire_cross_resource_token(
            user_id, target_scope, target_provider
        )


# Global instances — one per resource/scope set
microsoft_oauth_handler = MicrosoftOAuthHandler()
fabric_oauth_handler = MicrosoftOAuthHandler(
    scope=MicrosoftOAuthHandler.FABRIC_SCOPE,
    provider="fabric",
)
