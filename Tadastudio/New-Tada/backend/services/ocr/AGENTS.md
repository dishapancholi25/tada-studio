# OCR Service Documentation

## Overview

The OCR (Optical Character Recognition) service provides text extraction capabilities from various document formats
including images, PDFs, DOCX files, and plain text documents. The service offers two implementations: a modern GPT-4o
Vision-based OCR system for high accuracy and a legacy OCR service using traditional engines like EasyOCR and Tesseract.

**Location:** [backend/services/ocr/](../../backend/services/ocr/)

**Primary Responsibilities:**

- Extract text from images using GPT-4o Vision API
- Process multi-page PDF documents with page-by-page extraction
- Extract text and images from DOCX documents
- Support multiple document types with specialised prompts (resumes, invoices, forms, tables, handwritten text)
- Provide flexible file handling (file paths and byte streams)
- Offer legacy OCR support for traditional OCR engines

**Key Use Cases:**

- Document digitisation and text extraction from scanned documents
- Resume/CV parsing for structured information extraction
- Invoice and receipt data extraction
- Form processing and data capture
- Table extraction from images or PDFs
- Handwritten text recognition

## Architecture

### Module Structure

```
backend/services/ocr/
├── __init__.py              # Module exports and factory functions
├── base.py                  # Abstract base class for OCR processors
├── config.py                # Configuration constants and default prompts
├── exceptions.py            # Custom exception classes
├── models.py                # Pydantic models for requests/responses
├── service.py               # Main GPT4oOCRService orchestrator
├── legacy_ocr_service.py    # Legacy OCR service implementation
├── processors/              # File type-specific processors
│   ├── __init__.py
│   ├── image.py            # Image processor using GPT-4o Vision
│   ├── pdf.py              # PDF processor with page-by-page extraction
│   ├── docx.py             # DOCX processor with image extraction
│   └── text.py             # Direct text file processor
└── utils/                   # Utility functions
    ├── __init__.py
    ├── encoding.py         # Base64 image encoding utilities
    ├── file_handling.py    # File validation and loading utilities
    └── result_builder.py   # Response object builder utilities
```

### Design Patterns

**Strategy Pattern:** The service uses a strategy pattern with specialised processors for different file types. Each
processor implements the `OCRProcessor` abstract base class and handles a specific file format (images, PDFs, DOCX,
text).

**Factory Pattern:** The module provides factory functions (`create_gpt4o_ocr_service()` and
`create_legacy_ocr_service()`) to create properly configured service instances with appropriate dependencies.

**Template Method Pattern:** The `OCRProcessor` base class defines the processing interface (`process()` and
`supports_file_type()`) that all concrete processors must implement.

**Component Relationships:**

```
┌─────────────────────────────────────────────────────────────┐
│                    GPT4oOCRService                          │
│  (Orchestrator - routes requests to processors)             │
└───────────────┬─────────────────────────────────────────────┘
                │
                │ creates and manages
                ▼
    ┌───────────────────────────────────┐
    │     Processor Registry (dict)      │
    └───────┬───────────────────────────┘
            │
            │ contains
            ▼
┌───────────────────────────────────────────────────────────┐
│                   OCRProcessor (ABC)                       │
│                  - process()                               │
│                  - supports_file_type()                    │
└─────┬────────────────────────────────────────────────────┘
      │
      │ implemented by
      │
      ├─── ImageProcessor ──► GPT-4o Vision API
      ├─── PDFProcessor ────► GPT-4o Vision API (per page)
      ├─── DOCXProcessor ───► Text + Image extraction
      └─── TextProcessor ───► Direct file reading
```

### Dependencies

**Internal Dependencies:**

- None (self-contained service module)

**External Dependencies:**

- `openai` - Azure OpenAI SDK for GPT-4o Vision API
- `pydantic` - Data validation and settings management
- `pdf2image` - PDF to image conversion (used in PDF processor)
- `python-docx` - DOCX file reading (used in DOCX processor)
- `Pillow` - Image manipulation and encoding
- Legacy OCR engines (optional):
  - `easyocr` - EasyOCR library
  - `paddleocr` - PaddleOCR library
  - `pytesseract` - Tesseract OCR wrapper

**Database Dependencies:**

- None (stateless service)

**Environment Variables:**

- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key (required for GPT-4o service)
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL (required for GPT-4o service)
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Model deployment name (default: `gpt-4o-latest`)
- `AZURE_OPENAI_API_VERSION` - API version (default: `2024-02-01`)

## Public API

### Exported Classes

- `GPT4oOCRService` - Main OCR service using GPT-4o Vision API
- `OCRService` - Legacy OCR service using traditional engines (EasyOCR, Tesseract, etc.)
- `OCRRequest` - Request model for OCR processing
- `OCRResponse` - Response model with extracted text and metadata
- `PageResult` - Result for a single page in multi-page documents
- `AzureOpenAIConfig` - Configuration for Azure OpenAI client
- `LegacyOCRResponse` - Response model for legacy OCR services

### Exported Functions

- `get_default_prompt(doc_type)` - Get default OCR prompt for a document type
- `auto_detect_doc_type(file_path)` - Auto-detect document type from file path
- `create_gpt4o_ocr_service(azure_config)` - Factory function to create GPT-4o OCR service
- `create_legacy_ocr_service(library, language)` - Factory function to create legacy OCR service

### Constants and Configuration

- `ALL_SUPPORTED_EXTENSIONS` - List of all supported file extensions
- `DEFAULT_OCR_PROMPTS` - Dictionary of default prompts for each document type
- `SUPPORTED_IMAGE_EXTENSIONS` - List: `[".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]`
- `SUPPORTED_PDF_EXTENSIONS` - List: `[".pdf"]`
- `SUPPORTED_DOCX_EXTENSIONS` - List: `[".docx", ".doc"]`
- `SUPPORTED_TEXT_EXTENSIONS` - List: `[".txt", ".md", ".csv"]`
- `DEFAULT_MAX_TOKENS` - Default maximum tokens: `4000`
- `DEFAULT_MAX_FILE_SIZE_MB` - Default maximum file size: `10` MB
- `DEFAULT_TEMPERATURE` - Default temperature for GPT-4o: `0.1`

### Exceptions

```
Exception
└── OCRException
    ├── OCRConfigError
    ├── OCRProcessingError
    ├── UnsupportedFileTypeError
    ├── FileSizeExceededError
    ├── FileNotFoundError
    └── InvalidInputError
```

## Core Classes

### `GPT4oOCRService`

Main service class for performing OCR using GPT-4o Vision API.

**Purpose:** Provides a unified interface for text extraction from various document formats using Azure OpenAI's GPT-4o
Vision model.

**Responsibilities:**

- Orchestrate OCR processing across different file types
- Manage Azure OpenAI client configuration and initialisation
- Route requests to appropriate file type processors
- Provide convenience methods for specific file types (images, PDFs, DOCX)
- Handle auto-detection of document types and prompt selection

**Initialisation:**

```python
def __init__(
    self,
    azure_config: Optional[Dict[str, str]] = None,
) -> None:
    """
    Initialise GPT-4o OCR service with Azure OpenAI configuration.

    Args:
        azure_config: Optional dictionary with Azure OpenAI configuration
            - api_key: Azure OpenAI API key
            - endpoint: Azure OpenAI endpoint URL
            - deployment_name: Model deployment name (default: gpt-4o-latest)
            - api_version: API version (default: 2024-02-01)
            If None, configuration is loaded from environment variables.

    Raises:
        OCRConfigError: If configuration is invalid or missing
    """
```

**Key Methods:**

#### `process_file()`

```python
def process_file(
    self,
    file_path: str,
    prompt: Optional[str] = None,
    doc_type: str = "auto",
    **kwargs,
) -> Dict:
    """Process any supported file type."""
```

**Parameters:**

