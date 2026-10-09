"""Tests for database_tracker sub-agent execution recording.

Tests verify that each sub-agent invocation creates a new database record,
allowing multiple executions of the same sub-agent to be tracked separately.
"""

import pytest
from unittest.mock import patch, MagicMock

from backend.services.subgraph.agent.database_tracker import (
    create_agent_execution_record,
    complete_agent_execution_record,
    fail_agent_execution_record,
)


class TestCreateAgentExecutionRecord:
    """Tests for create_agent_execution_record function."""

    @pytest.mark.asyncio
    async def test_creates_new_record_for_each_call(self, sub_agent_node):
        """Should create a new record for each sub-agent invocation.

        This is the key test for the multiple sub-agent execution fix.
        Previously, the function would reuse an existing record if one
        existed for the same node_id, causing data to be overwritten.
        """
        mock_create = MagicMock(return_value={"id": "new-exec-id-1"})
        mock_start = MagicMock()

        with patch(
            "backend.services.subgraph.agent.database_tracker.ExecutionHistoryService"
        ) as mock_service:
            mock_service.create_node_execution = mock_create
            mock_service.start_node_execution = mock_start

            # First call
            result1 = await create_agent_execution_record(
                agent_node=sub_agent_node,
                parent_db_execution_id="parent-exec-123",
                parent_node_id="orchestrator-001",
                parent_node_execution_id="node-exec-789",
                execution_order=1,
                task_description="Task 1: Calculate 5^2 + 7",
            )

            # Second call with same agent node (different task)
            mock_create.return_value = {"id": "new-exec-id-2"}
            result2 = await create_agent_execution_record(
                agent_node=sub_agent_node,
                parent_db_execution_id="parent-exec-123",
                parent_node_id="orchestrator-001",
                parent_node_execution_id="node-exec-789",
                execution_order=2,
                task_description="Task 2: Calculate 11 * 7 - 3",
            )

            # Third call
            mock_create.return_value = {"id": "new-exec-id-3"}
            result3 = await create_agent_execution_record(
                agent_node=sub_agent_node,
                parent_db_execution_id="parent-exec-123",
                parent_node_id="orchestrator-001",
                parent_node_execution_id="node-exec-789",
                execution_order=3,
                task_description="Task 3: Reverse binary of 19",
            )

            # Should have called create_node_execution three times
            assert mock_create.call_count == 3
            assert result1 == "new-exec-id-1"
            assert result2 == "new-exec-id-2"
            assert result3 == "new-exec-id-3"

            # Verify each call had the correct task description
            calls = mock_create.call_args_list
            assert calls[0][1]["input_data"]["task"] == "Task 1: Calculate 5^2 + 7"
            assert calls[1][1]["input_data"]["task"] == "Task 2: Calculate 11 * 7 - 3"
            assert calls[2][1]["input_data"]["task"] == "Task 3: Reverse binary of 19"

    @pytest.mark.asyncio
    async def test_returns_none_without_parent_db_execution_id(self, sub_agent_node):
        """Should return None if no parent_db_execution_id provided."""
        result = await create_agent_execution_record(
            agent_node=sub_agent_node,
            parent_db_execution_id=None,
            parent_node_id="orchestrator-001",
            parent_node_execution_id="node-exec-789",
            execution_order=1,
            task_description="Task",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_stores_correct_metadata(self, sub_agent_node):
        """Should store task description and sub-agent metadata correctly."""
        mock_create = MagicMock(return_value={"id": "exec-id"})

        with patch(
            "backend.services.subgraph.agent.database_tracker.ExecutionHistoryService"
        ) as mock_service:
            mock_service.create_node_execution = mock_create
            mock_service.start_node_execution = MagicMock()

            await create_agent_execution_record(
                agent_node=sub_agent_node,
                parent_db_execution_id="parent-123",
                parent_node_id="orchestrator-001",
                parent_node_execution_id="node-exec-789",
                execution_order=5,
                task_description="Calculate 2+2",
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["input_data"] == {"task": "Calculate 2+2"}
            assert call_kwargs["is_sub_agent"] is True
            assert call_kwargs["parent_agent_id"] == "node-exec-789"
            assert call_kwargs["execution_order"] == 5
            assert call_kwargs["node_id"] == sub_agent_node.uniq_id
            assert call_kwargs["node_name"] == sub_agent_node.name

    @pytest.mark.asyncio
    async def test_starts_execution_after_creation(self, sub_agent_node):
        """Should call start_node_execution after creating the record."""
        mock_create = MagicMock(return_value={"id": "exec-id-123"})
        mock_start = MagicMock()

        with patch(
            "backend.services.subgraph.agent.database_tracker.ExecutionHistoryService"
        ) as mock_service:
            mock_service.create_node_execution = mock_create
            mock_service.start_node_execution = mock_start

            await create_agent_execution_record(
                agent_node=sub_agent_node,
                parent_db_execution_id="parent-123",
                parent_node_id="orchestrator-001",
                parent_node_execution_id="node-exec-789",
                execution_order=1,
                task_description="Task",
            )

            mock_start.assert_called_once_with("exec-id-123")

    @pytest.mark.asyncio
    async def test_handles_creation_error_gracefully(self, sub_agent_node):
        """Should return None and log error if creation fails."""
        with patch(
            "backend.services.subgraph.agent.database_tracker.ExecutionHistoryService"
        ) as mock_service:
            mock_service.create_node_execution.side_effect = Exception("DB error")

            result = await create_agent_execution_record(
                agent_node=sub_agent_node,
                parent_db_execution_id="parent-123",
                parent_node_id="orchestrator-001",
                parent_node_execution_id="node-exec-789",
                execution_order=1,
                task_description="Task",
            )

            assert result is None


class TestCompleteAgentExecutionRecord:
    """Tests for complete_agent_execution_record function."""

    @pytest.mark.asyncio
    async def test_returns_none_without_node_exec_id(self, sub_agent_node):
        """Should return None if no node_exec_id provided."""
        from datetime import datetime, timezone

        result = await complete_agent_execution_record(
            node_exec_id=None,
            agent_node=sub_agent_node,
            response_content="The answer is 4",
            tool_execution_tracker=[],
            token_counts={"input_tokens": 100, "output_tokens": 50},
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )

        assert result is None


class TestFailAgentExecutionRecord:
    """Tests for fail_agent_execution_record function."""

    @pytest.mark.asyncio
    async def test_returns_false_without_node_exec_id(self, sub_agent_node):
        """Should return False if no node_exec_id provided."""
        result = await fail_agent_execution_record(
            node_exec_id=None,
            agent_node=sub_agent_node,
            error="Some error occurred",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_marks_execution_as_failed(self, sub_agent_node):
        """Should call complete_node_execution with failed status."""
        with patch(
            "backend.services.subgraph.agent.database_tracker.ExecutionHistoryService"
        ) as mock_service:
            mock_service.complete_node_execution = MagicMock()

            result = await fail_agent_execution_record(
                node_exec_id="exec-123",
                agent_node=sub_agent_node,
                error="Calculation failed",
            )

            assert result is True
            mock_service.complete_node_execution.assert_called_once()
            call_kwargs = mock_service.complete_node_execution.call_args[1]
            assert call_kwargs["status"] == "failed"
            assert call_kwargs["output_data"] == {"error": "Calculation failed"}
