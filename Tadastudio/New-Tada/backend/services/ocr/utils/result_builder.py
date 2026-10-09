"""Result builder utilities for consistent OCR responses."""

import logging
from typing import List, Optional

from ..models import OCRResponse, PageResult


logger = logging.getLogger(__name__)


def build_success_response(
    text: str,
    extraction_method: str,
    tokens_used: int = 0,
    model: Optional[str] = None,
    page_count: Optional[int] = None,
    pages: Optional[List[PageResult]] = None,
    has_images: Optional[bool] = None,
) -> OCRResponse:
    """
    Build a successful OCR response.

    Args:
        text: Extracted text content
        extraction_method: Method used for extraction
        tokens_used: Number of tokens used
        model: Model name used for processing
        page_count: Number of pages processed
        pages: Per-page results for chunked output
        has_images: Whether document contains processed images

    Returns:
        OCR response object
    """
    logger.debug(
        f"[OCR-RESULT] Success response: method={extraction_method}, "
        f"tokens={tokens_used}, chars={len(text)}"
    )

    return OCRResponse(
        success=True,
        text=text,
        extraction_method=extraction_method,
        tokens_used=tokens_used,
        total_tokens=tokens_used,
        model=model,
        page_count=page_count,
        pages=pages,
        has_images=has_images,
        error=None,
    )


def build_error_response(error_message: str, extraction_method: str) -> OCRResponse:
    """
    Build an error OCR response.

    Args:
        error_message: Error message
        extraction_method: Method that was attempted

    Returns:
        OCR response object with error
    """
    logger.error(f"[OCR-RESULT] Error response: {error_message}")

    return OCRResponse(
        success=False,
        text="",
        extraction_method=extraction_method,
        tokens_used=0,
        total_tokens=0,
        error=error_message,
    )
