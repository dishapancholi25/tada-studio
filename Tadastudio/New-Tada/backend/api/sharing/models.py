"""Request and response models for sharing API endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field


class AddMemberRequest(BaseModel):
    """Request to add a user as a workflow member."""

    user_id: str = Field(..., min_length=1, description="User ID to add")
    role: str = Field(
        ...,
        pattern="^(editor|viewer)$",
        description="Role to assign (editor or viewer)",
    )


class UpdateMemberRoleRequest(BaseModel):
    """Request to update a member's role."""

    role: str = Field(
        ..., pattern="^(editor|viewer)$", description="New role (editor or viewer)"
    )


class WorkflowMemberResponse(BaseModel):
    """Response model for a single workflow member."""

    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    role: str
    is_owner: bool = False


class WorkflowMembersResponse(BaseModel):
    """Response model for listing workflow members."""

    members: List[WorkflowMemberResponse]
    workflow_id: str
    can_manage: bool = False
