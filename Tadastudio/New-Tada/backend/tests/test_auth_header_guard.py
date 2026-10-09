"""Tests for ISG Finding 1.9 – Sensitive header stripping.

Verifies that:
1. SensitiveHeaderStripMiddleware removes auth proxy headers from responses
2. The /api/auth/nginx-check endpoint does not forward token headers
3. Non-sensitive headers are preserved
"""

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.api.security.auth_header_guard import (
    SensitiveHeaderStripMiddleware,
    _SENSITIVE_RESPONSE_HEADERS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app_with_middleware() -> FastAPI:
    """Create a minimal FastAPI app with the header-strip middleware."""
    app = FastAPI()
    app.add_middleware(SensitiveHeaderStripMiddleware)

    @app.get("/echo-headers")
    async def echo_headers(request: Request) -> dict:
        """Endpoint that deliberately injects sensitive headers into the response."""
        resp = Response(content='{"ok": true}', media_type="application/json")
        # Simulate headers that oauth2-proxy might inject
        resp.headers["X-Auth-Request-Access-Token"] = "eyJ_FAKE_TOKEN"
        resp.headers["X-Auth-Request-Email"] = "user@test.com"
        resp.headers["X-Auth-Request-User"] = "user@test.com"
        resp.headers["X-Auth-Request-Username"] = "user"
        resp.headers["X-Auth-Request-Preferred-Username"] = "user@test.com"
        resp.headers["X-Auth-Request-Groups"] = "group1,group2"
        resp.headers["X-Forwarded-Access-Token"] = "eyJ_FAKE_TOKEN_2"
        # Also add a safe header
        resp.headers["X-Custom-App-Header"] = "keep-me"
        return resp

    @app.get("/clean-endpoint")
    async def clean_endpoint() -> dict:
        """Endpoint that does NOT set sensitive headers."""
        return {"status": "ok"}

    return app


@pytest.fixture()
def client(app_with_middleware: FastAPI) -> TestClient:
    return TestClient(app_with_middleware)


# ---------------------------------------------------------------------------
# Middleware Tests
# ---------------------------------------------------------------------------


class TestSensitiveHeaderStripMiddleware:
    """Tests for the SensitiveHeaderStripMiddleware."""

    def test_strips_all_sensitive_headers(self, client: TestClient) -> None:
        """All X-Auth-Request-* and X-Forwarded-Access-Token headers
        must be removed from the response."""
        resp = client.get("/echo-headers")
        assert resp.status_code == 200

        for header in _SENSITIVE_RESPONSE_HEADERS:
            assert header not in {
                k.lower() for k in resp.headers.keys()
            }, f"Sensitive header '{header}' was NOT stripped from response"

    def test_preserves_non_sensitive_headers(self, client: TestClient) -> None:
        """Non-sensitive headers must pass through untouched."""
        resp = client.get("/echo-headers")
        assert resp.headers.get("x-custom-app-header") == "keep-me"
        assert "content-type" in resp.headers

    def test_clean_endpoint_unaffected(self, client: TestClient) -> None:
        """Endpoints that don't set sensitive headers should work normally."""
        resp = client.get("/clean-endpoint")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_access_token_specifically_null(self, client: TestClient) -> None:
        """Simulates the ISG PoC: response.headers.get('X-Auth-Request-Access-Token')
        must return None."""
        resp = client.get("/echo-headers")
        assert resp.headers.get("X-Auth-Request-Access-Token") is None

    def test_all_isg_headers_null(self, client: TestClient) -> None:
        """ISG Finding 1.9: every identity and token header must be null in responses."""
        resp = client.get("/echo-headers")
        assert resp.headers.get("X-Auth-Request-Access-Token") is None
        assert resp.headers.get("X-Auth-Request-Email") is None
        assert resp.headers.get("X-Auth-Request-User") is None
        assert resp.headers.get("X-Auth-Request-Username") is None
        assert resp.headers.get("X-Auth-Request-Preferred-Username") is None

    def test_sensitive_headers_frozenset_complete(self) -> None:
        """Verify the header set covers all ISG-identified headers."""
        expected = {
            "x-auth-request-access-token",
            "x-auth-request-email",
            "x-auth-request-user",
            "x-auth-request-username",
            "x-auth-request-preferred-username",
            "x-auth-request-groups",
            "x-forwarded-access-token",
        }
        assert _SENSITIVE_RESPONSE_HEADERS == expected


# ---------------------------------------------------------------------------
# nginx-check Endpoint Tests
# ---------------------------------------------------------------------------


class TestNginxCheckHeaderForwarding:
    """Verify that /api/auth/nginx-check does not forward token headers."""

    def test_nginx_check_excluded_headers(self) -> None:
        """The nginx-check endpoint's header forwarding list must NOT include
        token-related headers."""
        import inspect
        from backend.api.auth import routes

        # Get the source of the nginx_session_check function
        source = inspect.getsource(routes.nginx_session_check)

        # These headers must NOT appear in the forwarding tuple
        # (they carry tokens that would leak to the browser)
        forbidden = [
            "X-Auth-Request-Access-Token",
            "X-Forwarded-Access-Token",
        ]

        for header in forbidden:
            assert header not in source, (
                f"nginx-check still forwards '{header}' — "
                f"this leaks tokens to the browser (ISG 1.9)"
            )

    def test_nginx_check_still_forwards_identity_headers(self) -> None:
        """The nginx-check endpoint must still forward User/Email/Groups
        for the auth subrequest to work."""
        import inspect
        from backend.api.auth import routes

        source = inspect.getsource(routes.nginx_session_check)

        required = [
            "X-Auth-Request-User",
            "X-Auth-Request-Email",
            "X-Auth-Request-Groups",
        ]

        for header in required:
            assert header in source, (
                f"nginx-check no longer forwards '{header}' — "
                f"this will break auth subrequest functionality"
            )


class FakeProxyResponse:
    """Stand-in for oauth2-proxy's /oauth2/auth response."""

    def __init__(self, status_code: int, headers: dict):
        import httpx

        self.status_code = status_code
        self.headers = httpx.Headers(headers)


class FakeAsyncClient:
    """Async-context-manager client returning a canned proxy response."""

    response: FakeProxyResponse

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def get(self, *args, **kwargs):
        return type(self).response


def _nginx_check_request() -> Request:
    """Minimal request with no cookies, so the local-auth branch is skipped."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/auth/nginx-check",
            "query_string": b"",
            "headers": [(b"host", b"localhost")],
        }
    )


class TestNginxCheckSetXAuthRequestDisabled:
    """nginx-check must still resolve identity when oauth2-proxy runs with
    --set-xauthrequest=false, which suppresses the X-Auth-Request-* headers."""

    def _patch(self, monkeypatch, status_code: int, headers: dict):
        from backend.api.auth import routes

        FakeAsyncClient.response = FakeProxyResponse(status_code, headers)
        monkeypatch.setattr(routes.httpx, "AsyncClient", FakeAsyncClient)
        return routes

    async def test_falls_back_to_gap_auth(self, monkeypatch) -> None:
        """With no X-Auth-Request-*, GAP-Auth supplies the identity."""
        routes = self._patch(
            monkeypatch, 202, {"GAP-Auth": "SachinKar@mashreq.com"}
        )

        resp = await routes.nginx_session_check(_nginx_check_request())

        assert resp.status_code == 200
        assert resp.headers["X-Auth-Request-Email"] == "SachinKar@mashreq.com"
        assert resp.headers["X-Auth-Request-User"] == "SachinKar@mashreq.com"

    async def test_explicit_headers_win_over_gap_auth(self, monkeypatch) -> None:
        """When set_xauthrequest is enabled, its values must not be overwritten."""
        routes = self._patch(
            monkeypatch,
            202,
            {
                "X-Auth-Request-Email": "real@mashreq.com",
                "X-Auth-Request-User": "opaque-user-id",
                "GAP-Auth": "SachinKar@mashreq.com",
            },
        )

        resp = await routes.nginx_session_check(_nginx_check_request())

        assert resp.headers["X-Auth-Request-Email"] == "real@mashreq.com"
        assert resp.headers["X-Auth-Request-User"] == "opaque-user-id"

    async def test_no_identity_available_is_not_fatal(self, monkeypatch) -> None:
        """A response carrying neither header must not raise."""
        routes = self._patch(monkeypatch, 202, {})

        resp = await routes.nginx_session_check(_nginx_check_request())

        assert resp.status_code == 200
        assert "X-Auth-Request-Email" not in resp.headers

    async def test_unauthenticated_status_is_preserved(self, monkeypatch) -> None:
        """A 401 from oauth2-proxy must still surface as 401."""
        routes = self._patch(monkeypatch, 401, {"GAP-Auth": "x@y.com"})

        resp = await routes.nginx_session_check(_nginx_check_request())

        assert resp.status_code == 401
