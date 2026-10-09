"""Graph building and storage services.

This package provides comprehensive graph management functionality including:
- GraphManager: Main facade for all graph operations
- Node and connection management
- Graph CRUD operations
- Orchestrator and delegation management
- Validation and export services
- Compilation services

Public API:
    GraphManager: Main interface for graph operations
    GraphStorageService: Database persistence
    GraphBuilder: Graph construction
    EdgeBuilder: Edge construction
    GraphCache: Caching utilities
"""

# Main GraphManager facade
from .manager import GraphManager

# Service modules (for advanced usage)
from .node_manager import NodeManager
from .connection_manager import ConnectionManager
from .graph_crud import GraphCRUDService
from .orchestrator_manager import OrchestratorManager
from .validation import ValidationService
from .export import ExportService
from .compilation import CompilationService

# Existing services
from .builder import GraphBuilder
from .cache import GraphCache
from .edge_builder import EdgeBuilder
from .storage import GraphStorageService, resolve_user_id

# Constants and exceptions (for advanced usage)
from .constants import (
    DEFAULT_AGENT_SYSTEM_PROMPT,
    LOG_PREFIX_NODE_MANAGER,
    LOG_PREFIX_CONNECTION_MANAGER,
    LOG_PREFIX_GRAPH_CRUD,
    LOG_PREFIX_ORCHESTRATOR,
    LOG_PREFIX_VALIDATION,
    LOG_PREFIX_EXPORT,
    LOG_PREFIX_COMPILATION,
    LOG_PREFIX_GRAPH_MANAGER,
)
from .exceptions import (
    GraphOperationError,
    GraphNotFoundError,
    NodeNotFoundError,
    NodeValidationError,
    ConnectionValidationError,
    CircularDependencyError,
    GraphValidationError,
    CompilationError,
    ExportError,
    OrchestratorConfigurationError,
    SubAgentCreationError,
)


__all__ = [
    # Main facade (primary public API)
    "GraphManager",
    # Service modules
    "NodeManager",
    "ConnectionManager",
    "GraphCRUDService",
    "OrchestratorManager",
    "ValidationService",
    "ExportService",
    "CompilationService",
    # Existing services
    "GraphBuilder",
    "EdgeBuilder",
    "GraphCache",
    "GraphStorageService",
    "resolve_user_id",
    # Constants
    "DEFAULT_AGENT_SYSTEM_PROMPT",
    "LOG_PREFIX_NODE_MANAGER",
    "LOG_PREFIX_CONNECTION_MANAGER",
    "LOG_PREFIX_GRAPH_CRUD",
    "LOG_PREFIX_ORCHESTRATOR",
    "LOG_PREFIX_VALIDATION",
    "LOG_PREFIX_EXPORT",
    "LOG_PREFIX_COMPILATION",
    "LOG_PREFIX_GRAPH_MANAGER",
    # Exceptions
    "GraphOperationError",
    "GraphNotFoundError",
    "NodeNotFoundError",
    "NodeValidationError",
    "ConnectionValidationError",
    "CircularDependencyError",
    "GraphValidationError",
    "CompilationError",
    "ExportError",
    "OrchestratorConfigurationError",
    "SubAgentCreationError",
]
