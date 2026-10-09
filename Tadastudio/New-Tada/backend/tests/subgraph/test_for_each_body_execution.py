"""Integration tests for For Each body execution.

These tests verify the fix for the For Each node bug where the loop body
never executed: `ForEachNodeExecutor._execute_body()` called
`SubgraphExecutor.execute_for_each_body(...)`, a method that did not exist,
so every iteration silently fell back to echoing the input item instead of
running the configured body nodes.

Coverage:
- `SubgraphExecutor.execute_for_each_body` in isolation: body traversal,
  chaining, END-node stop condition, CONDITION branching, and graceful
  handling of missing config/graph/executors.
- `ForEachNodeExecutor.execute()` end-to-end: a real For Each node with a
  body containing an "AGENT-like" node produces real per-item output
  (not a passthrough of the source item), aggregates it correctly, and
  respects the `continue_on_error` error strategy when a body node fails
  for a specific item.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from backend.models.workflow import NodeType
from backend.models.workflow.configs.for_each import ForEachConfig
from backend.services.nodes.base import BaseNodeExecutor
from backend.services.nodes.registry import NodeExecutorRegistry
from backend.services.nodes.executors.for_each import ForEachNodeExecutor
from backend.services.subgraph.executor import SubgraphExecutor


# ---------------------------------------------------------------------------
# Mock graph/node data classes (mirrors backend/tests/graph/test_for_each_internal_nodes.py)
# ---------------------------------------------------------------------------


@dataclass
class MockEnhancedNodeData:
    """Minimal stand-in for EnhancedNodeData."""

    uniq_id: str = ""
    name: str = ""
    type: NodeType = NodeType.AGENT
    nexts: List[str] = field(default_factory=list)
    true_next: Optional[str] = None
    false_next: Optional[str] = None
    for_each_config: Optional[ForEachConfig] = None
    is_sub_agent: bool = False


@dataclass
class MockConnection:
    """Minimal stand-in for a graph connection."""

    source_id: str = ""
    target_id: str = ""
    source_handle: Optional[str] = None
    label: Optional[str] = None
    connection_type: str = "workflow"


@dataclass
class MockGraphData:
    """Minimal stand-in for GraphData."""

    name: str = "TestWorkflow"
    nodes: List[MockEnhancedNodeData] = field(default_factory=list)
    connections: List[MockConnection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fake node executors used to populate the NodeExecutorRegistry in tests
# ---------------------------------------------------------------------------


class RecordingNodeExecutor(BaseNodeExecutor):
    """Records call order and returns a canned `node_output` per node id.

    Optionally raises for specific node ids to exercise error handling.
    """

    def __init__(
        self,
        outputs: Dict[str, Dict[str, Any]],
        calls: List[str],
        raise_for: Optional[Dict[str, Exception]] = None,
    ):
        super().__init__(
            execution_history_service=None, ws_notifier=None, subgraph_executor=None
        )
        self._outputs = outputs
        self._calls = calls
        self._raise_for = raise_for or {}

    async def execute(
        self,
        node: Any,
        state: Dict[str, Any],
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._calls.append(node.uniq_id)

        if node.uniq_id in self._raise_for:
            raise self._raise_for[node.uniq_id]

        output = self._outputs.get(
            node.uniq_id,
            {"raw": node.uniq_id, "structured": None, "fields": {}},
        )
        return {
            "node_output": output,
            "execution_order": state.get("execution_order", 0) + 1,
        }


class RecordingConditionExecutor(BaseNodeExecutor):
    """Fake CONDITION executor mirroring the real one's state side-effect.

    The real `ConditionNodeExecutor.execute()` mutates
    `state[f"__condition_result_{node.uniq_id}"]` directly (rather than
    returning a "node_output") - this fake replicates that contract so the
    branching logic in `SubgraphExecutor.execute_for_each_body` can be
    tested faithfully.
    """

    def __init__(self, branch_by_node: Dict[str, str], calls: List[str]):
        super().__init__(
            execution_history_service=None, ws_notifier=None, subgraph_executor=None
        )
        self._branch_by_node = branch_by_node
        self._calls = calls

    async def execute(
        self,
        node: Any,
        state: Dict[str, Any],
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._calls.append(node.uniq_id)
        result = self._branch_by_node.get(node.uniq_id, "true")
        state[f"__condition_result_{node.uniq_id}"] = result
        return {
            "branch_taken": 0 if result == "true" else 1,
            "source_handle": result,
            "condition_result": result,
        }


@pytest.fixture(autouse=True)
def registry_sandbox():
    """Snapshot and restore the NodeExecutorRegistry around each test.

    The registry is a process-wide singleton; tests must not leak
    registrations into other test modules that run in the same session.
    """
    executors_snapshot = dict(NodeExecutorRegistry._executors)
    factories_snapshot = dict(NodeExecutorRegistry._factories)
    instances_snapshot = dict(NodeExecutorRegistry._instances)
    yield
    NodeExecutorRegistry._executors = executors_snapshot
    NodeExecutorRegistry._factories = factories_snapshot
    NodeExecutorRegistry._instances = instances_snapshot


@pytest.fixture
def subgraph_executor():
    """Real SubgraphExecutor under test (subgraph_builder is unused by
    execute_for_each_body, so a mock is fine)."""
    return SubgraphExecutor(subgraph_builder=MagicMock())


def register_agent_executor(
    outputs: Dict[str, Dict[str, Any]],
    calls: List[str],
    raise_for: Optional[Dict[str, Exception]] = None,
):
    NodeExecutorRegistry.register(
        NodeType.AGENT,
        factory=lambda: RecordingNodeExecutor(outputs, calls, raise_for),
    )


def register_condition_executor(branch_by_node: Dict[str, str], calls: List[str]):
    NodeExecutorRegistry.register(
        NodeType.CONDITION,
        factory=lambda: RecordingConditionExecutor(branch_by_node, calls),
    )


# ---------------------------------------------------------------------------
# SubgraphExecutor.execute_for_each_body - unit tests
# ---------------------------------------------------------------------------


class TestExecuteForEachBody:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_body_config(self, subgraph_executor):
        node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=ForEachConfig(),  # body_node_ids/body_entry_node_id empty
        )

        result = await subgraph_executor.execute_for_each_body(
            node, {"node_outputs": {}}, 0, graph=MockGraphData()
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_graph_missing(self, subgraph_executor):
        node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=ForEachConfig(
                body_node_ids=["agent-body"], body_entry_node_id="agent-body"
            ),
        )

        result = await subgraph_executor.execute_for_each_body(
            node, {"node_outputs": {}}, 0, graph=None
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_executes_single_body_node_and_returns_its_output(
        self, subgraph_executor
    ):
        calls: List[str] = []
        register_agent_executor(
            outputs={"agent-body": {"raw": "hello item 0", "structured": {"n": 1}, "fields": {}}},
            calls=calls,
        )

        body_node = MockEnhancedNodeData(
            uniq_id="agent-body", name="Agent Body", type=NodeType.AGENT
        )
        for_each_node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=ForEachConfig(
                body_node_ids=["agent-body"], body_entry_node_id="agent-body"
            ),
        )
        graph = MockGraphData(nodes=[for_each_node, body_node])

        result = await subgraph_executor.execute_for_each_body(
            for_each_node,
            {"node_outputs": {"__for_each_current": {"fields": {"item": "x"}}}},
            0,
            graph=graph,
        )

        assert calls == ["agent-body"]
        assert result == {"raw": "hello item 0", "structured": {"n": 1}, "fields": {}}

    @pytest.mark.asyncio
    async def test_executes_chain_of_body_nodes_in_order(self, subgraph_executor):
        calls: List[str] = []
        register_agent_executor(
            outputs={
                "agent-1": {"raw": "step1", "structured": None, "fields": {}},
                "agent-2": {"raw": "step2", "structured": None, "fields": {}},
            },
            calls=calls,
        )

        agent1 = MockEnhancedNodeData(
            uniq_id="agent-1", type=NodeType.AGENT, nexts=["agent-2"]
        )
        agent2 = MockEnhancedNodeData(
            uniq_id="agent-2", type=NodeType.AGENT, nexts=["end-body"]
        )
        end_body = MockEnhancedNodeData(uniq_id="end-body", type=NodeType.END)
        for_each_node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=ForEachConfig(
                body_node_ids=["agent-1", "agent-2", "end-body"],
                body_entry_node_id="agent-1",
            ),
        )
        graph = MockGraphData(nodes=[for_each_node, agent1, agent2, end_body])

        result = await subgraph_executor.execute_for_each_body(
            for_each_node, {"node_outputs": {}}, 0, graph=graph
        )

        # Executed in order, END node not executed, final output from agent-2
        assert calls == ["agent-1", "agent-2"]
        assert result == {"raw": "step2", "structured": None, "fields": {}}

    @pytest.mark.asyncio
    async def test_downstream_body_node_sees_upstream_output(self, subgraph_executor):
        seen_upstream_output = {}

        class CapturingExecutor(BaseNodeExecutor):
            def __init__(self):
                super().__init__(
                    execution_history_service=None,
                    ws_notifier=None,
                    subgraph_executor=None,
                )

            async def execute(self, node, state, graph, execution_id, user_id=None):
                if node.uniq_id == "agent-1":
                    return {
                        "node_output": {"raw": "from-1", "structured": None, "fields": {}}
                    }
                # agent-2: should be able to read agent-1's output
                seen_upstream_output["value"] = state["node_outputs"].get("agent-1")
                return {
                    "node_output": {"raw": "from-2", "structured": None, "fields": {}}
                }

        NodeExecutorRegistry.register(
            NodeType.AGENT, factory=lambda: CapturingExecutor()
        )

        agent1 = MockEnhancedNodeData(
            uniq_id="agent-1", type=NodeType.AGENT, nexts=["agent-2"]
        )
        agent2 = MockEnhancedNodeData(uniq_id="agent-2", type=NodeType.AGENT, nexts=[])
        for_each_node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=ForEachConfig(
                body_node_ids=["agent-1", "agent-2"], body_entry_node_id="agent-1"
            ),
        )
        graph = MockGraphData(nodes=[for_each_node, agent1, agent2])

        await subgraph_executor.execute_for_each_body(
            for_each_node, {"node_outputs": {}}, 0, graph=graph
        )

        assert seen_upstream_output["value"] == {
            "raw": "from-1",
            "structured": None,
            "fields": {},
        }

    @pytest.mark.asyncio
    async def test_condition_node_branches_true(self, subgraph_executor):
        calls: List[str] = []
        register_condition_executor({"cond": "true"}, calls)
        register_agent_executor(
            outputs={
                "true-branch": {"raw": "true-path", "structured": None, "fields": {}},
                "false-branch": {"raw": "false-path", "structured": None, "fields": {}},
            },
            calls=calls,
        )

        cond = MockEnhancedNodeData(
            uniq_id="cond",
            type=NodeType.CONDITION,
            true_next="true-branch",
            false_next="false-branch",
        )
        true_branch = MockEnhancedNodeData(uniq_id="true-branch", type=NodeType.AGENT)
        false_branch = MockEnhancedNodeData(uniq_id="false-branch", type=NodeType.AGENT)
        for_each_node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=ForEachConfig(
                body_node_ids=["cond", "true-branch", "false-branch"],
                body_entry_node_id="cond",
            ),
        )
        graph = MockGraphData(
            nodes=[for_each_node, cond, true_branch, false_branch]
        )

        result = await subgraph_executor.execute_for_each_body(
            for_each_node, {"node_outputs": {}}, 0, graph=graph
        )

        assert calls == ["cond", "true-branch"]
        assert result == {"raw": "true-path", "structured": None, "fields": {}}

    @pytest.mark.asyncio
    async def test_condition_node_branches_false(self, subgraph_executor):
        calls: List[str] = []
        register_condition_executor({"cond": "false"}, calls)
        register_agent_executor(
            outputs={
                "true-branch": {"raw": "true-path", "structured": None, "fields": {}},
                "false-branch": {"raw": "false-path", "structured": None, "fields": {}},
            },
            calls=calls,
        )

        cond = MockEnhancedNodeData(
            uniq_id="cond",
            type=NodeType.CONDITION,
            true_next="true-branch",
            false_next="false-branch",
        )
        true_branch = MockEnhancedNodeData(uniq_id="true-branch", type=NodeType.AGENT)
        false_branch = MockEnhancedNodeData(uniq_id="false-branch", type=NodeType.AGENT)
        for_each_node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=ForEachConfig(
                body_node_ids=["cond", "true-branch", "false-branch"],
                body_entry_node_id="cond",
            ),
        )
        graph = MockGraphData(
            nodes=[for_each_node, cond, true_branch, false_branch]
        )

        result = await subgraph_executor.execute_for_each_body(
            for_each_node, {"node_outputs": {}}, 0, graph=graph
        )

        assert calls == ["cond", "false-branch"]
        assert result == {"raw": "false-path", "structured": None, "fields": {}}

    @pytest.mark.asyncio
    async def test_missing_executor_stops_traversal_gracefully(
        self, subgraph_executor
    ):
        # No executor registered for AGENT at all -> should not raise
        NodeExecutorRegistry.unregister(NodeType.AGENT)

        body_node = MockEnhancedNodeData(uniq_id="agent-body", type=NodeType.AGENT)
        for_each_node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=ForEachConfig(
                body_node_ids=["agent-body"], body_entry_node_id="agent-body"
            ),
        )
        graph = MockGraphData(nodes=[for_each_node, body_node])

        result = await subgraph_executor.execute_for_each_body(
            for_each_node, {"node_outputs": {}}, 0, graph=graph
        )

        assert result is None


# ---------------------------------------------------------------------------
# ForEachNodeExecutor.execute() - end-to-end integration tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_execution_history_service():
    service = MagicMock()
    service.create_node_execution = MagicMock(return_value={"id": "exec-123"})
    service.start_node_execution = MagicMock()
    service.complete_node_execution = MagicMock()
    service.mark_node_failed = MagicMock()
    return service


@pytest.fixture
def mock_ws_notifier():
    return MagicMock()


def build_for_each_graph(source_output, error_strategy="continue_on_error"):
    """Build a small graph: FOR_EACH -> agent-body -> end-body."""
    for_each_config = ForEachConfig(
        source_node_id="csv-reader",
        field_path="fields.rows",
        concurrency_limit=5,
        max_iterations=1000,
        error_strategy=error_strategy,
        body_node_ids=["agent-body", "end-body"],
        body_entry_node_id="agent-body",
    )
    for_each_node = MockEnhancedNodeData(
        uniq_id="for-each",
        name="For Each",
        type=NodeType.FOR_EACH,
        nexts=["agent-body"],
        for_each_config=for_each_config,
    )
    agent_body = MockEnhancedNodeData(
        uniq_id="agent-body",
        name="Agent Body",
        type=NodeType.AGENT,
        nexts=["end-body"],
    )
    end_body = MockEnhancedNodeData(uniq_id="end-body", type=NodeType.END)

    graph = MockGraphData(nodes=[for_each_node, agent_body, end_body])
    state = {
        "node_outputs": {"csv-reader": source_output},
        "execution_id": "exec-1",
        "db_execution_id": "db-exec-1",
        "execution_order": 0,
    }
    return graph, for_each_node, state


class TestForEachExecutorEndToEnd:
    @pytest.mark.asyncio
    async def test_body_executes_and_produces_real_output_per_item(
        self, mock_execution_history_service, mock_ws_notifier
    ):
        """This is the core regression test for the original bug: each
        iteration's output must come from actually running the body node,
        not from echoing the source item back."""
        calls: List[str] = []

        def make_output(node, state, graph, execution_id, user_id=None):
            item = state["node_outputs"]["__for_each_current"]["fields"]["item"]
            return {
                "node_output": {
                    "raw": f"processed:{item}",
                    "structured": {"processed": item},
                    "fields": {},
                }
            }

        class PerItemExecutor(BaseNodeExecutor):
            def __init__(self):
                super().__init__(
                    execution_history_service=None,
                    ws_notifier=None,
                    subgraph_executor=None,
                )

            async def execute(self, node, state, graph, execution_id, user_id=None):
                calls.append(node.uniq_id)
                return make_output(node, state, graph, execution_id, user_id)

        NodeExecutorRegistry.register(
            NodeType.AGENT, factory=lambda: PerItemExecutor()
        )

        subgraph_executor = SubgraphExecutor(subgraph_builder=MagicMock())
        executor = ForEachNodeExecutor(
            execution_history_service=mock_execution_history_service,
            ws_notifier=mock_ws_notifier,
            subgraph_executor=subgraph_executor,
            graph_manager=MagicMock(),
        )

        graph, for_each_node, state = build_for_each_graph(
            source_output={"fields": {"rows": ["a", "b", "c"]}}
        )

        result = await executor.execute(
            for_each_node, state, graph, execution_id="exec-1"
        )

        node_output = result["node_output"]
        succeeded = node_output["fields"]["succeeded"]

        # 3 iterations, all of them should have run the body node
        assert calls == ["agent-body", "agent-body", "agent-body"]
        assert node_output["fields"]["summary"]["succeeded"] == 3
        assert node_output["fields"]["summary"]["failed"] == 0

        # Real per-item output, not a passthrough of the source item
        produced = {entry["structured"]["processed"] for entry in succeeded}
        assert produced == {"a", "b", "c"}
        for entry in succeeded:
            assert entry["raw"].startswith("processed:")

    @pytest.mark.asyncio
    async def test_continue_on_error_reports_partial_failure(
        self, mock_execution_history_service, mock_ws_notifier
    ):
        class FlakyExecutor(BaseNodeExecutor):
            def __init__(self):
                super().__init__(
                    execution_history_service=None,
                    ws_notifier=None,
                    subgraph_executor=None,
                )

            async def execute(self, node, state, graph, execution_id, user_id=None):
                item = state["node_outputs"]["__for_each_current"]["fields"]["item"]
                if item == "b":
                    raise RuntimeError("boom")
                return {
                    "node_output": {
                        "raw": f"ok:{item}",
                        "structured": {"item": item},
                        "fields": {},
                    }
                }

        NodeExecutorRegistry.register(
            NodeType.AGENT, factory=lambda: FlakyExecutor()
        )

        subgraph_executor = SubgraphExecutor(subgraph_builder=MagicMock())
        executor = ForEachNodeExecutor(
            execution_history_service=mock_execution_history_service,
            ws_notifier=mock_ws_notifier,
            subgraph_executor=subgraph_executor,
            graph_manager=MagicMock(),
        )

        graph, for_each_node, state = build_for_each_graph(
            source_output={"fields": {"rows": ["a", "b", "c"]}},
            error_strategy="continue_on_error",
        )

        result = await executor.execute(
            for_each_node, state, graph, execution_id="exec-1"
        )

        node_output = result["node_output"]
        assert node_output["fields"]["summary"]["succeeded"] == 2
        assert node_output["fields"]["summary"]["failed"] == 1
        failed_entries = node_output["fields"]["failed"]
        assert len(failed_entries) == 1
        assert failed_entries[0]["input"] == "b"
        assert "boom" in failed_entries[0]["error"]

    @pytest.mark.asyncio
    async def test_no_body_configured_falls_back_to_source_item(
        self, mock_execution_history_service, mock_ws_notifier
    ):
        """When a For Each node has no body wired up at all (e.g. nothing
        connected in the editor), it should not error - it should surface
        the source item as the per-iteration output."""
        subgraph_executor = SubgraphExecutor(subgraph_builder=MagicMock())
        executor = ForEachNodeExecutor(
            execution_history_service=mock_execution_history_service,
            ws_notifier=mock_ws_notifier,
            subgraph_executor=subgraph_executor,
            graph_manager=MagicMock(),
        )

        for_each_config = ForEachConfig(
            source_node_id="csv-reader",
            field_path="fields.rows",
            body_node_ids=[],
            body_entry_node_id=None,
        )
        for_each_node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            nexts=[],
            for_each_config=for_each_config,
        )
        graph = MockGraphData(nodes=[for_each_node])
        state = {
            "node_outputs": {"csv-reader": {"fields": {"rows": ["a", "b"]}}},
            "execution_id": "exec-1",
            "db_execution_id": "db-exec-1",
            "execution_order": 0,
        }

        result = await executor.execute(
            for_each_node, state, graph, execution_id="exec-1"
        )

        node_output = result["node_output"]
        assert node_output["fields"]["summary"]["succeeded"] == 2
        succeeded = node_output["fields"]["succeeded"]
        # Falls back to the virtual "__for_each_current" output (item passthrough)
        items = {entry["fields"]["item"] for entry in succeeded}
        assert items == {"a", "b"}


# ---------------------------------------------------------------------------
# Body traversal: which nodes count as the next step
# ---------------------------------------------------------------------------


def _body_config(node_ids: List[str], entry: str) -> ForEachConfig:
    return ForEachConfig(body_node_ids=list(node_ids), body_entry_node_id=entry)


class TestBodyTraversal:
    """`nexts` mixes flow steps, tool nodes, sub-agents and stale ids.

    Only real flow steps may be walked, matching how the main graph builds
    edges (EdgeBuilder._should_skip_connection).
    """

    @pytest.mark.asyncio
    async def test_dangling_next_does_not_end_the_body(self, subgraph_executor):
        """A `nexts` entry pointing at a deleted node must be ignored.

        Previously the walker followed the stale id, failed to resolve it and
        silently stopped, leaving the rest of the body unexecuted.
        """
        calls: List[str] = []
        register_agent_executor({}, calls)
        nodes = [
            MockEnhancedNodeData(
                uniq_id="a", name="A", nexts=["deleted-node-id", "b"]
            ),
            MockEnhancedNodeData(uniq_id="b", name="B"),
        ]
        node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=_body_config(["a", "b", "deleted-node-id"], "a"),
        )

        await subgraph_executor.execute_for_each_body(
            node, {"node_outputs": {}}, 0, graph=MockGraphData(nodes=nodes)
        )

        assert calls == ["a", "b"]

    @pytest.mark.asyncio
    async def test_tool_nodes_are_not_walked_as_steps(self, subgraph_executor):
        """Tool nodes are invoked inside their agent, never as a next step."""
        calls: List[str] = []
        register_agent_executor({}, calls)
        nodes = [
            MockEnhancedNodeData(uniq_id="a", name="A", nexts=["search", "b"]),
            MockEnhancedNodeData(
                uniq_id="search", name="Doc Search", type=NodeType.DOCUMENT_SEARCH
            ),
            MockEnhancedNodeData(uniq_id="b", name="B"),
        ]
        node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=_body_config(["a", "search", "b"], "a"),
        )

        await subgraph_executor.execute_for_each_body(
            node, {"node_outputs": {}}, 0, graph=MockGraphData(nodes=nodes)
        )

        assert calls == ["a", "b"]

    @pytest.mark.asyncio
    async def test_delegated_sub_agents_are_not_walked_as_steps(
        self, subgraph_executor
    ):
        """An orchestrator's delegated agents run inside it, not in sequence."""
        calls: List[str] = []
        register_agent_executor({}, calls)
        nodes = [
            MockEnhancedNodeData(
                uniq_id="orch", name="Orchestrator", nexts=["translator", "b"]
            ),
            MockEnhancedNodeData(
                uniq_id="translator", name="Translator", is_sub_agent=True
            ),
            MockEnhancedNodeData(uniq_id="b", name="B"),
        ]
        node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=_body_config(["orch", "translator", "b"], "orch"),
        )

        await subgraph_executor.execute_for_each_body(
            node, {"node_outputs": {}}, 0, graph=MockGraphData(nodes=nodes)
        )

        assert calls == ["orch", "b"]

    @pytest.mark.asyncio
    async def test_fan_out_runs_every_branch(self, subgraph_executor):
        """A node with several flow successors runs all of them."""
        calls: List[str] = []
        register_agent_executor({}, calls)
        nodes = [
            MockEnhancedNodeData(uniq_id="a", name="A", nexts=["b", "c"]),
            MockEnhancedNodeData(uniq_id="b", name="B"),
            MockEnhancedNodeData(uniq_id="c", name="C"),
        ]
        node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=_body_config(["a", "b", "c"], "a"),
        )

        await subgraph_executor.execute_for_each_body(
            node, {"node_outputs": {}}, 0, graph=MockGraphData(nodes=nodes)
        )

        assert calls[0] == "a"
        assert sorted(calls[1:]) == ["b", "c"]

    @pytest.mark.asyncio
    async def test_join_node_runs_once_after_both_branches(self, subgraph_executor):
        """A node fed by two branches runs a single time, after both."""
        calls: List[str] = []
        register_agent_executor({}, calls)
        nodes = [
            MockEnhancedNodeData(uniq_id="a", name="A", nexts=["b", "c"]),
            MockEnhancedNodeData(uniq_id="b", name="B", nexts=["d"]),
            MockEnhancedNodeData(uniq_id="c", name="C", nexts=["d"]),
            MockEnhancedNodeData(uniq_id="d", name="D"),
        ]
        node = MockEnhancedNodeData(
            uniq_id="for-each",
            type=NodeType.FOR_EACH,
            for_each_config=_body_config(["a", "b", "c", "d"], "a"),
        )

        await subgraph_executor.execute_for_each_body(
            node, {"node_outputs": {}}, 0, graph=MockGraphData(nodes=nodes)
        )

        assert calls.count("d") == 1
        assert calls.index("d") > calls.index("b")
        assert calls.index("d") > calls.index("c")


