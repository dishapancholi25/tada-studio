"""Connection management service.

This module provides services for managing connections between nodes in workflow graphs,
including creation, deletion, and relationship maintenance.

Example:
    >>> from backend.services.graph.connection_manager import ConnectionManager
    >>> manager = ConnectionManager()
    >>> success = manager.add_connection(graph, "node1", "node2")
"""

from datetime import datetime
from typing import Any, Optional

from backend.models.workflow import (
    AgentConfig,
    Connection,
    ConnectionType,
    NodeType,
)
from backend.services.config import get_logger

from .constants import LOG_PREFIX_CONNECTION_MANAGER
from .exceptions import ConnectionValidationError, NodeNotFoundError


logger = get_logger(__name__)

# Node types that can be used as tools by agents
VALID_TOOL_TARGET_TYPES = {
    NodeType.TOOL,
    NodeType.CODE_EXECUTOR,
    NodeType.DATABASE_QUERY,
    NodeType.DOCUMENT_SEARCH,
    NodeType.DOCUMENT_RETRIEVE,
    NodeType.EMAIL_SEND_TOOL,
    NodeType.FILE_READ,
    NodeType.FILE_WRITE,
    NodeType.HTTP_REQUEST,
    NodeType.WEB_SEARCH,
    NodeType.MCP_SERVER,
    NodeType.SUBWORKFLOW,
}


