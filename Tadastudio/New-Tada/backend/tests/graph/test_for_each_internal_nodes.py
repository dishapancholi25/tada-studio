"""Tests for For Each internal node filtering.

These tests verify that nodes internal to For Each loops (body nodes that execute
once per iteration) are correctly identified and excluded from the main workflow graph.

The pattern follows SUBWORKFLOW internal node handling - body nodes are traversed
via BFS from the For Each node's nexts until END nodes are reached.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Optional
from unittest.mock import MagicMock

from backend.models.workflow import NodeType
from backend.models.workflow.base import Connection


# ---------------------------------------------------------------------------
# Mock Data Classes for Testing
# ---------------------------------------------------------------------------


@dataclass
class MockForEachConfig:
    """Mock ForEachConfig for testing."""

    source_node_id: str = ""
    field_path: str = "fields.rows"
    concurrency_limit: int = 5
    max_iterations: int = 1000
    error_strategy: str = "continue_on_error"
    body_node_ids: List[str] = field(default_factory=list)
    body_entry_node_id: Optional[str] = None
    body_exit_node_ids: List[str] = field(default_factory=list)


@dataclass
class MockEnhancedNodeData:
    """Mock EnhancedNodeData for testing graph building."""

    uniq_id: str = ""
    name: str = ""
    type: NodeType = NodeType.START
    nexts: List[str] = field(default_factory=list)
    inputs: List[str] = field(default_factory=list)
    is_sub_agent: bool = False
    agent_config: Optional[object] = None
    for_each_config: Optional[MockForEachConfig] = None


@dataclass
class MockGraphData:
    """Mock GraphData for testing graph building."""

    name: str = "TestWorkflow"
    nodes: List[MockEnhancedNodeData] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fixtures - For Each workflow structures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_for_each_workflow():
    """Create a simple workflow with a For Each loop.

    Structure:
    - Main: Start -> For Each -> End Main
    - For Each body: Agent Body -> End Body
    """
    return MockGraphData(
        name="SimpleForEachWorkflow",
        nodes=[
            # Main workflow nodes
            MockEnhancedNodeData(
                uniq_id="start",
                name="Start",
                type=NodeType.START,
                nexts=["for-each"],
            ),
            MockEnhancedNodeData(
                uniq_id="for-each",
                name="For Each",
                type=NodeType.FOR_EACH,
                nexts=["agent-body"],  # Points to body nodes
                inputs=["start"],
                for_each_config=MockForEachConfig(
                    source_node_id="csv-reader",
                    field_path="fields.rows",
                ),
            ),
            MockEnhancedNodeData(
                uniq_id="end-main",
                name="End Main",
                type=NodeType.END,
                nexts=[],
                inputs=["for-each"],
            ),
            # For Each body nodes
            MockEnhancedNodeData(
                uniq_id="agent-body",
                name="Agent Body",
                type=NodeType.AGENT,
                nexts=["end-body"],
                inputs=["for-each"],
            ),
            MockEnhancedNodeData(
                uniq_id="end-body",
                name="End Body",
                type=NodeType.END,
                nexts=[],
                inputs=["agent-body"],
            ),
        ],
        connections=[
            Connection(source_id="start", target_id="for-each"),
            Connection(source_id="for-each", target_id="agent-body"),
            Connection(source_id="agent-body", target_id="end-body"),
        ],
    )


@pytest.fixture
def for_each_with_chain():
    """Create workflow with For Each having multiple body nodes in chain.

    Structure:
    - Main: Start -> For Each -> End Main
    - For Each body: Agent 1 -> Agent 2 -> Agent 3 -> End Body
    """
    return MockGraphData(
        name="ChainedForEachWorkflow",
        nodes=[
            MockEnhancedNodeData(
                uniq_id="start",
                name="Start",
                type=NodeType.START,
                nexts=["for-each"],
            ),
            MockEnhancedNodeData(
                uniq_id="for-each",
                name="For Each",
                type=NodeType.FOR_EACH,
                nexts=["agent-1"],
                for_each_config=MockForEachConfig(),
            ),
            MockEnhancedNodeData(
                uniq_id="end-main",
                name="End Main",
                type=NodeType.END,
                nexts=[],
            ),
            # Chain of body nodes
            MockEnhancedNodeData(
                uniq_id="agent-1",
                name="Agent 1",
                type=NodeType.AGENT,
                nexts=["agent-2"],
            ),
            MockEnhancedNodeData(
                uniq_id="agent-2",
                name="Agent 2",
                type=NodeType.AGENT,
                nexts=["agent-3"],
            ),
            MockEnhancedNodeData(
                uniq_id="agent-3",
                name="Agent 3",
                type=NodeType.AGENT,
                nexts=["end-body"],
            ),
            MockEnhancedNodeData(
                uniq_id="end-body",
                name="End Body",
                type=NodeType.END,
                nexts=[],
            ),
        ],
        connections=[],
    )


@pytest.fixture
def workflow_with_both_subworkflow_and_for_each():
    """Create workflow with both SUBWORKFLOW and FOR_EACH nodes.

    Structure:
    - Main: Start -> Agent Main -> End Main
    - Subworkflow tool: Sub Agent -> End Sub
    - For Each: Agent Body -> End Body
    """
    return MockGraphData(
        name="MixedWorkflow",
        nodes=[
            # Main workflow
            MockEnhancedNodeData(
                uniq_id="start",
                name="Start",
                type=NodeType.START,
                nexts=["agent-main"],
            ),
            MockEnhancedNodeData(
                uniq_id="agent-main",
                name="Agent Main",
                type=NodeType.AGENT,
                nexts=["for-each"],
            ),
            MockEnhancedNodeData(
                uniq_id="for-each",
                name="For Each",
                type=NodeType.FOR_EACH,
                nexts=["agent-body"],
                for_each_config=MockForEachConfig(),
            ),
            MockEnhancedNodeData(
                uniq_id="end-main",
                name="End Main",
                type=NodeType.END,
                nexts=[],
            ),
            # Subworkflow
            MockEnhancedNodeData(
                uniq_id="subworkflow",
                name="Subworkflow",
                type=NodeType.SUBWORKFLOW,
                nexts=["sub-agent"],
            ),
            MockEnhancedNodeData(
                uniq_id="sub-agent",
                name="Sub Agent",
                type=NodeType.AGENT,
                nexts=["end-sub"],
            ),
            MockEnhancedNodeData(
                uniq_id="end-sub",
                name="End Sub",
                type=NodeType.END,
                nexts=[],
            ),
            # For Each body
            MockEnhancedNodeData(
                uniq_id="agent-body",
                name="Agent Body",
                type=NodeType.AGENT,
                nexts=["end-body"],
            ),
            MockEnhancedNodeData(
                uniq_id="end-body",
                name="End Body",
                type=NodeType.END,
                nexts=[],
            ),
        ],
        connections=[],
    )


@pytest.fixture
def workflow_without_for_each():
    """Simple workflow without any For Each nodes."""
    return MockGraphData(
        name="SimpleWorkflow",
        nodes=[
            MockEnhancedNodeData(
                uniq_id="start",
                name="Start",
                type=NodeType.START,
                nexts=["agent"],
            ),
            MockEnhancedNodeData(
                uniq_id="agent",
                name="Agent",
                type=NodeType.AGENT,
                nexts=["end"],
            ),
            MockEnhancedNodeData(
                uniq_id="end",
                name="End",
                type=NodeType.END,
                nexts=[],
            ),
        ],
        connections=[],
    )


# ---------------------------------------------------------------------------
# Tests for _identify_for_each_internal_nodes (builder.py)
# ---------------------------------------------------------------------------


class TestIdentifyForEachInternalNodes:
    """Tests for identifying nodes internal to For Each loops."""

    def test_identifies_for_each_internal_nodes(self, simple_for_each_workflow):
        """Should identify agent-body and end-body as internal nodes."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_for_each_internal_nodes(
            simple_for_each_workflow
        )

        # Should identify the body nodes
        assert "agent-body" in internal_ids
        assert "end-body" in internal_ids
        assert len(internal_ids) == 2

    def test_does_not_include_main_workflow_nodes(self, simple_for_each_workflow):
        """Main workflow nodes should not be identified as internal."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_for_each_internal_nodes(
            simple_for_each_workflow
        )

        # Main workflow nodes should NOT be in the internal set
        assert "start" not in internal_ids
        assert "for-each" not in internal_ids
        assert "end-main" not in internal_ids

    def test_does_not_include_for_each_node_itself(self, simple_for_each_workflow):
        """The FOR_EACH node itself should not be identified as internal."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_for_each_internal_nodes(
            simple_for_each_workflow
        )

        # The FOR_EACH node should NOT be internal
        assert "for-each" not in internal_ids

    def test_identifies_chain_of_body_nodes(self, for_each_with_chain):
        """Should identify all nodes in a chain of body nodes."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_for_each_internal_nodes(for_each_with_chain)

        # Should identify all 4 body nodes
        assert "agent-1" in internal_ids
        assert "agent-2" in internal_ids
        assert "agent-3" in internal_ids
        assert "end-body" in internal_ids
        assert len(internal_ids) == 4

    def test_returns_empty_set_for_workflow_without_for_each(
        self, workflow_without_for_each
    ):
        """Should return empty set when no For Each nodes exist."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_for_each_internal_nodes(
            workflow_without_for_each
        )

        assert internal_ids == set()

    def test_handles_for_each_with_no_nexts(self):
        """Should handle FOR_EACH nodes that have no nexts defined."""
        from backend.services.graph.builder import GraphBuilder

        graph = MockGraphData(
            name="EmptyForEach",
            nodes=[
                MockEnhancedNodeData(
                    uniq_id="start",
                    name="Start",
                    type=NodeType.START,
                    nexts=["for-each"],
                ),
                MockEnhancedNodeData(
                    uniq_id="for-each",
                    name="For Each",
                    type=NodeType.FOR_EACH,
                    nexts=[],  # No body nodes defined
                    for_each_config=MockForEachConfig(),
                ),
                MockEnhancedNodeData(
                    uniq_id="end",
                    name="End",
                    type=NodeType.END,
                    nexts=[],
                ),
            ],
            connections=[],
        )

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_for_each_internal_nodes(graph)

        # Should return empty set - no body nodes to identify
        assert internal_ids == set()


