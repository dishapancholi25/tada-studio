"""Base processor interface for document processing."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class DocumentProcessor(ABC):
    """Abstract base class for document processors."""

    @abstractmethod
    def supports(self, file_type: str) -> bool:
        """
        Check if this processor supports the given file type.

        Args:
            file_type: File type to check

        Returns:
            True if supported, False otherwise
        """
        pass

    @abstractmethod
    def process(self, file_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a document file.

        Args:
            file_path: Path to the file to process
            config: Processing configuration

        Returns:
            Dictionary with raw processing results
        """
        pass
