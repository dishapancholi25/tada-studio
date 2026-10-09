"""Factory for creating document loaders."""

import logging
from pathlib import Path
from typing import Dict, Type

from ..exceptions import UnsupportedFileTypeError
from .base import BaseLoader
from .docx_loader import DOCXLoader
from .excel_loader import ExcelLoader
from .pdf_loader import PDFLoader
from .text_loader import CSVLoader, TextLoader
from .markdown_loader import MarkdownLoader


logger = logging.getLogger(__name__)


class LoaderFactory:
    """Factory for creating appropriate document loaders based on file type."""

    # Map file extensions to loader classes
    LOADER_MAP: Dict[str, Type[BaseLoader]] = {
        ".pdf": PDFLoader,
        ".docx": DOCXLoader,
        ".txt": TextLoader,
        ".csv": CSVLoader,
        ".xlsx": ExcelLoader,
        ".md": MarkdownLoader,
    }

    @classmethod
    def get_loader(cls, file_path: str) -> BaseLoader:
        """Get appropriate loader for the file type.

        Args:
            file_path: Path to the file

        Returns:
            Instantiated loader for the file type

        Raises:
            UnsupportedFileTypeError: If file type is not supported
        """
        file_extension = Path(file_path).suffix.lower()

        if file_extension not in cls.LOADER_MAP:
            supported = list(cls.LOADER_MAP.keys())
            logger.error(f"[LOADER-FACTORY] Unsupported file type: {file_extension}")
            raise UnsupportedFileTypeError(file_extension, supported)

        loader_class = cls.LOADER_MAP[file_extension]
        logger.debug(
            f"[LOADER-FACTORY] Selected {loader_class.__name__} for {file_extension}"
        )

        return loader_class()

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """Check if file type is supported.

        Args:
            file_path: Path to the file

        Returns:
            True if file type is supported
        """
        file_extension = Path(file_path).suffix.lower()
        return file_extension in cls.LOADER_MAP

    @classmethod
    def get_supported_extensions(cls) -> list:
        """Get list of supported file extensions.

        Returns:
            List of supported extensions (e.g., ['.pdf', '.docx', ...])
        """
        return list(cls.LOADER_MAP.keys())
