"""
Structured logging utilities for execution engine.

This module provides structured logging with context management,
timing decorators, and consistent log formatting for execution tracking.
"""

import functools
import time
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional, Union

from backend.services.config import get_logger


execution_logger = get_logger("execution")


# Sensitive field names that should be redacted in logs
SENSITIVE_FIELDS = {
    "api_key",
    "password",
    "secret",
    "token",
    "auth_token",
    "access_token",
    "refresh_token",
    "bearer_token",
    "api_secret",
    "private_key",
    "client_secret",
    "auth_config",
    "oauth2_config",
    "credentials",
    "authorization",
    "environment_variables",  # May contain secrets
}

# Field names that should show partial values (e.g., first 8 chars)
PARTIAL_REDACT_FIELDS = {
    "connection_id",
    "server_url",
}


def redact_sensitive_data(
    data: Union[Dict[str, Any], Any],
    redact_text: str = "***REDACTED***",
    partial_redact_text: str = "***",
) -> Union[Dict[str, Any], Any]:
    """
    Redact sensitive fields from data for safe logging.

    Handles both dictionaries and dataclass instances. Recursively processes
    nested structures to ensure all sensitive data is redacted.

    Args:
        data: Data to redact (dict, dataclass, or other)
        redact_text: Text to use for fully redacted fields
        partial_redact_text: Text to append for partially redacted fields

    Returns:
        Redacted copy of the data

    Example:
        >>> config = {"api_key": "secret123", "max_results": 5}
        >>> redacted = redact_sensitive_data(config)
        >>> print(redacted)
        {"api_key": "***REDACTED***", "max_results": 5}
    """
    # Convert dataclass to dict if needed
    if is_dataclass(data) and not isinstance(data, type):
        data = asdict(data)

    # If not a dict, return as-is
    if not isinstance(data, dict):
        return data

    # Create a copy to avoid modifying original
    redacted = {}

    for key, value in data.items():
        key_lower = key.lower()

        # Check if this is a sensitive field
        if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
            # Fully redact sensitive fields
            if value and str(value).strip():
                redacted[key] = redact_text
            else:
                redacted[key] = value
        elif any(partial in key_lower for partial in PARTIAL_REDACT_FIELDS):
            # Partially redact fields (show first 8 chars)
            if value and isinstance(value, str) and len(value) > 8:
                redacted[key] = value[:8] + partial_redact_text
            else:
                redacted[key] = value
        elif isinstance(value, dict):
            # Recursively redact nested dicts
            redacted[key] = redact_sensitive_data(
                value, redact_text, partial_redact_text
            )
        elif isinstance(value, list):
            # Recursively redact lists
            redacted[key] = [
                redact_sensitive_data(item, redact_text, partial_redact_text)
                if isinstance(item, (dict, list))
                else item
                for item in value
            ]
        elif is_dataclass(value) and not isinstance(value, type):
            # Recursively redact dataclass instances
            redacted[key] = redact_sensitive_data(
                value, redact_text, partial_redact_text
            )
        else:
            # Keep non-sensitive values as-is
            redacted[key] = value

    return redacted


def safe_repr(obj: Any) -> str:
    """
    Create a safe string representation of an object with sensitive data redacted.

    Args:
        obj: Object to represent

    Returns:
        String representation with redacted sensitive fields

    Example:
        >>> config = WebSearchConfig(api_key="secret123", max_results=5)
        >>> print(safe_repr(config))
        "WebSearchConfig(api_key='***REDACTED***', max_results=5)"
    """
    redacted = redact_sensitive_data(obj)

    if isinstance(redacted, dict):
        return repr(redacted)
    else:
        return repr(obj)


