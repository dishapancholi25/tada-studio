"""
LangGraph subgraph implementation for proper async delegation.

This package provides native LangGraph subgraph support for sub-agent and
sub-workflow execution, eliminating the need for new event loops and
context variable workarounds.

Public API:
    - SubgraphBuilder: Creates and caches subgraphs
    - SubgraphExecutor: Executes subgraphs with proper state management
    - SubAgentState: State TypedDict for sub-agent execution
    - SubWorkflowState: State TypedDict for sub-workflow execution
    - create_subagent_graph: Convenience function for backward compatibility
"""

# Lazy imports to avoid circular dependencies
_lazy_imports = {
    "SubgraphBuilder": ".builder",
    "SubgraphExecutor": ".executor",
    "SubAgentState": ".models",
    "SubWorkflowState": ".models",
    "TokenCounts": ".models",
    "ToolExecution": ".models",
    "ToolNodeMapping": ".models",
}


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name in _lazy_imports:
        from importlib import import_module

        module = import_module(_lazy_imports[name], __package__)
        return getattr(module, name)
    if name == "create_subagent_graph":
        return _create_subagent_graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _create_subagent_graph(agent_node, graph_manager):
    """
    Create a subgraph for a delegated agent.

    This is a convenience function that creates a SubgraphBuilder
    and returns a compiled subgraph.

    Args:
        agent_node: The agent node to create a subgraph for
        graph_manager: The GraphManager instance

    Returns:
        Compiled StateGraph ready for execution
    """
    from .builder import SubgraphBuilder

    builder = SubgraphBuilder(graph_manager)
    return builder.create_subagent_graph(agent_node)


# For backwards compatibility with `from subgraph import *`
__all__ = [
    "SubgraphBuilder",
    "SubgraphExecutor",
    "SubAgentState",
    "SubWorkflowState",
    "ToolExecution",
    "ToolNodeMapping",
    "TokenCounts",
    "create_subagent_graph",
]