- `file_path` (str) - Path to the file to process
- `prompt` (Optional[str]) - Custom OCR prompt (default: None, uses prompt for doc_type)
- `doc_type` (str) - Document type for prompt selection: `auto`, `generic`, `resume`, `invoice`, `form`, `table`,
  `handwritten` (default: `auto`)
- `**kwargs` - Additional arguments:
  - `max_pages` (Optional[int]) - Maximum pages to process for PDFs
  - `chunk_by_page` (bool) - Return results separated by page (default: False)
  - `max_tokens` (int) - Maximum tokens for API response (default: 4000)

**Returns:**

- `Dict` - Dictionary with extraction results (OCRResponse as dict):
  - `success` (bool) - Whether processing succeeded
  - `text` (str) - Extracted text content
  - `extraction_method` (str) - Method used (e.g., `gpt4o_vision`, `direct_text`)
  - `tokens_used` (int) - Total tokens consumed
  - `page_count` (Optional[int]) - Number of pages processed
  - `pages` (Optional[List[PageResult]]) - Per-page results if `chunk_by_page=True`

**Raises:**

- `UnsupportedFileTypeError` - If file type is not supported
- `OCRProcessingError` - If processing fails

**Example:**

```python
from backend.services.ocr import GPT4oOCRService

# Initialise service
service = GPT4oOCRService()

# Process a resume with auto-detection
result = service.process_file(
    file_path="/path/to/resume.pdf",
    doc_type="auto",  # Will detect "resume" from filename
    max_pages=5,
)

print(f"Extracted {len(result['text'])} characters")
print(f"Used {result['tokens_used']} tokens")
```

**Behaviour:**

- Validates file extension against supported types
- Auto-detects document type from filename if `doc_type="auto"`
- Selects appropriate processor based on file extension
- Uses default prompt for document type if no custom prompt provided
- Logs processing information for debugging

**Use Cases:**

- Processing files of unknown or mixed types in a workflow
- Applying type-specific extraction logic (resume parsing, invoice extraction)
- Batch processing with automatic document type detection

#### `process_image()`

```python
def process_image(
    self,
    image_path: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
    prompt: Optional[str] = None,
    max_tokens: int = 4000,
) -> Dict:
    """Process a single image using GPT-4o Vision."""
```

**Parameters:**

- `image_path` (Optional[str]) - Path to image file
- `image_bytes` (Optional[bytes]) - Image data as bytes (alternative to file path)
- `prompt` (Optional[str]) - Custom OCR prompt
- `max_tokens` (int) - Maximum tokens for response (default: 4000)

**Returns:**

- `Dict` - OCRResponse as dictionary with extracted text and metadata

**Raises:**

- `InvalidInputError` - If neither image_path nor image_bytes provided
- `OCRProcessingError` - If image processing fails

**Example:**

```python
# Process image from file path
result = service.process_image(
    image_path="/path/to/document.png",
    prompt="Extract all text, preserving formatting",
    max_tokens=4000,
)

# Process image from bytes
with open("/path/to/image.jpg", "rb") as f:
    image_data = f.read()

result = service.process_image(
    image_bytes=image_data,
    prompt="Extract table data as markdown",
)
```

**Behaviour:**

- Accepts either file path or byte stream input
- Encodes image to base64 for API submission
- Supports all common image formats (PNG, JPG, GIF, BMP, TIFF)
- Returns token usage for cost tracking

**Use Cases:**

- Single image text extraction
- Screenshot text extraction
- Scanned document processing

#### `process_pdf()`

```python
def process_pdf(
    self,
    pdf_path: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    prompt: Optional[str] = None,
    max_pages: Optional[int] = None,
    chunk_by_page: bool = False,
) -> Dict:
    """Process PDF document page by page using GPT-4o Vision."""
```

**Parameters:**

- `pdf_path` (Optional[str]) - Path to PDF file
- `pdf_bytes` (Optional[bytes]) - PDF data as bytes
- `prompt` (Optional[str]) - Custom OCR prompt applied to each page
- `max_pages` (Optional[int]) - Maximum number of pages to process (default: None, process all)
- `chunk_by_page` (bool) - Return results separated by page (default: False)

**Returns:**

- `Dict` - OCRResponse as dictionary with:
  - `text` (str) - Combined text from all pages (if `chunk_by_page=False`)
  - `pages` (List[PageResult]) - Per-page results (if `chunk_by_page=True`)
  - `page_count` (int) - Number of pages processed
  - `tokens_used` (int) - Total tokens across all pages

**Raises:**

- `OCRProcessingError` - If PDF conversion or processing fails
- `InvalidInputError` - If neither pdf_path nor pdf_bytes provided

**Example:**

```python
# Process entire PDF with combined output
result = service.process_pdf(
    pdf_path="/path/to/report.pdf",
    prompt="Extract all text and tables",
)

print(f"Processed {result['page_count']} pages")
print(result['text'])

# Process first 3 pages with per-page results
result = service.process_pdf(
    pdf_path="/path/to/large_document.pdf",
    max_pages=3,
    chunk_by_page=True,
)

for page in result['pages']:
    print(f"Page {page['page']}: {page['text'][:100]}...")
```

**Behaviour:**

- Converts each PDF page to an image at 2x scale
- Processes pages sequentially using GPT-4o Vision
- Aggregates token usage across all pages
- Can combine text from all pages or return separately
- Handles multi-page documents efficiently

**Use Cases:**

- Multi-page document extraction
- Large PDF processing with page limits
- Per-page analysis for structured documents

#### `process_docx()`

```python
def process_docx(
    self,
    docx_path: Optional[str] = None,
    docx_bytes: Optional[bytes] = None,
    prompt: Optional[str] = None,
) -> Dict:
    """Process DOCX document, extracting text and processing embedded images."""
```

**Parameters:**

- `docx_path` (Optional[str]) - Path to DOCX file
- `docx_bytes` (Optional[bytes]) - DOCX data as bytes
- `prompt` (Optional[str]) - Custom OCR prompt for embedded images

**Returns:**

- `Dict` - OCRResponse as dictionary with:
  - `text` (str) - Combined text from document body and images
  - `has_images` (bool) - Whether document contained images
  - `extraction_method` (str) - `docx_text` or `docx_with_images`

**Raises:**

- `OCRProcessingError` - If DOCX reading fails
- `InvalidInputError` - If neither docx_path nor docx_bytes provided

**Example:**

```python
# Process DOCX with embedded images
result = service.process_docx(
    docx_path="/path/to/proposal.docx",
    prompt="Extract text from any images or diagrams",
)

if result['has_images']:
    print("Document contained images that were processed")

print(result['text'])
```

**Behaviour:**

- Extracts direct text from DOCX document structure
- Identifies and extracts embedded images
- Processes images using GPT-4o Vision if present
- Combines document text and image-extracted text
- Marks whether images were found and processed

**Use Cases:**

- DOCX document text extraction
- Processing documents with embedded screenshots or diagrams
- Comprehensive document content extraction

#### `get_default_prompt()` (Static Method)

```python
@staticmethod
def get_default_prompt(doc_type: str = "generic") -> str:
    """Get default OCR prompt for a document type."""
```

**Parameters:**

- `doc_type` (str) - Document type: `generic`, `resume`, `invoice`, `form`, `table`, `handwritten`

**Returns:**

- `str` - Default prompt optimised for the document type

**Example:**

```python
# Get prompt for invoice processing
invoice_prompt = GPT4oOCRService.get_default_prompt("invoice")
print(invoice_prompt)
# Output: "Extract all data from this invoice/receipt. Include:
#          - Document number and date
#          - Vendor/seller information..."
```

**Use Cases:**

- Understanding default prompts for customisation
- Reusing default prompts with modifications
- Document type-specific processing

**Class Attributes:**

- `config: AzureOpenAIConfig` - Azure OpenAI configuration
- `client: AzureOpenAI` - Azure OpenAI client instance
- `processors: dict` - Dictionary mapping file types to processors

### `OCRRequest`

Pydantic model for OCR processing requests.

