# Document Service Documentation

## Overview

The Document Service provides comprehensive document processing capabilities for AgenticStudio, supporting multiple file
types including PDFs, Word documents, Excel spreadsheets, text files, and images. The service intelligently selects the
best processing method based on file type and configuration, with automatic fallback mechanisms and caching support.

**Location:** [backend/services/document/](../../backend/services/document/)

**Primary Responsibilities:**

- Extract text and structured content from various document formats
- Automatically select optimal processing method (text, PDF, OCR, Unstructured)
- Format extracted content as markdown, JSON, or structured elements
- Cache processing results for improved performance
- Handle errors gracefully with configurable fallback strategies
- Extract comprehensive file metadata (size, timestamps, page counts)

**Key Use Cases:**

- Processing uploaded documents for RAG pipelines
- Extracting text from scanned images using OCR
- Converting complex documents (PDFs, DOCX) to structured format
- Batch document processing with caching
- Extracting tables and structured content from documents

## Architecture

### Module Structure

```
backend/services/document/
├── __init__.py              # Public API exports and factory function
├── service.py               # Main DocumentService orchestrator
├── models.py                # Pydantic data models
├── config.py                # Configuration and file type mappings
├── exceptions.py            # Custom exceptions
├── metadata.py              # File metadata extraction
├── processors/              # Document processors by type
│   ├── __init__.py
│   ├── base.py             # Abstract processor interface
│   ├── text.py             # Plain text processor
│   ├── pdf.py              # PDF processor (PyPDF2)
│   ├── docx.py             # Word document processor
│   ├── excel.py            # Excel spreadsheet processor
│   ├── ocr.py              # OCR processor for images
│   └── unstructured.py     # Unstructured.io processor
├── formatters/              # Output formatters
│   ├── __init__.py
│   ├── base.py             # Abstract formatter interface
│   ├── markdown.py         # Markdown formatter
│   ├── json.py             # JSON formatter
│   └── elements.py         # Structured elements formatter
└── cache/                   # Cache management
    ├── __init__.py
    ├── manager.py          # Cache manager
    └── key_generator.py    # Cache key generation
```

### Design Patterns

**Strategy Pattern (Processors):**
The service uses the Strategy pattern for document processing. Each processor implements the `DocumentProcessor`
interface with `supports()` and `process()` methods. The `DocumentService` selects the appropriate processor based on
file type and configuration.

```
DocumentService
    ├── selects processor based on file type
    └── delegates to
        ├── TextProcessor
        ├── PDFProcessor
        ├── DOCXProcessor
        ├── ExcelProcessor
        ├── OCRProcessor
        └── UnstructuredProcessor
```

**Strategy Pattern (Formatters):**
Similarly, formatters use the Strategy pattern to transform raw processor output into different formats (markdown, JSON,
elements).

**Caching:**
The service implements transparent caching using a cache manager that generates keys based on file path and
configuration, storing results as JSON files.

**Graceful Degradation:**
The service implements automatic fallback: if a processor fails and `fallback_on_error` is enabled, it attempts simpler
processing methods.

### Component Relationships

```
┌─────────────────────────────────────────────────────┐
│              DocumentService                         │
│  - Orchestrates processing                          │
│  - Manages cache                                    │
│  - Handles fallbacks                                │
└──────┬──────────┬───────────┬─────────────┬────────┘
       │          │           │             │
       ▼          ▼           ▼             ▼
 ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
 │ Metadata │ │  Cache  │ │Processor │ │Formatter │
 │ Extractor│ │ Manager │ │ Strategy │ │ Strategy │
 └──────────┘ └─────────┘ └──────────┘ └──────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.services.ocr` - OCR processing service (optional)

**External Dependencies:**

- `pydantic` - Data validation and models
- `PyPDF2` - PDF processing (optional)
- `python-docx` - Word document processing (optional)
- `openpyxl` - Excel processing (optional)
- `unstructured` - Advanced document processing (optional)
- `easyocr` / `pytesseract` - OCR libraries (optional)

**Database Dependencies:**
None - this is a stateless processing service

**Environment Variables:**
None required - all configuration passed via `ProcessingConfig`

## Public API

### Exported Classes

- `DocumentService` - Main service orchestrator for document processing
- `ProcessingConfig` - Configuration for document processing operations
- `ProcessingResult` - Result model containing extracted content and metadata
- `ProcessingRequest` - Request model for document processing
- `FileMetadata` - Metadata about a processed file
- `Element` - Structured document element (text, table, image)
- `PageContent` - Content for a single page

### Exported Functions

- `get_file_type_from_extension()` - Determine file type from extension
- `determine_extraction_mode()` - Determine best extraction mode for file type
- `is_supported_file_type()` - Check if file type is supported
- `create_document_service()` - Factory function to create DocumentService instance

### Constants and Configuration

- `FILE_TYPE_MAP` - Dictionary mapping file extensions to type strings
- `TEXT_FILE_TYPES` - List of text file types: `["text", "markdown", "csv"]`
- `PDF_FILE_TYPES` - List of PDF file types: `["pdf"]`
- `DOCX_FILE_TYPES` - List of Word document types: `["docx", "doc"]`
- `EXCEL_FILE_TYPES` - List of Excel types: `["xlsx", "xls"]`
- `IMAGE_FILE_TYPES` - List of image types: `["png", "jpg", "jpeg"]`

### Exceptions

```
Exception
└── DocumentException (base exception)
    ├── DocumentConfigError (invalid configuration)
    ├── DocumentProcessingError (processing failure)
    ├── UnsupportedFileTypeError (unsupported file type)
    ├── ProcessorNotAvailableError (processor unavailable)
    └── CacheError (cache operation failure)
```

## Core Classes

### `DocumentService`

Main orchestrator for document processing that manages processors, formatters, and caching.

**Purpose:** Provide a unified interface for processing various document types with automatic processor selection,
caching, and error handling.

**Responsibilities:**

- Initialise and manage document processors (text, PDF, DOCX, Excel, OCR, Unstructured)
- Initialise and manage output formatters (markdown, JSON, elements)
- Extract file metadata
- Determine optimal extraction method based on file type and configuration
- Cache processing results for performance
- Handle errors with configurable fallback strategies
- Transform raw processor output into desired format

**Initialisation:**

```python
def __init__(
    self,
    cache_dir: Path = None,
) -> None:
    """
    Initialise the document service.

    Args:
        cache_dir: Directory for cache storage (optional, defaults to ./document_cache)
    """
```

**Key Methods:**

#### `process_document()`

Main entry point for processing documents. Handles caching, metadata extraction, processor selection, and error
handling.

```python
def process_document(
    self,
    file_path: str,
    config: Dict[str, Any],
    use_cache: bool = True,
) -> Dict[str, Any]:
    """Process a document using the best available method."""
```

**Parameters:**

- `file_path` (str) - Path to the document file to process
- `config` (Dict[str, Any]) - Processing configuration (see ProcessingConfig model)
- `use_cache` (bool) - Whether to use cached results (default: True)

**Returns:**

- `Dict[str, Any]` - Processing result containing success status, content, metadata, and extraction method

**Raises:**

- `FileNotFoundError` - If the file doesn't exist
- `UnsupportedFileTypeError` - If file type is not supported and no fallback available

**Example:**

