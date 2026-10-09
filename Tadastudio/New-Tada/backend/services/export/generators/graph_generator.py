"""Generates graph construction and routing functions for the exported Python file."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.services.export.utils import safe_name

if TYPE_CHECKING:
    from backend.services.export.workflow_analyzer import WorkflowAnalysis


class GraphGenerator:
    """Generates routing functions and the build_graph() function."""

    def generate(self, analysis: WorkflowAnalysis) -> str:
        parts = []

        # Condition evaluation helper (needed by condition nodes)
        if analysis.condition_nodes:
            parts.append(self._generate_eval_helper())

        # Routing functions for condition nodes
        for node in analysis.condition_nodes:
            parts.append(self._generate_routing_function(node, analysis))

        # build_graph() function
        parts.append(self._generate_build_graph(analysis))

        return "\n\n\n".join(parts)

    def _generate_eval_helper(self) -> str:
        """Generate the _evaluate_condition helper used by condition nodes."""
        header = "# " + "=" * 70 + "\n# Condition Evaluation Helper\n# " + "=" * 70
        return (
            header
            + '''


def _evaluate_condition(value: Any, compare_value: Any, operator: str, value_type: str = "auto") -> bool:
    """Evaluate a single condition with the given operator."""
    # Determine if numeric comparison
    is_numeric = value_type == "number" or (
        value_type == "auto" and _is_numeric(compare_value)
    )

    if is_numeric:
        try:
            val = float(value) if value is not None else 0
            cmp = float(compare_value) if compare_value is not None else 0
            ops = {"==": val == cmp, "!=": val != cmp, ">": val > cmp,
                   "<": val < cmp, ">=": val >= cmp, "<=": val <= cmp}
            return ops.get(operator, False)
        except (ValueError, TypeError):
            return False

    val_str = str(value) if value is not None else ""
    cmp_str = str(compare_value) if compare_value is not None else ""

    ops = {
        "==": val_str == cmp_str,
        "!=": val_str != cmp_str,
        "contains": cmp_str.lower() in val_str.lower(),
        "not_contains": cmp_str.lower() not in val_str.lower(),
        "starts_with": val_str.lower().startswith(cmp_str.lower()),
        "ends_with": val_str.lower().endswith(cmp_str.lower()),
        "is_empty": not val_str.strip(),
        "is_not_empty": bool(val_str.strip()),
        "matches": bool(re.search(cmp_str, val_str)) if cmp_str else False,
    }
    return ops.get(operator, False)


def _is_numeric(value: Any) -> bool:
    """Check if a value is numeric."""
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except ValueError:
            return False
    return False'''
        )

    def _generate_routing_function(self, node, analysis) -> str:
        """Generate a routing function for a condition node."""
        sn = safe_name(node.name)
        node_id = node.uniq_id

        return "\n".join(
            [
                f"def route_{sn}(state: WorkflowState) -> str:",
                f'    """Routing function for condition: {node.name}"""',
                f'    result = state.get(f"__condition_result_{node_id}")',
                "    if result is not None:",
                "        return str(result)",
                '    return "0"  # Default to first branch',
            ]
        )

    def _generate_build_graph(self, analysis: WorkflowAnalysis) -> str:
        """Generate the build_graph() function."""
        lines = [
            "# " + "=" * 70,
            "# Graph Construction",
            "# " + "=" * 70,
            "",
            "",
            "def build_graph() -> StateGraph:",
            f'    """Build the LangGraph workflow: {analysis.workflow_name}"""',
            "    workflow = StateGraph(WorkflowState)",
            "",
            "    # Add nodes",
        ]

        # Add agent nodes
        for node in analysis.agent_nodes:
            sn = safe_name(node.name)
            lines.append(f'    workflow.add_node("{node.uniq_id}", node_{sn})')

        # Add condition nodes
        for node in analysis.condition_nodes:
            sn = safe_name(node.name)
            lines.append(f'    workflow.add_node("{node.uniq_id}", node_{sn})')

        # Add unsupported nodes
        for node in analysis.unsupported_nodes:
            sn = safe_name(node.name)
            lines.append(f'    workflow.add_node("{node.uniq_id}", node_{sn})')

        # Set entry point
        if analysis.edge_topology.entry_node_id:
            lines.append("")
            lines.append("    # Set entry point")
            lines.append(
                f'    workflow.set_entry_point("{analysis.edge_topology.entry_node_id}")'
            )

        # Add sequential edges
        if analysis.edge_topology.sequential_edges:
            lines.append("")
            lines.append("    # Sequential edges")
            for src, tgt in analysis.edge_topology.sequential_edges:
                if tgt == "__end__":
                    lines.append(f'    workflow.add_edge("{src}", END)')
                else:
                    lines.append(f'    workflow.add_edge("{src}", "{tgt}")')

        # Add conditional edges
        if analysis.edge_topology.conditional_edges:
            lines.append("")
            lines.append("    # Conditional edges")
            for cond_id, targets in analysis.edge_topology.conditional_edges.items():
                cond_node = analysis.node_map.get(cond_id)
                if cond_node:
                    sn = safe_name(cond_node.name)
                    # Build target dict
                    target_items = []
                    for key, tgt in targets.items():
                        if tgt == "__end__":
                            target_items.append(f'        "{key}": END,')
                        else:
                            target_items.append(f'        "{key}": "{tgt}",')
                    targets_str = "\n".join(target_items)
                    lines.append("    workflow.add_conditional_edges(")
                    lines.append(f'        "{cond_id}",')
                    lines.append(f"        route_{sn},")
                    lines.append("        {")
                    lines.append(targets_str)
                    lines.append("        },")
                    lines.append("    )")

        # Add parallel edges
        if analysis.edge_topology.parallel_sources:
            lines.append("")
            lines.append("    # Parallel fan-out edges")
            for src, targets in analysis.edge_topology.parallel_sources.items():
                for tgt in targets:
                    if tgt == "__end__":
                        lines.append(f'    workflow.add_edge("{src}", END)')
                    else:
                        lines.append(f'    workflow.add_edge("{src}", "{tgt}")')

        lines.append("")
        lines.append("    return workflow")

        return "\n".join(lines)
