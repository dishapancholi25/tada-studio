"""Authentication configuration and constants.

This module centralizes all OAuth2 proxy authentication configuration,
including JWT settings and Azure AD settings.

Environment Variables:
    OAUTH_PROXY_DISABLE_JWT_VALIDATION: Disable JWT signature validation. Default: "false"
    AUTH_PROXY_SHARED_SECRET: Shared secret that must be forwarded by trusted proxy
    AUTH_PROXY_SHARED_SECRET_HEADER: Header name that carries AUTH_PROXY_SHARED_SECRET
    JWT_SECRET: Secret key for JWT token signing. Default: "your-secret-key-change-in-production"
    JWT_ALGORITHM: JWT algorithm. Default: "HS256"
    JWT_EXPIRATION_HOURS: JWT token expiration in hours. Default: 24
    AZURE_TENANT_ID: Azure AD tenant ID (required for OAuth proxy with JWT validation)
    AZURE_CLIENT_ID: Azure AD client ID
    AZURE_ALLOWED_AUDIENCES: Comma-separated list of allowed JWT audiences
    AZURE_AUTHORITY: Azure AD authority URL. Default: "https://login.microsoftonline.com"
    AZURE_JWKS_URL: Override JWKS URL for other identity providers
    ADMIN_GROUP: Single group name for admin access (e.g., "admins")
    ADMIN_USERS: Comma-separated list of admin user emails

Example:
    >>> from backend.services.auth.config import AuthConfig
    >>> config = AuthConfig()
    >>> print(f"JWKS URL: {config.azure_jwks_url}")
"""

import os
from typing import Optional, Set

# Well-known name for the database-backed Administrators group.
# This group is auto-seeded on startup and provides admin RBAC
# permissions alongside the ADMIN_USERS / ADMIN_GROUP env vars.
ADMINISTRATORS_GROUP_NAME = "Administrators"


class AuthConfig:
    """Authentication configuration container.

    This class encapsulates all OAuth2 proxy authentication configuration settings,
    providing a centralized access point for auth-related constants.

    Attributes:
        oauth_proxy_disable_jwt_validation: Whether JWT validation is disabled
        jwt_secret: Secret key for JWT signing
        jwt_algorithm: JWT signing algorithm
        jwt_expiration_hours: JWT token expiration time in hours
        azure_tenant_id: Azure AD tenant ID
        azure_client_id: Azure AD client ID
        allowed_audiences: Set of allowed JWT audiences
        azure_authority: Azure AD authority URL
        azure_jwks_url: JWKS URL for token validation
        expected_issuer: Expected JWT issuer
        admin_group: Single group name for admin access
        admin_users: Set of admin user emails
    """

    def __init__(self) -> None:
        """Initialize authentication configuration from environment variables."""
        # OAuth2 Proxy settings
        self.oauth_proxy_disable_jwt_validation = os.getenv(
            "OAUTH_PROXY_DISABLE_JWT_VALIDATION", "false"
        ).lower() in {"1", "true", "yes"}
        self.proxy_auth_shared_secret: Optional[str] = os.getenv(
            "AUTH_PROXY_SHARED_SECRET"
        )
        self.proxy_auth_secret_header = os.getenv(
            "AUTH_PROXY_SHARED_SECRET_HEADER", "X-Auth-Proxy-Secret"
        ).strip() or "X-Auth-Proxy-Secret"

        # JWT settings
        self.jwt_secret = os.getenv(
            "JWT_SECRET", "your-secret-key-change-in-production"
        )
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24

        # Azure AD / OAuth2 Proxy settings
        self.azure_tenant_id: Optional[str] = os.getenv("AZURE_TENANT_ID")
        self.azure_client_id: Optional[str] = os.getenv("AZURE_CLIENT_ID")

        # Build allowed audiences set
        self.allowed_audiences: Set[str] = {
            aud.strip()
            for aud in os.getenv("AZURE_ALLOWED_AUDIENCES", "").split(",")
            if aud.strip()
        }
        # Azure authority and JWKS URL
        self.azure_authority = os.getenv(
            "AZURE_AUTHORITY", "https://login.microsoftonline.com"
        ).rstrip("/")

        # Calculate issuer and JWKS URL
        if self.azure_tenant_id:
            v2_issuer = f"{self.azure_authority}/{self.azure_tenant_id}/v2.0"
            # v1.0 issuer used by managed identities / service principals
            v1_issuer = f"https://sts.windows.net/{self.azure_tenant_id}/"
            self.expected_issuer = v2_issuer
            self.expected_issuers: Set[str] = {v2_issuer, v1_issuer}
            self.azure_jwks_url = (
                f"{self.azure_authority}/{self.azure_tenant_id}/discovery/v2.0/keys"
            )
        else:
            self.expected_issuer = None
            self.expected_issuers = set()
            self.azure_jwks_url = os.getenv("AZURE_JWKS_URL")

        # RBAC settings
        self.admin_group: Optional[str] = os.getenv("ADMIN_GROUP")
        self.admin_users: Set[str] = {
            user.strip().lower()
            for user in os.getenv("ADMIN_USERS", "").split(",")
            if user.strip()
        }

    def validate_oauth_config(self) -> None:
        """Validate OAuth2 proxy configuration.

        Raises:
            ValueError: If JWT validation is enabled but required config is missing

        Example:
            >>> config = AuthConfig()
            >>> config.validate_oauth_config()
        """
        if not self.oauth_proxy_disable_jwt_validation and not self.azure_jwks_url:
            raise ValueError(
                "OAuth proxy with JWT validation requires AZURE_TENANT_ID "
                "or AZURE_JWKS_URL to be set"
            )


# Global configuration instance
auth_config = AuthConfig()


def get_auth_config() -> AuthConfig:
    """Get the global authentication configuration instance.

    Returns:
        AuthConfig: The global auth configuration

    Example:
        >>> from backend.services.auth.config import get_auth_config
        >>> config = get_auth_config()
        >>> print(f"JWT validation disabled: {config.oauth_proxy_disable_jwt_validation}")
    """
    return auth_config
