"""Tests for tool_tracker delegation resolution.

These tests verify that delegation tools (delegate_to_*) are correctly
resolved to their actual agent node properties instead of synthetic IDs.
"""

import logging

import pytest

from backend.models.workflow import NodeType
from backend.services.subgraph.agent.tool_tracker import (
    ResolutionStrategy,
    ToolNodeInfo,
)


class MockGraph:
    """Mock graph for testing."""

    def __init__(self, nodes=None):
        self.nodes = nodes or []


class MockGraphManager:
    """Mock graph manager for testing."""

    def __init__(self, graph=None):
        self._graph = graph

    def get_graph(self, graph_name: str):
        return self._graph


class MockEnhancedNodeData:
    """Mock EnhancedNodeData for testing."""

    def __init__(self, uniq_id: str, name: str, node_type=NodeType.AGENT):
        self.uniq_id = uniq_id
        self.name = name
        self.type = node_type


class TestFindAgentByNormalizedName:
    """Test the _find_agent_by_normalized_name helper function."""

    @pytest.fixture
    def math_expert_node(self):
        """Create a Math Expert agent node."""
        return MockEnhancedNodeData(
            uniq_id="6e497c9d-7463-47ef-ae8b-668ddee7fa54",
            name="Math Expert",
            node_type=NodeType.AGENT,
        )

    @pytest.fixture
    def orchestrator_node(self):
        """Create an orchestrator agent node."""
        return MockEnhancedNodeData(
            uniq_id="ecee1c8b-cf19-4b53-8616-d65eddddcf89",
            name="Agent 1",
            node_type=NodeType.AGENT,
        )

    @pytest.fixture
    def graph_with_agents(self, math_expert_node, orchestrator_node):
        """Create a graph with test agents."""
        return MockGraph(nodes=[orchestrator_node, math_expert_node])

    def test_finds_agent_with_exact_name_match(
        self, graph_with_agents, math_expert_node
    ):
        """Should find 'Math Expert' when searching for 'math expert'."""
        from backend.services.subgraph.agent.tool_tracker import (
            _find_agent_by_normalized_name,
        )

        graph_manager = MockGraphManager(graph=graph_with_agents)

        result = _find_agent_by_normalized_name(
            graph_manager=graph_manager,
            graph_name="TestGraph",
            normalized_name="math expert",
        )

        assert result is not None
        assert result.uniq_id == math_expert_node.uniq_id
        assert result.name == "Math Expert"

    def test_returns_none_for_unknown_agent(self, graph_with_agents):
        """Should return None when agent name doesn't exist."""
        from backend.services.subgraph.agent.tool_tracker import (
            _find_agent_by_normalized_name,
        )

        graph_manager = MockGraphManager(graph=graph_with_agents)

        result = _find_agent_by_normalized_name(
            graph_manager=graph_manager,
            graph_name="TestGraph",
            normalized_name="unknown agent",
        )

        assert result is None

    def test_handles_missing_graph(self):
        """Should return None when graph is not found."""
        from backend.services.subgraph.agent.tool_tracker import (
            _find_agent_by_normalized_name,
        )

        graph_manager = MockGraphManager(graph=None)

        result = _find_agent_by_normalized_name(
            graph_manager=graph_manager,
            graph_name="NonExistentGraph",
            normalized_name="math expert",
        )

        assert result is None

    def test_handles_empty_nodes(self):
        """Should return None when graph has no nodes."""
        from backend.services.subgraph.agent.tool_tracker import (
            _find_agent_by_normalized_name,
        )

        graph_manager = MockGraphManager(graph=MockGraph(nodes=[]))

        result = _find_agent_by_normalized_name(
            graph_manager=graph_manager,
            graph_name="TestGraph",
            normalized_name="math expert",
        )

        assert result is None


