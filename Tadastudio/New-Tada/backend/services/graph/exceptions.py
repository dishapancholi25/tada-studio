"""Custom exceptions for graph operations.

This module defines domain-specific exceptions for graph management operations,
providing better error context and error handling capabilities.

Example:
    >>> from backend.services.graph.exceptions import NodeNotFoundError
    >>> raise NodeNotFoundError("agent-123", "my-workflow")
    NodeNotFoundError: Node 'agent-123' not found in graph 'my-workflow'
"""


class GraphOperationError(Exception):
    """Base exception for all graph operation errors."""

    pass


class GraphNotFoundError(GraphOperationError):
    """Raised when a requested graph cannot be found."""

    def __init__(self, graph_name: str):
        self.graph_name = graph_name
        super().__init__(f"Graph '{graph_name}' not found")


class NodeNotFoundError(GraphOperationError):
    """Raised when a requested node cannot be found."""

    def __init__(self, node_id: str, graph_name: str = None):
        self.node_id = node_id
        self.graph_name = graph_name
        message = f"Node '{node_id}' not found"
        if graph_name:
            message += f" in graph '{graph_name}'"
        super().__init__(message)


class NodeValidationError(GraphOperationError):
    """Raised when node validation fails."""

    def __init__(self, node_id: str, errors: list):
        self.node_id = node_id
        self.errors = errors
        error_list = "\n  - ".join(errors)
        super().__init__(f"Node '{node_id}' validation failed:\n  - {error_list}")


class ConnectionValidationError(GraphOperationError):
    """Raised when connection validation fails."""

    def __init__(self, source_id: str, target_id: str, reason: str):
        self.source_id = source_id
        self.target_id = target_id
        self.reason = reason
        super().__init__(f"Cannot connect '{source_id}' to '{target_id}': {reason}")


class CircularDependencyError(GraphOperationError):
    """Raised when a circular dependency is detected in the graph."""

    def __init__(self, cycle_path: list):
        self.cycle_path = cycle_path
        path_str = " -> ".join(cycle_path)
        super().__init__(f"Circular dependency detected: {path_str}")


class GraphValidationError(GraphOperationError):
    """Raised when graph validation fails."""

    def __init__(self, graph_name: str, errors: list, warnings: list = None):
        self.graph_name = graph_name
        self.errors = errors
        self.warnings = warnings or []
        error_list = "\n  - ".join(errors)
        message = f"Graph '{graph_name}' validation failed:\n  - {error_list}"
        if warnings:
            warning_list = "\n  - ".join(warnings)
            message += f"\nWarnings:\n  - {warning_list}"
        super().__init__(message)


class CompilationError(GraphOperationError):
    """Raised when graph compilation fails."""

    def __init__(self, graph_name: str, errors: list):
        self.graph_name = graph_name
        self.errors = errors
        error_list = "\n  - ".join(str(e) for e in errors)
        super().__init__(f"Failed to compile graph '{graph_name}':\n  - {error_list}")


class ExportError(GraphOperationError):
    """Raised when graph export fails."""

    def __init__(self, graph_name: str, format: str, reason: str):
        self.graph_name = graph_name
        self.format = format
        self.reason = reason
        super().__init__(f"Failed to export graph '{graph_name}' to {format}: {reason}")


class OrchestratorConfigurationError(GraphOperationError):
    """Raised when orchestrator configuration is invalid."""

    def __init__(self, node_id: str, reason: str):
        self.node_id = node_id
        self.reason = reason
        super().__init__(
            f"Invalid orchestrator configuration for node '{node_id}': {reason}"
        )


class SubAgentCreationError(GraphOperationError):
    """Raised when sub-agent creation fails."""

    def __init__(self, parent_id: str, reason: str):
        self.parent_id = parent_id
        self.reason = reason
        super().__init__(
            f"Failed to create sub-agent for parent '{parent_id}': {reason}"
        )