class ExecutionLogger:
    """
    Structured logger for execution tracking.

    Provides methods for logging execution events with consistent formatting
    and automatic context propagation.

    Example:
        >>> logger = ExecutionLogger("exec-123")
        >>> logger.log_execution_start("my-workflow", {"input": "data"})
        >>> logger.log_node_start("node-1", "Agent Node", "AGENT")
        >>> # ... node execution ...
        >>> logger.log_node_end("node-1", {"output": "result"}, 1.5)
        >>> logger.log_execution_end("success", {"final": "output"}, 10.2)
    """

    def __init__(self, execution_id: str, user_id: Optional[str] = None):
        """
        Initialize execution logger.

        Args:
            execution_id: Unique execution identifier
            user_id: Optional user identifier
        """
        self.execution_id = execution_id
        self.user_id = user_id
        self._context: Dict[str, Any] = {
            "execution_id": execution_id,
        }
        if user_id:
            self._context["user_id"] = user_id

    def _log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log message with context.

        Args:
            level: Log level (info, debug, warning, error)
            message: Log message
            extra: Additional context to include
        """
        context = {**self._context, **(extra or {})}
        log_func = getattr(execution_logger, level)

        # Format message with context
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        formatted_message = f"{message} | {context_str}"

        log_func(formatted_message)

    def log_execution_start(
        self,
        graph_name: str,
        initial_input: Dict[str, Any],
        workflow_id: Optional[str] = None,
    ) -> None:
        """
        Log execution start event.

        Args:
            graph_name: Name of the graph being executed
            initial_input: Initial input data
            workflow_id: Optional workflow identifier
        """
        extra = {
            "event": "execution_start",
            "graph_name": graph_name,
            "workflow_id": workflow_id,
            "input_keys": list(initial_input.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._log("info", f"Starting execution of graph: {graph_name}", extra)

    def log_execution_end(
        self,
        status: str,
        output: Any,
        duration_seconds: float,
        nodes_executed: int = 0,
    ) -> None:
        """
        Log execution end event.

        Args:
            status: Execution status (success, failed, interrupted)
            output: Final output value
            duration_seconds: Total execution duration
            nodes_executed: Number of nodes executed
        """
        extra = {
            "event": "execution_end",
            "status": status,
            "duration_seconds": round(duration_seconds, 3),
            "nodes_executed": nodes_executed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        level = "info" if status == "success" else "error"
        self._log(
            level,
            f"Execution {status} after {duration_seconds:.2f}s ({nodes_executed} nodes)",
            extra,
        )

    def log_node_start(
        self,
        node_id: str,
        node_name: str,
        node_type: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log node start event.

        Args:
            node_id: Node identifier
            node_name: Node display name
            node_type: Node type (AGENT, HTTP_REQUEST, etc.)
            input_data: Optional input data
        """
        extra = {
            "event": "node_start",
            "node_id": node_id,
            "node_name": node_name,
            "node_type": node_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if input_data:
            extra["input_keys"] = list(input_data.keys())

        self._log("debug", f"Starting node: {node_name} ({node_type})", extra)

    def log_node_end(
        self,
        node_id: str,
        output: Dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """
        Log node end event.

        Args:
            node_id: Node identifier
            output: Node output data
            duration_seconds: Node execution duration
        """
        extra = {
            "event": "node_end",
            "node_id": node_id,
            "duration_seconds": round(duration_seconds, 3),
            "output_keys": list(output.keys()) if isinstance(output, dict) else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._log("debug", f"Node completed in {duration_seconds:.2f}s", extra)

    def log_error(
        self,
        error: Exception,
        node_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log error event.

        Args:
            error: The exception that occurred
            node_id: Optional node identifier where error occurred
            context: Additional error context
        """
        extra = {
            "event": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if node_id:
            extra["node_id"] = node_id
        if context:
            extra["error_context"] = context

        self._log("error", f"Error occurred: {error}", extra)

    def log_checkpoint(
        self,
        checkpoint_id: str,
        checkpoint_type: str,
        node_id: str,
    ) -> None:
        """
        Log checkpoint creation.

        Args:
            checkpoint_id: Checkpoint identifier
            checkpoint_type: Type of checkpoint (auto, manual, email)
            node_id: Node where checkpoint was created
        """
        extra = {
            "event": "checkpoint_created",
            "checkpoint_id": checkpoint_id,
            "checkpoint_type": checkpoint_type,
            "node_id": node_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._log(
            "info", f"Checkpoint created: {checkpoint_id} ({checkpoint_type})", extra
        )

    @contextmanager
    def execution_context(self, graph_name: str, initial_input: Dict[str, Any]):
        """
        Context manager for execution logging.

        Automatically logs start and end events with timing.

        Args:
            graph_name: Name of the graph
            initial_input: Initial input data

        Example:
            >>> logger = ExecutionLogger("exec-123")
            >>> with logger.execution_context("my-workflow", {"input": "data"}):
            ...     # Execute workflow
            ...     pass
        """
        start_time = time.time()
        self.log_execution_start(graph_name, initial_input)

        try:
            yield self
        except Exception as e:
            duration = time.time() - start_time
            self.log_error(e)
            self.log_execution_end("failed", None, duration)
            raise
        else:
            duration = time.time() - start_time
            self.log_execution_end("success", None, duration)

    @contextmanager
    def node_context(
        self,
        node_id: str,
        node_name: str,
        node_type: str,
        input_data: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for node logging.

        Automatically logs start and end events with timing.

        Args:
            node_id: Node identifier
            node_name: Node display name
            node_type: Node type
            input_data: Optional input data

        Example:
            >>> with logger.node_context("node-1", "Agent", "AGENT"):
            ...     # Execute node
            ...     result = await node.execute()
        """
        start_time = time.time()
        self.log_node_start(node_id, node_name, node_type, input_data)

        try:
            yield self
        except Exception as e:
            duration = time.time() - start_time
            self.log_error(e, node_id=node_id)
            raise
        else:
            duration = time.time() - start_time
            self.log_node_end(node_id, {}, duration)


def timing_decorator(log_level: str = "info"):
    """
    Log function execution time.

    Args:
        log_level: Log level to use (info, debug, etc.)

    Example:
        >>> @timing_decorator("debug")
        ... async def execute_node(node):
        ...     # ... execution logic
        ...     pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__

            execution_logger.debug(f"Starting {func_name}")

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                log_func = getattr(execution_logger, log_level)
                log_func(f"{func_name} completed in {duration:.3f}s")

                return result
            except Exception as e:
                duration = time.time() - start_time
                execution_logger.error(f"{func_name} failed after {duration:.3f}s: {e}")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__

            execution_logger.debug(f"Starting {func_name}")

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                log_func = getattr(execution_logger, log_level)
                log_func(f"{func_name} completed in {duration:.3f}s")

                return result
            except Exception as e:
                duration = time.time() - start_time
                execution_logger.error(f"{func_name} failed after {duration:.3f}s: {e}")
                raise

        # Return appropriate wrapper based on whether func is async
        if functools.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
