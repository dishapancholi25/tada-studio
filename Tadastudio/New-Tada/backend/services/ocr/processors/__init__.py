"""OCR processors for different file types."""

from .csv import CSVProcessor
from .docx import DOCXProcessor
from .image import ImageProcessor
from .pdf import PDFProcessor
from .text import TextProcessor


__all__ = [
    "ImageProcessor",
    "PDFProcessor",
    "DOCXProcessor",
    "TextProcessor",
    "CSVProcessor",
]