```python
from backend.services.document import DocumentService

# Initialise service
service = DocumentService()

# Process a PDF document
result = service.process_document(
    file_path="/path/to/document.pdf",
    config={
        "extraction_mode": "auto",
        "output_format": "markdown",
        "use_cache": True,
        "fallback_on_error": True,
    },
)

# Check result
if result["success"]:
    print(f"Extracted content: {result['content']}")
    print(f"Method used: {result['extraction_method']}")
    print(f"Page count: {result['metadata']['page_count']}")
else:
    print(f"Error: {result['error']}")
```

**Behaviour:**

- Checks cache first if `use_cache` is True
- Extracts file metadata (size, timestamps, type)
- Determines optimal extraction mode (auto-detected or specified)
- Selects appropriate processor based on mode and file type
- Processes document using selected processor
- Formats output using specified formatter
- Caches successful results
- On error, attempts fallback if `fallback_on_error` is True in config
- Returns structured result with success status, content, and metadata

**Use Cases:**

- Processing uploaded documents in API endpoints
- Batch document processing pipelines
- Converting documents for RAG systems
- Extracting structured data from documents

#### `_determine_extraction_mode()`

```python
def _determine_extraction_mode(
    self,
    config: ProcessingConfig,
    file_type: str,
) -> str:
    """Determine extraction mode from config or file type."""
```

**Parameters:**

- `config` (ProcessingConfig) - Processing configuration
- `file_type` (str) - Detected file type

**Returns:**

- `str` - Extraction mode to use ("text", "pdf", "ocr", "unstructured")

**Behaviour:**

- Returns configured mode if not "auto"
- Otherwise, determines best mode based on file type:
  - PDF/DOCX → "unstructured"
  - Images → "ocr"
  - Text files → "text"

**Use Cases:**

- Automatic processor selection
- Override automatic selection with explicit mode

#### `_process_with_mode()`

```python
def _process_with_mode(
    self,
    file_path: Path,
    mode: str,
    config: Dict,
    metadata: FileMetadata,
) -> Dict[str, Any]:
    """Process document with specific mode."""
```

**Parameters:**

- `file_path` (Path) - Path to document
- `mode` (str) - Extraction mode to use
- `config` (Dict) - Processing configuration
- `metadata` (FileMetadata) - File metadata

**Returns:**

- `Dict[str, Any]` - Processing result

**Behaviour:**

- Gets appropriate processor for mode
- Processes document
- Formats output
- Updates metadata with processor results
- Returns complete processing result

#### `_get_processor()`

```python
def _get_processor(
    self,
    mode: str,
    file_type: str,
):
    """Get appropriate processor for mode and file type."""
```

**Parameters:**

- `mode` (str) - Extraction mode
- `file_type` (str) - File type

**Returns:**

- `DocumentProcessor` - Appropriate processor instance

**Raises:**

- `UnsupportedFileTypeError` - If no processor supports the file type

**Behaviour:**

- First tries direct mode mapping
- Falls back to finding processor that supports the file type
- Raises exception if no suitable processor found

#### `_fallback_process()`

```python
def _fallback_process(
    self,
    file_path: Path,
    metadata: FileMetadata,
    config: Dict,
) -> Dict[str, Any]:
    """Fallback processing using simpler methods."""
```

**Parameters:**

- `file_path` (Path) - Path to document
- `metadata` (FileMetadata) - File metadata
- `config` (Dict) - Processing configuration

**Returns:**

- `Dict[str, Any]` - Processing result or error result

**Behaviour:**

- Attempts text processor as ultimate fallback
- Returns formatted result if successful
- Returns error result if fallback also fails

**Use Cases:**

- Graceful degradation when primary processor fails
- Attempting to extract partial content from corrupted files

**Class Attributes:**

- `cache_manager: CacheManager` - Manages result caching
- `processors: Dict[str, Any]` - Available document processors
- `formatters: Dict[str, Any]` - Available output formatters

---

### `ProcessingConfig`

Pydantic model defining configuration options for document processing.

**Purpose:** Provide type-safe configuration with validation for document processing operations.

**Responsibilities:**

- Define processing options (extraction mode, output format)
- Validate configuration values
- Provide sensible defaults
- Support processor-specific options (OCR, chunking, etc.)

**Initialisation:**

```python
class ProcessingConfig(BaseModel):
    """Configuration for document processing."""

    extraction_mode: str = "auto"
    output_format: str = "markdown"
    use_cache: bool = True
    fallback_on_error: bool = True
    language: Optional[str] = None
    chunking_strategy: Optional[str] = None
    max_partition_size: int = 1500
    combine_under_n_chars: int = 500
    include_page_breaks: bool = False
    include_metadata: bool = True
    extract_tables: bool = True
    page_numbers: Optional[List[int]] = None
    ocr_library: str = "easyocr"
    ocr_confidence_threshold: float = 0.5
```

**Fields:**

- `extraction_mode` - Extraction mode: "auto", "unstructured", "ocr", "text" (default: "auto")
- `output_format` - Output format: "markdown", "json", "elements", "plain" (default: "markdown")
- `use_cache` - Whether to use cached results (default: True)
- `fallback_on_error` - Fall back to simpler methods on error (default: True)
- `language` - Language code for OCR/extraction (default: None)
- `chunking_strategy` - Chunking strategy for Unstructured (default: None)
- `max_partition_size` - Max characters per partition (default: 1500)
- `combine_under_n_chars` - Combine partitions under N characters (default: 500)
- `include_page_breaks` - Include page break markers in output (default: False)
- `include_metadata` - Include metadata in output (default: True)
- `extract_tables` - Extract tables from documents (default: True)
- `page_numbers` - Specific page numbers to extract (default: None)
- `ocr_library` - OCR library to use: "easyocr" or "tesseract" (default: "easyocr")
- `ocr_confidence_threshold` - Minimum OCR confidence threshold (default: 0.5)

**Example:**

```python
from backend.services.document import ProcessingConfig

# Basic configuration
config = ProcessingConfig()

# Advanced configuration
config = ProcessingConfig(
    extraction_mode="unstructured",
    output_format="json",
    use_cache=False,
    extract_tables=True,
    include_page_breaks=True,
    max_partition_size=2000,
    language="eng",
)

# Use with DocumentService
service.process_document(file_path="doc.pdf", config=config.model_dump())
```

---

### `FileMetadata`

Pydantic model containing metadata about a processed file.

**Purpose:** Provide comprehensive file information including type, size, timestamps, and processing results.

**Fields:**

- `filename` (str) - Name of the file
- `file_path` (str) - Full path to the file
- `file_type` (str) - Detected file type ("pdf", "docx", "text", etc.)
- `file_size` (int) - File size in bytes
- `file_size_mb` (float) - File size in megabytes
- `created_time` (str) - File creation time (ISO format)
- `modified_time` (str) - File modification time (ISO format)
- `extension` (str) - File extension
- `page_count` (Optional[int]) - Number of pages (if applicable)
- `sheet_count` (Optional[int]) - Number of sheets (for spreadsheets)
- `ocr_confidence` (Optional[float]) - OCR confidence score (if OCR used)
- `ocr_method` (Optional[str]) - OCR method used (if applicable)

**Example:**

```python
from backend.services.document import FileMetadata

metadata = FileMetadata(
    filename="report.pdf",
    file_path="/path/to/report.pdf",
    file_type="pdf",
    file_size=1024000,
    file_size_mb=1.02,
    created_time="2025-01-15T10:30:00",
    modified_time="2025-01-15T10:30:00",
    extension=".pdf",
    page_count=25,
)
```

---

### `ProcessingResult`

Pydantic model representing the result of document processing.

