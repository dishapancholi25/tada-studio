"""Custom exceptions for async agent execution.

This module provides specialized exception classes for different failure
modes in async agent execution, enabling precise error handling and
better debugging.
"""


class AsyncAgentExecutionError(Exception):
    """Base exception for async agent execution failures.

    All async agent execution exceptions inherit from this base class,
    allowing consumers to catch all async agent errors with a single
    exception handler if desired.
    """

    def __init__(self, message: str, agent_name: str = None, **context):
        """Initialize the exception with message and optional context.

        Args:
            message: Human-readable error message
            agent_name: Name of the agent that failed (if applicable)
            **context: Additional context information for debugging
        """
        super().__init__(message)
        self.agent_name = agent_name
        self.context = context


class LLMBuildError(AsyncAgentExecutionError):
    """Failed to build or initialize LLM instance.

    Raised when LLM construction fails due to invalid configuration,
    missing credentials, or other initialization issues.
    """

    pass


class ToolExecutionError(AsyncAgentExecutionError):
    """Tool execution failed during agent execution.

    Raised when a tool invoked by the agent fails to execute properly.
    Contains information about which tool failed and why.
    """

    def __init__(self, message: str, tool_name: str = None, **context):
        """Initialize with tool-specific context.

        Args:
            message: Human-readable error message
            tool_name: Name of the tool that failed
            **context: Additional context (args, stack trace, etc.)
        """
        super().__init__(message, **context)
        self.tool_name = tool_name


class MemoryOperationError(AsyncAgentExecutionError):
    """Memory retrieval or storage operation failed.

    Raised when memory operations (get or store) fail. This is often
    non-fatal and can be handled gracefully by continuing without memory.
    """

    pass


class MessageBuildError(AsyncAgentExecutionError):
    """Failed to construct message list for LLM.

    Raised when message preparation fails due to invalid configuration
    or missing required data.
    """

    pass


class StructuredOutputError(AsyncAgentExecutionError):
    """Structured output execution or validation failed.

    Raised when structured output schema creation or execution fails.
    """

    pass


class TokenCountError(AsyncAgentExecutionError):
    """Token counting or metadata extraction failed.

    Raised when token counting operations fail. This is typically
    non-fatal and execution can continue without token counts.
    """

    pass
