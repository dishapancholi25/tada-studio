"""OAuth storage service using SQLAlchemy.

This module provides a storage service for OAuth client registrations,
tokens, and state using the application's database.
"""

import base64
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


from ...models.oauth import OAuthClientRegistration, OAuthState, OAuthToken
from ..database.session import get_db

logger = logging.getLogger(__name__)
LOG_PREFIX = "[OAUTH-STORAGE]"


class OAuthStorageService:
    """Service for storing and retrieving OAuth credentials.

    Provides methods for managing OAuth client registrations, tokens,
    and state in the database.
    """

    # --- Client Registration ---

    def store_client_registration(
        self,
        user_id: str,
        provider: str,
        client_id: str,
        client_secret: Optional[str] = None,
        registration_access_token: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OAuthClientRegistration:
        """Store or update a client registration.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name (e.g., 'notion').
            client_id: OAuth client ID.
            client_secret: Optional client secret.
            registration_access_token: Optional registration access token.
            metadata: Optional additional metadata.

        Returns:
            The stored OAuthClientRegistration.
        """
        with get_db() as db:
            # Check for existing registration
            existing = (
                db.query(OAuthClientRegistration)
                .filter(
                    OAuthClientRegistration.user_id == user_id,
                    OAuthClientRegistration.provider == provider,
                )
                .first()
            )

            if existing:
                # Update existing
                existing.client_id = client_id
                existing.client_secret = client_secret
                existing.registration_access_token = registration_access_token
                existing.metadata_ = metadata
                logger.debug(
                    "%s Updated client registration for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
                db.commit()
                db.refresh(existing)
                return existing
            else:
                # Create new
                registration = OAuthClientRegistration(
                    user_id=user_id,
                    provider=provider,
                    client_id=client_id,
                    client_secret=client_secret,
                    registration_access_token=registration_access_token,
                    metadata_=metadata,
                )
                db.add(registration)
                logger.info(
                    "%s Created client registration for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
                db.commit()
                db.refresh(registration)
                return registration

    def get_client_registration(
        self, user_id: str, provider: str = "notion"
    ) -> Optional[OAuthClientRegistration]:
        """Get client registration for a user/provider.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.

        Returns:
            OAuthClientRegistration if found, None otherwise.
        """
        with get_db() as db:
            return (
                db.query(OAuthClientRegistration)
                .filter(
                    OAuthClientRegistration.user_id == user_id,
                    OAuthClientRegistration.provider == provider,
                )
                .first()
            )

    def delete_client_registration(
        self, user_id: str, provider: str = "notion"
    ) -> bool:
        """Delete client registration for a user/provider.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.

        Returns:
            True if deleted, False if not found.
        """
        with get_db() as db:
            deleted = (
                db.query(OAuthClientRegistration)
                .filter(
                    OAuthClientRegistration.user_id == user_id,
                    OAuthClientRegistration.provider == provider,
                )
                .delete()
            )
            db.commit()
            if deleted:
                logger.info(
                    "%s Deleted client registration for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
            return deleted > 0

    # --- OAuth Tokens ---

    def store_token(
        self,
        user_id: str,
        provider: str,
        client_id: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        scope: Optional[str] = None,
    ) -> OAuthToken:
        """Store or update OAuth tokens.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.
            client_id: OAuth client ID.
            access_token: The access token.
            refresh_token: Optional refresh token.
            expires_at: Optional expiry datetime.
            scope: Optional granted scope.

        Returns:
            The stored OAuthToken.
        """
        with get_db() as db:
            # Check for existing token
            existing = (
                db.query(OAuthToken)
                .filter(
                    OAuthToken.user_id == user_id,
                    OAuthToken.provider == provider,
                )
                .first()
            )

            if existing:
                # Update existing
                existing.client_id = client_id
                existing.access_token = access_token
                existing.refresh_token = refresh_token or existing.refresh_token
                existing.expires_at = expires_at
                existing.scope = scope
                logger.debug(
                    "%s Updated token for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
                db.commit()
                db.refresh(existing)
                return existing
            else:
                # Create new
                token = OAuthToken(
                    user_id=user_id,
                    provider=provider,
                    client_id=client_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    scope=scope,
                )
                db.add(token)
                logger.info(
                    "%s Created token for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
                db.commit()
                db.refresh(token)
                return token

    def get_token(self, user_id: str, provider: str = "notion") -> Optional[OAuthToken]:
        """Get OAuth token for a user/provider.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.

        Returns:
            OAuthToken if found, None otherwise.
        """
        with get_db() as db:
            return (
                db.query(OAuthToken)
                .filter(
                    OAuthToken.user_id == user_id,
                    OAuthToken.provider == provider,
                )
                .first()
            )

    def update_token(
        self,
        user_id: str,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[OAuthToken]:
        """Update an existing token (for refresh).

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.
            access_token: New access token.
            refresh_token: Optional new refresh token (keeps old if None).
            expires_at: Optional new expiry.

        Returns:
            Updated OAuthToken if found, None otherwise.
        """
        with get_db() as db:
            token = (
                db.query(OAuthToken)
                .filter(
                    OAuthToken.user_id == user_id,
                    OAuthToken.provider == provider,
                )
                .first()
            )

            if token:
                token.access_token = access_token
                if refresh_token:
                    token.refresh_token = refresh_token
                token.expires_at = expires_at
                logger.debug(
                    "%s Refreshed token for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
                db.commit()
                db.refresh(token)
                return token

            return None

    def delete_token(self, user_id: str, provider: str = "notion") -> bool:
        """Delete OAuth token for a user/provider.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.

        Returns:
            True if deleted, False if not found.
        """
        with get_db() as db:
            deleted = (
                db.query(OAuthToken)
                .filter(
                    OAuthToken.user_id == user_id,
                    OAuthToken.provider == provider,
                )
                .delete()
            )
            db.commit()
            if deleted:
                logger.info(
                    "%s Deleted token for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
            return deleted > 0

    # --- OAuth State (CSRF Protection) ---

    def store_state(
        self,
        user_id: str,
        provider: str = "notion",
        expires_in_seconds: int = 600,
    ) -> str:
        """Generate and store OAuth state for CSRF protection.

        The state encodes the user_id and a random nonce in base64.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.
            expires_in_seconds: State validity duration (default 10 minutes).

        Returns:
            The generated state string.
        """
        # Generate state with embedded user_id and provider
        state_data = {
            "user_id": user_id,
            "provider": provider,
            "nonce": secrets.token_urlsafe(32),
        }
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

        with get_db() as db:
            # Delete any existing state for this user/provider
            db.query(OAuthState).filter(
                OAuthState.user_id == user_id,
                OAuthState.provider == provider,
            ).delete()

            # Create new state
            oauth_state = OAuthState(
                user_id=user_id,
                provider=provider,
                state=state,
                expires_at=expires_at,
            )
            db.add(oauth_state)
            db.commit()

            logger.debug(
                "%s Stored state for user=%s provider=%s",
                LOG_PREFIX,
                user_id,
                provider,
            )

        return state

    def verify_and_delete_state(
        self, state: str, provider: str = "notion"
    ) -> Optional[str]:
        """Verify state and return user_id if valid.

        Deletes the state after verification (single use).

        Args:
            state: The state string to verify.
            provider: OAuth provider name.

        Returns:
            user_id if state is valid and not expired, None otherwise.
        """
        # Decode state to get user_id
        try:
            state_json = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(state_json)
            user_id = state_data.get("user_id")
            if not user_id:
                logger.warning("%s State missing user_id", LOG_PREFIX)
                return None
        except Exception as e:
            logger.warning("%s Failed to decode state: %s", LOG_PREFIX, e)
            return None

        with get_db() as db:
            # Find and verify state
            oauth_state = (
                db.query(OAuthState)
                .filter(
                    OAuthState.user_id == user_id,
                    OAuthState.provider == provider,
                    OAuthState.state == state,
                )
                .first()
            )

            if not oauth_state:
                logger.warning(
                    "%s State not found for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
                return None

            # Check expiry
            if oauth_state.is_expired():
                logger.warning(
                    "%s State expired for user=%s provider=%s",
                    LOG_PREFIX,
                    user_id,
                    provider,
                )
                db.delete(oauth_state)
                db.commit()
                return None

            # Delete after successful verification (single use)
            db.delete(oauth_state)
            db.commit()
            logger.debug(
                "%s Verified and deleted state for user=%s provider=%s",
                LOG_PREFIX,
                user_id,
                provider,
            )

            return user_id

    def delete_state(self, user_id: str, provider: str = "notion") -> bool:
        """Delete OAuth state for a user/provider.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.

        Returns:
            True if deleted, False if not found.
        """
        with get_db() as db:
            deleted = (
                db.query(OAuthState)
                .filter(
                    OAuthState.user_id == user_id,
                    OAuthState.provider == provider,
                )
                .delete()
            )
            db.commit()
            return deleted > 0

    # --- Cleanup ---

    def delete_all_for_user(self, user_id: str, provider: str = "notion") -> None:
        """Delete all OAuth data for a user/provider.

        Removes client registration, tokens, and state.

        Args:
            user_id: User identifier (email).
            provider: OAuth provider name.
        """
        self.delete_token(user_id, provider)
        self.delete_client_registration(user_id, provider)
        self.delete_state(user_id, provider)
        logger.info(
            "%s Deleted all OAuth data for user=%s provider=%s",
            LOG_PREFIX,
            user_id,
            provider,
        )


# Global instance for convenience
oauth_storage = OAuthStorageService()
