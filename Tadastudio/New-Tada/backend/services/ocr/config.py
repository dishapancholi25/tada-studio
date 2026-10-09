"""Configuration, constants, and default prompts for OCR services."""

from typing import Dict


# Supported file extensions by category
SUPPORTED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"]
SUPPORTED_PDF_EXTENSIONS = [".pdf"]
SUPPORTED_DOCX_EXTENSIONS = [".docx", ".doc"]
SUPPORTED_TEXT_EXTENSIONS = [".txt", ".md"]
SUPPORTED_CSV_EXTENSIONS = [".csv", ".tsv"]

ALL_SUPPORTED_EXTENSIONS = (
    SUPPORTED_IMAGE_EXTENSIONS
    + SUPPORTED_PDF_EXTENSIONS
    + SUPPORTED_DOCX_EXTENSIONS
    + SUPPORTED_TEXT_EXTENSIONS
    + SUPPORTED_CSV_EXTENSIONS
)

# CSV-specific constants
CSV_DELIMITERS = {
    "comma": ",",
    "semicolon": ";",
    "tab": "\t",
    "pipe": "|",
}
DEFAULT_CSV_CHUNK_SIZE = 50
MAX_CSV_ROWS_FOR_FULL_OUTPUT = 100
CSV_LARGE_FILE_THRESHOLD_ROWS = 500

# Default configuration values
DEFAULT_MAX_TOKENS = 4000
DEFAULT_MAX_FILE_SIZE_MB = 1024
DEFAULT_TEMPERATURE = 0.1  # Low temperature for accurate extraction
DEFAULT_PDF_SCALE = 2  # 2x scale for PDF to image conversion

# System prompts for AI model OCR
SYSTEM_PROMPT = (
    "You are an expert OCR system. Extract text accurately and format it clearly."
)

# Default OCR prompts for different document types
DEFAULT_OCR_PROMPTS: Dict[str, str] = {
    "generic": """Extract all text from this document image. Preserve the original formatting including:
- Headers and sections
- Lists and bullet points
- Tables (use markdown table format)
- Bold and italic text
- Page numbers if visible

Output as clean, well-structured markdown.""",
    "resume": """Extract all information from this resume/CV. Structure the output with these sections:
- Personal Information (name, contact)
- Professional Summary
- Work Experience (company, role, dates, responsibilities)
- Education (degree, institution, dates)
- Skills (categorized if applicable)
- Certifications and Awards

Format as structured markdown with clear headers.""",
    "invoice": """Extract all data from this invoice/receipt. Include:
- Document number and date
- Vendor/seller information
- Buyer/customer information
- Line items (description, quantity, price, total)
- Subtotal, tax, and total amounts
- Payment terms and notes

Format as structured data with a markdown table for line items.""",
    "form": """Extract all fields and values from this form. For each field:
- Field name/label
- Field value or response
- Checkbox/radio button selections
- Signatures or stamps if present

Maintain the form's logical structure and group related fields.""",
    "table": """Extract the table data from this image.
- Preserve all column headers
- Extract all row data accurately
- Maintain cell alignment and structure
- Handle merged cells appropriately

Output as a clean markdown table.""",
    "handwritten": """Extract all handwritten text from this image.
- Transcribe as accurately as possible
- Note any unclear or ambiguous text with [unclear]
- Preserve line breaks and paragraph structure
- Indicate any drawings or diagrams

Focus on accuracy over formatting.""",
}


def get_default_prompt(doc_type: str = "generic") -> str:
    """
    Get default OCR prompt for a document type.

    Args:
        doc_type: Type of document (generic, resume, invoice, form, table, handwritten)

    Returns:
        Default prompt string
    """
    return DEFAULT_OCR_PROMPTS.get(doc_type, DEFAULT_OCR_PROMPTS["generic"])


def auto_detect_doc_type(file_path: str) -> str:
    """
    Auto-detect document type from file path.

    Args:
        file_path: Path to the file

    Returns:
        Detected document type
    """
    file_path_lower = file_path.lower()

    if "resume" in file_path_lower or "cv" in file_path_lower:
        return "resume"
    elif "invoice" in file_path_lower or "receipt" in file_path_lower:
        return "invoice"
    elif "form" in file_path_lower:
        return "form"
    else:
        return "generic"
