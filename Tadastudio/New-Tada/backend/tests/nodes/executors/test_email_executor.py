"""
Unit tests for EmailNodeExecutor.

Tests cover the fixes made to replace ExecutionEngine instantiation:
- InputBuilder usage for building node inputs (instead of ExecutionEngine)
- Email field extraction from workflow state
- Template variable substitution
- Database tracking and WebSocket notifications
- Error handling
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.workflow import EnhancedNodeData
from backend.services.nodes.executors.email import EmailNodeExecutor
from backend.services.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def enable_email_feature():
    """Email ships disabled ("coming soon"); these tests cover enabled behaviour.

    The disabled behaviour is covered by TestEmailFeatureDisabled below.
    """
    with patch("backend.services.nodes.executors.email.EMAIL_FEATURE_ENABLED", True):
        yield


@pytest.fixture
def mock_execution_history_service():
    """Mock execution history service."""
    service = MagicMock()
    # create_node_execution is sync and returns a dict with 'id'
    service.create_node_execution = MagicMock(return_value={"id": 123})
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
def email_executor(mock_execution_history_service, mock_ws_notifier):
    """Create EmailNodeExecutor instance with mocked dependencies."""
    return EmailNodeExecutor(
        execution_history_service=mock_execution_history_service,
        ws_notifier=mock_ws_notifier,
        subgraph_executor=None,
        graph_manager=None,
    )


@pytest.fixture
def basic_email_node():
    """Create a basic email node with static configuration."""
    node = EnhancedNodeData(
        uniq_id="email_1",
        name="Test Email",
        type="EMAIL_SEND",
        email_send_config={
            "to_address": "recipient@example.com",
            "to_source_mode": "static",
            "subject": "Test Subject",
            "subject_source_mode": "static",
            "body": "Test Body",
            "body_source_mode": "static",
            "from_address": "sender@example.com",
            "from_source_mode": "static",
            "reply_to": "",
            "reply_to_source_mode": "static",
            "use_html": False,
            "html_body": "",
            "use_template": False,
            "template_variables": {},
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
        self, email_executor, basic_email_node, workflow_state, graph_data
    ):
        """Test that _create_tracking_record uses InputBuilder correctly."""
        with patch("backend.services.io.InputBuilder") as mock_input_builder_class:
            # Setup mock
            mock_builder_instance = MagicMock()
            mock_builder_instance.build = MagicMock(return_value="Built input message")
            mock_input_builder_class.return_value = mock_builder_instance

            # Call the method
            await email_executor._create_tracking_record(
                basic_email_node, workflow_state, graph_data
            )

            # Verify InputBuilder was instantiated correctly (no arguments)
            mock_input_builder_class.assert_called_once_with()

            # Verify build was called with correct arguments
            mock_builder_instance.build.assert_called_once_with(
                basic_email_node, workflow_state, graph_data
            )

    @pytest.mark.asyncio
    async def test_input_builder_no_arguments(
        self, email_executor, basic_email_node, workflow_state, graph_data
    ):
        """Test that InputBuilder is called without field_extractor argument."""
        with patch("backend.services.io.InputBuilder") as mock_input_builder_class:
            mock_builder_instance = MagicMock()
            mock_builder_instance.build = MagicMock(return_value="Test input")
            mock_input_builder_class.return_value = mock_builder_instance

            await email_executor._create_tracking_record(
                basic_email_node, workflow_state, graph_data
            )

            # Should be called with no arguments (not with field_extractor)
            call_args = mock_input_builder_class.call_args
            assert call_args == ((), {}) or call_args == ((),)  # No args, no kwargs


# ---------------------------------------------------------------------------
# Test Email Field Extraction
# ---------------------------------------------------------------------------


class TestEmailFieldExtraction:
    """Test email field extraction from workflow state."""

    def test_static_field_extraction(self, email_executor, workflow_state, graph_data):
        """Test extracting static email fields."""
        config = email_executor._parse_config(
            {
                "to_address": "test@example.com",
                "to_source_mode": "static",
                "subject": "Test Subject",
                "subject_source_mode": "static",
                "body": "Test Body",
                "body_source_mode": "static",
                "from_address": "sender@example.com",
                "from_source_mode": "static",
                "reply_to": "",
                "reply_to_source_mode": "static",
                "use_html": False,
                "html_body": "",
                "use_template": False,
                "template_variables": {},
            }
        )

        fields = email_executor._extract_email_fields(
            config, workflow_state, graph_data
        )

        assert fields.to == "test@example.com"
        assert fields.subject == "Test Subject"
        assert fields.body == "Test Body"
        assert fields.from_address == "sender@example.com"

    def test_previous_node_field_extraction(self, email_executor, graph_data):
        """Test extracting fields from previous node output."""
        state = WorkflowState(
            messages=[],
            node_outputs={
                "node_1": {
                    "raw": "Previous output",
                    "execution_order": 1,
                }
            },
            execution_order=1,
        )

        config = email_executor._parse_config(
            {
                "to_address": "",
                "to_source_mode": "previous",
                "to_source_field_path": "",
                "subject": "Test",
                "subject_source_mode": "static",
                "body": "Test",
                "body_source_mode": "static",
                "from_address": "",
                "from_source_mode": "static",
                "reply_to": "",
                "reply_to_source_mode": "static",
                "use_html": False,
                "html_body": "",
                "use_template": False,
                "template_variables": {},
            }
        )

        fields = email_executor._extract_email_fields(config, state, graph_data)

        assert fields.to == "Previous output"

    def test_specific_node_field_extraction(self, email_executor, graph_data):
        """Test extracting fields from specific node output."""
        state = WorkflowState(
            messages=[],
            node_outputs={
                "source_node": {
                    "raw": "source@example.com",
                    "execution_order": 1,
                }
            },
            execution_order=2,
        )

        config = email_executor._parse_config(
            {
                "to_address": "",
                "to_source_mode": "specific",
                "to_source_node_id": "source_node",
                "to_source_field_path": "",
                "subject": "Test",
                "subject_source_mode": "static",
                "body": "Test",
                "body_source_mode": "static",
                "from_address": "",
                "from_source_mode": "static",
                "reply_to": "",
                "reply_to_source_mode": "static",
                "use_html": False,
                "html_body": "",
                "use_template": False,
                "template_variables": {},
            }
        )

        fields = email_executor._extract_email_fields(config, state, graph_data)

        assert fields.to == "source@example.com"


# ---------------------------------------------------------------------------
# Test Email Execution Flow
# ---------------------------------------------------------------------------


class TestEmailExecution:
    """Test email execution flow."""

    @pytest.mark.asyncio
    async def test_successful_email_execution(
        self, email_executor, basic_email_node, workflow_state, graph_data
    ):
        """Test successful email execution flow."""
        with patch(
            "backend.services.email.providers.factory.EmailServiceFactory.create_provider"
        ) as mock_factory:
            with patch("backend.services.io.InputBuilder"):
                # Setup mock provider
                mock_provider = MagicMock()
                mock_provider.domain = "example.com"
                mock_provider.send_email = AsyncMock(
                    return_value={"id": "msg123", "status": "sent"}
                )
                mock_factory.return_value = mock_provider

                # Execute
                result = await email_executor.execute(
                    basic_email_node, workflow_state, graph_data, "exec_123"
                )

                # Verify email was sent
                mock_provider.send_email.assert_called_once()

                # Verify result structure
                assert "node_output" in result
                assert result["node_output"]["raw"].startswith("Email sent to")
                assert result["node_output"]["structured"]["status"] == "sent"

    @pytest.mark.asyncio
    async def test_email_execution_with_error(
        self, email_executor, basic_email_node, workflow_state, graph_data
    ):
        """Test email execution with send error."""
        with patch(
            "backend.services.email.providers.factory.EmailServiceFactory.create_provider"
        ) as mock_factory:
            with patch("backend.services.io.InputBuilder"):
                # Setup mock provider to raise error
                mock_provider = MagicMock()
                mock_provider.domain = "example.com"
                mock_provider.send_email = AsyncMock(
                    side_effect=Exception("Send failed")
                )
                mock_factory.return_value = mock_provider

                # Execute
                result = await email_executor.execute(
                    basic_email_node, workflow_state, graph_data, "exec_123"
                )

                # Verify error handling
                assert "node_output" in result
                assert "failed" in result["node_output"]["raw"].lower()
                assert result["node_output"]["structured"]["status"] == "failed"


# ---------------------------------------------------------------------------
# Test Template Variable Substitution
# ---------------------------------------------------------------------------


class TestTemplateVariables:
    """Test template variable substitution."""

    def test_simple_template_substitution(self, email_executor, graph_data):
        """Test simple template variable substitution."""
        state = WorkflowState(messages=[], node_outputs={})

        email_fields = email_executor._apply_template_variables(
            email_fields=MagicMock(
                to="test@example.com",
                subject="Test",
                body="Hello {{name}}, welcome!",
                from_address="sender@example.com",
                reply_to="",
                html_body=None,
            ),
            template_variables={"name": "John Doe"},
            state=state,
            graph=graph_data,
        )

        assert email_fields.body == "Hello John Doe, welcome!"

    def test_multiple_template_substitutions(self, email_executor, graph_data):
        """Test multiple template variable substitutions."""
        state = WorkflowState(messages=[], node_outputs={})

        email_fields = email_executor._apply_template_variables(
            email_fields=MagicMock(
                to="test@example.com",
                subject="Test",
                body="Hello {{name}}, your order {{order_id}} is ready!",
                from_address="sender@example.com",
                reply_to="",
                html_body="<p>Hello {{name}}, order {{order_id}}</p>",
            ),
            template_variables={"name": "Alice", "order_id": "12345"},
            state=state,
            graph=graph_data,
        )

        assert email_fields.body == "Hello Alice, your order 12345 is ready!"
        assert email_fields.html_body == "<p>Hello Alice, order 12345</p>"


# ---------------------------------------------------------------------------
# Test Database Tracking
# ---------------------------------------------------------------------------


class TestDatabaseTracking:
    """Test database tracking functionality."""

    @pytest.mark.asyncio
    async def test_tracking_record_creation(
        self, email_executor, basic_email_node, workflow_state, graph_data
    ):
        """Test that tracking record is created with correct data."""
        with patch("backend.services.io.InputBuilder") as mock_builder_class:
            mock_builder = MagicMock()
            mock_builder.build = MagicMock(return_value="Test input message")
            mock_builder_class.return_value = mock_builder

            node_exec_id = await email_executor._create_tracking_record(
                basic_email_node, workflow_state, graph_data
            )

            # Verify tracking was created
            assert node_exec_id == 123  # From fixture

            # Verify create_node_execution was called
            email_executor.database_tracker.execution_history_service.create_node_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_tracking_completion(
        self, email_executor, basic_email_node, workflow_state
    ):
        """Test that tracking is completed with output data."""
        node_output = {
            "message_id": "msg123",
            "to": "test@example.com",
            "status": "sent",
        }

        await email_executor._complete_tracking(
            basic_email_node, workflow_state, 123, node_output, 1.5
        )

        # Verify completion was called
        email_executor.database_tracker.execution_history_service.complete_node_execution.assert_called_once()


# ---------------------------------------------------------------------------
# Test Configuration Validation
# ---------------------------------------------------------------------------


class TestConfigurationValidation:
    """Test email configuration validation."""

    def test_missing_config_raises_error(self, email_executor):
        """Test that missing email_send_config raises ValueError."""
        node = EnhancedNodeData(
            uniq_id="email_1",
            name="Test Email",
            type="EMAIL_SEND",
            email_send_config=None,
        )

        with pytest.raises(ValueError, match="Email send configuration is missing"):
            email_executor._validate_config(node)

    def test_valid_config_returns_config(self, email_executor, basic_email_node):
        """Test that valid config is returned."""
        config = email_executor._validate_config(basic_email_node)
        assert config is not None
        assert config == basic_email_node.email_send_config


# ---------------------------------------------------------------------------
# Test State Update Building
# ---------------------------------------------------------------------------


class TestStateUpdate:
    """Test state update building."""

    def test_build_state_update(self, email_executor, workflow_state):
        """Test building state update dictionary."""
        node_output = {
            "message_id": "msg123",
            "to": "test@example.com",
            "status": "sent",
        }

        email_fields = MagicMock(
            to="test@example.com",
            subject="Test",
            body="Test body",
            from_address="sender@example.com",
            reply_to="",
            html_body=None,
        )

        result = email_executor._build_state_update(
            node_output, workflow_state, email_fields
        )

        assert "node_output" in result
        assert result["node_output"]["raw"] == "Email sent to test@example.com"
        assert result["node_output"]["structured"] == node_output
        assert result["node_output"]["fields"] == node_output
        assert "execution_order" in result


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestEmailExecutorIntegration:
    """Integration tests for EmailNodeExecutor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(
        self, email_executor, basic_email_node, workflow_state, graph_data
    ):
        """Test complete execution flow from start to finish."""
        with patch(
            "backend.services.email.providers.factory.EmailServiceFactory.create_provider"
        ) as mock_factory:
            with patch("backend.services.io.InputBuilder") as mock_builder_class:
                # Setup mocks
                mock_provider = MagicMock()
                mock_provider.domain = "example.com"
                mock_provider.send_email = AsyncMock(
                    return_value={"id": "msg123", "status": "sent"}
                )
                mock_factory.return_value = mock_provider

                mock_builder = MagicMock()
                mock_builder.build = MagicMock(return_value="Input message")
                mock_builder_class.return_value = mock_builder

                # Execute
                result = await email_executor.execute(
                    basic_email_node, workflow_state, graph_data, "exec_123"
                )

                # Verify complete flow
                assert result is not None
                assert "node_output" in result
                assert result["node_output"]["structured"]["status"] == "sent"

                # Verify InputBuilder was used correctly
                mock_builder_class.assert_called()
                mock_builder.build.assert_called()

                # Verify email was sent
                mock_provider.send_email.assert_called_once()

                # Verify tracking
                email_executor.database_tracker.execution_history_service.create_node_execution.assert_called_once()
                email_executor.database_tracker.execution_history_service.complete_node_execution.assert_called_once()


class TestEmailFeatureDisabled:
    """Email is a coming-soon feature and is disabled by default."""

    @pytest.mark.asyncio
    async def test_execution_fails_when_feature_disabled(
        self, email_executor, basic_email_node, workflow_state, graph_data
    ):
        """No provider is contacted and the node reports the coming-soon reason."""
        with (
            patch(
                "backend.services.nodes.executors.email.EMAIL_FEATURE_ENABLED", False
            ),
            patch("backend.services.io.InputBuilder"),
            patch(
                "backend.services.email.providers.factory.EmailServiceFactory.create_provider"
            ) as mock_factory,
        ):
            result = await email_executor.execute(
                basic_email_node, workflow_state, graph_data, "exec_123"
            )

            mock_factory.assert_not_called()
            assert "coming soon" in str(result).lower()
