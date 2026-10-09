"""Notion OAuth handler with Dynamic Client Registration.

This module implements the complete OAuth flow for Notion MCP:
1. Dynamic Client Registration (RFC 7591) - Create unique client_id per user
2. Authorization URL generation
3. Token exchange
4. Token refresh

Based on the working implementation in notionmcp/oauth_handler.py.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx

from .storage import OAuthStorageService, oauth_storage

logger = logging.getLogger(__name__)
LOG_PREFIX = "[NOTION-OAUTH]"


class NotionOAuthHandler:
    """Handles OAuth flow for Notion MCP with Dynamic Client Registration.

    Notion's MCP implementation uses a separate OAuth server at mcp.notion.com
    with dynamic client registration per user.
    """

    def __init__(
        self,
        storage: Optional[OAuthStorageService] = None,
        redirect_uri: Optional[str] = None,
        client_name: str = "AgenticStudio Notion Integration",
    ):
        """Initialize the Notion OAuth handler.

        Args:
            storage: Storage service for OAuth data (defaults to global instance).
            redirect_uri: OAuth callback URI (defaults to env or localhost).
            client_name: Name to register the OAuth client with.
        """
        self.storage = storage or oauth_storage

        # OAuth endpoints
        self.register_uri = os.getenv(
            "NOTION_OAUTH_REGISTER_URI", "https://mcp.notion.com/register"
        )
        self.authorize_uri = os.getenv(
            "NOTION_OAUTH_AUTHORIZE_URI", "https://mcp.notion.com/authorize"
        )
        self.token_uri = os.getenv(
            "NOTION_OAUTH_TOKEN_URI", "https://mcp.notion.com/token"
        )

        # Configuration
        self.redirect_uri = redirect_uri or os.getenv(
            "NOTION_OAUTH_REDIRECT_URI",
            "http://localhost:8000/api/notion-oauth/callback",
        )
        self.client_name = client_name
        self.scope = "mcp.tools"  # MCP-specific scope
        self.provider = "notion"

    async def register_client(self) -> Dict[str, Any]:
        """Dynamically register a new OAuth client with Notion MCP.

        This follows RFC 7591 Dynamic Client Registration.
        Each user gets a unique client_id for their OAuth flow.

        Returns:
            Dict with client_id and other registration metadata.

        Raises:
            httpx.HTTPStatusError: If registration fails.
        """
        registration_request = {
            "client_name": self.client_name,
            "redirect_uris": [self.redirect_uri],
            "token_endpoint_auth_method": "none",  # No client secret required
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": self.scope,
        }

        logger.info(
            "%s Registering new OAuth client at %s", LOG_PREFIX, self.register_uri
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.register_uri,
                json=registration_request,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )
            response.raise_for_status()

        registration_data = response.json()
        logger.info(
            "%s Client registered successfully, client_id=%s",
            LOG_PREFIX,
            registration_data.get("client_id", "")[:8] + "...",
        )
        return registration_data

    async def initiate_flow(self, user_id: str) -> Tuple[str, str]:
        """Initiate OAuth flow for a user.

        Steps:
        1. Register a new OAuth client dynamically
        2. Store the client registration
        3. Generate authorization URL with state for CSRF protection

        Args:
            user_id: Unique identifier for the user (email).

        Returns:
            Tuple of (authorization_url, state).

        Raises:
            httpx.HTTPStatusError: If client registration fails.
        """
        logger.info("%s Initiating OAuth flow for user=%s", LOG_PREFIX, user_id)

        # Step 1: Register new client
        registration = await self.register_client()

        # Step 2: Store client registration
        self.storage.store_client_registration(
            user_id=user_id,
            provider=self.provider,
            client_id=registration["client_id"],
            client_secret=registration.get("client_secret"),
            registration_access_token=registration.get("registration_access_token"),
            metadata={
                "redirect_uris": registration.get("redirect_uris", []),
                "token_endpoint_auth_method": registration.get(
                    "token_endpoint_auth_method", "none"
                ),
                "grant_types": registration.get("grant_types", []),
            },
        )

        # Step 3: Generate state and authorization URL
        state = self.storage.store_state(user_id, self.provider)

        auth_params = {
            "client_id": registration["client_id"],
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": state,
            # MCP-specific: Include resource indicator
            "resource": "https://mcp.notion.com",
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
            ValueError: If state doesn't match or client registration not found.
            httpx.HTTPStatusError: If token exchange fails.
        """
        # Verify state and get user_id
        user_id = self.storage.verify_and_delete_state(state, self.provider)
        if not user_id:
            raise ValueError("Invalid or expired state - possible CSRF attack")

        logger.info("%s Handling callback for user=%s", LOG_PREFIX, user_id)

        # Get client registration
        client_reg = self.storage.get_client_registration(user_id, self.provider)
        if not client_reg:
            raise ValueError("Client registration not found for user")

        # Exchange code for token
        token_request = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": client_reg.client_id,
            # Note: No client_secret due to token_endpoint_auth_method: "none"
        }

        logger.debug("%s Exchanging code for token", LOG_PREFIX)

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
            client_id=client_reg.client_id,
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
            ValueError: If token or client registration not found.
            httpx.HTTPStatusError: If refresh fails.
        """
        # Get stored token
        token = self.storage.get_token(user_id, self.provider)
        if not token or not token.refresh_token:
            raise ValueError("No refresh token found for user")

        # Get client registration
        client_reg = self.storage.get_client_registration(user_id, self.provider)
        if not client_reg:
            raise ValueError("Client registration not found for user")

        logger.info("%s Refreshing token for user=%s", LOG_PREFIX, user_id)

        # Refresh token request
        refresh_request = {
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "client_id": client_reg.client_id,
            # No client_secret needed
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

        # Calculate expiry
        expires_at = None
        if new_token_data.get("expires_in"):
            expires_at = datetime.utcnow() + timedelta(
                seconds=new_token_data["expires_in"]
            )

        # Update stored token
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
            Valid access token.

        Raises:
            ValueError: If no token found or refresh fails.
        """
        token = self.storage.get_token(user_id, self.provider)
        if not token:
            raise ValueError(f"No Notion OAuth token found for user {user_id}")

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


# Global instance for convenience
notion_oauth_handler = NotionOAuthHandler()