**Purpose:** Provide structured result with content, metadata, and status information.

**Fields:**

- `success` (bool) - Whether processing succeeded
- `content` (Union[str, dict, list]) - Extracted content (format depends on output_format)
- `metadata` (FileMetadata) - File metadata
- `extraction_method` (str) - Method used for extraction
- `error` (Optional[str]) - Error message if processing failed
- `document_count` (Optional[int]) - Number of documents/elements extracted
- `confidence` (Optional[float]) - Confidence score (for OCR)

**Example:**

```python
from backend.services.document import ProcessingResult

result = ProcessingResult(
    success=True,
    content="# Document Title\n\nDocument content...",
    metadata=metadata,
    extraction_method="unstructured",
    document_count=15,
)
```

---

### `ProcessingRequest`

Pydantic model for document processing requests.

**Purpose:** Validate and structure processing requests.

**Fields:**

- `file_path` (str) - Path to the file to process (required)
- `config` (ProcessingConfig) - Processing configuration (default: ProcessingConfig())

**Example:**

```python
from backend.services.document import ProcessingRequest, ProcessingConfig

request = ProcessingRequest(
    file_path="/path/to/document.pdf",
    config=ProcessingConfig(
        extraction_mode="auto",
        output_format="markdown",
    ),
)
```

---

### `Element`

Pydantic model representing a structured document element.

**Purpose:** Represent individual document components (text, table, image) with metadata.

**Fields:**

- `type` (str) - Element type ("text", "table", "image", "title", etc.)
- `text` (str) - Element text content
- `metadata` (dict) - Element metadata (page number, coordinates, etc.)

**Example:**

```python
from backend.services.document import Element

element = Element(
    type="table",
    text="| Column 1 | Column 2 |\n|----------|----------|\n| Value 1  | Value 2  |",
    metadata={"page": 3, "table_id": 0},
)
```

---

### `PageContent`

Pydantic model representing content for a single page.

**Purpose:** Structure page-level content extraction.

**Fields:**

- `page_number` (int) - Page number (1-indexed)
- `content` (str) - Page content

**Example:**

```python
from backend.services.document import PageContent

page = PageContent(
    page_number=1,
    content="Page 1 content here...",
)
```

## Functions

### `get_file_type_from_extension()`

Determine file type from file extension.

**Signature:**

```python
def get_file_type_from_extension(extension: str) -> str:
    """Get file type from extension."""
```

**Parameters:**

- `extension` (str) - File extension (with or without leading dot)

**Returns:**

- `str` - File type string ("pdf", "docx", "text", etc.) or "unknown"

**Example:**

```python
from backend.services.document import get_file_type_from_extension

file_type = get_file_type_from_extension(".pdf")  # Returns "pdf"
file_type = get_file_type_from_extension("docx")  # Returns "docx"
file_type = get_file_type_from_extension(".xyz")  # Returns "unknown"
```

**Use Cases:**

- Determining file type before processing
- Validating file uploads
- Routing files to appropriate processors

---

### `determine_extraction_mode()`

Determine the best extraction mode for a file type.

**Signature:**

```python
def determine_extraction_mode(file_type: str) -> str:
    """Determine best extraction mode for a file type."""
```

**Parameters:**

- `file_type` (str) - Detected file type

**Returns:**

- `str` - Recommended extraction mode ("text", "unstructured", "ocr")

**Example:**

```python
from backend.services.document import determine_extraction_mode

mode = determine_extraction_mode("pdf")        # Returns "unstructured"
mode = determine_extraction_mode("png")        # Returns "ocr"
mode = determine_extraction_mode("text")       # Returns "text"
mode = determine_extraction_mode("unknown")    # Returns "text"
```

**Use Cases:**

- Automatic processor selection
- Optimising processing strategy based on file type

---

### `is_supported_file_type()`

Check if a file type is supported by the document service.

**Signature:**

```python
def is_supported_file_type(file_type: str) -> bool:
    """Check if file type is supported."""
```

**Parameters:**

- `file_type` (str) - File type to check

**Returns:**

- `bool` - True if supported, False otherwise

**Example:**

```python
from backend.services.document import is_supported_file_type

if is_supported_file_type("pdf"):
    print("PDF files are supported")

if not is_supported_file_type("unknown"):
    print("This file type is not supported")
```

**Use Cases:**

- Pre-validation before processing
- API request validation
- User feedback on upload restrictions

---

### `create_document_service()`

Factory function to create a configured DocumentService instance.

**Signature:**

```python
def create_document_service(cache_dir=None) -> DocumentService:
    """
    Create document service.

    Args:
        cache_dir: Optional cache directory path

    Returns:
        Configured DocumentService instance
    """
```

**Parameters:**

- `cache_dir` (Optional[Path]) - Cache directory path (default: None, uses ./document_cache)

**Returns:**

- `DocumentService` - Configured service instance

**Example:**

```python
from backend.services.document import create_document_service

# Create with default cache directory
service = create_document_service()

# Create with custom cache directory
service = create_document_service(cache_dir="/path/to/cache")

# Use the service
result = service.process_document("document.pdf", {"extraction_mode": "auto"})
```

**Use Cases:**

- Consistent service initialisation across application
- Dependency injection in API layer
- Testing with custom cache directories

## Configuration

### Configuration Classes

The service uses `ProcessingConfig` as the main configuration model:

```python
from backend.services.document import ProcessingConfig

config = ProcessingConfig(
    extraction_mode="auto",              # "auto", "unstructured", "ocr", "text"
    output_format="markdown",            # "markdown", "json", "elements", "plain"
    use_cache=True,                      # Enable/disable caching
    fallback_on_error=True,              # Enable/disable fallback
    language="eng",                      # OCR language code
    extract_tables=True,                 # Extract tables
    include_page_breaks=False,           # Include page break markers
    include_metadata=True,               # Include metadata in output
    max_partition_size=1500,             # Max characters per partition
    combine_under_n_chars=500,           # Combine small partitions
    ocr_library="easyocr",               # "easyocr" or "tesseract"
    ocr_confidence_threshold=0.5,        # Minimum OCR confidence (0.0-1.0)
    page_numbers=[1, 2, 3],              # Specific pages to extract
)
```

### Environment Variables

The service does not require environment variables. All configuration is passed via `ProcessingConfig`.

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.document import DocumentService

# Create service with defaults
service = DocumentService()

# Process document
result = service.process_document(
    file_path="/path/to/document.pdf",
    config={"extraction_mode": "auto"},
)
```

**Advanced Initialisation:**

```python
from pathlib import Path
from backend.services.document import DocumentService, ProcessingConfig

# Create service with custom cache directory
cache_dir = Path("/custom/cache/directory")
service = DocumentService(cache_dir=cache_dir)

# Create detailed configuration
config = ProcessingConfig(
    extraction_mode="unstructured",
    output_format="json",
    use_cache=True,
    fallback_on_error=True,
    extract_tables=True,
    include_metadata=True,
    language="eng",
    max_partition_size=2000,
)

# Process with configuration
result = service.process_document(
    file_path="/path/to/document.pdf",
    config=config.model_dump(),
)
```

**Factory Pattern:**

```python
from backend.services.document import create_document_service

# Use factory function
service = create_document_service(cache_dir="/custom/cache")
```

**Dependency Injection:**

```python
from typing import Optional
from pathlib import Path
from backend.services.document import DocumentService