**Purpose:** Validate and structure OCR request parameters.

**Fields:**

```python
class OCRRequest(BaseModel):
    file_path: Optional[str] = None
    file_bytes: Optional[bytes] = None
    prompt: Optional[str] = None
    doc_type: str = "auto"
    max_tokens: int = 4000
    max_pages: Optional[int] = None
    chunk_by_page: bool = False
```

**Field Descriptions:**

- `file_path` (Optional[str]) - Path to file to process
- `file_bytes` (Optional[bytes]) - File content as bytes
- `prompt` (Optional[str]) - Custom OCR prompt
- `doc_type` (str) - Document type: `auto`, `generic`, `resume`, `invoice`, `form`, `table`, `handwritten` (default:
  `auto`)
- `max_tokens` (int) - Maximum tokens for API response (1-16000, default: 4000)
- `max_pages` (Optional[int]) - Maximum pages to process for multi-page documents
- `chunk_by_page` (bool) - Return results separated by page (default: False)

**Validators:**

- `validate_doc_type()` - Ensures doc_type is one of the valid values
- `validate_max_tokens()` - Ensures max_tokens is between 1 and 16000

**Example:**

```python
from backend.services.ocr import OCRRequest

# Create request with validation
request = OCRRequest(
    file_path="/path/to/resume.pdf",
    doc_type="resume",
    max_tokens=6000,
    max_pages=5,
)

# Validation error example
try:
    invalid_request = OCRRequest(
        file_path="/path/to/file.pdf",
        doc_type="invalid_type",  # Will raise ValidationError
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

### `OCRResponse`

Pydantic model for OCR processing responses.

**Purpose:** Structure OCR results with consistent metadata.

**Fields:**

```python
class OCRResponse(BaseModel):
    success: bool
    text: str = ""
    extraction_method: str
    tokens_used: int = 0
    total_tokens: int = 0
    error: Optional[str] = None
    page_count: Optional[int] = None
    pages: Optional[List[PageResult]] = None
    has_images: Optional[bool] = None
    model: Optional[str] = None
```

**Field Descriptions:**

- `success` (bool) - Whether processing succeeded
- `text` (str) - Extracted text content
- `extraction_method` (str) - Method used: `gpt4o_vision`, `direct_text`, `docx_text`, etc.
- `tokens_used` (int) - Total tokens used (for API-based methods)
- `total_tokens` (int) - Alias for tokens_used (automatically synced)
- `error` (Optional[str]) - Error message if processing failed
- `page_count` (Optional[int]) - Number of pages processed
- `pages` (Optional[List[PageResult]]) - Per-page results for chunked output
- `has_images` (Optional[bool]) - Whether document contained processed images
- `model` (Optional[str]) - Model used for processing

**Example:**

```python
from backend.services.ocr import OCRResponse, PageResult

# Successful response
response = OCRResponse(
    success=True,
    text="Extracted document text...",
    extraction_method="gpt4o_vision",
    tokens_used=1250,
    page_count=3,
)

# Response with per-page results
response = OCRResponse(
    success=True,
    text="",  # Empty when using chunk_by_page
    extraction_method="gpt4o_vision",
    tokens_used=2500,
    page_count=5,
    pages=[
        PageResult(page=1, text="Page 1 text...", tokens=500),
        PageResult(page=2, text="Page 2 text...", tokens=600),
        # ...
    ],
)

# Error response
error_response = OCRResponse(
    success=False,
    text="",
    extraction_method="gpt4o_vision",
    error="File not found: /invalid/path.pdf",
)
```

### `PageResult`

Result model for a single page in multi-page documents.

**Purpose:** Store per-page extraction results with metadata.

**Fields:**

```python
class PageResult(BaseModel):
    page: int           # Page number (1-indexed)
    text: str = ""      # Extracted text from page
    tokens: int = 0     # Tokens used for this page
    error: Optional[str] = None  # Error message if page processing failed
```

**Example:**

```python
from backend.services.ocr import PageResult

page_result = PageResult(
    page=1,
    text="First page content...",
    tokens=450,
)

# Page with error
failed_page = PageResult(
    page=5,
    text="",
    tokens=0,
    error="Image conversion failed for page 5",
)
```

### `AzureOpenAIConfig`

Configuration model for Azure OpenAI client.

**Purpose:** Validate and store Azure OpenAI connection settings.

**Fields:**

```python
class AzureOpenAIConfig(BaseModel):
    api_key: str
    endpoint: str
    deployment_name: str = "gpt-4o-latest"
    api_version: str = "2024-02-01"
```

**Field Descriptions:**

- `api_key` (str) - Azure OpenAI API key (required)
- `endpoint` (str) - Azure OpenAI endpoint URL (required, must start with http:// or https://)
- `deployment_name` (str) - Model deployment name (default: `gpt-4o-latest`)
- `api_version` (str) - API version (default: `2024-02-01`)

**Validators:**

- `validate_endpoint()` - Ensures endpoint is a valid URL

**Example:**

```python
from backend.services.ocr import AzureOpenAIConfig

config = AzureOpenAIConfig(
    api_key="your-api-key",
    endpoint="https://your-resource.openai.azure.com/",
    deployment_name="gpt-4o-latest",
    api_version="2024-02-01",
)
```

## Functions

### `get_default_prompt()`

Get the default OCR prompt for a specific document type.

**Signature:**

```python
def get_default_prompt(doc_type: str = "generic") -> str:
    """
    Get default OCR prompt for a document type.

    Args:
        doc_type: Type of document (generic, resume, invoice, form, table, handwritten)

    Returns:
        Default prompt string optimised for the document type
    """
```

**Parameters:**

- `doc_type` (str) - Document type identifier (default: `generic`)

**Returns:**

- `str` - Default prompt string

**Example:**

```python
from backend.services.ocr import get_default_prompt

# Get resume extraction prompt
resume_prompt = get_default_prompt("resume")
print(resume_prompt)
# Output: "Extract all information from this resume/CV..."

# Get generic prompt
generic_prompt = get_default_prompt()  # defaults to "generic"
```

**Use Cases:**

- Understanding what instructions are sent to GPT-4o
- Customising default prompts for specific use cases
- Building prompt templates for new document types

### `auto_detect_doc_type()`

Auto-detect document type from file path based on filename keywords.

**Signature:**

```python
def auto_detect_doc_type(file_path: str) -> str:
    """
    Auto-detect document type from file path.

    Args:
        file_path: Path to the file

    Returns:
        Detected document type: 'resume', 'invoice', 'form', or 'generic'
    """
```

**Parameters:**

- `file_path` (str) - Path to the file (can be relative or absolute)

**Returns:**

- `str` - Detected document type

**Example:**

```python
from backend.services.ocr import auto_detect_doc_type

# Detects 'resume' from filename
doc_type = auto_detect_doc_type("/uploads/john_doe_resume.pdf")
assert doc_type == "resume"

# Detects 'invoice' from filename
doc_type = auto_detect_doc_type("/invoices/receipt_2024.png")
assert doc_type == "invoice"

# Falls back to 'generic'
doc_type = auto_detect_doc_type("/documents/random_file.pdf")
assert doc_type == "generic"
```

**Detection Rules:**

- Filename contains "resume" or "cv" → `resume`
- Filename contains "invoice" or "receipt" → `invoice`
- Filename contains "form" → `form`
- Otherwise → `generic`

**Use Cases:**

- Automatic prompt selection based on filename conventions
- Smart document routing in batch processing
- User-friendly file upload handling

### `create_gpt4o_ocr_service()`

Factory function to create a configured GPT-4o OCR service instance.

**Signature:**

```python
def create_gpt4o_ocr_service(
    azure_config: Optional[Dict[str, str]] = None
) -> GPT4oOCRService:
    """
    Create GPT-4o OCR service.

    Args:
        azure_config: Optional Azure OpenAI configuration dict
            - api_key: Azure OpenAI API key
            - endpoint: Azure OpenAI endpoint
            - deployment_name: Model deployment name
            - api_version: API version

    Returns:
        Configured GPT4oOCRService instance
    """
