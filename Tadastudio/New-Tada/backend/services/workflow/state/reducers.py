"""
Custom reducer functions for LangGraph state management.

Reducers are functions that control how state updates are merged when multiple
nodes update the same state field. This is especially important for parallel
node execution where concurrent updates must be handled correctly.

LangGraph's State System:
    When a node returns a state update, LangGraph merges it with the current state.
    For fields with Annotated types that include a reducer, the reducer function
    determines how the old and new values are combined.

Common Patterns:
    - last_value_reducer: Keep the most recent value (for scalar fields)
    - merge_node_outputs: Merge dictionaries (for accumulating outputs)
    - merge_results: Concatenate lists (for collecting results)
    - max_execution_order: Take maximum (for counters)

Example:
    >>> from typing import Annotated
    >>> from langgraph.graph import StateGraph
    >>>
    >>> # Define state with custom reducer
    >>> class MyState(TypedDict):
    ...     counter: Annotated[int, max_execution_order]
    ...     outputs: Annotated[Dict[str, str], merge_node_outputs]
    >>>
    >>> # When two nodes update counter to 3 and 5, result is max(3, 5) = 5
    >>> # When two nodes add to outputs, dicts are merged

See Also:
    - https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers
    - backend.services.workflow.state.schemas: State type definitions
"""

# Import type hints from schemas module
# We import TYPE_CHECKING to avoid circular imports at runtime
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from .schemas import NodeOutput, NodeResult, WorkflowMetadata


def last_value_reducer(current: Optional[str], updates: Optional[str]) -> Optional[str]:
    """
    Reducer that keeps the last non-None value.

    This reducer is used for fields where concurrent updates should be resolved
    by simply taking the most recent value. If the update is None, the current
    value is preserved.

    Args:
        current: The current value in the state
        updates: The new value from the node update

    Returns:
        The update value if not None, otherwise the current value

    Example:
        >>> last_value_reducer("old", "new")
        'new'
        >>> last_value_reducer("old", None)
        'old'
        >>> last_value_reducer(None, "new")
        'new'

    Used For:
        - WorkflowState.current_node: Track which node is currently executing
    """
    return updates if updates is not None else current


def merge_node_outputs(
    current: Dict[str, "NodeOutput"], updates: Dict[str, "NodeOutput"]
) -> Dict[str, "NodeOutput"]:
    """
    Reducer that merges node output dictionaries.

    This reducer ensures that node outputs from different nodes are preserved
    and merged correctly. When a node re-executes (e.g., after checkpoint resume),
    its new output overwrites the old one.

    Args:
        current: The current node_outputs dictionary in the state
        updates: New node outputs from the node update

    Returns:
        Merged dictionary with all node outputs

    Example:
        >>> current = {"node1": {"raw": "output1", "fields": {}}}
        >>> updates = {"node2": {"raw": "output2", "fields": {}}}
        >>> result = merge_node_outputs(current, updates)
        >>> len(result)
        2
        >>> "node1" in result and "node2" in result
        True

    Behavior:
        - If current is None, returns updates (or empty dict)
        - If updates is None, returns current
        - Otherwise, merges updates into a copy of current (updates override)

    Used For:
        - WorkflowState.node_outputs: Accumulate outputs from all executed nodes
    """
    if current is None:
        return updates or {}
    if updates is None:
        return current

    # Create a new dict with current values
    merged = dict(current)
    # Update with new values (overwrites existing keys)
    merged.update(updates)
    return merged


def merge_metadata(
    current: Optional["WorkflowMetadata"], updates: Optional["WorkflowMetadata"]
) -> "WorkflowMetadata":
    """
    Reducer that merges metadata from parallel nodes.

    This reducer handles concurrent metadata updates when multiple nodes execute
    in parallel. It keeps the most recent non-None value for each metadata field,
    while preserving fields that aren't in the update.

    Args:
        current: The current metadata dictionary in the state
        updates: New metadata from the node update

    Returns:
        Merged metadata dictionary

    Example:
        >>> current = {"execution_started": "2025-10-13T10:00:00Z", "current_node_name": "node1"}
        >>> updates = {"current_node_name": "node2", "current_node_type": "AGENT"}
        >>> result = merge_metadata(current, updates)
        >>> result["execution_started"]
        '2025-10-13T10:00:00Z'
        >>> result["current_node_name"]
        'node2'
        >>> result["current_node_type"]
        'AGENT'

    Behavior:
        - If current is None, returns updates (or empty dict)
        - If updates is None, returns current
        - Otherwise, merges updates into current, keeping non-None values

    Used For:
        - WorkflowState.metadata: Track execution metadata across parallel nodes
    """
    if current is None:
        return updates or {}  # type: ignore
    if updates is None:
        return current

    # Create a new dict with current values
    merged = dict(current)

    # For parallel nodes, we want to keep the most recent update
    # but preserve other fields that may not be in the update
    if updates:
        for key, value in updates.items():
            if value is not None:  # Only update non-None values
                merged[key] = value

    return merged  # type: ignore


