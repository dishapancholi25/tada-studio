"""
Subgraph builder for creating LangGraph subgraphs.

This module provides the SubgraphBuilder class that coordinates the creation
of agent and workflow subgraphs with proper caching.
"""

from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph
from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger

from .agent.factory import create_agent_subgraph
from .cache import SubgraphCache
from .workflow.factory import create_workflow_subgraph


builder_logger = get_logger("subgraph.builder")


class SubgraphBuilder:
    """Builder class for creating LangGraph subgraphs for sub-agent execution.

    Provides caching and proper async execution patterns.
    """

    def __init__(self, graph_manager):
        """
        Initialize the subgraph builder.

        Args:
            graph_manager: The GraphManager instance for agent execution
        """
        self.graph_manager = graph_manager
        self._cache = SubgraphCache()

    def create_subagent_graph(
        self,
        agent_node: EnhancedNodeData,
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ) -> StateGraph:
        """
        Create a subgraph for a delegated agent.

        This subgraph will:
        1. Execute the agent with proper async patterns
        2. Track execution in the database
        3. Update execution order
        4. Track tool executions
        5. Send WebSocket notifications
        6. Return results to parent graph

        Args:
            agent_node: The agent node to create a subgraph for
            checkpointer: Optional checkpointer for state persistence

        Returns:
            Compiled StateGraph ready for execution
        """
        # Check cache first
        cached_graph = self._cache.get(agent_node, prefix="agent_")
        if cached_graph:
            builder_logger.debug(f"Using cached subgraph for {agent_node.name}")
            return cached_graph

        builder_logger.info(
            f"Creating subgraph for agent: {agent_node.name} ({agent_node.uniq_id})"
        )

        # Create the subgraph
        compiled_graph = create_agent_subgraph(
            agent_node=agent_node,
            graph_manager=self.graph_manager,
            checkpointer=checkpointer,
        )

        # Cache the compiled graph
        self._cache.put(agent_node, compiled_graph, prefix="agent_")
        builder_logger.info(f"Subgraph created and cached for {agent_node.name}")

        return compiled_graph

    def create_subworkflow_graph(
        self,
        subworkflow_node: EnhancedNodeData,
        graph_name: Optional[str] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ) -> StateGraph:
        """
        Create a subgraph for a sub-workflow execution.

        This subgraph will:
        1. Start from the SUBWORKFLOW node (acts as START)
        2. Execute all connected workflow nodes
        3. Collect output from END node
        4. Track execution in the database
        5. Send WebSocket notifications
        6. Return results to parent agent

        Args:
            subworkflow_node: The SUBWORKFLOW node that starts the workflow
            graph_name: Name of the parent graph for context
            checkpointer: Optional checkpointer for state persistence

        Returns:
            Compiled StateGraph ready for execution
        """
        # Check cache first
        cached_graph = self._cache.get(subworkflow_node, prefix="workflow_")
        if cached_graph:
            builder_logger.debug(
                f"Using cached subworkflow graph for {subworkflow_node.name}"
            )
            return cached_graph

        builder_logger.info(
            f"Creating subworkflow graph for: {subworkflow_node.name} "
            f"({subworkflow_node.uniq_id})"
        )

        # Create the subgraph
        compiled_graph = create_workflow_subgraph(
            subworkflow_node=subworkflow_node,
            graph_manager=self.graph_manager,
            graph_name=graph_name,
            checkpointer=checkpointer,
        )

        # Cache the compiled workflow
        self._cache.put(subworkflow_node, compiled_graph, prefix="workflow_")
        builder_logger.info(
            f"Subworkflow graph created and cached for {subworkflow_node.name}"
        )

        return compiled_graph

    def clear_cache(self) -> None:
        """Clear the subgraph cache."""
        self._cache.clear()
        builder_logger.info("Subgraph cache cleared")

    def get_cached_subgraph(self, agent_node: EnhancedNodeData) -> Optional[StateGraph]:
        """
        Get a cached subgraph if it exists.

        Args:
            agent_node: The agent node to look up

        Returns:
            The cached StateGraph, or None if not found
        """
        return self._cache.get(agent_node, prefix="agent_")
