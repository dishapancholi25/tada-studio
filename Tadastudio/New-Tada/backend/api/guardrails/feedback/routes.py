"""API routes for guardrail violation feedback.

Provides endpoints to submit, update, and remove user feedback on
guardrail violation events.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, field_validator

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.models.guardrails.violation_event import GuardrailViolationEvent
from backend.models.guardrails.violation_feedback import GuardrailViolationFeedback
from backend.services.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/guardrails/violations/{violation_id}/feedback",
    tags=["guardrail-feedback"],
    dependencies=[Depends(require_active_user)],
)


class FeedbackRequest(BaseModel):
    """Request body for submitting violation feedback."""

    rating: str

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: str) -> str:
        if v not in {"positive", "negative"}:
            raise ValueError("rating must be 'positive' or 'negative'")
        return v


def _get_user_id(current_user: Dict[str, Any]) -> str:
    return current_user.get("sub") or current_user.get("email", "")


def _is_admin(current_user: Dict[str, Any]) -> bool:
    return bool(current_user.get("is_admin"))


@router.post("/")
async def upsert_feedback(
    violation_id: str,
    request: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> JSONResponse:
    """Submit or update feedback on a violation event."""
    user_id = _get_user_id(current_user)
    is_admin = _is_admin(current_user)

    with get_db() as db:
        violation = (
            db.query(GuardrailViolationEvent)
            .filter(GuardrailViolationEvent.id == violation_id)
            .first()
        )
        if not violation:
            raise HTTPException(status_code=404, detail="Violation event not found")

        if not is_admin and violation.user_id is not None and violation.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        existing = (
            db.query(GuardrailViolationFeedback)
            .filter(
                GuardrailViolationFeedback.violation_event_id == violation_id,
                GuardrailViolationFeedback.user_id == user_id,
            )
            .first()
        )

        if existing:
            existing.rating = request.rating
            db.flush()
            return JSONResponse(status_code=200, content={"success": True, "feedback": existing.to_dict()})

        record = GuardrailViolationFeedback(
            violation_event_id=violation_id,
            user_id=user_id,
            rating=request.rating,
        )
        db.add(record)
        db.flush()
        return JSONResponse(status_code=201, content={"success": True, "feedback": record.to_dict()})


@router.delete("/")
async def delete_feedback(
    violation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Remove the current user's feedback on a violation event."""
    user_id = _get_user_id(current_user)

    with get_db() as db:
        record = (
            db.query(GuardrailViolationFeedback)
            .filter(
                GuardrailViolationFeedback.violation_event_id == violation_id,
                GuardrailViolationFeedback.user_id == user_id,
            )
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="No feedback found for this user")

        db.delete(record)

    return Response(status_code=204)
