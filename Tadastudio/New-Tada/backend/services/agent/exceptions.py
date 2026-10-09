"""Custom exceptions for agent compilation.

This module defines exception classes for various compilation failures,
providing better error handling and debugging support.
"""

from typing import Any, Dict, List, Optional


class CompilationError(Exception):
    """Base exception for all agent compilation errors.

    Args:
        message: Error message describing the compilation failure
        agent_id: Optional agent identifier
        context: Optional dictionary with additional error context
    """

    def __init__(
        self,
        message: str,
        agent_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize compilation error."""
        self.message = message
        self.agent_id = agent_id
        self.context = context or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context."""
        msg = f"[AGENT-COMPILATION] {self.message}"
        if self.agent_id:
            msg += f" (agent_id={self.agent_id})"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            msg += f" | Context: {context_str}"
        return msg


class LLMCompilationError(CompilationError):
    """Exception raised when LLM creation/configuration fails.

    Args:
        message: Error message
        provider: LLM provider name
        model_name: Model name
        agent_id: Optional agent identifier
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        agent_id: Optional[str] = None,
    ):
        """Initialize LLM compilation error."""
        context = {}
        if provider:
            context["provider"] = provider
        if model_name:
            context["model"] = model_name
        super().__init__(message, agent_id, context)


class ToolBindingError(CompilationError):
    """Exception raised when tool binding fails.

    Args:
        message: Error message
        tool_names: List of tool names that failed to bind
        agent_id: Optional agent identifier
    """

    def __init__(
        self,
        message: str,
        tool_names: Optional[List[str]] = None,
        agent_id: Optional[str] = None,
    ):
        """Initialize tool binding error."""
        context = {}
        if tool_names:
            context["failed_tools"] = ", ".join(tool_names)
        super().__init__(message, agent_id, context)


class ValidationError(CompilationError):
    """Exception raised when configuration validation fails.

    Args:
        message: Error message
        field: Field name that failed validation
        value: Invalid value
        agent_id: Optional agent identifier
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        agent_id: Optional[str] = None,
    ):
        """Initialize validation error."""
        context = {}
        if field:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)
        super().__init__(message, agent_id, context)


class CacheError(CompilationError):
    """Exception raised when cache operations fail.

    Args:
        message: Error message
        operation: Cache operation that failed (get, set, clear, etc.)
        cache_key: Optional cache key involved
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        cache_key: Optional[str] = None,
    ):
        """Initialize cache error."""
        context = {}
        if operation:
            context["operation"] = operation
        if cache_key:
            context["cache_key"] = cache_key
        super().__init__(message, None, context)