class ConnectionManager:
    """Service for managing connections between nodes.

    This service handles all connection-related operations including creation,
    deletion, and validation of connections between workflow nodes.

    Methods:
        add_connection: Create a connection between two nodes
        remove_connection: Remove a connection
        validate_connection: Validate connection compatibility
    """

    def __init__(self):
        """Initialize connection manager."""
        logger.debug(f"{LOG_PREFIX_CONNECTION_MANAGER} Initialized")

    def add_connection(
        self,
        graph: Any,
        source_id: str,
        target_id: str,
        source_handle: Optional[str] = None,
        target_handle: Optional[str] = None,
        connection_type: ConnectionType = ConnectionType.WORKFLOW,
        label: str = "",
        true_condition: bool = False,
    ) -> bool:
        """Add a connection between two nodes in the graph.

        Args:
            graph: The graph to add the connection to
            source_id: ID of the source node
            target_id: ID of the target node
            source_handle: Optional handle identifier for source (e.g., for condition branches)
            target_handle: Optional handle identifier for target
            connection_type: Type of connection (NEXT, TOOL, DELEGATION)
            label: Optional connection label
            true_condition: For condition nodes, whether this is the true branch

        Returns:
            True if connection was added successfully

        Raises:
            NodeNotFoundError: If source or target node doesn't exist
            ConnectionValidationError: If connection is invalid

        Example:
            >>> success = manager.add_connection(
            ...     graph,
            ...     "agent-1",
            ...     "tool-1",
            ...     ConnectionType.TOOL
            ... )
        """
        logger.debug(
            f"{LOG_PREFIX_CONNECTION_MANAGER} Adding connection: "
            f"{source_id} -> {target_id} (type: {connection_type})"
        )

        # Validate nodes exist
        source_node = graph.get_node_by_id(source_id)
        target_node = graph.get_node_by_id(target_id)

        if not source_node:
            raise NodeNotFoundError(source_id, graph.name)
        if not target_node:
            raise NodeNotFoundError(target_id, graph.name)

        # Validate connection
        self._validate_connection(source_node, target_node, connection_type)

        # Defense-in-depth: Check for duplicate connection
        for existing_conn in graph.connections:
            if (
                existing_conn.source_id == source_id
                and existing_conn.target_id == target_id
                and existing_conn.source_handle == source_handle
                and existing_conn.target_handle == target_handle
                and existing_conn.connection_type == connection_type
            ):
                logger.debug(
                    f"{LOG_PREFIX_CONNECTION_MANAGER} Connection already exists: "
                    f"{source_id} -> {target_id}, skipping duplicate"
                )
                return True  # Success (connection already exists)

        # Create connection object
        connection = Connection(
            source_id=source_id,
            target_id=target_id,
            source_handle=source_handle,
            target_handle=target_handle,
            connection_type=connection_type,
            label=label,
        )

        # Add to graph connections
        graph.connections.append(connection)

        # Update node relationships
        self._update_node_relationships(
            source_node,
            target_node,
            target_id,
            source_id,
            connection_type,
            true_condition,
        )

        graph.updated_at = datetime.now().isoformat()

        logger.info(
            f"{LOG_PREFIX_CONNECTION_MANAGER} Added connection: "
            f"{source_node.name} -> {target_node.name} (type: {connection_type})"
        )

        return True

    def _validate_connection(
        self,
        source_node: Any,
        target_node: Any,
        connection_type: ConnectionType,
    ) -> None:
        """Validate that a connection is allowed.

        Args:
            source_node: Source node
            target_node: Target node
            connection_type: Type of connection

        Raises:
            ConnectionValidationError: If connection is invalid
        """
        # TOOL connections: Agent -> Tool (or tool-like nodes)
        if connection_type == ConnectionType.TOOL:
            if source_node.type != NodeType.AGENT:
                raise ConnectionValidationError(
                    source_node.uniq_id,
                    target_node.uniq_id,
                    "TOOL connections must originate from AGENT nodes",
                )
            if target_node.type not in VALID_TOOL_TARGET_TYPES:
                raise ConnectionValidationError(
                    source_node.uniq_id,
                    target_node.uniq_id,
                    f"TOOL connections must target tool-compatible nodes. "
                    f"Valid types: {', '.join(t.value for t in VALID_TOOL_TARGET_TYPES)}",
                )

        # DELEGATION connections: Agent -> Agent
        if connection_type == ConnectionType.DELEGATION:
            if source_node.type != NodeType.AGENT:
                raise ConnectionValidationError(
                    source_node.uniq_id,
                    target_node.uniq_id,
                    "DELEGATION connections must originate from AGENT nodes",
                )
            if target_node.type != NodeType.AGENT:
                raise ConnectionValidationError(
                    source_node.uniq_id,
                    target_node.uniq_id,
                    "DELEGATION connections must target AGENT nodes",
                )

        # SUBWORKFLOW calls a saved external workflow and returns directly to the caller.
        if source_node.type == NodeType.SUBWORKFLOW:
            raise ConnectionValidationError(
                source_node.uniq_id,
                target_node.uniq_id,
                "Sub-Workflow nodes call an external workflow and return directly to the caller; no downstream connection is allowed",
            )

    def _update_node_relationships(
        self,
        source_node: Any,
        target_node: Any,
        target_id: str,
        source_id: str,
        connection_type: ConnectionType,
        true_condition: bool,
    ) -> None:
        """Update node relationship lists based on connection.

        Args:
            source_node: Source node
            target_node: Target node
            target_id: Target node ID
            source_id: Source node ID
            connection_type: Type of connection
            true_condition: Whether this is a true condition branch
        """
        # Update nexts and inputs
        if target_id not in source_node.nexts:
            source_node.nexts.append(target_id)

        if source_id not in target_node.inputs:
            target_node.inputs.append(source_id)

        # Handle condition nodes
        if source_node.type == NodeType.CONDITION:
            if true_condition:
                source_node.true_next = target_id
            else:
                source_node.false_next = target_id

        # Handle tool connections to agents
        if (
            connection_type == ConnectionType.TOOL
            and source_node.type == NodeType.AGENT
        ):
            if target_node.type == NodeType.TOOL:
                self._add_tool_to_agent(source_node, target_node)
            else:
                # Handle special tool-like node types
                self._configure_tool_node_parent(source_node, target_node, source_id)

        # Handle delegation connections
        if connection_type == ConnectionType.DELEGATION:
            self._configure_delegation(source_node, target_node, target_id, source_id)

    def _add_tool_to_agent(self, agent_node: Any, tool_node: Any) -> None:
        """Add a tool to an agent's tools list.

        Args:
            agent_node: The agent node
            tool_node: The tool node
        """
        if tool_node.tool_config and tool_node.tool_config.tool_name:
            if not agent_node.agent_config:
                agent_node.agent_config = AgentConfig()

            tool_name = tool_node.tool_config.tool_name
            if tool_name not in agent_node.agent_config.tools:
                agent_node.agent_config.tools.append(tool_name)
                logger.debug(
                    f"{LOG_PREFIX_CONNECTION_MANAGER} Added tool '{tool_name}' "
                    f"to agent '{agent_node.name}'"
                )

    def _configure_tool_node_parent(
        self, agent_node: Any, tool_node: Any, agent_id: str
    ) -> None:
        """Configure parent agent ID for special tool-like nodes.

        Args:
            agent_node: The agent node
            tool_node: The tool node (DATABASE_QUERY, DOCUMENT_SEARCH, etc.)
            agent_id: ID of the parent agent
        """
        # Map node types to their config attributes
        config_mapping = {
            NodeType.DATABASE_QUERY: "database_query_config",
            NodeType.DOCUMENT_SEARCH: "document_search_config",
            NodeType.HTTP_REQUEST: "http_request_config",
            NodeType.WEB_SEARCH: "web_search_config",
            NodeType.MCP_SERVER: "mcp_server_config",
            NodeType.SUBWORKFLOW: "subworkflow_config",
        }

        config_attr = config_mapping.get(tool_node.type)
        if config_attr:
            config = getattr(tool_node, config_attr, None)
            if config:
                config.parent_agent_id = agent_id
                logger.debug(
                    f"{LOG_PREFIX_CONNECTION_MANAGER} Set parent_agent_id for "
                    f"{tool_node.type.value} node '{tool_node.name}' to agent '{agent_node.name}'"
                )

    def _configure_delegation(
        self, source_node: Any, target_node: Any, target_id: str, source_id: str
    ) -> None:
        """Configure delegation relationship between agents.

        Args:
            source_node: Source (orchestrator) node
            target_node: Target (sub-agent) node
            target_id: Target node ID
            source_id: Source node ID
        """
        if not source_node.agent_config:
            source_node.agent_config = AgentConfig()

        # Mark source as orchestrator
        source_node.agent_config.is_orchestrator = True

        # Mark target as sub-agent
        target_node.is_sub_agent = True
        target_node.parent_agent_id = source_id

        # Add to delegated agents list
        if target_id not in source_node.agent_config.delegated_agents:
            source_node.agent_config.delegated_agents.append(target_id)

        logger.debug(
            f"{LOG_PREFIX_CONNECTION_MANAGER} Configured delegation: "
            f"'{source_node.name}' orchestrates '{target_node.name}'"
        )

    def remove_connection(self, graph: Any, source_id: str, target_id: str) -> bool:
        """Remove a connection between two nodes.

        Args:
            graph: The graph containing the connection
            source_id: ID of the source node
            target_id: ID of the target node

        Returns:
            True if connection was removed

        Example:
            >>> success = manager.remove_connection(graph, "agent-1", "tool-1")
        """
        logger.debug(
            f"{LOG_PREFIX_CONNECTION_MANAGER} Removing connection: "
            f"{source_id} -> {target_id}"
        )

        # Get nodes
        source_node = graph.get_node_by_id(source_id)
        target_node = graph.get_node_by_id(target_id)

        # Find the connection to determine its type
        conn_type = None
        for conn in graph.connections:
            if conn.source_id == source_id and conn.target_id == target_id:
                conn_type = conn.connection_type
                break

        # Handle type-specific cleanup
        if conn_type == ConnectionType.DELEGATION:
            self._cleanup_delegation(source_node, target_node, target_id)

        if conn_type == ConnectionType.TOOL:
            self._cleanup_tool_connection(source_node, target_node)

        # Remove from connections list
        graph.connections = [
            conn
            for conn in graph.connections
            if not (conn.source_id == source_id and conn.target_id == target_id)
        ]

        # Update node relationships
        self._cleanup_relationships(source_node, target_node, source_id, target_id)

        graph.updated_at = datetime.now().isoformat()

        logger.info(
            f"{LOG_PREFIX_CONNECTION_MANAGER} Removed connection: "
            f"{source_id} -> {target_id}"
        )

        return True

    def _cleanup_delegation(
        self, source_node: Any, target_node: Any, target_id: str
    ) -> None:
        """Clean up delegation relationship.

        Args:
            source_node: Source (orchestrator) node
            target_node: Target (sub-agent) node
            target_id: Target node ID
        """
        if source_node and source_node.agent_config:
            # Remove from delegated agents
            if target_id in source_node.agent_config.delegated_agents:
                source_node.agent_config.delegated_agents.remove(target_id)

            # If no more delegated agents, unmark as orchestrator
            if not source_node.agent_config.delegated_agents:
                source_node.agent_config.is_orchestrator = False
                source_node.agent_config.include_delegation_tools = False

        if target_node:
            target_node.is_sub_agent = False
            target_node.parent_agent_id = None

    def _cleanup_tool_connection(self, source_node: Any, target_node: Any) -> None:
        """Clean up tool connection from agent.

        Args:
            source_node: Agent node
            target_node: Tool node or tool-like node
        """
        if not source_node or source_node.type != NodeType.AGENT or not target_node:
            return

        if target_node.type == NodeType.TOOL:
            # Remove tool from agent's tools list
            if (
                target_node.tool_config
                and target_node.tool_config.tool_name
                and source_node.agent_config
            ):
                tool_name = target_node.tool_config.tool_name
                if tool_name in source_node.agent_config.tools:
                    source_node.agent_config.tools.remove(tool_name)
        else:
            # Clean up parent_agent_id for special tool-like nodes
            config_mapping = {
                NodeType.DATABASE_QUERY: "database_query_config",
                NodeType.DOCUMENT_SEARCH: "document_search_config",
                NodeType.HTTP_REQUEST: "http_request_config",
                NodeType.WEB_SEARCH: "web_search_config",
                NodeType.MCP_SERVER: "mcp_server_config",
                NodeType.SUBWORKFLOW: "subworkflow_config",
            }

            config_attr = config_mapping.get(target_node.type)
            if config_attr:
                config = getattr(target_node, config_attr, None)
                if config:
                    config.parent_agent_id = None

    def _cleanup_relationships(
        self, source_node: Any, target_node: Any, source_id: str, target_id: str
    ) -> None:
        """Clean up node relationship lists.

        Args:
            source_node: Source node
            target_node: Target node
            source_id: Source node ID
            target_id: Target node ID
        """
        # Update node relationships
        if source_node and target_id in source_node.nexts:
            source_node.nexts.remove(target_id)

        if target_node and source_id in target_node.inputs:
            target_node.inputs.remove(source_id)

        # Handle condition nodes
        if source_node and source_node.type == NodeType.CONDITION:
            if source_node.true_next == target_id:
                source_node.true_next = None
            if source_node.false_next == target_id:
                source_node.false_next = None
