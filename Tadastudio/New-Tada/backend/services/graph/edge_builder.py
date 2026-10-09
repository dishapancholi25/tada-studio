"""
Edge Builder.

Builds edges for LangGraph StateGraph from workflow connections.
"""

from typing import Dict, List, Set

from langgraph.graph import END
from backend.models.workflow import EnhancedNodeData, GraphData, NodeType
from backend.services.config import get_logger


edge_builder_logger = get_logger("graph.edge_builder")


class EdgeBuilder:
    """
    Builds edges for StateGraph from workflow connections.

    Handles:
    - Normal sequential edges
    - Conditional edges (from CONDITION nodes)
    - Parallel edges (fan-out patterns)
    - Review node edges (agent review loop)
    """

    def __init__(
        self,
        graph_data: GraphData,
        node_map: dict,
        end_nodes: list,
        review_node_map: Dict[str, str] = None,
        subworkflow_internal_ids: Set[str] = None,
    ):
        """
        Initialize the edge builder.

        Args:
            graph_data: The workflow graph definition
            node_map: Map of node IDs to node objects (already added to workflow)
            end_nodes: List of END nodes
            review_node_map: Map of agent_id -> review_node_id (for agents with review)
            subworkflow_internal_ids: Set of node IDs internal to subworkflows
        """
        self.graph_data = graph_data
        self.node_map = node_map
        self.end_nodes = end_nodes
        self.review_node_map = review_node_map or {}
        self.subworkflow_internal_ids = subworkflow_internal_ids or set()
        self.processed_conditions: Set[str] = set()
        self.processed_parallel: Set[str] = set()
        self.processed_review_nodes: Set[str] = set()

    def build_edges(
        self,
        workflow,
        start_node: EnhancedNodeData,
        sub_agent_ids: Set[str],
        tool_node_ids: Set[str],
        condition_function_factory,
    ):
        """
        Build all edges for the StateGraph.

        Args:
            workflow: The StateGraph workflow
            start_node: The START node
            sub_agent_ids: Set of sub-agent node IDs
            tool_node_ids: Set of tool node IDs
            condition_function_factory: Factory for creating condition functions
        """
        # Analyze connection patterns
        source_to_targets = self._analyze_connections(
            start_node, tool_node_ids, sub_agent_ids
        )

        # Log connection types
        self._log_connection_types()

        # Identify parallel branches
        parallel_sources = self._identify_parallel_sources(source_to_targets)

        # Process all connections
        for conn in self.graph_data.connections:
            source_id = conn.source_id
            target_id = conn.target_id

            # Skip various types of connections
            if self._should_skip_connection(
                conn, start_node, tool_node_ids, sub_agent_ids
            ):
                continue

            # Get source node
            source_node = self.node_map.get(source_id)
            if not source_node:
                continue

            # Handle different edge types
            if source_node.type == NodeType.CONDITION:
                self._add_conditional_edge(
                    workflow, source_node, source_id, condition_function_factory
                )
            elif source_id in parallel_sources:
                self._add_parallel_edges(
                    workflow, source_id, parallel_sources[source_id]
                )
            elif source_id not in parallel_sources:
                self._add_normal_edge(workflow, source_id, target_id)

        # FOR_EACH nodes execute their loop body internally per-iteration,
        # so the body's own connections were skipped above (body nodes are
        # internal). Add a direct edge from each FOR_EACH node to whatever
        # its body would have flowed into next (e.g. END, or a node after
        # the loop) so the main graph actually continues past the loop.
        self._add_for_each_exit_edges(workflow)

        # Log summary of all edges for debugging
        edge_builder_logger.info(
            f"All edges built successfully. "
            f"Nodes in graph: {list(self.node_map.keys())}, "
            f"End nodes: {[n.name for n in self.end_nodes]}, "
            f"Subworkflow internal nodes skipped: {list(self.subworkflow_internal_ids)}"
        )

    def _add_for_each_exit_edges(self, workflow):
        """
        Connect FOR_EACH nodes to the node(s) that follow their loop body.

        Since loop body nodes are excluded from the main graph (they run
        internally, per-iteration, inside the FOR_EACH node's own function),
        the normal connection-based edge from FOR_EACH -> body-entry is
        always skipped. Without this, the FOR_EACH node would have zero
        outgoing edges and the workflow would silently dead-end after the
        loop instead of continuing to END or the next node.

        Args:
            workflow: The StateGraph workflow
        """
        end_node_ids = {n.uniq_id for n in self.end_nodes}

        for node in self.graph_data.nodes:
            if node.type != NodeType.FOR_EACH:
                continue

            config = node.for_each_config
            exit_node_ids = getattr(config, "body_exit_node_ids", None) if config else None
            if not exit_node_ids:
                continue

            for exit_id in exit_node_ids:
                if exit_id in end_node_ids:
                    workflow.add_edge(node.uniq_id, END)
                    edge_builder_logger.info(
                        f"Added FOR_EACH exit edge from {node.name} to END"
                    )
                elif exit_id in self.node_map:
                    workflow.add_edge(node.uniq_id, exit_id)
                    edge_builder_logger.info(
                        f"Added FOR_EACH exit edge from {node.name} to {exit_id}"
                    )
                else:
                    edge_builder_logger.warning(
                        f"FOR_EACH exit target {exit_id} for '{node.name}' not "
                        "found in main graph nodes; skipping edge"
                    )

    def _analyze_connections(
        self,
        start_node: EnhancedNodeData,
        tool_node_ids: Set[str],
        sub_agent_ids: Set[str],
    ) -> Dict[str, List[str]]:
        """
        Analyze connection patterns to detect parallel branches.

        Args:
            start_node: The START node
            tool_node_ids: Set of tool node IDs
            sub_agent_ids: Set of sub-agent node IDs

        Returns:
            Map of source node IDs to target node IDs
        """
        source_to_targets = {}

        for conn in self.graph_data.connections:
            if (
                conn.connection_type != "tool"
                and conn.source_id not in tool_node_ids
                and conn.target_id not in tool_node_ids
                and conn.source_id not in sub_agent_ids
                and conn.target_id not in sub_agent_ids
                and conn.source_id not in self.subworkflow_internal_ids
                and conn.target_id not in self.subworkflow_internal_ids
                and conn.source_id != start_node.uniq_id
            ):
                if conn.source_id not in source_to_targets:
                    source_to_targets[conn.source_id] = []
                # Defense-in-depth: Deduplicate targets to avoid duplicate edges
                if conn.target_id not in source_to_targets[conn.source_id]:
                    source_to_targets[conn.source_id].append(conn.target_id)

        return source_to_targets

    def _log_connection_types(self):
        """Log connection types for debugging."""
        tool_connections = [
            c for c in self.graph_data.connections if c.connection_type == "tool"
        ]
        workflow_connections = [
            c for c in self.graph_data.connections if c.connection_type == "workflow"
        ]
        edge_builder_logger.info(
            f"Processing connections - Tool: {len(tool_connections)}, "
            f"Workflow: {len(workflow_connections)}"
        )

    def _identify_parallel_sources(
        self, source_to_targets: Dict[str, List[str]]
    ) -> Dict[str, List[str]]:
        """
        Identify nodes with parallel branches.

        Args:
            source_to_targets: Map of source to target nodes

        Returns:
            Map of parallel source nodes to their targets
        """
        parallel_sources = {}

        for source_id, targets in source_to_targets.items():
            source_node = self.node_map.get(source_id)
            if (
                source_node
                and source_node.type != NodeType.CONDITION
                and len(targets) > 1
            ):
                parallel_sources[source_id] = targets
                edge_builder_logger.info(
                    f"Detected parallel branch from {source_node.name} "
                    f"to {len(targets)} targets: {targets}"
                )

        return parallel_sources

    def _should_skip_connection(
        self,
        conn,
        start_node: EnhancedNodeData,
        tool_node_ids: Set[str],
        sub_agent_ids: Set[str],
    ) -> bool:
        """
        Determine if a connection should be skipped.

        Args:
            conn: The connection
            start_node: The START node
            tool_node_ids: Set of tool node IDs
            sub_agent_ids: Set of sub-agent node IDs

        Returns:
            True if connection should be skipped
        """
        # Skip START node connections
        if conn.source_id == start_node.uniq_id:
            return True

        # Skip tool connections
        if conn.connection_type == "tool":
            edge_builder_logger.info(
                f"Skipping tool connection (internal to agent): "
                f"{conn.source_id} -> {conn.target_id}"
            )
            return True

        # Skip connections to/from tool nodes
        if conn.source_id in tool_node_ids or conn.target_id in tool_node_ids:
            edge_builder_logger.info(
                f"Skipping connection involving tool node: "
                f"{conn.source_id} -> {conn.target_id}"
            )
            return True

        # Skip connections to/from sub-agent nodes
        if conn.source_id in sub_agent_ids or conn.target_id in sub_agent_ids:
            if conn.connection_type == "delegation":
                edge_builder_logger.debug(
                    f"Skipping delegation connection from "
                    f"{conn.source_id} to {conn.target_id}"
                )
            else:
                edge_builder_logger.warning(
                    f"Unexpected non-delegation connection to sub-agent: "
                    f"{conn.source_id} -> {conn.target_id}"
                )
            return True

        # Skip connections involving subworkflow internal nodes
        if (
            conn.source_id in self.subworkflow_internal_ids
            or conn.target_id in self.subworkflow_internal_ids
        ):
            edge_builder_logger.info(
                f"Skipping connection involving subworkflow internal node: "
                f"{conn.source_id} -> {conn.target_id}"
            )
            return True

        return False

    def _add_conditional_edge(
        self,
        workflow,
        source_node: EnhancedNodeData,
        source_id: str,
        condition_function_factory,
    ):
        """
        Add conditional edges from a CONDITION node.

        Args:
            workflow: The StateGraph workflow
            source_node: The condition source node
            source_id: Source node ID
            condition_function_factory: Factory for creating condition functions
        """
        # Only process each condition node once
        if source_id in self.processed_conditions:
            return
        self.processed_conditions.add(source_id)

        # Create condition function
        condition_func = condition_function_factory.create_condition_function(
            source_node, self.graph_data
        )

        # Get all possible targets from this condition
        targets = self._get_condition_targets(source_id)

        # Add default routing if needed
        targets = self._add_default_routing(targets)

        workflow.add_conditional_edges(source_id, condition_func, targets)
        edge_builder_logger.info(
            f"Added conditional edges from {source_id} with targets: {targets}"
        )

    def _get_condition_targets(self, source_id: str) -> Dict[str, str]:
        """
        Get all targets for a condition node.

        Args:
            source_id: Condition node ID

        Returns:
            Map of routing keys to target node IDs
        """
        targets = {}
        end_node_ids = [n.uniq_id for n in self.end_nodes]

        for c in self.graph_data.connections:
            if c.source_id == source_id:
                # Determine routing key
                if c.source_handle:
                    routing_key = c.source_handle.replace("branch-", "")
                elif c.label:
                    routing_key = c.label
                else:
                    routing_key = "default"

                # Map to target node or END
                if c.target_id in end_node_ids:
                    targets[routing_key] = END
                else:
                    targets[routing_key] = c.target_id

                edge_builder_logger.debug(
                    f"Condition routing: {routing_key} -> {c.target_id}"
                )

        return targets

    def _add_default_routing(self, targets: Dict[str, str]) -> Dict[str, str]:
        """
        Add default routing for edge cases.

        Binary mode uses "0" (true branch) and "1" (false branch) as routing keys.
        Multi-branch mode uses branch indices ("0", "1", "2", etc.).

        Args:
            targets: Current targets map

        Returns:
            Updated targets map (unchanged for most cases)
        """
        # Log warning if no valid routing keys found
        if not targets:
            edge_builder_logger.warning(
                "No routing targets found for condition. "
                "Ensure connections are properly configured."
            )

        return targets

    def _add_parallel_edges(self, workflow, source_id: str, targets: List[str]):
        """
        Add parallel edges for fan-out pattern.

        Args:
            workflow: The StateGraph workflow
            source_id: Source node ID
            targets: List of target node IDs
        """
        if source_id in self.processed_parallel:
            return
        self.processed_parallel.add(source_id)

        end_node_ids = [n.uniq_id for n in self.end_nodes]

        # Add all edges in one pass for same superstep
        for target in targets:
            if target in end_node_ids:
                workflow.add_edge(source_id, END)
                edge_builder_logger.info(f"Added parallel edge from {source_id} to END")
            else:
                workflow.add_edge(source_id, target)
                edge_builder_logger.info(
                    f"Added parallel edge from {source_id} to {target}"
                )

        edge_builder_logger.info(
            f"Added {len(targets)} parallel edges from {source_id} "
            f"for parallel execution within same superstep"
        )

    def _add_normal_edge(self, workflow, source_id: str, target_id: str):
        """
        Add a normal sequential edge.

        For agents with review nodes, the edge goes:
        Agent → Review Node (conditional) → next node or back to agent

        Args:
            workflow: The StateGraph workflow
            source_id: Source node ID
            target_id: Target node ID
        """
        end_node_ids = [n.uniq_id for n in self.end_nodes]

        # Check if source is an agent with a review node
        if source_id in self.review_node_map:
            review_node_id = self.review_node_map[source_id]

            # Add edge: Agent → Review Node
            workflow.add_edge(source_id, review_node_id)
            edge_builder_logger.info(
                f"Added edge from {source_id} to review node {review_node_id}"
            )

            # Add conditional edges from Review Node (only once)
            if review_node_id not in self.processed_review_nodes:
                self.processed_review_nodes.add(review_node_id)
                self._add_review_conditional_edges(
                    workflow, source_id, review_node_id, target_id, end_node_ids
                )
            return

        # Normal edge handling
        if target_id in end_node_ids:
            workflow.add_edge(source_id, END)
            edge_builder_logger.debug(f"Added edge from {source_id} to END")
        else:
            workflow.add_edge(source_id, target_id)
            edge_builder_logger.debug(f"Added edge from {source_id} to {target_id}")

    def _add_review_conditional_edges(
        self,
        workflow,
        agent_id: str,
        review_node_id: str,
        original_target_id: str,
        end_node_ids: List[str],
    ):
        """
        Add conditional edges from a review node.

        Routes:
        - "continue" → original target (or END)
        - "retry" → back to agent (for re-execution with feedback)

        Args:
            workflow: The StateGraph workflow
            agent_id: The agent node ID (for retry routing)
            review_node_id: The review node ID
            original_target_id: Original target from agent
            end_node_ids: List of END node IDs
        """

        def review_router(state):
            """Route based on review decision stored in state.custom_data."""
            # The review node stores route in custom_data["__review_route"]
            # LangGraph applies state updates before calling router
            custom_data = state.get("custom_data") or {}
            route = custom_data.get("__review_route", "continue")
            edge_builder_logger.debug(f"[REVIEW-ROUTER] Decision: {route}")
            return route

        # Determine the continue target
        if original_target_id in end_node_ids:
            continue_target = END
        else:
            continue_target = original_target_id

        routing_map = {
            "continue": continue_target,
            "retry": agent_id,  # Loop back to agent
        }

        workflow.add_conditional_edges(review_node_id, review_router, routing_map)
        edge_builder_logger.info(
            f"Added review conditional edges from {review_node_id}: "
            f"continue → {continue_target}, retry → {agent_id}"
        )
