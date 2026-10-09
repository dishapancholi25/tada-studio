"""Pydantic request/response models for guardrail policies API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreatePolicyRequest(BaseModel):
    """Request to create a new guardrail policy."""

    name: str = Field(..., description="Display name for the policy")
    description: Optional[str] = Field(None, description="Purpose / documentation")
    config: Dict[str, Any] = Field(..., description="Full GuardrailsConfig object")
    scope: str = Field("user", description="Policy scope: global, organization, or user")
    is_compulsory: bool = Field(False, description="Admin-enforced, cannot be disabled")
    applies_to: List[str] = Field(
        default_factory=list,
        description="Target types: agent, model, tool, workflow",
    )
    visible_to_groups: List[str] = Field(
        default_factory=list,
        description="Group-based visibility: [] = private, ['__all__'] = everyone, ['grp'] = specific groups",
    )
    # Legacy alias accepted for backwards compat
    shared_with: List[str] = Field(default_factory=list, description="Deprecated: use visible_to_groups")
    is_template: bool = Field(False, description="Available as a starting template")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")


class UpdatePolicyRequest(BaseModel):
    """Request to update an existing guardrail policy."""

    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    scope: Optional[str] = None
    is_compulsory: Optional[bool] = None
    applies_to: Optional[List[str]] = None
    visible_to_groups: Optional[List[str]] = None
    # Legacy alias
    shared_with: Optional[List[str]] = None
    is_template: Optional[bool] = None
    tags: Optional[List[str]] = None
    change_summary: Optional[str] = None


class UpdateVisibilityRequest(BaseModel):
    """Request to update policy group visibility (mirrors collections pattern)."""

    visible_to_groups: List[str] = Field(
        ...,
        description="Group names: [] = private, ['__all__'] = everyone, ['grp'] = specific groups",
    )


class SharePolicyRequest(BaseModel):
    """Legacy: Request to share a policy with users/groups."""

    share_with: List[str] = Field(..., description="Group names to share with")


class CreateAssignmentRequest(BaseModel):
    """Request to assign a policy to a target."""

    policy_id: str = Field(..., description="ID of the guardrail policy")
    target_type: str = Field(..., description="Target type: agent_node, model, tool, workflow")
    target_id: str = Field(..., description="ID of the target entity")
    workflow_id: Optional[str] = Field(None, description="Context workflow ID")
    priority: int = Field(0, description="Resolution priority (lower = higher)")
    override_mode: str = Field("merge", description="How to combine: merge, replace, append")


class UpdateAssignmentRequest(BaseModel):
    """Request to update an existing policy assignment."""

    priority: Optional[int] = Field(None, description="Resolution priority (lower = higher)")
    override_mode: Optional[str] = Field(None, description="How to combine: merge, replace, append")


class SetCompulsoryRequest(BaseModel):
    """Request to set a policy as compulsory."""

    policy_id: str = Field(..., description="ID of the policy to make compulsory")
    is_compulsory: bool = Field(True, description="Whether the policy is compulsory")


# Phase 3: Violations


class ViolationFeedbackRequest(BaseModel):
    """Request to submit feedback on a violation."""

    rating: str = Field(..., description="positive (legitimate) or negative (false positive)")
    comment: Optional[str] = Field(None, description="Optional explanation")


class ClonePolicyRequest(BaseModel):
    """Request to clone a policy with an optional name override."""

    name: Optional[str] = Field(None, description="Override name for the clone")


# Phase 4: Versioning


class RollbackPolicyRequest(BaseModel):
    """Request to rollback a policy to a prior version."""

    target_version: int = Field(..., description="Version number to restore")
    change_summary: Optional[str] = Field(None, description="Optional note about this rollback")


# Phase 4: Policy Testing


class PolicyTestRequest(BaseModel):
    """Request to test a policy config against sample content."""

    config_override: Optional[Dict[str, Any]] = Field(
        None,
        description="Draft config to test (uses saved policy config if not provided)",
    )
    sample_input: Optional[str] = Field(None, description="Sample input text to check")
    sample_output: Optional[str] = Field(None, description="Sample output text to check")
    include_behavioral: bool = Field(
        False,
        description="Include LLM-judge behavioral checks (incurs inference cost)",
    )


# ── Version History Models ─────────────────────────────────────


class PolicyVersionListItem(BaseModel):
    """Summary of a single policy version."""

    id: str
    version_number: int
    changed_by: Optional[str] = None
    created_at: Optional[str] = None
    change_summary: Optional[str] = None
    is_current: bool = False


class PolicyVersionDetail(PolicyVersionListItem):
    """Full detail of a policy version, including the config snapshot."""

    config_snapshot: Optional[Dict[str, Any]] = None


class RollbackResponse(BaseModel):
    """Response from a version rollback operation."""

    success: bool
    policy: Dict[str, Any]
    new_version_number: int
