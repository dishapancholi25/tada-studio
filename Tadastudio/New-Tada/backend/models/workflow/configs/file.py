"""File configuration for file reading and extraction nodes.

This module defines the configuration for file reading operations
using configurable AI model OCR and document extraction.
"""

from typing import TYPE_CHECKING

from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .guardrails import GuardrailsConfig
from typing import List, Optional


@dataclass
class FileReadConfig:
    """Configuration for file read action nodes using configurable AI model OCR.

    Supports multiple file formats with OCR, table extraction, and
    format preservation capabilities.

    Attributes:
        extraction_mode: Extraction mode (model_ocr, text_only, raw)
            - model_ocr: AI-powered extraction with OCR
            - text_only: Extract text without OCR
            - raw: Pass file content as-is without any processing (for MCP/external tools)
        model_deployment_id: Model deployment ID for AI OCR (optional)
        output_format: Output format (markdown, json, plain)
        ocr_prompt: Prompt for AI model OCR extraction
        doc_type: Document type hint (auto, generic, resume, invoice, etc.)
        max_tokens_per_request: Maximum tokens for AI model OCR response
        max_pages: Maximum pages to process for PDFs (None = all)
        chunk_by_page: Return results separated by page for PDFs
        include_metadata: Include file metadata in output
        preserve_formatting: Preserve original formatting
        extract_tables: Extract tables as structured data
        extract_images: Extract embedded images from DOCX
        max_file_size_mb: Maximum file size in MB
        allowed_extensions: Allowed file extensions
        fallback_on_error: Try alternative extraction methods on failure
        skip_on_error: Skip file and continue workflow on error
        use_cache: Use cached results for repeated processing
        file_path: Path to the file
        file_base64: Base64 encoded file content
        file_content: Direct file content
        file_type: MIME type of the file
        llm_safe_output: For raw binary files, send a compact runtime reference
            to agent prompts while preserving raw content for tools.
    """

    extraction_mode: str = "model_ocr"
    model_deployment_id: Optional[str] = None
    output_format: str = "markdown"
    ocr_prompt: str = """Extract all text from this document image. Preserve the original formatting including:
- Headers and sections
- Lists and bullet points
- Tables (use markdown table format)
- Bold and italic text
- Page numbers if visible

Output as clean, well-structured markdown."""
    doc_type: str = "auto"
    max_tokens_per_request: int = 4000
    max_pages: Optional[int] = None
    chunk_by_page: bool = False
    include_metadata: bool = True
    preserve_formatting: bool = True
    extract_tables: bool = True
    extract_images: bool = True
    max_file_size_mb: int = 1024
    allowed_extensions: List[str] = field(
        default_factory=lambda: [
            ".pdf",
            ".txt",
            ".docx",
            ".xlsx",
            ".csv",
            ".png",
            ".jpg",
            ".jpeg",
            ".html",
            ".md",
        ]
    )
    fallback_on_error: bool = True
    skip_on_error: bool = False
    use_cache: bool = True
    file_path: Optional[str] = None
    file_base64: Optional[str] = None
    file_content: Optional[str] = None
    file_type: Optional[str] = None
    llm_safe_output: bool = False

    # CSV-specific configuration
    csv_delimiter: str = "auto"  # auto, comma, semicolon, tab, pipe
    csv_has_header: str = "auto"  # auto, true, false
    csv_output_format: str = "markdown"  # markdown, json, row_by_row, summary
    csv_max_rows: Optional[int] = None  # None = all rows
    csv_chunk_size: int = 50  # Rows per chunk for large files
    csv_include_schema: bool = True  # Include column type inference
    csv_include_stats: bool = True  # Include basic statistics
    csv_encoding: str = "auto"  # auto or specific encoding (utf-8, latin-1, etc.)
    guardrails_config: Optional["GuardrailsConfig"] = None
 