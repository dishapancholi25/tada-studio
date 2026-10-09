"""Admin API routes for feature access management and user administration."""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.models.configuration import FeatureAccess
from backend.models.configuration.system_external_service import ExternalServiceAuthType
from backend.api.auth.dependencies import require_admin, get_current_user
from backend.services.auth.rbac import clear_feature_access_cache, _redact_email
from backend.services.auth.constants import FeatureName
from backend.services.configuration.group_external_service_service import (
    GroupExternalServiceService,
)
from backend.services.configuration.system_external_service_service import (
    SystemExternalServiceService,
)
from backend.services.database import get_db
from backend.api.user_settings.csrf import verify_csrf_token
from backend.services.admin.user_service import UserService
from backend.services.guardrails import ssrf_policy_service
from backend.api.user_settings.mcp_integration_handlers import (
    handle_delete_system_integration,
    handle_list_system_integrations,
    handle_save_system_integration,
)
from backend.api.user_settings.models import (
    DeleteMcpIntegrationResponse,
    ListMcpIntegrationsResponse,
    SaveMcpIntegrationRequest,
    SaveMcpIntegrationResponse,
)

logger = logging.getLogger(__name__)

# Valid feature name pattern: category.feature (e.g., "settings.database", "nav.workflow")
FEATURE_NAME_PATTERN = re.compile(r"^[a-z_]+\.[a-z_]+$")

# Whitelist of valid feature names (using constants from FeatureName enum)
VALID_FEATURES = FeatureName.all_features()

router = APIRouter(prefix="/api/admin", tags=["admin"])
user_service = UserService()


def validate_feature_name(feature_name: str) -> None:
    """Validate that a feature name is in the allowed whitelist.

    Args:
        feature_name: Feature identifier to validate

    Raises:
        HTTPException: 400 if feature name is invalid
    """
    if not FEATURE_NAME_PATTERN.match(feature_name):
        raise HTTPException(
            status_code=400,
            detail="Invalid feature name format. Must match pattern: category.feature",
        )

    if feature_name not in VALID_FEATURES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown feature name: {feature_name}. Must be one of: {', '.join(sorted(VALID_FEATURES))}",
        )


class FeatureAccessUpdate(BaseModel):
    """Request model for updating feature access."""

    admin_only: bool


class FeatureAccessResponse(BaseModel):
    """Response model for feature access.

    This response includes metadata about feature access control settings,
    indicating which features require admin privileges and which are accessible
    to all authenticated users.
    """

    success: bool
    feature: Optional[Dict[str, Any]] = None
    features: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