# ---------------------------------------------------------------------------
# Tests for combined subworkflow and for_each handling
# ---------------------------------------------------------------------------


class TestCombinedInternalNodeFiltering:
    """Tests for filtering both subworkflow and for_each internal nodes."""

    def test_identifies_both_subworkflow_and_for_each_internals(
        self, workflow_with_both_subworkflow_and_for_each
    ):
        """Should identify internal nodes from both SUBWORKFLOW and FOR_EACH."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        subworkflow_ids = builder._identify_subworkflow_internal_nodes(
            workflow_with_both_subworkflow_and_for_each
        )
        for_each_ids = builder._identify_for_each_internal_nodes(
            workflow_with_both_subworkflow_and_for_each
        )

        # Subworkflow internals
        assert "sub-agent" in subworkflow_ids
        assert "end-sub" in subworkflow_ids

        # For Each internals
        assert "agent-body" in for_each_ids
        assert "end-body" in for_each_ids

        # No overlap - distinct sets
        assert subworkflow_ids.isdisjoint(for_each_ids)

    def test_combined_sets_exclude_all_internal_nodes(
        self, workflow_with_both_subworkflow_and_for_each
    ):
        """Combined internal node sets should exclude all body nodes."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        subworkflow_ids = builder._identify_subworkflow_internal_nodes(
            workflow_with_both_subworkflow_and_for_each
        )
        for_each_ids = builder._identify_for_each_internal_nodes(
            workflow_with_both_subworkflow_and_for_each
        )
        combined_ids = subworkflow_ids | for_each_ids

        # Main workflow nodes should NOT be excluded
        assert "start" not in combined_ids
        assert "agent-main" not in combined_ids
        assert "for-each" not in combined_ids
        assert "end-main" not in combined_ids
        assert "subworkflow" not in combined_ids

        # Body nodes SHOULD be excluded
        assert "sub-agent" in combined_ids
        assert "end-sub" in combined_ids
        assert "agent-body" in combined_ids
        assert "end-body" in combined_ids