class TestConditionRoutingFromConnections:
    """Condition branches follow the drawn edges, not stale node fields."""

    @staticmethod
    def _graph():
        nodes = [
            MockEnhancedNodeData(uniq_id="cond", name="Is Verified",
                                 type=NodeType.CONDITION, nexts=["t", "f"],
                                 true_next=None, false_next="t"),
            MockEnhancedNodeData(uniq_id="t", name="TrueBranch"),
            MockEnhancedNodeData(uniq_id="f", name="FalseBranch"),
        ]
        connections = [
            MockConnection(source_id="cond", target_id="t", source_handle="branch-0"),
            MockConnection(source_id="cond", target_id="f", source_handle="branch-1"),
        ]
        return MockGraphData(nodes=nodes, connections=connections)

    def test_binary_keys_map_true_to_branch_zero(self, subgraph_executor):
        """Binary mode keys the true branch "0" and the false branch "1"."""
        graph = self._graph()
        routes = subgraph_executor._build_condition_routes(graph)
        nodes_by_id = {n.uniq_id: n for n in graph.nodes}
        cond = nodes_by_id["cond"]

        assert subgraph_executor._next_body_node_ids(
            cond, {"__condition_result_cond": "true"}, nodes_by_id, routes
        ) == ["t"]
        assert subgraph_executor._next_body_node_ids(
            cond, {"__condition_result_cond": "false"}, nodes_by_id, routes
        ) == ["f"]

    def test_connections_win_over_stale_branch_fields(self, subgraph_executor):
        """`false_next` pointing at the true branch must not misroute.

        The fixture mirrors a real workflow where false_next had drifted to the
        node wired to branch-0 (the true branch).
        """
        graph = self._graph()
        routes = subgraph_executor._build_condition_routes(graph)
        nodes_by_id = {n.uniq_id: n for n in graph.nodes}

        result = subgraph_executor._next_body_node_ids(
            nodes_by_id["cond"], {"__condition_result_cond": "false"}, nodes_by_id, routes
        )

        assert result == ["f"]  # not "t", which false_next wrongly points at

    def test_falls_back_to_branch_fields_without_connections(
        self, subgraph_executor
    ):
        """With no matching connection, the node's own fields still work."""
        nodes = [
            MockEnhancedNodeData(uniq_id="cond", name="C", type=NodeType.CONDITION,
                                 nexts=["t", "f"], true_next="t", false_next="f"),
            MockEnhancedNodeData(uniq_id="t", name="T"),
            MockEnhancedNodeData(uniq_id="f", name="F"),
        ]
        nodes_by_id = {n.uniq_id: n for n in nodes}

        assert subgraph_executor._next_body_node_ids(
            nodes_by_id["cond"], {"__condition_result_cond": "true"}, nodes_by_id, {}
        ) == ["t"]
