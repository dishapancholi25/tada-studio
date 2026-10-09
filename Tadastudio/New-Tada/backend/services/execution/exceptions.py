"""
Exception hierarchy for execution engine.

This module defines custom exceptions used throughout the execution engine,
providing structured error handling and better debugging capabilities.
"""

from typing import Any, Dict, Optional


class ExecutionError(Exception):
    """
    Base exception for all execution-related errors.

    Attributes:
        message: Human-readable error message
        execution_id: Execution identifier where error occurred
        context: Additional context about the error
        original_error: The original exception if this wraps another error
    """

    def __init__(
        self,
        message: str,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize execution error.

        Args:
            message: Human-readable error message
            execution_id: Execution identifier
            context: Additional context dict
            original_error: Original exception if wrapping
        """
        super().__init__(message)
        self.message = message
        self.execution_id = execution_id
        self.context = context or {}
        self.original_error = original_error

    def __str__(self) -> str:
        """Format error message with context."""
        parts = [self.message]
        if self.execution_id:
            parts.append(f"(execution_id: {self.execution_id})")
        if self.context:
            parts.append(f"Context: {self.context}")
        if self.original_error:
            parts.append(f"Caused by: {self.original_error}")
        return " ".join(parts)


class NodeExecutionError(ExecutionError):
    """
    Exception raised when a node execution fails.

    Attributes:
        node_id: ID of the node that failed
        node_name: Name of the node that failed
        node_type: Type of the node that failed
    """

    def __init__(
        self,
        message: str,
        node_id: Optional[str] = None,
        node_name: Optional[str] = None,
        node_type: Optional[str] = None,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize node execution error.

        Args:
            message: Error message
            node_id: Node identifier
            node_name: Node display name
            node_type: Node type (e.g., "AGENT", "HTTP_REQUEST")
            execution_id: Execution identifier
            context: Additional context
            original_error: Original exception
        """
        super().__init__(message, execution_id, context, original_error)
        self.node_id = node_id
        self.node_name = node_name
        self.node_type = node_type

    def __str__(self) -> str:
        """Format error with node details."""
        parts = [self.message]
        if self.node_name:
            parts.append(f"Node: {self.node_name}")
        if self.node_id:
            parts.append(f"(id: {self.node_id})")
        if self.node_type:
            parts.append(f"Type: {self.node_type}")
        if self.execution_id:
            parts.append(f"Execution: {self.execution_id}")
        if self.original_error:
            parts.append(f"Caused by: {self.original_error}")
        return " | ".join(parts)


class CheckpointError(ExecutionError):
    """
    Exception raised when checkpoint operations fail.

    Attributes:
        checkpoint_id: ID of the checkpoint
        thread_id: Thread ID for checkpointing
        operation: The operation that failed (save, load, delete)
    """

    def __init__(
        self,
        message: str,
        checkpoint_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        operation: Optional[str] = None,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize checkpoint error.

        Args:
            message: Error message
            checkpoint_id: Checkpoint identifier
            thread_id: Thread identifier
            operation: Operation that failed
            execution_id: Execution identifier
            context: Additional context
            original_error: Original exception
        """
        super().__init__(message, execution_id, context, original_error)
        self.checkpoint_id = checkpoint_id
        self.thread_id = thread_id
        self.operation = operation

    def __str__(self) -> str:
        """Format error with checkpoint details."""
        parts = [self.message]
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.checkpoint_id:
            parts.append(f"Checkpoint: {self.checkpoint_id}")
        if self.thread_id:
            parts.append(f"Thread: {self.thread_id}")
        if self.original_error:
            parts.append(f"Caused by: {self.original_error}")
        return " | ".join(parts)


class CheckpointResumeError(CheckpointError):
    """
    Exception raised when resuming from a checkpoint fails.

    More specific than CheckpointError for resume operations.
    """

    def __init__(
        self,
        message: str,
        checkpoint_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize checkpoint resume error."""
        super().__init__(
            message=message,
            checkpoint_id=checkpoint_id,
            thread_id=thread_id,
            operation="resume",
            execution_id=execution_id,
            context=context,
            original_error=original_error,
        )


class GraphBuildError(ExecutionError):
    """
    Exception raised when graph building fails.

    Attributes:
        graph_name: Name of the graph
        node_id: ID of the node causing the error (if applicable)
        phase: Build phase where error occurred (nodes, edges, conditions)
    """

    def __init__(
        self,
        message: str,
        graph_name: Optional[str] = None,
        node_id: Optional[str] = None,
        phase: Optional[str] = None,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize graph build error.

        Args:
            message: Error message
            graph_name: Graph name
            node_id: Node identifier (if relevant)
            phase: Build phase (nodes, edges, conditions, compilation)
            execution_id: Execution identifier
            context: Additional context
            original_error: Original exception
        """
        super().__init__(message, execution_id, context, original_error)
        self.graph_name = graph_name
        self.node_id = node_id
        self.phase = phase

    def __str__(self) -> str:
        """Format error with graph build details."""
        parts = [self.message]
        if self.graph_name:
            parts.append(f"Graph: {self.graph_name}")
        if self.phase:
            parts.append(f"Phase: {self.phase}")
        if self.node_id:
            parts.append(f"Node: {self.node_id}")
        if self.original_error:
            parts.append(f"Caused by: {self.original_error}")
        return " | ".join(parts)


class ConditionEvaluationError(ExecutionError):
    """
    Exception raised when condition evaluation fails.

    Attributes:
        condition_type: Type of condition (value, branch, llm, expression)
        node_id: ID of the condition node
        condition_config: Configuration that caused the error
    """

    def __init__(
        self,
        message: str,
        condition_type: Optional[str] = None,
        node_id: Optional[str] = None,
        condition_config: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize condition evaluation error.

        Args:
            message: Error message
            condition_type: Condition type
            node_id: Node identifier
            condition_config: Condition configuration
            execution_id: Execution identifier
            context: Additional context
            original_error: Original exception
        """
        super().__init__(message, execution_id, context, original_error)
        self.condition_type = condition_type
        self.node_id = node_id
        self.condition_config = condition_config

    def __str__(self) -> str:
        """Format error with condition details."""
        parts = [self.message]
        if self.condition_type:
            parts.append(f"Type: {self.condition_type}")
        if self.node_id:
            parts.append(f"Node: {self.node_id}")
        if self.original_error:
            parts.append(f"Caused by: {self.original_error}")
        return " | ".join(parts)


class ValidationError(ExecutionError):
    """
    Exception raised when validation fails.

    Attributes:
        validation_type: Type of validation (config, input, state)
        failed_checks: List of failed validation checks
    """

    def __init__(
        self,
        message: str,
        validation_type: Optional[str] = None,
        failed_checks: Optional[list] = None,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """
        Initialize validation error.

        Args:
            message: Error message
            validation_type: Type of validation
            failed_checks: List of failed checks
            execution_id: Execution identifier
            context: Additional context
            original_error: Original exception
        """
        super().__init__(message, execution_id, context, original_error)
        self.validation_type = validation_type
        self.failed_checks = failed_checks or []

    def __str__(self) -> str:
        """Format error with validation details."""
        parts = [self.message]
        if self.validation_type:
            parts.append(f"Type: {self.validation_type}")
        if self.failed_checks:
            parts.append(f"Failed checks: {', '.join(self.failed_checks)}")
        return " | ".join(parts)


class TimeoutError(ExecutionError):
    """
    Exception raised when execution exceeds timeout.

    Attributes:
        timeout_seconds: Configured timeout
        elapsed_seconds: Actual elapsed time
    """

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        elapsed_seconds: Optional[float] = None,
        execution_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize timeout error.

        Args:
            message: Error message
            timeout_seconds: Configured timeout
            elapsed_seconds: Elapsed time
            execution_id: Execution identifier
            context: Additional context
        """
        super().__init__(message, execution_id, context)
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds

    def __str__(self) -> str:
        """Format error with timeout details."""
        parts = [self.message]
        if self.timeout_seconds is not None:
            parts.append(f"Timeout: {self.timeout_seconds}s")
        if self.elapsed_seconds is not None:
            parts.append(f"Elapsed: {self.elapsed_seconds}s")
        return " | ".join(parts)
