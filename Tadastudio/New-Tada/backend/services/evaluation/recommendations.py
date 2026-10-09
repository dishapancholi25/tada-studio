"""Recommendation engine for evaluation runs.

Analyses evaluation run results across all scoring pillars, generates
actionable recommendations via LLM, and applies approved changes to
workflow graph definitions through the GraphManager.
"""

import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from backend.models.evaluation import (
    EvaluationRecommendation,
    EvaluationResult,
    EvaluationRun,
)
from backend.models.workflow.configs.llm import LLMConfig
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.llm_models.factory import LLMFactory
from backend.services.model_deployment import ModelDeploymentService

from .llm_dispatch_queue import get_llm_dispatch_queue
from .repositories import (
    EvaluationRecommendationRepository,
    EvaluationResultRepository,
    EvaluationRunRepository,
)

logger = get_logger("evaluation.recommendations")

# Canonical recommendation types per ticket contract
VALID_RECOMMENDATION_TYPES = {
    "model_swap",
    "prompt_edit",
    "param_change",
    "tool_replace",
    "guardrail_adjust",
}

# Risk classification for recommendation types
LOW_RISK_TYPES = {"model_swap", "param_change", "prompt_edit"}
MEDIUM_RISK_TYPES = {"tool_replace"}
HIGH_RISK_TYPES = {"guardrail_adjust"}

# Required keys for expected_impact
EXPECTED_IMPACT_KEYS = {"cost_delta_pct", "quality_delta", "latency_delta_ms"}

# Config-patch allowlist — keys that map to recognised EnhancedNodeData attributes
_AUTO_APPLICABLE_KEYS = {
    "agent_config",
    "tool_config",
    "condition_config",
    "document_search_config",
    "database_query_config",
    "web_search_config",
    "http_request_config",
    "mcp_server_config",
    "subworkflow_config",
    "database_insert_config",
    "email_send_config",
    "email_send_tool_config",
    "file_read_config",
    "file_write_config",
    "checkpoint_config",
    "end_node_config",
    "input_source_config",
    "name",
    "description",
    "prompt_template",
    "delegation_description",
}

# Structural keys that require manual application
_STRUCTURAL_KEYS = {"add_node", "remove_node", "add_edge", "remove_edge"}


