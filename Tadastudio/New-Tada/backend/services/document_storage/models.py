"""Pydantic models for document storage service."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""

    document_id: str
    collection_id: str
    chunk_index: int
    total_chunks: int
    source: str
    file_type: str
    file_url: Optional[str] = None
    page: Optional[int] = None
    page_label: Optional[str] = None
    pages: Optional[List[int]] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    spans_pages: Optional[bool] = None


class ProcessingMetadata(BaseModel):
    """Metadata about document processing."""

    chunk_count: int
    total_characters: int
    loader_mode: str
    chunking_strategy: str
    chunk_size: int
    chunk_overlap: int
    processing_time: Optional[float] = None


class DocumentInfo(BaseModel):
    """Information about a stored document."""

    id: str
    collection_id: str
    name: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    storage_path: Optional[str] = None
    uploaded_at: datetime
    updated_at: Optional[datetime] = None
    chunk_count: int = 0
    error_message: Optional[str] = None
    processing_metadata: Optional[Dict[str, Any]] = None
    embedding_tokens: Optional[int] = None
    embedding_cost: Optional[float] = None
    embedding_model: Optional[str] = None
    collection_name: Optional[str] = None
    collection_user_id: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None

    class Config:
        """Pydantic config."""

        from_attributes = True


class ChunkInfo(BaseModel):
    """Information about a document chunk."""

    id: Optional[str] = None  # UUID string from database
    index: int
    content: str
    preview: Optional[str] = None
    has_embedding: bool = False
    metadata: Optional[ChunkMetadata] = None


class UploadResult(BaseModel):
    """Result of document upload operation."""

    document: DocumentInfo
    chunks: List[ChunkInfo] = Field(default_factory=list)
    success: bool = True
    message: Optional[str] = None
    embedding_tokens: int = 0
    embedding_cost: Optional[float] = None


class CollectionInfo(BaseModel):
    """Information about a document collection, including group visibility and creator info."""

    id: str
    name: str
    description: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    document_count: int = 0
    visible_to_groups: List[str] = Field(default_factory=list)
    created_by_name: Optional[str] = None
    created_by_email: Optional[str] = None
    is_read_only: bool = False
    embedding_deployment_id: Optional[str] = None
    total_embedding_tokens: int = 0
    total_embedding_cost: float = 0.0
    search_count: int = 0

    class Config:
        """Pydantic config."""

        from_attributes = True


class SearchResult(BaseModel):
    """Search result from document search."""

    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchEmbeddingResult(BaseModel):
    """Result of batch embedding operation."""

    total: int
    successful: int
    failed: int
    embeddings: List[Optional[List[float]]]
    errors: List[Optional[str]] = Field(default_factory=list)
    token_count: int = 0
    embedding_cost: Optional[Dict[str, Any]] = None