```

**Parameters:**

- `azure_config` (Optional[Dict[str, str]]) - Azure OpenAI configuration (default: None, loads from environment)

**Returns:**

- `GPT4oOCRService` - Configured service instance

**Example:**

```python
from backend.services.ocr import create_gpt4o_ocr_service

# Create with environment variables
service = create_gpt4o_ocr_service()

# Create with explicit configuration
service = create_gpt4o_ocr_service(
    azure_config={
        "api_key": "your-api-key",
        "endpoint": "https://your-resource.openai.azure.com/",
        "deployment_name": "gpt-4o-latest",
        "api_version": "2024-02-01",
    }
)
```

**Use Cases:**

- Dependency injection in API routes
- Testing with different configurations
- Creating multiple service instances with different credentials

### `create_legacy_ocr_service()`

Factory function to create a legacy OCR service using traditional engines.

**Signature:**

```python
def create_legacy_ocr_service(
    library: str = "easyocr",
    language: str = "en",
):
    """
    Create legacy OCR service.

    Args:
        library: OCR library to use (easyocr, paddleocr, tesseract, etc.)
        language: Language code for OCR (default: en)

    Returns:
        Configured OCRService instance

    Raises:
        ImportError: If legacy OCR service is not available
    """
```

**Parameters:**

- `library` (str) - OCR engine: `easyocr`, `paddleocr`, `tesseract` (default: `easyocr`)
- `language` (str) - Language code (default: `en`)

**Returns:**

- `OCRService` - Configured legacy OCR service instance

**Raises:**

- `ImportError` - If legacy_ocr_service.py is not available

**Example:**

```python
from backend.services.ocr import create_legacy_ocr_service

# Create EasyOCR service
service = create_legacy_ocr_service(library="easyocr", language="en")

