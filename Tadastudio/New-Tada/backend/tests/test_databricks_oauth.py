"""Tests for Databricks OAuth M2M (Service Principal) authentication."""

import base64
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.services.oauth.databricks_handler import (
    DatabricksM2MHandler,
    _token_cache,
    clear_cached_tokens,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the token cache before and after each test."""
    _token_cache.clear()
    yield
    _token_cache.clear()


# ---------------------------------------------------------------------------
# DatabricksM2MHandler init
# ---------------------------------------------------------------------------


class TestDatabricksM2MHandlerInit:
    def test_strips_https_prefix(self):
        handler = DatabricksM2MHandler(
            "https://adb-123.azuredatabricks.net", "cid", "csec"
        )
        assert handler.workspace_hostname == "adb-123.azuredatabricks.net"
        assert handler.token_url == "https://adb-123.azuredatabricks.net/oidc/v1/token"

    def test_strips_trailing_slash(self):
        handler = DatabricksM2MHandler("adb-123.azuredatabricks.net/", "cid", "csec")
        assert handler.workspace_hostname == "adb-123.azuredatabricks.net"

    def test_plain_hostname(self):
        handler = DatabricksM2MHandler("adb-123.azuredatabricks.net", "cid", "csec")
        assert handler.token_url == "https://adb-123.azuredatabricks.net/oidc/v1/token"

    def test_strips_url_path(self):
        """Full server URL passed as hostname — path must be stripped."""
        handler = DatabricksM2MHandler(
            "https://adb-123.3.azuredatabricks.net/api/2.0/mcp/sql", "cid", "csec"
        )
        assert handler.workspace_hostname == "adb-123.3.azuredatabricks.net"
        assert (
            handler.token_url == "https://adb-123.3.azuredatabricks.net/oidc/v1/token"
        )

    def test_strips_path_without_protocol(self):
        handler = DatabricksM2MHandler(
            "adb-123.azuredatabricks.net/api/2.0/mcp/functions/cat/sch", "cid", "csec"
        )
        assert handler.workspace_hostname == "adb-123.azuredatabricks.net"

    def test_accepts_cloud_databricks_com(self):
        handler = DatabricksM2MHandler(
            "my-workspace.cloud.databricks.com", "cid", "csec"
        )
        assert (
            handler.token_url
            == "https://my-workspace.cloud.databricks.com/oidc/v1/token"
        )

    def test_accepts_gcp_databricks_com(self):
        handler = DatabricksM2MHandler("my-workspace.gcp.databricks.com", "cid", "csec")
        assert (
            handler.token_url == "https://my-workspace.gcp.databricks.com/oidc/v1/token"
        )

    def test_rejects_non_databricks_domain(self):
        with pytest.raises(ValueError, match="not on the allowed domain list"):
            DatabricksM2MHandler("evil-server.example.com", "cid", "csec")

    def test_rejects_localhost(self):
        with pytest.raises(ValueError, match="not on the allowed domain list"):
            DatabricksM2MHandler("127.0.0.1", "cid", "csec")

    def test_rejects_private_ip(self):
        with pytest.raises(ValueError, match="not on the allowed domain list"):
            DatabricksM2MHandler("10.0.0.1", "cid", "csec")

    def test_rejects_metadata_endpoint(self):
        with pytest.raises(ValueError, match="not on the allowed domain list"):
            DatabricksM2MHandler("169.254.169.254", "cid", "csec")


# ---------------------------------------------------------------------------
# _fetch_token: form-body success
# ---------------------------------------------------------------------------


class TestFetchTokenFormBody:
    @pytest.mark.asyncio
    async def test_form_body_success(self):
        handler = DatabricksM2MHandler(
            "adb-123.azuredatabricks.net", "client-id", "client-secret"
        )

        mock_response = httpx.Response(
            200,
            json={"access_token": "tok-abc", "expires_in": 3600},
            request=httpx.Request("POST", handler.token_url),
        )

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response
        ):
            token = await handler._fetch_token()

        assert token == "tok-abc"
        assert handler._cache_key in _token_cache

    @pytest.mark.asyncio
    async def test_form_body_missing_access_token(self):
        handler = DatabricksM2MHandler("adb-123.azuredatabricks.net", "cid", "csec")

        mock_response = httpx.Response(
            200,
            json={"token_type": "bearer"},
            request=httpx.Request("POST", handler.token_url),
        )

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response
        ):
            with pytest.raises(ValueError, match="missing access_token"):
                await handler._fetch_token()


# ---------------------------------------------------------------------------
# _fetch_token: Basic Auth fallback on 401
# ---------------------------------------------------------------------------


class TestFetchTokenBasicAuthFallback:
    @pytest.mark.asyncio
    async def test_fallback_to_basic_auth_on_401(self):
        handler = DatabricksM2MHandler(
            "adb-123.azuredatabricks.net", "client-id", "client-secret"
        )

        # First call returns 401, second succeeds
        resp_401 = httpx.Response(
            401,
            json={"error": "unauthorized"},
            request=httpx.Request("POST", handler.token_url),
        )
        resp_200 = httpx.Response(
            200,
            json={"access_token": "tok-basic", "expires_in": 1800},
            request=httpx.Request("POST", handler.token_url),
        )

        mock_post = AsyncMock(side_effect=[resp_401, resp_200])
        with patch("httpx.AsyncClient.post", mock_post):
            token = await handler._fetch_token()

        assert token == "tok-basic"
        # Verify Basic Auth was used in the second call
        second_call_headers = mock_post.call_args_list[1].kwargs.get(
            "headers",
            mock_post.call_args_list[1][1].get("headers", {})
            if len(mock_post.call_args_list[1]) > 1
            else {},
        )
        expected_creds = base64.b64encode(b"client-id:client-secret").decode()
        assert second_call_headers.get("Authorization") == f"Basic {expected_creds}"

    @pytest.mark.asyncio
    async def test_non_401_does_not_fallback(self):
        handler = DatabricksM2MHandler("adb-123.azuredatabricks.net", "cid", "csec")

        resp_403 = httpx.Response(
            403,
            json={"error": "forbidden"},
            request=httpx.Request("POST", handler.token_url),
        )

        mock_post = AsyncMock(return_value=resp_403)
        with patch("httpx.AsyncClient.post", mock_post):
            with pytest.raises(ValueError, match="HTTP 403"):
                await handler._fetch_token()

        # Only one call should have been made (no fallback)
        assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_both_methods_fail(self):
        handler = DatabricksM2MHandler("adb-123.azuredatabricks.net", "cid", "csec")

        resp_401_a = httpx.Response(
            401,
            json={"error": "bad creds"},
            request=httpx.Request("POST", handler.token_url),
        )
        resp_401_b = httpx.Response(
            401,
            json={"error": "still bad"},
            request=httpx.Request("POST", handler.token_url),
        )

        mock_post = AsyncMock(side_effect=[resp_401_a, resp_401_b])
        with patch("httpx.AsyncClient.post", mock_post):
            with pytest.raises(ValueError, match="both auth methods"):
                await handler._fetch_token()

        assert mock_post.call_count == 2


# ---------------------------------------------------------------------------
# _fetch_token: connection errors
# ---------------------------------------------------------------------------


class TestFetchTokenConnectionError:
    @pytest.mark.asyncio
    async def test_connection_error(self):
        handler = DatabricksM2MHandler("adb-123.azuredatabricks.net", "cid", "csec")

        mock_post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        with patch("httpx.AsyncClient.post", mock_post):
            with pytest.raises(ValueError, match="Failed to connect"):
                await handler._fetch_token()


# ---------------------------------------------------------------------------
# get_valid_token: caching
# ---------------------------------------------------------------------------


class TestGetValidToken:
    @pytest.mark.asyncio
    async def test_returns_cached_token(self):
        handler = DatabricksM2MHandler("adb-123.azuredatabricks.net", "cid", "csec")

        import time

        _token_cache[handler._cache_key] = ("cached-tok", time.time() + 600)

        token = await handler.get_valid_token()
        assert token == "cached-tok"

    @pytest.mark.asyncio
    async def test_fetches_when_cache_expired(self):
        handler = DatabricksM2MHandler("adb-123.azuredatabricks.net", "cid", "csec")

        import time

        # Expired token (past the refresh buffer)
        _token_cache[handler._cache_key] = ("old-tok", time.time() + 100)

        mock_response = httpx.Response(
            200,
            json={"access_token": "new-tok", "expires_in": 3600},
            request=httpx.Request("POST", handler.token_url),
        )

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response
        ):
            token = await handler.get_valid_token()

        assert token == "new-tok"


# ---------------------------------------------------------------------------
# clear_cached_tokens
# ---------------------------------------------------------------------------


class TestClearCachedTokens:
    def test_clear_all(self):
        _token_cache[("host1", "c1")] = ("t1", 0)
        _token_cache[("host2", "c2")] = ("t2", 0)
        clear_cached_tokens()
        assert len(_token_cache) == 0

    def test_clear_by_workspace(self):
        _token_cache[("host1", "c1")] = ("t1", 0)
        _token_cache[("host2", "c2")] = ("t2", 0)
        clear_cached_tokens("host1")
        assert ("host1", "c1") not in _token_cache
        assert ("host2", "c2") in _token_cache
