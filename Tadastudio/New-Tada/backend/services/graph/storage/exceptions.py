"""
Custom exceptions for graph storage operations.

This module provides specific exception types for better error handling
and more informative error messages in graph storage operations.
"""


class GraphStorageError(Exception):
    """Base exception for all graph storage errors."""

    pass


class WorkflowNotFoundError(GraphStorageError):
    """Raised when a requested workflow cannot be found."""

    def __init__(self, workflow_identifier: str, message: str = None):
        """Initialize workflow not found error."""
        self.workflow_identifier = workflow_identifier
        if message is None:
            message = f"Workflow '{workflow_identifier}' not found"
        super().__init__(message)


class AccessDeniedError(GraphStorageError):
    """Raised when a user doesn't have permission to access a workflow."""

    def __init__(
        self, user_identifier: str, workflow_identifier: str, message: str = None
    ):
        """Initialize access denied error."""
        self.user_identifier = user_identifier
        self.workflow_identifier = workflow_identifier
        if message is None:
            message = f"User '{user_identifier}' does not have access to workflow '{workflow_identifier}'"
        super().__init__(message)


class UserNotFoundError(GraphStorageError):
    """Raised when a user cannot be resolved."""

    def __init__(self, user_identifier: str, message: str = None):
        """Initialize user not found error."""
        self.user_identifier = user_identifier
        if message is None:
            message = f"User '{user_identifier}' not found in system"
        super().__init__(message)


class GraphNotFoundError(GraphStorageError):
    """Raised when a graph cannot be found."""

    def __init__(self, graph_name: str, workspace_id: str = None, message: str = None):
        """Initialize graph not found error."""
        self.graph_name = graph_name
        self.workspace_id = workspace_id
        if message is None:
            workspace_info = f" in workspace '{workspace_id}'" if workspace_id else ""
            message = f"Graph '{graph_name}'{workspace_info} not found"
        super().__init__(message)


class GraphVersionNotFoundError(GraphStorageError):
    """Raised when a specific graph version cannot be found."""

    def __init__(self, graph_name: str, version: int, message: str = None):
        """Initialize graph version not found error."""
        self.graph_name = graph_name
        self.version = version
        if message is None:
            message = f"Graph '{graph_name}' version {version} not found"
        super().__init__(message)
