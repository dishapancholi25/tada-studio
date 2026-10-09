"""Tests for the shared authorization framework.

ISG Finding 6430: Missing Object and Function-Level Authorization
"""

import sys
from unittest.mock import MagicMock

# Pre-mock heavy dependencies that may not be installed in test env
for mod in [
    "langchain_anthropic",
    "langchain_google_genai",
    "langchain_text_splitters",
    "langchain_community",
    "langchain_community.document_loaders",
    "langchain_community.vectorstores",
    "langchain_community.embeddings",
]:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

import pytest
from unittest.mock import patch
from fastapi import HTTPException

from backend.services.authorization.helpers import (
    get_user_identifier,
    verify_workflow_access,
    verify_workflow_access_by_id,
    verify_execution_access,
    require_workflow_access,
    require_execution_access,
    require_workflow_access_by_id,
)


class TestGetUserIdentifier:
    """Tests for extracting user identifier from JWT claims."""

    def test_returns_sub_claim(self):
        user = {"sub": "user-123", "email": "test@example.com"}
        assert get_user_identifier(user) == "user-123"

    def test_raises_401_when_sub_missing(self):
        user = {"email": "test@example.com"}
        with pytest.raises(HTTPException) as exc_info:
            get_user_identifier(user)
        assert exc_info.value.status_code == 401

    def test_raises_401_when_sub_empty(self):
        user = {"sub": "", "email": "test@example.com"}
        with pytest.raises(HTTPException) as exc_info:
            get_user_identifier(user)
        assert exc_info.value.status_code == 401

    def test_raises_401_when_sub_none(self):
        user = {"sub": None}
        with pytest.raises(HTTPException) as exc_info:
            get_user_identifier(user)
        assert exc_info.value.status_code == 401


