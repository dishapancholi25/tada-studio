"""Authentication providers.

This package contains OAuth2 proxy authentication for Azure AD/OIDC.

Example:
    >>> from backend.services.auth.providers import get_oauth_proxy_auth
    >>> oauth_auth = get_oauth_proxy_auth()
"""

from .oauth2_proxy import OAuth2ProxyAuth, get_oauth_proxy_auth


__all__ = [
    "OAuth2ProxyAuth",
    "get_oauth_proxy_auth",
]
