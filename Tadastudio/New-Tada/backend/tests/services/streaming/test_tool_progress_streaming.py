"""Tests for tool progress streaming in tool handlers.

These tests verify that tool handlers emit progress events correctly
during execution. Uses mock stream writers to capture emitted events.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# TestDocumentSearchProgressStreaming
# ---------------------------------------------------------------------------


class TestDocumentSearchProgressStreaming:
    """Tests for document search tool progress streaming."""

    @pytest.fixture
    def mock_document_search_dependencies(self):
        """Mock dependencies for document search handler."""
        with patch(
            "backend.tools.document_search.handlers.document_search_service"
        ) as mock_service:
            mock_service.search_multiple_collections.return_value = [
                {
                    "content": "Test document content",
                    "score": 0.85,
                    "metadata": {"doc_id": "doc-1"},
                }
            ]
            mock_service.get_all_chunks_for_document.return_value = []
            yield mock_service

    def test_emits_progress_during_search(
        self,
        mock_stream_writer,
        captured_events,
        mock_document_search_dependencies,
    ):
        """Should emit progress events during document search execution."""
        from backend.tools.document_search.handlers import execute_search
        from backend.tools.document_search.schemas import DocumentSearchConfig

        config = DocumentSearchConfig(
            collection_names=["collection-1"],
            search_k=3,
            search_type="similarity",
            similarity_threshold=0.7,
            include_metadata=True,
            citation_format="structured",
        )

        _result = execute_search(
            query="test query",
            config=config,
            call_id="call_doc_search_001",
        )

        # Should have emitted progress events
        progress_events = [
            e for e in captured_events if e["event_type"] == "tool_call_progress"
        ]

        assert len(progress_events) >= 2  # At least start and results formatting
        assert all(e["tool_name"] == "document_search" for e in progress_events)
        assert all(e["call_id"] == "call_doc_search_001" for e in progress_events)

    def test_no_error_when_call_id_empty(
        self,
        mock_stream_writer,
        captured_events,
        mock_document_search_dependencies,
    ):
        """Should handle empty call_id gracefully."""
        from backend.tools.document_search.handlers import execute_search
        from backend.tools.document_search.schemas import DocumentSearchConfig

        config = DocumentSearchConfig(
            collection_names=["collection-1"],
            search_k=3,
        )

        # Should not raise
        _result = execute_search(query="test", config=config, call_id="")

        # Events should still be emitted (with empty call_id)
        progress_events = [
            e for e in captured_events if e["event_type"] == "tool_call_progress"
        ]
        assert all(e["call_id"] == "" for e in progress_events)


# ---------------------------------------------------------------------------
# TestWebSearchProgressStreaming
# ---------------------------------------------------------------------------


class TestWebSearchProgressStreaming:
    """Tests for web search tool progress streaming."""

    @pytest.fixture
    def mock_web_search_dependencies(self):
        """Mock dependencies for web search handler."""
        with patch(
            "backend.tools.web_search.handlers.web_search_service"
        ) as mock_service:
            mock_service.search_duckduckgo.return_value = [
                {"title": "Test", "snippet": "Test snippet", "url": "https://test.com"}
            ]
            mock_service.format_results_as_text.return_value = "Formatted results"
            yield mock_service

    def test_emits_progress_during_search(
        self,
        mock_stream_writer,
        captured_events,
        mock_web_search_dependencies,
    ):
        """Should emit progress events during web search execution."""
        from backend.tools.web_search.handlers import handle_web_search_execution
        from backend.tools.web_search.schemas import WebSearchConfig

        config = WebSearchConfig(
            search_provider="duckduckgo",
            max_results=5,
        )

        _result = handle_web_search_execution(
            query="test query",
            config=config,
            search_impl_func=MagicMock(),
            call_id="call_web_search_001",
        )

        # Should have emitted progress events
        progress_events = [
            e for e in captured_events if e["event_type"] == "tool_call_progress"
        ]

        assert len(progress_events) >= 2
        assert all(e["tool_name"] == "web_search" for e in progress_events)
        assert all(e["call_id"] == "call_web_search_001" for e in progress_events)

        # Verify progress percentages increase
        progress_values = [e["progress"] for e in progress_events]
        assert progress_values == sorted(progress_values)  # Should be ascending


# ---------------------------------------------------------------------------
# TestDatabaseQueryProgressStreaming
# ---------------------------------------------------------------------------


class TestDatabaseQueryProgressStreaming:
    """Tests for database query tool progress streaming."""

    @pytest.fixture
    def mock_database_query_dependencies(self):
        """Mock dependencies for database query handler."""
        with (
            patch(
                "backend.tools.database_query.handlers.execute_query_with_async_handling"
            ) as mock_exec,
            patch(
                "backend.tools.database_query.handlers.format_query_result"
            ) as mock_format,
        ):
            mock_exec.return_value = {
                "rows": [{"id": 1, "name": "test"}],
                "columns": ["id", "name"],
            }
            mock_format.return_value = "| id | name |\n| 1 | test |"
            yield {"execute": mock_exec, "format": mock_format}

    def test_emits_progress_during_query(
        self,
        mock_stream_writer,
        captured_events,
        mock_database_query_dependencies,
    ):
        """Should emit progress events during database query execution."""
        from backend.tools.database_query.handlers import handle_query_execution

        _result = handle_query_execution(
            db=MagicMock(),
            query="SELECT * FROM users",
            connection_id="conn-1",
            table_names=["users"],
            allowed_operations=["SELECT"],
            max_rows=100,
            timeout_seconds=30,
            enable_read_only=True,
            return_format="markdown",
            include_schema=False,
            call_id="call_db_query_001",
        )

        # Should have emitted progress events
        progress_events = [
            e for e in captured_events if e["event_type"] == "tool_call_progress"
        ]

        assert len(progress_events) >= 2
        assert all(e["tool_name"] == "database_query" for e in progress_events)
        assert all(e["call_id"] == "call_db_query_001" for e in progress_events)


# ---------------------------------------------------------------------------
# TestHttpRequestProgressStreaming
# ---------------------------------------------------------------------------


class TestHttpRequestProgressStreaming:
    """Tests for HTTP request tool progress streaming."""

    @pytest.fixture
    def mock_http_request_dependencies(self):
        """Mock dependencies for HTTP request handler."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"result": "success"}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.text = '{"result": "success"}'

        with (
            patch(
                "backend.tools.http_request.handlers.execute_request_with_retries"
            ) as mock_exec,
            patch(
                "backend.tools.http_request.handlers.process_response"
            ) as mock_process,
            patch(
                "backend.tools.http_request.handlers.format_response_output"
            ) as mock_format,
        ):
            mock_exec.return_value = (mock_response, None)
            mock_process.return_value = ({"result": "success"}, {})
            mock_format.return_value = '{"result": "success"}'
            yield {
                "execute": mock_exec,
                "process": mock_process,
                "format": mock_format,
                "response": mock_response,
            }

    def test_emits_progress_during_request(
        self,
        mock_stream_writer,
        captured_events,
        mock_http_request_dependencies,
    ):
        """Should emit progress events during HTTP request execution."""
        from backend.tools.http_request.handlers import handle_http_request_execution
        from backend.tools.http_request.schemas import HttpRequestConfig, AuthConfig

        config = HttpRequestConfig(
            url_template="https://api.test.com/data",
            method="GET",
            headers={},
            query_params={},
            parameter_schema={},
            success_status_codes=[200],
        )

        auth_config = AuthConfig(auth_type="none")

        _result = handle_http_request_execution(
            kwargs={},
            config=config,
            auth_config=auth_config,
            oauth2_config=None,
            signing_config=None,
            rate_limiter=None,
            circuit_breaker=None,
            session=None,
            cache={},
            cache_ttl=300,
            http_request_impl_func=MagicMock(),
            call_id="call_http_001",
        )

        # Should have emitted progress events
        progress_events = [
            e for e in captured_events if e["event_type"] == "tool_call_progress"
        ]

        assert len(progress_events) >= 2
        assert all(e["tool_name"] == "http_request" for e in progress_events)
        assert all(e["call_id"] == "call_http_001" for e in progress_events)