# Create Tesseract service
service = create_legacy_ocr_service(library="tesseract", language="en")
```

**Use Cases:**

- Offline OCR processing without API dependencies
- Cost-conscious text extraction
- Traditional OCR engine integration

## Configuration

### Configuration Classes

The service uses Pydantic models for configuration:

```python
class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI configuration."""

    api_key: str
    endpoint: str
    deployment_name: str = "gpt-4o-latest"
    api_version: str = "2024-02-01"
```

**Fields:**

- `api_key` - Azure OpenAI API key (required)
- `endpoint` - Azure OpenAI endpoint URL (required)
- `deployment_name` - Model deployment name (default: `gpt-4o-latest`)
- `api_version` - API version (default: `2024-02-01`)

### Environment Variables

The service loads configuration from environment variables when no explicit configuration is provided:

- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key (required: yes)
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint URL (required: yes)
- `AZURE_OPENAI_DEPLOYMENT_NAME` - Model deployment name (default: `gpt-4o-latest`, required: no)
- `AZURE_OPENAI_API_VERSION` - API version (default: `2024-02-01`, required: no)

### Initialisation Patterns

**Basic Initialisation (Environment Variables):**

```python
from backend.services.ocr import GPT4oOCRService

# Loads configuration from environment variables
service = GPT4oOCRService()
```

**Advanced Initialisation (Explicit Configuration):**

```python
from backend.services.ocr import GPT4oOCRService

# Explicit configuration
service = GPT4oOCRService(
    azure_config={
        "api_key": "your-api-key",
        "endpoint": "https://your-resource.openai.azure.com/",
        "deployment_name": "gpt-4o-latest",
        "api_version": "2024-02-01",
    }
)
```

**Factory Function Pattern:**

```python
from backend.services.ocr import create_gpt4o_ocr_service

# Using factory function
service = create_gpt4o_ocr_service(
    azure_config={
        "api_key": "your-api-key",
        "endpoint": "https://your-resource.openai.azure.com/",
    }
)
```

**Dependency Injection:**

```python
from fastapi import Depends
from backend.services.ocr import GPT4oOCRService

def get_ocr_service() -> GPT4oOCRService:
    """Dependency for FastAPI routes."""
    return GPT4oOCRService()

@router.post("/process-document")
async def process_document(
    service: GPT4oOCRService = Depends(get_ocr_service)
):
    # Use service in route
    result = service.process_file("/path/to/file.pdf")
    return result
```

## Error Handling

### Exception Hierarchy

```
Exception
└── OCRException (Base exception for all OCR errors)
    ├── OCRConfigError (Configuration errors)
    ├── OCRProcessingError (Processing failures)
    ├── UnsupportedFileTypeError (Invalid file types)
    ├── FileSizeExceededError (File too large)
    ├── FileNotFoundError (Missing files)
    └── InvalidInputError (Invalid parameters)
```

### Exception Details

#### `OCRException`

Base exception for all OCR-related errors.

**Inherits from:** `Exception`

**When raised:**

- Never raised directly, only used as base class for other exceptions

#### `OCRConfigError`

Raised when OCR configuration is invalid or missing.

**Inherits from:** `OCRException`

**When raised:**

- Invalid Azure OpenAI configuration
- Missing required environment variables
- Invalid endpoint URL format
- Invalid API key format

**Example:**

```python
from backend.services.ocr import GPT4oOCRService, OCRConfigError

try:
    # Missing API key in config
    service = GPT4oOCRService(
        azure_config={
            "endpoint": "https://example.openai.azure.com/",
            # Missing api_key
        }
    )
except OCRConfigError as e:
    print(f"Configuration error: {e}")
```

#### `OCRProcessingError`

Raised when OCR processing fails.

**Inherits from:** `OCRException`

**Attributes:**

- `file_path` (Optional[str]) - Path to file that failed processing
- `page_num` (Optional[int]) - Page number that failed (for multi-page documents)

**When raised:**

- API request failures
- Image encoding errors
- PDF conversion failures
- Network timeouts

**Example:**

```python
from backend.services.ocr import GPT4oOCRService, OCRProcessingError

try:
    service = GPT4oOCRService()
    result = service.process_pdf("/path/to/corrupted.pdf")
except OCRProcessingError as e:
    print(f"Processing error: {e}")
    if e.file_path:
        print(f"Failed file: {e.file_path}")
    if e.page_num:
        print(f"Failed page: {e.page_num}")
```

#### `UnsupportedFileTypeError`

Raised when attempting to process an unsupported file type.

**Inherits from:** `OCRException`

**Attributes:**

- `file_ext` (str) - The unsupported file extension
- `supported_types` (list) - List of supported file extensions

**When raised:**

- File extension not in ALL_SUPPORTED_EXTENSIONS
- Unknown or missing file extension

**Example:**

```python
from backend.services.ocr import GPT4oOCRService, UnsupportedFileTypeError

try:
    service = GPT4oOCRService()
    result = service.process_file("/path/to/file.xyz")  # Unsupported type
except UnsupportedFileTypeError as e:
    print(f"Unsupported type: {e.file_ext}")
    print(f"Supported types: {', '.join(e.supported_types)}")
```

#### `FileSizeExceededError`

Raised when file size exceeds maximum allowed size.

**Inherits from:** `OCRException`

**Attributes:**

- `file_size_mb` (float) - Actual file size in MB
- `max_size_mb` (float) - Maximum allowed file size in MB

**When raised:**

- File larger than configured maximum
- Default maximum is 10 MB

**Example:**

```python
from backend.services.ocr import FileSizeExceededError
from backend.services.ocr.utils import validate_file_size

try:
    validate_file_size("/path/to/large_file.pdf", max_size_mb=10)
except FileSizeExceededError as e:
    print(f"File size ({e.file_size_mb:.2f} MB) exceeds maximum ({e.max_size_mb} MB)")
```

#### `InvalidInputError`

Raised when input parameters are invalid.

**Inherits from:** `OCRException`

**When raised:**

- Neither file_path nor file_bytes provided
- Invalid doc_type value
- Invalid max_tokens value
- Missing required parameters

**Example:**

```python
from backend.services.ocr import OCRRequest, InvalidInputError

try:
    # Invalid doc_type
    request = OCRRequest(
        file_path="/path/to/file.pdf",
        doc_type="invalid_type",
    )
except ValueError as e:  # Pydantic validation error
    print(f"Invalid input: {e}")
```

### Error Handling Patterns

**Recommended Pattern:**

```python
from backend.services.ocr import (
    GPT4oOCRService,
    OCRException,
    OCRConfigError,
    OCRProcessingError,
    UnsupportedFileTypeError,
)
import logging

logger = logging.getLogger(__name__)

def process_document(file_path: str) -> dict:
    """Process document with comprehensive error handling."""

    try:
        # Initialise service
        service = GPT4oOCRService()

        # Process file
        result = service.process_file(
            file_path=file_path,
            doc_type="auto",
        )

        return {
            "success": True,
            "data": result,
        }

    except OCRConfigError as e:
        # Configuration errors - likely deployment issue
        logger.error(f"OCR configuration error: {e}")
        return {
            "success": False,
            "error": "OCR service not configured properly",
            "details": str(e),
        }

    except UnsupportedFileTypeError as e:
        # Unsupported file type - user error
        logger.warning(f"Unsupported file type: {e.file_ext}")
        return {
            "success": False,
            "error": f"Unsupported file type: {e.file_ext}",
            "supported_types": e.supported_types,
        }

    except OCRProcessingError as e:
        # Processing error - could be API issue or corrupted file
        logger.error(f"OCR processing failed: {e}")
        return {
            "success": False,
            "error": "Failed to process document",
            "details": str(e),
        }

    except OCRException as e:
        # General OCR error
        logger.error(f"OCR error: {e}")
        return {
            "success": False,
            "error": "OCR processing error",
            "details": str(e),
        }

    except Exception as e:
        # Unexpected error
        logger.exception(f"Unexpected error processing document: {e}")
        return {
            "success": False,
            "error": "Unexpected error",
        }
```

## Integration Patterns

### Integration with API Layer

The OCR service is typically used in FastAPI routes for document upload and processing endpoints.

**Example from File Node Executor:**

```python
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services.ocr import GPT4oOCRService, OCRException

router = APIRouter()

@router.post("/documents/extract")
async def extract_document_text(
    file: UploadFile = File(...),
    doc_type: str = "auto",
) -> dict:
    """
    Extract text from uploaded document.

    Args:
        file: Uploaded file (PDF, image, DOCX, etc.)
        doc_type: Document type for prompt selection

    Returns:
        Extracted text and metadata
    """
    import tempfile
    import os

    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        # Process with OCR service
        service = GPT4oOCRService()
        result = service.process_file(
            file_path=tmp_path,
            doc_type=doc_type,
        )

        return {
            "success": True,
            "filename": file.filename,
            **result,
        }

    except OCRException as e:
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
```

### Integration with Other Services

The OCR service integrates with the document processing service for comprehensive document handling.

**Example from Document Service:**

```python
from backend.services.ocr import GPT4oOCRService, OCRException
from backend.services.document.processors.base import DocumentProcessor

class OCRDocumentProcessor(DocumentProcessor):
    """Processor that uses OCR service for image-based documents."""

    def __init__(self):
        """Initialise OCR document processor."""
        self.ocr_service = GPT4oOCRService()

    def supports(self, file_type: str) -> bool:
        """Check if this processor supports the file type."""
        return file_type in [".png", ".jpg", ".jpeg", ".pdf", ".tiff"]

    def process(self, file_path: str, config: dict) -> dict:
        """
        Process document using OCR.

        Args:
            file_path: Path to document
            config: Processing configuration

        Returns:
            Extracted content and metadata
        """
        try:
            # Extract using OCR service
            result = self.ocr_service.process_file(
                file_path=file_path,
                doc_type=config.get("doc_type", "auto"),
                max_pages=config.get("max_pages"),
            )

            return {
                "content": result["text"],
                "extraction_method": result["extraction_method"],
                "tokens_used": result["tokens_used"],
                "page_count": result.get("page_count"),
            }

        except OCRException as e:
            raise DocumentProcessingError(f"OCR failed: {e}")
```

### Dependency Flow

**What services this module depends on:**

- None (self-contained, only external API dependency is Azure OpenAI)

**What services depend on this module:**

- [Document Service](document.md) - Uses OCR for image-based document processing
- File Node Executors - Uses OCR for FILE_READ node processing
- Workflow Execution - Indirect dependency through file nodes

**Data Flow:**

```
User Upload / File Input
        │
        ▼
┌────────────────────────┐
│   API Layer / Nodes    │ ← FastAPI routes or workflow nodes
└──────────┬─────────────┘
           │ file_path or file_bytes
           ▼
┌────────────────────────┐
│   GPT4oOCRService      │ ← Service orchestrator
└──────────┬─────────────┘
           │
           ├─→ ImageProcessor ──→ Azure OpenAI GPT-4o ──→ Extracted Text
           ├─→ PDFProcessor ────→ Azure OpenAI GPT-4o ──→ Extracted Text
           ├─→ DOCXProcessor ───→ Azure OpenAI GPT-4o ──→ Extracted Text
           └─→ TextProcessor ───→ Direct file read ─────→ Raw Text
                   │
                   ▼
           ┌────────────────┐
           │  OCRResponse   │ ← Structured response
           └────────────────┘
```

### Common Integration Patterns

#### Pattern 1: Direct File Processing

```python
from backend.services.ocr import GPT4oOCRService

def extract_text_from_upload(file_path: str) -> str:
    """Simple text extraction from uploaded file."""
    service = GPT4oOCRService()
    result = service.process_file(file_path, doc_type="auto")
    return result["text"]
```

#### Pattern 2: Batch Document Processing

```python
from backend.services.ocr import GPT4oOCRService
from pathlib import Path
from typing import List, Dict

async def batch_process_documents(
    file_paths: List[str],
    doc_type: str = "auto",
) -> List[Dict]:
    """Process multiple documents in batch."""
    service = GPT4oOCRService()
    results = []

    for file_path in file_paths:
        try:
            result = service.process_file(
                file_path=file_path,
                doc_type=doc_type,
            )
            results.append({
                "filename": Path(file_path).name,
                "success": True,
                **result,
            })
        except Exception as e:
            results.append({
                "filename": Path(file_path).name,
                "success": False,
                "error": str(e),
            })

    return results
```

#### Pattern 3: Streaming Per-Page Processing

```python
from backend.services.ocr import GPT4oOCRService
from typing import Iterator, Dict

def stream_pdf_pages(pdf_path: str) -> Iterator[Dict]:
    """Stream PDF pages as they're processed."""
    service = GPT4oOCRService()

    # Process with per-page chunking
    result = service.process_pdf(
        pdf_path=pdf_path,
        chunk_by_page=True,
    )

    # Yield each page result
    for page in result.get("pages", []):
        yield {
            "page": page["page"],
            "text": page["text"],
            "tokens": page["tokens"],
        }
```

## Usage Examples

### Example 1: Basic Usage

Complete end-to-end example of basic image OCR:

```python
from backend.services.ocr import GPT4oOCRService

# Step 1: Initialise service (loads config from environment)
service = GPT4oOCRService()

# Step 2: Process an image
result = service.process_image(
    image_path="/path/to/scanned_document.png",
)

# Step 3: Access results
print(f"Success: {result['success']}")
print(f"Extracted text ({len(result['text'])} chars):")
print(result['text'])
print(f"Tokens used: {result['tokens_used']}")
print(f"Method: {result['extraction_method']}")
```

### Example 2: Advanced Usage - Resume Processing

Complete example showing advanced resume processing with custom prompts:

```python
from backend.services.ocr import (
    GPT4oOCRService,
    get_default_prompt,
    OCRException,
)
import json