class DocumentProcessor:
    """Example class using dependency injection."""

    def __init__(self, document_service: Optional[DocumentService] = None):
        self.document_service = document_service or DocumentService()

    async def process_file(self, file_path: str) -> dict:
        return self.document_service.process_document(
            file_path=file_path,
            config={"extraction_mode": "auto"},
        )
```

## Error Handling

### Exception Hierarchy

```
Exception
└── DocumentException (base exception for all document errors)
    ├── DocumentConfigError (configuration validation errors)
    ├── DocumentProcessingError (processing failures)
    │   └── Includes file_path and processor attributes
    ├── UnsupportedFileTypeError (unsupported file types)
    │   └── Includes file_type and supported_types attributes
    ├── ProcessorNotAvailableError (processor unavailable)
    │   └── Includes processor_name and reason attributes
    └── CacheError (cache operation failures)
```

### Exception Details

#### `DocumentException`

Base exception for all document processing errors.

**Inherits from:** `Exception`

**When raised:**

- Base class, not raised directly
- Catch this to handle any document service error

**Example:**

```python
from backend.services.document import DocumentService, DocumentException

try:
    service = DocumentService()
    result = service.process_document("file.pdf", {})
except DocumentException as e:
    print(f"Document error: {e}")
```

#### `DocumentConfigError`

Raised when document processing configuration is invalid.

**Inherits from:** `DocumentException`

**When raised:**

- Invalid extraction_mode value
- Invalid output_format value
- Invalid OCR confidence threshold (not in 0.0-1.0 range)
- Other configuration validation failures

**Example:**

```python
from backend.services.document import ProcessingConfig, DocumentConfigError
from pydantic import ValidationError

try:
    config = ProcessingConfig(
        extraction_mode="invalid_mode",  # Invalid!
    )
except ValidationError as e:
    print(f"Configuration error: {e}")
```

#### `DocumentProcessingError`

Raised when document processing fails.

**Inherits from:** `DocumentException`

**Attributes:**

- `file_path` (Optional[str]) - Path to file that failed
- `processor` (Optional[str]) - Name of processor that failed

**When raised:**

- File cannot be read
- Processor encounters an error
- Content extraction fails
- Formatting fails

**Example:**

```python
from backend.services.document import DocumentService, DocumentProcessingError

try:
    service = DocumentService()
    result = service.process_document(
        file_path="/path/to/corrupted.pdf",
        config={"fallback_on_error": False},
    )
except DocumentProcessingError as e:
    print(f"Failed to process {e.file_path} using {e.processor}: {e}")
```

#### `UnsupportedFileTypeError`

Raised when attempting to process an unsupported file type.

**Inherits from:** `DocumentException`

**Attributes:**

- `file_type` (str) - The unsupported file type
- `supported_types` (List[str]) - List of supported types

**When raised:**

- File type is not recognised
- No processor available for file type
- File extension not in FILE_TYPE_MAP

**Example:**

```python
from backend.services.document import DocumentService, UnsupportedFileTypeError

try:
    service = DocumentService()
    result = service.process_document(
        file_path="/path/to/file.xyz",
        config={},
    )
except UnsupportedFileTypeError as e:
    print(f"File type '{e.file_type}' not supported")
    print(f"Supported types: {', '.join(e.supported_types)}")
```

#### `ProcessorNotAvailableError`

Raised when a required processor is not available.

**Inherits from:** `DocumentException`

**Attributes:**

- `processor_name` (str) - Name of unavailable processor
- `reason` (Optional[str]) - Reason for unavailability

**When raised:**

- Required library not installed (e.g., PyPDF2, python-docx)
- Processor initialisation fails
- Dependencies missing

**Example:**

```python
from backend.services.document import DocumentService, ProcessorNotAvailableError

try:
    service = DocumentService()
    result = service.process_document(
        file_path="/path/to/document.pdf",
        config={"extraction_mode": "unstructured"},
    )
except ProcessorNotAvailableError as e:
    print(f"Processor '{e.processor_name}' not available")
    print(f"Reason: {e.reason}")
    print("Install required dependencies or use a different extraction mode")
```

#### `CacheError`

Raised when cache operations fail.

**Inherits from:** `DocumentException`

**When raised:**

- Cache directory cannot be created
- Cache file cannot be written
- Cache file cannot be read (usually logged as warning, not raised)
- Cache cannot be cleared

**Example:**

```python
from backend.services.document import DocumentService, CacheError

try:
    service = DocumentService(cache_dir="/readonly/path")
except CacheError as e:
    print(f"Cache error: {e}")
    # Fallback: create service without caching
    service = DocumentService()
```

### Error Handling Patterns

**Recommended Pattern:**

```python
from backend.services.document import (
    DocumentService,
    DocumentException,
    DocumentProcessingError,
    UnsupportedFileTypeError,
    ProcessorNotAvailableError,
)
import logging

logger = logging.getLogger(__name__)

def process_document_safely(file_path: str) -> dict:
    """Process document with comprehensive error handling."""

    service = DocumentService()

    try:
        result = service.process_document(
            file_path=file_path,
            config={
                "extraction_mode": "auto",
                "fallback_on_error": True,
                "use_cache": True,
            },
        )

        if result["success"]:
            logger.info(f"Successfully processed {file_path}")
            return result
        else:
            logger.error(f"Processing failed: {result.get('error')}")
            return {"success": False, "error": result.get("error")}

    except UnsupportedFileTypeError as e:
        logger.error(f"Unsupported file type: {e.file_type}")
        return {
            "success": False,
            "error": f"File type not supported: {e.file_type}",
            "supported_types": e.supported_types,
        }

    except ProcessorNotAvailableError as e:
        logger.error(f"Processor unavailable: {e.processor_name}")
        return {
            "success": False,
            "error": f"Required processor not available: {e.processor_name}",
            "reason": e.reason,
        }

    except DocumentProcessingError as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "file_path": e.file_path,
            "processor": e.processor,
        }

    except DocumentException as e:
        logger.error(f"Document service error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "error": "An unexpected error occurred",
        }
```

**API Integration Pattern:**

```python
from fastapi import APIRouter, HTTPException, UploadFile
from backend.services.document import (
    DocumentService,
    UnsupportedFileTypeError,
    ProcessorNotAvailableError,
)

router = APIRouter()
document_service = DocumentService()

@router.post("/process")
async def process_document(file: UploadFile):
    """Process uploaded document."""

    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())

        # Process document
        result = document_service.process_document(
            file_path=temp_path,
            config={"extraction_mode": "auto"},
        )

        if not result["success"]:
            raise HTTPException(
                status_code=422,
                detail=result.get("error", "Processing failed"),
            )

        return result

    except UnsupportedFileTypeError as e:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {e.file_type}",
        )

    except ProcessorNotAvailableError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Processing service unavailable: {e.reason}",
        )
```

## Integration Patterns

### Integration with API Layer

The document service is typically used in API endpoints for processing uploaded files or existing documents.

**Example: File Upload Endpoint**

```python
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from pathlib import Path
import tempfile
from backend.services.document import DocumentService, ProcessingConfig

router = APIRouter(prefix="/documents", tags=["documents"])

def get_document_service() -> DocumentService:
    """Dependency for document service."""
    return DocumentService()

