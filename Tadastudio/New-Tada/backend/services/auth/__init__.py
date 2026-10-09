"""Authentication service layer.

This package provides OAuth2 proxy authentication services, including
user synchronization and token handling.

Modules:
    config: Authentication configuration and constants
    exceptions: Custom authentication exceptions
    jwt_utils: JWT token decoding utilities
    token_extractor: Token extraction from requests
    user_sync: User database synchronization
    providers: OAuth2 proxy authentication implementation

Example:
    >>> from backend.services.auth import get_oauth_proxy_auth
    >>> oauth_auth = get_oauth_proxy_auth()
"""

from .config import AuthConfig, get_auth_config
from .exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    MissingEmailClaimError,
    MissingTokenError,
    OAuth2ConfigurationError,
    RequestContextUnavailableError,
    UserSyncError,
)
from .providers import OAuth2ProxyAuth, get_oauth_proxy_auth
from .token_extractor import extract_token_from_request, log_auth_headers
from .user_sync import enrich_claims, sync_user_from_claims


__all__ = [
    # Configuration
    "AuthConfig",
    "get_auth_config",
    # Exceptions
    "AuthenticationError",
    "InvalidTokenError",
    "MissingTokenError",
    "InvalidCredentialsError",
    "MissingEmailClaimError",
    "OAuth2ConfigurationError",
    "RequestContextUnavailableError",
    "UserSyncError",
    # Token extraction
    "extract_token_from_request",
    "log_auth_headers",
    # User sync
    "sync_user_from_claims",
    "enrich_claims",
    # Providers
    "OAuth2ProxyAuth",
    "get_oauth_proxy_auth",
]
