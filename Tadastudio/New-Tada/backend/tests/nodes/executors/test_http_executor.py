"""
Unit tests for HttpNodeExecutor.

Tests cover the fixes made to replace ExecutionEngine instantiation:
- InputBuilder usage for building node inputs (instead of ExecutionEngine)
- TemplateProcessor usage for template replacement
- MappingValueExtractor usage for parameter/header/body mappings
- HTTP request execution with various configurations
- Error handling and retries
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from backend.models.workflow import EnhancedNodeData
from backend.services.nodes.executors.http import HttpNodeExecutor
from backend.services.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_execution_history_service():
    """Mock execution history service."""
    service = MagicMock()
    # create_node_execution is sync and returns a dict with 'id'
    service.create_node_execution = MagicMock(return_value={"id": 456})
    # complete_node_execution is sync (not async)
    service.complete_node_execution = MagicMock()
    service.mark_node_failed = MagicMock()
    # Additional methods used by database tracker
    service.get_node_execution_by_node_id = MagicMock(return_value=None)
    service.start_node_execution = MagicMock()
    service.get_node_execution_by_id = MagicMock(return_value=None)
    return service


@pytest.fixture
def mock_ws_notifier():
    """Mock WebSocket notifier."""
    notifier = MagicMock()
    notifier.send_execution_update = AsyncMock()
    return notifier


@pytest.fixture
def http_executor(mock_execution_history_service, mock_ws_notifier):
    """Create HttpNodeExecutor instance with mocked dependencies."""
    return HttpNodeExecutor(
        execution_history_service=mock_execution_history_service,
        ws_notifier=mock_ws_notifier,
        subgraph_executor=None,
        graph_manager=None,
    )


@pytest.fixture
def basic_http_node():
    """Create a basic HTTP request node."""
    node = EnhancedNodeData(
        uniq_id="http_1",
        name="Test HTTP Request",
        type="HTTP_REQUEST_ACTION",
        http_request_action_config={
            "url": "https://api.example.com/endpoint",
            "method": "GET",
            "headers": {},
            "body_type": "none",
            "auth_type": "none",
            "timeout": 30,
            "max_retries": 3,
            "success_status_codes": [200, 201],
        },
    )
    return node


@pytest.fixture
def workflow_state():
    """Create a basic workflow state."""
    return WorkflowState(
        messages=[],
        node_outputs={},
        execution_order=0,
        db_execution_id=999,  # Required for database tracking
    )


@pytest.fixture
def graph_data():
    """Create basic graph data."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Test InputBuilder Usage (Primary Fix Validation)
# ---------------------------------------------------------------------------


class TestInputBuilderUsage:
    """Test that InputBuilder is correctly used instead of ExecutionEngine."""

    @pytest.mark.asyncio
    async def test_create_tracking_uses_input_builder(
        self, http_executor, basic_http_node, workflow_state, graph_data
    ):
        """Test that _create_tracking_record uses InputBuilder correctly."""
        with patch("backend.services.io.InputBuilder") as mock_input_builder_class:
            # Setup mock
            mock_builder_instance = MagicMock()
            mock_builder_instance.build = MagicMock(return_value="Built input message")
            mock_input_builder_class.return_value = mock_builder_instance

            # Call the method
            await http_executor._create_tracking_record(
                basic_http_node, workflow_state, graph_data
            )

            # Verify InputBuilder was instantiated correctly (no arguments)
            mock_input_builder_class.assert_called_once_with()

            # Verify build was called with correct arguments
            mock_builder_instance.build.assert_called_once_with(
                basic_http_node, workflow_state, graph_data
            )

    @pytest.mark.asyncio
    async def test_complete_tracking_uses_input_builder(
        self, http_executor, basic_http_node, workflow_state, graph_data
    ):
        """Test that _complete_tracking uses InputBuilder correctly."""
        with patch("backend.services.io.InputBuilder") as mock_input_builder_class:
            # Setup mock
            mock_builder_instance = MagicMock()
            mock_builder_instance.build = MagicMock(return_value="Built input message")
            mock_input_builder_class.return_value = mock_builder_instance

            node_output = {"status_code": 200, "data": "test"}

            # Call the method
            await http_executor._complete_tracking(
                basic_http_node, workflow_state, 456, node_output, 1.5, graph_data
            )

            # Verify InputBuilder was instantiated correctly
            mock_input_builder_class.assert_called_once_with()
            mock_builder_instance.build.assert_called_once_with(
                basic_http_node, workflow_state, graph_data
            )


