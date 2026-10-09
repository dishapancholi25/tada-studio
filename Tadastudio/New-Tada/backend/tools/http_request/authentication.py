"""Authentication handlers for HTTP request tool."""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Dict

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from .schemas import AuthConfig, OAuth2Config, RequestSigningConfig


logger = logging.getLogger(__name__)


def apply_bearer_auth(headers: Dict[str, str], token: str) -> Dict[str, str]:
    """Apply Bearer token authentication.

    Args:
        headers: Request headers
        token: Bearer token

    Returns:
        Updated headers with Authorization
    """
    headers["Authorization"] = f"Bearer {token}"
    return headers


def apply_custom_token_auth(
    headers: Dict[str, str], scheme: str, token: str
) -> Dict[str, str]:
    """Apply custom token authentication.

    Args:
        headers: Request headers
        scheme: Token scheme (e.g., "Token", "ApiKey")
        token: Token value

    Returns:
        Updated headers with Authorization
    """
    headers["Authorization"] = f"{scheme} {token}"
    return headers


def apply_api_key_header(
    headers: Dict[str, str], key: str, header_name: str
) -> Dict[str, str]:
    """Apply API key in header.

    Args:
        headers: Request headers
        key: API key
        header_name: Header name for the key

    Returns:
        Updated headers with API key
    """
    headers[header_name] = key
    return headers


def apply_api_key_query(url: str, key: str, param_name: str) -> str:
    """Apply API key as query parameter.

    Args:
        url: Request URL
        key: API key
        param_name: Parameter name

    Returns:
        Updated URL with API key parameter
    """
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{param_name}={key}"


def create_basic_auth(username: str, password: str) -> HTTPBasicAuth:
    """Create HTTP Basic authentication.

    Args:
        username: Username
        password: Password

    Returns:
        HTTPBasicAuth instance
    """
    return HTTPBasicAuth(username, password)


def create_digest_auth(username: str, password: str) -> HTTPDigestAuth:
    """Create HTTP Digest authentication.

    Args:
        username: Username
        password: Password

    Returns:
        HTTPDigestAuth instance
    """
    return HTTPDigestAuth(username, password)


def handle_oauth2_flow(oauth2_config: OAuth2Config) -> str:
    """Handle OAuth2 client credentials flow.

    Args:
        oauth2_config: OAuth2 configuration

    Returns:
        Access token

    Raises:
        ValueError: If token acquisition fails
    """
    from .handlers import _ssrf_validate_before_send  # local import avoids circular import

    block_reason = _ssrf_validate_before_send(oauth2_config.token_url)
    if block_reason:
        raise ValueError(f"OAuth2 token acquisition blocked: {block_reason}")

    verify = getattr(oauth2_config, "verify_ssl", True)
    token_response = requests.post(
        oauth2_config.token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": oauth2_config.client_id,
            "client_secret": oauth2_config.client_secret,
            "scope": oauth2_config.scope,
        },
        verify=verify,
    )

    if token_response.status_code == 200:
        return token_response.json().get("access_token")
    else:
        raise ValueError(f"OAuth2 token acquisition failed: {token_response.text}")


def sign_request_hmac_sha256(
    method: str, url: str, body: str, secret: str, header_name: str
) -> str:
    """Sign request using HMAC-SHA256.

    Args:
        method: HTTP method
        url: Request URL
        body: Request body
        secret: Secret key
        header_name: Header name for signature

    Returns:
        Signature string
    """
    message = f"{method.upper()}\n{url}\n{body}"
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return signature


def sign_request(
    method: str,
    url: str,
    headers: Dict[str, str],
    body: str,
    signing_config: RequestSigningConfig,
) -> Dict[str, str]:
    """Sign the request based on the algorithm specified.

    Args:
        method: HTTP method
        url: Request URL
        headers: Request headers
        body: Request body
        signing_config: Signing configuration

    Returns:
        Updated headers with signature
    """
    algorithm = signing_config.algorithm.lower()

    if algorithm == "hmac-sha256":
        signature = sign_request_hmac_sha256(
            method,
            url,
            body,
            signing_config.secret,
            signing_config.header_name,
        )
        headers[signing_config.header_name] = signature

    elif algorithm == "aws-v4":
        # Simplified AWS Signature V4 (placeholder)
        headers["X-Amz-Date"] = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        logger.warning("AWS V4 signing not fully implemented")

    elif algorithm == "custom":
        # Custom signing would need a safe execution environment
        logger.warning("Custom signing scripts not implemented for security")

    return headers


