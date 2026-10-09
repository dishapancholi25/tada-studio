"""User database synchronization utilities."""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.models.auth.user import User
from backend.services.database import get_db

from .exceptions import UserSyncError


logger = logging.getLogger(__name__)

# Debug mode: log user groups when DEBUG_GROUPS=true
DEBUG_GROUPS = os.getenv("DEBUG_GROUPS", "false").lower() in {"1", "true", "yes"}


def is_service_principal_claims(claims: Dict[str, Any]) -> bool:
    """Detect if claims originate from a service principal or managed identity.

    Service principals and managed identities produce app-only tokens that
    lack user-type claims (name, email). Two heuristics are used:

    1. ``idtyp == "app"`` — present on Azure AD v2 app-only tokens.
    2. ``appid`` present without any human display name claim — covers v1 tokens.

    Args:
        claims: Authentication claims dictionary

    Returns:
        bool: True if the token represents a service principal / managed identity
    """
    # Most reliable: idtyp claim is set to "app" for all Azure AD app-only tokens
    if claims.get("idtyp") == "app":
        return True

    # Fallback for v1 tokens: appid present but no user-type name claims
    if claims.get("appid") and not claims.get("name") and not claims.get("given_name"):
        return True

    return False


def extract_user_id_from_claims(claims: Dict[str, Any]) -> str:
    """Extract user ID from authentication claims.

    Args:
        claims: Authentication claims dictionary

    Returns:
        str: User ID (subject claim)

    Raises:
        UserSyncError: If 'sub' claim is missing

    Example:
        >>> claims = {"sub": "user123", "email": "user@example.com"}
        >>> user_id = extract_user_id_from_claims(claims)
        >>> print(user_id)
        user123
    """
    user_id = claims.get("sub")
    if not user_id:
        raise UserSyncError("Token missing 'sub' claim; cannot identify user")
    return user_id


def extract_email_from_claims(claims: Dict[str, Any]) -> str:
    """Extract email from authentication claims.

    This function checks multiple claim fields to find the user's email,
    trying: email, preferred_username, upn, unique_name in that order.

    Args:
        claims: Authentication claims dictionary

    Returns:
        str: User email address

    Raises:
        UserSyncError: If no email claim is found

    Example:
        >>> claims = {"email": "user@example.com"}
        >>> email = extract_email_from_claims(claims)
        >>> print(email)
        user@example.com
    """
    email = (
        claims.get("email")
        or claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("unique_name")
    )

    if not email:
        raise UserSyncError("No email claim found in token")

    return email