# ---------------------------------------------------------------------------
# Test TemplateProcessor Usage
# ---------------------------------------------------------------------------


class TestTemplateProcessorUsage:
    """Test that TemplateProcessor is correctly used for template replacement."""

    def test_build_body_uses_template_processor(self, http_executor, workflow_state):
        """Test that _build_body uses TemplateProcessor for templates."""
        with patch("backend.services.io.TemplateProcessor") as mock_template_class:
            # Setup mock
            mock_processor = MagicMock()
            mock_processor.process = MagicMock(return_value="Processed template")
            mock_template_class.return_value = mock_processor

            headers = {}
            # Call with template
            result = http_executor._process_body(
                method="POST",
                body_template="Hello {{name}}",
                body_mappings=[],
                state=workflow_state,
                headers=headers,
            )

            # Verify TemplateProcessor was used
            mock_template_class.assert_called_once()
            mock_processor.process.assert_called_once_with(
                "Hello {{name}}", workflow_state
            )
            assert result == "Processed template"


# ---------------------------------------------------------------------------
# Test MappingValueExtractor Usage
# ---------------------------------------------------------------------------


class TestMappingValueExtractorUsage:
    """Test that MappingValueExtractor is correctly used for mappings."""

    def test_extract_mapping_value_uses_extractor(self, http_executor, workflow_state):
        """Test that _extract_mapping_value uses MappingValueExtractor."""
        with patch("backend.services.io.MappingValueExtractor") as mock_extractor_class:
            # Setup mock
            mock_extractor = MagicMock()
            mock_extractor.extract = MagicMock(return_value="extracted_value")
            mock_extractor_class.return_value = mock_extractor

            param_mapping = {
                "parameter_name": "user_id",
                "source_mode": "specific",
                "source_node_id": "node_1",
                "source_field_path": "id",
                "static_value": "",
                "default_value": "",
            }

            # Call the method
            param_name, value = http_executor._extract_mapping_value(
                param_mapping, workflow_state
            )

            # Verify MappingValueExtractor was used
            mock_extractor_class.assert_called_once()
            mock_extractor.extract.assert_called_once()

            # Verify the call arguments
            call_kwargs = mock_extractor.extract.call_args[1]
            assert call_kwargs["source_mode"] == "specific"
            assert call_kwargs["state"] == workflow_state
            assert call_kwargs["source_node_id"] == "node_1"
            assert call_kwargs["source_field_path"] == "id"

            assert param_name == "user_id"
            assert value == "extracted_value"

    def test_extract_header_mapping_value_uses_extractor(
        self, http_executor, workflow_state
    ):
        """Test that _extract_header_mapping_value uses MappingValueExtractor."""
        with patch("backend.services.io.MappingValueExtractor") as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_extractor.extract = MagicMock(return_value="header_value")
            mock_extractor_class.return_value = mock_extractor

            header_mapping = {
                "header_name": "X-API-Key",
                "source_mode": "static",
                "static_value": "secret123",
                "default_value": "",
            }

            header_name, value = http_executor._extract_header_mapping_value(
                header_mapping, workflow_state
            )

            mock_extractor_class.assert_called_once()
            mock_extractor.extract.assert_called_once()
            assert header_name == "X-API-Key"
            assert value == "header_value"

    def test_extract_body_mapping_value_uses_extractor(
        self, http_executor, workflow_state
    ):
        """Test that _extract_body_mapping_value uses MappingValueExtractor."""
        with patch("backend.services.io.MappingValueExtractor") as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_extractor.extract = MagicMock(return_value="body_value")
            mock_extractor_class.return_value = mock_extractor

            body_mapping = {
                "field_name": "email",
                "source_mode": "previous",
                "static_value": "",
                "default_value": "",
            }

            field_name, value = http_executor._extract_body_mapping_value(
                body_mapping, workflow_state
            )

            mock_extractor_class.assert_called_once()
            mock_extractor.extract.assert_called_once()
            assert field_name == "email"
            assert value == "body_value"


# ---------------------------------------------------------------------------
# Test HTTP Request Execution
# ---------------------------------------------------------------------------


