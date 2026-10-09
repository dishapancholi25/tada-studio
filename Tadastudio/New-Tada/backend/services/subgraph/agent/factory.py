"""
Factory for creating agent subgraphs.

This module provides the factory function that creates complete agent subgraphs
with proper state management and execution logic, including optional review nodes.
"""

from typing import Any, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from backend.models.workflow import EnhancedNodeData
from backend.models.workflow.configs import ReviewConfig
from backend.services.config import get_logger

from ..models import SubAgentState
from .execution_handler import execute_agent_in_subgraph
from .review_node import SubAgentReviewNodeFactory, create_subagent_review_router


factory_logger = get_logger("subgraph.agent.factory")


def _get_review_config(agent_node: EnhancedNodeData) -> Optional[ReviewConfig]:
    """Extract and parse review config from agent node.

    Args:
        agent_node: The agent node to check for review config

    Returns:
        ReviewConfig if enabled, None otherwise
    """
    if not agent_node.agent_config:
        return None

    review_config = agent_node.agent_config.review_config
    if review_config is None:
        return None

    # Handle dict representation
    if isinstance(review_config, dict):
        try:
            return ReviewConfig(**review_config)
        except Exception as e:
            factory_logger.warning(
                f"[SUBGRAPH-FACTORY] Failed to parse review_config dict: {e}"
            )
            return None

    return review_config


def create_agent_subgraph(
    agent_node: EnhancedNodeData,
    graph_manager: Any,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> StateGraph:
    """
    Create a LangGraph subgraph for agent delegation.

    This subgraph will:
    1. Execute the agent with proper async patterns
    2. Track execution in the database
    3. Update execution order
    4. Track tool executions
    5. Send WebSocket notifications
    6. Return results to parent graph
    7. (Optional) Add review node with conditional routing for feedback loops

    When review is enabled, the graph structure is:
        execute_agent -> review_node -> (conditional)
                                         ├─ "continue" -> END
                                         └─ "retry" -> execute_agent

    Args:
        agent_node: The agent node to create a subgraph for
        graph_manager: The GraphManager instance for agent execution
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled StateGraph ready for execution
    """
    factory_logger.info(
        f"Creating subgraph for agent: {agent_node.name} ({agent_node.uniq_id})"
    )

    # Check if review is enabled
    review_config = _get_review_config(agent_node)
    review_enabled = review_config and review_config.review_enabled

    factory_logger.info(
        f"[SUBGRAPH-FACTORY] Review enabled for {agent_node.name}: {review_enabled}"
    )

    # Create the state graph
    workflow = StateGraph(SubAgentState)

    # Define the agent execution node
    async def execute_agent(state: SubAgentState):
        """Execute the agent and update state."""
        return await execute_agent_in_subgraph(
            state=state,
            agent_node=agent_node,
            graph_manager=graph_manager,
        )

    # Add the execution node - use agent UUID so LangGraph messages have unique node identifier
    workflow.add_node(agent_node.uniq_id, execute_agent)

    # Set entry point
    workflow.set_entry_point(agent_node.uniq_id)

    if review_enabled:
        # Add review node for agents with review enabled
        factory_logger.info(
            f"[SUBGRAPH-FACTORY] Adding review node for {agent_node.name}"
        )

        # Get LLM factory and model service from graph_manager for LLM review
        llm_factory = getattr(graph_manager, "llm_factory", None)
        model_service = getattr(graph_manager, "model_service", None)

        # Create review node factory
        review_factory = SubAgentReviewNodeFactory(
            llm_factory=llm_factory,
            model_service=model_service,
        )

        # Create review node function
        review_node_fn = review_factory.create_review_function(agent_node)

        # Add review node
        workflow.add_node("review_node", review_node_fn)

        # Add edge from agent to review
        workflow.add_edge(agent_node.uniq_id, "review_node")

        # Add conditional edges from review node
        review_router = create_subagent_review_router()
        workflow.add_conditional_edges(
            "review_node",
            review_router,
            {
                "continue": END,
                "retry": agent_node.uniq_id,
            },
        )

        factory_logger.info(
            f"[SUBGRAPH-FACTORY] Review node added with conditional routing for {agent_node.name}"
        )
    else:
        # Simple flow: agent -> END
        workflow.add_edge(agent_node.uniq_id, END)

    # Compile the workflow without checkpointer
    # Subgraphs don't need checkpointers - they complete in a single invocation
    # and their state is returned to the parent graph which handles persistence.
    # Using checkpointers here causes event loop mismatch errors when subgraphs
    # are invoked via asyncio.run() in delegation contexts.
    compiled_graph = workflow.compile(checkpointer=None)

    factory_logger.info(f"Subgraph created for {agent_node.name}")

    return compiled_graph
