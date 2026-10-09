"""
Custom exceptions for state execution tracking.

This module defines exception classes for various error conditions
that can occur during state tracking operations.
"""


class StateTrackingError(Exception):
    """Base exception for all state tracking errors."""

    def __init__(self, message: str, state_snapshot: dict = None):
        """
        Initialize state tracking error.

        Args:
            message: Error message
            state_snapshot: Optional snapshot of the state when error occurred
        """
        super().__init__(message)
        self.message = message
        self.state_snapshot = state_snapshot


class InvalidExecutionOrderError(StateTrackingError):
    """Raised when an invalid execution order value is encountered."""

    def __init__(self, order: int, reason: str = None):
        """
        Initialize invalid execution order error.

        Args:
            order: The invalid execution order value
            reason: Optional explanation of why the order is invalid
        """
        message = f"Invalid execution order: {order}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)
        self.order = order
        self.reason = reason


class MissingStateKeyError(StateTrackingError):
    """Raised when a required state key is missing."""

    def __init__(self, key: str, context: str = None):
        """
        Initialize missing state key error.

        Args:
            key: The missing state key
            context: Optional context about where the key was expected
        """
        message = f"Missing required state key: '{key}'"
        if context:
            message += f" ({context})"
        super().__init__(message)
        self.key = key
        self.context = context


class InvalidStateStructureError(StateTrackingError):
    """Raised when the state structure is invalid or corrupted."""

    def __init__(self, expected: str, actual: str = None):
        """
        Initialize invalid state structure error.

        Args:
            expected: Description of expected state structure
            actual: Description of actual state structure
        """
        message = f"Invalid state structure. Expected: {expected}"
        if actual:
            message += f", Got: {actual}"
        super().__init__(message)
        self.expected = expected
        self.actual = actual


class StateUpdateError(StateTrackingError):
    """Raised when a state update operation fails."""

    def __init__(self, operation: str, reason: str = None):
        """
        Initialize state update error.

        Args:
            operation: The update operation that failed
            reason: Optional reason for the failure
        """
        message = f"State update failed: {operation}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)
        self.operation = operation
        self.reason = reason
