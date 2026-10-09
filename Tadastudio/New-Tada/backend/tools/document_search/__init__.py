"""
Document Search Tool - Modular implementation.

This module provides document search capabilities with configurable options for
vector similarity search, full-text search, and hybrid search across document
collections and specific documents.

Main exports:
    - create_document_search_tool: Factory for standard document search tool
    - create_document_qa_tool: Factory for document Q&A tool
"""

# Configuration
from .config import (
    DEFAULT_FULL_DOCUMENT_CONFIG,
    DEFAULT_HYBRID_CONFIG,
    DEFAULT_SIMILARITY_CONFIG,
    ConfigValidator,
    ToolDescriptionBuilder,
)

# Execution tracking
from .execution import (
    ExecutionStorage,
    attach_execution_metadata,
    get_document_search_execution_for_node,
    get_execution_storage,
    get_last_document_search_execution,
)

# Factory functions (primary interface)
from .factory import create_document_qa_tool, create_document_search_tool

# Formatters
from .formatters import (
    FootnoteFormatter,
    FullDocumentFormatter,
    InlineFormatter,
    PlainFormatter,
    StructuredFormatter,
    get_formatter,
)

# Handlers (for advanced usage)
from .handlers import (
    execute_collection_search,
    execute_document_search,
    execute_full_document_retrieval,
    execute_search,
)

# Schemas
from .schemas import (
    DocumentSearchArgs,
    DocumentSearchConfig,
    DocumentSearchExecutionMetadata,
    DocumentSearchResponse,
    SearchResultItem,
    ValidateConfigRequest,
    ValidateConfigResponse,
)


__all__ = [
    # Factory functions (primary interface)
    "create_document_search_tool",
    "create_document_qa_tool",
    # Schemas
    "DocumentSearchArgs",
    "DocumentSearchConfig",
    "SearchResultItem",
    "DocumentSearchResponse",
    "ValidateConfigRequest",
    "ValidateConfigResponse",
    "DocumentSearchExecutionMetadata",
    # Configuration
    "ToolDescriptionBuilder",
    "ConfigValidator",
    "DEFAULT_SIMILARITY_CONFIG",
    "DEFAULT_HYBRID_CONFIG",
    "DEFAULT_FULL_DOCUMENT_CONFIG",
    # Handlers (for advanced usage)
    "execute_search",
    "execute_collection_search",
    "execute_document_search",
    "execute_full_document_retrieval",
    # Formatters
    "get_formatter",
    "StructuredFormatter",
    "InlineFormatter",
    "FootnoteFormatter",
    "PlainFormatter",
    "FullDocumentFormatter",
    # Execution tracking
    "ExecutionStorage",
    "get_execution_storage",
    "attach_execution_metadata",
    "get_last_document_search_execution",
    "get_document_search_execution_for_node",
]
