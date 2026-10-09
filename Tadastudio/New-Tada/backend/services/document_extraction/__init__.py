"""Document extraction service module.

Provides a pluggable extraction backend for the file reader node.
Supported providers:
- model_ocr: AI model OCR (default)
- tika: Apache Tika REST server
- azure_document_intelligence: Azure AI Document Intelligence
"""

from .factory import DocumentExtractionFactory, get_extraction_provider

__all__ = ["DocumentExtractionFactory", "get_extraction_provider"]
