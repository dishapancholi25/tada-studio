"""Tests for trusted proxy identity-header enforcement."""

from unittest.mock import patch

import pytest
from fastapi import Request

from backend.api.auth import dependencies
from backend.services.auth.exceptions import MissingTokenError
from backend.services.auth.token_extractor import is_trusted_oauth_proxy_request


def _build_request(headers: dict[str, str]) -> Request:
    """Create a minimal HTTP request object for auth dependency tests."""
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/auth/me",
            "raw_path": b"/api/auth/me",
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 8000),
            "headers": [
                (name.lower().encode("latin-1"), value.encode("latin-1"))
                for name, value in headers.items()
            ],
        }
    )


def test_is_trusted_oauth_proxy_request_true(monkeypatch):
    """Request is trusted when shared-secret header matches."""
    from backend.services.auth.config import get_auth_config

    config = get_auth_config()
    monkeypatch.setattr(config, "proxy_auth_shared_secret", "super-secret-value")
    monkeypatch.setattr(config, "proxy_auth_secret_header", "X-Auth-Proxy-Secret")

    request = _build_request({"X-Auth-Proxy-Secret": "super-secret-value"})
    assert is_trusted_oauth_proxy_request(request) is True


def test_is_trusted_oauth_proxy_request_true_when_secret_not_configured(monkeypatch):
    """Request is trusted (backward-compat) when backend secret is not configured."""
    from backend.services.auth import token_extractor
    from backend.services.auth.config import get_auth_config

    config = get_auth_config()
    monkeypatch.setattr(config, "proxy_auth_shared_secret", "")
    monkeypatch.setattr(config, "proxy_auth_secret_header", "X-Auth-Proxy-Secret")
    monkeypatch.setattr(token_extractor, "_proxy_secret_missing_warned", False)

    request = _build_request({"X-Auth-Proxy-Secret": "anything"})
    # Without secret configured, headers are trusted for backward compatibility
    assert is_trusted_oauth_proxy_request(request) is True


def test_is_trusted_oauth_proxy_request_rejects_wrong_secret(monkeypatch):
    """Request is NOT trusted when secret IS configured but header doesn't match."""
    from backend.services.auth.config import get_auth_config

    config = get_auth_config()
    monkeypatch.setattr(config, "proxy_auth_shared_secret", "correct-secret")
    monkeypatch.setattr(config, "proxy_auth_secret_header", "X-Auth-Proxy-Secret")

    request = _build_request({"X-Auth-Proxy-Secret": "wrong-secret"})
    assert is_trusted_oauth_proxy_request(request) is False


@pytest.mark.asyncio
async def test_get_current_user_rejects_untrusted_identity_headers():
    """Untrusted X-Auth-Request-Email is ignored instead of authenticating."""
    request = _build_request({"X-Auth-Request-Email": "attacker@example.com"})

    with patch(
        "backend.api.auth.dependencies.is_trusted_oauth_proxy_request",
        return_value=False,
    ), patch(
        "backend.api.auth.dependencies.extract_token_from_request", return_value=None
    ):
        with pytest.raises(MissingTokenError):
            await dependencies.get_current_user(credentials=None, request=request)


@pytest.mark.asyncio
async def test_get_current_user_accepts_trusted_identity_headers():
    """Trusted proxy headers continue to use header-based auth flow."""
    request = _build_request({"X-Auth-Request-Email": "trusted@example.com"})
    expected_claims = {"email": "trusted@example.com", "sub": "trusted@example.com"}

    with patch(
        "backend.api.auth.dependencies.is_trusted_oauth_proxy_request",
        return_value=True,
    ), patch(
        "backend.api.auth.dependencies.extract_token_from_request", return_value=None
    ), patch(
        "backend.api.auth.dependencies._authenticate_oauth_proxy_with_headers",
        return_value=expected_claims,
    ):
        claims = await dependencies.get_current_user(credentials=None, request=request)

    assert claims == expected_claims
