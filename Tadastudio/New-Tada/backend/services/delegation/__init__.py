"""Delegation service for multi-agent orchestration.

This service provides functionality for creating and managing delegation tools
that allow orchestrator agents to delegate tasks to sub-agents and sub-workflows.

Public API:
    - AgentDelegationToolFactory: Main factory for creating delegation tools
    - detect_orchestrator_pattern: Detect if a node is an orchestrator
    - create_handoff_tool: Create handoff tools for agent transfers

Example:
    >>> from backend.services.delegation import AgentDelegationToolFactory
    >>> factory = AgentDelegationToolFactory(graph_manager)
    >>> tools = factory.create_delegation_tools_for_orchestrator(
    ...     orchestrator_node, connected_agents
    ... )
"""


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name == "detect_orchestrator_pattern":
        from .detection import detect_orchestrator_pattern

        return detect_orchestrator_pattern
    elif name == "AgentDelegationToolFactory":
        from .factories import AgentDelegationToolFactory

        return AgentDelegationToolFactory
    elif name == "create_handoff_tool":
        from .factories import create_handoff_tool

        return create_handoff_tool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AgentDelegationToolFactory",
    "detect_orchestrator_pattern",
    "create_handoff_tool",
]
