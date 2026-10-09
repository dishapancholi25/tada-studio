"""User API Token service for Personal Access Token (PAT) management.

This service provides CRUD operations and validation logic for user-generated
API tokens that can be used to authenticate HTTP execution requests.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import bcrypt
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ...models import UserAPIToken, Workflow, WorkflowMembership
from ...services.config import get_logger
from ...services.database import get_db


logger = get_logger(__name__)
LOG_PREFIX = "[USER-API-TOKEN]"


class UserAPITokenService:
    """Service for managing user API tokens (Personal Access Tokens)."""

    # Token prefix for easy identification
    TOKEN_PREFIX = "na"  # Nexus Agent
    TOKEN_LENGTH = 32  # Length in bytes (will be 43 chars base64 encoded)

    @staticmethod
    def generate_token_string() -> Tuple[str, str]:
        """Generate a new random token string with prefix.

        Returns:
            Tuple of (full_token, token_prefix_for_display)
            Example: ("na_abc123def456...", "na_abc123de")
        """
        # Generate cryptographically secure random token
        random_part = secrets.token_urlsafe(UserAPITokenService.TOKEN_LENGTH)

        # Create full token with prefix
        full_token = f"{UserAPITokenService.TOKEN_PREFIX}_{random_part}"

        # Extract prefix for display (first 11 chars)
        token_prefix = full_token[:11]

        return full_token, token_prefix

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token using bcrypt.

        Args:
            token: Plaintext token to hash

        Returns:
            Bcrypt hash of the token
        """
        return bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_token(token: str, token_hash: str) -> bool:
        """Verify a token against its hash.

        Args:
            token: Plaintext token to verify
            token_hash: Bcrypt hash to verify against

        Returns:
            True if token matches hash, False otherwise
        """
        try:
            return bcrypt.checkpw(token.encode(), token_hash.encode())
        except Exception as e:
            logger.warning(f"{LOG_PREFIX} Token verification failed: {e}")
            return False

    @staticmethod
    def create_token(
        user_id: str,
        token_name: str,
        scopes: List[str] = None,
        description: str = None,
        expires_in_days: int = None,
    ) -> Tuple[UserAPIToken, str]:
        """Create a new user API token.

        Args:
            user_id: User who owns this token (email)
            token_name: User-friendly name for the token
            scopes: List of scopes (e.g., ["workflow:*"] or ["workflow:my-workflow"])
            description: Optional description of token purpose
            expires_in_days: Number of days until expiration (None for no expiration)

        Returns:
            Tuple of (UserAPIToken object, plaintext_token)
            The plaintext token is only returned once and should be shown to the user

        Example:
            >>> token_obj, plaintext = UserAPITokenService.create_token(
            ...     user_id="user@example.com",
            ...     token_name="My Integration Token",
            ...     scopes=["workflow:*"],
            ...     expires_in_days=90
            ... )
            >>> print(f"Token: {plaintext}")  # Show to user
            >>> # token_obj is saved to database
        """
        with get_db() as db:
            # Generate token
            plaintext_token, token_prefix = UserAPITokenService.generate_token_string()

            # Hash token for storage
            token_hash = UserAPITokenService.hash_token(plaintext_token)

            # Calculate expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now(timezone.utc) + timedelta(
                    days=expires_in_days
                )

            # Default scopes
            if scopes is None:
                scopes = ["workflow:*:execute"]  # Default: execute all workflows

            # Create token record
            token_obj = UserAPIToken(
                user_id=user_id,
                token_hash=token_hash,
                token_prefix=token_prefix,
                token_name=token_name,
                description=description,
                scopes=scopes,
                expires_at=expires_at,
                is_active=True,
                created_by_user_id=user_id,
            )

            db.add(token_obj)
            db.commit()
            db.refresh(token_obj)

            # Detach from session
            db.expunge(token_obj)

            logger.info(
                f"{LOG_PREFIX} Created token '{token_name}' for user '{user_id}' "
                f"(prefix: {token_prefix}, scopes: {scopes})"
            )

            return token_obj, plaintext_token

    @staticmethod
    def list_user_tokens(user_id: str) -> List[UserAPIToken]:
        """List all tokens for a user (without plaintext tokens).

        Args:
            user_id: User to list tokens for

        Returns:
            List of UserAPIToken objects (token_hash is included but not plaintext)
        """
        with get_db() as db:
            tokens = (
                db.query(UserAPIToken)
                .filter(UserAPIToken.user_id == user_id)
                .order_by(UserAPIToken.created_at.desc())
                .all()
            )

            # Detach from session
            for token in tokens:
                db.expunge(token)

            return tokens

    @staticmethod
    def get_token_by_id(token_id: str, user_id: str = None) -> Optional[UserAPIToken]:
        """Get a token by its ID.

        Args:
            token_id: Token UUID
            user_id: Optional user ID to verify ownership

        Returns:
            UserAPIToken object or None if not found
        """
        with get_db() as db:
            query = db.query(UserAPIToken).filter(UserAPIToken.id == token_id)

            if user_id:
                query = query.filter(UserAPIToken.user_id == user_id)

            token = query.first()

            if token:
                db.expunge(token)

            return token

    @staticmethod
    def revoke_token(token_id: str, user_id: str = None) -> bool:
        """Revoke (deactivate) a token.

        Args:
            token_id: Token UUID to revoke
            user_id: Optional user ID to verify ownership

        Returns:
            True if token was revoked, False if not found
        """
        with get_db() as db:
            query = db.query(UserAPIToken).filter(UserAPIToken.id == token_id)

            if user_id:
                query = query.filter(UserAPIToken.user_id == user_id)

            token = query.first()

            if not token:
                return False

            token.is_active = False
            token.updated_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                f"{LOG_PREFIX} Revoked token '{token.token_name}' "
                f"(prefix: {token.token_prefix}) for user '{token.user_id}'"
            )

            return True

    @staticmethod
    def validate_token(
        plaintext_token: str, workflow_name: str = None
    ) -> Optional[Tuple[UserAPIToken, str]]:
        """Validate a token and check if it has access to a workflow.

        This is the main validation method used by the authentication system.

        Args:
            plaintext_token: The plaintext token to validate
            workflow_name: Optional workflow name to check access for

        Returns:
            Tuple of (UserAPIToken, user_id) if valid, None otherwise

        Example:
            >>> token_obj, user_id = UserAPITokenService.validate_token(
            ...     "na_abc123...",
            ...     workflow_name="my-workflow"
            ... )
            >>> if token_obj:
            ...     print(f"Valid token for user {user_id}")
        """
        with get_db() as db:
            # Extract prefix for faster lookup
            if not plaintext_token.startswith(f"{UserAPITokenService.TOKEN_PREFIX}_"):
                logger.debug(f"{LOG_PREFIX} Invalid token format (missing prefix)")
                return None

            token_prefix = plaintext_token[:11]

            # Find candidate tokens by prefix (faster than checking all hashes)
            candidates = (
                db.query(UserAPIToken)
                .filter(
                    and_(
                        UserAPIToken.token_prefix == token_prefix,
                        UserAPIToken.is_active,
                        or_(
                            UserAPIToken.expires_at.is_(None),
                            UserAPIToken.expires_at > datetime.now(timezone.utc),
                        ),
                    )
                )
                .all()
            )

            # Verify hash (may have multiple tokens with same prefix)
            token_obj = None
            for candidate in candidates:
                if UserAPITokenService.verify_token(
                    plaintext_token, candidate.token_hash
                ):
                    token_obj = candidate
                    break

            if not token_obj:
                logger.debug(f"{LOG_PREFIX} Token not found or hash mismatch")
                return None

            # Check if token is expired (double-check)
            if not token_obj.is_valid():
                logger.warning(
                    f"{LOG_PREFIX} Token '{token_obj.token_name}' is expired or inactive"
                )
                return None

            # Check workflow access if specified
            if workflow_name:
                has_access = UserAPITokenService._check_workflow_access(
                    token_obj, workflow_name, db
                )

                if not has_access:
                    logger.warning(
                        f"{LOG_PREFIX} Token '{token_obj.token_name}' does not have "
                        f"access to workflow '{workflow_name}'"
                    )
                    return None

            # Update usage stats
            token_obj.update_usage()
            db.commit()
            db.refresh(token_obj)

            # Detach from session
            db.expunge(token_obj)

            logger.debug(
                f"{LOG_PREFIX} Token '{token_obj.token_name}' validated successfully "
                f"for user '{token_obj.user_id}'"
            )

            return token_obj, token_obj.user_id

    @staticmethod
    def _check_workflow_access(
        token: UserAPIToken, workflow_identifier: str, db: Session
    ) -> bool:
        """Check if a token has access to a specific workflow.

        This checks:
        1. Token scopes (e.g., "workflow:*" or "workflow:specific-name")
        2. User's workflow ownership and memberships

        Args:
            token: UserAPIToken object
            workflow_identifier: Workflow UUID or name to check access for
            db: Database session

        Returns:
            True if token has access, False otherwise
        """
        # Check if token has scope for this workflow
        required_scope = f"workflow:{workflow_identifier}"

        if not token.has_scope(required_scope):
            logger.debug(
                f"{LOG_PREFIX} Token does not have scope for '{workflow_identifier}' "
                f"(scopes: {token.scopes})"
            )
            return False

        # Check if user actually has access to this workflow
        # (to prevent scope manipulation)
        # Try to parse as UUID first, then fall back to name lookup
        import uuid

        is_uuid = False
        try:
            uuid.UUID(workflow_identifier)
            is_uuid = True
        except (ValueError, AttributeError):
            pass

        if is_uuid:
            # Look up by workflow ID (UUID)
            workflow = (
                db.query(Workflow).filter(Workflow.id == workflow_identifier).first()
            )
        else:
            # Look up by workflow name (legacy)
            workflow = (
                db.query(Workflow).filter(Workflow.name == workflow_identifier).first()
            )

        if not workflow:
            logger.warning(f"{LOG_PREFIX} Workflow '{workflow_identifier}' not found")
            return False

        # Check if user owns the workflow or is a member
        is_owner = workflow.created_by_user_id == token.user_id

        is_member = (
            db.query(WorkflowMembership)
            .filter(
                and_(
                    WorkflowMembership.workflow_id == workflow.id,
                    WorkflowMembership.user_id == token.user_id,
                )
            )
            .first()
            is not None
        )

        if not (is_owner or is_member):
            logger.warning(
                f"{LOG_PREFIX} User '{token.user_id}' does not have access to "
                f"workflow '{workflow_identifier}'"
            )
            return False

        return True

    @staticmethod
    def validate_token_no_scope_check(
        plaintext_token: str,
    ) -> Optional[Tuple["UserAPIToken", str]]:
        """Validate a PAT without performing workflow-scope checks.

        Used by the PAT authentication path (get_current_user) where scope
        checking happens per-route via require_scope(), not at auth time.

        Args:
            plaintext_token: The plaintext na_-prefixed token.

        Returns:
            Tuple of (UserAPIToken, user_id) if valid and active, None otherwise.
        """
        with get_db() as db:
            if not plaintext_token.startswith(f"{UserAPITokenService.TOKEN_PREFIX}_"):
                logger.debug(f"{LOG_PREFIX} Invalid token format (missing prefix)")
                return None

            token_prefix = plaintext_token[:11]

            candidates = (
                db.query(UserAPIToken)
                .filter(
                    and_(
                        UserAPIToken.token_prefix == token_prefix,
                        UserAPIToken.is_active,
                        or_(
                            UserAPIToken.expires_at.is_(None),
                            UserAPIToken.expires_at > datetime.now(timezone.utc),
                        ),
                    )
                )
                .all()
            )

            token_obj = None
            for candidate in candidates:
                if UserAPITokenService.verify_token(plaintext_token, candidate.token_hash):
                    token_obj = candidate
                    break

            if not token_obj:
                logger.debug(f"{LOG_PREFIX} Token not found or hash mismatch")
                return None

            if not token_obj.is_valid():
                logger.warning(
                    f"{LOG_PREFIX} Token '{token_obj.token_name}' is expired or inactive"
                )
                return None

            db.expunge(token_obj)
            return token_obj, token_obj.user_id

    @staticmethod
    def enforce_creator_ceiling(scopes: List[str], is_admin: bool) -> None:
        """Raise ValueError if any scope exceeds what the creator can grant.

        Regular users may only grant:
          - workflow:*:read
          - workflow:*:execute
          - workflow:<name>:read
          - workflow:<name>:execute

        Admins can grant any valid scope.

        Args:
            scopes: Requested scope list (already validated against registry)
            is_admin: Whether the creating user holds admin privileges

        Raises:
            ValueError: If any scope exceeds the creator's ceiling
        """
        if is_admin:
            return
        from .scope_registry import is_admin_only_scope

        exceeded = [s for s in scopes if is_admin_only_scope(s)]
        if exceeded:
            raise ValueError(
                f"Scopes exceed your permissions: {exceeded}. "
                "Non-admin users may only grant workflow:*:read, workflow:*:execute, "
                "or workflow:<name>:read / workflow:<name>:execute."
            )

    @staticmethod
    def update_token_scopes(
        token_id: str, user_id: str, scopes: List[str]
    ) -> Optional[UserAPIToken]:
        """Update token scopes.

        Args:
            token_id: Token UUID
            user_id: User ID to verify ownership
            scopes: New list of scopes

        Returns:
            Updated UserAPIToken object or None if not found
        """
        with get_db() as db:
            token = (
                db.query(UserAPIToken)
                .filter(
                    and_(
                        UserAPIToken.id == token_id,
                        UserAPIToken.user_id == user_id,
                    )
                )
                .first()
            )

            if not token:
                return None

            token.scopes = scopes
            token.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(token)

            # Detach from session
            db.expunge(token)

            logger.info(
                f"{LOG_PREFIX} Updated scopes for token '{token.token_name}' "
                f"to {scopes}"
            )

            return token