def sync_user_from_claims(claims: Dict[str, Any]) -> None:
    """Persist or update authenticated user in the database.

    This function creates a new user record if one doesn't exist, or updates
    an existing user's information based on the provided claims. It updates
    email, name, tenant information, group membership, and last login timestamp.

    Args:
        claims: Authentication claims dictionary from JWT or OAuth

    Raises:
        UserSyncError: If user synchronization fails

    Example:
        >>> claims = {
        ...     "sub": "user123",
        ...     "email": "user@example.com",
        ...     "name": "John Doe",
        ...     "tid": "tenant123",
        ...     "oid": "object123"
        ... }
        >>> sync_user_from_claims(claims)

    Note:
        This function does not raise exceptions on failure. Sync errors are
        logged as warnings to prevent authentication failures due to database issues.
    """
    try:
        user_id = extract_user_id_from_claims(claims)
    except UserSyncError as exc:
        logger.warning(f"[AUTH-SYNC] Cannot sync user: {exc}")
        return

    # Defensive copy to avoid DB serialization issues
    serialized_claims = dict(claims)

    MAX_OAUTH_GROUPS = 500  # Defense-in-depth: cap group count

    try:
        with get_db() as db:
            # Find or create user
            user = db.query(User).filter(User.id == user_id).first()
            is_new_user = user is None
            if not user:
                logger.info("[AUTH-SYNC] Creating new user record")
                # Service principals / managed identities always get the SYSTEM role
                if is_service_principal_claims(claims):
                    assigned_role = "SYSTEM"
                    logger.info(
                        "[AUTH-SYNC] Detected service principal / managed identity; assigning role 'SYSTEM'"
                    )
                else:
                    # Get default role from environment (default to USER)
                    assigned_role = os.getenv("DEFAULT_USER_ROLE", "USER").upper()
                    valid_roles = ["PENDING", "USER", "ADMIN"]
                    if assigned_role not in valid_roles:
                        logger.warning(
                            f"[AUTH-SYNC] Invalid DEFAULT_USER_ROLE '{assigned_role}', using 'USER'"
                        )
                        assigned_role = "USER"

                user = User(id=user_id, role=assigned_role)
                db.add(user)
                logger.info(f"[AUTH-SYNC] Assigned role '{assigned_role}' to new user")
            elif user.role not in ("SYSTEM",) and is_service_principal_claims(claims):
                # Promote existing non-SYSTEM user to SYSTEM if we now recognise it as a
                # service principal (e.g. role was USER before this feature was deployed)
                user.role = "SYSTEM"
                logger.info(
                    "[AUTH-SYNC] Promoted existing service principal user to role 'SYSTEM'"
                )

            # Update tenant and object IDs
            user.tenant_id = claims.get("tid") or user.tenant_id
            user.object_id = claims.get("oid") or user.object_id

            # Update email (try multiple claim fields)
            try:
                email = extract_email_from_claims(claims)
                user.email = email
            except UserSyncError:
                # Email not found in claims, keep existing value
                pass

            # Update display name
            display_name = claims.get("name")
            if display_name:
                user.name = display_name

            # Update given name (first name)
            given_name = claims.get("given_name") or claims.get("first_name")
            if given_name:
                user.given_name = given_name

            # Update family name (last name)
            family_name = claims.get("family_name") or claims.get("last_name")
            if family_name:
                user.family_name = family_name

            # Update groups from OAuth claims
            # Always normalize and persist groups, even if empty, to ensure removals are tracked
            groups = claims.get("groups")
            if groups:
                # Ensure groups is a list with validated entries
                if isinstance(groups, list):
                    validated_groups = [
                        g for g in groups if isinstance(g, str) and len(g) <= 255
                    ][:MAX_OAUTH_GROUPS]
                    if len(validated_groups) != len(groups):
                        logger.warning(
                            f"[AUTH-SYNC-GROUPS] Filtered {len(groups) - len(validated_groups)} "
                            f"invalid/excess group entries from claims"
                        )
                    user.groups = validated_groups
                    if DEBUG_GROUPS:
                        logger.debug(
                            f"[AUTH-SYNC-GROUPS] Updated {len(user.groups)} groups for user"
                        )
                else:
                    # Handle single group as string
                    if isinstance(groups, str) and len(groups) <= 255:
                        user.groups = [groups]
                    else:
                        user.groups = []
                        logger.warning(
                            "[AUTH-SYNC-GROUPS] Invalid groups claim type, clearing groups"
                        )
                    if DEBUG_GROUPS:
                        logger.debug(
                            f"[AUTH-SYNC-GROUPS] Updated {len(user.groups)} group(s) for user"
                        )
            else:
                # No groups claim or empty - set to empty list to persist removal
                user.groups = []
                if DEBUG_GROUPS:
                    logger.debug(
                        "[AUTH-SYNC-GROUPS] Cleared groups for user (no groups in claim)"
                    )

            # Update last login and claims
            user.last_login_at = datetime.now(timezone.utc)
            user.last_claims = serialized_claims

            logger.debug("[AUTH-SYNC] User synchronized successfully")

        # Auto-enroll into the Administrators DB group if user qualifies
        # via ADMIN_USERS or ADMIN_GROUP env vars
        try:
            from backend.services.auth.config import (
                ADMINISTRATORS_GROUP_NAME,
                get_auth_config,
            )
            from backend.services.auth.rbac import clear_admin_group_cache

            auth_config = get_auth_config()
            user_email = claims.get("email")
            user_groups = claims.get("groups", [])
            is_env_admin = False

            # Check ADMIN_USERS
            if user_email and user_email.lower() in auth_config.admin_users:
                is_env_admin = True

            # Check ADMIN_GROUP
            if not is_env_admin and auth_config.admin_group:
                if (
                    isinstance(user_groups, list)
                    and auth_config.admin_group in user_groups
                ):
                    is_env_admin = True

            if is_env_admin:
                from backend.services.groups.repository import GroupRepository

                repo = GroupRepository()
                repo.add_member(group_name=ADMINISTRATORS_GROUP_NAME, user_id=user_id)
                clear_admin_group_cache(user_id)

                # Promote role to ADMIN for env-protected admins (new and existing users).
                # Only promote; never downgrade an existing ADMIN role.
                with get_db() as db_role:
                    user_role = db_role.query(User).filter(User.id == user_id).first()
                    if user_role and user_role.role != "ADMIN":
                        user_role.role = "ADMIN"
                        logger.info(
                            "[AUTH-SYNC] Set role to ADMIN for env-protected admin user"
                        )

            # If new user was created with ADMIN role (from DEFAULT_USER_ROLE),
            # add them to Administrators group (mirroring update_user_role logic)
            elif is_new_user:
                with get_db() as db_check:
                    user_check = db_check.query(User).filter(User.id == user_id).first()
                    if user_check and user_check.role == "ADMIN":
                        from backend.services.groups.repository import GroupRepository

                        repo = GroupRepository()
                        repo.add_member(
                            group_name=ADMINISTRATORS_GROUP_NAME, user_id=user_id
                        )
                        clear_admin_group_cache(user_id)
        except Exception as admin_sync_error:
            logger.warning(
                f"[AUTH-SYNC] Failed to auto-enroll admin user: {admin_sync_error}"
            )

    except Exception as sync_error:
        # Don't fail authentication if user sync fails
        # Log warning and continue
        logger.warning(
            f"[AUTH-SYNC] Failed to persist user: {type(sync_error).__name__}"
        )


