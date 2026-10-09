"""Document loaders module."""

from .base import BaseLoader
from .docx_loader import DOCXLoader
from .excel_loader import ExcelLoader
from .factory import LoaderFactory
from .pdf_loader import PDFLoader
from .text_loader import CSVLoader, TextLoader
from .markdown_loader import MarkdownLoader


__all__ = [
    "BaseLoader",
    "PDFLoader",
    "DOCXLoader",
    "TextLoader",
    "CSVLoader",
    "ExcelLoader",
    "MarkdownLoader",
    "LoaderFactory",
]