class AuthenticationHandler:
    """Handler for all authentication methods using dispatcher pattern."""

    def __init__(
        self,
        auth_config: AuthConfig,
        oauth2_config: OAuth2Config = None,
        signing_config: RequestSigningConfig = None,
    ):
        """Initialize authentication handler."""
        self.auth_config = auth_config
        self.oauth2_config = oauth2_config
        self.signing_config = signing_config

        # Dispatcher mapping auth types to handler methods
        self._auth_handlers = {
            "bearer": self._apply_bearer_auth,
            "custom_token": self._apply_custom_token_auth,
            "api_key_header": self._apply_api_key_header_auth,
            "api_key_query": self._apply_api_key_query_auth,
            "basic": self._apply_basic_auth,
            "digest": self._apply_digest_auth,
            "oauth2": self._apply_oauth2_auth,
        }

    def _apply_bearer_auth(
        self, url: str, headers: Dict[str, str], body: str
    ) -> tuple[str, Dict[str, str], any]:
        """Apply Bearer token authentication."""
        if self.auth_config.token:
            headers = apply_bearer_auth(headers, self.auth_config.token)
        return url, headers, None

    def _apply_custom_token_auth(
        self, url: str, headers: Dict[str, str], body: str
    ) -> tuple[str, Dict[str, str], any]:
        """Apply custom token scheme authentication."""
        if self.auth_config.scheme and self.auth_config.token:
            headers = apply_custom_token_auth(
                headers, self.auth_config.scheme, self.auth_config.token
            )
        return url, headers, None

    def _apply_api_key_header_auth(
        self, url: str, headers: Dict[str, str], body: str
    ) -> tuple[str, Dict[str, str], any]:
        """Apply API key in header authentication."""
        if self.auth_config.key and self.auth_config.header_name:
            headers = apply_api_key_header(
                headers, self.auth_config.key, self.auth_config.header_name
            )
        return url, headers, None

    def _apply_api_key_query_auth(
        self, url: str, headers: Dict[str, str], body: str
    ) -> tuple[str, Dict[str, str], any]:
        """Apply API key in query parameter authentication."""
        if self.auth_config.key and self.auth_config.param_name:
            url = apply_api_key_query(
                url, self.auth_config.key, self.auth_config.param_name
            )
        return url, headers, None

    def _apply_basic_auth(
        self, url: str, headers: Dict[str, str], body: str
    ) -> tuple[str, Dict[str, str], any]:
        """Apply HTTP Basic authentication."""
        auth = None
        if self.auth_config.username and self.auth_config.password:
            auth = create_basic_auth(
                self.auth_config.username, self.auth_config.password
            )
        return url, headers, auth

    def _apply_digest_auth(
        self, url: str, headers: Dict[str, str], body: str
    ) -> tuple[str, Dict[str, str], any]:
        """Apply HTTP Digest authentication."""
        auth = None
        if self.auth_config.username and self.auth_config.password:
            auth = create_digest_auth(
                self.auth_config.username, self.auth_config.password
            )
        return url, headers, auth

    def _apply_oauth2_auth(
        self, url: str, headers: Dict[str, str], body: str
    ) -> tuple[str, Dict[str, str], any]:
        """Apply OAuth2 authentication."""
        if self.oauth2_config:
            try:
                token = handle_oauth2_flow(self.oauth2_config)
                headers = apply_bearer_auth(headers, token)
            except ValueError as e:
                raise ValueError(f"Error: {str(e)}")
        return url, headers, None

    def apply_authentication(
        self, url: str, headers: Dict[str, str], body: str = ""
    ) -> tuple[str, Dict[str, str], any]:
        """Apply authentication to the request using dispatcher pattern.

        Args:
            url: Request URL
            headers: Request headers
            body: Request body

        Returns:
            Tuple of (updated_url, updated_headers, auth_object)
        """
        auth = None
        auth_type = self.auth_config.auth_type

        # Dispatch to appropriate handler
        handler = self._auth_handlers.get(auth_type)
        if handler:
            url, headers, auth = handler(url, headers, body)

        # Apply request signing if configured
        if self.signing_config:
            headers = sign_request(
                "POST" if body else "GET",
                url,
                headers,
                body,
                self.signing_config,
            )

        return url, headers, auth
