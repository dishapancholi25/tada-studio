"""API routes for guardrail policy version history.

Provides endpoints to list versions, view version details, and rollback
a policy to a previous version.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.models.guardrails.guardrail_policy import GuardrailPolicy
from backend.models.guardrails.policy_version import GuardrailPolicyVersion
from backend.services.database import get_db
from backend.services.guardrails.policy_service import GuardrailPolicyService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/guardrails/policies/{policy_id}/versions",
    tags=["guardrail-versions"],
    dependencies=[Depends(require_active_user)],
)


def _get_user_id(current_user: Dict[str, Any]) -> str:
    return current_user.get("sub") or current_user.get("email", "")


def _is_admin(current_user: Dict[str, Any]) -> bool:
    return bool(current_user.get("is_admin"))


@router.get("/")
async def list_versions(
    policy_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all versions of a guardrail policy."""
    user_id = _get_user_id(current_user)

    # Access check via existing service
    policy = GuardrailPolicyService.get_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    current_version = policy.get("current_version") or policy.get("version", 1)

    with get_db() as db:
        versions = (
            db.query(GuardrailPolicyVersion)
            .filter(GuardrailPolicyVersion.policy_id == policy_id)
            .order_by(GuardrailPolicyVersion.version.desc())
            .all()
        )
        result = []
        for v in versions:
            d = v.to_dict()
            d["is_current"] = v.version == current_version
            # Exclude config_snapshot from list response
            d.pop("config_snapshot", None)
            d.pop("policy_id", None)
            result.append(d)

    return {"success": True, "versions": result}


@router.get("/{version_id}")
async def get_version(
    policy_id: str,
    version_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get full details of a specific policy version."""
    user_id = _get_user_id(current_user)

    # Access check
    policy = GuardrailPolicyService.get_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    current_version = policy.get("current_version") or policy.get("version", 1)

    with get_db() as db:
        version = (
            db.query(GuardrailPolicyVersion)
            .filter(
                GuardrailPolicyVersion.id == version_id,
                GuardrailPolicyVersion.policy_id == policy_id,
            )
            .first()
        )
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")

        d = version.to_dict()
        d["is_current"] = version.version == current_version
        d.pop("policy_id", None)

    return {"success": True, "version": d}


@router.post("/{version_id}/rollback")
async def rollback_version(
    policy_id: str,
    version_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Rollback a policy to a previous version's configuration.

    Creates a new version record with the restored config and updates
    the policy's active configuration.
    """
    user_id = _get_user_id(current_user)
    is_admin = _is_admin(current_user)

    with get_db() as db:
        # Lock the policy row for update
        policy = (
            db.query(GuardrailPolicy)
            .filter(GuardrailPolicy.id == policy_id)
            .with_for_update()
            .first()
        )
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        if not is_admin and policy.created_by != user_id:
            raise HTTPException(status_code=403, detail="You do not own this policy")

        # Fetch the target version
        target_version = (
            db.query(GuardrailPolicyVersion)
            .filter(
                GuardrailPolicyVersion.id == version_id,
                GuardrailPolicyVersion.policy_id == policy_id,
            )
            .first()
        )
        if not target_version:
            raise HTTPException(status_code=404, detail="Version not found")

        # Create a new version record for the rollback
        new_version_number = (getattr(policy, "version_count", None) or 0) + 1
        rollback_record = GuardrailPolicyVersion(
            policy_id=policy_id,
            version=new_version_number,
            config_snapshot=target_version.config_snapshot,
            changed_by=user_id,
            change_summary=f"Restored from v{target_version.version}",
        )
        db.add(rollback_record)

        # Update the policy config
        policy.config = target_version.config_snapshot

        # Increment version tracking columns
        if hasattr(policy, "version_count"):
            policy.version_count = new_version_number
        if hasattr(policy, "current_version"):
            policy.current_version = new_version_number
        policy.version = (policy.version or 1) + 1

        db.flush()

        result = policy.to_dict()

    logger.info(
        "[GUARDRAILS] Policy rolled back: id=%s to version %s (new v%s)",
        policy_id,
        target_version.version,
        new_version_number,
    )
    return {"success": True, "policy": result, "new_version_number": new_version_number}