@router.post("/upload")
async def upload_and_process(
    file: UploadFile,
    extraction_mode: str = "auto",
    output_format: str = "markdown",
    service: DocumentService = Depends(get_document_service),
):
    """
    Upload and process a document.

    Args:
        file: Uploaded file
        extraction_mode: Processing mode
        output_format: Output format
        service: Document service instance

    Returns:
        Processing result with extracted content
    """

    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Process document
        result = service.process_document(
            file_path=tmp_path,
            config={
                "extraction_mode": extraction_mode,
                "output_format": output_format,
                "use_cache": False,  # Don't cache temp files
            },
        )

        if not result["success"]:
            raise HTTPException(status_code=422, detail=result.get("error"))

        return {
            "filename": file.filename,
            "content": result["content"],
            "metadata": result["metadata"],
            "extraction_method": result["extraction_method"],
        }

    finally:
        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)
```

**Example: Process Existing File**

```python
from fastapi import APIRouter, HTTPException, Depends
from backend.services.document import DocumentService, UnsupportedFileTypeError

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/process/{file_id}")
async def process_existing_file(
    file_id: str,
    extraction_mode: str = "auto",
    use_cache: bool = True,
    service: DocumentService = Depends(get_document_service),
):
    """Process an existing file by ID."""

    # Get file path from storage
    file_path = get_file_path_from_id(file_id)  # Your storage logic

    try:
        result = service.process_document(
            file_path=file_path,
            config={
                "extraction_mode": extraction_mode,
                "use_cache": use_cache,
            },
        )

        return result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

    except UnsupportedFileTypeError as e:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {e.file_type}",
        )
```

### Integration with Other Services

**Pattern 1: RAG Pipeline Integration**

```python
from backend.services.document import DocumentService
from backend.services.text_splitting import TextSplittingService
from backend.services.embedding import EmbeddingService

class RAGDocumentPipeline:
    """Pipeline for processing documents for RAG."""

    def __init__(self):
        self.document_service = DocumentService()
        self.text_splitter = TextSplittingService()
        self.embedding_service = EmbeddingService()

    async def process_for_rag(self, file_path: str) -> dict:
        """
        Process document for RAG system.

        Args:
            file_path: Path to document

        Returns:
            Processed chunks with embeddings
        """
        # Step 1: Extract content from document
        doc_result = self.document_service.process_document(
            file_path=file_path,
            config={
                "extraction_mode": "auto",
                "output_format": "markdown",
                "extract_tables": True,
                "include_metadata": True,
            },
        )

        if not doc_result["success"]:
            raise ValueError(f"Document processing failed: {doc_result['error']}")

        content = doc_result["content"]
        metadata = doc_result["metadata"]

        # Step 2: Split content into chunks
        chunks = self.text_splitter.split_text(
            text=content,
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Step 3: Generate embeddings
        embeddings = await self.embedding_service.embed_documents(chunks)

        # Step 4: Combine results
        return {
            "file_path": file_path,
            "metadata": metadata,
            "chunks": [
                {
                    "text": chunk,
                    "embedding": embedding,
                    "metadata": metadata,
                }
                for chunk, embedding in zip(chunks, embeddings)
            ],
        }
```

**Pattern 2: Batch Processing**

```python
from pathlib import Path
from typing import List
from backend.services.document import DocumentService, ProcessingConfig
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

class BatchDocumentProcessor:
    """Batch process multiple documents."""

    def __init__(self, max_workers: int = 4):
        self.service = DocumentService()
        self.max_workers = max_workers

    def process_directory(
        self,
        directory: str,
        config: ProcessingConfig,
        recursive: bool = True,
    ) -> List[dict]:
        """
        Process all documents in a directory.

        Args:
            directory: Directory path
            config: Processing configuration
            recursive: Process subdirectories

        Returns:
            List of processing results
        """
        # Find all supported files
        dir_path = Path(directory)
        patterns = ["*.pdf", "*.docx", "*.txt", "*.md"]

        files = []
        for pattern in patterns:
            if recursive:
                files.extend(dir_path.rglob(pattern))
            else:
                files.extend(dir_path.glob(pattern))

        logger.info(f"Found {len(files)} files to process")

        # Process files in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self.service.process_document,
                    str(file_path),
                    config.model_dump(),
                ): file_path
                for file_path in files
            }

            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Processed {file_path.name}")
                except Exception as e:
                    logger.error(f"Failed to process {file_path.name}: {e}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "file_path": str(file_path),
                    })

        return results
```

**Pattern 3: Document Validation**

```python
from backend.services.document import (
    DocumentService,
    is_supported_file_type,
    get_file_type_from_extension,
)
from pathlib import Path

class DocumentValidator:
    """Validate documents before processing."""

    def __init__(self):
        self.service = DocumentService()

    def validate_file(self, file_path: str) -> dict:
        """
        Validate a file can be processed.

        Args:
            file_path: Path to file

        Returns:
            Validation result with recommendations
        """
        path = Path(file_path)

        # Check file exists
        if not path.exists():
            return {
                "valid": False,
                "error": "File does not exist",
            }

        # Check file size
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > 100:
            return {
                "valid": False,
                "error": f"File too large: {size_mb:.2f} MB (max 100 MB)",
            }

        # Check file type
        file_type = get_file_type_from_extension(path.suffix)
        if not is_supported_file_type(file_type):
            return {
                "valid": False,
                "error": f"Unsupported file type: {file_type}",
            }

        # Try to process (with fallback disabled to detect issues)
        result = self.service.process_document(
            file_path=str(path),
            config={
                "extraction_mode": "auto",
                "fallback_on_error": False,
                "use_cache": False,
            },
        )

        return {
            "valid": result["success"],
            "file_type": file_type,
            "size_mb": size_mb,
            "extraction_method": result.get("extraction_method"),
            "error": result.get("error"),
        }
```

### Dependency Flow

**Services that document service depends on:**

- `backend.services.ocr` (optional) - For OCR processing

**Services that depend on document service:**

- API endpoints (file upload, document processing)
- RAG pipelines (document ingestion)
- Workflow nodes (document processing nodes)
- Batch processing services

**Data Flow:**

```
User Upload → API Endpoint → DocumentService
                                    ↓
                          ┌─────────┴─────────┐
                          ↓                   ↓
                    Extract Metadata    Select Processor
                          ↓                   ↓
                     Cache Check       Process Document
                          ↓                   ↓
                     Format Output      Update Metadata
                          ↓                   ↓
                     Cache Result    ← Return Result
                          ↓
                      Return to API
                          ↓
                    RAG Pipeline / Storage
```

## Usage Examples

### Example 1: Basic Usage

Process a PDF document with default settings:

```python
from backend.services.document import DocumentService

# Step 1: Initialise service
service = DocumentService()

# Step 2: Process document
result = service.process_document(
    file_path="/path/to/document.pdf",
    config={"extraction_mode": "auto"},
)

# Step 3: Check result and use content
if result["success"]:
    print("Content extracted successfully!")
    print(f"Method: {result['extraction_method']}")
    print(f"Pages: {result['metadata']['page_count']}")
    print(f"\nContent preview:\n{result['content'][:500]}...")
else:
    print(f"Failed to process document: {result['error']}")
```

### Example 2: Advanced Configuration

Process with detailed configuration for OCR and table extraction:

```python
from backend.services.document import DocumentService, ProcessingConfig

# Step 1: Create detailed configuration
config = ProcessingConfig(
    extraction_mode="unstructured",     # Use Unstructured.io
    output_format="json",               # Get structured JSON
    use_cache=True,                     # Enable caching
    fallback_on_error=True,             # Enable fallback
    extract_tables=True,                # Extract tables
    include_page_breaks=True,           # Include page markers
    include_metadata=True,              # Include element metadata
    max_partition_size=2000,            # Larger partitions
    combine_under_n_chars=300,          # Combine small elements
    language="eng",                     # English content
)