class TestVerifyWorkflowAccess:
    """Tests for workflow access verification by graph name."""

    @patch("backend.services.authorization.helpers.get_db")
    def test_admin_access_granted(self, mock_get_db):
        mock_db = MagicMock()
        mock_gd = MagicMock()
        mock_gd.workflow_id = "wf-123"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_gd
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        result = verify_workflow_access("admin-user", "my-graph", is_admin=True)
        assert result == "wf-123"

    @patch("backend.services.authorization.helpers._storage_verify_workflow_access")
    @patch("backend.services.authorization.helpers.get_db")
    def test_owner_access_granted(self, mock_get_db, mock_storage_verify):
        mock_db = MagicMock()
        mock_gd = MagicMock()
        mock_gd.workflow_id = "wf-456"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_gd
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_storage_verify.return_value = True

        result = verify_workflow_access("user-123", "my-graph")
        assert result == "wf-456"

    @patch("backend.services.authorization.helpers._storage_verify_workflow_access")
    @patch("backend.services.authorization.helpers.get_db")
    def test_access_denied_raises_403(self, mock_get_db, mock_storage_verify):
        mock_db = MagicMock()
        mock_gd = MagicMock()
        mock_gd.workflow_id = "wf-789"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_gd
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_storage_verify.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            verify_workflow_access("user-123", "my-graph")
        assert exc_info.value.status_code == 403

    @patch("backend.services.authorization.helpers.get_db")
    def test_workflow_not_found_raises_404(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            verify_workflow_access("user-123", "nonexistent-graph")
        assert exc_info.value.status_code == 404


class TestVerifyWorkflowAccessById:
    """Tests for workflow access verification by workflow ID."""

    def test_admin_always_granted(self):
        assert verify_workflow_access_by_id("admin", "wf-123", is_admin=True) is True

    @patch("backend.services.authorization.helpers._storage_verify_workflow_access")
    @patch("backend.services.authorization.helpers.get_db")
    def test_owner_access_granted(self, mock_get_db, mock_storage_verify):
        mock_db = MagicMock()
        mock_workflow = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_workflow
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_storage_verify.return_value = True

        assert verify_workflow_access_by_id("user-123", "wf-456") is True

    @patch("backend.services.authorization.helpers._storage_verify_workflow_access")
    @patch("backend.services.authorization.helpers.get_db")
    def test_access_denied_raises_403(self, mock_get_db, mock_storage_verify):
        mock_db = MagicMock()
        mock_workflow = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_workflow
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_storage_verify.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            verify_workflow_access_by_id("user-123", "wf-456")
        assert exc_info.value.status_code == 403

    @patch("backend.services.authorization.helpers.get_db")
    def test_workflow_not_found_raises_404(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            verify_workflow_access_by_id("user-123", "wf-nonexistent")
        assert exc_info.value.status_code == 404


class TestVerifyExecutionAccess:
    """Tests for execution access verification."""

    @patch("backend.services.authorization.helpers.get_db")
    def test_execution_not_found_raises_404(self, mock_get_db):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        with pytest.raises(HTTPException) as exc_info:
            verify_execution_access("user-123", "exec-nonexistent")
        assert exc_info.value.status_code == 404

    @patch("backend.services.authorization.helpers.get_db")
    def test_admin_access_granted(self, mock_get_db):
        mock_db = MagicMock()
        mock_exec = MagicMock()
        mock_exec.id = "exec-123"
        mock_exec.user_id = "other-user"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_exec
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)

        result = verify_execution_access("admin-user", "exec-123", is_admin=True)
        assert result == mock_exec

    @patch("backend.services.authorization.helpers.resolve_user_id")
    @patch("backend.services.authorization.helpers.get_db")
    def test_initiator_access_granted(self, mock_get_db, mock_resolve):
        mock_db = MagicMock()
        mock_exec = MagicMock()
        mock_exec.id = "exec-123"
        mock_exec.user_id = "resolved-user-id"
        mock_exec.workflow_id = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_exec
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_resolve.return_value = "resolved-user-id"

        result = verify_execution_access("user-123", "exec-123")
        assert result == mock_exec

    @patch("backend.services.authorization.helpers._storage_verify_workflow_access")
    @patch("backend.services.authorization.helpers.resolve_user_id")
    @patch("backend.services.authorization.helpers.get_db")
    def test_workflow_member_access_granted(self, mock_get_db, mock_resolve, mock_storage_verify):
        mock_db = MagicMock()
        mock_exec = MagicMock()
        mock_exec.id = "exec-123"
        mock_exec.user_id = "other-user"
        mock_exec.workflow_id = "wf-456"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_exec
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_resolve.return_value = "different-resolved-id"
        mock_storage_verify.return_value = True

        result = verify_execution_access("user-123", "exec-123")
        assert result == mock_exec

    @patch("backend.services.authorization.helpers._storage_verify_workflow_access")
    @patch("backend.services.authorization.helpers.resolve_user_id")
    @patch("backend.services.authorization.helpers.get_db")
    def test_access_denied_raises_403(self, mock_get_db, mock_resolve, mock_storage_verify):
        mock_db = MagicMock()
        mock_exec = MagicMock()
        mock_exec.id = "exec-123"
        mock_exec.user_id = "other-user"
        mock_exec.workflow_id = "wf-456"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_exec
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        mock_resolve.return_value = "different-resolved-id"
        mock_storage_verify.return_value = False

        with pytest.raises(HTTPException) as exc_info:
            verify_execution_access("user-123", "exec-123")
        assert exc_info.value.status_code == 403


class TestConvenienceFunctions:
    """Tests for require_* convenience wrappers."""

    @patch("backend.services.authorization.helpers.verify_workflow_access")
    def test_require_workflow_access_extracts_user(self, mock_verify):
        mock_verify.return_value = "wf-123"
        user = {"sub": "user-123", "is_admin": False}

        result = require_workflow_access(user, "my-graph")
        assert result == "wf-123"
        mock_verify.assert_called_once_with("user-123", "my-graph", False)

    @patch("backend.services.authorization.helpers.verify_workflow_access")
    def test_require_workflow_access_passes_admin_flag(self, mock_verify):
        mock_verify.return_value = "wf-123"
        user = {"sub": "admin-user", "is_admin": True}

        require_workflow_access(user, "my-graph")
        mock_verify.assert_called_once_with("admin-user", "my-graph", True)

    def test_require_workflow_access_raises_on_missing_sub(self):
        user = {"email": "test@example.com"}
        with pytest.raises(HTTPException) as exc_info:
            require_workflow_access(user, "my-graph")
        assert exc_info.value.status_code == 401

    @patch("backend.services.authorization.helpers.verify_execution_access")
    def test_require_execution_access_extracts_user(self, mock_verify):
        mock_exec = MagicMock()
        mock_verify.return_value = mock_exec
        user = {"sub": "user-123", "is_admin": False}

        result = require_execution_access(user, "exec-456")
        assert result == mock_exec
        mock_verify.assert_called_once_with("user-123", "exec-456", False)

    @patch("backend.services.authorization.helpers.verify_workflow_access_by_id")
    def test_require_workflow_access_by_id_works(self, mock_verify):
        mock_verify.return_value = True
        user = {"sub": "user-123", "is_admin": False}

        result = require_workflow_access_by_id(user, "wf-789")
        assert result is True
        mock_verify.assert_called_once_with("user-123", "wf-789", False)