# ---------------------------------------------------------------------------
# TestProgressEventContent
# ---------------------------------------------------------------------------


class TestProgressEventContent:
    """Tests for progress event content and structure."""

    def test_progress_percentage_in_valid_range(
        self, mock_stream_writer, captured_events
    ):
        """Progress percentages should be in 0-100 range."""
        from backend.services.streaming import streaming_emitter

        # Emit various progress values
        streaming_emitter.emit_tool_progress("call_1", "tool", "msg", progress=0)
        streaming_emitter.emit_tool_progress("call_1", "tool", "msg", progress=50)
        streaming_emitter.emit_tool_progress("call_1", "tool", "msg", progress=100)

        for event in captured_events:
            assert 0 <= event["progress"] <= 100

    def test_progress_message_descriptive(self, mock_stream_writer, captured_events):
        """Progress messages should be descriptive strings."""
        from backend.services.streaming import streaming_emitter

        messages = [
            "Preparing request...",
            "Executing GET request...",
            "Processing response...",
            "Formatting results...",
        ]

        for msg in messages:
            streaming_emitter.emit_tool_progress("call_1", "tool", msg, progress=25)

        assert len(captured_events) == 4
        for event in captured_events:
            assert isinstance(event["message"], str)
            assert len(event["message"]) > 0
