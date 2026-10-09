"""Tests for WebSocket authentication identity resolution.

The WebSocket and HTTP auth paths must agree on the ``sub`` claim. Handlers
persist ``get_user_identifier(current_user)`` (i.e. ``claims["sub"]``) as the
owner of a record, ``require_execution_access`` compares the connecting user
against it, and ``is_user_admin`` looks the role up in the database keyed on
the same value. When oauth2-proxy proxies straight to the backend the HTTP path
resolves ``sub`` from the bearer token, while header identity would resolve it
to the email -- so the token must win.
"""

from unittest.mock import patch

import pytest
from starlette.websockets import WebSocket

from backend.api.auth import dependencies


def _build_websocket(headers: dict[str, str]) -> WebSocket:
    """Create a minimal WebSocket object for auth dependency tests."""

    async def _receive():  # pragma: no cover - never awaited in these tests
        return {"type": "websocket.connect"}

    async def _send(_message):  # pragma: no cover - never awaited in these tests
        return None

    return WebSocket(
        {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "scheme": "ws",
            "path": "/api/ws/execution/exec_1",
            "raw_path": b"/api/ws/execution/exec_1",
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 8000),
            "headers": [
                (name.lower().encode("latin-1"), value.encode("latin-1"))
                for name, value in headers.items()
            ],
        },
        _receive,
        _send,
    )


@pytest.fixture(autouse=True)
def _disable_skip_auth(monkeypatch):
    """Ensure the dev-mode bypass never masks the production code path."""
    monkeypatch.setenv("SKIP_AUTH", "false")


@pytest.fixture(autouse=True)
def _no_ambient_proxy_secret(monkeypatch):
    """Pin the proxy shared secret off so ambient .env values cannot leak in.

    Tests that exercise the trust check set the secret explicitly.
    """
    from backend.services.auth.config import auth_config

    monkeypatch.setattr(auth_config, "proxy_auth_shared_secret", None)


@pytest.mark.asyncio
async def test_token_sub_wins_over_header_email():
    """Token claims are used even when identity headers are also present.

    Regression: header identity set sub=email while the HTTP path recorded the
    Azure AD subject, so every execution WebSocket was closed with 4003.
    """
    websocket = _build_websocket(
        {
            "Authorization": "Bearer header.payload.signature",
            "X-Forwarded-Email": "user@example.com",
        }
    )
    token_claims = {"sub": "azure-oid-123", "email": "user@example.com"}

    with (
        patch(
            "backend.api.auth.dependencies._authenticate_oauth_proxy_with_token",
            return_value=token_claims,
        ),
        patch("backend.services.auth.rbac.is_user_admin", return_value=False),
    ):
        claims = await dependencies.get_current_user_ws(websocket)

    assert claims is not None
    assert claims["sub"] == "azure-oid-123"
    assert claims["auth_source"] == "websocket_token"


@pytest.mark.asyncio
async def test_admin_flag_resolved_from_database():
    """is_admin is populated so admins are not blocked by ownership checks."""
    websocket = _build_websocket({"Authorization": "Bearer header.payload.signature"})
    token_claims = {"sub": "azure-oid-123", "email": "admin@example.com"}

    with (
        patch(
            "backend.api.auth.dependencies._authenticate_oauth_proxy_with_token",
            return_value=token_claims,
        ),
        patch(
            "backend.services.auth.rbac.is_user_admin", return_value=True
        ) as mock_is_admin,
    ):
        claims = await dependencies.get_current_user_ws(websocket)

    assert claims["is_admin"] is True
    # Looked up by the token subject, which is the users table primary key.
    assert mock_is_admin.call_args.args[0]["sub"] == "azure-oid-123"


@pytest.mark.asyncio
async def test_falls_back_to_headers_when_token_rejected():
    """An unusable token does not break topologies that forward identity headers."""
    websocket = _build_websocket(
        {
            "Authorization": "Bearer not-a-valid-jwt",
            "X-Auth-Request-Email": "user@example.com",
        }
    )

    with (
        patch(
            "backend.api.auth.dependencies._authenticate_oauth_proxy_with_token",
            side_effect=ValueError("invalid token"),
        ),
        patch("backend.services.auth.rbac.is_user_admin", return_value=False),
    ):
        claims = await dependencies.get_current_user_ws(websocket)

    assert claims is not None
    assert claims["sub"] == "user@example.com"
    assert claims["auth_source"] == "websocket_oauth"


@pytest.mark.asyncio
async def test_header_only_identity_populates_admin_flag():
    """Header-based claims also carry is_admin, which callers read directly."""
    websocket = _build_websocket({"X-Forwarded-Email": "admin@example.com"})

    with patch("backend.services.auth.rbac.is_user_admin", return_value=True):
        claims = await dependencies.get_current_user_ws(websocket)

    assert claims["is_admin"] is True


@pytest.mark.asyncio
async def test_returns_none_without_token_or_headers():
    """No identity at all is rejected rather than defaulting to a user."""
    websocket = _build_websocket({"Host": "testserver"})

    assert await dependencies.get_current_user_ws(websocket) is None


@pytest.mark.asyncio
async def test_header_identity_rejected_without_proxy_secret(monkeypatch):
    """With AUTH_PROXY_SHARED_SECRET configured, spoofed identity headers fail.

    A client that reaches the backend directly can set X-Forwarded-Email, but
    without the proxy-injected X-Auth-Proxy-Secret the WS auth must reject it,
    mirroring the HTTP path's is_trusted_oauth_proxy_request enforcement.
    """
    from backend.services.auth.config import auth_config

    monkeypatch.setattr(auth_config, "proxy_auth_shared_secret", "expected-secret")
    websocket = _build_websocket({"X-Forwarded-Email": "attacker@example.com"})

    assert await dependencies.get_current_user_ws(websocket) is None


@pytest.mark.asyncio
async def test_header_identity_accepted_with_valid_proxy_secret(monkeypatch):
    """Identity headers are honoured when the proxy authenticity secret matches."""
    from backend.services.auth.config import auth_config

    monkeypatch.setattr(auth_config, "proxy_auth_shared_secret", "expected-secret")
    websocket = _build_websocket(
        {
            "X-Forwarded-Email": "user@example.com",
            "X-Auth-Proxy-Secret": "expected-secret",
        }
    )

    with patch("backend.services.auth.rbac.is_user_admin", return_value=False):
        claims = await dependencies.get_current_user_ws(websocket)

    assert claims is not None
    assert claims["sub"] == "user@example.com"
