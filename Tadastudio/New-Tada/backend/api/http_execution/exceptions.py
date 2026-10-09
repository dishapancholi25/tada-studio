"""Custom exceptions for HTTP execution API.

This module defines domain-specific exceptions for HTTP-triggered workflow execution,
providing clear error messages and proper HTTP status code mappings.
"""

from typing import Optional


class HttpExecutionException(Exception):
    """Base exception for HTTP execution errors."""

    def __init__(self, message: str, status_code: int = 500):
        """Initialize HTTP execution exception.

        Args:
            message: Error message
            status_code: HTTP status code to return
        """
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class WorkflowNotPublishedException(HttpExecutionException):
    """Raised when attempting to execute a workflow that is not published."""

    def __init__(self, workflow_name: str):
        """Initialize workflow not published exception.

        Args:
            workflow_name: Name of the workflow
        """
        message = (
            f"Workflow '{workflow_name}' is not published. "
            "Only published workflows can be executed via HTTP."
        )
        super().__init__(message, status_code=403)
        self.workflow_name = workflow_name


class AuthenticationRequiredException(HttpExecutionException):
    """Raised when authentication is required but no credentials provided."""

    def __init__(self, workflow_name: str):
        """Initialize authentication required exception.

        Args:
            workflow_name: Name of the workflow
        """
        message = (
            f"Authentication required for workflow '{workflow_name}'. "
            "Use Authorization: Bearer <token> header or ?token=na_xxx query parameter."
        )
        super().__init__(message, status_code=401)
        self.workflow_name = workflow_name


class InvalidAuthenticationTokenException(HttpExecutionException):
    """Raised when authentication token is invalid or expired."""

    def __init__(self, detail: Optional[str] = None):
        """Initialize invalid authentication token exception.

        Args:
            detail: Optional additional details about the error
        """
        message = detail or "Invalid or expired authentication token"
        super().__init__(message, status_code=401)


class RateLimitExceededException(HttpExecutionException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit_type: str,
        retry_after: int,
        reset_time: Optional[int] = None,
        remaining: int = 0,
    ):
        """Initialize rate limit exceeded exception.

        Args:
            limit_type: Type of rate limit hit (e.g., 'requests', 'tokens')
            retry_after: Seconds until the rate limit resets
            reset_time: Unix timestamp when the limit resets
            remaining: Number of remaining requests/tokens
        """
        message = (
            f"Rate limit exceeded for {limit_type}. Try again in {retry_after} seconds."
        )
        super().__init__(message, status_code=429)
        self.limit_type = limit_type
        self.retry_after = retry_after
        self.reset_time = reset_time
        self.remaining = remaining


class WorkflowNotFoundException(HttpExecutionException):
    """Raised when the specified workflow cannot be found."""

    def __init__(self, workflow_name: str):
        """Initialize workflow not found exception.

        Args:
            workflow_name: Name of the workflow
        """
        message = f"Workflow '{workflow_name}' not found"
        super().__init__(message, status_code=404)
        self.workflow_name = workflow_name


class ExecutionTimeoutException(HttpExecutionException):
    """Raised when execution exceeds the configured timeout."""

    def __init__(self, timeout_seconds: int, execution_id: str):
        """Initialize execution timeout exception.

        Args:
            timeout_seconds: Configured timeout in seconds
            execution_id: ID of the timed out execution
        """
        message = f"Execution timeout after {timeout_seconds} seconds"
        super().__init__(message, status_code=408)
        self.timeout_seconds = timeout_seconds
        self.execution_id = execution_id


class InvalidInputException(HttpExecutionException):
    """Raised when input validation fails."""

    def __init__(self, message: str):
        """Initialize invalid input exception.

        Args:
            message: Description of the validation error
        """
        super().__init__(message, status_code=400)


class CheckpointNotFoundException(HttpExecutionException):
    """Raised when a checkpoint state cannot be found for resumption."""

    def __init__(self, thread_id: str):
        """Initialize checkpoint not found exception.

        Args:
            thread_id: Thread ID of the paused execution
        """
        message = f"No paused execution found for thread_id: {thread_id}"
        super().__init__(message, status_code=404)
        self.thread_id = thread_id


class ExecutionFailedException(HttpExecutionException):
    """Raised when workflow execution fails."""

    def __init__(self, execution_id: str, error_message: str):
        """Initialize execution failed exception.

        Args:
            execution_id: ID of the failed execution
            error_message: Error message from the execution
        """
        message = f"Execution failed: {error_message}"
        super().__init__(message, status_code=500)
        self.execution_id = execution_id
        self.error_message = error_message


class FileProcessingException(HttpExecutionException):
    """Raised when file upload processing fails."""

    def __init__(self, filename: str, error: str):
        """Initialize file processing exception.

        Args:
            filename: Name of the file being processed
            error: Description of the processing error
        """
        message = f"Failed to process file '{filename}': {error}"
        super().__init__(message, status_code=400)
        self.filename = filename
