"""Custom exceptions for Graph API.

This module defines a hierarchy of custom exceptions for the Graph API,
providing structured error handling with appropriate HTTP status codes.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException


class GraphAPIException(HTTPException):
    """Base exception for Graph API errors.

    All Graph API exceptions inherit from this base class.
    """

    def __init__(
        self, status_code: int, detail: str, headers: Optional[Dict[str, Any]] = None
    ):
        """Initialize GraphAPIException.

        Args:
            status_code: HTTP status code
            detail: Error message
            headers: Optional HTTP headers
        """
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class GraphNotFoundError(GraphAPIException):
    """Raised when a graph is not found."""

    def __init__(self, graph_name: str):
        """Initialize GraphNotFoundError.

        Args:
            graph_name: Name of the graph that was not found
        """
        super().__init__(status_code=404, detail=f"Graph '{graph_name}' not found")


class NodeNotFoundError(GraphAPIException):
    """Raised when a node is not found."""

    def __init__(self, node_id: str, graph_name: Optional[str] = None):
        """Initialize NodeNotFoundError.

        Args:
            node_id: ID of the node that was not found
            graph_name: Optional graph name for context
        """
        if graph_name:
            detail = f"Node '{node_id}' not found in graph '{graph_name}'"
        else:
            detail = f"Node '{node_id}' not found"
        super().__init__(status_code=404, detail=detail)


class ConnectionNotFoundError(GraphAPIException):
    """Raised when a connection is not found."""

    def __init__(self, source_id: str, target_id: str):
        """Initialize ConnectionNotFoundError.

        Args:
            source_id: Source node ID
            target_id: Target node ID
        """
        super().__init__(
            status_code=404,
            detail=f"Connection from '{source_id}' to '{target_id}' not found",
        )


class GraphValidationError(GraphAPIException):
    """Raised when graph validation fails."""

    def __init__(self, graph_name: str, errors: list):
        """Initialize GraphValidationError.

        Args:
            graph_name: Name of the graph that failed validation
            errors: List of validation errors
        """
        error_details = "; ".join(errors)
        super().__init__(
            status_code=400,
            detail=f"Graph '{graph_name}' validation failed: {error_details}",
        )


class NodeValidationError(GraphAPIException):
    """Raised when node validation fails."""

    def __init__(self, node_id: str, error: str):
        """Initialize NodeValidationError.

        Args:
            node_id: ID of the node that failed validation
            error: Validation error message
        """
        super().__init__(
            status_code=400, detail=f"Node '{node_id}' validation failed: {error}"
        )


class ExecutionError(GraphAPIException):
    """Raised when graph execution fails."""

    def __init__(self, execution_id: str, error: str):
        """Initialize ExecutionError.

        Args:
            execution_id: ID of the failed execution
            error: Error message
        """
        super().__init__(
            status_code=500, detail=f"Execution '{execution_id}' failed: {error}"
        )


class ExecutionNotFoundError(GraphAPIException):
    """Raised when an execution is not found."""

    def __init__(self, execution_id: str):
        """Initialize ExecutionNotFoundError.

        Args:
            execution_id: ID of the execution that was not found
        """
        super().__init__(
            status_code=404, detail=f"Execution '{execution_id}' not found"
        )


class FileUploadError(GraphAPIException):
    """Raised when file upload fails."""

    def __init__(self, error: str):
        """Initialize FileUploadError.

        Args:
            error: Error message
        """
        super().__init__(status_code=400, detail=f"File upload failed: {error}")


class FileProcessingError(GraphAPIException):
    """Raised when file processing fails."""

    def __init__(self, file_path: str, error: str):
        """Initialize FileProcessingError.

        Args:
            file_path: Path to file that failed processing
            error: Error message
        """
        super().__init__(
            status_code=500, detail=f"Failed to process file '{file_path}': {error}"
        )


class UnauthorizedError(GraphAPIException):
    """Raised when user is not authorized."""

    def __init__(self, detail: str = "Unauthorized"):
        """Initialize UnauthorizedError.

        Args:
            detail: Error message
        """
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(GraphAPIException):
    """Raised when user is forbidden from accessing resource."""

    def __init__(self, detail: str = "You do not have access to this resource"):
        """Initialize ForbiddenError.

        Args:
            detail: Error message
        """
        super().__init__(status_code=403, detail=detail)


class GraphAlreadyExistsError(GraphAPIException):
    """Raised when attempting to create a graph that already exists."""

    def __init__(self, graph_name: str):
        """Initialize GraphAlreadyExistsError.

        Args:
            graph_name: Name of the graph that already exists
        """
        super().__init__(status_code=400, detail=f"Graph '{graph_name}' already exists")


class InvalidRequestError(GraphAPIException):
    """Raised when request is invalid."""

    def __init__(self, detail: str):
        """Initialize InvalidRequestError.

        Args:
            detail: Error message
        """
        super().__init__(status_code=400, detail=detail)
