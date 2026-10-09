"""Tests for PAT scope enforcer.

Covers:
- _scopes_satisfy: wildcard expansion, api:* super-scope, exact match
- require_scope: session users bypass, PAT users enforced
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.services.auth.scope_enforcer import _scopes_satisfy


# ---------------------------------------------------------------------------
# _scopes_satisfy — pure function tests (no I/O)
# ---------------------------------------------------------------------------


class TestScopesSatisfy:
    # api:* super-scope
    def test_api_star_satisfies_any_wildcard_scope(self):
        assert _scopes_satisfy(["api:*"], "workflow:*:execute")

    def test_api_star_satisfies_named_scope(self):
        assert _scopes_satisfy(["api:*"], "workflow:my-flow:execute")

    def test_api_star_satisfies_itself(self):
        assert _scopes_satisfy(["api:*"], "api:*")

    def test_api_star_satisfies_admin_scope(self):
        assert _scopes_satisfy(["api:*"], "document:*:read")

    # Exact match
    def test_exact_match_passes(self):
        assert _scopes_satisfy(["workflow:*:execute"], "workflow:*:execute")

    def test_exact_match_different_scope_fails(self):
        assert not _scopes_satisfy(["workflow:*:execute"], "workflow:*:read")

    # Wildcard expansion: resource:*:action → resource:<name>:action
    def test_wildcard_execute_covers_named_execute(self):
        assert _scopes_satisfy(["workflow:*:execute"], "workflow:my-flow:execute")

    def test_wildcard_read_covers_named_read(self):
        assert _scopes_satisfy(["workflow:*:read"], "workflow:some-workflow:read")

    def test_wildcard_execute_does_not_cover_named_read(self):
        assert not _scopes_satisfy(["workflow:*:execute"], "workflow:my-flow:read")

    def test_wildcard_read_does_not_cover_named_execute(self):
        assert not _scopes_satisfy(["workflow:*:read"], "workflow:my-flow:execute")

    def test_named_scope_does_not_cover_different_named_scope(self):
        assert not _scopes_satisfy(["workflow:flow-a:execute"], "workflow:flow-b:execute")

    def test_named_scope_covers_itself_exactly(self):
        assert _scopes_satisfy(["workflow:flow-a:execute"], "workflow:flow-a:execute")

    # Multiple scopes in held list
    def test_one_of_multiple_scopes_satisfies(self):
        held = ["workflow:*:read", "workflow:*:execute"]
        assert _scopes_satisfy(held, "workflow:my-flow:execute")

    def test_none_of_multiple_scopes_satisfy(self):
        held = ["workflow:*:read", "document:*:write"]
        assert not _scopes_satisfy(held, "workflow:my-flow:execute")

    # Edge cases
    def test_empty_held_fails(self):
        assert not _scopes_satisfy([], "workflow:*:execute")

    def test_two_part_required_scope_no_wildcard_expansion(self):
        # api:* is a two-part scope; exact match only (unless api:* is in held)
        assert not _scopes_satisfy(["workflow:*:execute"], "api:*")

    def test_document_wildcard_covers_named_document(self):
        assert _scopes_satisfy(["document:*:read"], "document:my-collection:read")

    def test_datasource_wildcard_covers_named_datasource(self):
        assert _scopes_satisfy(["datasource:*:write"], "datasource:my-ds:write")

    # api:*:read — admin read scope covers any :read action
    def test_api_star_read_satisfies_workflow_read(self):
        assert _scopes_satisfy(["api:*:read"], "workflow:*:read")

    def test_api_star_read_satisfies_document_read(self):
        assert _scopes_satisfy(["api:*:read"], "document:*:read")

    def test_api_star_read_satisfies_evaluation_read(self):
        assert _scopes_satisfy(["api:*:read"], "evaluation:*:read")

    def test_api_star_read_satisfies_execution_read(self):
        assert _scopes_satisfy(["api:*:read"], "execution:*:read")

    def test_api_star_read_satisfies_named_resource_read(self):
        assert _scopes_satisfy(["api:*:read"], "workflow:my-flow:read")

    def test_api_star_read_does_not_satisfy_write(self):
        assert not _scopes_satisfy(["api:*:read"], "workflow:*:write")

    def test_api_star_read_does_not_satisfy_execute(self):
        assert not _scopes_satisfy(["api:*:read"], "workflow:*:execute")

    # api:*:write — admin write scope covers any :write or :execute action
    def test_api_star_write_satisfies_workflow_write(self):
        assert _scopes_satisfy(["api:*:write"], "workflow:*:write")

    def test_api_star_write_satisfies_datasource_write(self):
        assert _scopes_satisfy(["api:*:write"], "datasource:*:write")

    def test_api_star_write_satisfies_evaluation_write(self):
        assert _scopes_satisfy(["api:*:write"], "evaluation:*:write")

    def test_api_star_write_satisfies_execution_write(self):
        assert _scopes_satisfy(["api:*:write"], "execution:*:write")

    def test_api_star_write_satisfies_execute_action(self):
        assert _scopes_satisfy(["api:*:write"], "workflow:*:execute")

    def test_api_star_write_satisfies_named_resource_write(self):
        assert _scopes_satisfy(["api:*:write"], "datasource:my-ds:write")

    def test_api_star_write_does_not_satisfy_read(self):
        assert not _scopes_satisfy(["api:*:write"], "workflow:*:read")

    # Combined api:*:read + api:*:write covers everything
    def test_api_read_plus_write_covers_read(self):
        assert _scopes_satisfy(["api:*:read", "api:*:write"], "document:*:read")

    def test_api_read_plus_write_covers_write(self):
        assert _scopes_satisfy(["api:*:read", "api:*:write"], "evaluation:*:write")

    def test_api_read_plus_write_covers_execute(self):
        assert _scopes_satisfy(["api:*:read", "api:*:write"], "workflow:*:execute")

    # New scope types — execution and evaluation
    def test_execution_write_covers_named(self):
        assert _scopes_satisfy(["execution:*:write"], "execution:some-exec:write")

    def test_evaluation_read_covers_named(self):
        assert _scopes_satisfy(["evaluation:*:read"], "evaluation:my-dataset:read")

    def test_evaluation_write_covers_named(self):
        assert _scopes_satisfy(["evaluation:*:write"], "evaluation:my-dataset:write")

    def test_execution_read_does_not_cover_write(self):
        assert not _scopes_satisfy(["execution:*:read"], "execution:*:write")

    def test_evaluation_read_does_not_cover_write(self):
        assert not _scopes_satisfy(["evaluation:*:read"], "evaluation:*:write")


# ---------------------------------------------------------------------------
# require_scope — dependency factory (async)
# ---------------------------------------------------------------------------


class TestRequireScope:
    """Test the require_scope dependency factory using mock request/user claims."""

    def _make_request(self, path="/api/test", method="GET", client_host="127.0.0.1"):
        request = MagicMock()
        request.url.path = path
        request.method = method
        request.client.host = client_host
        return request

    def _session_claims(self, email="user@example.com"):
        """Claims for a session-authenticated (non-PAT) user."""
        return {
            "email": email,
            "sub": email,
            "auth_via_pat": False,
            "is_admin": False,
            "groups": [],
        }

    def _pat_claims(self, scopes=None, email="user@example.com", token_id="tok-1", prefix="na_abc"):
        """Synthetic PAT claims."""
        return {
            "email": email,
            "sub": email,
            "auth_via_pat": True,
            "is_admin": False,
            "groups": [],
            "active_scopes": scopes or [],
            "pat_token_id": token_id,
            "pat_token_prefix": prefix,
        }

    @pytest.mark.asyncio
    async def test_session_user_bypasses_scope_check(self):
        from backend.services.auth.scope_enforcer import require_scope

        dep = require_scope("workflow:*:execute")
        request = self._make_request()
        claims = self._session_claims()

        # Should not raise
        with patch("backend.services.auth.scope_enforcer._record_rejection") as mock_record:
            result = await dep(request=request, current_user=claims)
            mock_record.assert_not_called()
        assert result is None  # dependency returns None when it passes

    @pytest.mark.asyncio
    async def test_pat_with_sufficient_scope_passes(self):
        from backend.services.auth.scope_enforcer import require_scope

        dep = require_scope("workflow:*:execute")
        request = self._make_request()
        claims = self._pat_claims(scopes=["workflow:*:execute"])

        with patch("backend.services.auth.scope_enforcer._record_rejection") as mock_record:
            result = await dep(request=request, current_user=claims)
            mock_record.assert_not_called()
        assert result is None

    @pytest.mark.asyncio
    async def test_pat_with_api_star_passes_any_scope(self):
        from backend.services.auth.scope_enforcer import require_scope

        dep = require_scope("document:*:read")
        request = self._make_request()
        claims = self._pat_claims(scopes=["api:*"])

        with patch("backend.services.auth.scope_enforcer._record_rejection"):
            result = await dep(request=request, current_user=claims)
        assert result is None

    @pytest.mark.asyncio
    async def test_pat_without_scope_raises_403(self):
        from backend.services.auth.scope_enforcer import require_scope
        from fastapi import HTTPException

        dep = require_scope("workflow:*:execute")
        request = self._make_request()
        claims = self._pat_claims(scopes=["workflow:*:read"])

        with patch("backend.services.auth.scope_enforcer._record_rejection") as mock_record:
            with pytest.raises(HTTPException) as exc_info:
                await dep(request=request, current_user=claims)
            mock_record.assert_called_once()

        assert exc_info.value.status_code == 403
        assert "workflow:*:execute" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_pat_with_empty_scopes_raises_403(self):
        from backend.services.auth.scope_enforcer import require_scope
        from fastapi import HTTPException

        dep = require_scope("workflow:*:execute")
        request = self._make_request()
        claims = self._pat_claims(scopes=[])

        with patch("backend.services.auth.scope_enforcer._record_rejection"):
            with pytest.raises(HTTPException) as exc_info:
                await dep(request=request, current_user=claims)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_pat_wildcard_satisfies_named_scope_requirement(self):
        from backend.services.auth.scope_enforcer import require_scope

        dep = require_scope("workflow:*:execute")
        request = self._make_request()
        # Token has wildcard; route requires the named scope — wildcard should satisfy
        claims = self._pat_claims(scopes=["workflow:*:execute"])

        with patch("backend.services.auth.scope_enforcer._record_rejection") as mock_record:
            await dep(request=request, current_user=claims)
            mock_record.assert_not_called()

    def test_require_scope_asserts_on_unknown_scope(self):
        from backend.services.auth.scope_enforcer import require_scope

        with pytest.raises(AssertionError, match="Unknown scope"):
            require_scope("not:a:real:scope")

    def test_require_scope_named_resource_passes_registry_check(self):
        """Named resource scopes like workflow:my-flow:execute are valid."""
        from backend.services.auth.scope_enforcer import require_scope

        # Should not raise AssertionError since named scopes are valid
        dep = require_scope("workflow:my-flow:execute")
        assert callable(dep)

    @pytest.mark.asyncio
    async def test_pat_with_api_star_read_passes_read_scope(self):
        from backend.services.auth.scope_enforcer import require_scope

        dep = require_scope("evaluation:*:read")
        request = self._make_request()
        claims = self._pat_claims(scopes=["api:*:read"])

        with patch("backend.services.auth.scope_enforcer._record_rejection"):
            result = await dep(request=request, current_user=claims)
        assert result is None

    @pytest.mark.asyncio
    async def test_pat_with_api_star_read_fails_write_scope(self):
        from backend.services.auth.scope_enforcer import require_scope
        from fastapi import HTTPException

        dep = require_scope("evaluation:*:write")
        request = self._make_request()
        claims = self._pat_claims(scopes=["api:*:read"])

        with patch("backend.services.auth.scope_enforcer._record_rejection"):
            with pytest.raises(HTTPException) as exc_info:
                await dep(request=request, current_user=claims)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_pat_with_api_star_write_passes_write_scope(self):
        from backend.services.auth.scope_enforcer import require_scope

        dep = require_scope("datasource:*:write")
        request = self._make_request()
        claims = self._pat_claims(scopes=["api:*:write"])

        with patch("backend.services.auth.scope_enforcer._record_rejection"):
            result = await dep(request=request, current_user=claims)
        assert result is None

    @pytest.mark.asyncio
    async def test_pat_with_api_star_write_passes_execute_scope(self):
        from backend.services.auth.scope_enforcer import require_scope

        dep = require_scope("workflow:*:execute")
        request = self._make_request()
        claims = self._pat_claims(scopes=["api:*:write"])

        with patch("backend.services.auth.scope_enforcer._record_rejection"):
            result = await dep(request=request, current_user=claims)
        assert result is None

    @pytest.mark.asyncio
    async def test_pat_with_api_star_write_fails_read_scope(self):
        from backend.services.auth.scope_enforcer import require_scope
        from fastapi import HTTPException

        dep = require_scope("workflow:*:read")
        request = self._make_request()
        claims = self._pat_claims(scopes=["api:*:write"])

        with patch("backend.services.auth.scope_enforcer._record_rejection"):
            with pytest.raises(HTTPException) as exc_info:
                await dep(request=request, current_user=claims)
        assert exc_info.value.status_code == 403

    def test_require_scope_accepts_new_scope_types(self):
        """New scope types should pass registry validation."""
        from backend.services.auth.scope_enforcer import require_scope

        for scope in ["execution:*:write", "evaluation:*:read", "evaluation:*:write"]:
            dep = require_scope(scope)
            assert callable(dep)
