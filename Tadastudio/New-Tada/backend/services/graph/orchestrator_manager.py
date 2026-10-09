"""Orchestrator and delegation management service.

This module provides services for managing orchestrator agents, sub-agents,
and delegation relationships within workflow graphs.

Example:
    >>> from backend.services.graph.orchestrator_manager import OrchestratorManager
    >>> manager = OrchestratorManager(delegation_factory, node_manager, connection_manager)
    >>> count = manager.detect_and_configure_orchestrators(graph)
"""

from typing import Any, List, Optional

from backend.models.workflow import (
    AgentConfig,
    ConnectionType,
    EnhancedNodeData,
    GraphData,
    NodeType,
    Position,
)
from backend.services.config import get_logger
from backend.services.delegation import detect_orchestrator_pattern

from .constants import (
    LOG_PREFIX_ORCHESTRATOR,
    SUB_AGENT_OFFSET_X_BASE,
    SUB_AGENT_OFFSET_X_INCREMENT,
    SUB_AGENT_OFFSET_Y,
)
from .exceptions import SubAgentCreationError


logger = get_logger(__name__)


class OrchestratorManager:
    """Service for managing orchestrator agents and delegation.

    This service handles orchestrator detection, configuration, sub-agent
    creation, and delegation tool management.

    Methods:
        detect_and_configure_orchestrators: Auto-detect orchestrator patterns
        create_sub_agent: Create a sub-agent for an orchestrator
        get_delegation_tools: Get delegation tools for an orchestrator
        get_connected_agents: Get agents connected to an orchestrator
    """

    def __init__(
        self,
        delegation_factory: Any,
        node_manager: Any = None,
        connection_manager: Any = None,
    ):
        """Initialize orchestrator manager.

        Args:
            delegation_factory: Factory for creating delegation tools
            node_manager: Optional node manager for creating sub-agents
            connection_manager: Optional connection manager for creating connections
        """
        self.delegation_factory = delegation_factory
        self.node_manager = node_manager
        self.connection_manager = connection_manager

        logger.debug(f"{LOG_PREFIX_ORCHESTRATOR} Initialized")

    @staticmethod
    def get_connected_agents(
        graph: GraphData, orchestrator_id: str
    ) -> List[EnhancedNodeData]:
        """Get all agent nodes connected to an orchestrator via delegation.

        Args:
            graph: The graph containing the nodes
            orchestrator_id: ID of the orchestrator node

        Returns:
            List of agent nodes connected to the orchestrator

        Example:
            >>> agents = manager.get_connected_agents(graph, "orchestrator-1")
            >>> print(f"Found {len(agents)} connected agents")
        """
        connected_agents = []

        # Find all DELEGATION connections from the orchestrator
        for conn in graph.connections:
            if (
                conn.source_id == orchestrator_id
                and conn.connection_type == ConnectionType.DELEGATION
            ):
                target_node = graph.get_node_by_id(conn.target_id)
                if target_node and target_node.type == NodeType.AGENT:
                    connected_agents.append(target_node)

        # Also check for sub-agents by parent_agent_id
        for node in graph.nodes:
            if (
                node.type == NodeType.AGENT
                and node.is_sub_agent
                and node.parent_agent_id == orchestrator_id
            ):
                if node not in connected_agents:
                    connected_agents.append(node)

        logger.debug(
            f"{LOG_PREFIX_ORCHESTRATOR} Found {len(connected_agents)} agents "
            f"connected to orchestrator {orchestrator_id}"
        )

        return connected_agents

    def get_delegation_tools(
        self, graph: GraphData, orchestrator_node: EnhancedNodeData
    ) -> List[Any]:
        """Get delegation tools for an orchestrator agent.

        Args:
            graph: The graph containing the nodes
            orchestrator_node: The orchestrator agent node

        Returns:
            List of delegation tools

        Example:
            >>> tools = manager.get_delegation_tools(graph, orchestrator_node)
            >>> print(f"Created {len(tools)} delegation tools")
        """
        if (
            not orchestrator_node.agent_config
            or not orchestrator_node.agent_config.is_orchestrator
        ):
            logger.debug(
                f"{LOG_PREFIX_ORCHESTRATOR} Node {orchestrator_node.name} "
                "is not an orchestrator, returning empty tool list"
            )
            return []

        # Get connected agents
        connected_agents = self.get_connected_agents(graph, orchestrator_node.uniq_id)

        # Create delegation tools
        delegation_tools = (
            self.delegation_factory.create_delegation_tools_for_orchestrator(
                orchestrator_node, connected_agents
            )
        )

        logger.info(
            f"{LOG_PREFIX_ORCHESTRATOR} Created {len(delegation_tools)} delegation tools "
            f"for orchestrator '{orchestrator_node.name}'"
        )

        return delegation_tools

    def detect_and_configure_orchestrators(self, graph: GraphData) -> int:
        """Detect and configure orchestrator agents in a graph.

        Uses pattern detection to identify agents that should be orchestrators
        based on their connections and relationships.

        Args:
            graph: The graph to analyze

        Returns:
            Number of orchestrators detected and configured

        Example:
            >>> count = manager.detect_and_configure_orchestrators(graph)
            >>> print(f"Configured {count} orchestrators")
        """
        logger.debug(
            f"{LOG_PREFIX_ORCHESTRATOR} Detecting orchestrator patterns in graph: {graph.name}"
        )

        orchestrator_count = 0

        for node in graph.nodes:
            if node.type == NodeType.AGENT and node.agent_config:
                # Check if this agent should be an orchestrator
                is_orchestrator = detect_orchestrator_pattern(
                    node, graph.nodes, graph.connections
                )

                logger.info(
                    f"[ORCHESTRATOR_DEBUG] Agent {node.uniq_id} ({node.name}) "
                    f"orchestrator pattern detected: {is_orchestrator}"
                )

                if is_orchestrator:
                    if not node.agent_config.is_orchestrator:
                        # Configure as orchestrator
                        logger.info(
                            f"[ORCHESTRATOR_DEBUG] Setting agent {node.uniq_id} "
                            "as orchestrator"
                        )
                        node.agent_config.is_orchestrator = True

                        # Get connected agents
                        connected_agents = self.get_connected_agents(
                            graph, node.uniq_id
                        )
                        node.agent_config.delegated_agents = [
                            a.uniq_id for a in connected_agents
                        ]

                        orchestrator_count += 1

        logger.info(
            f"{LOG_PREFIX_ORCHESTRATOR} Detected and configured {orchestrator_count} "
            f"orchestrators in graph: {graph.name}"
        )

        return orchestrator_count

    def create_sub_agent(
        self,
        graph_name: str,
        active_graphs: dict,
        parent_agent_id: str,
        name: Optional[str] = None,
        position: Optional[Position] = None,
        delegation_description: str = "",
        agent_template: Optional[str] = None,
    ) -> Optional[EnhancedNodeData]:
        """Create a sub-agent for an orchestrator.

        Args:
            graph_name: Name of the graph
            active_graphs: Dict of active graphs
            parent_agent_id: ID of the parent agent (orchestrator)
            name: Optional name for the sub-agent
            position: Optional position (will be calculated if not provided)
            delegation_description: Description of when/how to use this sub-agent
            agent_template: Optional agent template to use

        Returns:
            The created sub-agent node, or None if failed

        Raises:
            SubAgentCreationError: If creation fails

        Example:
            >>> sub_agent = manager.create_sub_agent(
            ...     "my-workflow",
            ...     active_graphs,
            ...     "orchestrator-1",
            ...     name="Customer Support Agent",
            ...     delegation_description="Handle customer support queries"
            ... )
        """
        logger.debug(
            f"{LOG_PREFIX_ORCHESTRATOR} Creating sub-agent for parent: {parent_agent_id} "
            f"in graph: {graph_name}"
        )

        # Validate graph exists
        if graph_name not in active_graphs:
            logger.error(f"{LOG_PREFIX_ORCHESTRATOR} Graph not found: {graph_name}")
            logger.info(
                f"{LOG_PREFIX_ORCHESTRATOR} Available graphs: {list(active_graphs.keys())}"
            )
            raise SubAgentCreationError(
                parent_agent_id, f"Graph '{graph_name}' not found"
            )

        graph = active_graphs[graph_name]
        parent_node = graph.get_node_by_id(parent_agent_id)

        # Validate parent node
        if not parent_node or parent_node.type != NodeType.AGENT:
            raise SubAgentCreationError(
                parent_agent_id,
                f"Parent node not found or not an agent: {parent_agent_id}",
            )

        # Ensure parent has agent config
        if not parent_node.agent_config:
            logger.warning(
                f"{LOG_PREFIX_ORCHESTRATOR} Parent node {parent_agent_id} "
                "has no agent config, creating default"
            )
            parent_node.agent_config = AgentConfig(
                system_prompt="You are a helpful AI assistant.",
                tools=[],
                is_orchestrator=True,
                include_delegation_tools=True,
            )

        # Configure parent as orchestrator if not already
        if not parent_node.agent_config.is_orchestrator:
            parent_node.agent_config.is_orchestrator = True

        # Generate name if not provided
        if not name:
            # Count existing sub-agents
            sub_agent_count = sum(
                1 for n in graph.nodes if n.parent_agent_id == parent_agent_id
            )
            name = f"SubAgent {sub_agent_count + 1}"

        # Calculate position if not provided
        if not position:
            position = self._calculate_sub_agent_position(parent_node)

        # Require node_manager for creating nodes
        if not self.node_manager:
            raise SubAgentCreationError(
                parent_agent_id, "NodeManager not available for sub-agent creation"
            )

        # Create the sub-agent
        sub_agent = self.node_manager.create_node(
            node_type=NodeType.AGENT,
            name=name,
            position=position,
            agent_template=agent_template,
            description=delegation_description,
        )

        # Configure as sub-agent
        sub_agent.is_sub_agent = True
        sub_agent.parent_agent_id = parent_agent_id
        sub_agent.delegation_description = delegation_description

        # Fix template defaults to match regular agent behavior
        if sub_agent.agent_config:
            # If no tools are specified, disable automatic tool binding
            if (
                not sub_agent.agent_config.tools
                and not sub_agent.agent_config.structured_outputs
            ):
                sub_agent.agent_config.tool_binding_mode = "none"

            # Disable memory by default for sub-agents
            sub_agent.agent_config.memory_enabled = False

        # Add to graph
        if not self.node_manager.add_node_to_graph(graph, sub_agent):
            raise SubAgentCreationError(
                parent_agent_id, "Failed to add sub-agent to graph"
            )

        # Create delegation connection
        if not self.connection_manager:
            raise SubAgentCreationError(
                parent_agent_id,
                "ConnectionManager not available for creating delegation connection",
            )

        self.connection_manager.add_connection(
            graph=graph,
            source_id=parent_agent_id,
            target_id=sub_agent.uniq_id,
            connection_type=ConnectionType.DELEGATION,
            label="delegates to",
        )

        logger.info(
            f"{LOG_PREFIX_ORCHESTRATOR} Created sub-agent '{name}' "
            f"(ID: {sub_agent.uniq_id}) for parent: {parent_agent_id}"
        )

        return sub_agent

    def _calculate_sub_agent_position(self, parent_node: EnhancedNodeData) -> Position:
        """Calculate position for a new sub-agent.

        Positions sub-agents below and to the right of the parent,
        with spacing for multiple sub-agents.

        Args:
            parent_node: The parent orchestrator node

        Returns:
            Position for the new sub-agent
        """
        parent_pos = parent_node.position
        delegated_count = (
            len(parent_node.agent_config.delegated_agents)
            if parent_node.agent_config
            else 0
        )

        offset_x = SUB_AGENT_OFFSET_X_BASE + (
            SUB_AGENT_OFFSET_X_INCREMENT * delegated_count
        )

        return Position(x=parent_pos.x + offset_x, y=parent_pos.y + SUB_AGENT_OFFSET_Y)
