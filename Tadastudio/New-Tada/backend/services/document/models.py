"""Pydantic models for document processing service."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class ProcessingConfig(BaseModel):
    """Configuration for document processing."""

    extraction_mode: str = Field(
        "auto", description="Extraction mode (auto, unstructured, ocr, text)"
    )
    output_format: str = Field(
        "markdown", description="Output format (markdown, json, elements)"
    )
    use_cache: bool = Field(True, description="Whether to use cached results")
    fallback_on_error: bool = Field(
        True, description="Fall back to simpler methods on error"
    )
    language: Optional[str] = Field(
        None, description="Language code for OCR/extraction"
    )
    chunking_strategy: Optional[str] = Field(
        None, description="Chunking strategy for Unstructured"
    )
    max_partition_size: int = Field(1500, description="Max characters per partition")
    combine_under_n_chars: int = Field(
        500, description="Combine partitions under N characters"
    )
    include_page_breaks: bool = Field(
        False, description="Include page break markers in output"
    )
    include_metadata: bool = Field(True, description="Include metadata in output")
    extract_tables: bool = Field(True, description="Extract tables from documents")
    page_numbers: Optional[List[int]] = Field(
        None, description="Specific page numbers to extract"
    )
    ocr_library: str = Field("easyocr", description="OCR library to use")
    ocr_confidence_threshold: float = Field(
        0.5, description="Minimum OCR confidence threshold"
    )

    @field_validator("extraction_mode")
    @classmethod
    def validate_extraction_mode(cls, v: str) -> str:
        """Validate extraction mode."""
        valid_modes = ["auto", "unstructured", "ocr", "text"]
        if v not in valid_modes:
            raise ValueError(f"Invalid extraction_mode. Must be one of: {valid_modes}")
        return v

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        """Validate output format."""
        valid_formats = ["markdown", "json", "elements", "plain"]
        if v not in valid_formats:
            raise ValueError(f"Invalid output_format. Must be one of: {valid_formats}")
        return v

    @field_validator("ocr_confidence_threshold")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate OCR confidence threshold."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("ocr_confidence_threshold must be between 0.0 and 1.0")
        return v


class FileMetadata(BaseModel):
    """Metadata about a processed file."""

    filename: str = Field(..., description="Name of the file")
    file_path: str = Field(..., description="Path to the file")
    file_type: str = Field(..., description="Detected file type")
    file_size: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in MB")
    created_time: str = Field(..., description="File creation time (ISO format)")
    modified_time: str = Field(..., description="File modification time (ISO format)")
    extension: str = Field(..., description="File extension")
    page_count: Optional[int] = Field(
        None, description="Number of pages (if applicable)"
    )
    sheet_count: Optional[int] = Field(
        None, description="Number of sheets (for spreadsheets)"
    )
    ocr_confidence: Optional[float] = Field(
        None, description="OCR confidence score (if applicable)"
    )
    ocr_method: Optional[str] = Field(
        None, description="OCR method used (if applicable)"
    )


class ProcessingResult(BaseModel):
    """Result of document processing."""

    success: bool = Field(..., description="Whether processing succeeded")
    content: Union[str, dict, list] = Field(..., description="Extracted content")
    metadata: FileMetadata = Field(..., description="File metadata")
    extraction_method: str = Field(..., description="Method used for extraction")
    error: Optional[str] = Field(None, description="Error message if processing failed")
    document_count: Optional[int] = Field(
        None, description="Number of documents/elements extracted"
    )
    confidence: Optional[float] = Field(None, description="Confidence score (for OCR)")


class ProcessingRequest(BaseModel):
    """Request for document processing."""

    file_path: str = Field(..., description="Path to the file to process")
    config: ProcessingConfig = Field(
        default_factory=ProcessingConfig, description="Processing configuration"
    )

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path is not empty."""
        if not v or not v.strip():
            raise ValueError("file_path cannot be empty")
        return v


class Element(BaseModel):
    """Structured document element."""

    type: str = Field(..., description="Element type (e.g., text, table, image)")
    text: str = Field(..., description="Element text content")
    metadata: dict = Field(default_factory=dict, description="Element metadata")


class PageContent(BaseModel):
    """Content for a single page."""

    page_number: int = Field(..., description="Page number")
    content: str = Field(..., description="Page content")