def build_full_name(claims: Dict[str, Any]) -> str:
    """Build full name from claims.

    This function constructs a full name from given_name and family_name
    claims, falling back to the name claim if components aren't available.

    Args:
        claims: Authentication claims dictionary

    Returns:
        str: Full name string

    Example:
        >>> claims = {"given_name": "John", "family_name": "Doe"}
        >>> full_name = build_full_name(claims)
        >>> print(full_name)
        John Doe
    """
    # Try to build from components first
    given = claims.get("given_name", "")
    family = claims.get("family_name", "")

    if given or family:
        return f"{given} {family}".strip()

    # Fall back to name claim
    return claims.get("name", "")


def enrich_claims_with_email(
    claims: Dict[str, Any], header_email: Optional[str] = None
) -> Dict[str, Any]:
    """Enrich claims dictionary with email from multiple sources.

    This function ensures the claims dictionary contains an email field,
    checking multiple sources: email claim, preferred_username, upn,
    unique_name, and OAuth proxy header.

    Args:
        claims: Authentication claims dictionary (will be modified)
        header_email: Optional email from X-Auth-Request-Email header

    Returns:
        Dict[str, Any]: Enriched claims dictionary

    Example:
        >>> claims = {"sub": "user123"}
        >>> claims = enrich_claims_with_email(claims, "user@example.com")
        >>> print(claims["email"])
        user@example.com
    """
    # Try to find email in claims first
    email = (
        claims.get("email")
        or claims.get("preferred_username")
        or claims.get("upn")
        or claims.get("unique_name")
        or header_email
    )

    # Fallback for service principal / managed identity tokens which carry no
    # email-like claim.  Construct a stable synthetic identifier from the
    # application ID and tenant ID so the user-sync step can succeed.
    # appid  – present on v1 tokens (service principal OAuth client credential flow)
    # azp    – present on v2 tokens (same flow)
    # oid    – object ID, always present; used when neither appid nor azp is set
    if not email:
        appid = claims.get("appid") or claims.get("azp")
        tid = claims.get("tid")
        oid = claims.get("oid")
        if appid and tid:
            email = f"{appid}@{tid}"
        elif oid and tid:
            email = f"{oid}@{tid}"

    if email:
        claims["email"] = email

    return claims


def enrich_claims_with_name(claims: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich claims dictionary with constructed name field.

    This function ensures the claims dictionary contains a name field,
    constructing it from given_name and family_name if not already present.

    Args:
        claims: Authentication claims dictionary (will be modified)

    Returns:
        Dict[str, Any]: Enriched claims dictionary

    Example:
        >>> claims = {"given_name": "John", "family_name": "Doe"}
        >>> claims = enrich_claims_with_name(claims)
        >>> print(claims["name"])
        John Doe
    """
    if not claims.get("name"):
        full_name = build_full_name(claims)
        if full_name:
            claims["name"] = full_name

    return claims


def enrich_claims(
    claims: Dict[str, Any],
    header_email: Optional[str] = None,
    auth_source: str = "azure_ad",
) -> Dict[str, Any]:
    """Enrich authentication claims with additional fields.

    This is a convenience function that applies all claim enrichment
    operations: adding email, name, and auth_source fields.

    Args:
        claims: Authentication claims dictionary (will be modified)
        header_email: Optional email from OAuth proxy header
        auth_source: Authentication source identifier (default: "azure_ad")

    Returns:
        Dict[str, Any]: Enriched claims dictionary

    Example:
        >>> claims = {"sub": "user123", "given_name": "John"}
        >>> claims = enrich_claims(claims, "user@example.com")
        >>> print(claims.get("email"), claims.get("auth_source"))
        user@example.com azure_ad
    """
    claims = enrich_claims_with_email(claims, header_email)
    claims = enrich_claims_with_name(claims)
    claims.setdefault("auth_source", auth_source)
    return claims
