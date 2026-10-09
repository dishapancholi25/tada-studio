"""Orchestrator pattern detection.

This module provides utilities for detecting whether a node should be
configured as an orchestrator based on its connections.
"""

from typing import Any, List

from backend.models.workflow import ConnectionType, EnhancedNodeData, NodeType
from backend.services.config import get_logger

logger = get_logger("delegation.detection")


def detect_orchestrator_pattern(
    node: EnhancedNodeData, graph_nodes: List[EnhancedNodeData], connections: List[Any]
) -> bool:
    """Detect if a node should be configured as an orchestrator.

    An orchestrator is an agent node that delegates to 2 or more other agents
    via DELEGATION connections.

    Args:
        node: The node to check
        graph_nodes: All nodes in the graph
        connections: All connections in the graph

    Returns:
        True if the node appears to be an orchestrator
    """
    if node.type != NodeType.AGENT:
        return False

    # Count outgoing DELEGATION connections to other agents
    agent_connections = 0

    for conn in connections:
        if conn.source_id == node.uniq_id:
            target_node = next(
                (n for n in graph_nodes if n.uniq_id == conn.target_id), None
            )
            if target_node:
                logger.debug(
                    f"Agent {node.uniq_id} -> {target_node.type.value} "
                    f"({_get_connection_type_str(conn)})"
                )

                # Only count DELEGATION connections to other AGENTS
                if target_node.type == NodeType.AGENT:
                    connection_type = _parse_connection_type(conn)

                    if connection_type == ConnectionType.DELEGATION:
                        agent_connections += 1
                    elif connection_type is None:
                        # Legacy graphs without explicit connection type:
                        # treat agent→agent links as delegation
                        agent_connections += 1

    logger.info(f"Agent {node.uniq_id} has {agent_connections} delegation connections")

    # If connected to 2 or more agents via DELEGATION, it's an orchestrator
    return agent_connections >= 2


def _parse_connection_type(conn: Any) -> ConnectionType:
    """Parse connection type from connection object.

    Args:
        conn: Connection object

    Returns:
        ConnectionType enum value or None
    """
    connection_type = getattr(conn, "connection_type", None)

    if isinstance(connection_type, str):
        try:
            return ConnectionType(connection_type)
        except ValueError:
            logger.warning(f"Invalid connection type string: {connection_type}")
            return None

    return connection_type


def _get_connection_type_str(conn: Any) -> str:
    """Get connection type as string for logging.

    Args:
        conn: Connection object

    Returns:
        Connection type string or 'UNKNOWN'
    """
    connection_type = getattr(conn, "connection_type", None)
    if hasattr(connection_type, "value"):
        return connection_type.value
    elif isinstance(connection_type, str):
        return connection_type
    else:
        return "UNKNOWN"
