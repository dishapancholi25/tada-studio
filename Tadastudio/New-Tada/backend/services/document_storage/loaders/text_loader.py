"""Text and CSV document loaders."""

import logging
from typing import List

from langchain_core.documents import Document

from ..exceptions import LoaderNotAvailableError
from .base import BaseLoader


logger = logging.getLogger(__name__)


class TextLoader(BaseLoader):
    """Plain text document loader."""

    SUPPORTED_EXTENSIONS = {".txt"}

    def load(self, file_path: str) -> List[Document]:
        """Load text document.

        Args:
            file_path: Path to text file

        Returns:
            List of Document objects

        Raises:
            Exception: If loading fails
        """
        from langchain_community.document_loaders import TextLoader as LCTextLoader

        logger.info("[TEXT-LOADER] Loading text file")
        loader = LCTextLoader(file_path, encoding="utf-8")
        return loader.load()

    @staticmethod
    def supports(file_extension: str) -> bool:
        """Check if text loader supports the file extension.

        Args:
            file_extension: File extension (e.g., '.txt')

        Returns:
            True if extension is .txt
        """
        return file_extension.lower() in TextLoader.SUPPORTED_EXTENSIONS


class CSVLoader(BaseLoader):
    """CSV document loader."""

    SUPPORTED_EXTENSIONS = {".csv"}

    def load(self, file_path: str) -> List[Document]:
        """Load CSV document.

        Args:
            file_path: Path to CSV file

        Returns:
            List of Document objects

        Raises:
            LoaderNotAvailableError: If CSV loading fails
            Exception: If loading fails
        """
        try:
            from langchain_community.document_loaders import CSVLoader as LCCSVLoader

            logger.info("[CSV-LOADER] Loading CSV file")
            loader = LCCSVLoader(file_path)
            return loader.load()

        except ImportError as e:
            # CSV should work with standard library
            logger.error(f"[CSV-LOADER] CSV loader not available: {e}")
            raise LoaderNotAvailableError(
                "CSV loader", "pip install langchain-community"
            )

        except Exception as e:
            logger.error(f"[CSV-LOADER] Failed to load CSV: {e}")
            raise

    @staticmethod
    def supports(file_extension: str) -> bool:
        """Check if CSV loader supports the file extension.

        Args:
            file_extension: File extension (e.g., '.csv')

        Returns:
            True if extension is .csv
        """
        return file_extension.lower() in CSVLoader.SUPPORTED_EXTENSIONS