# Step 2: Initialise service with custom cache
service = DocumentService(cache_dir="/custom/cache")

# Step 3: Process document
result = service.process_document(
    file_path="/path/to/complex_document.pdf",
    config=config.model_dump(),
)

# Step 4: Process structured result
if result["success"]:
    elements = result["content"]  # JSON structure

    # Extract tables
    tables = [el for el in elements if el.get("type") == "table"]
    print(f"Found {len(tables)} tables")

    # Extract text elements
    text_elements = [el for el in elements if el.get("type") == "text"]
    print(f"Found {len(text_elements)} text elements")

    # Process each element
    for element in elements:
        print(f"Type: {element['type']}")
        print(f"Content: {element['text'][:100]}...")
        if element.get("metadata"):
            print(f"Page: {element['metadata'].get('page_number')}")
        print("---")
```

### Example 3: Complete RAG Workflow

Process documents for a RAG system with chunking and storage:

```python
from backend.services.document import DocumentService, ProcessingConfig
from backend.services.database import get_db_session
from backend.models import DocumentChunk
import hashlib

async def ingest_document_for_rag(
    file_path: str,
    collection_id: str,
    user_id: str,
) -> dict:
    """
    Complete workflow for ingesting a document into RAG system.

    Args:
        file_path: Path to document file
        collection_id: Collection to add document to
        user_id: User who owns the document

    Returns:
        Ingestion result with statistics
    """

    # Step 1: Initialise service
    service = DocumentService()

    # Step 2: Configure processing
    config = ProcessingConfig(
        extraction_mode="auto",
        output_format="markdown",
        use_cache=True,
        fallback_on_error=True,
        extract_tables=True,
        include_metadata=True,
        max_partition_size=1500,
        combine_under_n_chars=500,
    )

    try:
        # Step 3: Process document
        result = service.process_document(
            file_path=file_path,
            config=config.model_dump(),
        )

        if not result["success"]:
            return {
                "success": False,
                "error": result["error"],
            }

        content = result["content"]
        metadata = result["metadata"]

        # Step 4: Split into chunks (simple splitting)
        chunk_size = 1000
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk_text = content[i:i + chunk_size]

            # Create unique chunk ID
            chunk_id = hashlib.md5(
                f"{file_path}:{i}".encode()
            ).hexdigest()

            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "position": i,
                "size": len(chunk_text),
            })

        # Step 5: Store in database
        db = get_db_session()
        stored_chunks = []

        for chunk in chunks:
            db_chunk = DocumentChunk(
                id=chunk["id"],
                collection_id=collection_id,
                user_id=user_id,
                text=chunk["text"],
                metadata={
                    "filename": metadata["filename"],
                    "file_type": metadata["file_type"],
                    "position": chunk["position"],
                    "extraction_method": result["extraction_method"],
                },
            )
            db.add(db_chunk)
            stored_chunks.append(db_chunk)

        db.commit()

        # Step 6: Return success result
        return {
            "success": True,
            "document": {
                "filename": metadata["filename"],
                "file_type": metadata["file_type"],
                "size_mb": metadata["file_size_mb"],
                "page_count": metadata.get("page_count"),
            },
            "chunks": len(chunks),
            "extraction_method": result["extraction_method"],
            "collection_id": collection_id,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
```

### Example 4: Testing Usage

Examples for testing the document service:

```python
import pytest
from pathlib import Path
from backend.services.document import (
    DocumentService,
    ProcessingConfig,
    UnsupportedFileTypeError,
)

@pytest.fixture
def document_service(tmp_path):
    """Create document service with temp cache."""
    cache_dir = tmp_path / "cache"
    return DocumentService(cache_dir=cache_dir)

@pytest.fixture
def sample_text_file(tmp_path):
    """Create a sample text file."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("This is a test document.\nWith multiple lines.")
    return str(file_path)

def test_service_initialisation(document_service):
    """Test service initialises correctly."""
    assert document_service is not None
    assert document_service.cache_manager is not None
    assert "text" in document_service.processors
    assert "markdown" in document_service.formatters

def test_process_text_file(document_service, sample_text_file):
    """Test processing a text file."""
    result = document_service.process_document(
        file_path=sample_text_file,
        config={"extraction_mode": "text"},
    )

    assert result["success"] is True
    assert "test document" in result["content"]
    assert result["metadata"]["file_type"] == "text"
    assert result["extraction_method"] == "text"

def test_caching_behaviour(document_service, sample_text_file):
    """Test that caching works correctly."""
    config = {"extraction_mode": "text", "use_cache": True}

    # First call - should process
    result1 = document_service.process_document(sample_text_file, config)
    assert result1["success"] is True

    # Second call - should use cache
    result2 = document_service.process_document(sample_text_file, config)
    assert result2["success"] is True
    assert result1["content"] == result2["content"]

def test_unsupported_file_type(document_service, tmp_path):
    """Test handling of unsupported file type."""
    # Create file with unsupported extension
    file_path = tmp_path / "test.xyz"
    file_path.write_text("content")

    result = document_service.process_document(
        file_path=str(file_path),
        config={"fallback_on_error": False},
    )

    # Should fail without fallback
    assert result["success"] is False

def test_fallback_behaviour(document_service, tmp_path):
    """Test fallback processing on error."""
    # Create a text file with .xyz extension
    file_path = tmp_path / "test.xyz"
    file_path.write_text("This is actually text content")

    result = document_service.process_document(
        file_path=str(file_path),
        config={"fallback_on_error": True},
    )

    # Should succeed with fallback to text processor
    assert result["success"] is True or result["extraction_method"] == "fallback"

def test_config_validation():
    """Test configuration validation."""
    # Valid config
    config = ProcessingConfig(
        extraction_mode="auto",
        output_format="markdown",
    )
    assert config.extraction_mode == "auto"

    # Invalid extraction mode
    with pytest.raises(Exception):
        ProcessingConfig(extraction_mode="invalid_mode")

    # Invalid output format
    with pytest.raises(Exception):
        ProcessingConfig(output_format="invalid_format")

@pytest.mark.integration
def test_pdf_processing(document_service):
    """Integration test for PDF processing."""
    # This test requires a real PDF file
    pdf_path = "tests/fixtures/sample.pdf"

    if not Path(pdf_path).exists():
        pytest.skip("PDF test file not available")

    result = document_service.process_document(
        file_path=pdf_path,
        config={"extraction_mode": "auto"},
    )

    assert result["success"] is True
    assert len(result["content"]) > 0
    assert result["metadata"]["file_type"] == "pdf"
```

## Performance Considerations

### Performance Characteristics

**Complexity Analysis:**

- **File metadata extraction:** O(1) - File system stat operations
- **Text processing:** O(n) - Linear in file size
- **PDF processing:** O(n*p) - Linear in file size and number of pages
- **OCR processing:** O(n*p*r) - Linear in file size, pages, and resolution (most expensive)
- **Cache lookup:** O(1) - Hash-based key lookup
- **Cache storage:** O(n) - Linear in content size

**Memory Usage:**

- Service instance: ~10-50 MB (depending on loaded processors)
- Text processing: 1-2x file size (content in memory)
- PDF processing: 3-5x file size (page objects in memory)
- OCR processing: 5-10x file size (images in memory)
- Cache: Minimal (JSON serialisation to disk)

**I/O Characteristics:**

- **Text processor:** I/O-bound (file reading)
- **PDF processor:** Mixed CPU/I/O (parsing and extraction)
- **OCR processor:** CPU-bound (image processing and recognition)
- **Unstructured processor:** Mixed (depends on document complexity)
- **Cache operations:** I/O-bound (disk reads/writes)

### Optimisation Tips

#### Tip 1: Use Caching for Repeated Processing

**Problem:**

```python
# Processing same file multiple times without caching
for _ in range(10):
    result = service.process_document(
        file_path="large_document.pdf",
        config={"use_cache": False},  # Inefficient!
    )
```

**Solution:**

```python
# Enable caching for repeated processing
config = {"use_cache": True}

for _ in range(10):
    result = service.process_document(
        file_path="large_document.pdf",
        config=config,  # First call processes, rest use cache
    )
```

**Impact:** 10-100x faster for cached results (depending on document complexity)

#### Tip 2: Batch Processing with Parallelisation

**Problem:**

```python
# Sequential processing of multiple documents
results = []
for file_path in file_paths:
    result = service.process_document(file_path, config)
    results.append(result)
```

**Solution:**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

# Parallel processing of multiple documents
def process_file(file_path):
    return service.process_document(file_path, config)

results = []
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(process_file, fp): fp for fp in file_paths}

    for future in as_completed(futures):
        results.append(future.result())
```

**Impact:** 3-4x faster for I/O-bound operations (text, PDF), 1.5-2x for CPU-bound (OCR)

#### Tip 3: Selective Page Extraction

**Problem:**

```python
# Processing entire large document when only first page needed
result = service.process_document(
    file_path="large_document.pdf",  # 100 pages
    config={"extraction_mode": "auto"},  # Processes all pages
)
```

**Solution:**

```python
# Extract specific pages only
result = service.process_document(
    file_path="large_document.pdf",
    config={
        "extraction_mode": "auto",
        "page_numbers": [1, 2, 3],  # Only first 3 pages
    },
)
```

**Impact:** 10-50x faster for large documents when only few pages needed

#### Tip 4: Choose Appropriate Extraction Mode

**Problem:**

```python
# Using expensive OCR for text-based PDFs
result = service.process_document(
    file_path="text_document.pdf",
    config={"extraction_mode": "ocr"},  # Slow and unnecessary!
)
```

**Solution:**

```python
# Use appropriate mode for content type
result = service.process_document(
    file_path="text_document.pdf",
    config={"extraction_mode": "auto"},  # Intelligently selects best method
)

# Or explicitly choose for known content
result = service.process_document(
    file_path="scanned_image.pdf",
    config={"extraction_mode": "ocr"},  # OCR only when needed
)
```

**Impact:** 10-100x faster (text/PDF extraction vs OCR)

### Async/Await Support

The document service is currently synchronous but can be wrapped for async use:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from backend.services.document import DocumentService

class AsyncDocumentService:
    """Async wrapper for document service."""

    def __init__(self, cache_dir=None, executor=None):
        self.service = DocumentService(cache_dir=cache_dir)
        self.executor = executor or ThreadPoolExecutor(max_workers=4)

    async def process_document(
        self,
        file_path: str,
        config: dict,
        use_cache: bool = True,
    ) -> dict:
        """Process document asynchronously."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self.service.process_document,
            file_path,
            config,
            use_cache,
        )
        return result

    async def process_multiple(
        self,
        file_paths: list,
        config: dict,
    ) -> list:
        """Process multiple documents concurrently."""
        tasks = [
            self.process_document(fp, config)
            for fp in file_paths
        ]
        return await asyncio.gather(*tasks)

