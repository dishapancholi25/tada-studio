"""
Graph Builder.

Builds LangGraph StateGraph from workflow definitions.
"""

from typing import Dict, Optional, Set

from langgraph.graph import StateGraph
from backend.models.workflow import EnhancedNodeData, GraphData, NodeType
from backend.services.config import get_logger
from backend.services.nodes.executors.review import ReviewNodeFunctionFactory
from backend.services.workflow.state import WorkflowState

from .edge_builder import EdgeBuilder


graph_builder_logger = get_logger("graph.builder")


class GraphBuilder:
    """
    Builds LangGraph StateGraph from workflow definitions.

    Handles:
    - Node analysis and counting
    - StateGraph creation
    - Node addition (workflow, tool, sub-agent handling)
    - Entry point configuration
    - Edge building (delegates to EdgeBuilder)
    """

    def __init__(
        self,
        node_function_creator,
        tool_node_creator,
        should_use_native_tools_fn,
        condition_function_factory,
        llm_factory=None,
        model_service=None,
    ):
        """
        Initialize the graph builder.

        Args:
            node_function_creator: Function to create node functions
            tool_node_creator: Function to create tool nodes
            should_use_native_tools_fn: Function to check if native tools enabled
            condition_function_factory: Factory for creating condition functions
            llm_factory: Optional LLM factory for LLM review mode
            model_service: Optional model service for LLM review mode
        """
        self.create_node_function = node_function_creator
        self.create_tool_node = tool_node_creator
        self.should_use_native_tools = should_use_native_tools_fn
        self.condition_function_factory = condition_function_factory

        # Review node factory for agents with review enabled
        self.review_node_factory = ReviewNodeFunctionFactory(
            llm_factory=llm_factory,
            model_service=model_service,
        )

    def build(
        self, graph: GraphData, execution_id: str, db_execution_id: Optional[int]
    ) -> StateGraph:
        """
        Build a LangGraph StateGraph from the workflow definition.

        Args:
            graph: The workflow graph definition
            execution_id: Execution identifier
            db_execution_id: Database execution ID

        Returns:
            Configured StateGraph ready for compilation
        """
        graph_builder_logger.info(f"Building StateGraph for {graph.name}")

        # Analyze nodes
        self._analyze_nodes(graph)

        # Create the state graph
        workflow = self._create_state_graph()

        # Find START and END nodes
        start_node, end_nodes = self._find_start_and_end_nodes(graph)

        # Add nodes to the graph
        (
            node_map,
            tool_node_ids,
            sub_agent_ids,
            review_node_map,
            subworkflow_internal_ids,
        ) = self._add_nodes(workflow, graph)

        # Filter end_nodes to exclude subworkflow internal END nodes
        # These are END nodes inside subworkflows that should not be part of the main graph
        original_end_count = len(end_nodes)
        end_nodes = [n for n in end_nodes if n.uniq_id not in subworkflow_internal_ids]
        if len(end_nodes) < original_end_count:
            filtered_count = original_end_count - len(end_nodes)
            graph_builder_logger.info(
                f"Filtered {filtered_count} subworkflow internal END nodes. "
                f"Main graph END nodes: {[n.name for n in end_nodes]}"
            )

        # Set entry point
        self._set_entry_point(workflow, graph, start_node)

        # Build edges
        self._add_edges(
            workflow,
            graph,
            node_map,
            end_nodes,
            start_node,
            sub_agent_ids,
            tool_node_ids,
            review_node_map,
            subworkflow_internal_ids,
        )

        graph_builder_logger.info("StateGraph built successfully")
        return workflow

    def _analyze_nodes(self, graph: GraphData):
        """
        Count and analyze node types.

        Args:
            graph: The workflow graph definition
        """
        tool_nodes_count = len(
            [
                n
                for n in graph.nodes
                if n.type
                in [
                    NodeType.DOCUMENT_SEARCH,
                    NodeType.DATABASE_QUERY,
                    NodeType.HTTP_REQUEST,
                    NodeType.WEB_SEARCH,
                    NodeType.MCP_SERVER,
                    NodeType.DOCUMENT_RETRIEVE,
                ]
            ]
        )

        workflow_nodes_count = len(
            [
                n
                for n in graph.nodes
                if n.type
                not in [
                    NodeType.START,
                    NodeType.END,
                    NodeType.DOCUMENT_SEARCH,
                    NodeType.DATABASE_QUERY,
                    NodeType.HTTP_REQUEST,
                    NodeType.WEB_SEARCH,
                    NodeType.MCP_SERVER,
                    NodeType.DOCUMENT_RETRIEVE,
                ]
                and not n.is_sub_agent
            ]
        )

        graph_builder_logger.info(
            f"Graph contains {len(graph.nodes)} total nodes: "
            f"{workflow_nodes_count} workflow nodes, "
            f"{tool_nodes_count} tool nodes (will be handled internally by agents)"
        )

    def _create_state_graph(self) -> StateGraph:
        """
        Create a new StateGraph with WorkflowState.

        Returns:
            Empty StateGraph
        """
        return StateGraph(WorkflowState)

    def _identify_subworkflow_internal_nodes(self, graph: GraphData) -> Set[str]:
        """
        Identify all nodes that are internal to subworkflows.

        These nodes should not be added to the main graph - they are only
        executed when the subworkflow runs as a tool from an agent.

        Args:
            graph: The workflow graph definition

        Returns:
            Set of node IDs that are internal to subworkflows
        """
        internal_node_ids: Set[str] = set()

        # Find all SUBWORKFLOW nodes
        subworkflow_nodes = [n for n in graph.nodes if n.type == NodeType.SUBWORKFLOW]

        for sw_node in subworkflow_nodes:
            # Traverse from subworkflow's nexts to find all internal nodes
            nodes_to_process = list(sw_node.nexts or [])
            processed: Set[str] = set()

            while nodes_to_process:
                node_id = nodes_to_process.pop(0)
                if node_id in processed:
                    continue
                processed.add(node_id)
                internal_node_ids.add(node_id)

                # Find the node and add its nexts (unless it's an END node)
                node = next((n for n in graph.nodes if n.uniq_id == node_id), None)
                if node and node.type != NodeType.END and node.nexts:
                    nodes_to_process.extend(node.nexts)

            if internal_node_ids:
                graph_builder_logger.info(
                    f"Identified {len(processed)} internal nodes for subworkflow "
                    f"'{sw_node.name}': {[n.name for n in graph.nodes if n.uniq_id in processed]}"
                )

        return internal_node_ids

    def _identify_for_each_internal_nodes(self, graph: GraphData) -> Set[str]:
        """
        Identify all nodes that are internal to For Each loops.

        These nodes should not be added to the main graph - they are only
        executed when the For Each node iterates over its body.

        Uses the same BFS traversal pattern as subworkflow internal node
        identification.

        Args:
            graph: The workflow graph definition

        Returns:
            Set of node IDs that are internal to For Each loops
        """
        internal_node_ids: Set[str] = set()

        # Find all FOR_EACH nodes
        for_each_nodes = [n for n in graph.nodes if n.type == NodeType.FOR_EACH]

        for fe_node in for_each_nodes:
            # Traverse from For Each node's nexts to find all body nodes
            nodes_to_process = list(fe_node.nexts or [])
            processed: Set[str] = set()
            # Nodes the loop body flows into that must remain part of the
            # main graph (e.g. the shared END node, or a node after the
            # loop) — the FOR_EACH node itself needs a real edge to these
            # once its per-iteration body execution completes.
            exit_node_ids: Set[str] = set()

            while nodes_to_process:
                node_id = nodes_to_process.pop(0)
                if node_id in processed:
                    continue

                node = next((n for n in graph.nodes if n.uniq_id == node_id), None)

                # A `nexts` entry can outlive the node it points at (e.g. the
                # node was deleted). Such an id must not become part of the
                # body: body traversal would follow it and stop dead, leaving
                # the rest of the loop body unexecuted.
                if node is None:
                    graph_builder_logger.warning(
                        f"For Each '{fe_node.name}': ignoring connection to "
                        f"unknown node '{node_id}'"
                    )
                    continue

                processed.add(node_id)

                if node.type == NodeType.END:
                    # END nodes must not be swallowed into the loop body -
                    # they belong to the main graph. Record them as an exit
                    # target instead of marking them internal.
                    exit_node_ids.add(node_id)
                    continue

                internal_node_ids.add(node_id)

                if node.nexts:
                    nodes_to_process.extend(node.nexts)

            # Store body node IDs on the For Each config for the executor
            if fe_node.for_each_config and processed:
                fe_node.for_each_config.body_node_ids = list(
                    processed - exit_node_ids
                )
                # Set body entry node as the first next of the For Each node
                if fe_node.nexts:
                    fe_node.for_each_config.body_entry_node_id = fe_node.nexts[0]
                # Nodes to route to directly once the loop finishes, since
                # the body itself is executed internally and excluded from
                # the main graph's edges.
                fe_node.for_each_config.body_exit_node_ids = list(exit_node_ids)

            if processed:
                graph_builder_logger.info(
                    f"Identified {len(internal_node_ids & processed)} internal nodes for For Each "
                    f"'{fe_node.name}': "
                    f"{[n.name for n in graph.nodes if n.uniq_id in (internal_node_ids & processed)]}"
                    + (
                        f"; exits to: {[n.name for n in graph.nodes if n.uniq_id in exit_node_ids]}"
                        if exit_node_ids
                        else ""
                    )
                )

        return internal_node_ids

    def _find_start_and_end_nodes(self, graph: GraphData) -> tuple:
        """
        Find START and END nodes in the graph.

        Args:
            graph: The workflow graph definition

        Returns:
            Tuple of (start_node, end_nodes list)

        Raises:
            ValueError: If no START node found
        """
        start_node = None
        end_nodes = []

        for node in graph.nodes:
            if node.type == NodeType.START:
                start_node = node
            elif node.type == NodeType.END:
                end_nodes.append(node)

        if not start_node:
            raise ValueError("No START node found in graph")

        graph_builder_logger.info(
            f"Found START node: {start_node.name} and {len(end_nodes)} END nodes"
        )

        return start_node, end_nodes

    def _add_nodes(self, workflow: StateGraph, graph: GraphData) -> tuple:
        """
        Add all nodes to the StateGraph.

        Args:
            workflow: The StateGraph
            graph: The workflow graph definition

        Returns:
            Tuple of (node_map, tool_node_ids, sub_agent_ids, review_node_map,
                      subworkflow_internal_ids)
        """
        node_map = {}
        tool_node_map = {}
        tool_node_ids = set()
        sub_agent_ids = set()
        review_node_map: Dict[str, str] = {}  # Maps agent_id -> review_node_id

        # Identify subworkflow internal nodes - these should not be in main graph
        subworkflow_internal_ids = self._identify_subworkflow_internal_nodes(graph)

        # Identify For Each internal (body) nodes - these should not be in main graph
        for_each_internal_ids = self._identify_for_each_internal_nodes(graph)
        subworkflow_internal_ids = subworkflow_internal_ids | for_each_internal_ids

        for node in graph.nodes:
            if node.type == NodeType.START:
                # START is implicit, handled by set_entry_point
                continue
            elif node.type == NodeType.END:
                # END nodes will be handled with edges
                continue
            elif node.uniq_id in subworkflow_internal_ids:
                # Skip nodes that are internal to subworkflows - they are only
                # executed when the subworkflow runs as a tool from an agent
                graph_builder_logger.info(
                    f"Skipping subworkflow internal node: {node.name} ({node.uniq_id})"
                )
                continue
            elif node.is_sub_agent:
                # Sub-agents are executed via delegation
                sub_agent_ids.add(node.uniq_id)
                graph_builder_logger.info(
                    f"Skipping sub-agent node: {node.name} ({node.uniq_id})"
                )
                continue
            elif node.type in [
                NodeType.DOCUMENT_SEARCH,
                NodeType.DATABASE_QUERY,
                NodeType.HTTP_REQUEST,
                NodeType.WEB_SEARCH,
                NodeType.MCP_SERVER,
                NodeType.DOCUMENT_RETRIEVE,
            ]:
                tool_node_ids.add(node.uniq_id)
                if self.should_use_native_tools():
                    self._add_tool_node(workflow, node, graph, tool_node_map)
                else:
                    graph_builder_logger.info(
                        f"Skipping tool node (handled internally by agent): "
                        f"{node.name} ({node.uniq_id}) - Type: {node.type}"
                    )
                continue

            # Add regular workflow node
            self._add_workflow_node(workflow, node, graph, node_map)

            # Check if this is an AGENT with review enabled - add review node
            if node.type == NodeType.AGENT:
                review_node_id = self._maybe_add_review_node(workflow, node)
                if review_node_id:
                    review_node_map[node.uniq_id] = review_node_id

        return (
            node_map,
            tool_node_ids,
            sub_agent_ids,
            review_node_map,
            subworkflow_internal_ids,
        )

    def _add_tool_node(
        self,
        workflow: StateGraph,
        node: EnhancedNodeData,
        graph: GraphData,
        tool_node_map: dict,
    ):
        """
        Add a native tool node to the workflow.

        Args:
            workflow: The StateGraph
            node: The tool node
            graph: The workflow graph definition
            tool_node_map: Map of tool nodes
        """
        tool_node = self.create_tool_node(node, graph)
        if tool_node:
            workflow.add_node(node.uniq_id, tool_node)
            tool_node_map[node.uniq_id] = node
            graph_builder_logger.info(
                f"Added native ToolNode: {node.name} ({node.uniq_id}) - "
                f"Type: {node.type}"
            )
        else:
            graph_builder_logger.info(
                f"Skipping tool node (no ToolNode implementation): "
                f"{node.name} ({node.uniq_id})"
            )

    def _add_workflow_node(
        self,
        workflow: StateGraph,
        node: EnhancedNodeData,
        graph: GraphData,
        node_map: dict,
    ):
        """
        Add a workflow node to the StateGraph.

        Args:
            workflow: The StateGraph
            node: The workflow node
            graph: The workflow graph definition
            node_map: Map of added nodes
        """
        node_func = self.create_node_function(node, graph)
        workflow.add_node(node.uniq_id, node_func)
        node_map[node.uniq_id] = node
        graph_builder_logger.debug(
            f"Added workflow node: {node.name} ({node.uniq_id}) of type {node.type}"
        )

    def _maybe_add_review_node(
        self,
        workflow: StateGraph,
        node: EnhancedNodeData,
    ) -> Optional[str]:
        """
        Add a review node for an agent if review is enabled.

        Args:
            workflow: The StateGraph
            node: The agent node

        Returns:
            The review node ID if added, None otherwise
        """
        # Check if review is enabled for this agent
        if not node.agent_config:
            return None

        review_config = getattr(node.agent_config, "review_config", None)
        if not review_config:
            return None

        # Handle both dict and dataclass
        if isinstance(review_config, dict):
            review_enabled = review_config.get("review_enabled", False)
        else:
            review_enabled = getattr(review_config, "review_enabled", False)

        if not review_enabled:
            return None

        # Create review node
        review_node_id = f"{node.uniq_id}_review"
        review_func = self.review_node_factory.create_review_function(node)
        workflow.add_node(review_node_id, review_func)

        graph_builder_logger.info(
            f"Added review node: {review_node_id} for agent {node.name} ({node.uniq_id})"
        )

        return review_node_id

    def _set_entry_point(
        self, workflow: StateGraph, graph: GraphData, start_node: EnhancedNodeData
    ):
        """
        Set the entry point for the StateGraph.

        Args:
            workflow: The StateGraph
            graph: The workflow graph definition
            start_node: The START node

        Raises:
            ValueError: If no connection from START node found
        """
        # Find first node connected from START
        entry_node_id = None
        for conn in graph.connections:
            if conn.source_id == start_node.uniq_id:
                entry_node_id = conn.target_id
                break

        if entry_node_id:
            workflow.set_entry_point(entry_node_id)
            graph_builder_logger.info(f"Set entry point to: {entry_node_id}")
        else:
            raise ValueError("No connection from START node found")

    def _add_edges(
        self,
        workflow: StateGraph,
        graph: GraphData,
        node_map: dict,
        end_nodes: list,
        start_node: EnhancedNodeData,
        sub_agent_ids: Set[str],
        tool_node_ids: Set[str],
        review_node_map: Dict[str, str],
        subworkflow_internal_ids: Set[str],
    ):
        """
        Add all edges to the StateGraph.

        Args:
            workflow: The StateGraph
            graph: The workflow graph definition
            node_map: Map of added nodes
            end_nodes: List of END nodes
            start_node: The START node
            sub_agent_ids: Set of sub-agent node IDs
            tool_node_ids: Set of tool node IDs
            review_node_map: Map of agent_id -> review_node_id
            subworkflow_internal_ids: Set of node IDs internal to subworkflows
        """
        edge_builder = EdgeBuilder(
            graph, node_map, end_nodes, review_node_map, subworkflow_internal_ids
        )
        edge_builder.build_edges(
            workflow,
            start_node,
            sub_agent_ids,
            tool_node_ids,
            self.condition_function_factory,
        )
