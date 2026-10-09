"""Tests for DocumentSearchService SQL parameterization of document_ids.

Verifies the security fix that replaced string-interpolated document_ids
with proper SQLAlchemy parameterized queries (ANY(:document_ids)).

These tests mock the database layer and verify that the generated SQL text
uses :document_ids as a bind parameter rather than inlining the values.
"""

import sys
from contextlib import contextmanager
from types import ModuleType
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub heavy third-party modules that are not needed for SQL-construction
# tests. This avoids pulling in langchain_anthropic, pgvector, etc.
# ---------------------------------------------------------------------------
_STUBS = [
    "pgvector",
    "pgvector.sqlalchemy",
    "langchain_anthropic",
    "langchain_openai",
    "langchain_google_genai",
    "langchain_aws",
]
for _mod_name in _STUBS:
    if _mod_name not in sys.modules:
        _stub = ModuleType(_mod_name)
        # Give common attributes that import-time code may reference
        for _attr in (
            "ChatAnthropic",
            "AzureChatOpenAI",
            "ChatOpenAI",
            "ChatGoogleGenerativeAI",
            "ChatBedrock",
            "Vector",
            "AzureOpenAIEmbeddings",
            "OpenAIEmbeddings",
        ):
            setattr(_stub, _attr, MagicMock())
        sys.modules[_mod_name] = _stub


# Now patch the module-level singleton creation so importing doesn't
# trigger real storage/embedding initialization.
with patch(
    "backend.services.document_storage.service.DocumentStorageService.__init__",
    lambda self, *a, **kw: None,
):
    from backend.services.document_storage.search_service import (
        DocumentSearchService,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_storage():
    """Create a mock storage service with mock embeddings."""
    mock_embeddings = MagicMock()
    mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
    mock_embeddings.model = "text-embedding-3-small"

    mock_storage = MagicMock()
    mock_storage.get_embeddings.return_value = mock_embeddings
    return mock_storage


@contextmanager
def _patched_db():
    """Yield (mock_session, patch) with get_db mocked as a context manager."""
    mock_session = MagicMock()
    mock_session.execute.return_value.fetchall.return_value = []

    with patch(
        "backend.services.document_storage.search_service.get_db"
    ) as mock_get_db:
        mock_get_db.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_db.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_session


def _get_executed_sql_and_params(mock_session):
    """Extract the SQL text string and params dict from the execute call."""
    call_args = mock_session.execute.call_args[0]
    sql_text = call_args[0].text
    params = call_args[1]
    return sql_text, params


# ---------------------------------------------------------------------------
# vector_search parameterization tests
# ---------------------------------------------------------------------------


class TestVectorSearchParameterization:
    """Ensure vector_search uses parameterized queries for document_ids."""

    def test_without_document_ids(self):
        """Query omits ANY(:document_ids) when no filter is given."""
        with _patched_db() as mock_session:
            service = DocumentSearchService(storage_service=_make_mock_storage())
            service.vector_search("col-1", "test query", k=5, document_ids=None)

        sql_text, params = _get_executed_sql_and_params(mock_session)
        assert "ANY(:document_ids)" not in sql_text
        assert "document_ids" not in params

    def test_with_document_ids_uses_bind_param(self):
        """document_ids is passed as a bind parameter, not interpolated into SQL."""
        doc_ids = ["doc-aaa", "doc-bbb"]

        with _patched_db() as mock_session:
            service = DocumentSearchService(storage_service=_make_mock_storage())
            service.vector_search("col-1", "test query", k=5, document_ids=doc_ids)

        sql_text, params = _get_executed_sql_and_params(mock_session)

        assert "ANY(:document_ids)" in sql_text
        assert params["document_ids"] == doc_ids
        # Values must NOT appear in the SQL string itself
        for doc_id in doc_ids:
            assert doc_id not in sql_text

    def test_sql_injection_payloads_not_in_sql_text(self):
        """Malicious document_ids never appear in the SQL text."""
        malicious_ids = ["'; DROP TABLE documents;--", "1' OR '1'='1"]

        with _patched_db() as mock_session:
            service = DocumentSearchService(storage_service=_make_mock_storage())
            service.vector_search("col-1", "query", k=5, document_ids=malicious_ids)

        sql_text, params = _get_executed_sql_and_params(mock_session)

        for payload in malicious_ids:
            assert payload not in sql_text
        assert params["document_ids"] == malicious_ids


# ---------------------------------------------------------------------------
# text_search parameterization tests
# ---------------------------------------------------------------------------


class TestTextSearchParameterization:
    """Ensure text_search uses parameterized queries for document_ids."""

    def test_without_document_ids(self):
        """Query omits ANY(:document_ids) when no filter is given."""
        with _patched_db() as mock_session:
            DocumentSearchService.text_search(
                "col-1", "test query", k=5, document_ids=None
            )

        sql_text, params = _get_executed_sql_and_params(mock_session)
        assert "ANY(:document_ids)" not in sql_text
        assert "document_ids" not in params

    def test_with_document_ids_uses_bind_param(self):
        """document_ids is passed as a bind parameter, not interpolated into SQL."""
        doc_ids = ["doc-111", "doc-222", "doc-333"]

        with _patched_db() as mock_session:
            DocumentSearchService.text_search(
                "col-1", "test query", k=5, document_ids=doc_ids
            )

        sql_text, params = _get_executed_sql_and_params(mock_session)

        assert "ANY(:document_ids)" in sql_text
        assert params["document_ids"] == doc_ids
        for doc_id in doc_ids:
            assert doc_id not in sql_text

    def test_sql_injection_payloads_not_in_sql_text(self):
        """Malicious document_ids never appear in the SQL text."""
        malicious_ids = ["'; DROP TABLE documents;--", "1' OR '1'='1"]

        with _patched_db() as mock_session:
            DocumentSearchService.text_search(
                "col-1", "query", k=5, document_ids=malicious_ids
            )

        sql_text, params = _get_executed_sql_and_params(mock_session)

        for payload in malicious_ids:
            assert payload not in sql_text
        assert params["document_ids"] == malicious_ids


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestDocumentIdsEdgeCases:
    """Edge cases for document_ids filtering."""

    def test_empty_list_does_not_add_filter(self):
        """An empty list is falsy and should not add the ANY clause."""
        with _patched_db() as mock_session:
            DocumentSearchService.text_search("col-1", "query", k=5, document_ids=[])

        sql_text, _ = _get_executed_sql_and_params(mock_session)
        assert "ANY(:document_ids)" not in sql_text

    def test_single_document_id(self):
        """A single-element list should still use parameterized binding."""
        with _patched_db() as mock_session:
            DocumentSearchService.text_search(
                "col-1", "query", k=5, document_ids=["only-one"]
            )

        sql_text, params = _get_executed_sql_and_params(mock_session)
        assert "ANY(:document_ids)" in sql_text
        assert params["document_ids"] == ["only-one"]
        assert "only-one" not in sql_text
