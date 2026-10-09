"""Pydantic request/response models for Wiki API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class WikiPageCreate(BaseModel):
    """Request model for creating a wiki page."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="")
    slug: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_published: bool = True


class WikiPageUpdate(BaseModel):
    """Request model for updating a wiki page."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    parent_id: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None
    change_summary: Optional[str] = None


class WikiPageResponse(BaseModel):
    """Response model for a wiki page."""

    id: str
    slug: str
    title: str
    content: str
    parent_id: Optional[str]
    order_index: int
    is_published: bool
    tags: Optional[List[str]]
    created_by: Optional[str]
    updated_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    version: int  # Current version number

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class WikiPageListItem(BaseModel):
    """Simplified model for wiki page listings."""

    id: str
    slug: str
    title: str
    parent_id: Optional[str]
    order_index: int
    is_published: bool
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class WikiRevisionResponse(BaseModel):
    """Response model for a wiki revision."""

    id: str
    page_id: str
    title: str
    content: str
    version: int
    created_by: Optional[str]
    change_summary: Optional[str]
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class WikiTreeNode(BaseModel):
    """Tree structure for wiki navigation."""

    id: str
    slug: str
    title: str
    parent_id: Optional[str]
    order_index: int
    children: List["WikiTreeNode"] = Field(default_factory=list)

    class Config:
        """Pydantic configuration."""

        from_attributes = True