# Custom prompt for resume parsing
custom_resume_prompt = """
Extract information from this resume and structure it as JSON:
{
  "name": "Full name",
  "email": "Email address",
  "phone": "Phone number",
  "experience": [
    {"company": "", "role": "", "years": "", "description": ""}
  ],
  "education": [
    {"institution": "", "degree": "", "year": ""}
  ],
  "skills": ["skill1", "skill2"]
}

Be precise and extract only information that is clearly visible.
"""

def extract_resume_data(pdf_path: str) -> dict:
    """Extract structured data from resume PDF."""

    # Initialise service with explicit configuration
    service = GPT4oOCRService(
        azure_config={
            "api_key": "your-api-key",
            "endpoint": "https://your-resource.openai.azure.com/",
            "deployment_name": "gpt-4o-latest",
        }
    )

    try:
        # Process resume with custom prompt
        result = service.process_pdf(
            pdf_path=pdf_path,
            prompt=custom_resume_prompt,
            max_pages=3,  # Resumes typically 1-3 pages
        )

        # Parse JSON response
        try:
            structured_data = json.loads(result['text'])
            return {
                "success": True,
                "data": structured_data,
                "tokens_used": result['tokens_used'],
            }
        except json.JSONDecodeError:
            # Fallback to raw text if JSON parsing fails
            return {
                "success": True,
                "raw_text": result['text'],
                "tokens_used": result['tokens_used'],
            }

    except OCRException as e:
        return {
            "success": False,
            "error": str(e),
        }

# Use the function
resume_data = extract_resume_data("/uploads/candidate_resume.pdf")
if resume_data["success"]:
    print(f"Candidate: {resume_data['data']['name']}")
    print(f"Email: {resume_data['data']['email']}")
```

### Example 3: Complete Workflow - Invoice Processing Pipeline

Show a realistic, complete workflow for invoice processing:

```python
from backend.services.ocr import (
    GPT4oOCRService,
    get_default_prompt,
    UnsupportedFileTypeError,
    OCRProcessingError,
)
from pathlib import Path
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

async def process_invoice_batch(
    invoice_folder: str,
    output_folder: str,
) -> Dict[str, any]:
    """
    Complete invoice processing pipeline.

    Args:
        invoice_folder: Folder containing invoice PDFs/images
        output_folder: Folder to save extracted data

    Returns:
        Processing summary with success/failure counts
    """

    # Setup
    service = GPT4oOCRService()
    invoice_path = Path(invoice_folder)
    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True)

    # Get invoice prompt
    invoice_prompt = get_default_prompt("invoice")

    results = {
        "total": 0,
        "successful": 0,
        "failed": 0,
        "total_tokens": 0,
        "invoices": [],
    }

    try:
        # Step 1: Find all invoice files
        invoice_files = []
        for ext in [".pdf", ".png", ".jpg", ".jpeg"]:
            invoice_files.extend(invoice_path.glob(f"*{ext}"))

        results["total"] = len(invoice_files)
        logger.info(f"Found {len(invoice_files)} invoice files")

        # Step 2: Process each invoice
        for invoice_file in invoice_files:
            try:
                logger.info(f"Processing: {invoice_file.name}")

                # Extract invoice data
                result = service.process_file(
                    file_path=str(invoice_file),
                    prompt=invoice_prompt,
                    doc_type="invoice",
                )

                # Step 3: Save extracted text
                output_file = output_path / f"{invoice_file.stem}_extracted.txt"
                output_file.write_text(result["text"])

                # Track success
                results["successful"] += 1
                results["total_tokens"] += result["tokens_used"]
                results["invoices"].append({
                    "filename": invoice_file.name,
                    "status": "success",
                    "tokens": result["tokens_used"],
                    "output_file": str(output_file),
                })

                logger.info(f"✓ Processed {invoice_file.name} ({result['tokens_used']} tokens)")

            except UnsupportedFileTypeError as e:
                # Skip unsupported files
                results["failed"] += 1
                results["invoices"].append({
                    "filename": invoice_file.name,
                    "status": "failed",
                    "error": f"Unsupported type: {e.file_ext}",
                })
                logger.warning(f"✗ Skipped {invoice_file.name}: unsupported type")

            except OCRProcessingError as e:
                # Log processing failures
                results["failed"] += 1
                results["invoices"].append({
                    "filename": invoice_file.name,
                    "status": "failed",
                    "error": str(e),
                })
                logger.error(f"✗ Failed {invoice_file.name}: {e}")

        # Step 4: Generate summary report
        summary_file = output_path / "processing_summary.txt"
        summary_file.write_text(
            f"Invoice Processing Summary\n"
            f"=========================\n"
            f"Total files: {results['total']}\n"
            f"Successful: {results['successful']}\n"
            f"Failed: {results['failed']}\n"
            f"Total tokens: {results['total_tokens']}\n"
        )

        logger.info(f"Processing complete: {results['successful']}/{results['total']} successful")
        return results

    except Exception as e:
        logger.exception(f"Batch processing failed: {e}")
        raise

# Example usage
if __name__ == "__main__":
    import asyncio

    results = asyncio.run(process_invoice_batch(
        invoice_folder="/data/invoices/2024",
        output_folder="/data/invoices/extracted",
    ))

    print(f"Processed {results['successful']} invoices")
    print(f"Total tokens used: {results['total_tokens']}")
```

### Example 4: Testing Usage

Show how to use this service in tests:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.ocr import (
    GPT4oOCRService,
    OCRException,
    UnsupportedFileTypeError,
)

@pytest.fixture
def mock_azure_config():
    """Mock Azure configuration."""
    return {
        "api_key": "test-api-key",
        "endpoint": "https://test.openai.azure.com/",
        "deployment_name": "gpt-4o-latest",
    }

@pytest.fixture
def ocr_service(mock_azure_config):
    """OCR service fixture with mocked Azure client."""
    with patch("backend.services.ocr.service.AzureOpenAI"):
        service = GPT4oOCRService(azure_config=mock_azure_config)
        return service

def test_service_initialisation(mock_azure_config):
    """Test service initialises correctly."""
    with patch("backend.services.ocr.service.AzureOpenAI"):
        service = GPT4oOCRService(azure_config=mock_azure_config)
        assert service.config.api_key == "test-api-key"
        assert service.config.deployment_name == "gpt-4o-latest"

def test_unsupported_file_type(ocr_service):
    """Test handling of unsupported file types."""
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        ocr_service.process_file("/path/to/file.xyz")

    assert exc_info.value.file_ext == ".xyz"
    assert len(exc_info.value.supported_types) > 0

def test_process_image_success(ocr_service):
    """Test successful image processing."""
    # Mock the image processor
    mock_response = Mock(
        success=True,
        text="Extracted text",
        extraction_method="gpt4o_vision",
        tokens_used=100,
    )
    mock_response.model_dump.return_value = {
        "success": True,
        "text": "Extracted text",
        "extraction_method": "gpt4o_vision",
        "tokens_used": 100,
    }

    with patch.object(ocr_service.processors["image"], "process", return_value=mock_response):
        result = ocr_service.process_image(image_path="/path/to/test.png")

        assert result["success"] is True
        assert result["text"] == "Extracted text"
        assert result["tokens_used"] == 100

@pytest.mark.integration
def test_real_image_processing():
    """Integration test with real image (requires Azure credentials)."""
    import os

    # Skip if credentials not available
    if not os.getenv("AZURE_OPENAI_API_KEY"):
        pytest.skip("Azure credentials not configured")

    service = GPT4oOCRService()

    # Test with a small test image
    result = service.process_image(
        image_path="tests/fixtures/sample_receipt.png",
        max_tokens=1000,
    )

    assert result["success"] is True
    assert len(result["text"]) > 0
    assert result["tokens_used"] > 0
```

## Performance Considerations

### Performance Characteristics

**Image Processing:**