class TestHttpRequestExecution:
    """Test HTTP request execution."""

    @pytest.mark.asyncio
    async def test_successful_get_request(
        self, http_executor, basic_http_node, workflow_state, graph_data
    ):
        """Test successful GET request execution."""
        with patch(
            "backend.services.nodes.executors.http.requests.request"
        ) as mock_request:
            with patch("backend.services.io.InputBuilder"):
                # Setup mock response
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"result": "success"}
                mock_request.return_value = mock_response

                # Execute
                result = await http_executor.execute(
                    basic_http_node, workflow_state, graph_data, "exec_123"
                )

                # Verify request was made
                mock_request.assert_called_once()
                assert mock_request.call_args[1]["method"] == "GET"

                # Verify result
                assert "node_output" in result
                assert result["node_output"]["structured"]["status_code"] == 200

    @pytest.mark.asyncio
    async def test_post_request_with_json_body(
        self, http_executor, workflow_state, graph_data
    ):
        """Test POST request with JSON body."""
        node = EnhancedNodeData(
            uniq_id="http_post",
            name="POST Request",
            type="HTTP_REQUEST_ACTION",
            http_request_action_config={
                "url": "https://api.example.com/users",
                "method": "POST",
                "body_type": "mappings",
                "body_mappings": [
                    {
                        "field_name": "name",
                        "source_mode": "static",
                        "static_value": "John Doe",
                        "default_value": "",
                    }
                ],
                "headers": {},
                "auth_type": "none",
                "timeout": 30,
                "max_retries": 3,
                "success_status_codes": [200, 201],
            },
        )

        with patch(
            "backend.services.nodes.executors.http.requests.request"
        ) as mock_request:
            with patch("backend.services.io.InputBuilder"):
                with patch(
                    "backend.services.io.MappingValueExtractor"
                ) as mock_extractor_class:
                    # Setup mocks
                    mock_response = MagicMock()
                    mock_response.status_code = 201
                    mock_response.json.return_value = {"id": 123, "name": "John Doe"}
                    mock_request.return_value = mock_response

                    mock_extractor = MagicMock()
                    mock_extractor.extract = MagicMock(return_value="John Doe")
                    mock_extractor_class.return_value = mock_extractor

                    # Execute
                    result = await http_executor.execute(
                        node, workflow_state, graph_data, "exec_123"
                    )

                    # Verify request
                    assert mock_request.call_args[1]["method"] == "POST"
                    assert result["node_output"]["structured"]["status_code"] == 201

    @pytest.mark.asyncio
    async def test_request_with_retry_on_timeout(self, http_executor, basic_http_node):
        """Test request retry on timeout."""
        request_spec = MagicMock()
        request_spec.method = "GET"
        request_spec.url = "https://api.example.com"
        request_spec.headers = {}
        request_spec.body = None
        request_spec.auth = None

        with patch(
            "backend.services.nodes.executors.http.requests.request"
        ) as mock_request:
            with patch(
                "backend.services.nodes.executors.http.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                # First attempt times out, second succeeds
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"data": "success"}

                mock_request.side_effect = [
                    requests.exceptions.Timeout("Timeout"),
                    mock_response,
                ]

                # Execute with retries
                result = await http_executor._execute_request(
                    request_spec, max_retries=3, timeout_seconds=30
                )

                # Verify retry happened
                assert mock_request.call_count == 2
                assert result["success"] is True


# ---------------------------------------------------------------------------
# Test Authentication
# ---------------------------------------------------------------------------


class TestAuthentication:
    """Test authentication setup."""

    def test_bearer_token_auth(self, http_executor):
        """Test Bearer token authentication."""
        headers = {}
        auth_config = {"token": "secret_token"}

        result = http_executor._setup_auth("bearer", auth_config, headers)

        assert headers["Authorization"] == "Bearer secret_token"
        assert result is None  # Bearer auth uses headers, not HTTPBasicAuth

    def test_api_key_auth(self, http_executor):
        """Test API key authentication."""
        headers = {}
        auth_config = {"header": "X-API-Key", "key": "my_api_key"}

        result = http_executor._setup_auth("api_key", auth_config, headers)

        assert headers["X-API-Key"] == "my_api_key"
        assert result is None

    def test_basic_auth(self, http_executor):
        """Test basic authentication."""
        headers = {}
        auth_config = {"username": "user", "password": "pass"}

        result = http_executor._setup_auth("basic", auth_config, headers)

        assert result is not None
        assert result.username == "user"
        assert result.password == "pass"


