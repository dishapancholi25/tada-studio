"""API routes for guardrail policy metrics.

Provides an endpoint to retrieve aggregated violation and feedback
metrics for a specific guardrail policy.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.models.guardrails.violation_event import GuardrailViolationEvent
from backend.models.guardrails.violation_feedback import GuardrailViolationFeedback
from backend.services.database import get_db
from backend.services.guardrails.policy_service import GuardrailPolicyService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/guardrails/policies/{policy_id}",
    tags=["guardrail-metrics"],
    dependencies=[Depends(require_active_user)],
)


def _get_user_id(current_user: Dict[str, Any]) -> str:
    return current_user.get("sub") or current_user.get("email", "")


def _is_admin(current_user: Dict[str, Any]) -> bool:
    return bool(current_user.get("is_admin"))


VALID_WINDOWS = {"7d", "30d", "all"}


@router.get("/metrics")
async def get_policy_metrics(
    policy_id: str,
    window: str = Query("7d"),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return aggregated violation and feedback metrics for a policy."""
    if window not in VALID_WINDOWS:
        raise HTTPException(status_code=400, detail=f"Invalid window. Must be one of: {', '.join(sorted(VALID_WINDOWS))}")

    user_id = _get_user_id(current_user)

    policy = GuardrailPolicyService.get_policy(
        policy_id=policy_id,
        user_id=user_id,
        is_admin=_is_admin(current_user),
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    cutoff = None
    if window == "7d":
        cutoff = datetime.utcnow() - timedelta(days=7)
    elif window == "30d":
        cutoff = datetime.utcnow() - timedelta(days=30)

    with get_db() as db:
        # Base query for violations belonging to this policy
        base = db.query(GuardrailViolationEvent).filter(
            GuardrailViolationEvent.policy_id == policy_id,
        )
        if cutoff is not None:
            base = base.filter(GuardrailViolationEvent.created_at >= cutoff)

        total_violations = base.count()

        block_count = base.filter(GuardrailViolationEvent.severity == "block").count()
        warn_count = base.filter(GuardrailViolationEvent.severity == "warn").count()

        block_rate = block_count / total_violations if total_violations else 0.0
        warn_rate = warn_count / total_violations if total_violations else 0.0

        # Top-5 most triggered rules
        top_rules_rows = (
            db.query(
                GuardrailViolationEvent.rule_name,
                func.count(GuardrailViolationEvent.id).label("count"),
            )
            .filter(GuardrailViolationEvent.policy_id == policy_id)
        )
        if cutoff is not None:
            top_rules_rows = top_rules_rows.filter(GuardrailViolationEvent.created_at >= cutoff)
        top_rules_rows = (
            top_rules_rows
            .group_by(GuardrailViolationEvent.rule_name)
            .order_by(func.count(GuardrailViolationEvent.id).desc())
            .limit(5)
            .all()
        )
        top_rules = [{"rule_name": rn, "count": cnt} for rn, cnt in top_rules_rows]

        # False positive count — feedback with rating == "negative" on events for this policy
        event_ids_subq = (
            db.query(GuardrailViolationEvent.id)
            .filter(GuardrailViolationEvent.policy_id == policy_id)
        )
        if cutoff is not None:
            event_ids_subq = event_ids_subq.filter(GuardrailViolationEvent.created_at >= cutoff)
        event_ids_subq = event_ids_subq.subquery()

        false_positive_count = (
            db.query(func.count(GuardrailViolationFeedback.id))
            .filter(
                GuardrailViolationFeedback.violation_event_id.in_(
                    db.query(event_ids_subq.c.id)
                ),
                GuardrailViolationFeedback.rating == "negative",
            )
            .scalar()
        ) or 0

        false_positive_rate = false_positive_count / total_violations if total_violations else 0.0

        # Per-rule feedback breakdown
        per_rule_rows = (
            db.query(
                GuardrailViolationEvent.rule_name,
                GuardrailViolationFeedback.rating,
                func.count(GuardrailViolationFeedback.id).label("cnt"),
            )
            .join(
                GuardrailViolationFeedback,
                GuardrailViolationFeedback.violation_event_id == GuardrailViolationEvent.id,
            )
            .filter(GuardrailViolationEvent.policy_id == policy_id)
        )
        if cutoff is not None:
            per_rule_rows = per_rule_rows.filter(GuardrailViolationEvent.created_at >= cutoff)
        per_rule_rows = (
            per_rule_rows
            .group_by(GuardrailViolationEvent.rule_name, GuardrailViolationFeedback.rating)
            .all()
        )

        # Pivot into {rule_name, positive_count, negative_count}
        rule_feedback_map: Dict[str, Dict[str, int]] = {}
        for rule_name, rating, cnt in per_rule_rows:
            if rule_name not in rule_feedback_map:
                rule_feedback_map[rule_name] = {"positive_count": 0, "negative_count": 0}
            if rating == "positive":
                rule_feedback_map[rule_name]["positive_count"] = cnt
            elif rating == "negative":
                rule_feedback_map[rule_name]["negative_count"] = cnt

        per_rule_feedback = [
            {"rule_name": rn, **counts}
            for rn, counts in rule_feedback_map.items()
        ]

    return {
        "success": True,
        "total_violations": total_violations,
        "block_count": block_count,
        "warn_count": warn_count,
        "block_rate": round(block_rate, 4),
        "warn_rate": round(warn_rate, 4),
        "false_positive_count": false_positive_count,
        "false_positive_rate": round(false_positive_rate, 4),
        "top_rules": top_rules,
        "per_rule_feedback": per_rule_feedback,
    }