class RecommendationEngine:
    """Generates and applies evaluation-based workflow recommendations.

    Uses LLM analysis of evaluation run results to produce actionable
    recommendations with a two-tier confirmation policy based on risk tier.
    """

    def __init__(self):
        self._run_repo = EvaluationRunRepository()
        self._result_repo = EvaluationResultRepository()
        self._rec_repo = EvaluationRecommendationRepository()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_recommendations(self, run_id: str) -> list:
        """Generate recommendations for a completed evaluation run.

        Loads run data and results, calls the LLM for analysis, and
        persists the generated recommendations to the database.

        Args:
            run_id: UUID of the evaluation run.

        Returns:
            List of created recommendation dicts. Returns ``[]`` on any error.
        """
        try:
            # Step 1: Load EvaluationRun as a plain dict snapshot
            run_snapshot = self._load_run_snapshot(run_id)
            if run_snapshot is None:
                logger.warning(
                    "Evaluation run not found for recommendations: %s", run_id
                )
                return []

            workflow_id = run_snapshot.get("workflow_id")

            # Step 2: Load all EvaluationResult rows as plain dict snapshots
            results_snapshot = self._load_results_snapshot(run_id)

            # Step 3: Fetch graph definition — prefer execution-time snapshot
            graph_execution_ids = [
                r["graph_execution_id"]
                for r in results_snapshot
                if r.get("graph_execution_id")
            ]
            graph_definition = None
            if graph_execution_ids:
                graph_definition = self._get_graph_definition_from_snapshot(
                    graph_execution_ids
                )
            # Fallback to latest only if no snapshot available
            if graph_definition is None and workflow_id:
                logger.debug(
                    "No execution-time graph snapshot available for run %s, "
                    "falling back to latest graph definition",
                    run_id,
                )
                graph_definition = self._get_graph_definition(workflow_id)

            # Step 4: Call the recommendation LLM
            raw_recommendations = await self._call_recommendation_llm(
                run_snapshot, results_snapshot, graph_definition
            )

            # Step 5: Persist each recommendation
            created: List[Dict[str, Any]] = []
            for item in raw_recommendations:
                rec_type = item.get("recommendation_type", "unknown")
                rec_data = {
                    "run_id": run_id,
                    "target_node_id": item.get("target_node_id"),
                    "recommendation_type": rec_type,
                    "risk_tier": self._classify_risk_tier(rec_type),
                    "title": item.get("title", "Untitled recommendation"),
                    "rationale": item.get("rationale"),
                    "expected_impact": item.get("expected_impact"),
                    "proposed_change": item.get("proposed_change"),
                    "status": "pending",
                }
                try:
                    rec = self._rec_repo.create(rec_data)
                    created.append(
                        {
                            "id": str(rec.id),
                            "title": rec.title,
                            "recommendation_type": rec.recommendation_type,
                            "risk_tier": rec.risk_tier,
                            "status": rec.status,
                        }
                    )
                except Exception as create_exc:
                    logger.warning(
                        "Failed to persist recommendation for run %s: %s",
                        run_id,
                        create_exc,
                    )

            logger.info("Generated %d recommendations for run %s", len(created), run_id)
            return created

        except Exception:
            logger.warning(
                "Recommendation generation failed for run %s", run_id, exc_info=True
            )
            return []

    async def apply_recommendation(
        self,
        recommendation_id: str,
        user_id: str,
        confirmed: bool = False,
        impact_acknowledged: bool = False,
        proposed_change_override: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Apply a pending recommendation to the workflow graph.

        Enforces a two-tier confirmation policy based on risk tier before
        applying the change via GraphManager.

        Args:
            recommendation_id: UUID of the recommendation.
            user_id: UUID of the user applying the recommendation.
            confirmed: Whether the user has confirmed the action.
            impact_acknowledged: Whether the user has acknowledged the impact.
            proposed_change_override: Optional edited proposed change from the
                user review (e.g. edited prompt). When provided, this replaces
                the stored proposed_change for this application.

        Returns:
            Status dict describing the outcome.
        """
        # Step 1: Load recommendation snapshot
        rec_snapshot = self._load_recommendation_snapshot(recommendation_id)
        if rec_snapshot is None:
            return {"status": "error", "reason": "recommendation_not_found"}

        # Step 2: Guard against re-application
        if rec_snapshot["status"] != "pending":
            return {"status": "error", "reason": "already_applied_or_dismissed"}

        # Step 3: Two-tier policy enforcement
        risk_tier = rec_snapshot["risk_tier"]

        if risk_tier == "low":
            if not confirmed:
                return {"status": "confirmation_required", "risk_tier": "low"}
        elif risk_tier in ("medium", "high"):
            if not confirmed or not impact_acknowledged:
                return {
                    "status": "impact_acknowledgement_required",
                    "risk_tier": risk_tier,
                    "expected_impact": rec_snapshot.get("expected_impact"),
                }

        # Step 4: Execution safety check
        run_snapshot = self._load_run_snapshot(rec_snapshot["run_id"])
        if run_snapshot is None:
            return {"status": "error", "reason": "run_not_found"}

        workflow_id = run_snapshot.get("workflow_id")
        if not workflow_id:
            return {"status": "error", "reason": "no_workflow_associated"}

        if self._is_workflow_executing(workflow_id):
            return {
                "status": "blocked",
                "reason": "workflow_is_executing",
                "workflow_id": workflow_id,
            }

        # Step 5: Patchability check
        proposed_change = (
            proposed_change_override
            if proposed_change_override is not None
            else (rec_snapshot.get("proposed_change") or {})
        )
        if not self._is_auto_applicable(proposed_change):
            return {
                "status": "manual_apply_required",
                "recommendation_type": rec_snapshot["recommendation_type"],
                "proposed_change": proposed_change,
                "guidance": self._get_manual_guidance(
                    rec_snapshot["recommendation_type"]
                ),
            }

        # Step 6: Apply the patch
        target_node_id = rec_snapshot.get("target_node_id")
        if not target_node_id:
            return {
                "status": "manual_apply_required",
                "recommendation_type": rec_snapshot["recommendation_type"],
                "proposed_change": proposed_change,
                "guidance": self._get_manual_guidance(
                    rec_snapshot["recommendation_type"]
                ),
            }

        try:
            patch_result = await self._apply_node_patch(
                workflow_id=workflow_id,
                target_node_id=target_node_id,
                proposed_change=proposed_change,
                user_id=user_id,
            )
        except Exception as exc:
            logger.error(
                "Failed to apply recommendation %s: %s", recommendation_id, exc
            )
            return {"status": "error", "reason": "apply_failed", "detail": str(exc)}

        # Step 7: Mark as applied and store version info
        applied_version = patch_result.get("applied_version")
        applied_graph_definition_id = patch_result.get("applied_graph_definition_id")

        self._rec_repo.update_status(
            recommendation_id,
            "applied",
            applied_by_user_id=user_id,
            applied_version=applied_version,
            applied_graph_definition_id=applied_graph_definition_id,
        )

        return {
            "status": "applied",
            "recommendation_id": recommendation_id,
            "workflow_id": workflow_id,
            "applied_version": applied_version,
            "applied_graph_definition_id": applied_graph_definition_id,
        }

    async def dismiss_recommendation(
        self, recommendation_id: str, user_id: str
    ) -> dict:
        """Dismiss a pending recommendation.

        Args:
            recommendation_id: UUID of the recommendation.
            user_id: UUID of the user dismissing it.

        Returns:
            Status dict describing the outcome.
        """
        rec_snapshot = self._load_recommendation_snapshot(recommendation_id)
        if rec_snapshot is None:
            return {"status": "error", "reason": "recommendation_not_found"}

        if rec_snapshot["status"] != "pending":
            return {"status": "error", "reason": "already_applied_or_dismissed"}

        self._rec_repo.update_status(recommendation_id, "dismissed")

        return {"status": "dismissed", "recommendation_id": recommendation_id}

    def preview_recommendation(
        self, recommendation_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Return a preview of the proposed change versus the current value.

        For prompt_edit recommendations, this returns the current and proposed
        system_prompt so the user can review a diff before applying.

        Args:
            recommendation_id: UUID of the recommendation.
            user_id: UUID of the requesting user.

        Returns:
            Dict with current_value, proposed_value, node_name, etc.
        """
        from dataclasses import asdict

        from backend.services.dependency_injection import get_graph_manager

        rec_snapshot = self._load_recommendation_snapshot(recommendation_id)
        if rec_snapshot is None:
            raise LookupError("Recommendation not found")

        run_snapshot = self._load_run_snapshot(rec_snapshot["run_id"])
        if run_snapshot is None:
            raise LookupError("Run not found")

        workflow_id = run_snapshot.get("workflow_id")
        if not workflow_id:
            raise ValueError("No workflow associated with this run")

        proposed_change = rec_snapshot.get("proposed_change") or {}
        target_node_id = rec_snapshot.get("target_node_id")

        result: Dict[str, Any] = {
            "recommendation_id": recommendation_id,
            "recommendation_type": rec_snapshot["recommendation_type"],
            "target_node_id": target_node_id,
            "proposed_change": proposed_change,
            "current_value": None,
            "proposed_value": None,
            "node_name": None,
            "field": None,
        }

        if not target_node_id:
            return result

        graph_manager = get_graph_manager()
        graph = graph_manager.load_graph_by_workflow_id(workflow_id, username=user_id)
        if graph is None:
            return result

        node = graph.get_node_by_id(target_node_id)
        if node is None:
            return result

        result["node_name"] = node.name or node.id

        # Extract current and proposed values for the primary changed field
        if "agent_config" in proposed_change:
            ac_patch = proposed_change["agent_config"]
            if "system_prompt" in ac_patch:
                result["field"] = "system_prompt"
                result["proposed_value"] = ac_patch["system_prompt"]
                if node.agent_config:
                    result["current_value"] = node.agent_config.system_prompt or ""
            elif "llm_config" in ac_patch and node.agent_config:
                llm_patch = ac_patch["llm_config"]
                # Return the first changed LLM field
                current_llm = (
                    asdict(node.agent_config.llm_config)
                    if node.agent_config.llm_config
                    else {}
                )
                for key in llm_patch:
                    result["field"] = key
                    result["current_value"] = current_llm.get(key)
                    result["proposed_value"] = llm_patch[key]
                    break

        return result

    # ------------------------------------------------------------------
    # Data loading helpers (snapshot ORM objects into plain dicts)
    # ------------------------------------------------------------------

    def _load_run_snapshot(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load an EvaluationRun and return a plain dict snapshot."""
        with get_db() as db:
            run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
            if run is None:
                return None
            return {
                "id": str(run.id),
                "workflow_id": run.workflow_id,
                "target_id": run.target_id,
                "target_type": run.target_type,
                "status": run.status,
                "composite_score": run.composite_score,
                "cost_score": run.cost_score,
                "quality_score": run.quality_score,
                "reliability_score": run.reliability_score,
                "latency_score": run.latency_score,
                "total_cases": run.total_cases,
                "completed_cases": run.completed_cases,
                "failed_cases": run.failed_cases,
                "pillar_weights": run.pillar_weights,
                "judge_model_config": run.judge_model_config,
            }

    def _load_results_snapshot(self, run_id: str) -> List[Dict[str, Any]]:
        """Load all EvaluationResult rows for a run as plain dict snapshots."""
        with get_db() as db:
            results = (
                db.query(EvaluationResult)
                .filter(EvaluationResult.run_id == run_id)
                .order_by(EvaluationResult.created_at)
                .all()
            )
            return [
                {
                    "id": str(r.id),
                    "test_case_id": str(r.test_case_id) if r.test_case_id else None,
                    "graph_execution_id": str(r.graph_execution_id)
                    if r.graph_execution_id
                    else None,
                    "composite_score": r.composite_score,
                    "cost_score": r.cost_score,
                    "quality_score": r.quality_score,
                    "reliability_score": r.reliability_score,
                    "latency_score": r.latency_score,
                    "cost_raw": r.cost_raw,
                    "latency_raw": r.latency_raw,
                    "quality_raw": r.quality_raw,
                    "reliability_raw": r.reliability_raw,
                    "guardrail_signals": r.guardrail_signals,
                    "external_eval_raw": r.external_eval_raw,
                    "trace_reference": r.trace_reference,
                }
                for r in results
            ]

    def _load_recommendation_snapshot(
        self, recommendation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Load an EvaluationRecommendation as a plain dict snapshot."""
        with get_db() as db:
            rec = (
                db.query(EvaluationRecommendation)
                .filter(EvaluationRecommendation.id == recommendation_id)
                .first()
            )
            if rec is None:
                return None
            return {
                "id": str(rec.id),
                "run_id": rec.run_id,
                "target_node_id": rec.target_node_id,
                "recommendation_type": rec.recommendation_type,
                "risk_tier": rec.risk_tier,
                "title": rec.title,
                "rationale": rec.rationale,
                "expected_impact": rec.expected_impact,
                "proposed_change": rec.proposed_change,
                "status": rec.status,
            }

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    @staticmethod
    def _get_default_llm_config() -> LLMConfig:
        """Build an LLMConfig from the default LLM deployment.

        Uses :class:`ModelDeploymentService` to resolve the deployment
        marked as default for model_type ``"llm"`` — the same mechanism
        used by :class:`DatasetGenerationService` for AI test-case
        generation.

        Falls back to a bare ``LLMConfig()`` when no default deployment
        has been configured.
        """
        try:
            default_deployment = ModelDeploymentService().get_default_deployment(
                model_type="llm"
            )
            if default_deployment:
                logger.info(
                    "Using default LLM deployment for recommendations: %s (%s)",
                    default_deployment["name"],
                    default_deployment["provider"],
                )
                return LLMConfig(
                    provider=default_deployment["provider"],
                    model_name=default_deployment["model_name"],
                    model_deployment_id=default_deployment["id"],
                    display_name=default_deployment.get("display_name"),
                )
        except Exception:
            logger.warning(
                "Failed to resolve default LLM deployment; "
                "falling back to LLMConfig defaults",
                exc_info=True,
            )

        return LLMConfig()

    async def _call_recommendation_llm(
        self,
        run_snapshot: Dict[str, Any],
        results_snapshot: List[Dict[str, Any]],
        graph_definition: Optional[Dict[str, Any]],
    ) -> list:
        """Dispatch the recommendation LLM call through the queue.

        Mirrors the ``_call_llm_for_generation`` pattern in
        ``dataset_generation.py``.
        """
        queue = get_llm_dispatch_queue()
        coro = self._invoke_recommendation_llm(
            run_snapshot, results_snapshot, graph_definition
        )
        return await queue.submit(coro)

    async def _invoke_recommendation_llm(
        self,
        run_snapshot: Dict[str, Any],
        results_snapshot: List[Dict[str, Any]],
        graph_definition: Optional[Dict[str, Any]],
    ) -> list:
        """Invoke the LLM and parse the recommendation response.

        Mirrors ``_invoke_llm`` in ``dataset_generation.py``.
        """
        model_config = run_snapshot.get("judge_model_config")
        if model_config:
            llm_config = LLMConfig(**model_config)
        else:
            llm_config = self._get_default_llm_config()

        llm_instance = LLMFactory().create_llm_instance(llm_config)

        messages = [
            SystemMessage(content=self._build_recommendation_system_prompt()),
            HumanMessage(
                content=self._build_recommendation_user_prompt(
                    run_snapshot, results_snapshot, graph_definition
                )
            ),
        ]

        response = await llm_instance.llm.ainvoke(messages)
        return self._parse_recommendations(response.content)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_recommendation_system_prompt() -> str:
        """Return the system prompt for recommendation generation."""
        return (
            "You are an expert AI workflow optimization specialist. "
            "Your task is to analyse evaluation run results across all scoring "
            "pillars (cost, quality, latency, reliability) and produce actionable "
            "recommendations for improving the workflow.\n\n"
            "Each recommendation must target a specific node in the workflow graph "
            "and propose a concrete, machine-readable configuration change.\n\n"
            "When external evaluation diagnostics (e.g. Giskard, Phoenix) or trace "
            "references are provided, reference them in your rationale where relevant.\n\n"
            "Always respond with a JSON array of recommendation objects. "
            "Each object must have the following structure:\n"
            "{\n"
            '  "recommendation_type": "model_swap | prompt_edit | param_change | tool_replace | guardrail_adjust",\n'
            '  "title": "Short descriptive title",\n'
            '  "rationale": "Detailed explanation of why this change is recommended",\n'
            '  "expected_impact": {\n'
            '    "cost_delta_pct": <number or null>,\n'
            '    "quality_delta": <number or null>,\n'
            '    "latency_delta_ms": <number or null>\n'
            "  },\n"
            '  "proposed_change": { <machine-readable config patch dict — see examples below> },\n'
            '  "target_node_id": "<node ID to apply the change to>",\n'
            '  "risk_tier": "low | medium | high"\n'
            "}\n\n"
            "## proposed_change examples\n"
            "The proposed_change dict is applied as a partial patch to the node. "
            "Use the EXACT nested key paths shown below.\n\n"
            "param_change (temperature):\n"
            '  {"agent_config": {"llm_config": {"temperature": 0.3}}}\n\n'
            "param_change (max_tokens):\n"
            '  {"agent_config": {"llm_config": {"max_tokens": 2048}}}\n\n'
            "param_change (top_p):\n"
            '  {"agent_config": {"llm_config": {"top_p": 0.9}}}\n\n'
            "model_swap:\n"
            '  {"agent_config": {"llm_config": {"provider": "azure_openai", "model_name": "gpt-4o-mini"}}}\n\n'
            "prompt_edit:\n"
            '  {"agent_config": {"system_prompt": "You are a helpful assistant..."}}\n\n'
            "## CRITICAL: prompt_edit guidelines\n"
            "For prompt_edit recommendations, you MUST make **minimal, surgical changes** "
            "to the existing system prompt — NOT a complete rewrite. Preserve the original "
            "prompt structure, tone, and content. Only add, remove, or modify the specific "
            "sentences or clauses that address the identified issue.\n"
            "- If the prompt is non-trivial (more than ~2 sentences), copy the ENTIRE "
            "existing prompt and apply targeted additions, removals, or wording changes.\n"
            "- Only rewrite from scratch if the existing prompt is trivially short "
            "(e.g. a single generic sentence like 'You are a helpful assistant').\n"
            "- In the rationale, clearly describe what was added, removed, or changed "
            "and why, so the user can review the diff.\n\n"
            "IMPORTANT: LLM parameters (temperature, max_tokens, top_p, model_name, "
            "provider) MUST be nested under agent_config.llm_config. "
            "Do NOT place them directly under agent_config.\n\n"
            "Return ONLY the JSON array — no markdown fences, no explanations."
        )

    @staticmethod
    def _build_recommendation_user_prompt(
        run_snapshot: Dict[str, Any],
        results_snapshot: List[Dict[str, Any]],
        graph_definition: Optional[Dict[str, Any]],
    ) -> str:
        """Return the user prompt with run data for recommendation generation."""
        parts: List[str] = []

        # Run summary
        parts.append("## Evaluation Run Summary")
        parts.append(f"- Target type: {run_snapshot.get('target_type', 'unknown')}")
        parts.append(f"- Target ID: {run_snapshot.get('target_id', 'unknown')}")
        parts.append(f"- Status: {run_snapshot.get('status', 'unknown')}")
        parts.append(f"- Total cases: {run_snapshot.get('total_cases', 0)}")
        parts.append(f"- Failed cases: {run_snapshot.get('failed_cases', 0)}")
        parts.append(f"- Composite score: {run_snapshot.get('composite_score')}")
        parts.append(f"- Cost score: {run_snapshot.get('cost_score')}")
        parts.append(f"- Quality score: {run_snapshot.get('quality_score')}")
        parts.append(f"- Latency score: {run_snapshot.get('latency_score')}")
        parts.append(f"- Reliability score: {run_snapshot.get('reliability_score')}")

        # Per-result aggregates
        if results_snapshot:
            parts.append("\n## Per-Result Details")
            pillar_scores: Dict[str, List[float]] = {
                "cost": [],
                "quality": [],
                "latency": [],
                "reliability": [],
            }
            quality_raw_samples: List[Any] = []
            guardrail_samples: List[Any] = []
            reliability_raw_samples: List[Any] = []

            for r in results_snapshot:
                for pillar in pillar_scores:
                    val = r.get(f"{pillar}_score")
                    if val is not None:
                        pillar_scores[pillar].append(val)
                if r.get("quality_raw"):
                    quality_raw_samples.append(r["quality_raw"])
                if r.get("guardrail_signals"):
                    guardrail_samples.append(r["guardrail_signals"])
                if r.get("reliability_raw"):
                    reliability_raw_samples.append(r["reliability_raw"])

            for pillar, values in pillar_scores.items():
                if values:
                    avg = sum(values) / len(values)
                    parts.append(
                        f"- Average {pillar} score: {avg:.3f} ({len(values)} samples)"
                    )

            if quality_raw_samples:
                sample_text = json.dumps(quality_raw_samples[:3], default=str)
                parts.append(f"\nQuality raw samples (first 3): {sample_text}")

            if guardrail_samples:
                sample_text = json.dumps(guardrail_samples[:3], default=str)
                parts.append(f"\nGuardrail signal samples (first 3): {sample_text}")

            if reliability_raw_samples:
                sample_text = json.dumps(reliability_raw_samples[:3], default=str)
                parts.append(f"\nReliability raw samples (first 3): {sample_text}")

            # External evaluation diagnostics (e.g. Giskard/Phoenix)
            external_eval_samples: List[Any] = []
            trace_ref_samples: List[Any] = []
            for r in results_snapshot:
                if r.get("external_eval_raw"):
                    external_eval_samples.append(r["external_eval_raw"])
                if r.get("trace_reference"):
                    trace_ref_samples.append(r["trace_reference"])

            if external_eval_samples:
                sample_text = json.dumps(external_eval_samples[:3], default=str)
                parts.append(
                    f"\nExternal evaluation diagnostics (first 3): {sample_text}"
                )

            if trace_ref_samples:
                sample_text = json.dumps(trace_ref_samples[:3], default=str)
                parts.append(f"\nTrace references (first 3): {sample_text}")

        # Graph definition summary (evaluation-time snapshot when available)
        if graph_definition:
            parts.append("\n## Evaluation-time Graph Snapshot")
            parts.append(
                "The following node configurations were captured at evaluation "
                "time. Use these snapshot configs (not the latest workflow "
                "version) when determining target_node_id values and "
                "proposed_change relevance."
            )
            nodes = graph_definition.get("nodes", [])
            for node in nodes:
                node_id = node.get("uniq_id") or node.get("id", "unknown")
                node_name = node.get("name", "unnamed")
                node_type = node.get("type", "unknown")
                node_desc = f"- Node `{node_id}` ({node_name}): type={node_type}"

                # Include LLM config details for agent nodes
                agent_config = node.get("agent_config")
                if agent_config:
                    llm_cfg = agent_config.get("llm_config")
                    if llm_cfg:
                        provider = llm_cfg.get("provider", "")
                        model = llm_cfg.get("model", "")
                        node_desc += f", llm={provider}/{model}"
                        temp = llm_cfg.get("temperature")
                        if temp is not None:
                            node_desc += f", temp={temp}"

                parts.append(node_desc)

                # Include the current system prompt so the LLM can make
                # incremental edits rather than rewriting from scratch
                if agent_config:
                    sys_prompt = agent_config.get("system_prompt")
                    if (
                        sys_prompt
                        and isinstance(sys_prompt, str)
                        and sys_prompt.strip()
                    ):
                        parts.append(
                            f"  Current system_prompt for `{node_id}`:\n"
                            f"  ```\n  {sys_prompt}\n  ```"
                        )

        # Final instruction
        parts.append(
            "\n## Instructions\n"
            "Based on the evaluation results above, generate 1-5 actionable "
            "recommendations targeting the identified weakness pillars. "
            "Each recommendation must use one of these types: "
            "model_swap, prompt_edit, param_change, tool_replace, guardrail_adjust.\n"
            "Ensure target_node_id and proposed_change values reference nodes "
            "and configurations from the evaluation-time graph snapshot above.\n"
            "For prompt_edit: copy the FULL existing system_prompt shown above "
            "and apply only targeted additions, removals, or wording changes. "
            "Do NOT rewrite non-trivial prompts from scratch.\n"
            "Return a JSON array of recommendation objects."
        )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_recommendations(raw: str) -> list:
        """Parse the LLM response into a list of recommendation dicts.

        Handles optional markdown code fences around the JSON payload.
        Validates and normalises each recommendation so that
        ``recommendation_type`` is one of the contract types and
        ``expected_impact`` uses the required keys.

        Raises:
            ValueError: If the response cannot be parsed as a JSON array.
        """
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            first_newline = text.index("\n")
            text = text[first_newline + 1 :]
            if text.endswith("```"):
                text = text[: -len("```")].rstrip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned malformed JSON: {exc}") from exc

        if not isinstance(parsed, list):
            raise ValueError(
                f"Expected a JSON array of recommendations, got {type(parsed).__name__}"
            )

        # Validate and normalise each recommendation
        validated: list = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            # Normalise recommendation_type to contract types
            rec_type = item.get("recommendation_type", "")
            if rec_type not in VALID_RECOMMENDATION_TYPES:
                logger.warning(
                    "Dropping recommendation with non-contract type: %s", rec_type
                )
                continue

            # Normalise expected_impact to required schema
            impact = item.get("expected_impact")
            if isinstance(impact, dict):
                item["expected_impact"] = {
                    "cost_delta_pct": impact.get("cost_delta_pct"),
                    "quality_delta": impact.get("quality_delta"),
                    "latency_delta_ms": impact.get("latency_delta_ms"),
                }
            else:
                item["expected_impact"] = {
                    "cost_delta_pct": None,
                    "quality_delta": None,
                    "latency_delta_ms": None,
                }

            validated.append(item)

        return validated

    # ------------------------------------------------------------------
    # Risk classification
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_risk_tier(recommendation_type: str) -> str:
        """Classify a recommendation type into a risk tier.

        Args:
            recommendation_type: One of model_swap, prompt_edit, param_change,
                tool_replace, guardrail_adjust.

        Returns:
            Risk tier string: "low", "medium", or "high".
        """
        if recommendation_type in LOW_RISK_TYPES:
            return "low"
        if recommendation_type in MEDIUM_RISK_TYPES:
            return "medium"
        if recommendation_type in HIGH_RISK_TYPES:
            return "high"
        return "high"  # default safe

    # ------------------------------------------------------------------
    # Auto-applicability check
    # ------------------------------------------------------------------

    @staticmethod
    def _is_auto_applicable(proposed_change: dict) -> bool:
        """Determine whether a proposed change can be auto-applied.

        Returns ``True`` when the change only contains config-field-level
        patches (keys that map to recognised ``EnhancedNodeData`` config
        attributes). Returns ``False`` for structural changes.

        Args:
            proposed_change: The machine-readable patch dict.

        Returns:
            True if auto-applicable, False if manual intervention needed.
        """
        if not proposed_change:
            return False

        for key in proposed_change:
            if key in _STRUCTURAL_KEYS:
                return False
            if key not in _AUTO_APPLICABLE_KEYS:
                return False

        return True

    @staticmethod
    def _get_manual_guidance(recommendation_type: str) -> str:
        """Return human-readable guidance for manual application.

        Args:
            recommendation_type: The type of recommendation.

        Returns:
            Guidance string.
        """
        guidance_map = {
            "model_swap": (
                "Open the workflow canvas, select the target agent node, "
                "and update the LLM model in the agent configuration panel."
            ),
            "prompt_edit": (
                "Open the workflow canvas, select the target node, "
                "and edit the prompt template in the node properties panel."
            ),
            "param_change": (
                "Open the workflow canvas, select the target node, "
                "and adjust the parameters in the node configuration panel."
            ),
            "tool_replace": (
                "Open the workflow canvas, select the target tool node, "
                "and replace or reconfigure the tool using the node properties panel."
            ),
            "guardrail_adjust": (
                "Open the workflow canvas, select the target node, "
                "and update the guardrail configuration using the node properties panel. "
                "Review the expected impact carefully before making changes."
            ),
        }
        return guidance_map.get(
            recommendation_type,
            "Open the workflow canvas, select the target node, and update "
            "the agent configuration using the node properties panel.",
        )

    # ------------------------------------------------------------------
    # Graph / execution helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_graph_definition_from_snapshot(
        graph_execution_ids: List[str],
    ) -> Optional[Dict[str, Any]]:
        """Load a graph definition snapshot from execution-time records.

        Follows the chain ``EvaluationResult.graph_execution_id`` →
        ``GraphExecution.graph_definition_id`` → ``GraphDefinition.definition_json``
        to retrieve the graph definition that was active at evaluation time
        rather than the latest version.

        When multiple unique graph_execution_ids are provided (rare — happens
        if a run spans different graph versions), the definition from the most
        frequently referenced execution is returned.

        Args:
            graph_execution_ids: Non-empty list of GraphExecution UUIDs.

        Returns:
            Plain dict of the graph definition or None.
        """
        with get_db() as db:
            from backend.models.execution.graph_execution import GraphExecution
            from backend.models.workflows import GraphDefinition

            # Pick the most frequent graph_execution_id
            from collections import Counter

            id_counts = Counter(graph_execution_ids)
            most_common_id = id_counts.most_common(1)[0][0]

            ge = (
                db.query(GraphExecution)
                .filter(GraphExecution.id == most_common_id)
                .first()
            )
            if ge is None or ge.graph_definition_id is None:
                return None

            gd = (
                db.query(GraphDefinition)
                .filter(GraphDefinition.id == ge.graph_definition_id)
                .first()
            )
            if gd is None:
                return None
            return dict(gd.definition_json)

    @staticmethod
    def _get_graph_definition(workflow_id: str) -> Optional[Dict[str, Any]]:
        """Load the latest graph definition for a workflow (fallback only).

        Used only when no graph_execution_id is available on evaluation
        results. Prefer ``_get_graph_definition_from_snapshot`` for
        execution-time accuracy.

        Args:
            workflow_id: The workflow UUID.

        Returns:
            Plain dict of the graph definition or None.
        """
        with get_db() as db:
            from backend.models.workflows import GraphDefinition

            gd = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.workflow_id == workflow_id,
                    GraphDefinition.is_latest == True,  # noqa: E712
                )
                .first()
            )
            if gd is None:
                return None
            return dict(gd.definition_json)

    @staticmethod
    def _is_workflow_executing(workflow_id: str) -> bool:
        """Check if a workflow has any active (non-evaluation) executions.

        Only considers executions created within the last 30 minutes to
        avoid stale "running" records permanently blocking applies.

        Args:
            workflow_id: The workflow UUID.

        Returns:
            True if there is at least one running execution.
        """
        with get_db() as db:
            from datetime import datetime, timedelta, timezone

            from sqlalchemy import and_

            from backend.models.execution.graph_execution import GraphExecution

            stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            row = (
                db.query(GraphExecution)
                .filter(
                    and_(
                        GraphExecution.workflow_id == workflow_id,
                        GraphExecution.status == "running",
                        GraphExecution.evaluation_run_id == None,  # noqa: E711
                        GraphExecution.created_at > stale_cutoff,
                    )
                )
                .first()
            )
            return row is not None

    # LLM parameters that belong under agent_config.llm_config, not agent_config
    _LLM_CONFIG_KEYS = {
        "temperature",
        "max_tokens",
        "top_p",
        "reasoning_effort",
        "provider",
        "model_name",
        "model_type",
        "api_base",
        "api_version",
        "deployment_name",
        "api_key_env_var",
        "base_url_env_var",
        "model_deployment_id",
    }

    @classmethod
    def _normalise_proposed_change(cls, proposed_change: dict) -> dict:
        """Normalise a proposed_change dict so LLM params are correctly nested.

        The LLM sometimes places LLM-level keys (temperature, max_tokens, …)
        at the top level, under ``llm_config``, or directly under
        ``agent_config`` instead of inside ``agent_config.llm_config``.
        This helper moves them to the correct nesting level before the
        patch is applied.
        """
        result = dict(proposed_change)

        # --- Phase 1: top-level LLM params → agent_config.llm_config ---
        top_level_llm = {k: v for k, v in result.items() if k in cls._LLM_CONFIG_KEYS}
        if top_level_llm:
            for k in top_level_llm:
                del result[k]
            ac = result.setdefault("agent_config", {})
            if not isinstance(ac, dict):
                ac = {}
                result["agent_config"] = ac
            llm = ac.setdefault("llm_config", {})
            if not isinstance(llm, dict):
                llm = {}
                ac["llm_config"] = llm
            llm.update(top_level_llm)

        # --- Phase 2: top-level llm_config → agent_config.llm_config ---
        if "llm_config" in result and "agent_config" not in result:
            llm_val = result.pop("llm_config")
            if isinstance(llm_val, dict):
                result["agent_config"] = {"llm_config": llm_val}
        elif "llm_config" in result and "agent_config" in result:
            llm_val = result.pop("llm_config")
            ac = result["agent_config"]
            if isinstance(ac, dict) and isinstance(llm_val, dict):
                existing = ac.get("llm_config", {})
                if not isinstance(existing, dict):
                    existing = {}
                ac["llm_config"] = {**existing, **llm_val}

        # --- Phase 3: agent_config-level LLM params → llm_config ---
        if "agent_config" not in result:
            return result

        ac = result["agent_config"]
        if not isinstance(ac, dict):
            return result

        misplaced = {k: v for k, v in ac.items() if k in cls._LLM_CONFIG_KEYS}
        if not misplaced:
            return result

        corrected_ac = {k: v for k, v in ac.items() if k not in cls._LLM_CONFIG_KEYS}
        existing_llm = corrected_ac.get("llm_config", {})
        if not isinstance(existing_llm, dict):
            existing_llm = {}
        corrected_ac["llm_config"] = {**existing_llm, **misplaced}

        return {**result, "agent_config": corrected_ac}

    async def _apply_node_patch(
        self,
        workflow_id: str,
        target_node_id: str,
        proposed_change: dict,
        user_id: str,
    ) -> dict:
        """Apply a configuration patch to a workflow node via GraphManager.

        Uses the same ``update_node`` + ``save_graph`` path as the
        batch-update API for consistency and proper versioning.

        Args:
            workflow_id: The workflow UUID.
            target_node_id: The node ID to patch.
            proposed_change: Dict of config updates to apply.
            user_id: The user applying the change.

        Returns:
            Dict with patch result details.

        Raises:
            ValueError: If the graph or node cannot be found.
        """
        from dataclasses import asdict

        from backend.services.dependency_injection import get_graph_manager

        graph_manager = get_graph_manager()
        graph = graph_manager.load_graph_by_workflow_id(workflow_id, username=user_id)

        if graph is None:
            raise ValueError(f"Graph not found for workflow {workflow_id}")

        normalised = self._normalise_proposed_change(proposed_change)
        logger.info(
            "Applying node patch: workflow=%s node=%s normalised_change=%s",
            workflow_id,
            target_node_id,
            normalised,
        )

        # Capture before state
        target_node = graph.get_node_by_id(target_node_id)
        if target_node and target_node.agent_config:
            before_llm = (
                asdict(target_node.agent_config.llm_config)
                if target_node.agent_config.llm_config
                else None
            )
            logger.info("BEFORE patch — llm_config: %s", before_llm)

        graph_manager.node_manager.update_node(graph, target_node_id, normalised)

        # Capture after state
        target_node = graph.get_node_by_id(target_node_id)
        if target_node and target_node.agent_config:
            after_llm = (
                asdict(target_node.agent_config.llm_config)
                if target_node.agent_config.llm_config
                else None
            )
            logger.info("AFTER patch — llm_config: %s", after_llm)

        graph_manager.save_graph(graph, username=user_id)

        # Capture the version info from the newly saved graph definition
        applied_version = None
        applied_graph_definition_id = None
        reloaded = graph_manager.load_graph_by_workflow_id(
            workflow_id, username=user_id
        )
        if reloaded:
            applied_graph_definition_id = reloaded.definition_id
            # Look up the version number from the graph definition
            with get_db() as db:
                from backend.models.workflows.graph_definition import GraphDefinition

                gd = (
                    db.query(GraphDefinition)
                    .filter(GraphDefinition.id == reloaded.definition_id)
                    .first()
                )
                if gd:
                    applied_version = gd.version

            reloaded_node = reloaded.get_node_by_id(target_node_id)
            if reloaded_node and reloaded_node.agent_config:
                persisted_llm = (
                    asdict(reloaded_node.agent_config.llm_config)
                    if reloaded_node.agent_config.llm_config
                    else None
                )
                logger.info("PERSISTED (reloaded) — llm_config: %s", persisted_llm)

        logger.info(
            "Recommendation applied: workflow=%s node=%s → v%s (def=%s)",
            workflow_id,
            target_node_id,
            applied_version,
            applied_graph_definition_id,
        )

        return {
            "patched": True,
            "node_id": target_node_id,
            "workflow_id": workflow_id,
            "applied_version": applied_version,
            "applied_graph_definition_id": applied_graph_definition_id,
        }