def max_execution_order(current: int, updates: int) -> int:
    """
    Reducer that keeps the maximum execution order value.

    This reducer handles parallel nodes that may have the same execution order
    by taking the maximum value. This ensures the execution order counter
    always progresses forward.

    Args:
        current: The current execution order in the state
        updates: New execution order from the node update

    Returns:
        Maximum of current and updates

    Example:
        >>> max_execution_order(3, 5)
        5
        >>> max_execution_order(10, 7)
        10
        >>> max_execution_order(None, 5)
        5

    Behavior:
        - If current is None, returns updates (or 0)
        - If updates is None, returns current
        - Otherwise, returns max(current, updates)

    Used For:
        - WorkflowState.execution_order: Sequential execution order counter
    """
    if current is None:
        return updates or 0
    if updates is None:
        return current
    return max(current, updates)


def merge_review_state(
    current: Optional[Dict[str, Dict]], updates: Optional[Dict[str, Dict]]
) -> Dict[str, Dict]:
    """
    Reducer that merges review state dictionaries.

    This reducer handles concurrent updates to review states for different agent nodes.
    Each agent node has its own review state keyed by node_id.

    Args:
        current: The current review_state dictionary in the state
        updates: New review state updates from the node

    Returns:
        Merged review state dictionary

    Example:
        >>> current = {"node1": {"output": "result1", "iteration": 1}}
        >>> updates = {"node2": {"output": "result2", "iteration": 1}}
        >>> result = merge_review_state(current, updates)
        >>> "node1" in result and "node2" in result
        True

    Behavior:
        - If current is None, returns updates (or empty dict)
        - If updates is None, returns current
        - Otherwise, merges updates into a copy of current (updates override per key)
        - If a node_id update is None, removes that entry (clearing review state)

    Used For:
        - WorkflowState.review_state: Track review loop state for each agent node
    """
    if current is None:
        return updates or {}
    if updates is None:
        return current

    # Create a new dict with current values
    merged = dict(current)

    # Update with new values, handling None to clear entries
    for node_id, state in updates.items():
        if state is None:
            # Clear review state for this node (approved/completed)
            merged.pop(node_id, None)
        else:
            merged[node_id] = state

    return merged


def merge_results(
    current: List["NodeResult"], updates: List["NodeResult"]
) -> List["NodeResult"]:
    """
    Reducer that merges result lists from parallel nodes.

    This reducer handles concurrent updates when multiple nodes add results
    simultaneously. It concatenates the lists to preserve all results.

    Args:
        current: The current results list in the state
        updates: New results from the node update

    Returns:
        Concatenated list of all results

    Example:
        >>> current = [{"agent": "Agent1", "response": "Result1"}]
        >>> updates = [{"agent": "Agent2", "response": "Result2"}]
        >>> result = merge_results(current, updates)
        >>> len(result)
        2

    Behavior:
        - If current is None, returns updates (or empty list)
        - If updates is None, returns current
        - Otherwise, concatenates lists (current + updates)

    Used For:
        - WorkflowState.results: Accumulate execution history from all nodes

    Note:
        This preserves the execution order of results. Results from 'current'
        appear before results from 'updates' in the merged list.
    """
    if current is None:
        return updates or []
    if updates is None:
        return current

    # Combine both lists
    merged = list(current) if current else []
    if updates:
        merged.extend(updates)
    return merged


# Export all reducer functions
__all__ = [
    "last_value_reducer",
    "merge_node_outputs",
    "merge_metadata",
    "max_execution_order",
    "merge_results",
    "merge_review_state",
]
