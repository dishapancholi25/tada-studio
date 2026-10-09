"""
Type definitions for state execution tracking.

This module provides TypedDicts, Protocols, and custom types for
type-safe state management in LangGraph workflows.
"""

from typing import Any, Dict, Protocol, TypedDict

from typing_extensions import NotRequired


class StateMetadata(TypedDict, total=False):
    """
    Metadata stored in workflow state.

    Attributes:
        current_node_name: Display name of the currently executing node
        current_node_type: Type of the current node (AGENT, CONDITION, etc.)
        last_execution_order: The execution order when this node started
    """

    current_node_name: str
    current_node_type: str
    last_execution_order: int


class WorkflowStateProtocol(Protocol):
    """
    Protocol defining the minimum required state structure.

    This protocol allows type checking without requiring specific state classes.
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the state dictionary."""
        ...


class StateUpdate(TypedDict, total=False):
    """
    Dictionary representing a state update.

    Attributes:
        execution_order: Updated execution order value
        current_node: ID of the currently executing node
        metadata: Updated metadata dictionary
    """

    execution_order: int
    current_node: str
    metadata: StateMetadata


class NodeExecutionInfo(TypedDict):
    """
    Information about current node execution.

    Attributes:
        current_node: ID of the current node (may be None)
        current_order: Current execution order
        node_name: Display name of the node (may be None)
        node_type: Type of the node (may be None)
    """

    current_node: NotRequired[str]
    current_order: int
    node_name: NotRequired[str]
    node_type: NotRequired[str]


# Type aliases for common patterns
WorkflowState = Dict[str, Any]  # Generic workflow state dictionary
ExecutionOrder = int  # Execution order value (non-negative integer)
NodeId = str  # Unique node identifier
NodeName = str  # Display name for a node
NodeType = str  # Node type (AGENT, CONDITION, START, END, etc.)
