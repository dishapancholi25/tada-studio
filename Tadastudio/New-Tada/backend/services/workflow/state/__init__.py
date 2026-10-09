"""
Workflow state management for LangGraph workflows.

This module provides state schemas, reducer functions, and constants for managing
the state that flows through LangGraph workflow graphs.

Main Exports:
    - WorkflowState: The main state TypedDict for LangGraph workflows
    - NodeOutput: Structure for capturing node execution outputs
    - Reducer functions: Custom state merge functions
    - Constants: Special node identifiers (ENTRY_POINT, EXIT_POINT, etc.)

Example:
    >>> from backend.services.workflow.state import WorkflowState, NodeOutput
    >>> from langgraph.graph import StateGraph
    >>>
    >>> # Create workflow with WorkflowState
    >>> workflow = StateGraph(WorkflowState)
    >>>
    >>> # Define node that returns NodeOutput
    >>> def my_node(state: WorkflowState) -> dict:
    ...     output: NodeOutput = {
    ...         "raw": "Hello World",
    ...         "structured": {"key": "value"},
    ...         "fields": {"extracted": "data"}
    ...     }
    ...     return {"node_outputs": {"my_node": output}}

Usage Notes:
    - WorkflowState uses custom reducers to handle parallel node execution
    - Import reducers if you need to use them in other TypedDict definitions
    - Constants are useful when building conditional edges or checking node states

See Also:
    - backend.services.workflow.state.schemas: TypedDict definitions
    - backend.services.workflow.state.reducers: Reducer function implementations
    - backend.services.workflow.state.constants: Special node constants
"""

# Import constants
from .constants import ENTRY_POINT, ERROR_POINT, EXIT_POINT, INTERRUPT_POINT

# Import reducer functions
from .reducers import (
    last_value_reducer,
    max_execution_order,
    merge_metadata,
    merge_node_outputs,
    merge_results,
)

# Import core schemas
from .schemas import (
    MemoryContext,
    NodeOutput,
    NodeResult,
    OrchestrationContext,
    StateTransition,
    StateUpdate,
    WorkflowMetadata,
    WorkflowState,
)


# Public API - these are the most commonly used exports
__all__ = [
    # Core state schemas (most commonly used)
    "WorkflowState",
    "NodeOutput",
    # Additional schemas (less commonly used, but exported for completeness)
    "NodeResult",
    "WorkflowMetadata",
    "MemoryContext",
    "OrchestrationContext",
    "StateUpdate",
    "StateTransition",
    # Reducer functions (typically used automatically via Annotated types)
    "last_value_reducer",
    "merge_node_outputs",
    "merge_metadata",
    "max_execution_order",
    "merge_results",
    # Constants (useful for conditional logic)
    "ENTRY_POINT",
    "EXIT_POINT",
    "INTERRUPT_POINT",
    "ERROR_POINT",
]