# ---------------------------------------------------------------------------
# Test Error Handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_request_failure_after_retries(self, http_executor):
        """Test request failure after all retries exhausted."""
        request_spec = MagicMock()
        request_spec.method = "GET"
        request_spec.url = "https://api.example.com"
        request_spec.headers = {}
        request_spec.body = None
        request_spec.auth = None

        with patch(
            "backend.services.nodes.executors.http.requests.request"
        ) as mock_request:
            with patch(
                "backend.services.nodes.executors.http.asyncio.sleep",
                new_callable=AsyncMock,
            ):
                # All attempts fail
                mock_request.side_effect = requests.exceptions.RequestException(
                    "Connection error"
                )

                # Execute should raise after retries
                with pytest.raises(Exception, match="HTTP request failed after"):
                    await http_executor._execute_request(
                        request_spec, max_retries=2, timeout_seconds=30
                    )

                # Verify all retries were attempted
                assert mock_request.call_count == 2

    def test_invalid_status_code_raises_error(self, http_executor):
        """Test that invalid status code raises error."""
        response_data = {
            "response": MagicMock(status_code=404, text="Not found"),
            "success": True,
        }

        with pytest.raises(Exception, match="HTTP 404"):
            http_executor._handle_response(
                response_data, response_path=None, success_status_codes=[200, 201]
            )


# ---------------------------------------------------------------------------
# Test Response Processing
# ---------------------------------------------------------------------------


class TestResponseProcessing:
    """Test response data processing."""

    def test_json_response_parsing(self, http_executor):
        """Test parsing JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"user": {"name": "Alice", "id": 123}}

        response_data = {"response": mock_response, "success": True}

        result = http_executor._handle_response(
            response_data, response_path=None, success_status_codes=[200]
        )

        assert result["status_code"] == 200
        assert result["data"]["user"]["name"] == "Alice"

    def test_response_path_extraction(self, http_executor):
        """Test extracting specific path from JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"user": {"name": "Bob", "id": 456}}}

        response_data = {"response": mock_response, "success": True}

        result = http_executor._handle_response(
            response_data, response_path="data.user", success_status_codes=[200]
        )

        assert result["data"]["name"] == "Bob"
        assert result["data"]["id"] == 456


# ---------------------------------------------------------------------------
# Test Body Building
# ---------------------------------------------------------------------------


