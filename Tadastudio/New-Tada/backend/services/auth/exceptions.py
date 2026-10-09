"""Custom exceptions for authentication operations.

This module defines custom exception classes for various authentication
and authorization error scenarios, providing better error handling and
HTTP status code mapping.

Example:
    >>> from backend.services.auth.exceptions import InvalidTokenError
    >>> raise InvalidTokenError("Token has expired")
"""

from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """Base exception for authentication errors.

    This exception and its subclasses automatically set appropriate
    HTTP status codes and error messages for authentication failures.

    Attributes:
        status_code: HTTP status code (default: 401 Unauthorized)
        detail: Error message detail
    """

    def __init__(
        self,
        detail: str = "Authentication failed",
        status_code: int = status.HTTP_401_UNAUTHORIZED,
    ) -> None:
        """Initialize authentication error.

        Args:
            detail: Error message detail
            status_code: HTTP status code (default: 401)

        Example:
            >>> raise AuthenticationError("Invalid credentials")
        """
        super().__init__(status_code=status_code, detail=detail)


class InvalidTokenError(AuthenticationError):
    """Exception raised when a token is invalid or expired.

    This exception is raised when JWT validation fails, token signature
    is invalid, or token has expired.

    Example:
        >>> raise InvalidTokenError("Token has expired")
    """

    def __init__(self, detail: str = "Invalid or expired token") -> None:
        """Initialize invalid token error.

        Args:
            detail: Error message detail

        Example:
            >>> raise InvalidTokenError()
        """
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class MissingTokenError(AuthenticationError):
    """Exception raised when authentication token is missing.

    This exception is raised when a protected endpoint is accessed
    without providing a required authentication token.

    Example:
        >>> raise MissingTokenError()
    """

    def __init__(self, detail: str = "Missing bearer token") -> None:
        """Initialize missing token error.

        Args:
            detail: Error message detail

        Example:
            >>> raise MissingTokenError("No authorization header provided")
        """
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class InvalidCredentialsError(AuthenticationError):
    """Exception raised when user credentials are invalid.

    This exception is raised when username/password authentication
    fails due to incorrect credentials.

    Example:
        >>> raise InvalidCredentialsError()
    """

    def __init__(self, detail: str = "Invalid email or password") -> None:
        """Initialize invalid credentials error.

        Args:
            detail: Error message detail

        Example:
            >>> raise InvalidCredentialsError("User not found")
        """
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class MissingEmailClaimError(AuthenticationError):
    """Exception raised when token is missing required email claim.

    This exception is raised when a JWT token doesn't contain the
    required email claim for user identification.

    Example:
        >>> raise MissingEmailClaimError()
    """

    def __init__(self, detail: str = "Token missing email claim") -> None:
        """Initialize missing email claim error.

        Args:
            detail: Error message detail

        Example:
            >>> raise MissingEmailClaimError()
        """
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class OAuth2ConfigurationError(HTTPException):
    """Exception raised when OAuth2 configuration is invalid.

    This exception is raised when OAuth2 proxy authentication is
    enabled but required configuration (JWKS URL, tenant ID, etc.)
    is missing or invalid.

    Example:
        >>> raise OAuth2ConfigurationError("AZURE_TENANT_ID not set")
    """

    def __init__(self, detail: str = "OAuth authentication is not configured") -> None:
        """Initialize OAuth2 configuration error.

        Args:
            detail: Error message detail

        Example:
            >>> raise OAuth2ConfigurationError("Missing AZURE_TENANT_ID")
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class RequestContextUnavailableError(HTTPException):
    """Exception raised when request context is required but unavailable.

    This exception is raised when authentication requires access to
    the HTTP request object but it's not available in the current context.

    Example:
        >>> raise RequestContextUnavailableError()
    """

    def __init__(self, detail: str = "Request context unavailable") -> None:
        """Initialize request context unavailable error.

        Args:
            detail: Error message detail

        Example:
            >>> raise RequestContextUnavailableError()
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class UserSyncError(Exception):
    """Exception raised when user database synchronization fails.

    This is a non-HTTP exception used internally to handle user
    persistence failures. It does not automatically return an HTTP error.

    Example:
        >>> raise UserSyncError("Database connection failed")
    """

    def __init__(self, message: str, user_id: str = None) -> None:
        """Initialize user sync error.

        Args:
            message: Error message
            user_id: Optional user ID that failed to sync

        Example:
            >>> raise UserSyncError("Failed to save user", user_id="user123")
        """
        self.user_id = user_id
        super().__init__(message)


class DisabledFeatureError(HTTPException):
    """Exception raised when a feature is disabled for current auth mode.

    This exception is raised when attempting to use a feature that's
    only available in a different authentication mode (e.g., password
    login when in OAuth mode).

    Example:
        >>> raise DisabledFeatureError("Password login is disabled")
    """

    def __init__(
        self, detail: str = "This feature is disabled for current deployment"
    ) -> None:
        """Initialize disabled feature error.

        Args:
            detail: Error message detail

        Example:
            >>> raise DisabledFeatureError("Registration disabled in OAuth mode")
        """
        super().__init__(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail=detail)
