"""Document Search Tool - Backward Compatibility Wrapper.

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from tools.document_search instead.

The complex implementation has been refactored into a modular structure:
- tools/document_search/schemas.py - Pydantic models and schemas
- tools/document_search/config.py - Configuration and validation
- tools/document_search/formatters.py - Result formatting logic
- tools/document_search/handlers.py - Business logic handlers
- tools/document_search/execution.py - Metadata tracking
- tools/document_search/factory.py - Simplified tool factories

This wrapper simply re-exports the factory functions to maintain
backward compatibility with existing imports.
"""

import warnings

# Re-export factory functions from the new modular implementation
from .document_search import create_document_qa_tool, create_document_search_tool


# Issue deprecation warning
warnings.warn(
    "Importing from tools.document_search_tool is deprecated. "
    "Please use 'from tools.document_search import create_document_search_tool' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "create_document_search_tool",
    "create_document_qa_tool",
]
