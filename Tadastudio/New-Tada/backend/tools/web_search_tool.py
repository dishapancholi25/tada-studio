"""Web Search Tool - Backward Compatibility Wrapper.

DEPRECATED: This module is maintained for backward compatibility only.
New code should import from tools.web_search instead.

The complex implementation has been refactored into a modular structure:
- tools/web_search/schemas.py - Pydantic models and schemas
- tools/web_search/config.py - Configuration and validation
- tools/web_search/handlers.py - Business logic handlers
- tools/web_search/execution.py - Metadata tracking
- tools/web_search/factory.py - Simplified tool factories

This wrapper simply re-exports the factory functions to maintain
backward compatibility with existing imports.
"""

import warnings

# Re-export factory functions from the new modular implementation
from .web_search import create_web_search_and_summarize_tool, create_web_search_tool


# Issue deprecation warning
warnings.warn(
    "Importing from tools.web_search_tool is deprecated. "
    "Please use 'from tools.web_search import create_web_search_tool' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "create_web_search_tool",
    "create_web_search_and_summarize_tool",
]