class TestBodyBuilding:
    """Test HTTP body building."""

    def test_no_body(self, http_executor, workflow_state):
        """Test building request with no body."""
        headers = {}
        result = http_executor._process_body(
            method="GET",
            body_template=None,
            body_mappings=[],
            state=workflow_state,
            headers=headers,
        )

        assert result is None

    def test_json_body_from_mappings(self, http_executor, workflow_state):
        """Test building JSON body from mappings."""
        with patch("backend.services.io.MappingValueExtractor") as mock_extractor_class:
            mock_extractor = MagicMock()
            mock_extractor.extract = MagicMock(
                side_effect=["Alice", "alice@example.com"]
            )
            mock_extractor_class.return_value = mock_extractor

            body_mappings = [
                {
                    "field_name": "name",
                    "source_mode": "static",
                    "static_value": "Alice",
                },
                {
                    "field_name": "email",
                    "source_mode": "static",
                    "static_value": "alice@example.com",
                },
            ]

            headers = {}
            result = http_executor._process_body(
                method="POST",
                body_template=None,
                body_mappings=body_mappings,
                state=workflow_state,
                headers=headers,
            )

            import json

            parsed = json.loads(result)
            assert parsed["name"] == "Alice"
            assert parsed["email"] == "alice@example.com"


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestHttpExecutorIntegration:
    """Integration tests for HttpNodeExecutor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(
        self, http_executor, basic_http_node, workflow_state, graph_data
    ):
        """Test complete HTTP execution flow."""
        with patch(
            "backend.services.nodes.executors.http.requests.request"
        ) as mock_request:
            with patch("backend.services.io.InputBuilder") as mock_builder_class:
                # Setup mocks
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"result": "success", "data": "test"}
                mock_request.return_value = mock_response

                mock_builder = MagicMock()
                mock_builder.build = MagicMock(return_value="Input message")
                mock_builder_class.return_value = mock_builder

                # Execute
                result = await http_executor.execute(
                    basic_http_node, workflow_state, graph_data, "exec_123"
                )

                # Verify complete flow
                assert result is not None
                assert "node_output" in result
                assert result["node_output"]["structured"]["status_code"] == 200

                # Verify InputBuilder was used correctly
                assert mock_builder_class.call_count >= 1
                assert mock_builder.build.call_count >= 1

                # Verify request was made
                mock_request.assert_called_once()

                # Verify tracking
                http_executor.database_tracker.execution_history_service.create_node_execution.assert_called_once()
                http_executor.database_tracker.execution_history_service.complete_node_execution.assert_called_once()


# ---------------------------------------------------------------------------
# Test Panel Field-Name Compatibility and Value Chaining
# ---------------------------------------------------------------------------


class TestPanelFieldNames:
    """Mappings saved by the properties panel use parameter_name."""

    def test_header_mapping_uses_parameter_name(self, http_executor, workflow_state):
        """Panel saves header mappings with parameter_name, not header_name."""
        header_name, value = http_executor._extract_header_mapping_value(
            {
                "parameter_name": "clientid",
                "source_mode": "static",
                "static_value": "abc123",
            },
            workflow_state,
        )

        assert header_name == "clientid"
        assert value == "abc123"

    def test_body_mapping_uses_parameter_name(self, http_executor, workflow_state):
        """Panel saves body mappings with parameter_name, not field_name."""
        field_name, value = http_executor._extract_body_mapping_value(
            {
                "parameter_name": "grant_type",
                "source_mode": "static",
                "static_value": "client_credentials",
            },
            workflow_state,
        )

        assert field_name == "grant_type"
        assert value == "client_credentials"

    def test_legacy_field_names_still_supported(self, http_executor, workflow_state):
        """Legacy header_name/field_name keys keep working."""
        header_name, _ = http_executor._extract_header_mapping_value(
            {"header_name": "X-Legacy", "source_mode": "static", "static_value": "v"},
            workflow_state,
        )
        field_name, _ = http_executor._extract_body_mapping_value(
            {"field_name": "legacy", "source_mode": "static", "static_value": "v"},
            workflow_state,
        )

        assert header_name == "X-Legacy"
        assert field_name == "legacy"

    def test_api_key_auth_with_panel_field_names(self, http_executor):
        """Panel saves API key auth as header_name/api_key."""
        headers = {}

        http_executor._setup_auth(
            "api_key", {"header_name": "X-IBM-Client-Id", "api_key": "k123"}, headers
        )

        assert headers["X-IBM-Client-Id"] == "k123"


class TestValueChaining:
    """Values produced by an upstream node can be reused downstream."""

    @pytest.fixture
    def token_state(self):
        """State holding an OAuth token response from a previous node."""
        return WorkflowState(
            messages=[],
            node_outputs={
                "token_node": {
                    "success": True,
                    "status_code": 200,
                    "data": {"access_token": "tok_abc", "expires_in": 3600},
                }
            },
            execution_order=1,
            db_execution_id=999,
        )

    def test_auth_config_resolves_templates(self, http_executor, token_state):
        """Bearer token can reference an upstream value via {{access_token}}."""
        resolved = http_executor._resolve_auth_config_templates(
            {"token": "{{access_token}}"}, token_state
        )

        assert resolved["token"] == "tok_abc"

    def test_auth_config_without_templates_is_unchanged(
        self, http_executor, token_state
    ):
        """Plain auth values pass through untouched."""
        resolved = http_executor._resolve_auth_config_templates(
            {"token": "literal_token"}, token_state
        )

        assert resolved["token"] == "literal_token"

    def test_header_mapping_from_specific_node(self, http_executor, token_state):
        """'Specific Node' mode pulls a field from an upstream node output."""
        header_name, value = http_executor._extract_header_mapping_value(
            {
                "parameter_name": "Authorization",
                "source_mode": "specific",
                "source_node_id": "token_node",
                "source_field_path": "access_token",
            },
            token_state,
        )

        assert header_name == "Authorization"
        assert value == "tok_abc"

    def test_header_mapping_from_custom_template(self, http_executor, token_state):
        """'Custom Template' mode renders {{variable}} against state."""
        header_name, value = http_executor._extract_header_mapping_value(
            {
                "parameter_name": "Authorization",
                "source_mode": "template",
                "custom_template": "Bearer {{access_token}}",
            },
            token_state,
        )

        assert header_name == "Authorization"
        assert value == "Bearer tok_abc"

    def test_body_mapping_from_custom_template(self, http_executor, token_state):
        """Body fields also support custom templates."""
        field_name, value = http_executor._extract_body_mapping_value(
            {
                "parameter_name": "token",
                "source_mode": "template",
                "custom_template": "{{access_token}}",
            },
            token_state,
        )

        assert field_name == "token"
        assert value == "tok_abc"

    def test_field_source_mode_behaves_like_specific(self, http_executor, token_state):
        """'Specific Field' mode resolves the same way as 'Specific Node'."""
        _, value = http_executor._extract_mapping_value(
            {
                "parameter_name": "token",
                "source_mode": "field",
                "source_node_id": "token_node",
                "source_field_path": "access_token",
            },
            token_state,
        )

        assert value == "tok_abc"
