"""Generates WorkflowState and reducer definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.export.workflow_analyzer import WorkflowAnalysis


class StateGenerator:
    """Generates the state schema section of the exported file."""

    def generate(self, analysis: WorkflowAnalysis) -> str:
        parts = []
        parts.append(self._generate_reducers(analysis))
        parts.append(self._generate_types())
        parts.append(self._generate_state())
        return "\n\n\n".join(parts)

    def _generate_reducers(self, analysis: WorkflowAnalysis) -> str:
        lines = [
            "# " + "=" * 70,
            "# State Reducers",
            "# " + "=" * 70,
            "",
        ]

        # merge_node_outputs — always needed
        lines.append(
            '''def merge_node_outputs(
    current: Dict[str, Any], updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge node output dictionaries."""
    if current is None:
        return updates or {}
    if updates is None:
        return current
    merged = dict(current)
    merged.update(updates)
    return merged'''
        )

        # last_value_reducer — always needed
        lines.append("")
        lines.append("")
        lines.append(
            '''def last_value_reducer(current: Optional[str], updates: Optional[str]) -> Optional[str]:
    """Keep the most recent non-None value."""
    return updates if updates is not None else current'''
        )

        # merge_results — include if parallel edges
        lines.append("")
        lines.append("")
        lines.append(
            '''def merge_results(
    current: List[Any], updates: List[Any]
) -> List[Any]:
    """Concatenate result lists."""
    if current is None:
        return updates or []
    if updates is None:
        return current
    merged = list(current) if current else []
    if updates:
        merged.extend(updates)
    return merged'''
        )

        # merge_metadata — always useful for tracking
        lines.append("")
        lines.append("")
        lines.append(
            '''def merge_metadata(
    current: Optional[Dict[str, Any]], updates: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Merge metadata, keeping non-None values."""
    if current is None:
        return updates or {}
    if updates is None:
        return current
    merged = dict(current)
    if updates:
        for key, value in updates.items():
            if value is not None:
                merged[key] = value
    return merged'''
        )

        # max_execution_order
        lines.append("")
        lines.append("")
        lines.append(
            '''def max_execution_order(current: int, updates: int) -> int:
    """Keep the maximum execution order value."""
    if current is None:
        return updates or 0
    if updates is None:
        return current
    return max(current, updates)'''
        )

        return "\n".join(lines)

    def _generate_types(self) -> str:
        lines = [
            "# " + "=" * 70,
            "# Type Definitions",
            "# " + "=" * 70,
            "",
            "",
        ]
        lines.append(
            '''class NodeOutput(TypedDict, total=False):
    """Output from a single node execution."""
    raw: str
    structured: Optional[Dict[str, Any]]
    fields: Dict[str, Any]'''
        )
        lines.append("")
        lines.append("")
        lines.append(
            '''class NodeResult(TypedDict, total=False):
    """Result entry for execution history."""
    agent: Optional[str]
    response: str
    tools: List[str]
    tool_executions: List[Dict[str, Any]]'''
        )
        return "\n".join(lines)

    def _generate_state(self) -> str:
        return '''class WorkflowState(TypedDict):
    """Main state that flows through the LangGraph workflow."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    original_message: str
    node_outputs: Annotated[Dict[str, "NodeOutput"], merge_node_outputs]
    results: Annotated[List["NodeResult"], merge_results]
    current_node: Annotated[Optional[str], last_value_reducer]
    execution_id: str
    graph_name: str
    metadata: Annotated[Dict[str, Any], merge_metadata]
    execution_order: Annotated[int, max_execution_order]'''