- Complexity: O(1) per image - single API call
- Latency: ~2-5 seconds per image (network + API processing)
- Memory: Low - images encoded to base64, streamed to API
- Token usage: ~100-500 tokens per page depending on content density

**PDF Processing:**

- Complexity: O(n) where n = number of pages - sequential page processing
- Latency: ~2-5 seconds per page
- Memory: Medium - PDF pages converted to images (cleared after each page)
- Token usage: ~100-500 tokens per page

**DOCX Processing:**

- Complexity: O(n) where n = number of embedded images
- Latency: ~1 second for text + ~2-5 seconds per image
- Memory: Low - document read incrementally
- Token usage: Only for embedded images

**Text Processing:**

- Complexity: O(1) - direct file read
- Latency: <100ms
- Memory: File size (full content loaded into memory)
- Token usage: 0 (no API calls)

**I/O Characteristics:**

- Network-bound for GPT-4o Vision processing (API calls)
- I/O-bound for PDF conversion (disk read + image conversion)
- CPU-bound for image encoding (base64 encoding)

### Optimisation Tips

#### Tip 1: Use Page Limits for Large PDFs

**Problem:**

```python
# Inefficient - processes entire 100-page PDF
service = GPT4oOCRService()
result = service.process_pdf(
    pdf_path="/path/to/large_document.pdf"
)  # Could take 5+ minutes and cost $$
```

**Solution:**

```python
# Efficient - process only needed pages
result = service.process_pdf(
    pdf_path="/path/to/large_document.pdf",
    max_pages=5,  # Only process first 5 pages
)
```

#### Tip 2: Use Direct Text Extraction for Text Files

**Problem:**

```python
# Inefficient - uses API for plain text
service = GPT4oOCRService()
result = service.process_file("/path/to/document.txt")  # Wastes API tokens
```

**Solution:**

```python
# Efficient - check file type first
import os

file_ext = os.path.splitext(file_path)[1].lower()
if file_ext in [".txt", ".md", ".csv"]:
    # Use direct text reading
    with open(file_path, "r") as f:
        text = f.read()
else:
    # Use OCR service for images/PDFs
    service = GPT4oOCRService()
    result = service.process_file(file_path)
    text = result["text"]
```

#### Tip 3: Batch Processing with Async

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from backend.services.ocr import GPT4oOCRService

async def process_files_async(file_paths: list) -> list:
    """Process multiple files concurrently."""

    def process_single(file_path: str) -> dict:
        service = GPT4oOCRService()
        return service.process_file(file_path)

    # Use thread pool for concurrent API calls
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, process_single, path)
            for path in file_paths
        ]
        results = await asyncio.gather(*tasks)

    return results

# Process 10 files concurrently
results = asyncio.run(process_files_async([
    "/path/to/file1.pdf",
    "/path/to/file2.png",
    # ... more files
]))
```

#### Tip 4: Cache Results for Repeated Processing

```python
from functools import lru_cache
from pathlib import Path
import hashlib

def get_file_hash(file_path: str) -> str:
    """Get hash of file content for cache key."""
    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

@lru_cache(maxsize=100)
def process_file_cached(file_hash: str, file_path: str) -> dict:
    """
    Cached OCR processing.

    Args:
        file_hash: MD5 hash of file (for cache key)
        file_path: Path to file

    Returns:
        OCR result (cached if processed before)
    """
    service = GPT4oOCRService()
    return service.process_file(file_path)

# Usage
file_path = "/path/to/document.pdf"
file_hash = get_file_hash(file_path)
result = process_file_cached(file_hash, file_path)  # Cached on subsequent calls
```

### Async/Await Support

The service does not natively support async/await, but can be used in async contexts with executors:

```python
from backend.services.ocr import GPT4oOCRService
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def async_process_file(file_path: str) -> dict:
    """Process file asynchronously using thread executor."""

    def sync_process():
        service = GPT4oOCRService()
        return service.process_file(file_path)

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        result = await loop.run_in_executor(executor, sync_process)

    return result

# Usage in async function
result = await async_process_file("/path/to/document.pdf")
```

### Connection Pooling

The Azure OpenAI client handles connection pooling internally. For high-volume processing, reuse service instances:

```python
# Good - reuse service instance
service = GPT4oOCRService()

for file_path in file_list:
    result = service.process_file(file_path)  # Reuses client connection

# Bad - creates new client for each file
for file_path in file_list:
    service = GPT4oOCRService()  # New client every iteration
    result = service.process_file(file_path)
```

### Batch Operations

Process multiple pages or files efficiently:

```python
from backend.services.ocr import GPT4oOCRService

service = GPT4oOCRService()

# Process PDF with per-page chunking for parallel downstream processing
result = service.process_pdf(
    pdf_path="/path/to/document.pdf",
    chunk_by_page=True,  # Get per-page results
)

# Process each page in parallel (downstream)
from concurrent.futures import ProcessPoolExecutor

def process_page_text(page_result: dict) -> dict:
    """Process extracted page text (CPU-intensive task)."""
    # Your processing logic here
    return {"page": page_result["page"], "processed": True}

with ProcessPoolExecutor() as executor:
    processed_pages = list(executor.map(
        process_page_text,
        result["pages"]
    ))
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.ocr import GPT4oOCRService, OCRResponse

@pytest.fixture
def mock_ocr_service():
    """Mock OCR service for testing."""
    with patch("backend.services.ocr.service.AzureOpenAI") as mock_client:
        service = GPT4oOCRService(
            azure_config={
                "api_key": "test-key",
                "endpoint": "https://test.openai.azure.com/",
            }
        )
        service.client = mock_client
        yield service

def test_process_image_with_mock(mock_ocr_service):
    """Test image processing with mocked response."""

    # Mock processor response
    mock_response = OCRResponse(
        success=True,
        text="Mock extracted text",
        extraction_method="gpt4o_vision",
        tokens_used=150,
    )

    with patch.object(
        mock_ocr_service.processors["image"],
        "process",
        return_value=mock_response
    ):
        result = mock_ocr_service.process_image(
            image_path="/test/image.png"
        )

        assert result["success"] is True
        assert result["text"] == "Mock extracted text"
        assert result["tokens_used"] == 150

def test_unsupported_file_type_handling():
    """Test that unsupported file types raise appropriate error."""
    from backend.services.ocr import UnsupportedFileTypeError

    service = GPT4oOCRService(
        azure_config={
            "api_key": "test-key",
            "endpoint": "https://test.openai.azure.com/",
        }
    )

    with pytest.raises(UnsupportedFileTypeError) as exc:
        service.process_file("/path/to/file.unknown")

    assert ".unknown" in str(exc.value)
```

### Mocking Dependencies

```python
from unittest.mock import patch, Mock, MagicMock
import pytest

@patch("backend.services.ocr.service.AzureOpenAI")
def test_service_initialization_with_env_vars(mock_azure_client, monkeypatch):
    """Test service initialises from environment variables."""

    # Set environment variables
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "env-api-key")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://env.openai.azure.com/")

    # Create service without explicit config
    service = GPT4oOCRService()

    # Verify configuration loaded from env
    assert service.config.api_key == "env-api-key"
    assert service.config.endpoint == "https://env.openai.azure.com/"

    # Verify Azure client was created
    mock_azure_client.assert_called_once()

@patch("backend.services.ocr.processors.image.ImageProcessor.process")
def test_mock_image_processor(mock_process):
    """Test with mocked image processor."""

    # Setup mock return value
    mock_process.return_value = OCRResponse(
        success=True,
        text="Mocked text",
        extraction_method="gpt4o_vision",
        tokens_used=200,
    )

    # Use service
    with patch("backend.services.ocr.service.AzureOpenAI"):
        service = GPT4oOCRService(
            azure_config={
                "api_key": "test",
                "endpoint": "https://test.openai.azure.com/",
            }
        )

        result = service.process_image(image_path="/test.png")

        # Verify mock was called
        mock_process.assert_called_once()
        assert result["text"] == "Mocked text"
