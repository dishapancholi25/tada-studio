"""Custom exceptions for execution context management."""


class ExecutionContextError(Exception):
    """Base exception for execution context errors."""

    pass


class ContextNotSetError(ExecutionContextError):
    """Raised when attempting to access context that hasn't been set."""

    def __init__(self, message: str = "Execution context has not been set"):
        """
        Initialize ContextNotSetError.

        Args:
            message: Error message
        """
        super().__init__(message)
        self.message = message


class ContextAlreadySetError(ExecutionContextError):
    """Raised when attempting to set context that is already active."""

    def __init__(
        self,
        execution_id: str,
        message: str = "Execution context is already set",
    ):
        """
        Initialize ContextAlreadySetError.

        Args:
            execution_id: The execution ID that is already set
            message: Error message
        """
        super().__init__(f"{message}: {execution_id}")
        self.execution_id = execution_id
        self.message = message


class ContextValidationError(ExecutionContextError):
    """Raised when context data fails validation."""

    def __init__(self, field: str, value, message: str = "Invalid context value"):
        """
        Initialize ContextValidationError.

        Args:
            field: The field that failed validation
            value: The invalid value
            message: Error message
        """
        super().__init__(f"{message} for field '{field}': {value}")
        self.field = field
        self.value = value
        self.message = message
