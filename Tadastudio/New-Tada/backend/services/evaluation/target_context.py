"""Target context resolution for evaluation datasets.

Resolves metadata about a workflow, agent, model, or tool target so that
the frontend can display context cards, suggest judge criteria, suggest
tags, and pre-fill AI seed prompts — all without any LLM calls.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.models.configuration.model_deployment import ModelDeployment
from backend.models.workflows import Workflow
from backend.models.workflows.graph_definition import GraphDefinition
from backend.services.database import get_db

logger = logging.getLogger(__name__)


class TargetContextService:
    """Resolve rich context for an evaluation target (workflow / agent / model / tool)."""

    # ── public API ─────────────────────────────────────────────────

    def resolve_context(
        self,
        target_type: str,
        target_id: str,
        workflow_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return a dict matching ``TargetContextResponse`` fields.

        Raises ``LookupError`` only when the primary DB entity cannot be found.
        All other failures are caught and result in partial data.
        """
        if target_type == "workflow":
            return self._resolve_workflow(target_id)
        if target_type == "agent":
            return self._resolve_agent(target_id, workflow_id)
        if target_type == "model":
            return self._resolve_model(target_id)
        if target_type == "tool":
            return self._resolve_tool(target_id, workflow_id)
        raise LookupError(f"Unknown target_type: {target_type}")

    # ── workflow ───────────────────────────────────────────────────

    def _resolve_workflow(self, workflow_id: str) -> Dict[str, Any]:
        with get_db() as db:
            wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if not wf:
                raise LookupError(f"Workflow {workflow_id} not found")

            display_name = wf.name or workflow_id
            description = wf.description or ""

            gd = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.workflow_id == workflow_id,
                    GraphDefinition.is_latest.is_(True),
                )
                .first()
            )

        nodes = self._parse_graph_nodes(gd.definition_json if gd else {})
        agent_nodes = [n for n in nodes if self._get_node_type(n).upper() == "AGENT"]

        purposes: List[str] = []
        models: List[str] = []
        all_tools: List[str] = []
        for an in agent_nodes:
            cfg = self._extract_agent_config(an)
            if cfg.get("purpose"):
                purposes.append(cfg["purpose"][:120])
            if cfg.get("model_info"):
                models.append(cfg["model_info"])
            all_tools.extend(cfg.get("tools", []))

        purpose = description or ("; ".join(purposes) if purposes else None)
        model_info = ", ".join(dict.fromkeys(models)) if models else None
        tools = list(dict.fromkeys(all_tools)) if all_tools else None

        return self._build_response(
            target_type="workflow",
            target_id=workflow_id,
            display_name=display_name,
            purpose=purpose,
            model_info=model_info,
            tools=tools,
            suggested_judge_criteria={
                "task_completion": "The workflow completes the requested task successfully",
                "response_quality": "The output is accurate, relevant, and well-structured",
                "coherence": "Multi-step outputs are logically consistent across nodes",
                "policy_compliance": "Responses follow defined guidelines and safety boundaries",
            },
            extra_tags=[
                t
                for t in [model_info.split(",")[0].strip() if model_info else None]
                if t
            ],
        )

    # ── agent ─────────────────────────────────────────────────────

    def _resolve_agent(
        self, agent_id: str, workflow_id: Optional[str]
    ) -> Dict[str, Any]:
        # Best-effort: return partial context when workflow_id is missing
        if not workflow_id:
            return self._build_response(
                target_type="agent",
                target_id=agent_id,
                display_name=self._resolve_node_name(agent_id) or agent_id,
                purpose=None,
                model_info=None,
                tools=None,
                suggested_judge_criteria={
                    "task_completion": "The agent completes its assigned task correctly",
                    "prompt_adherence": "The agent follows its system prompt instructions faithfully",
                    "response_quality": "The output is accurate, relevant, and well-structured",
                    "coherence": "The agent's reasoning is logically consistent",
                    "policy_compliance": "Responses stay within safety and policy boundaries",
                },
                extra_tags=[],
            )

        with get_db() as db:
            gd = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.workflow_id == workflow_id,
                    GraphDefinition.is_latest.is_(True),
                )
                .first()
            )
        if not gd:
            raise LookupError(f"No graph definition found for workflow {workflow_id}")

        nodes = self._parse_graph_nodes(gd.definition_json)
        node = next(
            (
                n
                for n in nodes
                if n.get("id") == agent_id or n.get("uniq_id") == agent_id
            ),
            None,
        )
        if not node:
            raise LookupError(
                f"Agent node {agent_id} not found in workflow {workflow_id}"
            )

        cfg = self._extract_agent_config(node)
        display_name = self._get_node_display_name(node, agent_id)
        # Prefer the user-authored node description; fall back to truncated system prompt
        node_description = node.get("description") or ""
        purpose = node_description if node_description.strip() else cfg.get("purpose")

        return self._build_response(
            target_type="agent",
            target_id=agent_id,
            display_name=display_name,
            purpose=purpose,
            system_prompt=cfg.get("system_prompt"),
            model_info=cfg.get("model_info"),
            tools=cfg.get("tools") or None,
            suggested_judge_criteria={
                "task_completion": "The agent completes its assigned task correctly",
                "prompt_adherence": "The agent follows its system prompt instructions faithfully",
                "response_quality": "The output is accurate, relevant, and well-structured",
                "coherence": "The agent's reasoning is logically consistent",
                "policy_compliance": "Responses stay within safety and policy boundaries",
            },
            extra_tags=[cfg.get("model_info", "").split("/")[-1]]
            if cfg.get("model_info")
            else [],
        )

    # ── model ─────────────────────────────────────────────────────

    def _resolve_model(self, model_id: str) -> Dict[str, Any]:
        with get_db() as db:
            dep = (
                db.query(ModelDeployment).filter(ModelDeployment.id == model_id).first()
            )

        # Graceful partial context when deployment is not found
        if not dep:
            return self._build_response(
                target_type="model",
                target_id=model_id,
                display_name=model_id,
                purpose=None,
                model_info=None,
                tools=None,
                suggested_judge_criteria={
                    "response_quality": "The model output is accurate, relevant, and well-structured",
                    "coherence": "Reasoning is logically consistent and well-organized",
                    "instruction_following": "The model follows instructions precisely",
                    "safety": "Responses stay within safety and policy boundaries",
                },
                extra_tags=[],
            )

        display_name = dep.display_name or dep.name or model_id
        model_info = (
            f"{dep.provider}/{dep.model_name}"
            if dep.provider and dep.model_name
            else None
        )

        return self._build_response(
            target_type="model",
            target_id=model_id,
            display_name=display_name,
            purpose=dep.description,
            model_info=model_info,
            tools=None,
            suggested_judge_criteria={
                "response_quality": "The model output is accurate, relevant, and well-structured",
                "coherence": "Reasoning is logically consistent and well-organized",
                "instruction_following": "The model follows instructions precisely",
                "safety": "Responses stay within safety and policy boundaries",
            },
            extra_tags=[dep.provider, dep.model_name] if dep.provider else [],
        )

    # ── tool ──────────────────────────────────────────────────────

    def _resolve_tool(self, tool_id: str, workflow_id: Optional[str]) -> Dict[str, Any]:
        # Best-effort: return partial context when workflow_id is missing
        if not workflow_id:
            return self._build_response(
                target_type="tool",
                target_id=tool_id,
                display_name=self._resolve_node_name(tool_id) or tool_id,
                purpose="tool node",
                model_info=None,
                tools=None,
                suggested_judge_criteria={
                    "functional_correctness": "The tool produces the correct output for given inputs",
                    "reliability": "The tool succeeds consistently without unexpected failures",
                    "response_quality": "The output format and content meet expectations",
                },
                extra_tags=[],
            )

        with get_db() as db:
            gd = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.workflow_id == workflow_id,
                    GraphDefinition.is_latest.is_(True),
                )
                .first()
            )
        if not gd:
            raise LookupError(f"No graph definition found for workflow {workflow_id}")

        nodes = self._parse_graph_nodes(gd.definition_json)
        node = next(
            (n for n in nodes if n.get("id") == tool_id or n.get("uniq_id") == tool_id),
            None,
        )
        if not node:
            raise LookupError(
                f"Tool node {tool_id} not found in workflow {workflow_id}"
            )

        display_name = self._get_node_display_name(node, tool_id)
        tool_type = (
            node.get("tool_type")
            or node.get("type", "")
            or node.get("data", {}).get("tool_type")
            or node.get("data", {}).get("type", "unknown")
        )

        return self._build_response(
            target_type="tool",
            target_id=tool_id,
            display_name=display_name,
            purpose=f"{tool_type} tool node",
            model_info=None,
            tools=[tool_type] if tool_type else None,
            suggested_judge_criteria={
                "functional_correctness": "The tool produces the correct output for given inputs",
                "reliability": "The tool succeeds consistently without unexpected failures",
                "response_quality": "The output format and content meet expectations",
            },
            extra_tags=[tool_type] if tool_type else [],
        )

    # ── helpers ────────────────────────────────────────────────────

    @staticmethod
    def _resolve_node_name(node_id: str) -> Optional[str]:
        """Search latest graph definitions for a node and return its display name."""
        try:
            with get_db() as db:
                latest_defs = (
                    db.query(GraphDefinition.definition_json)
                    .filter(GraphDefinition.is_latest.is_(True))
                    .all()
                )
                for (defn_json,) in latest_defs:
                    if not isinstance(defn_json, dict):
                        continue
                    for node in defn_json.get("nodes", []):
                        nid = node.get("uniq_id") or node.get("id")
                        if nid == node_id:
                            return (
                                node.get("name")
                                or node.get("label")
                                or node.get("data", {}).get("label")
                                or node.get("data", {}).get("name")
                                or None
                            )
            return None
        except Exception:
            return None

    @staticmethod
    def _parse_graph_nodes(definition_json: Any) -> List[dict]:
        if not isinstance(definition_json, dict):
            return []
        return definition_json.get("nodes", [])

    @staticmethod
    def _get_node_type(node: dict) -> str:
        """Get node type, checking top-level first (NodeSerializer schema) then data.*."""
        return node.get("type", "") or node.get("data", {}).get("type", "")

    @staticmethod
    def _get_node_display_name(node: dict, fallback: str) -> str:
        """Get display name, checking top-level first (NodeSerializer schema) then data.*."""
        return (
            node.get("name")
            or node.get("label")
            or node.get("data", {}).get("label")
            or node.get("data", {}).get("name")
            or fallback
        )

    @staticmethod
    def _extract_agent_config(node: dict) -> dict:
        # NodeSerializer writes agent_config at top level; fall back to data.* for legacy
        agent_cfg = node.get("agent_config") or node.get("data", {}).get(
            "agent_config", {}
        )
        if not isinstance(agent_cfg, dict):
            agent_cfg = {}
        llm_cfg = agent_cfg.get("llm_config", {})

        system_prompt = agent_cfg.get("system_prompt", "") or ""
        purpose = system_prompt
        if purpose and len(purpose) > 200:
            purpose = purpose[:200] + "..."

        provider = llm_cfg.get("provider", "")
        model_name = llm_cfg.get("model_name", "")
        model_info = (
            f"{provider}/{model_name}"
            if provider and model_name
            else model_name or provider or None
        )

        raw_tools = agent_cfg.get("tools", [])
        tools: List[str] = []
        for t in raw_tools:
            if isinstance(t, dict):
                tools.append(t.get("name", str(t)))
            elif isinstance(t, str):
                tools.append(t)

        return {
            "purpose": purpose or None,
            "system_prompt": system_prompt or None,
            "model_info": model_info,
            "tools": tools,
        }

    @staticmethod
    def _build_response(
        *,
        target_type: str,
        target_id: str,
        display_name: str,
        purpose: Optional[str],
        system_prompt: Optional[str] = None,
        model_info: Optional[str],
        tools: Optional[List[str]],
        suggested_judge_criteria: Dict[str, str],
        extra_tags: List[str],
    ) -> Dict[str, Any]:
        base_tags = [target_type]
        base_tags.extend([t for t in extra_tags if t])
        base_tags.extend(["regression", "happy-path"])
        suggested_tags = list(dict.fromkeys(base_tags))

        parts: List[str] = [f"Target: {display_name} ({target_type})"]
        # Include both description and system prompt when available (agents).
        if purpose:
            parts.append(f"Description: {purpose}")
        if system_prompt:
            parts.append(f"System Prompt:\n{system_prompt}")
        if model_info:
            parts.append(f"Model: {model_info}")
        if tools:
            parts.append(f"Tools: {', '.join(tools)}")
        parts.append(
            "Key behaviors to test: task completion, edge cases, error handling"
        )
        ai_seed_enrichment = "\n".join(parts)

        summary_pieces = [f"{display_name} is a {target_type} target"]
        if purpose:
            summary_pieces[0] += f" — {purpose[:100]}"
        if model_info:
            summary_pieces.append(f"Uses {model_info}.")
        context_summary = " ".join(summary_pieces)

        return {
            "target_type": target_type,
            "target_id": target_id,
            "display_name": display_name,
            "purpose": purpose,
            "input_schema": None,
            "output_schema": None,
            "tools": tools,
            "model_info": model_info,
            "suggested_judge_criteria": suggested_judge_criteria,
            "suggested_tags": suggested_tags,
            "context_summary": context_summary,
            "ai_seed_enrichment": ai_seed_enrichment,
        }
