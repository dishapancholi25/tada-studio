"""Base factory functionality for delegation tools.

This module provides shared functionality for all delegation tool factories.
"""

from typing import Dict, Optional

from backend.services.config import get_logger
from backend.services.delegation.config import (
    generate_tool_description,
    generate_tool_name,
)
from backend.services.delegation.models import DelegationContext
from backend.services.delegation.utils.tool_mapping import build_tool_node_mapping
from backend.services.execution.context import (
    ExecutionContext,
    get_current_db_execution_id,
    get_current_execution_id,
    get_current_user_id,
)

logger = get_logger("delegation.factory.base")


class BaseDelegationToolFactory:
    """Base factory for creating delegation tools.

    This class provides shared functionality for all delegation tool factories.
    """

    def __init__(self, graph_manager):
        """Initialize the factory.

        Args:
            graph_manager: GraphManager instance for executing agents
        """
        self.graph_manager = graph_manager
        self.logger = logger

    def _get_execution_context(
        self,
        parent_execution_id: Optional[str] = None,
        parent_db_execution_id: Optional[str] = None,
    ) -> DelegationContext:
        """Get execution context from various sources.

        Args:
            parent_execution_id: Optional parent execution ID
            parent_db_execution_id: Optional parent database execution ID

        Returns:
            Delegation context dictionary
        """
        exec_id = parent_execution_id
        db_exec_id = parent_db_execution_id

        # Try to get from ExecutionContext first
        execution_context = ExecutionContext.get_current()
        if not exec_id and execution_context:
            exec_id = execution_context.execution_id
        if not db_exec_id and execution_context:
            db_exec_id = execution_context.db_execution_id

        # Fall back to context variables
        if not exec_id:
            exec_id = get_current_execution_id()
        if not db_exec_id:
            db_exec_id = get_current_db_execution_id()

        return {
            "execution_id": exec_id,
            "db_execution_id": db_exec_id,
            "execution_order": 0,  # Will be managed by state in subgraph
            "graph_name": None,
            "tool_node_mapping": {},
            "user_id": get_current_user_id(),
        }

    def _build_tool_mapping(
        self,
        agent_node_id: str,
    ) -> Dict[str, Dict[str, str]]:
        """Build tool node mapping for a sub-agent.

        Args:
            agent_node_id: The agent node ID to build mapping for

        Returns:
            Tool node mapping dictionary
        """
        # Get graph name from context
        graph_name = self._get_graph_name()

        if not graph_name or not self.graph_manager:
            self.logger.warning(
                f"Cannot build tool mapping: graph_name={graph_name}, "
                f"has_graph_manager={self.graph_manager is not None}"
            )
            return {}

        try:
            graph = self.graph_manager.get_graph(graph_name)
            if not graph:
                self.logger.warning(f"Graph '{graph_name}' not found")
                return {}

            self.logger.info(
                f"Building tool mapping for sub-agent {agent_node_id} "
                f"in graph '{graph_name}'"
            )

            return build_tool_node_mapping(graph, agent_node_id)

        except Exception as e:
            self.logger.warning(f"Failed to build tool node mapping: {e}")
            return {}

    def _get_graph_name(self) -> Optional[str]:
        """Get the current graph name from various sources.

        Returns:
            Graph name or None
        """
        # Try from graph_manager attribute
        graph_name = getattr(self.graph_manager, "current_graph_name", None)
        if graph_name:
            self.logger.debug(f"Got graph_name from graph_manager: {graph_name}")
            return graph_name

        # Try from dependency injection
        try:
            from backend.services.dependency_injection import get_graph_manager

            dep_graph_manager = get_graph_manager()
            graph_name = getattr(dep_graph_manager, "current_graph_name", None)
            if graph_name:
                self.logger.debug(
                    f"Got graph_name from dependency injection: {graph_name}"
                )
                return graph_name
        except Exception as e:
            self.logger.debug(f"Could not get graph_name from dependencies: {e}")

        return None

    def _get_tool_name_and_description(
        self,
        agent_node,
        custom_description: Optional[str] = None,
    ) -> tuple[str, str]:
        """Generate tool name and description for an agent.

        Args:
            agent_node: The agent node
            custom_description: Optional custom description

        Returns:
            Tuple of (tool_name, description)
        """
        tool_name = generate_tool_name(agent_node)
        description = custom_description or generate_tool_description(agent_node)
        return tool_name, description
