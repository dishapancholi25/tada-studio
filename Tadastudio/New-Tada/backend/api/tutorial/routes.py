"""Tutorial step override and progress API routes."""

import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ...models.evaluation import EvaluationRecommendation, EvaluationRun
from ...models.tutorial.progress import TutorialProgress
from ...models.tutorial.step_override import TutorialStepOverride
from ...services.authorization import require_workflow_access_by_id
from ...services.database import get_db
from ..auth.dependencies import get_current_user, require_admin
from .models import (
    OverridesResponse,
    SaveOverridesRequest,
    StepOverrideResponse,
    TutorialProgressResponse,
    UpdateProgressRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tutorial", tags=["tutorial"])


@router.get("/overrides/{tutorial_id}", response_model=OverridesResponse)
async def get_overrides(
    tutorial_id: str,
    _current_user: Dict[str, Any] = Depends(get_current_user),
) -> OverridesResponse:
    """Get all step overrides for a tutorial.

    Any authenticated user can read overrides so the tutorial renders correctly.

    Args:
        tutorial_id: Tutorial identifier (e.g. 'home', 'workflow-canvas')
        _current_user: Authenticated user claims

    Returns:
        OverridesResponse with list of step overrides
    """
    with get_db() as db:
        rows = (
            db.query(TutorialStepOverride)
            .filter(TutorialStepOverride.tutorial_id == tutorial_id)
            .order_by(TutorialStepOverride.step_index)
            .all()
        )

    return OverridesResponse(
        tutorial_id=tutorial_id,
        overrides=[
            StepOverrideResponse(
                step_index=r.step_index,
                breakpoint=r.breakpoint or "desktop",
                popover_offset_x=r.popover_offset_x,
                popover_offset_y=r.popover_offset_y,
                pointer_offset_x=r.pointer_offset_x,
                pointer_offset_y=r.pointer_offset_y,
                title=r.title,
                description=r.description,
                interaction_hint=r.interaction_hint,
            )
            for r in rows
        ],
    )


@router.put("/overrides/{tutorial_id}", response_model=OverridesResponse)
async def save_overrides(
    tutorial_id: str,
    request: SaveOverridesRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
) -> OverridesResponse:
    """Save step overrides for a tutorial (admin only).

    Upserts overrides — existing rows for the same tutorial_id + step_index
    are updated; new ones are created. Overrides where all offsets are zero
    and all text fields are null are deleted to keep the table clean.

    Args:
        tutorial_id: Tutorial identifier
        request: Bulk overrides payload
        current_user: Authenticated admin user claims

    Returns:
        OverridesResponse with saved overrides

    Raises:
        HTTPException: 403 if user is not admin
    """
    admin_email = current_user.get("email", "unknown")

    with get_db() as db:
        for override in request.overrides:
            is_empty = (
                override.popover_offset_x == 0
                and override.popover_offset_y == 0
                and override.pointer_offset_x == 0
                and override.pointer_offset_y == 0
                and override.title is None
                and override.description is None
                and override.interaction_hint is None
            )

            bp = override.breakpoint or "desktop"

            existing = (
                db.query(TutorialStepOverride)
                .filter(
                    TutorialStepOverride.tutorial_id == tutorial_id,
                    TutorialStepOverride.step_index == override.step_index,
                    TutorialStepOverride.breakpoint == bp,
                )
                .first()
            )

            if is_empty:
                if existing:
                    db.delete(existing)
                continue

            if existing:
                existing.popover_offset_x = override.popover_offset_x
                existing.popover_offset_y = override.popover_offset_y
                existing.pointer_offset_x = override.pointer_offset_x
                existing.pointer_offset_y = override.pointer_offset_y
                existing.title = override.title
                existing.description = override.description
                existing.interaction_hint = override.interaction_hint
                existing.updated_by = admin_email
            else:
                db.add(
                    TutorialStepOverride(
                        tutorial_id=tutorial_id,
                        step_index=override.step_index,
                        breakpoint=bp,
                        popover_offset_x=override.popover_offset_x,
                        popover_offset_y=override.popover_offset_y,
                        pointer_offset_x=override.pointer_offset_x,
                        pointer_offset_y=override.pointer_offset_y,
                        title=override.title,
                        description=override.description,
                        interaction_hint=override.interaction_hint,
                        updated_by=admin_email,
                    )
                )

        db.commit()

        # Re-read to return current state
        rows = (
            db.query(TutorialStepOverride)
            .filter(TutorialStepOverride.tutorial_id == tutorial_id)
            .order_by(TutorialStepOverride.step_index)
            .all()
        )

    logger.info("Admin %s saved tutorial overrides for '%s'", admin_email, tutorial_id)

    return OverridesResponse(
        tutorial_id=tutorial_id,
        overrides=[
            StepOverrideResponse(
                step_index=r.step_index,
                breakpoint=r.breakpoint or "desktop",
                popover_offset_x=r.popover_offset_x,
                popover_offset_y=r.popover_offset_y,
                pointer_offset_x=r.pointer_offset_x,
                pointer_offset_y=r.pointer_offset_y,
                title=r.title,
                description=r.description,
                interaction_hint=r.interaction_hint,
            )
            for r in rows
        ],
    )


# ── Tutorial progress endpoints ──────────────────────────────────────


def _get_user_id(current_user: Dict[str, Any]) -> str:
    """Extract the stable user identifier from JWT claims."""
    uid = current_user.get("sub") or current_user.get("email")
    if not uid:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Unable to identify user")
    return uid


@router.get("/progress", response_model=TutorialProgressResponse)
async def get_progress(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> TutorialProgressResponse:
    """Get the current user's tutorial progress."""
    user_id = _get_user_id(current_user)
    with get_db() as db:
        row = (
            db.query(TutorialProgress)
            .filter(TutorialProgress.user_id == user_id)
            .first()
        )

    if not row:
        return TutorialProgressResponse()

    return TutorialProgressResponse(
        completed_tutorials=row.completed_tutorials or {},
        last_step_reached=row.last_step_reached or {},
    )


@router.put("/progress", response_model=TutorialProgressResponse)
async def update_progress(
    request: UpdateProgressRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> TutorialProgressResponse:
    """Update the current user's tutorial progress (merge semantics)."""
    user_id = _get_user_id(current_user)

    with get_db() as db:
        row = (
            db.query(TutorialProgress)
            .filter(TutorialProgress.user_id == user_id)
            .first()
        )
        if not row:
            row = TutorialProgress(
                user_id=user_id, completed_tutorials={}, last_step_reached={}
            )
            db.add(row)

        if request.completed_tutorials is not None:
            if request.replace:
                row.completed_tutorials = request.completed_tutorials
            else:
                row.completed_tutorials = {
                    **(row.completed_tutorials or {}),
                    **request.completed_tutorials,
                }

        if request.last_step_reached is not None:
            if request.replace:
                row.last_step_reached = request.last_step_reached
            else:
                row.last_step_reached = {
                    **(row.last_step_reached or {}),
                    **request.last_step_reached,
                }

        db.commit()
        db.refresh(row)

    return TutorialProgressResponse(
        completed_tutorials=row.completed_tutorials or {},
        last_step_reached=row.last_step_reached or {},
    )


# ── Tutorial recommendation seeding ─────────────────────────────────


class SeedRecommendationRequest(BaseModel):
    """Request to ensure a prompt_edit recommendation exists for a tutorial run."""

    run_id: str = Field(..., description="Evaluation run ID")
    target_node_id: str = Field(
        ..., description="Node ID to target with the recommendation"
    )
    current_prompt: str = Field(..., description="Current system prompt of the node")


TUTORIAL_IMPROVED_PROMPT = (
    "You are a helpful, concise assistant. Answer questions directly and accurately. "
    "Keep responses brief and to the point. When asked to summarize, provide exactly "
    "the number of sentences requested. When asked to translate, provide only the "
    "translation without additional commentary."
)


@router.post("/seed-recommendation")
async def seed_recommendation(
    request: SeedRecommendationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Ensure a prompt_edit recommendation exists for a tutorial evaluation run.

    If the run already has recommendations, returns the first one.
    Otherwise, creates a seeded prompt_edit recommendation.
    """
    with get_db() as db:
        run = db.query(EvaluationRun).filter(EvaluationRun.id == request.run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        workflow_id = str(run.workflow_id) if run.workflow_id else None
        if (
            not workflow_id
            and run.graph_definition
            and run.graph_definition.workflow_id
        ):
            workflow_id = str(run.graph_definition.workflow_id)
        if not workflow_id:
            raise HTTPException(status_code=403, detail="Not authorized for this run")
        require_workflow_access_by_id(current_user, workflow_id)

        existing = (
            db.query(EvaluationRecommendation)
            .filter(EvaluationRecommendation.run_id == request.run_id)
            .all()
        )
        if existing:
            return {"seeded": False, "recommendation_count": len(existing)}

        rec = EvaluationRecommendation(
            id=str(uuid.uuid4()),
            run_id=request.run_id,
            target_node_id=request.target_node_id,
            recommendation_type="prompt_edit",
            risk_tier="low",
            title="Improve system prompt for concise, accurate responses",
            rationale=(
                "The current system prompt instructs the agent to respond with long, "
                "imaginative narratives and embellish answers with fictional details. "
                "This directly conflicts with the test cases which expect concise, "
                "factual answers. The quality scores are low because the agent's verbose, "
                "creative responses don't match the expected outputs."
            ),
            expected_impact={
                "cost_delta_pct": -40,
                "quality_delta": 35,
                "latency_delta_ms": -500,
            },
            proposed_change={
                "agent_config": {
                    "system_prompt": TUTORIAL_IMPROVED_PROMPT,
                    "llm_config": {"temperature": 0.3},
                },
            },
            status="pending",
        )
        db.add(rec)
        db.commit()

    return {"seeded": True, "recommendation_count": 1}
