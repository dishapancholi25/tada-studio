"""
Unit tests for ForEachNodeExecutor.

Tests cover:
- Item extraction (valid path, invalid path, missing source)
- Dynamic source resolution (previous/specific/start source_mode)
- AsyncRateLimiter utility
- Basic executor initialization
"""

import asyncio
from dataclasses import dataclass, field
from typing import List
from unittest.mock import MagicMock

import pytest

from backend.models.workflow import NodeType
from backend.models.workflow.base import Connection
from backend.models.workflow.configs.for_each import ForEachConfig
from backend.services.config import ExecutionConfig
from backend.services.nodes.executors.for_each import (
    ForEachNodeExecutor,
    AsyncRateLimiter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_execution_history_service():
    """Mock execution history service."""
    service = MagicMock()
    service.create_node_execution = MagicMock(return_value={"id": "exec-123"})
    service.complete_node_execution = MagicMock()
    service.mark_node_failed = MagicMock()
    return service


@pytest.fixture
def mock_ws_notifier():
    """Mock WebSocket notifier."""
    notifier = MagicMock()
    return notifier


@pytest.fixture
def mock_subgraph_executor():
    """Mock subgraph executor."""
    return MagicMock()


@pytest.fixture
def mock_graph_manager():
    """Mock graph manager."""
    return MagicMock()


@pytest.fixture
def for_each_executor(
    mock_execution_history_service,
    mock_ws_notifier,
    mock_subgraph_executor,
    mock_graph_manager,
):
    """Create ForEachNodeExecutor instance with mocked dependencies."""
    return ForEachNodeExecutor(
        execution_history_service=mock_execution_history_service,
        ws_notifier=mock_ws_notifier,
        subgraph_executor=mock_subgraph_executor,
        graph_manager=mock_graph_manager,
    )


@pytest.fixture
def basic_for_each_config():
    """Create a basic For Each config."""
    return ForEachConfig(
        source_mode="specific",
        source_node_id="csv-reader",
        field_path="fields.rows",
        concurrency_limit=5,
        max_iterations=1000,
        error_strategy="continue_on_error",
        max_retries_per_item=0,
    )


@pytest.fixture
def mock_for_each_node():
    """Create a mock For Each node (only attributes used by _extract_items)."""
    node = MagicMock()
    node.uniq_id = "for-each-1"
    node.name = "For Each"
    return node


# ---------------------------------------------------------------------------
# Tests for Item Extraction
# ---------------------------------------------------------------------------


class TestItemExtraction:
    """Tests for extracting items from source node output."""

    def test_extract_items_valid_path(self, for_each_executor, basic_for_each_config, mock_for_each_node):
        """Should extract items from valid field path."""
        state = {
            "node_outputs": {
                "csv-reader": {"fields": {"rows": [{"a": 1}, {"a": 2}, {"a": 3}]}}
            }
        }

        items = for_each_executor._extract_items(mock_for_each_node, state, basic_for_each_config)

        assert len(items) == 3
        assert items[0] == {"a": 1}
        assert items[1] == {"a": 2}
        assert items[2] == {"a": 3}

    def test_extract_items_nested_path(self, for_each_executor, basic_for_each_config, mock_for_each_node):
        """Should extract items from deeply nested path."""
        basic_for_each_config.field_path = "structured.data.items"
        state = {
            "node_outputs": {
                "csv-reader": {"structured": {"data": {"items": ["a", "b", "c"]}}}
            }
        }

        items = for_each_executor._extract_items(mock_for_each_node, state, basic_for_each_config)

        assert items == ["a", "b", "c"]

    def test_extract_items_direct_list(self, for_each_executor, basic_for_each_config, mock_for_each_node):
        """Should extract items when path points directly to a list."""
        basic_for_each_config.field_path = "items"
        state = {"node_outputs": {"csv-reader": {"items": [1, 2, 3, 4, 5]}}}

        items = for_each_executor._extract_items(mock_for_each_node, state, basic_for_each_config)

        assert items == [1, 2, 3, 4, 5]

    def test_extract_items_missing_source_node(self, for_each_executor, basic_for_each_config, mock_for_each_node):
        """Should raise error when source node not found."""
        state = {"node_outputs": {}}

        with pytest.raises(ValueError) as exc_info:
            for_each_executor._extract_items(mock_for_each_node, state, basic_for_each_config)

        assert "csv-reader" in str(exc_info.value)

    def test_extract_items_invalid_path(self, for_each_executor, basic_for_each_config, mock_for_each_node):
        """Should raise error when field path doesn't exist."""
        basic_for_each_config.field_path = "nonexistent.path"
        state = {"node_outputs": {"csv-reader": {"fields": {"rows": [1, 2, 3]}}}}

        with pytest.raises(ValueError) as exc_info:
            for_each_executor._extract_items(mock_for_each_node, state, basic_for_each_config)

        assert "nonexistent" in str(exc_info.value)

    def test_extract_items_empty_array(self, for_each_executor, basic_for_each_config, mock_for_each_node):
        """Should return empty list for empty source array."""
        state = {"node_outputs": {"csv-reader": {"fields": {"rows": []}}}}

        items = for_each_executor._extract_items(mock_for_each_node, state, basic_for_each_config)

        assert items == []


# ---------------------------------------------------------------------------
# Fixtures for dynamic source_mode resolution tests
# ---------------------------------------------------------------------------


@dataclass
class MockGraphNode:
    """Minimal node stand-in for graph.nodes in _resolve_source_node_id tests."""

    uniq_id: str
    type: NodeType = NodeType.AGENT


@dataclass
class MockGraph:
    """Minimal graph stand-in exposing `.nodes` and `.connections`."""

    nodes: List[MockGraphNode] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tests for dynamic source_mode resolution
# ---------------------------------------------------------------------------


class TestResolveSourceNodeId:
    """Tests for ForEachNodeExecutor._resolve_source_node_id."""

    def test_specific_mode_returns_configured_source_node_id(
        self, for_each_executor, mock_for_each_node
    ):
        config = ForEachConfig(source_mode="specific", source_node_id="db-query")

        resolved = for_each_executor._resolve_source_node_id(
            mock_for_each_node, config, graph=None
        )

        assert resolved == "db-query"

    def test_specific_mode_raises_when_source_node_id_empty(
        self, for_each_executor, mock_for_each_node
    ):
        config = ForEachConfig(source_mode="specific", source_node_id="")

        with pytest.raises(ValueError):
            for_each_executor._resolve_source_node_id(
                mock_for_each_node, config, graph=None
            )

    def test_previous_mode_resolves_incoming_workflow_connection(
        self, for_each_executor, mock_for_each_node
    ):
        graph = MockGraph(
            nodes=[MockGraphNode(uniq_id="db-query")],
            connections=[
                Connection(
                    source_id="db-query",
                    target_id=mock_for_each_node.uniq_id,
                    connection_type="workflow",
                ),
            ],
        )
        config = ForEachConfig(source_mode="previous")

        resolved = for_each_executor._resolve_source_node_id(
            mock_for_each_node, config, graph=graph
        )

        assert resolved == "db-query"

    def test_previous_mode_ignores_tool_connections(
        self, for_each_executor, mock_for_each_node
    ):
        """A tool-type connection (e.g. Agent -> its own tool node) must not
        be mistaken for the For Each node's data source."""
        graph = MockGraph(
            nodes=[MockGraphNode(uniq_id="agent-1"), MockGraphNode(uniq_id="db-tool")],
            connections=[
                Connection(
                    source_id="agent-1",
                    target_id="db-tool",
                    connection_type="tool",
                ),
                Connection(
                    source_id="agent-1",
                    target_id=mock_for_each_node.uniq_id,
                    connection_type="workflow",
                ),
            ],
        )
        config = ForEachConfig(source_mode="previous")

        resolved = for_each_executor._resolve_source_node_id(
            mock_for_each_node, config, graph=graph
        )

        assert resolved == "agent-1"

    def test_previous_mode_raises_when_no_incoming_connection(
        self, for_each_executor, mock_for_each_node
    ):
        graph = MockGraph(nodes=[], connections=[])
        config = ForEachConfig(source_mode="previous")

        with pytest.raises(ValueError):
            for_each_executor._resolve_source_node_id(
                mock_for_each_node, config, graph=graph
            )

    def test_previous_mode_raises_when_graph_missing(
        self, for_each_executor, mock_for_each_node
    ):
        config = ForEachConfig(source_mode="previous")

        with pytest.raises(ValueError):
            for_each_executor._resolve_source_node_id(
                mock_for_each_node, config, graph=None
            )

    def test_start_mode_resolves_start_node(self, for_each_executor, mock_for_each_node):
        graph = MockGraph(
            nodes=[
                MockGraphNode(uniq_id="start-1", type=NodeType.START),
                MockGraphNode(uniq_id="agent-1", type=NodeType.AGENT),
            ],
            connections=[],
        )
        config = ForEachConfig(source_mode="start")

        resolved = for_each_executor._resolve_source_node_id(
            mock_for_each_node, config, graph=graph
        )

        assert resolved == "start-1"

    def test_start_mode_raises_when_no_start_node(
        self, for_each_executor, mock_for_each_node
    ):
        graph = MockGraph(nodes=[MockGraphNode(uniq_id="agent-1")], connections=[])
        config = ForEachConfig(source_mode="start")

        with pytest.raises(ValueError):
            for_each_executor._resolve_source_node_id(
                mock_for_each_node, config, graph=graph
            )

    def test_unknown_mode_raises(self, for_each_executor, mock_for_each_node):
        config = ForEachConfig(source_mode="specific", source_node_id="x")
        config.source_mode = "bogus"  # bypass Literal typing for the test

        with pytest.raises(ValueError):
            for_each_executor._resolve_source_node_id(
                mock_for_each_node, config, graph=None
            )


# ---------------------------------------------------------------------------
# Tests for AsyncRateLimiter
# ---------------------------------------------------------------------------


class TestAsyncRateLimiter:
    """Tests for the rate limiter utility."""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic_acquire(self):
        """Should allow basic acquire operations."""
        limiter = AsyncRateLimiter(rate_per_second=10.0)

        # Should complete quickly for first few acquires
        for _ in range(5):
            await limiter.acquire()

        # If we got here, basic functionality works
        assert True

    @pytest.mark.asyncio
    async def test_rate_limiter_throttles_when_exhausted(self):
        """Should throttle when tokens exhausted."""
        # Very low rate to ensure throttling
        limiter = AsyncRateLimiter(rate_per_second=2.0)

        start = asyncio.get_event_loop().time()

        # Rapidly exhaust tokens
        for _ in range(5):
            await limiter.acquire()

        elapsed = asyncio.get_event_loop().time() - start

        # Should take some time due to throttling
        assert elapsed > 0.5  # At least some delay


# ---------------------------------------------------------------------------
# Tests for Executor Initialization
# ---------------------------------------------------------------------------


class TestForEachExecutorInit:
    """Tests for ForEachNodeExecutor initialization."""

    def test_executor_initializes_with_dependencies(
        self,
        mock_execution_history_service,
        mock_ws_notifier,
        mock_subgraph_executor,
        mock_graph_manager,
    ):
        """Should initialize with all dependencies."""
        executor = ForEachNodeExecutor(
            execution_history_service=mock_execution_history_service,
            ws_notifier=mock_ws_notifier,
            subgraph_executor=mock_subgraph_executor,
            graph_manager=mock_graph_manager,
        )

        assert executor is not None
        assert executor.database_tracker is not None
        assert executor.notification_handler is not None

    def test_executor_initializes_with_none_dependencies(self):
        """Should initialize with None dependencies (graceful handling)."""
        executor = ForEachNodeExecutor(
            execution_history_service=None,
            ws_notifier=None,
            subgraph_executor=None,
            graph_manager=None,
        )

        assert executor is not None


# ---------------------------------------------------------------------------
# Tests for ForEachConfig
# ---------------------------------------------------------------------------


class TestForEachConfig:
    """Tests for ForEachConfig dataclass."""

    def test_config_defaults(self):
        """Should have sensible defaults."""
        config = ForEachConfig()

        assert config.concurrency_limit == 5
        assert config.max_iterations == 1000
        assert config.error_strategy == "continue_on_error"
        assert config.max_retries_per_item == 0
        assert config.rate_limit_per_second is None

    def test_config_custom_values(self):
        """Should accept custom values."""
        config = ForEachConfig(
            source_node_id="my-source",
            field_path="data.items",
            concurrency_limit=10,
            max_iterations=500,
            error_strategy="fail_fast",
            rate_limit_per_second=5.0,
            max_retries_per_item=3,
        )

        assert config.source_node_id == "my-source"
        assert config.field_path == "data.items"
        assert config.concurrency_limit == 10
        assert config.max_iterations == 500
        assert config.error_strategy == "fail_fast"
        assert config.rate_limit_per_second == 5.0
        assert config.max_retries_per_item == 3


# ---------------------------------------------------------------------------
# Test System Limit Ceilings
# ---------------------------------------------------------------------------


class TestSystemLimitCeilings:
    """System ceilings bound what a single For Each node can fan out.

    Per-node limits are honoured when stricter, and clamped when they exceed
    the ceiling, so the safety cap cannot be disabled from a workflow.
    """

    @staticmethod
    def _resolve(config):
        return ForEachNodeExecutor._resolve_limits(config, "Test For Each")

    def test_limits_within_ceilings_are_unchanged(self):
        """Configured values at or below the ceilings pass through."""
        config = ForEachConfig(max_iterations=1000, concurrency_limit=5)

        assert self._resolve(config) == (1000, 5)

    def test_stricter_limits_are_honoured(self):
        """A workflow may always lower its own limits."""
        config = ForEachConfig(max_iterations=50, concurrency_limit=2)

        assert self._resolve(config) == (50, 2)

    def test_excessive_limits_are_clamped(self):
        """A runaway config is capped at the system defaults."""
        config = ForEachConfig(max_iterations=1_000_000, concurrency_limit=500)

        assert self._resolve(config) == (5000, 20)

    def test_ceilings_are_env_configurable(self, monkeypatch):
        """Administrators can raise or lower the ceilings."""
        monkeypatch.setenv("FOR_EACH_MAX_ITEMS", "20000")
        monkeypatch.setenv("FOR_EACH_MAX_CONCURRENCY", "50")
        config = ForEachConfig(max_iterations=1_000_000, concurrency_limit=500)

        assert self._resolve(config) == (20000, 50)

    @pytest.mark.parametrize("value", ["not-a-number", "0", "-5", ""])
    def test_invalid_env_falls_back_to_default(self, monkeypatch, value):
        """A bad env value must never disable the limit it guards."""
        monkeypatch.setenv("FOR_EACH_MAX_ITEMS", value)

        assert ExecutionConfig.get_for_each_max_items() == 5000

    def test_concurrency_default(self):
        """Default concurrency ceiling matches the UI slider maximum."""
        assert ExecutionConfig.get_for_each_max_concurrency() == 20


# ---------------------------------------------------------------------------
# Test Deliberate Item Subsets (item_limit)
# ---------------------------------------------------------------------------


class TestItemLimit:
    """item_limit processes the first N items on purpose, and says so.

    Distinct from max_iterations, which fails rather than dropping data.
    """

    @staticmethod
    def _apply(items, **config_kwargs):
        return ForEachNodeExecutor._apply_item_limit(
            items, ForEachConfig(**config_kwargs), "Test For Each"
        )

    @pytest.fixture
    def items(self):
        """A source array larger than any limit used in these tests."""
        return [{"i": n} for n in range(110)]

    def test_limit_trims_to_first_n(self, items):
        """Only the first N items are processed; the rest are counted."""
        trimmed, skipped = self._apply(items, item_limit=3)

        assert trimmed == [{"i": 0}, {"i": 1}, {"i": 2}]
        assert skipped == 107

    def test_no_limit_processes_everything(self, items):
        """Unset item_limit leaves the array untouched."""
        assert self._apply(items) == (items, 0)

    def test_limit_larger_than_source_is_a_no_op(self, items):
        """A limit above the item count does not mark the run partial."""
        assert self._apply(items, item_limit=500) == (items, 0)

    @pytest.mark.parametrize("value", [0, -1, None])
    def test_non_positive_limit_means_no_limit(self, items, value):
        """A non-positive limit must never mean 'process nothing'."""
        assert self._apply(items, item_limit=value) == (items, 0)

    def test_subset_of_huge_source_stays_within_safety_cap(self):
        """Requesting a few rows of a large source is not a cap breach."""
        huge = [{"i": n} for n in range(50_000)]

        trimmed, skipped = self._apply(huge, item_limit=3, max_iterations=1000)
        max_items, _ = ForEachNodeExecutor._resolve_limits(
            ForEachConfig(item_limit=3, max_iterations=1000), "Test For Each"
        )

        assert len(trimmed) == 3
        assert skipped == 49_997
        assert len(trimmed) <= max_items


class TestPartialRunReporting:
    """A partial run must never look like a complete one."""

    @pytest.fixture
    def executor(self, mock_execution_history_service, mock_ws_notifier):
        return ForEachNodeExecutor(
            execution_history_service=mock_execution_history_service,
            ws_notifier=mock_ws_notifier,
        )

    @pytest.fixture
    def results(self):
        from backend.services.nodes.executors.for_each import IterationResult

        return [
            IterationResult(
                index=i,
                status="success",
                input_item={"i": i},
                output={"ok": True},
                duration_seconds=0.1,
            )
            for i in range(3)
        ]

    def test_summary_reports_skipped_items(self, executor, results):
        """Skipped counts and the source total appear in the summary."""
        output = executor._build_output(
            results, [{"i": i} for i in range(3)], skipped=107, source_total=110
        )
        summary = output["fields"]["summary"]

        assert summary["total"] == 3
        assert summary["source_total"] == 110
        assert summary["skipped"] == 107
        assert summary["partial"] is True

    def test_raw_message_states_the_subset(self, executor, results):
        """The human-readable summary names both counts."""
        output = executor._build_output(
            results, [{"i": i} for i in range(3)], skipped=107, source_total=110
        )

        assert "3 of 110" in output["raw"]

    def test_full_run_is_not_marked_partial(self, executor, results):
        """A complete run keeps its original reporting."""
        output = executor._build_output(results, [{"i": i} for i in range(3)])
        summary = output["fields"]["summary"]

        assert summary["partial"] is False
        assert summary["skipped"] == 0
        assert summary["source_total"] == 3