# ---------------------------------------------------------------------------
# Tests for END node filtering
# ---------------------------------------------------------------------------


class TestForEachEndNodeFiltering:
    """Tests for filtering END nodes to exclude For Each body ends."""

    def test_filters_for_each_internal_end_nodes(self, simple_for_each_workflow):
        """Should filter out end-body, keeping only end-main."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(return_value=MagicMock()),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        # Get internal node IDs
        internal_ids = builder._identify_for_each_internal_nodes(
            simple_for_each_workflow
        )

        # Get all END nodes
        all_end_nodes = [
            n for n in simple_for_each_workflow.nodes if n.type == NodeType.END
        ]

        # Filter END nodes
        filtered_end_nodes = [n for n in all_end_nodes if n.uniq_id not in internal_ids]

        # Should only have End Main
        assert len(filtered_end_nodes) == 1
        assert filtered_end_nodes[0].name == "End Main"
        assert filtered_end_nodes[0].uniq_id == "end-main"

    def test_preserves_all_end_nodes_when_no_for_each(self, workflow_without_for_each):
        """Should preserve all END nodes when no For Each nodes exist."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(return_value=MagicMock()),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_for_each_internal_nodes(
            workflow_without_for_each
        )

        all_end_nodes = [
            n for n in workflow_without_for_each.nodes if n.type == NodeType.END
        ]
        filtered_end_nodes = [n for n in all_end_nodes if n.uniq_id not in internal_ids]

        # Should preserve the single END node
        assert len(filtered_end_nodes) == 1
        assert filtered_end_nodes[0].name == "End"