# Usage
async def main():
    service = AsyncDocumentService()

    # Process single document
    result = await service.process_document("doc.pdf", {})

    # Process multiple documents concurrently
    results = await service.process_multiple(
        ["doc1.pdf", "doc2.pdf", "doc3.pdf"],
        {"extraction_mode": "auto"},
    )

asyncio.run(main())
```

### Batch Operations

For processing multiple documents efficiently:

```python
from backend.services.document import DocumentService
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def batch_process_documents(
    file_paths: List[str],
    config: Dict,
    batch_size: int = 10,
) -> List[dict]:
    """
    Process documents in batches with progress tracking.

    Args:
        file_paths: List of file paths to process
        config: Processing configuration
        batch_size: Number of documents to process before logging progress

    Returns:
        List of processing results
    """
    service = DocumentService()
    results = []
    total = len(file_paths)

    for i, file_path in enumerate(file_paths, 1):
        try:
            result = service.process_document(file_path, config)
            results.append(result)

            # Log progress every batch_size documents
            if i % batch_size == 0:
                success_count = sum(1 for r in results if r["success"])
                logger.info(
                    f"Progress: {i}/{total} documents processed "
                    f"({success_count} successful)"
                )

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            results.append({"success": False, "error": str(e)})

    # Final summary
    success_count = sum(1 for r in results if r["success"])
    logger.info(
        f"Batch complete: {success_count}/{total} documents processed successfully"
    )

    return results
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from backend.services.document import DocumentService, ProcessingConfig
from backend.services.document.processors.text import TextProcessor

@pytest.fixture
def mock_cache_manager():
    """Mock cache manager."""
    mock = Mock()
    mock.get.return_value = None
    mock.set.return_value = None
    return mock

@pytest.fixture
def document_service(mock_cache_manager):
    """Service with mocked cache."""
    service = DocumentService()
    service.cache_manager = mock_cache_manager
    return service

def test_processor_selection(document_service):
    """Test processor selection logic."""
    # Text file should select text processor
    processor = document_service._get_processor("text", "text")
    assert isinstance(processor, TextProcessor)

def test_cache_hit(document_service, mock_cache_manager):
    """Test cache hit behaviour."""
    # Setup cache to return result
    cached_result = {
        "success": True,
        "content": "cached content",
    }
    mock_cache_manager.get.return_value = cached_result

    # Process should return cached result
    result = document_service.process_document(
        file_path="/path/to/file.txt",
        config={"use_cache": True},
    )

    assert result == cached_result
    mock_cache_manager.get.assert_called_once()

def test_fallback_on_error(document_service, tmp_path):
    """Test fallback processing on error."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Mock processor to fail
    with patch.object(
        document_service.processors["text"],
        "process",
        side_effect=Exception("Processing failed"),
    ):
        result = document_service.process_document(
            file_path=str(test_file),
            config={"fallback_on_error": True},
        )

        # Should attempt fallback
        assert "error" in result or result.get("extraction_method") == "fallback"
```

### Mocking Dependencies

```python
from unittest.mock import patch, Mock
import pytest
from backend.services.document import DocumentService

@pytest.fixture
def mock_processors():
    """Mock all processors."""
    with patch("backend.services.document.service.TextProcessor") as text_proc, \
         patch("backend.services.document.service.PDFProcessor") as pdf_proc, \
         patch("backend.services.document.service.OCRProcessor") as ocr_proc:

        # Setup mock returns
        text_proc.return_value.process.return_value = {
            "content": "mocked content",
            "extraction_method": "text",
        }

        yield {
            "text": text_proc,
            "pdf": pdf_proc,
            "ocr": ocr_proc,
        }

def test_with_mocked_processors(mock_processors, tmp_path):
    """Test service with mocked processors."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    service = DocumentService()
    result = service.process_document(
        file_path=str(test_file),
        config={"extraction_mode": "text"},
    )

    assert result["success"] is True
    assert "mocked content" in str(result["content"])
```

### Integration Testing

```python
import pytest
from pathlib import Path
from backend.services.document import DocumentService, ProcessingConfig

