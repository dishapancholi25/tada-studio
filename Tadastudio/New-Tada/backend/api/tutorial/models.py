"""Pydantic request/response models for tutorial API."""

from typing import List, Optional

from pydantic import BaseModel, Field


class StepOverridePayload(BaseModel):
    """A single step override sent by the admin UI."""

    step_index: int = Field(..., ge=0, description="Zero-based step index")
    breakpoint: str = Field(
        "desktop", description="Nav layout breakpoint: 'desktop' or 'compact'"
    )
    popover_offset_x: int = Field(0, description="Horizontal pixel offset for popover")
    popover_offset_y: int = Field(0, description="Vertical pixel offset for popover")
    pointer_offset_x: int = Field(0, description="Horizontal pixel offset for pointer")
    pointer_offset_y: int = Field(0, description="Vertical pixel offset for pointer")
    title: Optional[str] = Field(None, description="Title override (null = default)")
    description: Optional[str] = Field(
        None, description="Description override (null = default)"
    )
    interaction_hint: Optional[str] = Field(
        None, description="Interaction hint override (null = default)"
    )


class SaveOverridesRequest(BaseModel):
    """Bulk save overrides for a tutorial."""

    overrides: List[StepOverridePayload] = Field(
        ..., description="List of step overrides to save"
    )


class StepOverrideResponse(BaseModel):
    """A single step override returned to the frontend."""

    step_index: int
    breakpoint: str = "desktop"
    popover_offset_x: int
    popover_offset_y: int
    pointer_offset_x: int
    pointer_offset_y: int
    title: Optional[str] = None
    description: Optional[str] = None
    interaction_hint: Optional[str] = None


class OverridesResponse(BaseModel):
    """Response containing all overrides for a tutorial."""

    success: bool = True
    tutorial_id: str
    overrides: List[StepOverrideResponse]


# ── Tutorial progress models ─────────────────────────────────────────


class TutorialProgressResponse(BaseModel):
    """Current tutorial progress for the authenticated user."""

    success: bool = True
    completed_tutorials: dict = Field(
        default_factory=dict, description="Map of tutorial_id -> true"
    )
    last_step_reached: dict = Field(
        default_factory=dict, description="Map of tutorial_id -> step index"
    )


class UpdateProgressRequest(BaseModel):
    """Update tutorial progress for the authenticated user."""

    completed_tutorials: Optional[dict] = Field(
        None, description="Map of tutorial_id -> true"
    )
    last_step_reached: Optional[dict] = Field(
        None, description="Map of tutorial_id -> step index"
    )
    replace: bool = Field(False, description="If true, replace instead of merge")
