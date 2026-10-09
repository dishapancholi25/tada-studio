"""Agent tool factory for creating tool instances.

This module provides the main factory for creating tools that agents can use.
It replaces the massive get_tools() method from GraphManager with a modular approach.
"""

import logging
from typing import Any, List, Optional

from backend.models.workflow import (
    ConnectionType,
    EnhancedNodeData,
    GraphData,
    NodeType,
)
from backend.services.config import get_logger
from backend.services.execution.context import get_node_execution_id

from .creators import (
    create_code_executor_tool_from_node,
    create_database_query_tool_from_node,
    create_document_retrieve_tool_from_node,
    create_document_search_tool_from_node,
    create_email_send_tool_from_node,
    create_file_write_tool_from_node,
    create_http_request_tool_from_node,
    create_legacy_document_search_tool,
    create_mcp_server_tools_from_node,
    create_subworkflow_tool_from_node,
    create_web_search_tool_from_node,
)
from .serialization import create_serializable_tools


logger = get_logger(__name__)


class AgentToolFactory:
    """
    Factory for creating tool instances for agents.

    This factory handles:
    1. Finding connected tool nodes for an agent
    2. Creating tool instances from node configurations
    3. Creating serializable tool wrappers
    4. Legacy tool support (backward compatibility)
    """

    def __init__(self, graph_manager: Any, delegation_factory: Any):
        """
        Initialize the tool factory.

        Args:
            graph_manager: GraphManager instance (for accessing active_graphs)
            delegation_factory: AgentDelegationToolFactory instance (for subworkflows)
        """
        self.graph_manager = graph_manager
        self.delegation_factory = delegation_factory

        # Setup tool creation logger
        self.tool_logger = logging.getLogger("tool_creation")
        self.tool_logger.setLevel(logging.DEBUG)

        if not self.tool_logger.handlers:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            console_handler.setFormatter(formatter)
            self.tool_logger.addHandler(console_handler)

    def get_tools(
        self,
        tool_list: Optional[List[str]] = None,
        agent_config: Any = None,
        graph_name: Optional[str] = None,
        agent_node_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Any]:
        """
        Return actual LangChain tools with proper handling for all tool types.

        This method replaces GraphManager.get_tools() with a cleaner,
        modular implementation.

        Args:
            tool_list: List of tool names to instantiate (deprecated)
            agent_config: Agent configuration object
            graph_name: Name of the graph (for checking connected nodes)
            agent_node_id: ID of the agent node (for checking connected nodes)
            user_id: User ID for OAuth token lookup in MCP tools

        Returns:
            List of LangChain tool instances
        """
        if tool_list is None:
            tool_list = []

        self.tool_logger.info("=== GET_TOOLS START ===")
        self.tool_logger.info(f"Requested tools: {tool_list}")
        self.tool_logger.info(f"Agent config provided: {agent_config is not None}")

        tools = []

        # Check for connected tool nodes
        logger.info(
            f"Checking for connected tools - graph_name: {graph_name}, "
            f"agent_node_id: {agent_node_id}, "
            f"active_graphs: {list(self.graph_manager.active_graphs.keys())}"
        )

        if (
            graph_name
            and agent_node_id
            and graph_name in self.graph_manager.active_graphs
        ):
            logger.info(
                f"Checking for connected tool nodes for agent {agent_node_id} "
                f"in graph {graph_name}"
            )
            graph = self.graph_manager.active_graphs[graph_name]
            tools.extend(
                self._create_tools_from_connected_nodes(graph, agent_node_id, user_id)
            )

            # Check if this is an orchestrator agent and add delegation tools
            if agent_config:
                if (
                    agent_config.is_orchestrator
                    and agent_config.include_delegation_tools
                ):
                    logger.info(
                        f"Agent {agent_node_id} is an orchestrator - checking for delegation tools"
                    )

                    agent_node = graph.get_node_by_id(agent_node_id)

                    if agent_node:
                        delegation_tools = self.graph_manager.orchestrator_manager.get_delegation_tools(
                            graph, agent_node
                        )
                        if delegation_tools:
                            logger.info(
                                f"Adding {len(delegation_tools)} delegation tools for orchestrator"
                            )
                            tools.extend(delegation_tools)
                    else:
                        logger.warning(
                            f"Agent node {agent_node_id} not found in graph {graph_name}, "
                            "cannot retrieve delegation tools"
                        )

        # Check if document search is enabled in agent config (legacy support)
        if agent_config:
            legacy_tool = create_legacy_document_search_tool(agent_config)
            if legacy_tool:
                tools.append(legacy_tool)

        # Warn about deprecated tool_list parameter
        if tool_list:
            logger.warning(
                f"Ignoring tool_list: {tool_list}. Simple string-based tools have been removed. "
                "Use connected node types instead."
            )

        self.tool_logger.info("=== GET_TOOLS END ===")
        logger.info(f"Total tools created: {len(tools)}")
        logger.info(f"Tool names: {[getattr(t, 'name', 'unknown') for t in tools]}")

        # Deduplicate tools by name to avoid binding mismatch errors
        tools = self._deduplicate_tools(tools)

        return tools

    def _create_tools_from_connected_nodes(
        self,
        graph: GraphData,
        agent_node_id: str,
        user_id: Optional[str] = None,
    ) -> List[Any]:
        """
        Create tools from nodes connected to an agent via TOOL connections.

        Args:
            graph: The graph containing the nodes
            agent_node_id: ID of the agent node
            user_id: User ID for OAuth token lookup in MCP tools

        Returns:
            List of tool instances
        """
        tools = []
        used_tool_names = set()  # Track tool names to detect collisions

        # Find all connections from this agent
        for connection in graph.connections:
            if (
                connection.source_id == agent_node_id
                and connection.connection_type == ConnectionType.TOOL
            ):
                target_node = graph.get_node_by_id(connection.target_id)
                if not target_node:
                    logger.warning(
                        f"Target node {connection.target_id} not found for connection"
                    )
                    continue

                logger.info(
                    f"Found TOOL connection to node: {target_node.name} "
                    f"(type: {target_node.type})"
                )

                # Create tool based on node type, passing collision tracking
                tool = self._create_tool_from_node(
                    target_node, agent_node_id, user_id, used_tool_names
                )
                if tool:
                    # MCP server can return multiple tools
                    if isinstance(tool, list):
                        tools.extend(tool)
                    else:
                        tools.append(tool)

        return tools

    def _create_tool_from_node(
        self,
        target_node: EnhancedNodeData,
        agent_node_id: str,
        user_id: Optional[str] = None,
        used_tool_names: Optional[set] = None,
    ) -> Optional[Any]:
        """
        Create a tool from a specific node type.

        Args:
            target_node: The tool node
            agent_node_id: ID of the agent requesting the tool
            user_id: User ID for OAuth token lookup in MCP tools
            used_tool_names: Optional set to track used tool names for collision detection

        Returns:
            Tool instance, list of tools (for MCP), or None
        """
        if target_node.type == NodeType.DOCUMENT_SEARCH:
            return create_document_search_tool_from_node(
                target_node, used_tool_names, user_id=user_id
            )

        elif target_node.type == NodeType.DATABASE_QUERY:
            return create_database_query_tool_from_node(target_node, used_tool_names)

        elif target_node.type == NodeType.HTTP_REQUEST:
            return create_http_request_tool_from_node(
                target_node, used_tool_names, user_id=user_id
            )

        elif target_node.type == NodeType.WEB_SEARCH:
            return create_web_search_tool_from_node(target_node, used_tool_names)

        elif target_node.type == NodeType.EMAIL_SEND_TOOL:
            return create_email_send_tool_from_node(
                target_node, user_id, used_tool_names
            )

        elif target_node.type == NodeType.FILE_WRITE:
            # Create callback that looks up agent's execution ID at runtime
            def node_execution_id_provider() -> Optional[str]:
                return get_node_execution_id(agent_node_id)

            return create_file_write_tool_from_node(
                target_node,
                used_tool_names,
                node_execution_id_provider=node_execution_id_provider,
            )

        elif target_node.type == NodeType.MCP_SERVER:
            # MCP server can return multiple tools
            return create_mcp_server_tools_from_node(target_node, user_id=user_id)

        elif target_node.type == NodeType.DOCUMENT_RETRIEVE:
            return create_document_retrieve_tool_from_node(
                target_node, used_tool_names, user_id=user_id
            )

        elif target_node.type == NodeType.SUBWORKFLOW:
            return create_subworkflow_tool_from_node(
                target_node, agent_node_id, self.delegation_factory, user_id=user_id
            )

        elif target_node.type == NodeType.CODE_EXECUTOR:
            # Create callback that looks up agent's execution ID at runtime
            def node_execution_id_provider() -> Optional[str]:
                return get_node_execution_id(agent_node_id)

            return create_code_executor_tool_from_node(
                target_node,
                used_tool_names,
                node_execution_id_provider=node_execution_id_provider,
            )

        else:
            logger.warning(f"Unsupported tool node type: {target_node.type}")
            return None

    def _deduplicate_tools(self, tools: List[Any]) -> List[Any]:
        """
        Deduplicate tools by name to avoid binding mismatch errors.

        Args:
            tools: List of tools potentially with duplicates

        Returns:
            List of deduplicated tools
        """
        seen_names = set()
        deduplicated_tools = []

        for tool in tools:
            tool_name = getattr(tool, "name", "unknown")
            if tool_name not in seen_names:
                deduplicated_tools.append(tool)
                seen_names.add(tool_name)
            else:
                logger.warning(f"Skipping duplicate tool: {tool_name}")

        if len(deduplicated_tools) != len(tools):
            logger.info(
                f"Deduplicated tools: {len(tools)} -> {len(deduplicated_tools)}"
            )
            logger.info(
                f"Final tool names: {[getattr(t, 'name', 'unknown') for t in deduplicated_tools]}"
            )

        return deduplicated_tools

    def create_serializable_tools(
        self, tools: List[Any], tool_execution_tracker: Optional[List] = None
    ) -> List[Any]:
        """
        Create serializable tool wrappers.

        This is a thin wrapper around the serialization module function.

        Args:
            tools: List of tools to wrap
            tool_execution_tracker: Optional list to track executions

        Returns:
            List of serializable tools
        """
        return create_serializable_tools(tools, tool_execution_tracker)