```

### Integration Testing

```python
import pytest
import os
from pathlib import Path

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="Azure credentials not configured"
)
def test_real_pdf_processing():
    """
    Integration test with real Azure OpenAI API.

    Requires:
        - AZURE_OPENAI_API_KEY environment variable
        - AZURE_OPENAI_ENDPOINT environment variable
        - Test fixture file: tests/fixtures/sample.pdf
    """
    from backend.services.ocr import GPT4oOCRService

    # Use real service with env credentials
    service = GPT4oOCRService()

    # Process test PDF
    test_pdf = Path(__file__).parent / "fixtures" / "sample.pdf"
    result = service.process_pdf(
        pdf_path=str(test_pdf),
        max_pages=1,
    )

    # Verify real response
    assert result["success"] is True
    assert len(result["text"]) > 0
    assert result["tokens_used"] > 0
    assert result["extraction_method"] == "gpt4o_vision"
    assert result["page_count"] == 1

@pytest.mark.integration
def test_real_image_with_known_content():
    """Test OCR accuracy with image containing known text."""

    if not os.getenv("AZURE_OPENAI_API_KEY"):
        pytest.skip("Azure credentials not configured")

    from backend.services.ocr import GPT4oOCRService

    service = GPT4oOCRService()

    # Process image with known content
    test_image = Path(__file__).parent / "fixtures" / "test_text.png"
    result = service.process_image(image_path=str(test_image))

    # Verify expected text appears in result
    expected_text = "TEST DOCUMENT"  # Known content in test image
    assert expected_text.lower() in result["text"].lower()
```

## Best Practices

### Do's

✅ **Reuse service instances for multiple files**

```python
# Good - reuse service instance
service = GPT4oOCRService()

for file_path in file_list:
    result = service.process_file(file_path)
```

✅ **Use appropriate max_pages limits for large PDFs**

```python
# Good - limit pages for preview or sampling
service = GPT4oOCRService()
result = service.process_pdf(
    pdf_path="/path/to/large_doc.pdf",
    max_pages=10,  # Process only first 10 pages
)
```

✅ **Handle exceptions gracefully with specific error types**

```python
# Good - catch specific exceptions
from backend.services.ocr import (
    GPT4oOCRService,
    UnsupportedFileTypeError,
    OCRProcessingError,
)

try:
    result = service.process_file(file_path)
except UnsupportedFileTypeError as e:
    # Handle unsupported type
    logger.warning(f"Skipping unsupported file: {e.file_ext}")
except OCRProcessingError as e:
    # Handle processing error
    logger.error(f"Processing failed: {e}")
```

✅ **Use doc_type for specialised extraction**

```python
# Good - use specific doc types for better results
result = service.process_file(
    file_path="/uploads/invoice_2024.pdf",
    doc_type="invoice",  # Uses invoice-specific prompt
)
```

✅ **Validate file size and type before processing**

```python
# Good - validate before processing
from backend.services.ocr.utils import validate_file_size, get_file_extension
from backend.services.ocr.config import ALL_SUPPORTED_EXTENSIONS

file_ext = get_file_extension(file_path)
if file_ext not in ALL_SUPPORTED_EXTENSIONS:
    raise ValueError(f"Unsupported file type: {file_ext}")

validate_file_size(file_path, max_size_mb=10)

# Now safe to process
result = service.process_file(file_path)
```

✅ **Use chunk_by_page for downstream processing**

```python
# Good - chunk by page for parallel processing
result = service.process_pdf(
    pdf_path="/path/to/doc.pdf",
    chunk_by_page=True,
)

# Process each page independently
for page in result["pages"]:
    process_page_content(page["text"])
```

### Don'ts

❌ **Don't create new service instances repeatedly**

```python
# Bad - creates new client connection each time
for file_path in file_list:
    service = GPT4oOCRService()  # Wasteful
    result = service.process_file(file_path)

# Good - reuse service instance (see Do's above)
```

❌ **Don't process entire large PDFs without page limits**

```python
# Bad - processes all 500 pages, expensive and slow
result = service.process_pdf(
    pdf_path="/path/to/huge_book.pdf"
)  # Could cost $50+ and take hours

# Good - use max_pages or process in batches
```

❌ **Don't ignore error handling**

```python
# Bad - no error handling
result = service.process_file(file_path)
content = result["text"]  # Could fail if processing failed

# Good - check success and handle errors
result = service.process_file(file_path)
if result.get("success"):
    content = result["text"]
else:
    logger.error(f"Processing failed: {result.get('error')}")
```

❌ **Don't use OCR for plain text files**

```python
# Bad - wastes API tokens on plain text
result = service.process_file("/path/to/document.txt")  # Unnecessary API call

# Good - read text files directly
if file_path.endswith(".txt"):
    with open(file_path) as f:
        text = f.read()
else:
    result = service.process_file(file_path)
    text = result["text"]
```

❌ **Don't hardcode API credentials**

```python
# Bad - credentials in code
service = GPT4oOCRService(
    azure_config={
        "api_key": "abc123xyz",  # Hardcoded secret!
        "endpoint": "https://my-resource.openai.azure.com/",
    }
)

# Good - use environment variables
service = GPT4oOCRService()  # Loads from environment
```

❌ **Don't forget to clean up temporary files**

```python
# Bad - leaks temporary files
import tempfile

temp_file = tempfile.NamedTemporaryFile(delete=False)
temp_file.write(uploaded_data)
temp_file.close()

result = service.process_file(temp_file.name)
# temp_file.name never deleted!

# Good - clean up temp files
import os

try:
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(uploaded_data)
    temp_file.close()

    result = service.process_file(temp_file.name)
finally:
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)
```

## Related Documentation

### Related Services

- [Document Service](document.md) - Document processing service that uses OCR for image-based documents
- [Execution Service](execution.md) - Workflow execution service that uses file nodes with OCR

### Related API Modules

- File Node Executor ([backend/services/nodes/executors/file.py](../../../backend/services/nodes/executors/file.py)) - Uses
  OCR service for FILE_READ nodes

### External Documentation

- [Azure OpenAI Service Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/) - Azure OpenAI API
  reference
- [GPT-4o Vision Documentation](https://platform.openai.com/docs/guides/vision) - GPT-4o Vision capabilities
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation library used for models

## Summary

The OCR service provides comprehensive text extraction capabilities from diverse document formats using Azure OpenAI's
GPT-4o Vision API. It serves as a critical component in the AgenticStudio document processing pipeline, enabling workflows
to ingest and understand visual information from scanned documents, images, PDFs, and office documents.

The service is architected around a processor pattern where specialised handlers (ImageProcessor, PDFProcessor,
DOCXProcessor, TextProcessor) each manage extraction for their respective file types. This design allows for
extensibility and maintains clean separation of concerns while providing a unified interface through the
`GPT4oOCRService` orchestrator.

Built on a foundation of Pydantic models for validation and type safety, the service ensures reliable processing with
comprehensive error handling. Configuration is flexible, supporting both environment variable-based setup for production
environments and explicit configuration for testing scenarios.

**Key Features:**

- GPT-4o Vision-based text extraction with high accuracy
- Support for images, PDFs, DOCX, and text files
- Specialised prompts for different document types (resumes, invoices, forms, tables, handwritten text)
- Page-by-page PDF processing with chunking support
- Embedded image extraction from DOCX documents
- Token usage tracking for cost management
- Comprehensive error handling with specific exception types

**Primary Use Cases:**

- Document digitisation and archival
- Resume/CV parsing for recruitment workflows
- Invoice and receipt data extraction for accounting
- Form processing and data capture
- Table extraction from reports and documents

**When to Use This Service:**

- When you need to extract text from images or scanned documents
- When processing PDFs that don't have selectable text
- When you need structured data extraction from documents (invoices, resumes, forms)
- When you need high-accuracy OCR with understanding of document structure
- When processing documents with mixed content (text, images, tables)
