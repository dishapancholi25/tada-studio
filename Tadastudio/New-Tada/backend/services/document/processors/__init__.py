"""Document processors for different file types."""

from .docx import DOCXProcessor
from .excel import ExcelProcessor
from .ocr import OCRProcessor
from .pdf import PDFProcessor
from .text import TextProcessor
from .unstructured import UnstructuredProcessor


__all__ = [
    "TextProcessor",
    "PDFProcessor",
    "DOCXProcessor",
    "ExcelProcessor",
    "UnstructuredProcessor",
    "OCRProcessor",
]
