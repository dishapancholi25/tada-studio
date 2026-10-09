"""Pydantic models for OCR service requests and responses."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


class OCRRequest(BaseModel):
    """Request model for OCR processing."""

    file_path: Optional[str] = Field(None, description="Path to file to process")
    file_bytes: Optional[bytes] = Field(None, description="File content as bytes")
    prompt: Optional[str] = Field(None, description="Custom OCR prompt")
    doc_type: str = Field(
        "auto", description="Document type (auto, generic, resume, invoice, etc.)"
    )
    max_tokens: int = Field(4000, description="Maximum tokens for API response")
    max_pages: Optional[int] = Field(None, description="Maximum pages to process")
    chunk_by_page: bool = Field(False, description="Return results separated by page")

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        """Validate document type."""
        valid_types = [
            "auto",
            "generic",
            "resume",
            "invoice",
            "form",
            "table",
            "handwritten",
        ]
        if v not in valid_types:
            raise ValueError(f"Invalid doc_type. Must be one of: {valid_types}")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Validate max tokens."""
        if v < 1 or v > 16000:
            raise ValueError("max_tokens must be between 1 and 16000")
        return v


class PageResult(BaseModel):
    """Result for a single page in multi-page documents."""

    page: int = Field(..., description="Page number (1-indexed)")
    text: str = Field("", description="Extracted text from page")
    tokens: int = Field(0, description="Tokens used for this page")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class OCRResponse(BaseModel):
    """Response model for OCR processing."""

    success: bool = Field(..., description="Whether processing succeeded")
    text: str = Field("", description="Extracted text content")
    extraction_method: str = Field(
        ...,
        description="Method used for extraction (e.g., model_ocr_vision, direct_text)",
    )
    tokens_used: int = Field(0, description="Total tokens used (for API-based methods)")
    total_tokens: int = Field(
        0, description="Total tokens used (alias for tokens_used)"
    )
    error: Optional[str] = Field(None, description="Error message if processing failed")
    page_count: Optional[int] = Field(None, description="Number of pages processed")
    pages: Optional[List[PageResult]] = Field(
        None, description="Per-page results for chunked output"
    )
    has_images: Optional[bool] = Field(
        None, description="Whether document contains processed images"
    )
    model: Optional[str] = Field(None, description="Model used for processing")

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to sync tokens_used and total_tokens."""
        if self.tokens_used > 0 and self.total_tokens == 0:
            self.total_tokens = self.tokens_used
        elif self.total_tokens > 0 and self.tokens_used == 0:
            self.tokens_used = self.total_tokens


class AzureOpenAIConfig(BaseModel):
    """Configuration for Azure OpenAI client."""

    api_key: str = Field(..., description="Azure OpenAI API key")
    endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    deployment_name: str = Field("gpt-4o-latest", description="Model deployment name")
    api_version: str = Field("2024-02-01", description="API version")

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Validate endpoint URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("endpoint must be a valid URL")
        return v


class TextBlock(BaseModel):
    """Text block with confidence and position information."""

    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., description="Confidence score (0-1)")
    bbox: List[float] = Field(
        ..., description="Bounding box coordinates [x1, y1, x2, y2]"
    )


class LegacyOCRResponse(BaseModel):
    """Response model for legacy OCR services (EasyOCR, Tesseract, etc.)."""

    text: str = Field("", description="Extracted text content")
    blocks: List[TextBlock] = Field(
        default_factory=list, description="Individual text blocks with positions"
    )
    average_confidence: float = Field(
        0.0, description="Average confidence across all blocks"
    )
    extraction_method: str = Field(
        ..., description="OCR library used (easyocr, tesseract, etc.)"
    )
    language: str = Field("en", description="Language code used for OCR")
    error: Optional[str] = Field(None, description="Error message if processing failed")


class CSVColumnInfo(BaseModel):
    """Information about a CSV column for LLM consumption."""

    name: str = Field(..., description="Column name")
    inferred_type: str = Field(
        "string",
        description="Inferred data type (string, integer, decimal, date, boolean)",
    )
    sample_values: List[str] = Field(
        default_factory=list, description="Sample values from this column"
    )
    null_count: int = Field(0, description="Count of null/empty values")
    unique_count: Optional[int] = Field(None, description="Count of unique values")


class CSVMetadata(BaseModel):
    """Metadata about a CSV file for LLM consumption."""

    filename: Optional[str] = Field(None, description="Original filename")
    row_count: int = Field(..., description="Total number of data rows")
    column_count: int = Field(..., description="Number of columns")
    columns: List[CSVColumnInfo] = Field(
        default_factory=list, description="Column information"
    )
    has_header: bool = Field(True, description="Whether file has a header row")
    detected_delimiter: str = Field(",", description="Detected delimiter character")
    detected_encoding: str = Field("utf-8", description="Detected file encoding")
    file_size_bytes: int = Field(0, description="File size in bytes")
    is_chunked: bool = Field(False, description="Whether output is chunked")
    total_chunks: Optional[int] = Field(
        None, description="Total number of chunks if chunked"
    )
