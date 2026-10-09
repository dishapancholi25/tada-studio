"""OAuth2 Proxy authentication provider.

This module implements authentication for applications behind oauth2-proxy,
validating access tokens forwarded by the proxy and syncing users to the database.

Example:
    >>> from backend.services.auth.providers.oauth2_proxy import OAuth2ProxyAuth
    >>> from fastapi import Request
    >>> auth = OAuth2ProxyAuth()
    >>> claims = auth.verify_and_sync(token, request)
    >>> print(f"Authenticated user: {claims['email']}")
"""

import logging
from typing import Any, Dict, Optional

import jwt
from fastapi import Request
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError

from ..config import get_auth_config
from ..exceptions import InvalidTokenError, OAuth2ConfigurationError
from ..token_extractor import is_trusted_oauth_proxy_request
from ..user_sync import enrich_claims, sync_user_from_claims


logger = logging.getLogger(__name__)


class OAuth2ProxyAuth:
    """Validate access tokens forwarded by oauth2-proxy and persist users.

    This class handles JWT token validation for applications deployed behind
    oauth2-proxy. It supports both Azure AD tokens and generic OIDC tokens,
    with configurable JWT validation and user synchronization.

    Attributes:
        config: Authentication configuration
        jwks_client: Optional PyJWKClient for JWT signature verification

    Example:
        >>> auth = OAuth2ProxyAuth()
        >>> claims = auth.verify_and_sync(access_token, request)
        >>> print(f"User: {claims['email']}")
    """

    def __init__(self) -> None:
        """Initialize OAuth2 proxy authentication.

        Raises:
            ValueError: If JWT validation is enabled but JWKS URL is not configured
        """
        self.config = get_auth_config()
        self._jwks_client: Optional[PyJWKClient] = None

        if not self.config.oauth_proxy_disable_jwt_validation:
            if not self.config.azure_jwks_url:
                logger.error(
                    "[AUTH-OAUTH] JWT validation is enabled but JWKS URL is not configured. "
                    "Set AZURE_TENANT_ID or AZURE_JWKS_URL."
                )
            else:
                self._jwks_client = PyJWKClient(self.config.azure_jwks_url)
                logger.info(
                    f"[AUTH-OAUTH] Initialized with JWKS URL: {self.config.azure_jwks_url}"
                )

    def _decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token.

        This method validates the token signature, audience, issuer, and
        expiration based on configuration settings.

        Args:
            token: JWT access token string

        Returns:
            Dict[str, Any]: Decoded token claims

        Raises:
            InvalidTokenError: If token validation fails
            OAuth2ConfigurationError: If JWT validation is required but not configured

        Example:
            >>> auth = OAuth2ProxyAuth()
            >>> claims = auth._decode_token(token)
        """
        if self.config.oauth_proxy_disable_jwt_validation:
            logger.warning(
                "[AUTH-OAUTH] JWT signature validation disabled via configuration"
            )
            return jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_iss": False,
                    "verify_exp": True,
                },
            )

        if not self._jwks_client:
            raise OAuth2ConfigurationError(
                "OAuth token validation is not configured on the API"
            )

        if token.count(".") != 2:
            logger.error(
                "[AUTH-OAUTH] Token does not appear to be a JWT (expected 3 segments)"
            )
            raise InvalidTokenError("Bearer token is not a valid JWT")

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
        except Exception as exc:
            logger.error(f"[AUTH-OAUTH] Failed to get signing key: {exc}")
            raise InvalidTokenError("Failed to retrieve token signing key") from exc

        decode_options: Dict[str, Any] = {"require": ["exp", "iat", "sub"]}
        decode_kwargs: Dict[str, Any] = {
            "algorithms": ["RS256"],
            "options": decode_options,
        }

        # Add audience validation if configured
        if self.config.allowed_audiences:
            audiences = list(self.config.allowed_audiences)
            decode_kwargs["audience"] = (
                audiences[0] if len(audiences) == 1 else audiences
            )
        else:
            decode_options["verify_aud"] = False

        # Skip PyJWT issuer validation when multiple issuers are allowed;
        # we validate manually below to support both v1.0 (STS) and v2.0 issuers.
        if self.config.expected_issuers:
            decode_options["verify_iss"] = False
        elif self.config.expected_issuer:
            decode_kwargs["issuer"] = self.config.expected_issuer

        try:
            claims = jwt.decode(token, signing_key.key, **decode_kwargs)
        except PyJWTError as exc:
            # Decode without verification to surface the actual aud/iss for diagnostics
            try:
                unverified = jwt.decode(
                    token,
                    options={
                        "verify_signature": False,
                        "verify_aud": False,
                        "verify_exp": False,
                    },
                    algorithms=["RS256"],
                )
                logger.error(
                    "[AUTH-OAUTH] Token validation failed: %s — token aud=%s iss=%s, "
                    "configured audiences=%s",
                    exc,
                    unverified.get("aud"),
                    unverified.get("iss"),
                    self.config.allowed_audiences,
                )
            except Exception:
                logger.error(f"[AUTH-OAUTH] Token validation failed: {exc}")
            raise InvalidTokenError("Token validation failed") from exc

        # Manual issuer check against the allowed set (v1.0 + v2.0)
        if self.config.expected_issuers:
            token_issuer = claims.get("iss", "")
            if token_issuer not in self.config.expected_issuers:
                logger.error(
                    "[AUTH-OAUTH] Token issuer '%s' not in allowed issuers %s",
                    token_issuer,
                    self.config.expected_issuers,
                )
                raise InvalidTokenError(f"Invalid token issuer: {token_issuer}")

        return claims

    def verify_and_sync(self, token: str, request: Request) -> Dict[str, Any]:
        """Validate the token, hydrate claims, and persist the user.

        This is the main entry point for OAuth2 proxy authentication. It:
        1. Decodes and validates the JWT token
        2. Enriches claims with additional information from headers
        3. Syncs the user to the database
        4. Returns the complete claims dictionary

        Args:
            token: JWT access token from oauth2-proxy
            request: FastAPI Request object

        Returns:
            Dict[str, Any]: Complete user claims dictionary

        Raises:
            InvalidTokenError: If token validation fails

        Example:
            >>> from fastapi import Request
            >>> auth = OAuth2ProxyAuth()
            >>> token = request.headers.get("X-Auth-Request-Access-Token")
            >>> claims = auth.verify_and_sync(token, request)
            >>> print(f"Authenticated: {claims['email']}")
        """
        try:
            payload = self._decode_token(token)
        except PyJWTError as exc:
            logger.error(f"[AUTH-OAUTH] Token validation error: {exc}")
            raise InvalidTokenError("Invalid bearer token") from exc

        # Only accept header-based email fallback from authenticated trusted proxy.
        header_email = None
        if is_trusted_oauth_proxy_request(request):
            header_email = request.headers.get("X-Auth-Request-Email")

        # Start with token payload
        claims = dict(payload)

        # Enrich claims with additional information
        claims = enrich_claims(
            claims, header_email=header_email, auth_source="azure_ad"
        )

        logger.debug(
            "[AUTH-OAUTH] OAuth proxy claims received - sub=%s, email=%s, aud=%s, issuer=%s",
            claims.get("sub"),
            claims.get("email"),
            claims.get("aud"),
            claims.get("iss"),
        )

        # Sync user to database
        sync_user_from_claims(claims)

        return claims


# Global singleton instance
_oauth_proxy_auth: Optional[OAuth2ProxyAuth] = None


def get_oauth_proxy_auth() -> OAuth2ProxyAuth:
    """Get or create the global OAuth2ProxyAuth instance.

    This function returns the singleton OAuth2ProxyAuth instance,
    creating it if necessary.

    Returns:
        OAuth2ProxyAuth: OAuth2ProxyAuth instance

    Example:
        >>> from backend.services.auth.providers.oauth2_proxy import get_oauth_proxy_auth
        >>> auth = get_oauth_proxy_auth()
        >>> claims = auth.verify_and_sync(token, request)
    """
    global _oauth_proxy_auth

    if _oauth_proxy_auth is None:
        _oauth_proxy_auth = OAuth2ProxyAuth()
        logger.info("[AUTH-OAUTH] OAuth2ProxyAuth initialized")

    return _oauth_proxy_auth