@pytest.mark.integration
class TestDocumentServiceIntegration:
    """Integration tests with real files and processors."""

    @pytest.fixture(scope="class")
    def test_files(self, tmp_path_factory):
        """Create test files."""
        tmp_dir = tmp_path_factory.mktemp("test_docs")

        # Create text file
        text_file = tmp_dir / "test.txt"
        text_file.write_text("This is a test document.")

        # Create markdown file
        md_file = tmp_dir / "test.md"
        md_file.write_text("# Test\n\nMarkdown content.")

        return {
            "text": str(text_file),
            "markdown": str(md_file),
        }

    def test_text_file_processing(self, test_files):
        """Test complete text file processing."""
        service = DocumentService()

        result = service.process_document(
            file_path=test_files["text"],
            config={
                "extraction_mode": "auto",
                "output_format": "markdown",
            },
        )

        assert result["success"] is True
        assert "test document" in result["content"]
        assert result["metadata"]["file_type"] == "text"
        assert result["metadata"]["filename"] == "test.txt"

    def test_end_to_end_workflow(self, test_files):
        """Test complete workflow from upload to storage."""
        service = DocumentService()

        # Process document
        result = service.process_document(
            file_path=test_files["markdown"],
            config=ProcessingConfig(
                extraction_mode="auto",
                output_format="json",
                use_cache=True,
            ).model_dump(),
        )

        assert result["success"] is True

        # Verify cache was used on second call
        result2 = service.process_document(
            file_path=test_files["markdown"],
            config=ProcessingConfig(
                extraction_mode="auto",
                output_format="json",
                use_cache=True,
            ).model_dump(),
        )

        assert result["content"] == result2["content"]
```

## Best Practices

### Do's

✅ **Use caching for production workloads:**

```python
# Enable caching for better performance
service = DocumentService()
result = service.process_document(
    file_path="document.pdf",
    config={"use_cache": True},  # Recommended for production
)
```

✅ **Enable fallback for robustness:**

```python
# Enable fallback to handle edge cases
result = service.process_document(
    file_path="document.pdf",
    config={
        "extraction_mode": "auto",
        "fallback_on_error": True,  # Graceful degradation
    },
)
```

✅ **Validate files before processing:**

```python
from pathlib import Path
from backend.services.document import is_supported_file_type, get_file_type_from_extension

def process_with_validation(file_path: str):
    """Process document with validation."""
    path = Path(file_path)

    # Check file exists
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check file size
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 100:
        raise ValueError(f"File too large: {size_mb:.2f} MB")

    # Check file type
    file_type = get_file_type_from_extension(path.suffix)
    if not is_supported_file_type(file_type):
        raise ValueError(f"Unsupported file type: {file_type}")

    # Process
    service = DocumentService()
    return service.process_document(file_path, {"extraction_mode": "auto"})
```

✅ **Use appropriate extraction mode for known content:**

```python
# For text-based documents
result = service.process_document(
    file_path="report.pdf",
    config={"extraction_mode": "unstructured"},  # Best for PDFs with text
)

# For scanned images
result = service.process_document(
    file_path="scanned.png",
    config={"extraction_mode": "ocr"},  # Explicit OCR
)
```

✅ **Handle errors appropriately:**

```python
from backend.services.document import DocumentException

try:
    result = service.process_document(file_path, config)
    if not result["success"]:
        logger.error(f"Processing failed: {result['error']}")
        # Handle gracefully
except DocumentException as e:
    logger.error(f"Document error: {e}", exc_info=True)
    # Handle gracefully
```

### Don'ts

❌ **Don't disable caching without good reason:**

```python
# Anti-pattern: Disabling cache unnecessarily
for file_path in file_paths:
    result = service.process_document(
        file_path=file_path,
        config={"use_cache": False},  # Wasteful!
    )
```

**Why:** Caching provides significant performance improvements for repeated operations. Only disable when processing
temporary files or when content changes frequently.

❌ **Don't use OCR for all file types:**

```python
# Anti-pattern: Forcing OCR for everything
result = service.process_document(
    file_path="text_document.pdf",
    config={"extraction_mode": "ocr"},  # Slow and unnecessary!
)
```

**Why:** OCR is expensive and only needed for scanned images. Use "auto" mode to let the service select the best method.

❌ **Don't process files without validation:**

```python
# Anti-pattern: No validation
result = service.process_document(
    file_path=user_provided_path,  # Could be anything!
    config={},
)
```

**Why:** Always validate file existence, size, and type before processing to avoid security issues and provide better
error messages.

❌ **Don't ignore processing errors:**

```python
# Anti-pattern: Ignoring errors
result = service.process_document(file_path, config)
content = result["content"]  # Could fail if result["success"] is False!
```

**Why:** Always check `result["success"]` before using content. Failing silently can cause downstream issues.

❌ **Don't create multiple service instances unnecessarily:**

```python
# Anti-pattern: Creating new service for each file
for file_path in file_paths:
    service = DocumentService()  # Wasteful!
    result = service.process_document(file_path, config)
```

**Why:** Service initialisation loads processors and creates cache manager. Reuse a single instance:

```python
# Good pattern: Reuse service instance
service = DocumentService()
for file_path in file_paths:
    result = service.process_document(file_path, config)
```

## Related Documentation

### Related Services

- [OCR Service](./ocr.md) - OCR processing for images (legacy, used by OCRProcessor)
- [Database Service](./database.md) - Database operations for storing processed documents

### Related API Modules

- [Graph API](../agents-guide/api/graph.md) - Uses document service for file input nodes
- [Workflow API](../agents-guide/api/workflow.md) - Document processing in workflow nodes

### External Documentation

- [Unstructured.io](https://unstructured.io/) - Advanced document processing library
- [PyPDF2](https://pypdf2.readthedocs.io/) - PDF processing library
- [python-docx](https://python-docx.readthedocs.io/) - Word document processing
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - OCR library
- [Pydantic](https://docs.pydantic.dev/) - Data validation library

## Summary

The Document Service is a comprehensive document processing system for AgenticStudio that intelligently handles multiple
file formats including PDFs, Word documents, Excel spreadsheets, text files, and images. It provides a unified interface
that automatically selects the best processing method based on file type and user configuration, with built-in caching
for performance and fallback mechanisms for reliability.

The service uses a Strategy pattern for both processors (text, PDF, DOCX, Excel, OCR, Unstructured) and formatters (
markdown, JSON, elements), making it extensible and maintainable. It integrates seamlessly with AgenticStudio's RAG
pipelines, workflow nodes, and API endpoints to provide document ingestion capabilities.

**Key Features:**

- Multi-format support (PDF, DOCX, XLSX, TXT, MD, images)
- Intelligent processor selection (auto or explicit)
- Multiple output formats (markdown, JSON, structured elements)
- Transparent result caching for performance
- Graceful error handling with configurable fallback
- Comprehensive metadata extraction
- Table extraction and structured content support
- OCR capabilities for scanned documents
- Page-level and selective extraction

**Primary Use Cases:**

- Processing uploaded documents in API endpoints
- Extracting content for RAG (Retrieval-Augmented Generation) systems
- Batch document processing pipelines
- Converting documents to structured formats
- OCR processing of scanned documents and images

**When to Use This Service:**

- Building document upload and processing features
- Implementing RAG document ingestion pipelines
- Creating document conversion or extraction tools
- Processing documents in workflow nodes
- Extracting structured data from various document types
