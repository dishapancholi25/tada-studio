"""Generates node functions for the exported Python file."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from backend.services.export.utils import safe_name

if TYPE_CHECKING:
    from backend.models.workflow import EnhancedNodeData
    from backend.services.export.workflow_analyzer import WorkflowAnalysis


class NodeGenerator:
    """Generates async node functions for agents, conditions, and unsupported types."""

    def generate(self, analysis: WorkflowAnalysis) -> str:
        lines = [
            "# " + "=" * 70,
            "# Node Functions",
            "# " + "=" * 70,
        ]

        # Agent nodes
        for node in analysis.agent_nodes:
            lines.append("")
            lines.append("")
            lines.append(self._generate_agent_node(node, analysis))

        # Condition nodes
        for node in analysis.condition_nodes:
            lines.append("")
            lines.append("")
            lines.append(self._generate_condition_node(node, analysis))

        # Unsupported nodes (stubs)
        for node in analysis.unsupported_nodes:
            lines.append("")
            lines.append("")
            lines.append(self._generate_unsupported_stub(node))

        return "\n".join(lines)

    def _generate_agent_node(
        self, node: EnhancedNodeData, analysis: WorkflowAnalysis
    ) -> str:
        sn = safe_name(node.name)
        node_id = node.uniq_id

        # Build input code based on input_source_config
        input_code = self._generate_input_code(node, analysis)

        # Build tool binding code
        tool_code = self._generate_tool_binding(node, analysis)

        # System prompt
        system_prompt = ""
        if node.agent_config and node.agent_config.system_prompt:
            system_prompt = node.agent_config.system_prompt

        # Escape the system prompt for triple-quoted string
        prompt_escaped = system_prompt.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')

        parts = [
            f"async def node_{sn}(state: WorkflowState) -> dict:",
            f'    """Agent node: {node.name}"""',
            f"    llm = create_llm_{sn}()",
        ]

        # Add tool binding
        if tool_code:
            parts.append(tool_code)

        # Build input
        parts.append(input_code)

        # Build messages
        parts.append("    messages = []")
        if system_prompt:
            parts.append(
                f'    messages.append(SystemMessage(content="""{prompt_escaped}"""))'
            )
        parts.append("    messages.append(HumanMessage(content=input_text))")

        # Invoke
        parts.append("    response = await llm.ainvoke(messages)")
        parts.append(
            "    content = response.content if hasattr(response, 'content') else str(response)"
        )

        # Build state update
        parts.extend(
            [
                "",
                "    # Parse structured output if JSON",
                '    structured = {"response": content}',
                '    fields = {"response": content}',
                "    try:",
                "        parsed = json.loads(content)",
                "        if isinstance(parsed, dict):",
                '            structured = {**parsed, "response": content}',
                '            fields = {**parsed, "response": content}',
                "    except (json.JSONDecodeError, TypeError):",
                "        pass",
                "",
                "    return {",
                '        "messages": [response],',
                '        "node_outputs": {',
                f'            "{node_id}": {{',
                '                "raw": content,',
                '                "structured": structured,',
                '                "fields": fields,',
                "            }",
                "        },",
                f'        "current_node": "{node_id}",',
                "    }",
            ]
        )

        return "\n".join(parts)

    def _generate_condition_node(
        self, node: EnhancedNodeData, analysis: WorkflowAnalysis
    ) -> str:
        sn = safe_name(node.name)
        node_id = node.uniq_id

        cc = node.condition_config
        if not cc:
            return self._generate_default_condition(sn, node_id, node.name)

        branch_mode = getattr(cc, "branch_mode", "binary")
        condition_type = getattr(cc, "condition_type", "simple")

        parts = [
            f"async def node_{sn}(state: WorkflowState) -> dict:",
            f'    """Condition node: {node.name}"""',
        ]

        # Value extraction
        parts.append(self._generate_value_extraction(cc))

        # Evaluation
        if branch_mode == "multi":
            parts.append(self._generate_multi_branch_eval(cc))
        elif condition_type == "expression":
            parts.append(self._generate_expression_eval(cc))
        else:
            parts.append(self._generate_binary_eval(cc))

        # Store result and return
        parts.extend(
            [
                "",
                f'    state[f"__condition_result_{node_id}"] = condition_result',
                "    return {",
                '        "node_outputs": {',
                f'            "{node_id}": {{',
                '                "raw": str(condition_result),',
                '                "structured": {"condition_result": condition_result},',
                '                "fields": {"condition_result": condition_result},',
                "            }",
                "        },",
                f'        "current_node": "{node_id}",',
                "    }",
            ]
        )

        return "\n".join(parts)

    def _generate_value_extraction(self, cc) -> str:
        """Generate code to extract the value for condition evaluation."""
        input_source = getattr(cc, "input_source", "previous")
        source_node_id = getattr(cc, "source_node_id", None)
        field_path = getattr(cc, "field_path", "")

        # Check simple_conditions for source info
        simple_conditions = getattr(cc, "simple_conditions", [])
        if simple_conditions:
            first = simple_conditions[0]
            if hasattr(first, "__dict__"):
                input_source = getattr(first, "input_source", input_source)
                source_node_id = getattr(first, "source_node_id", source_node_id)
                field_path = getattr(first, "field_path", field_path)
            elif isinstance(first, dict):
                input_source = first.get("input_source", input_source)
                source_node_id = first.get("source_node_id", source_node_id)
                field_path = first.get("field_path", field_path)

        if input_source == "specific" and source_node_id:
            if field_path:
                return f'    value = _get_node_output(state, "{source_node_id}", "{field_path}")'
            return f'    value = _get_node_output(state, "{source_node_id}")'
        elif input_source == "start":
            return '    value = state.get("original_message", "")'
        else:
            # previous — get from messages
            return (
                '    messages = state.get("messages", [])\n'
                '    value = messages[-1].content if messages and hasattr(messages[-1], "content") else ""'
            )

    def _generate_binary_eval(self, cc) -> str:
        """Generate binary condition evaluation code."""
        simple_conditions = getattr(cc, "simple_conditions", [])
        logic_operator = getattr(cc, "logic_operator", "AND")

        if not simple_conditions:
            # Passthrough mode — interpret value as boolean
            return (
                "    # Passthrough boolean evaluation\n"
                "    str_val = str(value).strip().lower()\n"
                '    is_true = str_val in ("true", "yes", "1", "on") and str_val not in ("false", "no", "0", "off", "")\n'
                '    condition_result = "0" if is_true else "1"'
            )

        # Operator mode
        lines = ["    # Operator evaluation"]
        lines.append("    results = []")

        for i, cond in enumerate(simple_conditions):
            if hasattr(cond, "__dict__"):
                op = getattr(cond, "operator", "==")
                compare = getattr(cond, "value", "")
                vtype = getattr(cond, "value_type", "auto")
            else:
                op = cond.get("operator", "==")
                compare = cond.get("value", "")
                vtype = cond.get("value_type", "auto")

            compare_repr = repr(compare)
            lines.append(f"    # Condition {i}: value {op} {compare_repr}")
            lines.append(
                f'    results.append(_evaluate_condition(value, {compare_repr}, "{op}", "{vtype}"))'
            )

        if logic_operator == "OR":
            lines.append("    is_true = any(results)")
        else:
            lines.append("    is_true = all(results)")

        lines.append('    condition_result = "0" if is_true else "1"')
        return "\n".join(lines)

    def _generate_multi_branch_eval(self, cc) -> str:
        """Generate multi-branch condition evaluation code."""
        branches = getattr(cc, "branches", [])
        if not branches:
            return '    condition_result = "0"  # No branches configured'

        lines = ["    # Multi-branch evaluation"]
        lines.append('    condition_result = "0"  # Default branch')

        for i, branch in enumerate(branches):
            if hasattr(branch, "__dict__"):
                handle_id = getattr(branch, "handle_id", f"branch-{i}")
                condition = getattr(branch, "condition", {})
            else:
                handle_id = branch.get("handle_id", f"branch-{i}")
                condition = branch.get("condition", {})

            result_key = handle_id.replace("branch-", "")

            # Extract operator and compare value from condition
            if hasattr(condition, "__dict__"):
                op = getattr(condition, "operator", "==")
                compare = getattr(condition, "value", "")
                vtype = getattr(condition, "value_type", "auto")
            elif isinstance(condition, dict):
                op = condition.get("operator", "==")
                compare = condition.get("value", "")
                vtype = condition.get("value_type", "auto")
            else:
                op = "=="
                compare = ""
                vtype = "auto"

            compare_repr = repr(compare)
            prefix = "if" if i == 0 else "elif"
            lines.append(
                f'    {prefix} _evaluate_condition(value, {compare_repr}, "{op}", "{vtype}"):'
            )
            lines.append(f'        condition_result = "{result_key}"')

        return "\n".join(lines)

    def _generate_expression_eval(self, cc) -> str:
        """Generate expression-based condition evaluation code."""
        expression = getattr(cc, "expression", "True")
        expr_escaped = expression.replace("\\", "\\\\").replace('"', '\\"')
        return (
            f"    # Expression evaluation\n"
            f"    try:\n"
            f'        expr_result = eval("{expr_escaped}", {{"value": value, "state": state}})\n'
            f"    except Exception:\n"
            f"        expr_result = False\n"
            f'    condition_result = "0" if expr_result else "1"'
        )

    def _generate_default_condition(self, sn: str, node_id: str, name: str) -> str:
        return "\n".join(
            [
                f"async def node_{sn}(state: WorkflowState) -> dict:",
                f'    """Condition node: {name} (default - always takes true branch)"""',
                '    condition_result = "0"',
                f'    state[f"__condition_result_{node_id}"] = condition_result',
                "    return {",
                f'        "node_outputs": {{"{node_id}": {{"raw": "true", "fields": {{}}}}}},',
                f'        "current_node": "{node_id}",',
                "    }",
            ]
        )

    def _generate_input_code(
        self, node: EnhancedNodeData, analysis: WorkflowAnalysis
    ) -> str:
        """Generate input building code for an agent node."""
        config = node.input_source_config
        if not config:
            # Default: previous node output
            incoming = self._find_incoming_ids(node, analysis)
            return f"    input_text = _get_previous_output(state, {repr(incoming)})"

        mode = getattr(config, "source_mode", "previous")

        if mode == "start":
            return '    input_text = state.get("original_message", "")'
        elif mode == "specific":
            source_ids = getattr(config, "source_node_ids", []) or []
            if not source_ids:
                sid = getattr(config, "source_node_id", None)
                if sid:
                    source_ids = [sid]
            if len(source_ids) == 1:
                return f'    input_text = _get_node_output(state, "{source_ids[0]}")'
            elif source_ids:
                parts = ["    parts = []"]
                for sid in source_ids:
                    parts.append(f'    parts.append(_get_node_output(state, "{sid}"))')
                parts.append('    input_text = "\\n\\n".join(p for p in parts if p)')
                return "\n".join(parts)
            else:
                incoming = self._find_incoming_ids(node, analysis)
                return f"    input_text = _get_previous_output(state, {repr(incoming)})"
        elif mode == "custom":
            template = getattr(config, "custom_template", "") or ""
            # Replace START node references with {original} keyword
            if analysis.start_node:
                start_id = analysis.start_node.uniq_id
                template = template.replace("{" + start_id + "}", "{original}")
                # Also handle {start_id.field} patterns — START has no fields
                template = template.replace("{" + start_id + ".", "{original}")
            template_escaped = template.replace("\\", "\\\\").replace('"', '\\"')
            return f'    input_text = _resolve_template(state, "{template_escaped}")'
        else:
            # previous
            incoming = self._find_incoming_ids(node, analysis)
            return f"    input_text = _get_previous_output(state, {repr(incoming)})"

    def _generate_tool_binding(
        self, node: EnhancedNodeData, analysis: WorkflowAnalysis
    ) -> str:
        """Generate tool binding code for an agent node."""
        tool_nodes = analysis.agent_tool_map.get(node.uniq_id, [])
        if not tool_nodes:
            return ""

        lines = ["    tools = []"]
        for tn in tool_nodes:
            tsn = safe_name(tn.name)
            lines.append(f"    tools.append(create_tool_{tsn}())")
        lines.append("    if tools:")
        lines.append("        llm = llm.bind_tools(tools)")
        return "\n".join(lines)

    def _find_incoming_ids(
        self, node: EnhancedNodeData, analysis: WorkflowAnalysis
    ) -> List[str]:
        """Find incoming node IDs from the edge topology."""
        incoming = []
        for src, tgt in analysis.edge_topology.sequential_edges:
            if tgt == node.uniq_id:
                incoming.append(src)
        for cond_id, targets in analysis.edge_topology.conditional_edges.items():
            for _, tgt in targets.items():
                if tgt == node.uniq_id:
                    incoming.append(cond_id)
        for src, targets in analysis.edge_topology.parallel_sources.items():
            if node.uniq_id in targets:
                incoming.append(src)
        return incoming

    def _generate_unsupported_stub(self, node: EnhancedNodeData) -> str:
        sn = safe_name(node.name)
        type_val = node.type.value if hasattr(node.type, "value") else str(node.type)
        return "\n".join(
            [
                f"async def node_{sn}(state: WorkflowState) -> dict:",
                f'    """Unsupported node type: {type_val}"""',
                f"    # TODO: Implement {type_val} node logic",
                "    raise NotImplementedError(",
                f'        "Node type {type_val} ({node.name}) is not supported in exported workflows. "',
                '        "Please implement this node manually."',
                "    )",
            ]
        )
