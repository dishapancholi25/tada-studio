"""API routes for guardrail violation events.

Provides endpoints to list violations, view violation details, and
get an admin summary of violations across the system.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func

from backend.api.auth.dependencies import get_current_user, require_active_user, require_admin
from backend.models.guardrails.guardrail_policy import GuardrailPolicy
from backend.models.guardrails.violation_event import GuardrailViolationEvent
from backend.models.guardrails.violation_feedback import GuardrailViolationFeedback
from backend.models.workflows.workflow import Workflow
from backend.services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/guardrails/violations",
    tags=["guardrail-violations"],
    dependencies=[Depends(require_active_user)],
)


def _get_user_id(current_user: Dict[str, Any]) -> str:
    return current_user.get("sub") or current_user.get("email", "")


def _is_admin(current_user: Dict[str, Any]) -> bool:
    return bool(current_user.get("is_admin"))


def _enrich_violations(db, violations: List[Dict[str, Any]]) -> None:
    """Fill in missing workflow_name and policy_name from related tables."""
    # Collect IDs that need lookup
    wf_ids = {v["workflow_id"] for v in violations if v.get("workflow_id") and not v.get("workflow_name")}
    pol_ids = {v["policy_id"] for v in violations if v.get("policy_id") and not v.get("policy_name")}

    wf_names: Dict[str, str] = {}
    pol_names: Dict[str, str] = {}

    if wf_ids:
        rows = db.query(Workflow.id, Workflow.name).filter(Workflow.id.in_(wf_ids)).all()
        wf_names = {str(r.id): r.name for r in rows}

    if pol_ids:
        rows = db.query(GuardrailPolicy.id, GuardrailPolicy.name).filter(GuardrailPolicy.id.in_(pol_ids)).all()
        pol_names = {str(r.id): r.name for r in rows}

    for v in violations:
        if not v.get("workflow_name") and v.get("workflow_id"):
            v["workflow_name"] = wf_names.get(v["workflow_id"])
        if not v.get("policy_name") and v.get("policy_id"):
            v["policy_name"] = pol_names.get(v["policy_id"])


def _get_feedback_summary(db, violation_event_id: str) -> Dict[str, int]:
    """Compute positive/negative feedback counts for a violation event."""
    rows = (
        db.query(GuardrailViolationFeedback.rating, func.count(GuardrailViolationFeedback.id))
        .filter(GuardrailViolationFeedback.violation_event_id == violation_event_id)
        .group_by(GuardrailViolationFeedback.rating)
        .all()
    )
    summary = {"positive": 0, "negative": 0}
    for rating, count in rows:
        if rating in summary:
            summary[rating] = count
    return summary


@router.get("/summary", dependencies=[Depends(require_admin)])
async def get_violations_summary(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Admin summary of guardrail violations and policy enforcement modes."""
    with get_db() as db:
        # Enforcement breakdown from policies
        policies = db.query(GuardrailPolicy).all()
        enforce_count = 0
        audit_count = 0
        disabled_count = 0
        compulsory_count = 0
        for policy in policies:
            mode = (policy.config or {}).get("enforcement_mode", "enforce")
            if mode == "enforce":
                enforce_count += 1
            elif mode == "audit":
                audit_count += 1
            elif mode == "disabled":
                disabled_count += 1
            if getattr(policy, "is_compulsory", False):
                compulsory_count += 1

        # Violations in last 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)
        total_violations_24h = (
            db.query(func.count(GuardrailViolationEvent.id))
            .filter(GuardrailViolationEvent.created_at >= cutoff)
            .scalar()
        )

        # Most triggered rules (top 5)
        most_triggered_rules = (
            db.query(
                GuardrailViolationEvent.rule_name,
                func.count(GuardrailViolationEvent.id).label("count"),
            )
            .group_by(GuardrailViolationEvent.rule_name)
            .order_by(func.count(GuardrailViolationEvent.id).desc())
            .limit(5)
            .all()
        )

    return {
        "success": True,
        "summary": {
            "enforcement_breakdown": {
                "enforce": enforce_count,
                "audit": audit_count,
                "disabled": disabled_count,
                "compulsory": compulsory_count,
            },
            "total_violations_24h": total_violations_24h,
            "most_triggered_rules": [
                {"rule_name": rule_name, "count": count}
                for rule_name, count in most_triggered_rules
            ],
        },
    }


@router.get("/")
async def list_violations(
    policy_id: Optional[str] = Query(None),
    rule_name: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    workflow_id: Optional[str] = Query(None),
    agent_node_id: Optional[str] = Query(None),
    from_time: Optional[str] = Query(None),
    to_time: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List guardrail violations with optional filters."""
    user_id = _get_user_id(current_user)
    is_admin = _is_admin(current_user)

    with get_db() as db:
        query = db.query(GuardrailViolationEvent)

        if not is_admin:
            query = query.filter(GuardrailViolationEvent.user_id == user_id)

        if policy_id:
            query = query.filter(GuardrailViolationEvent.policy_id == policy_id)
        if rule_name:
            query = query.filter(GuardrailViolationEvent.rule_name == rule_name)
        if severity:
            query = query.filter(GuardrailViolationEvent.severity == severity)
        if workflow_id:
            query = query.filter(GuardrailViolationEvent.workflow_id == workflow_id)
        if agent_node_id:
            query = query.filter(GuardrailViolationEvent.agent_node_id == agent_node_id)
        if from_time:
            query = query.filter(GuardrailViolationEvent.created_at >= datetime.fromisoformat(from_time))
        if to_time:
            query = query.filter(GuardrailViolationEvent.created_at <= datetime.fromisoformat(to_time))

        total = query.count()

        events = (
            query.order_by(GuardrailViolationEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        violations = []
        for event in events:
            d = event.to_dict()
            d["feedback_summary"] = _get_feedback_summary(db, event.id)
            violations.append(d)

        _enrich_violations(db, violations)

    return {
        "success": True,
        "violations": violations,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{violation_id}")
async def get_violation(
    violation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get a single violation event with feedback details."""
    user_id = _get_user_id(current_user)
    is_admin = _is_admin(current_user)

    with get_db() as db:
        event = (
            db.query(GuardrailViolationEvent)
            .filter(GuardrailViolationEvent.id == violation_id)
            .first()
        )
        if not event:
            raise HTTPException(status_code=404, detail="Violation not found")

        if not is_admin and event.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this violation")

        d = event.to_dict()
        d["feedback_summary"] = _get_feedback_summary(db, event.id)
        _enrich_violations(db, [d])

        # Current user's feedback
        user_feedback = (
            db.query(GuardrailViolationFeedback)
            .filter(
                GuardrailViolationFeedback.violation_event_id == violation_id,
                GuardrailViolationFeedback.user_id == user_id,
            )
            .first()
        )
        d["user_feedback"] = user_feedback.rating if user_feedback else None

    return {"success": True, "violation": d}
