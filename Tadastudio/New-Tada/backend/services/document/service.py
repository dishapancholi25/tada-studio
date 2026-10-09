"""Main document processing service orchestrator."""

import logging
from pathlib import Path
from typing import Any, Dict

from .cache import CacheManager
from .config import DEFAULT_CACHE_DIR, determine_extraction_mode
from .exceptions import UnsupportedFileTypeError
from .formatters import ElementsFormatter, JSONFormatter, MarkdownFormatter
from .metadata import extract_file_metadata
from .models import FileMetadata, ProcessingConfig, ProcessingResult
from .processors import (
    DOCXProcessor,
    ExcelProcessor,
    OCRProcessor,
    PDFProcessor,
    TextProcessor,
    UnstructuredProcessor,
)


logger = logging.getLogger(__name__)


class DocumentService:
    """Service for processing various document types."""

    def __init__(self, cache_dir: Path = None):
        """
        Initialize the document service.

        Args:
            cache_dir: Directory for cache storage (optional)
        """
        self.cache_manager = CacheManager(cache_dir or DEFAULT_CACHE_DIR)
        self.processors = self._init_processors()
        self.formatters = self._init_formatters()

        logger.info("[DOC-SERVICE] Document service initialized")

    def _init_processors(self) -> Dict[str, Any]:
        """Initialize all available processors."""
        processors = {}

        # Always available
        processors["text"] = TextProcessor()

        # Try to initialize optional processors
        for processor_class, key in [
            (PDFProcessor, "pdf"),
            (DOCXProcessor, "docx"),
            (ExcelProcessor, "excel"),
            (UnstructuredProcessor, "unstructured"),
            (OCRProcessor, "ocr"),
        ]:
            try:
                processors[key] = processor_class()
                logger.debug(f"[DOC-SERVICE] {key} processor available")
            except Exception as e:
                logger.warning(f"[DOC-SERVICE] {key} processor not available: {e}")

        return processors

    def _init_formatters(self) -> Dict[str, Any]:
        """Initialize output formatters."""
        return {
            "markdown": MarkdownFormatter(),
            "plain": MarkdownFormatter(),  # Same as markdown for now
            "json": JSONFormatter(),
            "elements": ElementsFormatter(),
        }

    def process_document(
        self, file_path: str, config: Dict[str, Any], use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Process a document using the best available method.

        Args:
            file_path: Path to the document
            config: Processing configuration dictionary
            use_cache: Whether to use cached results

        Returns:
            Dictionary containing extracted content and metadata
        """
        # Convert to Path object
        file_path = Path(file_path)

        # Parse config
        processing_config = ProcessingConfig(**config)

        # Check cache first
        if use_cache and processing_config.use_cache:
            cached_result = self.cache_manager.get(file_path, config)
            if cached_result:
                logger.info(f"[DOC-SERVICE] Using cached result for {file_path.name}")
                return cached_result

        # Extract metadata
        metadata = extract_file_metadata(file_path)

        # Determine extraction mode
        extraction_mode = self._determine_extraction_mode(
            processing_config, metadata.file_type
        )

        # Process document
        try:
            result = self._process_with_mode(
                file_path, extraction_mode, config, metadata
            )

            # Cache successful result
            if use_cache and result.get("success", False):
                self.cache_manager.set(file_path, config, result)

            return result

        except Exception as e:
            logger.error(f"[DOC-SERVICE] Error processing {file_path.name}: {e}")

            # Try fallback if configured
            if processing_config.fallback_on_error:
                logger.info("[DOC-SERVICE] Attempting fallback processing")
                return self._fallback_process(file_path, metadata, config)

            return self._build_error_result(e, metadata)

    def _determine_extraction_mode(
        self, config: ProcessingConfig, file_type: str
    ) -> str:
        """Determine extraction mode from config or file type."""
        if config.extraction_mode != "auto":
            return config.extraction_mode
        return determine_extraction_mode(file_type)

    def _process_with_mode(
        self, file_path: Path, mode: str, config: Dict, metadata: FileMetadata
    ) -> Dict[str, Any]:
        """Process document with specific mode."""
        logger.info(
            f"[DOC-SERVICE] Processing {file_path.name} with mode: {mode}",
            extra={"file_type": metadata.file_type, "size_mb": metadata.file_size_mb},
        )

        # Get processor
        processor = self._get_processor(mode, metadata.file_type)

        # Process
        raw_result = processor.process(file_path, config)

        # Format output
        formatter = self.formatters.get(config.get("output_format", "markdown"))
        formatted_content = formatter.format(raw_result, config)

        # Update metadata from processor result
        self._update_metadata(metadata, raw_result)

        # Build final result
        return ProcessingResult(
            success=True,
            content=formatted_content,
            metadata=metadata,
            extraction_method=raw_result.get("extraction_method", mode),
            document_count=raw_result.get("document_count"),
            confidence=raw_result.get("ocr_confidence"),
        ).model_dump()

    def _get_processor(self, mode: str, file_type: str):
        """Get appropriate processor for mode and file type."""
        # Direct mode mapping
        if mode in self.processors:
            return self.processors[mode]

        # Fallback: find processor that supports file type
        for processor in self.processors.values():
            if processor.supports(file_type):
                return processor

        raise UnsupportedFileTypeError(file_type, list(self.processors.keys()))

    def _fallback_process(
        self, file_path: Path, metadata: FileMetadata, config: Dict
    ) -> Dict[str, Any]:
        """Fallback processing using simpler methods."""
        # Try text processor as ultimate fallback
        if "text" in self.processors:
            try:
                processor = self.processors["text"]
                raw_result = processor.process(file_path, config)

                formatter = self.formatters.get(config.get("output_format", "markdown"))
                content = formatter.format(raw_result, config)

                return ProcessingResult(
                    success=True,
                    content=content,
                    metadata=metadata,
                    extraction_method="fallback",
                ).model_dump()

            except Exception as e:
                logger.error(f"[DOC-SERVICE] Fallback also failed: {e}")

        return self._build_error_result(
            Exception("All processing methods failed"), metadata
        )

    def _update_metadata(self, metadata: FileMetadata, raw_result: Dict):
        """Update metadata with processor results."""
        if "page_count" in raw_result:
            metadata.page_count = raw_result["page_count"]
        if "sheet_count" in raw_result:
            metadata.sheet_count = raw_result["sheet_count"]
        if "ocr_confidence" in raw_result:
            metadata.ocr_confidence = raw_result["ocr_confidence"]
        if "ocr_method" in raw_result:
            metadata.ocr_method = raw_result["ocr_method"]

    def _build_error_result(
        self, error: Exception, metadata: FileMetadata
    ) -> Dict[str, Any]:
        """Build error result dictionary."""
        return ProcessingResult(
            success=False,
            content="",
            metadata=metadata,
            extraction_method="failed",
            error=str(error),
        ).model_dump()