class TestResolveToolNodeInfo:
    """Test delegation tool resolution in _resolve_tool_node_info."""

    @pytest.fixture
    def math_expert_node(self):
        """Create a Math Expert agent node."""
        return MockEnhancedNodeData(
            uniq_id="6e497c9d-7463-47ef-ae8b-668ddee7fa54",
            name="Math Expert",
            node_type=NodeType.AGENT,
        )

    @pytest.fixture
    def orchestrator_node(self):
        """Create an orchestrator agent node."""
        return MockEnhancedNodeData(
            uniq_id="ecee1c8b-cf19-4b53-8616-d65eddddcf89",
            name="Agent 1",
            node_type=NodeType.AGENT,
        )

    @pytest.fixture
    def graph_with_agents(self, math_expert_node, orchestrator_node):
        """Create a graph with test agents."""
        return MockGraph(nodes=[orchestrator_node, math_expert_node])

    def test_delegation_tool_resolves_to_agent_node(
        self, graph_with_agents, math_expert_node, orchestrator_node
    ):
        """delegate_to_math_expert should resolve to Math Expert's actual ID."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        graph_manager = MockGraphManager(graph=graph_with_agents)

        result = _resolve_tool_node_info(
            base_tool_name="delegate_to_math_expert",
            synthetic_tool_name="delegate_to_math_expert",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert isinstance(result, ToolNodeInfo)
        assert result.node_id == math_expert_node.uniq_id
        assert result.node_name == "Math Expert"
        assert result.node_type == NodeType.AGENT
        assert result.is_delegation is True
        assert result.is_fallback is False
        assert result.resolution_strategy == ResolutionStrategy.DELEGATION_PARSE

    def test_delegation_tool_returns_is_delegation_true(
        self, graph_with_agents, orchestrator_node
    ):
        """is_delegation flag should be True for delegate_to_* tools."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        graph_manager = MockGraphManager(graph=graph_with_agents)

        result = _resolve_tool_node_info(
            base_tool_name="delegate_to_math_expert",
            synthetic_tool_name="delegate_to_math_expert",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert result.is_delegation is True

    def test_delegation_tool_has_agent_node_type(
        self, graph_with_agents, orchestrator_node
    ):
        """node_type should be NodeType.AGENT for delegation tools."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        graph_manager = MockGraphManager(graph=graph_with_agents)

        result = _resolve_tool_node_info(
            base_tool_name="delegate_to_math_expert",
            synthetic_tool_name="delegate_to_math_expert",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert result.node_type == NodeType.AGENT

    def test_regular_tool_returns_is_delegation_false(self, orchestrator_node):
        """Regular tools should have is_delegation=False."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        graph_manager = MockGraphManager(graph=None)

        result = _resolve_tool_node_info(
            base_tool_name="web_search",
            synthetic_tool_name="web_search_abc123",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert result.is_delegation is False

    def test_fallback_to_synthetic_for_unknown_tools(self, orchestrator_node):
        """Unknown tools should still use synthetic IDs."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        graph_manager = MockGraphManager(graph=None)

        result = _resolve_tool_node_info(
            base_tool_name="some_unknown_tool",
            synthetic_tool_name="some_unknown_tool_xyz",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        # Falls back to agent ID when tool can't be resolved
        assert result.node_id == orchestrator_node.uniq_id
        assert result.node_name == "some_unknown_tool_xyz"
        assert result.node_type is None
        assert result.is_delegation is False
        assert result.is_fallback is True
        assert result.resolution_strategy == ResolutionStrategy.FALLBACK

    def test_mapped_tool_returns_is_delegation_false(self, orchestrator_node):
        """Tools found in mapping should have is_delegation=False."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        tool_mapping = {
            "web_search": {
                "node_id": "actual-web-search-id",
                "node_name": "Web Search Tool",
                "node_type": NodeType.WEB_SEARCH,
            }
        }

        graph_manager = MockGraphManager(graph=None)

        result = _resolve_tool_node_info(
            base_tool_name="web_search",
            synthetic_tool_name="web_search_abc123",
            tool_node_mapping=tool_mapping,
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert result.node_id == "actual-web-search-id"
        assert result.is_delegation is False
        assert result.is_fallback is False
        assert result.resolution_strategy == ResolutionStrategy.DIRECT_MAPPING

    def test_delegation_without_graph_manager_uses_synthetic(self, orchestrator_node):
        """Delegation tools without graph_manager should fall back to synthetic IDs."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        result = _resolve_tool_node_info(
            base_tool_name="delegate_to_math_expert",
            synthetic_tool_name="delegate_to_math_expert",
            tool_node_mapping={},
            graph_name=None,  # No graph name
            graph_manager=None,  # No graph manager
            agent_node=orchestrator_node,
            execution_order=1,
        )

        # Still marked as delegation, but falls back to agent ID since can't resolve
        assert result.is_delegation is True
        assert result.node_id == orchestrator_node.uniq_id
        assert result.is_fallback is True
        assert result.resolution_strategy == ResolutionStrategy.FALLBACK


class TestExtractToolInfo:
    """Test _extract_tool_info includes is_delegation flag."""

    @pytest.fixture
    def math_expert_node(self):
        """Create a Math Expert agent node."""
        return MockEnhancedNodeData(
            uniq_id="6e497c9d-7463-47ef-ae8b-668ddee7fa54",
            name="Math Expert",
            node_type=NodeType.AGENT,
        )

    @pytest.fixture
    def orchestrator_node(self):
        """Create an orchestrator agent node."""
        return MockEnhancedNodeData(
            uniq_id="ecee1c8b-cf19-4b53-8616-d65eddddcf89",
            name="Agent 1",
            node_type=NodeType.AGENT,
        )

    @pytest.fixture
    def graph_with_agents(self, math_expert_node, orchestrator_node):
        """Create a graph with test agents."""
        return MockGraph(nodes=[orchestrator_node, math_expert_node])

    def test_delegation_tool_info_includes_is_delegation(
        self, graph_with_agents, math_expert_node, orchestrator_node
    ):
        """Tool info for delegation tools should include is_delegation=True."""
        from backend.services.subgraph.agent.tool_tracker import _extract_tool_info

        graph_manager = MockGraphManager(graph=graph_with_agents)

        tool_exec = {
            "tool": "delegate_to_math_expert",
            "input": "Solve 2+2",
            "output": "The answer is 4",
        }

        tool_info = _extract_tool_info(
            tool_exec=tool_exec,
            tool_name="delegate_to_math_expert",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert "is_delegation" in tool_info
        assert tool_info["is_delegation"] is True
        assert tool_info["node_id"] == math_expert_node.uniq_id
        assert tool_info["node_name"] == "Math Expert"
        assert tool_info["node_type"] == "AGENT"
        # New fields
        assert "is_fallback" in tool_info
        assert tool_info["is_fallback"] is False
        assert "resolution_strategy" in tool_info
        assert tool_info["resolution_strategy"] == "delegation_parse"

    def test_regular_tool_info_includes_is_delegation_false(self, orchestrator_node):
        """Tool info for regular tools should include is_delegation=False."""
        from backend.services.subgraph.agent.tool_tracker import _extract_tool_info

        graph_manager = MockGraphManager(graph=None)

        tool_exec = {
            "tool": "web_search",
            "query": "test query",
            "results": "some results",
        }

        tool_info = _extract_tool_info(
            tool_exec=tool_exec,
            tool_name="web_search_abc123",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert "is_delegation" in tool_info
        assert tool_info["is_delegation"] is False
        # New fields - fallback is used since no mapping exists
        assert "is_fallback" in tool_info
        assert tool_info["is_fallback"] is True
        assert "resolution_strategy" in tool_info
        assert tool_info["resolution_strategy"] == "fallback"
        assert "fallback_reason" in tool_info

    def test_mapped_tool_info_includes_fallback_false(self, orchestrator_node):
        """Tool info for mapped tools should include is_fallback=False."""
        from backend.services.subgraph.agent.tool_tracker import _extract_tool_info

        graph_manager = MockGraphManager(graph=None)

        # The mapping should include both base name and synthetic name
        # for reliable matching
        tool_mapping = {
            "web_search": {
                "node_id": "actual-web-search-id",
                "node_name": "Web Search Tool",
                "node_type": NodeType.WEB_SEARCH,
            },
            "web_search_abc123": {
                "node_id": "actual-web-search-id",
                "node_name": "Web Search Tool",
                "node_type": NodeType.WEB_SEARCH,
            },
        }

        tool_exec = {
            "tool": "web_search",
            "query": "test query",
            "results": "some results",
        }

        tool_info = _extract_tool_info(
            tool_exec=tool_exec,
            tool_name="web_search_abc123",
            tool_node_mapping=tool_mapping,
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert tool_info["is_fallback"] is False
        assert tool_info["resolution_strategy"] == "direct_mapping"
        assert tool_info["fallback_reason"] is None


class TestSendToolNotificationDuplicateSkipping:
    """Tests for skipping duplicate WebSocket notifications.

    When tools are invoked via LLM tool calls, streaming events (tool_call_start,
    tool_call_complete) are already sent in real-time. The _send_tool_notification
    function should skip these duplicates to avoid sending the same update twice.
    """

    @pytest.fixture
    def mock_agent_node(self):
        """Create a mock agent node."""
        return MockEnhancedNodeData(
            uniq_id="agent-123",
            name="Test Agent",
            node_type=NodeType.AGENT,
        )

    @pytest.fixture
    def tool_info(self):
        """Sample tool info dictionary."""
        return {
            "node_id": "node_123",
            "node_name": "Document Search",
            "node_type": "DOCUMENT_SEARCH",
            "input_data": {"query": "test query"},
            "output_data": {"result": "found documents"},
            "is_delegation": False,
            "synthetic_tool_name": "search_documents_abc123",
        }

    @pytest.mark.asyncio
    async def test_skips_notification_when_was_streamed_true(
        self, tool_info, mock_agent_node
    ):
        """Verify _send_tool_notification skips when was_streamed is True."""
        from unittest.mock import patch

        from backend.services.subgraph.agent.tool_tracker import _send_tool_notification

        tool_exec = {
            "was_streamed": True,  # Explicitly marked as streamed
            "timestamp": 12345.0,
        }

        with patch(
            "backend.services.subgraph.agent.tool_tracker.send_node_complete_notification"
        ) as mock_send:
            mock_send.return_value = None

            await _send_tool_notification(
                tool_info=tool_info,
                tool_exec=tool_exec,
                parent_execution_id="exec-123",
                agent_node=mock_agent_node,
            )

            # Should NOT call send_node_complete_notification
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_notification_when_was_streamed_false(
        self, tool_info, mock_agent_node
    ):
        """Verify _send_tool_notification sends when was_streamed is False."""
        from unittest.mock import patch

        from backend.services.subgraph.agent.tool_tracker import _send_tool_notification

        tool_exec = {
            "was_streamed": False,  # Explicitly not streamed
            "timestamp": 12345.0,
        }

        with patch(
            "backend.services.subgraph.agent.tool_tracker.send_node_complete_notification"
        ) as mock_send:
            mock_send.return_value = None

            await _send_tool_notification(
                tool_info=tool_info,
                tool_exec=tool_exec,
                parent_execution_id="exec-123",
                agent_node=mock_agent_node,
            )

            # SHOULD call send_node_complete_notification
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_sends_notification_when_was_streamed_missing(
        self, tool_info, mock_agent_node
    ):
        """Verify notification is sent when was_streamed field is missing (backward compat)."""
        from unittest.mock import patch

        from backend.services.subgraph.agent.tool_tracker import _send_tool_notification

        tool_exec = {
            # No was_streamed field - backward compatibility, defaults to False
            "timestamp": 12345.0,
        }

        with patch(
            "backend.services.subgraph.agent.tool_tracker.send_node_complete_notification"
        ) as mock_send:
            mock_send.return_value = None

            await _send_tool_notification(
                tool_info=tool_info,
                tool_exec=tool_exec,
                parent_execution_id="exec-123",
                agent_node=mock_agent_node,
            )

            # Missing was_streamed defaults to False, so notification should be sent
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_notification_includes_correct_params(
        self, tool_info, mock_agent_node
    ):
        """Verify notification is called with correct parameters."""
        from unittest.mock import patch

        from backend.services.subgraph.agent.tool_tracker import _send_tool_notification

        tool_exec = {
            # No tool_id - should send notification
            "timestamp": 12345.0,
            "duration": 1.5,
        }

        with patch(
            "backend.services.subgraph.agent.tool_tracker.send_node_complete_notification"
        ) as mock_send:
            mock_send.return_value = None

            await _send_tool_notification(
                tool_info=tool_info,
                tool_exec=tool_exec,
                parent_execution_id="exec-123",
                agent_node=mock_agent_node,
            )

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]

            assert call_kwargs["execution_id"] == "exec-123"
            assert call_kwargs["node_id"] == "node_123"
            assert call_kwargs["node_name"] == "Document Search"
            assert call_kwargs["node_type"] == "DOCUMENT_SEARCH"
            assert call_kwargs["duration_seconds"] == 1.5
            assert call_kwargs["parent_agent_id"] == "agent-123"


class TestFallbackResolution:
    """Tests for fallback resolution behavior and logging."""

    @pytest.fixture
    def orchestrator_node(self):
        """Create an orchestrator agent node."""
        return MockEnhancedNodeData(
            uniq_id="ecee1c8b-cf19-4b53-8616-d65eddddcf89",
            name="Test Agent",
            node_type=NodeType.AGENT,
        )

    def test_fallback_logs_warning(self, orchestrator_node, caplog):
        """Fallback should log a warning with FALLBACK RESOLUTION prefix."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        graph_manager = MockGraphManager(graph=None)

        with caplog.at_level(logging.WARNING):
            _resolve_tool_node_info(
                base_tool_name="unknown_tool",
                synthetic_tool_name="unknown_tool_xyz",
                tool_node_mapping={},
                graph_name="TestGraph",
                graph_manager=graph_manager,
                agent_node=orchestrator_node,
                execution_order=1,
            )

        # Check that the fallback warning was logged
        assert any("FALLBACK RESOLUTION" in record.message for record in caplog.records)

    def test_fallback_sets_is_fallback_true(self, orchestrator_node):
        """Fallback resolution should set is_fallback=True."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        graph_manager = MockGraphManager(graph=None)

        result = _resolve_tool_node_info(
            base_tool_name="unknown_tool",
            synthetic_tool_name="unknown_tool_xyz",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert result.is_fallback is True

    def test_fallback_includes_reason(self, orchestrator_node):
        """Fallback resolution should include a reason."""
        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        graph_manager = MockGraphManager(graph=None)

        result = _resolve_tool_node_info(
            base_tool_name="unknown_tool",
            synthetic_tool_name="unknown_tool_xyz",
            tool_node_mapping={},
            graph_name="TestGraph",
            graph_manager=graph_manager,
            agent_node=orchestrator_node,
            execution_order=1,
        )

        assert result.fallback_reason is not None
        assert "no mapping found" in result.fallback_reason.lower()

    def test_fallback_records_metric(self, orchestrator_node):
        """Fallback resolution should record a metric."""
        from unittest.mock import patch

        from backend.services.subgraph.agent.tool_tracker import _resolve_tool_node_info

        # Mock the metric recording function
        with patch(
            "backend.services.subgraph.agent.tool_tracker._record_fallback_metric"
        ) as mock_record:
            graph_manager = MockGraphManager(graph=None)

            _resolve_tool_node_info(
                base_tool_name="unknown_tool",
                synthetic_tool_name="unknown_tool_xyz",
                tool_node_mapping={},
                graph_name="TestGraph",
                graph_manager=graph_manager,
                agent_node=orchestrator_node,
                execution_order=1,
            )

            mock_record.assert_called_once_with(
                "unknown_tool", orchestrator_node.name, "TestGraph"
            )


class TestToolNodeInfoDataclass:
    """Tests for the ToolNodeInfo dataclass."""

    def test_creation_with_all_fields(self):
        """Should create ToolNodeInfo with all required fields."""
        info = ToolNodeInfo(
            node_id="test-id",
            node_name="Test Tool",
            node_type=NodeType.WEB_SEARCH,
            is_delegation=False,
            is_fallback=False,
            resolution_strategy=ResolutionStrategy.DIRECT_MAPPING,
            fallback_reason=None,
        )

        assert info.node_id == "test-id"
        assert info.node_name == "Test Tool"
        assert info.node_type == NodeType.WEB_SEARCH
        assert info.is_delegation is False
        assert info.is_fallback is False
        assert info.resolution_strategy == ResolutionStrategy.DIRECT_MAPPING
        assert info.fallback_reason is None

    def test_fallback_reason_optional(self):
        """fallback_reason should be optional."""
        info = ToolNodeInfo(
            node_id="test-id",
            node_name="Test Tool",
            node_type=None,
            is_delegation=False,
            is_fallback=True,
            resolution_strategy=ResolutionStrategy.FALLBACK,
        )

        # fallback_reason defaults to None
        assert info.fallback_reason is None

    def test_resolution_strategy_values(self):
        """ResolutionStrategy enum should have expected values."""
        assert ResolutionStrategy.DIRECT_MAPPING.value == "direct_mapping"
        assert ResolutionStrategy.DELEGATION_PARSE.value == "delegation_parse"
        assert ResolutionStrategy.FALLBACK.value == "fallback"


class TestRecordFallbackMetric:
    """Tests for the _record_fallback_metric function."""

    def test_metric_failure_does_not_raise(self):
        """Metric recording failures should not raise exceptions."""
        from unittest.mock import patch

        from backend.services.subgraph.agent.tool_tracker import _record_fallback_metric

        # Mock MetricCollector at its source to simulate import failure
        with patch.dict(
            "sys.modules",
            {"backend.services.metrics.collector": None},
        ):
            # Should not raise even when metrics module is unavailable
            _record_fallback_metric("test_tool", "test_agent", "test_graph")

    def test_metric_collector_exception_handled(self):
        """MetricCollector exceptions should be handled gracefully."""
        from unittest.mock import MagicMock, patch

        from backend.services.subgraph.agent.tool_tracker import _record_fallback_metric

        # Mock MetricCollector to raise an exception on record()
        mock_collector = MagicMock()
        mock_collector.record.side_effect = Exception("Metric recording failed")

        with patch(
            "backend.services.metrics.collector.MetricCollector",
            return_value=mock_collector,
        ):
            # Should not raise
            _record_fallback_metric("test_tool", "test_agent", "test_graph")


class TestReviewIterationPropagation:
    """Tests for review_iteration propagation through tool tracking."""

    @pytest.fixture
    def orchestrator_node(self):
        """Create an orchestrator agent node."""
        return MockEnhancedNodeData(
            uniq_id="agent-123",
            name="Test Agent",
            node_type=NodeType.AGENT,
        )

    @pytest.fixture
    def tool_info(self):
        """Sample tool info dictionary."""
        return {
            "node_id": "http-tool-123",
            "node_name": "HTTP Request",
            "node_type": "HTTP_REQUEST",
            "input_data": {"url": "https://api.example.com"},
            "output_data": {"status_code": 200},
            "is_delegation": False,
            "synthetic_tool_name": "http_request_abc123",
        }

    @pytest.mark.asyncio
    async def test_create_tool_execution_record_passes_review_iteration(
        self, tool_info, orchestrator_node
    ):
        """_create_tool_execution_record should pass review_iteration to ExecutionHistoryService."""
        from unittest.mock import MagicMock, patch

        from backend.services.subgraph.agent.tool_tracker import (
            _create_tool_execution_record,
        )

        mock_service = MagicMock()
        mock_service.create_node_execution.return_value = {"id": 123}
        mock_service.start_node_execution.return_value = None
        mock_service.complete_node_execution.return_value = None

        with patch(
            "backend.services.subgraph.agent.tool_tracker.ExecutionHistoryService",
            mock_service,
        ):
            await _create_tool_execution_record(
                tool_info=tool_info,
                parent_db_execution_id="exec-456",
                execution_order=1,
                agent_node=orchestrator_node,
                parent_node_execution_id="node-exec-789",
                review_iteration=2,  # Second iteration
            )

            # Verify create_node_execution was called with review_iteration
            mock_service.create_node_execution.assert_called_once()
            call_kwargs = mock_service.create_node_execution.call_args[1]
            assert call_kwargs["review_iteration"] == 2

    @pytest.mark.asyncio
    async def test_create_tool_execution_record_handles_none_review_iteration(
        self, tool_info, orchestrator_node
    ):
        """_create_tool_execution_record should handle None review_iteration."""
        from unittest.mock import MagicMock, patch

        from backend.services.subgraph.agent.tool_tracker import (
            _create_tool_execution_record,
        )

        mock_service = MagicMock()
        mock_service.create_node_execution.return_value = {"id": 123}
        mock_service.start_node_execution.return_value = None
        mock_service.complete_node_execution.return_value = None

        with patch(
            "backend.services.subgraph.agent.tool_tracker.ExecutionHistoryService",
            mock_service,
        ):
            await _create_tool_execution_record(
                tool_info=tool_info,
                parent_db_execution_id="exec-456",
                execution_order=1,
                agent_node=orchestrator_node,
                parent_node_execution_id="node-exec-789",
                review_iteration=None,  # No iteration tracking
            )

            # Verify create_node_execution was called with review_iteration=None
            mock_service.create_node_execution.assert_called_once()
            call_kwargs = mock_service.create_node_execution.call_args[1]
            assert call_kwargs["review_iteration"] is None

    @pytest.mark.asyncio
    async def test_track_tool_executions_passes_review_iteration(
        self, orchestrator_node
    ):
        """track_tool_executions should pass review_iteration to _create_tool_execution_record."""
        from unittest.mock import AsyncMock, patch

        from backend.services.subgraph.agent.tool_tracker import track_tool_executions

        tool_exec_tracker = [
            {
                "tool": "http_request",
                "input": {"url": "https://example.com"},
                "output": {"status_code": 200},
                "timestamp": 12345.0,
            }
        ]

        tool_mapping = {
            "http_request": {
                "node_id": "http-123",
                "node_name": "HTTP Request",
                "node_type": "HTTP_REQUEST",
            }
        }

        mock_create_record = AsyncMock(return_value=123)
        mock_send_notification = AsyncMock()

        with (
            patch(
                "backend.services.subgraph.agent.tool_tracker._create_tool_execution_record",
                mock_create_record,
            ),
            patch(
                "backend.services.subgraph.agent.tool_tracker._send_tool_notification",
                mock_send_notification,
            ),
        ):
            await track_tool_executions(
                tool_execution_tracker=tool_exec_tracker,
                agent_node=orchestrator_node,
                parent_db_execution_id="exec-456",
                parent_node_execution_id="node-exec-789",
                parent_execution_id="parent-exec-123",
                execution_order=1,
                tool_node_mapping=tool_mapping,
                graph_name="TestGraph",
                graph_manager=MockGraphManager(graph=None),
                review_iteration=3,  # Third iteration
            )

            # Verify _create_tool_execution_record was called with review_iteration=3
            mock_create_record.assert_called_once()
            call_kwargs = mock_create_record.call_args[1]
            assert call_kwargs["review_iteration"] == 3
