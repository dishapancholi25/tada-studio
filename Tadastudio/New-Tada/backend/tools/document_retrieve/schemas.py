"""Pydantic schemas for document retrieve tool."""

from typing import Optional

from pydantic import BaseModel, Field


class DocumentRetrieveArgs(BaseModel):
    """Input arguments for document retrieve tool."""

    document_id: Optional[str] = Field(
        default=None,
        description="Specific document UUID to retrieve",
    )
    document_name: Optional[str] = Field(
        default=None,
        description="Document name to search for (case-insensitive partial match)",
    )
    page_range: Optional[str] = Field(
        default=None,
        description="Page range for partial retrieval, e.g. '1-5' or '3'",
    )
