"""
Unit tests for DatabaseQueryActionNodeExecutor.

Tests cover:
- Successful query execution (using table_names / table_name → SELECT ... LIMIT)
- Config parsing from dict vs. dataclass instances
- Missing/invalid configuration handling
- Database connection failures
- Query execution failures
- State update shape (node_output.raw / node_output.structured)
- Database tracking and WebSocket notification calls
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.models.workflow import EnhancedNodeData
from backend.models.workflow.configs import DatabaseQueryActionConfig
from backend.services.nodes.executors.database.exceptions import (
    DatabaseConnectionError,
    QueryExecutionError,
)
from backend.services.nodes.executors.database.query_action_executor import (
    DatabaseQueryActionNodeExecutor,
)
from backend.services.workflow.state import WorkflowState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_execution_history_service():
    """Mock execution history service."""
    service = MagicMock()
    service.create_node_execution = MagicMock(return_value={"id": 123})
    service.complete_node_execution = MagicMock()
    service.mark_node_failed = MagicMock()
    service.get_node_execution_by_node_id = MagicMock(return_value=None)
    service.start_node_execution = MagicMock()
    service.get_node_execution_by_id = MagicMock(return_value=None)
    return service


@pytest.fixture
def mock_ws_notifier():
    """Mock WebSocket notifier."""
    notifier = MagicMock()
    notifier.on_node_start = AsyncMock()
    notifier.on_node_error = AsyncMock()
    notifier.on_node_complete = AsyncMock()
    return notifier


@pytest.fixture
def mock_connection_manager():
    """Mock DatabaseConnectionManager so no real DB/datasource calls happen."""
    manager = MagicMock()
    manager.get_connection_details = MagicMock(return_value=MagicMock())
    manager.create_psycopg2_connection = MagicMock(return_value=MagicMock())
    manager.execute_select_with_limit = MagicMock(return_value=[])
    return manager


@pytest.fixture
def query_action_executor(
    mock_execution_history_service, mock_ws_notifier, mock_connection_manager
):
    """Create DatabaseQueryActionNodeExecutor with mocked dependencies."""
    with patch(
        "backend.services.nodes.executors.database.query_action_executor.DatabaseConnectionManager",
        return_value=mock_connection_manager,
    ):
        executor = DatabaseQueryActionNodeExecutor(
            execution_history_service=mock_execution_history_service,
            ws_notifier=mock_ws_notifier,
            subgraph_executor=None,
            graph_manager=None,
        )
    return executor


@pytest.fixture
def basic_query_action_node():
    """Node configured with table_names (preferred field)."""
    return EnhancedNodeData(
        uniq_id="db_query_action_1",
        name="Test Database Query",
        type="DATABASE_QUERY_ACTION",
        database_query_action_config={
            "connection_id": "conn-123",
            "table_names": ["users"],
            "max_rows": 50,
        },
    )


@pytest.fixture
def workflow_state():
    """Basic workflow state with db tracking enabled."""
    return WorkflowState(
        messages=[],
        node_outputs={},
        execution_order=0,
        db_execution_id=999,
        execution_id="exec-1",
    )


@pytest.fixture
def graph_data():
    return MagicMock()


# ---------------------------------------------------------------------------
# Successful execution
# ---------------------------------------------------------------------------


class TestSuccessfulExecution:
    @pytest.mark.asyncio
    async def test_execute_returns_rows_from_table_names(
        self,
        query_action_executor,
        basic_query_action_node,
        workflow_state,
        graph_data,
        mock_connection_manager,
    ):
        """Query runs against table_names and returns rows in node_output."""
        rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        mock_connection_manager.execute_select_with_limit.return_value = rows

        result = await query_action_executor.execute(
            basic_query_action_node, workflow_state, graph_data, "exec-1"
        )

        structured = result["node_output"]["structured"]
        assert structured["success"] is True
        assert structured["rows_returned"] == 2
        assert structured["data"] == rows

    @pytest.mark.asyncio
    async def test_execute_builds_select_query_with_max_rows_limit(
        self,
        query_action_executor,
        basic_query_action_node,
        workflow_state,
        graph_data,
        mock_connection_manager,
    ):
        """The SELECT query should target the configured table and LIMIT."""
        await query_action_executor.execute(
            basic_query_action_node, workflow_state, graph_data, "exec-1"
        )

        args, _ = mock_connection_manager.execute_select_with_limit.call_args
        query = args[1]
        assert "SELECT * FROM users" in query
        assert "LIMIT 50" in query

    @pytest.mark.asyncio
    async def test_execute_builds_select_query_with_selected_columns(
        self,
        query_action_executor,
        workflow_state,
        graph_data,
        mock_connection_manager,
    ):
        """When selected_columns is set, only those columns are selected."""
        node = EnhancedNodeData(
            uniq_id="db_query_action_cols",
            name="Column Selection Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config={
                "connection_id": "conn-123",
                "table_names": ["customers"],
                "max_rows": 50,
                "selected_columns": ["CustomerID", "Name"],
            },
        )

        await query_action_executor.execute(node, workflow_state, graph_data, "exec-1")

        args, _ = mock_connection_manager.execute_select_with_limit.call_args
        query = args[1]
        assert 'SELECT "CustomerID", "Name" FROM customers' in query
        assert "LIMIT 50" in query

    @pytest.mark.asyncio
    async def test_execute_falls_back_to_deprecated_table_name(
        self,
        query_action_executor,
        workflow_state,
        graph_data,
        mock_connection_manager,
    ):
        """When table_names is empty, the deprecated table_name field is used."""
        node = EnhancedNodeData(
            uniq_id="db_query_action_2",
            name="Legacy Table Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config={
                "connection_id": "conn-123",
                "table_name": "legacy_orders",
                "max_rows": 100,
            },
        )

        await query_action_executor.execute(node, workflow_state, graph_data, "exec-1")

        args, _ = mock_connection_manager.execute_select_with_limit.call_args
        assert "SELECT * FROM legacy_orders" in args[1]

    @pytest.mark.asyncio
    async def test_execute_closes_connection_after_query(
        self,
        query_action_executor,
        basic_query_action_node,
        workflow_state,
        graph_data,
        mock_connection_manager,
    ):
        """Connection should always be closed after the query runs."""
        conn = mock_connection_manager.create_psycopg2_connection.return_value

        await query_action_executor.execute(
            basic_query_action_node, workflow_state, graph_data, "exec-1"
        )

        conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------


class TestConfigParsing:
    def test_get_config_accepts_dict(self, query_action_executor, basic_query_action_node):
        config = query_action_executor._get_config(basic_query_action_node)
        assert isinstance(config, DatabaseQueryActionConfig)
        assert config.connection_id == "conn-123"
        assert config.table_names == ["users"]
        assert config.max_rows == 50

    def test_get_config_accepts_dataclass_instance(self, query_action_executor):
        node = EnhancedNodeData(
            uniq_id="db_query_action_3",
            name="Dataclass Config Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config=DatabaseQueryActionConfig(
                connection_id="conn-xyz", table_names=["orders"]
            ),
        )
        config = query_action_executor._get_config(node)
        assert config.connection_id == "conn-xyz"
        assert config.table_names == ["orders"]

    def test_get_config_raises_when_missing(self, query_action_executor):
        node = EnhancedNodeData(
            uniq_id="db_query_action_4",
            name="No Config Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config=None,
        )
        with pytest.raises(ValueError, match="database_query_action_config is missing"):
            query_action_executor._get_config(node)

    def test_get_config_raises_when_connection_id_missing(self, query_action_executor):
        node = EnhancedNodeData(
            uniq_id="db_query_action_5",
            name="No Connection Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config={"table_names": ["users"]},
        )
        with pytest.raises(ValueError, match="connection_id is required"):
            query_action_executor._get_config(node)

    def test_get_config_ignores_unknown_dict_keys(self, query_action_executor):
        """Unknown keys in the dict config should be silently dropped."""
        node = EnhancedNodeData(
            uniq_id="db_query_action_6",
            name="Unknown Keys Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config={
                "connection_id": "conn-123",
                "table_names": ["users"],
                "not_a_real_field": "ignored",
            },
        )
        config = query_action_executor._get_config(node)
        assert config.connection_id == "conn-123"
        assert not hasattr(config, "not_a_real_field")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_execute_with_no_tables_returns_error_output(
        self, query_action_executor, workflow_state, graph_data
    ):
        node = EnhancedNodeData(
            uniq_id="db_query_action_7",
            name="No Table Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config={"connection_id": "conn-123"},
        )

        result = await query_action_executor.execute(node, workflow_state, graph_data, "exec-1")

        structured = result["node_output"]["structured"]
        assert structured["success"] is False
        assert structured["rows_returned"] == 0
        assert "No table specified" in structured["error"]

    @pytest.mark.asyncio
    async def test_execute_handles_connection_error(
        self,
        query_action_executor,
        basic_query_action_node,
        workflow_state,
        graph_data,
        mock_connection_manager,
    ):
        mock_connection_manager.create_psycopg2_connection.side_effect = (
            DatabaseConnectionError("conn-123", "connection refused")
        )

        result = await query_action_executor.execute(
            basic_query_action_node, workflow_state, graph_data, "exec-1"
        )

        structured = result["node_output"]["structured"]
        assert structured["success"] is False
        assert "connection refused" in structured["error"]

    @pytest.mark.asyncio
    async def test_execute_handles_query_execution_error(
        self,
        query_action_executor,
        basic_query_action_node,
        workflow_state,
        graph_data,
        mock_connection_manager,
    ):
        mock_connection_manager.execute_select_with_limit.side_effect = Exception(
            "syntax error"
        )

        result = await query_action_executor.execute(
            basic_query_action_node, workflow_state, graph_data, "exec-1"
        )

        structured = result["node_output"]["structured"]
        assert structured["success"] is False
        assert "Query execution failed" in structured["error"]

    @pytest.mark.asyncio
    async def test_execute_handles_unexpected_error(
        self, query_action_executor, workflow_state, graph_data
    ):
        """A missing connection_id raises ValueError, caught as unexpected error."""
        node = EnhancedNodeData(
            uniq_id="db_query_action_8",
            name="Bad Config Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config={"table_names": ["users"]},
        )

        result = await query_action_executor.execute(node, workflow_state, graph_data, "exec-1")

        structured = result["node_output"]["structured"]
        assert structured["success"] is False
        assert "Unexpected error" in structured["error"]

    @pytest.mark.asyncio
    async def test_execute_notifies_error_on_failure(
        self,
        query_action_executor,
        workflow_state,
        graph_data,
        mock_ws_notifier,
    ):
        node = EnhancedNodeData(
            uniq_id="db_query_action_9",
            name="Failing Node",
            type="DATABASE_QUERY_ACTION",
            database_query_action_config={"connection_id": "conn-123"},
        )

        await query_action_executor.execute(node, workflow_state, graph_data, "exec-1")

        mock_ws_notifier.on_node_error.assert_called()


# ---------------------------------------------------------------------------
# Tracking / notifications
# ---------------------------------------------------------------------------


class TestTrackingAndNotifications:
    @pytest.mark.asyncio
    async def test_execute_creates_and_completes_tracking_record(
        self,
        query_action_executor,
        basic_query_action_node,
        workflow_state,
        graph_data,
        mock_execution_history_service,
    ):
        await query_action_executor.execute(
            basic_query_action_node, workflow_state, graph_data, "exec-1"
        )

        mock_execution_history_service.create_node_execution.assert_called_once()
        mock_execution_history_service.complete_node_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_notifies_start(
        self,
        query_action_executor,
        basic_query_action_node,
        workflow_state,
        graph_data,
        mock_ws_notifier,
    ):
        await query_action_executor.execute(
            basic_query_action_node, workflow_state, graph_data, "exec-1"
        )

        mock_ws_notifier.on_node_start.assert_called()
