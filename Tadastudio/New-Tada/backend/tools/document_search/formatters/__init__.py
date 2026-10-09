"""Document search result formatters.

This module provides various formatters for document search results,
including structured markdown, inline citations, footnotes, and plain text.
"""

import logging

from .base import BaseFormatter
from .footnote_formatter import FootnoteFormatter
from .full_document_formatter import FullDocumentFormatter
from .inline_formatter import InlineFormatter
from .plain_formatter import PlainFormatter
from .structured_formatter import StructuredFormatter


logger = logging.getLogger(__name__)


def get_formatter(
    citation_format: str,
    prompt_template: str = "structured",
) -> BaseFormatter:
    """Get appropriate formatter based on configuration.

    Args:
        citation_format: Citation format (structured, inline, footnote, none)
        prompt_template: Prompt template preference (for backward compatibility)

    Returns:
        Appropriate formatter instance
    """
    # Check prompt template first (for backward compatibility)
    if prompt_template == "structured":
        return StructuredFormatter()

    # Then check citation format
    if citation_format == "structured":
        return StructuredFormatter()
    if citation_format == "inline":
        return InlineFormatter()
    if citation_format == "footnote":
        return FootnoteFormatter()
    # "none" or any other value
    return PlainFormatter()


__all__ = [
    # Base
    "BaseFormatter",
    # Formatters
    "StructuredFormatter",
    "InlineFormatter",
    "FootnoteFormatter",
    "PlainFormatter",
    "FullDocumentFormatter",
    # Factory
    "get_formatter",
]
