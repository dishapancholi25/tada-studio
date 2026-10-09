"""Request and response models for library API endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AddToLibraryRequest(BaseModel):
    """Request model for adding a workflow to the library."""

    workflow_id: str = Field(..., description="ID of the workflow to add to library")
    name: str = Field(..., description="Display name for the template in the library")
    description: str = Field(..., description="Template description")
    category: List[str] = Field(..., description="List of template categories")
    tags: List[str] = Field(..., description="List of tags")
    complexity: Optional[str] = Field(
        None, description="Complexity level (beginner/intermediate/advanced)"
    )
    icon_color: Optional[str] = Field(None, description="Icon color")


class AddAgentTemplateRequest(BaseModel):
    """Request model for adding a single agent to the library."""

    workflow_id: str = Field(..., description="ID of the source workflow")
    agent_node_id: str = Field(
        ..., description="Identifier of the agent node to publish"
    )
    name: str = Field(..., description="Display name for the agent template")
    description: str = Field(..., description="Template description")
    category: List[str] = Field(..., description="List of template categories")
    tags: List[str] = Field(..., description="List of tags")
    icon_color: Optional[str] = Field(None, description="Icon color")


class CloneTemplateRequest(BaseModel):
    """Request model for cloning a template."""

    workspace_id: Optional[str] = Field(
        None, description="Target workspace ID (defaults to user's email)"
    )
    target_name: Optional[str] = Field(
        None,
        description="Custom name for the cloned workflow (defaults to template name)",
    )


class UpdateTemplateRequest(BaseModel):
    """Request model for updating template metadata."""

    name: Optional[str] = Field(None, description="New name")
    description: Optional[str] = Field(None, description="New description")
    category: Optional[List[str]] = Field(None, description="New categories")
    tags: Optional[List[str]] = Field(None, description="New tags")
    complexity: Optional[str] = Field(None, description="New complexity level")
    icon_color: Optional[str] = Field(None, description="New icon color")


class ImportAgentJSONRequest(BaseModel):
    """Request model for importing an agent from JSON."""

    agent_json: Dict[str, Any] = Field(..., description="Agent configuration JSON")
    metadata_override: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional metadata overrides (category, tags, complexity, icon_color)",
    )


class CollectionDependency(BaseModel):
    """Response model for collection dependency information."""

    collection_id: Optional[str] = Field(
        None, description="Collection ID (null if not found)"
    )
    collection_name: str = Field(..., description="Collection name")
    visible_to_groups: List[str] = Field(
        default_factory=list, description="Groups with access"
    )
    has_access: bool = Field(..., description="Whether current user has access")
    access_reason: str = Field(
        ..., description="Reason for access (owner/global/group: name/no access)"
    )
    created_by_name: Optional[str] = Field(None, description="Collection creator name")
