"""Generates input-building helper functions for the exported Python file."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.export.workflow_analyzer import WorkflowAnalysis


class HelpersGenerator:
    """Generates helper functions for input source resolution."""

    def generate(self, analysis: WorkflowAnalysis) -> str:
        lines = [
            "# " + "=" * 70,
            "# Input Building Helpers",
            "# " + "=" * 70,
        ]

        lines.append("")
        lines.append(self._generate_get_previous_output())
        lines.append("")
        lines.append("")
        lines.append(self._generate_get_node_output())

        if "custom" in analysis.input_modes_used:
            lines.append("")
            lines.append("")
            lines.append(self._generate_resolve_template())

        return "\n".join(lines)

    def _generate_get_previous_output(self) -> str:
        return '''def _get_previous_output(state: WorkflowState, incoming_node_ids: List[str]) -> str:
    """Get output from the previous node in the workflow."""
    node_outputs = state.get("node_outputs", {})
    for prev_id in reversed(incoming_node_ids):
        if prev_id in node_outputs:
            return node_outputs[prev_id].get("raw", "")
    return state.get("original_message", "")'''

    def _generate_get_node_output(self) -> str:
        return '''def _get_node_output(state: WorkflowState, node_id: str, field_path: str = "") -> Any:
    """Get output from a specific node, optionally extracting a field."""
    node_outputs = state.get("node_outputs", {})
    output = node_outputs.get(node_id, {})
    if not field_path:
        return output.get("raw", "")
    # Try fields dict first
    fields = output.get("fields", {})
    if field_path in fields:
        return fields[field_path]
    # Try structured output
    structured = output.get("structured", {})
    if structured and field_path in structured:
        return structured[field_path]
    # Try parsing raw as JSON
    raw = output.get("raw", "")
    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, dict) and field_path in data:
                return data[field_path]
        except (json.JSONDecodeError, TypeError):
            pass
    return output.get("raw", "")'''

    def _generate_resolve_template(self) -> str:
        return '''def _resolve_template(state: WorkflowState, template: str) -> str:
    """Resolve a custom template with variable substitution."""
    result = template
    result = result.replace("{original}", state.get("original_message", ""))
    messages = state.get("messages", [])
    if messages:
        result = result.replace("{previous}", getattr(messages[-1], "content", ""))
    # Replace {node_id.field} patterns
    node_outputs = state.get("node_outputs", {})
    field_pattern = re.compile(r"\\{([^}]+)\\.([^}]+)\\}")
    for match in field_pattern.finditer(result):
        nid, fld = match.group(1), match.group(2)
        if nid in node_outputs:
            output = node_outputs[nid]
            value = None
            if output.get("fields"):
                value = output["fields"].get(fld)
            if value is None and output.get("structured"):
                value = output["structured"].get(fld)
            if value is None:
                raw = output.get("raw", "")
                try:
                    data = json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(data, dict):
                        value = data.get(fld)
                except (json.JSONDecodeError, TypeError):
                    pass
            result = result.replace(match.group(0), str(value) if value is not None else "")
    # Replace {node_id} patterns (raw output)
    node_pattern = re.compile(r"\\{([^}.]+)\\}")
    for match in node_pattern.finditer(result):
        nid = match.group(1)
        if nid in node_outputs:
            result = result.replace(match.group(0), node_outputs[nid].get("raw", ""))
    return result'''