@router.get("/feature-access", response_model=FeatureAccessResponse)
def list_feature_access(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> FeatureAccessResponse:
    """List all feature access settings.

    Available to all authenticated users (returns metadata about feature access control).

    Returns:
        FeatureAccessResponse with all feature access settings
    """
    try:
        with get_db() as session:
            features = session.query(FeatureAccess).all()
            return FeatureAccessResponse(
                success=True, features=[f.to_dict() for f in features]
            )
    except Exception as e:
        logger.error(f"Error listing feature access: {e}")
        raise HTTPException(status_code=500, detail="Failed to list feature access")


@router.get("/feature-access/{feature_name}", response_model=FeatureAccessResponse)
def get_feature_access(
    request: Request,
    feature_name: str,
    current_user: Dict[str, Any] = Depends(require_admin),
) -> FeatureAccessResponse:
    """Get specific feature access setting.

    Requires admin privileges.
    Note: Rate limiting is applied at the application level via middleware.

    Args:
        feature_name: Feature identifier (e.g., "settings.database")

    Returns:
        FeatureAccessResponse with the feature setting

    Raises:
        HTTPException: 400 if feature name is invalid, 404 if not found
    """
    # Validate feature name
    validate_feature_name(feature_name)

    try:
        with get_db() as session:
            feature = (
                session.query(FeatureAccess)
                .filter(FeatureAccess.feature_name == feature_name)
                .first()
            )

            if not feature:
                raise HTTPException(status_code=404, detail="Feature not found")

            return FeatureAccessResponse(success=True, feature=feature.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feature access: {e}")
        raise HTTPException(status_code=500, detail="Failed to get feature access")


@router.put("/feature-access/{feature_name}", response_model=FeatureAccessResponse)
def update_feature_access(
    request: Request,
    feature_name: str,
    update: FeatureAccessUpdate,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> FeatureAccessResponse:
    """Update feature access setting.

    Requires admin privileges and CSRF token.
    Note: Rate limiting is applied at the application level via middleware.

    Args:
        feature_name: Feature identifier (e.g., "settings.database")
        update: Feature access update data

    Returns:
        FeatureAccessResponse with updated feature setting

    Raises:
        HTTPException: 400 if feature name is invalid, 403 if CSRF validation fails, 404 if not found
    """
    # Validate feature name
    validate_feature_name(feature_name)

    try:
        with get_db() as session:
            feature = (
                session.query(FeatureAccess)
                .filter(FeatureAccess.feature_name == feature_name)
                .first()
            )

            if not feature:
                raise HTTPException(status_code=404, detail="Feature not found")

            # Update admin_only flag
            old_value = feature.admin_only
            feature.admin_only = update.admin_only
            session.commit()

            # Clear cache to ensure updated settings take effect
            clear_feature_access_cache()

            # Audit logging for security events
            user_email = current_user.get("email", "unknown")
            logger.info(
                f"[AUDIT] Feature access changed by {_redact_email(user_email)}: "
                f"{feature_name} admin_only={old_value} -> {update.admin_only}"
            )

            return FeatureAccessResponse(
                success=True,
                message="Feature access updated successfully",
                feature=feature.to_dict(),
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feature access: {e}")
        raise HTTPException(status_code=500, detail="Failed to update feature access")


@router.post("/feature-access/reset", response_model=FeatureAccessResponse)
def reset_feature_access(
    request: Request,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> FeatureAccessResponse:
    """Reset all feature access settings to defaults.

    Requires admin privileges and CSRF token.
    Note: Rate limiting is applied at the application level via middleware.

    Resets Settings Features Only:
    - Database Settings: Admin Only
    - LLM Providers: Admin Only
    - External Services: Admin Only
    - External Tools: All Users
    - Appearance: All Users
    - API Tokens: All Users

    Note: This does not reset navigation features. Navigation features default
    to accessible by all users and are not modified by this operation.

    Returns:
        FeatureAccessResponse with success message

    Raises:
        HTTPException: 403 if CSRF validation fails, 500 on error
    """
    try:
        with get_db() as session:
            # Define default settings
            defaults = {
                "settings.database": True,
                "settings.llm_providers": True,
                "settings.external_services": True,
                "settings.external_tools": False,
                "settings.appearance": False,
                "settings.api_tokens": False,
            }

            # Update each feature
            for feature_name, admin_only in defaults.items():
                feature = (
                    session.query(FeatureAccess)
                    .filter(FeatureAccess.feature_name == feature_name)
                    .first()
                )

                if feature:
                    feature.admin_only = admin_only

            session.commit()

            # Clear cache to ensure updated settings take effect
            clear_feature_access_cache()

            # Audit logging for security events
            user_email = current_user.get("email", "unknown")
            logger.info(
                f"[AUDIT] Feature access settings reset to defaults by {_redact_email(user_email)}"
            )

            return FeatureAccessResponse(
                success=True, message="Feature access settings reset to defaults"
            )
    except Exception as e:
        logger.error(f"Error resetting feature access: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset feature access")


# ============================================================================
# SSRF Policy Endpoints (per-tool allow-list of endpoints)
# ============================================================================

# Canonical tool identifiers are uppercase alphanumeric + underscore (e.g. HTTP_REQUEST).
TOOL_ID_PATTERN = re.compile(r"^[A-Z0-9_]+$")


def _validate_tool_id(tool_id: str) -> None:
    """Validate a tool identifier, raising HTTP 400 if malformed."""
    if not TOOL_ID_PATTERN.match(tool_id or ""):
        raise HTTPException(
            status_code=400,
            detail="Invalid tool_id. Must match pattern: ^[A-Z0-9_]+$",
        )


class SSRFPolicyUpdate(BaseModel):
    """Request model for creating/updating a per-tool SSRF policy.

    ``allowed_ip_ranges`` holds allow-list entries. Each entry is an exact
    IP/host, optionally scoped to a port and/or path, e.g. ``10.0.0.1``,
    ``10.0.0.1:5005``, ``10.0.0.1/get``, ``10.0.0.1:5005/get``, a domain, or
    a full URL.
    """

    allowed_ip_ranges: List[str] = Field(default_factory=list)
    enabled: bool = True


class SSRFPolicyResponse(BaseModel):
    """Response model for SSRF policy operations."""

    success: bool
    policy: Optional[Dict[str, Any]] = None
    policies: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


@router.get("/ssrf-policies", response_model=SSRFPolicyResponse)
def list_ssrf_policies(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SSRFPolicyResponse:
    """List all per-tool SSRF allow-list policies. Requires admin."""
    try:
        return SSRFPolicyResponse(
            success=True, policies=ssrf_policy_service.list_policies()
        )
    except Exception as e:
        logger.error(f"Error listing SSRF policies: {e}")
        raise HTTPException(status_code=500, detail="Failed to list SSRF policies")


@router.get("/ssrf-policies/{tool_id}", response_model=SSRFPolicyResponse)
def get_ssrf_policy(
    tool_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SSRFPolicyResponse:
    """Get the SSRF policy for a specific tool. Requires admin."""
    _validate_tool_id(tool_id)
    try:
        policy = ssrf_policy_service.get_policy(tool_id)
        if policy is None:
            raise HTTPException(status_code=404, detail="Policy not found")
        return SSRFPolicyResponse(success=True, policy=policy)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SSRF policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to get SSRF policy")


@router.put("/ssrf-policies/{tool_id}", response_model=SSRFPolicyResponse)
def update_ssrf_policy(
    tool_id: str,
    update: SSRFPolicyUpdate,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> SSRFPolicyResponse:
    """Create or update the SSRF policy for a tool. Requires admin + CSRF.

    Body: ``{"allowed_ip_ranges": ["10.0.0.1", "10.0.0.1:5005/get"], "enabled": true}``.
    This replaces the full allow-list for the tool; only these entries (plus
    any added later via this API) will be permitted, i.e. fail-closed.
    """
    _validate_tool_id(tool_id)
    try:
        policy = ssrf_policy_service.upsert_policy(
            tool_id, update.allowed_ip_ranges, update.enabled
        )
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] SSRF policy updated by {_redact_email(user_email)}: "
            f"{tool_id} -> {policy['allowed_ip_ranges']}"
        )
        return SSRFPolicyResponse(
            success=True, policy=policy, message="Policy updated successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating SSRF policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to update SSRF policy")


@router.put("/ssrf-policies", response_model=SSRFPolicyResponse)
def bulk_update_ssrf_policies(
    payload: Dict[str, List[str]],
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> SSRFPolicyResponse:
    """Bulk create/update SSRF policies. Requires admin + CSRF.

    Body is a ``{tool_id: [ranges]}`` map, e.g.
    ``{"HTTP_REQUEST": ["1.2.3.4", "10.0.0.0/8"]}``.
    """
    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")
    for tool_id in payload:
        _validate_tool_id(tool_id)
    try:
        policies = ssrf_policy_service.bulk_upsert(payload)
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] SSRF policies bulk-updated by {_redact_email(user_email)}: "
            f"{sorted(payload.keys())}"
        )
        return SSRFPolicyResponse(
            success=True, policies=policies, message="Policies updated successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error bulk updating SSRF policies: {e}")
        raise HTTPException(status_code=500, detail="Failed to update SSRF policies")


@router.delete("/ssrf-policies/{tool_id}", response_model=SSRFPolicyResponse)
def delete_ssrf_policy(
    tool_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> SSRFPolicyResponse:
    """Delete the SSRF policy for a tool. Requires admin + CSRF."""
    _validate_tool_id(tool_id)
    try:
        deleted = ssrf_policy_service.delete_policy(tool_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Policy not found")
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] SSRF policy deleted by {_redact_email(user_email)}: {tool_id}"
        )
        return SSRFPolicyResponse(success=True, message="Policy deleted successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting SSRF policy: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete SSRF policy")


class SSRFPolicyIpRequest(BaseModel):
    """Request model for adding/removing a single IP/CIDR entry."""

    ip: str


@router.post("/ssrf-policies/{tool_id}/ips", response_model=SSRFPolicyResponse)
def add_ssrf_policy_ip(
    tool_id: str,
    body: SSRFPolicyIpRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> SSRFPolicyResponse:
    """Add a single blocked IP/CIDR to a tool's policy. Requires admin + CSRF.

    Creates the policy (seeded with the built-in defaults) if it does not
    exist yet. Body: ``{"ip": "1.2.3.4"}`` or ``{"ip": "10.0.0.0/8"}``.
    """
    _validate_tool_id(tool_id)
    try:
        policy = ssrf_policy_service.add_ip(tool_id, body.ip)
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] SSRF policy IP added by {_redact_email(user_email)}: "
            f"{tool_id} += {body.ip}"
        )
        return SSRFPolicyResponse(success=True, policy=policy, message="IP added")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding SSRF policy IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to add IP")


@router.delete("/ssrf-policies/{tool_id}/ips", response_model=SSRFPolicyResponse)
def remove_ssrf_policy_ip(
    tool_id: str,
    ip: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> SSRFPolicyResponse:
    """Remove a single blocked IP/CIDR from a tool's policy. Requires admin + CSRF.

    ``ip`` is passed as a query parameter (e.g. ``?ip=10.0.0.0/8``) since CIDR
    values contain a ``/`` and cannot be used as a path segment. Creates the
    policy (seeded with the built-in defaults minus ``ip``) if it does not
    exist yet, so a default entry can be explicitly removed on first use.
    """
    _validate_tool_id(tool_id)
    try:
        policy = ssrf_policy_service.remove_ip(tool_id, ip)
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] SSRF policy IP removed by {_redact_email(user_email)}: "
            f"{tool_id} -= {ip}"
        )
        return SSRFPolicyResponse(success=True, policy=policy, message="IP removed")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing SSRF policy IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove IP")


# ============================================================================
# User Management Endpoints
# ============================================================================


class UserListItem(BaseModel):
    """User list item model."""

    id: str
    email: Optional[str]
    name: Optional[str]
    role: str  # 'PENDING', 'USER', 'ADMIN', or 'SYSTEM'
    last_login_at: Optional[datetime]
    created_at: datetime
    group_count: int


class UsersListResponse(BaseModel):
    """Response model for users list."""

    users: List[UserListItem]
    total_count: int


class GroupInfo(BaseModel):
    """Group information model."""

    id: str
    name: str
    description: Optional[str]
    is_system: bool


class UserDetailResponse(BaseModel):
    """Response model for detailed user information."""

    id: str
    email: Optional[str]
    name: Optional[str]
    role: str  # 'PENDING', 'USER', 'ADMIN', or 'SYSTEM'
    last_login_at: Optional[datetime]
    created_at: datetime
    groups: List[GroupInfo]


class UserGroupUpdateRequest(BaseModel):
    """Request model for updating user group memberships."""

    group_ids: List[str]


class UserRoleUpdateRequest(BaseModel):
    """Request model for updating user role."""

    role: str  # 'PENDING', 'USER', 'ADMIN', or 'SYSTEM'


@router.get("/users", response_model=UsersListResponse)
def list_users(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    role: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(require_admin),
) -> UsersListResponse:
    """List all users with pagination and search.

    Requires admin privileges.
    Note: Rate limiting is applied at the application level via middleware.

    Args:
        limit: Maximum number of users to return (default 50)
        offset: Number of users to skip (default 0)
        search: Optional search query to filter by name, email, or role
        role: Optional role filter (PENDING, USER, or ADMIN)

    Returns:
        UsersListResponse with paginated user list (sorted by role: ADMIN, USER, PENDING)

    Raises:
        HTTPException: 500 on error
    """
    try:
        user_data, total_count = user_service.get_users_list(
            limit, offset, search, role
        )

        users = [
            UserListItem(
                id=user.id,
                email=user.email,
                name=user.name,
                role=role,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                group_count=group_count,
            )
            for user, role, group_count in user_data
        ]

        return UsersListResponse(users=users, total_count=total_count)
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user_detail(
    request: Request,
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
) -> UserDetailResponse:
    """Get detailed user information.

    Requires admin privileges.
    Note: Rate limiting is applied at the application level via middleware.

    Args:
        user_id: The user's ID

    Returns:
        UserDetailResponse with detailed user information

    Raises:
        HTTPException: 404 if user not found, 500 on error
    """
    try:
        user, role, groups = user_service.get_user_detail(user_id)

        group_info = [
            GroupInfo(
                id=g.id, name=g.name, description=g.description, is_system=g.is_system
            )
            for g in groups
        ]

        return UserDetailResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=role,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            groups=group_info,
        )
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting user detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user detail")


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    request: Request,
    user_id: str,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> None:
    """Delete a user permanently.

    Requires admin privileges and CSRF token.
    Note: Rate limiting is applied at the application level via middleware.

    Args:
        user_id: The user's ID to delete

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 403 if unauthorized or self-deletion attempt, 404 if user not found, 500 on error
    """
    try:
        user_service.delete_user(user_id, current_user)

        # Audit logging
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] User deleted via API by {_redact_email(user_email)}: user_id={user_id}"
        )
    except PermissionError as e:
        logger.error(str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")


@router.put("/users/{user_id}/groups")
def update_user_groups(
    request: Request,
    user_id: str,
    update: UserGroupUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> Dict[str, Any]:
    """Update user's group memberships.

    Requires admin privileges and CSRF token.
    Note: Rate limiting is applied at the application level via middleware.

    Args:
        user_id: The user's ID
        update: Group membership update data

    Returns:
        Success response

    Raises:
        HTTPException: 400 if invalid data, 403 if unauthorized, 404 if user not found, 500 on error
    """
    try:
        user_service.update_user_groups(user_id, update.group_ids, current_user)

        # Audit logging
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] User groups updated via API by {_redact_email(user_email)}: "
            f"user_id={user_id}, groups={len(update.group_ids)}"
        )

        return {"success": True, "message": "User groups updated successfully"}
    except PermissionError as e:
        logger.error(str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user groups: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user groups")


@router.put("/users/{user_id}/role")
def update_user_role(
    request: Request,
    user_id: str,
    update: UserRoleUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
    _csrf: None = Depends(verify_csrf_token),
) -> Dict[str, Any]:
    """Update user's role.

    Requires admin privileges and CSRF token.
    Note: Rate limiting is applied at the application level via middleware.

    Args:
        user_id: The user's ID
        update: Role update data

    Returns:
        Success response

    Raises:
        HTTPException: 400 if invalid role, 403 if unauthorized, 404 if user not found, 500 on error
    """
    try:
        user_service.update_user_role(user_id, update.role, current_user)

        # Audit logging
        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] User role updated via API by {_redact_email(user_email)}: "
            f"user_id={user_id}, new_role={update.role}"
        )

        return {"success": True, "message": "User role updated successfully"}
    except PermissionError as e:
        logger.error(str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.error(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user role")


# ---------------------------------------------------------------------------
# System External Services  (issue #217 — org-tier admin-managed services)
# ---------------------------------------------------------------------------


class SystemExternalServiceRequest(BaseModel):
    """Request body for creating/updating a system external service."""

    display_name: Optional[str] = Field(None, description="Human-readable label")
    description: Optional[str] = Field(None, description="Optional description")
    service_url: Optional[str] = Field(
        None, description="Base URL / endpoint of the service"
    )
    auth_type: str = Field(
        ExternalServiceAuthType.API_KEY_HEADER.value,
        description="How credentials are applied",
    )
    credentials: Optional[Dict[str, str]] = Field(
        None,
        description=(
            "Sensitive credential values to encrypt and store "
            "(e.g. {'api_key': '...'}). "
            "Omit to preserve existing credentials."
        ),
    )
    settings: Optional[Dict[str, Any]] = Field(
        None, description="Non-sensitive config (headers, timeout, region …)"
    )
    is_active: bool = Field(True, description="Whether the service is enabled")


class SystemExternalServiceResponse(BaseModel):
    """Safe (credential-free) representation of a system external service."""

    success: bool
    service: Optional[Dict[str, Any]] = None
    services: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


@router.get(
    "/settings/external-services",
    response_model=SystemExternalServiceResponse,
)
async def list_system_external_services(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SystemExternalServiceResponse:
    """List all system-level external service configurations (metadata only, no credentials).

    Accessible to all authenticated users so the UI can display which
    services are available at the system level.
    """
    try:
        services = SystemExternalServiceService.list_services()
        return SystemExternalServiceResponse(
            success=True,
            services=[
                SystemExternalServiceService.build_metadata_dict(s) for s in services
            ],
        )
    except Exception as exc:
        logger.error("Error listing system external services: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to list system external services"
        )


@router.get(
    "/settings/external-services/{service_name}",
    response_model=SystemExternalServiceResponse,
)
async def get_system_external_service(
    service_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> SystemExternalServiceResponse:
    """Get metadata for a single system external service (no credentials exposed).

    Accessible to all authenticated users.
    """
    svc = SystemExternalServiceService.get_service(service_name)
    if not svc:
        raise HTTPException(
            status_code=404,
            detail=f"System external service '{service_name}' not found",
        )
    return SystemExternalServiceResponse(
        success=True,
        service=SystemExternalServiceService.build_metadata_dict(svc),
    )


@router.put(
    "/settings/external-services/{service_name}",
    response_model=SystemExternalServiceResponse,
)
async def upsert_system_external_service(
    service_name: str,
    body: SystemExternalServiceRequest,
    _csrf: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SystemExternalServiceResponse:
    """Create or update a system external service configuration (admin only).

    Credentials supplied in ``credentials`` are encrypted before storage and
    are never returned by any API endpoint.
    """

    try:
        auth_type = ExternalServiceAuthType(body.auth_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid auth_type '{body.auth_type}'. "
                f"Valid values: {[e.value for e in ExternalServiceAuthType]}"
            ),
        )

    try:
        svc = SystemExternalServiceService.save_service(
            service_name=service_name,
            display_name=body.display_name,
            description=body.description,
            service_url=body.service_url,
            auth_type=auth_type,
            credentials=body.credentials,
            settings=body.settings,
            is_active=body.is_active,
        )
        return SystemExternalServiceResponse(
            success=True,
            service=SystemExternalServiceService.build_metadata_dict(svc),
            message=f"System external service '{service_name}' saved successfully",
        )
    except Exception as exc:
        logger.error("Error saving system external service '%s': %s", service_name, exc)
        raise HTTPException(
            status_code=500, detail="Failed to save system external service"
        )


@router.delete(
    "/settings/external-services/{service_name}",
    response_model=SystemExternalServiceResponse,
)
async def delete_system_external_service(
    service_name: str,
    _csrf: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SystemExternalServiceResponse:
    """Delete a system external service configuration (admin only)."""

    deleted = SystemExternalServiceService.delete_service(service_name)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"System external service '{service_name}' not found",
        )
    return SystemExternalServiceResponse(
        success=True,
        message=f"System external service '{service_name}' deleted successfully",
    )


# ── MCP Integration (Official Provider) Admin Endpoints ─────────────────


@router.get(
    "/settings/mcp-integrations",
    response_model=ListMcpIntegrationsResponse,
)
async def list_system_mcp_integrations(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ListMcpIntegrationsResponse:
    """List all system-wide MCP integration configs (accessible to all users)."""
    return await handle_list_system_integrations()


@router.put(
    "/settings/mcp-integrations/{provider}",
    response_model=SaveMcpIntegrationResponse,
)
async def save_system_mcp_integration(
    provider: str,
    request: SaveMcpIntegrationRequest,
    _csrf: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> SaveMcpIntegrationResponse:
    """Create or update a system-wide MCP integration (admin only)."""
    return await handle_save_system_integration(provider, request)


@router.delete(
    "/settings/mcp-integrations/{provider}",
    response_model=DeleteMcpIntegrationResponse,
)
async def delete_system_mcp_integration(
    provider: str,
    _csrf: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> DeleteMcpIntegrationResponse:
    """Delete a system-wide MCP integration (admin only)."""
    return await handle_delete_system_integration(provider)


# ── Group MCP Configurations ─────────────────────────────────────────────


class GroupMcpConfigRequest(BaseModel):
    """Request body for creating or updating a group MCP configuration."""

    service_name: str = Field(
        ..., description="Stable service identifier (e.g. mcp_preset_github)"
    )
    display_name: Optional[str] = Field(None, description="Human-readable label")
    description: Optional[str] = Field(None, description="Optional description")
    service_url: Optional[str] = Field(
        None, description="Base URL / endpoint (non-sensitive)"
    )
    auth_type: str = Field(
        "api_key_header", description="Credential application method"
    )
    api_key: Optional[str] = Field(
        None, description="Primary credential (will be encrypted)"
    )
    credentials: Optional[Dict[str, str]] = Field(
        None, description="Structured credentials dict (each value encrypted)"
    )
    settings: Optional[Dict[str, Any]] = Field(
        None, description="Non-sensitive configuration"
    )
    group_ids: List[str] = Field(
        default_factory=list, description="Groups to assign this config to"
    )
    is_active: bool = Field(True, description="Whether the config is enabled")


class GroupMcpConfigResponse(BaseModel):
    """Safe (credential-free) representation of a group MCP config."""

    success: bool
    config: Optional[Dict[str, Any]] = None
    configs: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None


@router.get("/settings/group-mcp-configs", response_model=GroupMcpConfigResponse)
async def list_group_mcp_configs(
    current_user: Dict[str, Any] = Depends(require_admin),
) -> GroupMcpConfigResponse:
    """List all group-scoped MCP configurations (admin only)."""
    try:
        configs = GroupExternalServiceService.list_configs()
        result = []
        for cfg in configs:
            group_ids = GroupExternalServiceService.get_group_ids_for_config(cfg.id)
            result.append(
                GroupExternalServiceService.build_metadata_dict(
                    cfg, group_ids=group_ids
                )
            )
        return GroupMcpConfigResponse(success=True, configs=result)
    except Exception as exc:
        logger.error("Error listing group MCP configs: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to list group MCP configurations"
        )


@router.post(
    "/settings/group-mcp-configs",
    response_model=GroupMcpConfigResponse,
    status_code=201,
)
async def create_group_mcp_config(
    body: GroupMcpConfigRequest,
    _csrf: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> GroupMcpConfigResponse:
    """Create a new group-scoped MCP configuration (admin only).

    Credentials supplied are encrypted before storage and never returned by any endpoint.
    """
    try:
        cfg = GroupExternalServiceService.create_config(
            service_name=body.service_name,
            display_name=body.display_name,
            description=body.description,
            service_url=body.service_url,
            auth_type=body.auth_type,
            api_key=body.api_key,
            credentials=body.credentials,
            settings=body.settings,
            group_ids=body.group_ids,
            is_active=body.is_active,
        )
        group_ids = GroupExternalServiceService.get_group_ids_for_config(cfg.id)
        return GroupMcpConfigResponse(
            success=True,
            config=GroupExternalServiceService.build_metadata_dict(
                cfg, group_ids=group_ids
            ),
            message="Group MCP configuration created successfully",
        )
    except Exception as exc:
        logger.error("Error creating group MCP config: %s", exc)
        raise HTTPException(
            status_code=500, detail="Failed to create group MCP configuration"
        )


@router.put(
    "/settings/group-mcp-configs/{config_id}", response_model=GroupMcpConfigResponse
)
async def update_group_mcp_config(
    config_id: str,
    body: GroupMcpConfigRequest,
    _csrf: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> GroupMcpConfigResponse:
    """Update an existing group-scoped MCP configuration (admin only)."""
    try:
        cfg = GroupExternalServiceService.update_config(
            config_id,
            display_name=body.display_name,
            description=body.description,
            service_url=body.service_url,
            auth_type=body.auth_type,
            api_key=body.api_key,
            credentials=body.credentials,
            settings=body.settings,
            group_ids=body.group_ids,
            is_active=body.is_active,
        )
        group_ids = GroupExternalServiceService.get_group_ids_for_config(cfg.id)
        return GroupMcpConfigResponse(
            success=True,
            config=GroupExternalServiceService.build_metadata_dict(
                cfg, group_ids=group_ids
            ),
            message="Group MCP configuration updated successfully",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Error updating group MCP config '%s': %s", config_id, exc)
        raise HTTPException(
            status_code=500, detail="Failed to update group MCP configuration"
        )


@router.delete(
    "/settings/group-mcp-configs/{config_id}", response_model=GroupMcpConfigResponse
)
async def delete_group_mcp_config(
    config_id: str,
    _csrf: None = Depends(verify_csrf_token),
    current_user: Dict[str, Any] = Depends(require_admin),
) -> GroupMcpConfigResponse:
    """Delete a group-scoped MCP configuration (admin only).

    Access is immediately revoked for all group members on the next workflow run.
    """
    deleted = GroupExternalServiceService.delete_config(config_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"Group MCP config '{config_id}' not found"
        )
    return GroupMcpConfigResponse(
        success=True, message="Group MCP configuration deleted successfully"
    )
