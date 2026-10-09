"""Abstract base classes for OCR processors."""

from abc import ABC, abstractmethod
from typing import Optional

from openai import AzureOpenAI

from .models import OCRRequest, OCRResponse


class OCRProcessor(ABC):
    """Abstract base class for OCR processors."""

    def __init__(self, client: Optional[AzureOpenAI] = None):
        """
        Initialize OCR processor.

        Args:
            client: Azure OpenAI client (optional for non-AI processors)
        """
        self.client = client

    @abstractmethod
    def process(self, request: OCRRequest) -> OCRResponse:
        """
        Process a document and extract text.

        Args:
            request: OCR request with file and configuration

        Returns:
            OCR response with extracted text and metadata
        """
        pass

    @abstractmethod
    def supports_file_type(self, file_ext: str) -> bool:
        """
        Check if this processor supports the given file type.

        Args:
            file_ext: File extension (e.g., '.pdf', '.png')

        Returns:
            True if supported, False otherwise
        """
        pass
