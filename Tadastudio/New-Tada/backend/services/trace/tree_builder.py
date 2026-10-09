"""Hierarchical trace tree builder for execution visualization.

Transforms flat execution data into a nested tree structure.
"""

from typing import Any, Dict, List

from ...services.config import get_logger
from .cost_calculator import CostCalculator
from .node_mapper import NodeMapper


logger = get_logger("trace_tree_builder")


class TraceTreeBuilder:
    """Build hierarchical trace tree from flat execution data."""

    def __init__(self):
        """Initialize trace tree builder."""
        self.node_map: Dict[str, Dict[str, Any]] = {}  # Maps database ID -> trace node
        self.node_id_to_db_ids: Dict[
            str, List[str]
        ] = {}  # Maps graph node_id -> list of database IDs
        self.root_nodes: List[Dict[str, Any]] = []

    @classmethod
    def build_trace_tree(cls, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform flat execution data into hierarchical trace tree.

        Args:
            execution_data: Execution dictionary with node_executions list

        Returns:
            Hierarchical trace tree with metadata
        """
        if not execution_data:
            return {"nodes": [], "metadata": {}}

        builder = cls()
        nodes = execution_data.get("node_executions", [])

        logger.info(
            f"Processing {len(nodes)} nodes for execution {execution_data.get('id')}"
        )

        # Build the tree structure
        builder._build_node_map(nodes)
        builder._build_hierarchy(nodes)
        builder._remove_subworkflow_tool_duplicates()
        builder._sort_tree()

        # Calculate aggregate metadata
        metadata = builder._calculate_metadata(execution_data, nodes)

        return {
            "executionId": execution_data["id"],
            "graphName": execution_data["graph_name"],
            "status": execution_data["status"],
            "startTime": execution_data.get("start_time"),
            "endTime": execution_data.get("end_time"),
            "duration": execution_data.get("duration_seconds", 0),
            "nodes": builder.root_nodes,
            "metadata": metadata,
        }

    def _build_node_map(self, nodes: List[Dict[str, Any]]) -> None:
        """
        First pass: Create trace nodes and build lookup maps.

        Args:
            nodes: List of node dictionaries from database
        """
        for node in nodes:
            # Create trace node using NodeMapper
            trace_node = NodeMapper.create_trace_node(node)

            db_id = node["id"]  # Unique database ID
            node_id = node["node_id"]  # Graph node ID (may have duplicates)

            # Store in map using database ID as unique key
            self.node_map[db_id] = trace_node

            # Track which database IDs correspond to each graph node_id
            if node_id not in self.node_id_to_db_ids:
                self.node_id_to_db_ids[node_id] = []
            self.node_id_to_db_ids[node_id].append(db_id)

        logger.info(f"Node map contains {len(self.node_map)} unique database entries")
        logger.info(f"Found {len(self.node_id_to_db_ids)} unique graph node IDs")

        # Log duplicate node_id executions
        duplicates = {
            nid: db_ids
            for nid, db_ids in self.node_id_to_db_ids.items()
            if len(db_ids) > 1
        }
        if duplicates:
            logger.info(f"Found {len(duplicates)} node IDs with multiple executions:")
            for nid, db_ids in duplicates.items():
                logger.info(f"  - Node {nid}: {len(db_ids)} executions")

        # Log missing parent references
        self._log_missing_parents(nodes)

    def _log_missing_parents(self, nodes: List[Dict[str, Any]]) -> None:
        """
        Log warnings for parent IDs that don't exist in node map.

        Args:
            nodes: List of node dictionaries
        """
        missing_parents = set()
        for node in nodes:
            parent_id = node.get("parent_agent_id")
            # parent_agent_id is a database execution ID (FK to node_executions.id)
            if parent_id and parent_id not in self.node_map:
                missing_parents.add(parent_id)

        if missing_parents:
            logger.warning(
                f"Found {len(missing_parents)} parent execution IDs that don't exist in node map:"
            )
            for parent_id in missing_parents:
                logger.warning(f"  - Missing parent: {parent_id}")

    def _build_hierarchy(self, nodes: List[Dict[str, Any]]) -> None:
        """
        Second pass: Build parent-child relationships.

        Args:
            nodes: List of node dictionaries from database
        """
        for node in nodes:
            db_id = node["id"]
            trace_node = self.node_map[db_id]
            parent_id = node.get("parent_agent_id")

            if parent_id:
                self._attach_to_parent(node, trace_node, parent_id)
            else:
                self._add_as_root(node, trace_node)

    def _attach_to_parent(
        self, node: Dict[str, Any], trace_node: Dict[str, Any], parent_id: str
    ) -> None:
        """
        Attach trace node to its parent.

        Args:
            node: Original node dictionary
            trace_node: Trace tree node
            parent_id: Parent execution database ID (FK to node_executions.id)
        """
        logger.debug(f"Node {node['node_name']} has parent_agent_id: {parent_id}")

        # parent_agent_id is a database execution ID (FK to node_executions.id),
        # so look it up directly in node_map which is keyed by database ID
        if parent_id in self.node_map:
            parent_node = self.node_map[parent_id]
            if trace_node not in parent_node["children"]:
                parent_node["children"].append(trace_node)
                logger.debug(
                    f"Added {node['node_name']} as child of {parent_node['name']}"
                )
        else:
            # Parent not found - add as root with warning
            logger.warning(
                f"Parent execution ID {parent_id} not found in node_map for {node['node_name']} "
                f"(node_id: {node['node_id']}, db_id: {node['id']})"
            )
            if trace_node not in self.root_nodes:
                self.root_nodes.append(trace_node)

    def _add_as_root(self, node: Dict[str, Any], trace_node: Dict[str, Any]) -> None:
        """
        Add trace node as a root node.

        Args:
            node: Original node dictionary
            trace_node: Trace tree node
        """
        if trace_node not in self.root_nodes:
            self.root_nodes.append(trace_node)

            # Warn about unexpected root nodes
            expected_root_types = {
                "START",
                "AGENT",
                "ORCHESTRATOR",
                "CONDITION",
                "HUMAN",
                "END",
            }
            if node["node_type"] not in expected_root_types:
                logger.warning(
                    f"Node {node['node_name']} (type: {node['node_type']}) "
                    f"has no parent_agent_id, adding as root"
                )

    def _remove_subworkflow_tool_duplicates(self) -> None:
        """Remove tool nodes that are just the invocation wrapper for a subworkflow.

        When an agent calls a subworkflow, two trace nodes are created:
        1. A TOOL node like 'execute_level_1_workflow_workflow' (the LangChain tool call)
        2. A SUBWORKFLOW node like 'Level 1 workflow' (the actual execution)

        The tool node is redundant since the subworkflow node already represents
        the execution. This method removes the tool duplicates from the tree.
        """
        import re

        # Collect all subworkflow node names for matching
        subworkflow_names = set()
        for trace_node in self.node_map.values():
            if trace_node.get("type") == "subgraph":
                subworkflow_names.add(trace_node["name"].lower().replace(" ", "_"))

        if not subworkflow_names:
            return

        def is_subworkflow_tool(node: Dict[str, Any]) -> bool:
            """Check if a tool node is a subworkflow invocation wrapper."""
            if node.get("type") != "tool":
                return False
            name = node.get("name", "").lower()
            # Match pattern: execute_{workflow_name}_workflow
            match = re.match(r"^execute_(.+)_workflow$", name)
            if not match:
                return False
            return match.group(1) in subworkflow_names

        def filter_children(children: list) -> list:
            filtered = [c for c in children if not is_subworkflow_tool(c)]
            for child in filtered:
                if child.get("children"):
                    child["children"] = filter_children(child["children"])
            return filtered

        self.root_nodes = filter_children(self.root_nodes)
        for root in self.root_nodes:
            if root.get("children"):
                root["children"] = filter_children(root["children"])

    def _sort_tree(self) -> None:
        """Sort root nodes and all children by execution order."""
        self.root_nodes = self._sort_nodes(self.root_nodes)
        for root in self.root_nodes:
            self._sort_children_recursive(root)

    def _sort_nodes(self, node_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort nodes by execution order and start time.

        Args:
            node_list: List of trace nodes

        Returns:
            Sorted list of trace nodes
        """

        def get_sort_key(node: Dict[str, Any]) -> tuple:
            # Start nodes should always come first
            if node.get("type") == "start" or node.get("name", "").lower() == "start":
                return (-1, node.get("startTime") or "")

            # Then sort by execution order, then by start time
            execution_order = node.get("executionOrder")
            if execution_order is None:
                execution_order = 999

            return (execution_order, node.get("startTime") or "")

        return sorted(node_list, key=get_sort_key)

    def _sort_children_recursive(self, node: Dict[str, Any]) -> None:
        """
        Recursively sort all children of a node.

        Args:
            node: Trace tree node
        """
        if node.get("children"):
            node["children"] = self._sort_nodes(node["children"])
            for child in node["children"]:
                self._sort_children_recursive(child)

    def _calculate_metadata(
        self, execution_data: Dict[str, Any], nodes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate aggregate metadata for the execution.

        Args:
            execution_data: Execution dictionary
            nodes: List of node dictionaries

        Returns:
            Metadata dictionary
        """
        total_tokens = sum(
            n.get("total_tokens")
            or ((n.get("input_tokens") or 0) + (n.get("output_tokens") or 0))
            for n in nodes
        )

        # Calculate total cost using CostCalculator
        total_cost = CostCalculator.calculate_total_cost(nodes)

        # Count node types
        node_type_counts = {}
        for node in nodes:
            node_type = node["node_type"]
            node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1

        return {
            "totalNodes": len(nodes),
            "totalTokens": total_tokens,
            "totalCost": total_cost,
            "nodeTypeCounts": node_type_counts,
            "inputData": execution_data.get("input_data"),
            "outputData": execution_data.get("output_data"),
            "error": execution_data.get("error_message"),
        }
