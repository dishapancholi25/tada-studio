"""
Custom exceptions for dependency injection.

This module provides specialized exceptions for dependency-related errors,
making it easier to handle and debug initialization and access issues.
"""


class DependencyError(Exception):
    """Base exception for dependency-related errors."""

    pass


class DependencyNotInitializedError(DependencyError):
    """
    Raised when accessing a dependency that hasn't been initialized.

    Attributes:
        dependency_name: Name of the dependency that wasn't initialized
    """

    def __init__(self, dependency_name: str):
        """
        Initialize the exception.

        Args:
            dependency_name: Name of the uninitialized dependency
        """
        self.dependency_name = dependency_name
        super().__init__(
            f"{dependency_name} not initialized. Call initialize_dependencies() first."
        )


class InitializationError(DependencyError):
    """
    Raised when dependency initialization fails.

    This exception wraps the underlying error that occurred during initialization.
    """

    pass
