"""Unstructured library processor."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from ..config import UNSTRUCTURED_SUPPORTED_TYPES
from ..exceptions import DocumentProcessingError, ProcessorNotAvailableError
from .base import DocumentProcessor


logger = logging.getLogger(__name__)


class UnstructuredProcessor(DocumentProcessor):
    """Processor using langchain_unstructured library."""

    def __init__(self):
        """Initialize Unstructured processor."""
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if langchain_unstructured is available."""
        try:
            import langchain_unstructured  # noqa: F401

            logger.debug("[DOC-UNSTRUCTURED] langchain_unstructured available")
        except ImportError:
            raise ProcessorNotAvailableError(
                "unstructured", "langchain_unstructured library not installed"
            )

    def supports(self, file_type: str) -> bool:
        """Check if this processor supports the file type."""
        return file_type in UNSTRUCTURED_SUPPORTED_TYPES

    def process(self, file_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process document using Unstructured.

        Args:
            file_path: Path to document
            config: Processing configuration

        Returns:
            Dictionary with extracted content
        """
        logger.info(f"[DOC-UNSTRUCTURED] Processing file: {file_path.name}")

        try:
            from langchain_unstructured import UnstructuredLoader

            loader_kwargs = self._build_loader_kwargs(config)
            loader = UnstructuredLoader(str(file_path), **loader_kwargs)
            documents = loader.load()

            page_count = self._extract_page_count(documents)

            logger.debug(
                f"[DOC-UNSTRUCTURED] Extracted {len(documents)} documents, "
                f"{page_count} pages"
            )

            return {
                "documents": documents,
                "content": None,  # Will be formatted later
                "extraction_method": "unstructured",
                "document_count": len(documents),
                "page_count": page_count,
            }

        except Exception as e:
            logger.error(f"[DOC-UNSTRUCTURED] Processing failed: {e}")
            raise DocumentProcessingError(
                f"Unstructured processing failed: {e}",
                file_path=str(file_path),
                processor="unstructured",
            )

    def _build_loader_kwargs(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build kwargs for UnstructuredLoader."""
        loader_kwargs = {
            "mode": "elements"
            if config.get("output_format") == "elements"
            else "single",
            "strategy": "hi_res" if config.get("extraction_mode") == "ocr" else "fast",
        }

        # Add optional parameters
        if config.get("language"):
            loader_kwargs["languages"] = [config.get("language")]

        if config.get("chunking_strategy"):
            loader_kwargs["chunking_strategy"] = config.get("chunking_strategy")
            loader_kwargs["max_characters"] = config.get("max_partition_size", 1500)
            loader_kwargs["combine_under_n_chars"] = config.get(
                "combine_under_n_chars", 500
            )

        return loader_kwargs

    def _extract_page_count(self, documents: List) -> int:
        """Extract page count from documents."""
        page_numbers = [doc.metadata.get("page_number", 1) for doc in documents]
        return max(page_numbers) if page_numbers else 1
