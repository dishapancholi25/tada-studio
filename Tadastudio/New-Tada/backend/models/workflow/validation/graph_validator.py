"""Graph validation logic.

This module provides validation for complete workflow graphs,
split into focused functions to reduce complexity.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Set

from ..enums import NodeType

if TYPE_CHECKING:
    from ..graph import GraphData

logger = logging.getLogger(__name__)


class GraphValidator:
    """Validates complete workflow graphs with low complexity methods."""

    @staticmethod
    def validate_graph(graph: "GraphData") -> Dict[str, Any]:
        """Validate the entire graph.

        Args:
            graph: Graph to validate

        Returns:
            Dictionary with validation results containing:
                - is_valid: bool
                - errors: List[str]
                - warnings: List[str]
        """
        logger.info(f"=== VALIDATING GRAPH '{graph.name}' ===")
        errors = []
        warnings = []

        # Validate start and end nodes
        start_errors, start_warnings = GraphValidator._validate_start_end_nodes(graph)
        errors.extend(start_errors)
        warnings.extend(start_warnings)

        # Validate individual nodes
        node_errors = GraphValidator._validate_individual_nodes(graph)
        errors.extend(node_errors)

        # Validate connections
        connection_errors = GraphValidator._validate_connections(graph)
        errors.extend(connection_errors)

        # Validate agent-tool relationships
        tool_warnings = GraphValidator._validate_agent_tools(graph)
        warnings.extend(tool_warnings)

        # Check for unreachable nodes
        unreachable_warnings = GraphValidator._check_unreachable_nodes(graph)
        warnings.extend(unreachable_warnings)

        result = {"is_valid": len(errors) == 0, "errors": errors, "warnings": warnings}

        logger.info("=== VALIDATION COMPLETE ===")
        logger.info(f"Valid: {result['is_valid']}")
        logger.info(f"Errors ({len(errors)}): {errors}")
        logger.info(f"Warnings ({len(warnings)}): {warnings}")

        return result

    @staticmethod
    def _validate_start_end_nodes(graph: "GraphData") -> tuple[List[str], List[str]]:
        """Validate START and END nodes.

        Args:
            graph: Graph to validate

        Returns:
            Tuple of (errors, warnings)
        """
        errors = []
        warnings = []

        # Check for start node
        start_nodes = [n for n in graph.nodes if n.type == NodeType.START]
        logger.info(f"Found {len(start_nodes)} START nodes")

        if len(start_nodes) == 0:
            errors.append("Graph must have at least one START node")
        elif len(start_nodes) > 1:
            warnings.append("Graph has multiple START nodes, only first will be used")

        # Check for end node
        end_nodes = [n for n in graph.nodes if n.type == NodeType.END]
        logger.info(f"Found {len(end_nodes)} END nodes")

        if len(end_nodes) == 0:
            errors.append("Graph must have at least one END node")

        return errors, warnings

    @staticmethod
    def _validate_individual_nodes(graph: "GraphData") -> List[str]:
        """Validate all individual nodes.

        Args:
            graph: Graph to validate

        Returns:
            List of validation errors
        """
        errors = []

        logger.info(f"Validating {len(graph.nodes)} nodes...")

        for node in graph.nodes:
            logger.info(
                f"  Validating node '{node.name}' (ID: {node.uniq_id}, Type: {node.type})"
            )
            if not node.validate():
                logger.error(
                    f"  Node '{node.name}' validation failed: {node.validation_errors}"
                )
                errors.extend(
                    [f"Node '{node.name}': {error}" for error in node.validation_errors]
                )

        return errors

    @staticmethod
    def _validate_connections(graph: "GraphData") -> List[str]:
        """Validate all graph connections.

        Args:
            graph: Graph to validate

        Returns:
            List of validation errors
        """
        errors = []
        logger.info(f"Validating {len(graph.connections)} connections...")

        node_ids = {node.uniq_id for node in graph.nodes}

        for connection in graph.connections:
            logger.info(
                f"  Checking connection: {connection.source_id} -> {connection.target_id}"
            )

            if connection.source_id not in node_ids:
                logger.error(
                    f"  Connection references non-existent source node: {connection.source_id}"
                )
                errors.append(
                    f"Connection references non-existent source node: {connection.source_id}"
                )

            if connection.target_id not in node_ids:
                logger.error(
                    f"  Connection references non-existent target node: {connection.target_id}"
                )
                errors.append(
                    f"Connection references non-existent target node: {connection.target_id}"
                )

        return errors

    @staticmethod
    def _validate_agent_tools(graph: "GraphData") -> List[str]:
        """Validate agent-tool relationships.

        Args:
            graph: Graph to validate

        Returns:
            List of validation warnings
        """
        warnings = []
        agent_nodes = graph.get_nodes_by_type(NodeType.AGENT)

        for agent_node in agent_nodes:
            if agent_node.agent_config and agent_node.agent_config.tools:
                tool_names = set(agent_node.agent_config.tools)
                available_tools = {
                    node.tool_config.tool_name
                    for node in graph.nodes
                    if node.type == NodeType.TOOL and node.tool_config
                }
                missing_tools = tool_names - available_tools

                if missing_tools:
                    warnings.append(
                        f"Agent '{agent_node.name}' has embedded tools: {', '.join(missing_tools)}"
                    )

        return warnings

    @staticmethod
    def _check_unreachable_nodes(graph: "GraphData") -> List[str]:
        """Check for unreachable nodes.

        Args:
            graph: Graph to validate

        Returns:
            List of validation warnings
        """
        warnings = []
        start_nodes = [n for n in graph.nodes if n.type == NodeType.START]

        if not start_nodes:
            return warnings

        visited: Set[str] = set()

        def dfs(node_id: str):
            """Depth-first search to find reachable nodes."""
            if node_id in visited:
                return
            visited.add(node_id)
            for connection in graph.connections:
                if connection.source_id == node_id:
                    dfs(connection.target_id)

        dfs(start_nodes[0].uniq_id)

        unreachable = [n.name for n in graph.nodes if n.uniq_id not in visited]
        if unreachable:
            warnings.append(f"Unreachable nodes detected: {', '.join(unreachable)}")

        return warnings
