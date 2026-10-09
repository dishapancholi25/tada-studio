"""Tests for subworkflow internal node filtering.

These tests verify that nodes internal to subworkflows (nodes that should only
execute when the subworkflow runs as a tool) are correctly identified and
excluded from the main workflow graph.

The fix addresses the issue where workflows with subworkflows would route to
the subworkflow's END node instead of the main workflow's END node.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Optional
from unittest.mock import MagicMock

from backend.models.workflow import NodeType
from backend.models.workflow.base import Connection
from backend.models.workflow.enums import ConnectionType


# ---------------------------------------------------------------------------
# Mock Data Classes for Testing
# ---------------------------------------------------------------------------


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


@dataclass
class MockGraphData:
    """Mock GraphData for testing graph building."""

    name: str = "TestWorkflow"
    nodes: List[MockEnhancedNodeData] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Fixtures - Based on SubWorkflowTest workflow structure
# ---------------------------------------------------------------------------


@pytest.fixture
def subworkflow_test_nodes():
    """Create nodes matching the SubWorkflowTest workflow structure.

    Structure:
    - Main workflow: Start -> Agent 1 -> End Final
    - Subworkflow (Data Pipeline): Agent 1 (inside) -> End Sub
    - Agent 1 has a tool connection to Data Pipeline
    """
    return [
        # Main workflow nodes
        MockEnhancedNodeData(
            uniq_id="start-001",
            name="Start",
            type=NodeType.START,
            nexts=["agent1-main"],
        ),
        MockEnhancedNodeData(
            uniq_id="agent1-main",
            name="Agent 1",
            type=NodeType.AGENT,
            nexts=["end-final"],
            inputs=["start-001"],
        ),
        MockEnhancedNodeData(
            uniq_id="end-final",
            name="End Final",
            type=NodeType.END,
            nexts=[],
            inputs=["agent1-main"],
        ),
        # Subworkflow entry point
        MockEnhancedNodeData(
            uniq_id="data-pipeline",
            name="Data Pipeline",
            type=NodeType.SUBWORKFLOW,
            nexts=["agent1-inside"],  # Points to internal nodes
            inputs=["agent1-main"],  # Tool connection from main agent
        ),
        # Subworkflow internal nodes
        MockEnhancedNodeData(
            uniq_id="agent1-inside",
            name="Agent 1",  # Same name but different ID
            type=NodeType.AGENT,
            nexts=["end-sub"],
            inputs=["data-pipeline"],
        ),
        MockEnhancedNodeData(
            uniq_id="end-sub",
            name="End Sub",
            type=NodeType.END,
            nexts=[],
            inputs=["agent1-inside"],
        ),
    ]


@pytest.fixture
def subworkflow_test_connections():
    """Create connections matching the SubWorkflowTest workflow structure."""
    return [
        # Main workflow connections
        Connection(
            source_id="start-001",
            target_id="agent1-main",
            connection_type=ConnectionType.WORKFLOW,
        ),
        Connection(
            source_id="agent1-main",
            target_id="end-final",
            connection_type=ConnectionType.WORKFLOW,
        ),
        # Tool connection to subworkflow
        Connection(
            source_id="agent1-main",
            target_id="data-pipeline",
            connection_type=ConnectionType.TOOL,
        ),
        # Subworkflow internal connections
        Connection(
            source_id="data-pipeline",
            target_id="agent1-inside",
            connection_type=ConnectionType.WORKFLOW,
        ),
        Connection(
            source_id="agent1-inside",
            target_id="end-sub",
            connection_type=ConnectionType.WORKFLOW,
        ),
    ]


@pytest.fixture
def subworkflow_test_graph(subworkflow_test_nodes, subworkflow_test_connections):
    """Create complete MockGraphData for SubWorkflowTest."""
    return MockGraphData(
        name="SubWorkflowTest",
        nodes=subworkflow_test_nodes,
        connections=subworkflow_test_connections,
    )


@pytest.fixture
def nested_subworkflow_nodes():
    """Create nodes with nested subworkflows (subworkflow containing another subworkflow).

    Structure:
    - Main: Start -> Main Agent -> End Main
    - Sub1: Agent A -> Sub2 -> End Sub1
    - Sub2: Agent B -> End Sub2
    """
    return [
        # Main workflow
        MockEnhancedNodeData(
            uniq_id="start",
            name="Start",
            type=NodeType.START,
            nexts=["main-agent"],
        ),
        MockEnhancedNodeData(
            uniq_id="main-agent",
            name="Main Agent",
            type=NodeType.AGENT,
            nexts=["end-main"],
        ),
        MockEnhancedNodeData(
            uniq_id="end-main",
            name="End Main",
            type=NodeType.END,
            nexts=[],
        ),
        # Sub1 (first level subworkflow)
        MockEnhancedNodeData(
            uniq_id="sub1",
            name="Sub1",
            type=NodeType.SUBWORKFLOW,
            nexts=["agent-a"],
        ),
        MockEnhancedNodeData(
            uniq_id="agent-a",
            name="Agent A",
            type=NodeType.AGENT,
            nexts=["sub2"],  # Points to nested subworkflow
        ),
        MockEnhancedNodeData(
            uniq_id="end-sub1",
            name="End Sub1",
            type=NodeType.END,
            nexts=[],
        ),
        # Sub2 (nested subworkflow)
        MockEnhancedNodeData(
            uniq_id="sub2",
            name="Sub2",
            type=NodeType.SUBWORKFLOW,
            nexts=["agent-b"],
        ),
        MockEnhancedNodeData(
            uniq_id="agent-b",
            name="Agent B",
            type=NodeType.AGENT,
            nexts=["end-sub2"],
        ),
        MockEnhancedNodeData(
            uniq_id="end-sub2",
            name="End Sub2",
            type=NodeType.END,
            nexts=[],
        ),
    ]


@pytest.fixture
def workflow_without_subworkflows():
    """Simple workflow without any subworkflows."""
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
        connections=[
            Connection(source_id="start", target_id="agent"),
            Connection(source_id="agent", target_id="end"),
        ],
    )


@pytest.fixture
def workflow_with_multiple_end_nodes():
    """Workflow with multiple END nodes (condition branches)."""
    return MockGraphData(
        name="MultiEndWorkflow",
        nodes=[
            MockEnhancedNodeData(
                uniq_id="start",
                name="Start",
                type=NodeType.START,
                nexts=["condition"],
            ),
            MockEnhancedNodeData(
                uniq_id="condition",
                name="Condition",
                type=NodeType.CONDITION,
                nexts=["end-true", "end-false"],
            ),
            MockEnhancedNodeData(
                uniq_id="end-true",
                name="End True",
                type=NodeType.END,
                nexts=[],
            ),
            MockEnhancedNodeData(
                uniq_id="end-false",
                name="End False",
                type=NodeType.END,
                nexts=[],
            ),
        ],
        connections=[],
    )


# ---------------------------------------------------------------------------
# Tests for _identify_subworkflow_internal_nodes (builder.py)
# ---------------------------------------------------------------------------


class TestIdentifySubworkflowInternalNodes:
    """Tests for identifying nodes internal to subworkflows."""

    def test_identifies_subworkflow_internal_nodes(self, subworkflow_test_graph):
        """Should identify Agent 1 (inside) and End Sub as internal nodes."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_subworkflow_internal_nodes(
            subworkflow_test_graph
        )

        # Should identify the two internal nodes
        assert "agent1-inside" in internal_ids
        assert "end-sub" in internal_ids
        assert len(internal_ids) == 2

    def test_does_not_include_main_workflow_nodes(self, subworkflow_test_graph):
        """Main workflow nodes should not be identified as internal."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_subworkflow_internal_nodes(
            subworkflow_test_graph
        )

        # Main workflow nodes should NOT be in the internal set
        assert "start-001" not in internal_ids
        assert "agent1-main" not in internal_ids
        assert "end-final" not in internal_ids

    def test_does_not_include_subworkflow_entry_node(self, subworkflow_test_graph):
        """The SUBWORKFLOW node itself should not be identified as internal."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_subworkflow_internal_nodes(
            subworkflow_test_graph
        )

        # The SUBWORKFLOW entry node should NOT be internal
        assert "data-pipeline" not in internal_ids

    def test_returns_empty_set_for_workflow_without_subworkflows(
        self, workflow_without_subworkflows
    ):
        """Should return empty set when no subworkflows exist."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_subworkflow_internal_nodes(
            workflow_without_subworkflows
        )

        assert internal_ids == set()

    def test_handles_subworkflow_with_no_nexts(self):
        """Should handle SUBWORKFLOW nodes that have no nexts defined."""
        from backend.services.graph.builder import GraphBuilder

        graph = MockGraphData(
            name="EmptySubworkflow",
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
                    uniq_id="subworkflow",
                    name="Empty Subworkflow",
                    type=NodeType.SUBWORKFLOW,
                    nexts=[],  # No internal nodes defined
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

        internal_ids = builder._identify_subworkflow_internal_nodes(graph)

        # Should return empty set - no internal nodes to identify
        assert internal_ids == set()


# ---------------------------------------------------------------------------
# Tests for END node filtering in builder.py
# ---------------------------------------------------------------------------


class TestEndNodeFiltering:
    """Tests for filtering END nodes to exclude subworkflow internal ones."""

    def test_filters_subworkflow_internal_end_nodes(self, subworkflow_test_graph):
        """Should filter out End Sub, keeping only End Final."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(return_value=MagicMock()),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        # Get internal node IDs
        internal_ids = builder._identify_subworkflow_internal_nodes(
            subworkflow_test_graph
        )

        # Get all END nodes
        all_end_nodes = [
            n for n in subworkflow_test_graph.nodes if n.type == NodeType.END
        ]

        # Filter END nodes
        filtered_end_nodes = [n for n in all_end_nodes if n.uniq_id not in internal_ids]

        # Should only have End Final
        assert len(filtered_end_nodes) == 1
        assert filtered_end_nodes[0].name == "End Final"
        assert filtered_end_nodes[0].uniq_id == "end-final"

    def test_preserves_all_end_nodes_when_no_subworkflows(
        self, workflow_without_subworkflows
    ):
        """Should preserve all END nodes when no subworkflows exist."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(return_value=MagicMock()),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_subworkflow_internal_nodes(
            workflow_without_subworkflows
        )

        all_end_nodes = [
            n for n in workflow_without_subworkflows.nodes if n.type == NodeType.END
        ]
        filtered_end_nodes = [n for n in all_end_nodes if n.uniq_id not in internal_ids]

        # Should preserve the single END node
        assert len(filtered_end_nodes) == 1
        assert filtered_end_nodes[0].name == "End"

    def test_preserves_multiple_end_nodes_when_all_in_main_workflow(
        self, workflow_with_multiple_end_nodes
    ):
        """Should preserve all END nodes when all are in main workflow."""
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(return_value=MagicMock()),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_subworkflow_internal_nodes(
            workflow_with_multiple_end_nodes
        )

        all_end_nodes = [
            n for n in workflow_with_multiple_end_nodes.nodes if n.type == NodeType.END
        ]
        filtered_end_nodes = [n for n in all_end_nodes if n.uniq_id not in internal_ids]

        # Should preserve both END nodes
        assert len(filtered_end_nodes) == 2
        end_names = {n.name for n in filtered_end_nodes}
        assert end_names == {"End True", "End False"}


# ---------------------------------------------------------------------------
# Tests for edge skipping in edge_builder.py
# ---------------------------------------------------------------------------


class TestEdgeBuilderSkipsInternalNodes:
    """Tests for EdgeBuilder skipping connections involving internal nodes."""

    def test_skips_connections_with_internal_source(self, subworkflow_test_graph):
        """Should skip connections where source is an internal node."""
        from backend.services.graph.edge_builder import EdgeBuilder

        internal_ids = {"agent1-inside", "end-sub"}
        node_map = {n.uniq_id: n for n in subworkflow_test_graph.nodes}
        end_nodes = [n for n in subworkflow_test_graph.nodes if n.type == NodeType.END]

        edge_builder = EdgeBuilder(
            graph_data=subworkflow_test_graph,
            node_map=node_map,
            end_nodes=end_nodes,
            review_node_map={},
            subworkflow_internal_ids=internal_ids,
        )

        # Test connection from internal node
        internal_conn = Connection(
            source_id="agent1-inside",
            target_id="end-sub",
            connection_type=ConnectionType.WORKFLOW,
        )

        start_node = next(
            n for n in subworkflow_test_graph.nodes if n.type == NodeType.START
        )
        should_skip = edge_builder._should_skip_connection(
            internal_conn, start_node, set(), set()
        )

        assert should_skip is True

    def test_skips_connections_with_internal_target(self, subworkflow_test_graph):
        """Should skip connections where target is an internal node."""
        from backend.services.graph.edge_builder import EdgeBuilder

        internal_ids = {"agent1-inside", "end-sub"}
        node_map = {n.uniq_id: n for n in subworkflow_test_graph.nodes}
        end_nodes = [n for n in subworkflow_test_graph.nodes if n.type == NodeType.END]

        edge_builder = EdgeBuilder(
            graph_data=subworkflow_test_graph,
            node_map=node_map,
            end_nodes=end_nodes,
            review_node_map={},
            subworkflow_internal_ids=internal_ids,
        )

        # Test connection to internal node
        to_internal_conn = Connection(
            source_id="data-pipeline",
            target_id="agent1-inside",
            connection_type=ConnectionType.WORKFLOW,
        )

        start_node = next(
            n for n in subworkflow_test_graph.nodes if n.type == NodeType.START
        )
        should_skip = edge_builder._should_skip_connection(
            to_internal_conn, start_node, set(), set()
        )

        assert should_skip is True

    def test_does_not_skip_main_workflow_connections(self, subworkflow_test_graph):
        """Should not skip connections in main workflow."""
        from backend.services.graph.edge_builder import EdgeBuilder

        internal_ids = {"agent1-inside", "end-sub"}
        node_map = {n.uniq_id: n for n in subworkflow_test_graph.nodes}
        end_nodes = [
            n
            for n in subworkflow_test_graph.nodes
            if n.type == NodeType.END and n.uniq_id not in internal_ids
        ]

        edge_builder = EdgeBuilder(
            graph_data=subworkflow_test_graph,
            node_map=node_map,
            end_nodes=end_nodes,
            review_node_map={},
            subworkflow_internal_ids=internal_ids,
        )

        # Test main workflow connection
        main_conn = Connection(
            source_id="agent1-main",
            target_id="end-final",
            connection_type=ConnectionType.WORKFLOW,
        )

        start_node = next(
            n for n in subworkflow_test_graph.nodes if n.type == NodeType.START
        )
        should_skip = edge_builder._should_skip_connection(
            main_conn, start_node, set(), set()
        )

        # Should NOT skip - this is the main workflow connection
        assert should_skip is False


# ---------------------------------------------------------------------------
# Tests for _process_end_node filtering in workflow_executor.py
# ---------------------------------------------------------------------------


class TestProcessEndNodeFiltering:
    """Tests for filtering END nodes in workflow executor."""

    def test_filters_internal_end_nodes(self, subworkflow_test_graph):
        """Should filter out subworkflow internal END nodes."""
        from backend.services.execution.workflow_executor import (
            _get_subworkflow_internal_node_ids,
        )

        internal_ids = _get_subworkflow_internal_node_ids(subworkflow_test_graph)

        # Should identify the internal nodes
        assert "agent1-inside" in internal_ids
        assert "end-sub" in internal_ids

        # Filter END nodes
        all_end_nodes = [
            n for n in subworkflow_test_graph.nodes if n.type == NodeType.END
        ]
        filtered_end_nodes = [n for n in all_end_nodes if n.uniq_id not in internal_ids]

        # Should only have End Final
        assert len(filtered_end_nodes) == 1
        assert filtered_end_nodes[0].name == "End Final"

    def test_returns_empty_set_for_simple_workflow(self, workflow_without_subworkflows):
        """Should return empty set for workflows without subworkflows."""
        from backend.services.execution.workflow_executor import (
            _get_subworkflow_internal_node_ids,
        )

        internal_ids = _get_subworkflow_internal_node_ids(workflow_without_subworkflows)

        assert internal_ids == set()

    def test_helper_function_matches_builder(self, subworkflow_test_graph):
        """Helper function should produce same results as builder method."""
        from backend.services.graph.builder import GraphBuilder
        from backend.services.execution.workflow_executor import (
            _get_subworkflow_internal_node_ids,
        )

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        builder_ids = builder._identify_subworkflow_internal_nodes(
            subworkflow_test_graph
        )
        executor_ids = _get_subworkflow_internal_node_ids(subworkflow_test_graph)

        # Both should identify the same internal nodes
        assert builder_ids == executor_ids


# ---------------------------------------------------------------------------
# Integration-style Tests
# ---------------------------------------------------------------------------


class TestSubworkflowNodeFilteringIntegration:
    """Integration tests verifying the complete filtering flow."""

    def test_main_workflow_only_reaches_main_end_node(self, subworkflow_test_graph):
        """Verify that graph building excludes internal nodes correctly.

        This test simulates what happens when building a StateGraph:
        - Internal nodes should be identified
        - END nodes list should be filtered
        - Edge builder should receive filtered list
        """
        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(return_value=MagicMock()),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        # Step 1: Find all END nodes
        all_end_nodes = [
            n for n in subworkflow_test_graph.nodes if n.type == NodeType.END
        ]
        assert len(all_end_nodes) == 2  # End Final and End Sub

        # Step 2: Identify internal nodes
        internal_ids = builder._identify_subworkflow_internal_nodes(
            subworkflow_test_graph
        )
        assert len(internal_ids) == 2  # agent1-inside and end-sub

        # Step 3: Filter END nodes
        filtered_end_nodes = [n for n in all_end_nodes if n.uniq_id not in internal_ids]
        assert len(filtered_end_nodes) == 1
        assert filtered_end_nodes[0].name == "End Final"

        # Step 4: Verify filtered list only contains main workflow END
        end_node_ids = {n.uniq_id for n in filtered_end_nodes}
        assert "end-final" in end_node_ids
        assert "end-sub" not in end_node_ids

    def test_subworkflow_with_chain_of_agents(self):
        """Test subworkflow with multiple chained agents."""
        graph = MockGraphData(
            name="ChainedSubworkflow",
            nodes=[
                # Main workflow
                MockEnhancedNodeData(
                    uniq_id="start",
                    name="Start",
                    type=NodeType.START,
                    nexts=["main-agent"],
                ),
                MockEnhancedNodeData(
                    uniq_id="main-agent",
                    name="Main Agent",
                    type=NodeType.AGENT,
                    nexts=["end-main"],
                ),
                MockEnhancedNodeData(
                    uniq_id="end-main",
                    name="End Main",
                    type=NodeType.END,
                    nexts=[],
                ),
                # Subworkflow with chain
                MockEnhancedNodeData(
                    uniq_id="sub",
                    name="Subworkflow",
                    type=NodeType.SUBWORKFLOW,
                    nexts=["chain-1"],
                ),
                MockEnhancedNodeData(
                    uniq_id="chain-1",
                    name="Chain Agent 1",
                    type=NodeType.AGENT,
                    nexts=["chain-2"],
                ),
                MockEnhancedNodeData(
                    uniq_id="chain-2",
                    name="Chain Agent 2",
                    type=NodeType.AGENT,
                    nexts=["chain-3"],
                ),
                MockEnhancedNodeData(
                    uniq_id="chain-3",
                    name="Chain Agent 3",
                    type=NodeType.AGENT,
                    nexts=["end-sub"],
                ),
                MockEnhancedNodeData(
                    uniq_id="end-sub",
                    name="End Sub",
                    type=NodeType.END,
                    nexts=[],
                ),
            ],
            connections=[],
        )

        from backend.services.graph.builder import GraphBuilder

        builder = GraphBuilder(
            node_function_creator=MagicMock(),
            tool_node_creator=MagicMock(),
            should_use_native_tools_fn=MagicMock(return_value=False),
            condition_function_factory=MagicMock(),
        )

        internal_ids = builder._identify_subworkflow_internal_nodes(graph)

        # Should identify all 4 internal nodes
        assert len(internal_ids) == 4
        assert "chain-1" in internal_ids
        assert "chain-2" in internal_ids
        assert "chain-3" in internal_ids
        assert "end-sub" in internal_ids

        # Main workflow nodes should not be internal
        assert "start" not in internal_ids
        assert "main-agent" not in internal_ids
        assert "end-main" not in internal_ids
        assert "sub" not in internal_ids
