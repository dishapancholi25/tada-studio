"""Base document loader interface."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from langchain_core.documents import Document


logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """Abstract base class for document loaders."""

    @abstractmethod
    def load(self, file_path: str) -> List[Document]:
        """Load a document and return list of Document objects.

        Args:
            file_path: Path to the document file

        Returns:
            List of Document objects with page_content and metadata

        Raises:
            LoaderNotAvailableError: If required dependencies are missing
            Exception: If loading fails
        """
        pass

    @staticmethod
    def supports(file_extension: str) -> bool:
        """Check if loader supports given file extension.

        Args:
            file_extension: File extension (e.g., '.pdf', '.docx')

        Returns:
            True if supported, False otherwise
        """
        return False

    @staticmethod
    def _get_file_extension(file_path: str) -> str:
        """Get normalized file extension.

        Args:
            file_path: Path to file

        Returns:
            Lowercase file extension with dot (e.g., '.pdf')
        """
        return Path(file_path).suffix.lower()
