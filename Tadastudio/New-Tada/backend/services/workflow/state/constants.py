"""
Constants for workflow state management.

This module defines special constants used in LangGraph workflow state management,
particularly for identifying special node types and control flow points.

These constants are used by both LangGraph's internal state management system
and by the workflow execution engine to handle special cases in the workflow graph.
"""

# Special node identifiers for LangGraph control flow
# These match LangGraph's internal special node names

ENTRY_POINT = "__start__"
"""
The entry point node identifier for LangGraph workflows.

This constant represents the implicit START node that LangGraph creates
at the beginning of every workflow. It's used when setting the entry point
for the state graph.

Example:
    >>> from langgraph.graph import StateGraph
    >>> workflow = StateGraph(WorkflowState)
    >>> workflow.set_entry_point("first_node")  # Internally uses __start__
"""

EXIT_POINT = "__end__"
"""
The exit point node identifier for LangGraph workflows.

This constant represents the implicit END node that LangGraph uses to
terminate workflow execution. Edges pointing to END will finish the workflow.

Example:
    >>> from langgraph.graph import END
    >>> workflow.add_edge("last_node", END)  # END == "__end__"
"""

INTERRUPT_POINT = "__interrupt__"
"""
The interrupt point identifier for human-in-the-loop workflows.

This constant is used when a workflow needs to pause for human input.
When a node returns this special value, LangGraph suspends execution
and waits for external input before resuming.

Example:
    >>> def human_input_node(state):
    ...     return {"next": "__interrupt__"}  # Pauses workflow
"""

ERROR_POINT = "__error__"
"""
The error point identifier for error handling in workflows.

This constant can be used to identify error states or special error
handling nodes in the workflow graph.

Note:
    This is a custom constant and not a built-in LangGraph special node.
    It's used by the application for error handling conventions.
"""


# Export all constants
__all__ = [
    "ENTRY_POINT",
    "EXIT_POINT",
    "INTERRUPT_POINT",
    "ERROR_POINT",
]
