"""Composite scoring service for evaluation runs.

Computes pillar scores (cost, quality, reliability, latency), applies
guardrail penalties, and returns a result dict that the orchestrator
persists via the result repository.
"""

import dataclasses
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from backend.services.config import get_logger

logger = get_logger("evaluation.scoring")

MAX_COST_THRESHOLD = float(os.getenv("EVAL_MAX_COST_THRESHOLD", "1.0"))
MAX_LATENCY_THRESHOLD = float(os.getenv("EVAL_MAX_LATENCY_THRESHOLD", "30.0"))
# Per-node latency budget: each additional node adds this many seconds to the threshold
PER_NODE_LATENCY_BUDGET = float(os.getenv("EVAL_PER_NODE_LATENCY_BUDGET", "8.0"))
# Minimum latency threshold regardless of node count
MIN_LATENCY_THRESHOLD = float(os.getenv("EVAL_MIN_LATENCY_THRESHOLD", "10.0"))


@dataclasses.dataclass
class ExternalEvaluationResults:
    """Pre-computed evaluation data from all providers, available for scoring."""

    builtin_judge: Optional[Dict[str, Any]] = None
    phoenix_judge: Optional[Dict[str, Any]] = None
    phoenix_supplementary: Optional[Dict[str, Any]] = None


class CompositeScorer:
    """Scores a single test-case execution across four pillars."""

    def __init__(self) -> None:
        from .judge import EvaluationJudge

        self._judge = EvaluationJudge()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def score_test_case(self, run_snapshot: dict, test_case: dict) -> dict:
        """Score one test-case execution.

        The orchestrator calls this method, then appends ``run_id``,
        ``test_case_id``, and ``graph_execution_id`` to the returned dict
        before persisting.

        Args:
            run_snapshot: Snapshot of the EvaluationRun (dict).
            test_case: The test-case dict (includes ``expected_output``,
                ``judge_criteria``, etc.).

        Returns:
            Dict with composite + pillar scores, raw data, guardrail
            signals, and optional external evaluation results.
        """
        from backend.models import GraphExecution, NodeExecution
        from backend.services.database import get_db

        # Resolve workflow/agent description for judge context
        context_description = _resolve_target_description(run_snapshot)

        run_id = run_snapshot["id"]
        test_case_id = test_case.get("id", "")

        # ----- Step 1: Resolve GraphExecution & load NodeExecutions -----
        # Use deterministic matching via websocket_execution_id pattern
        # (format: eval_{run_id}_{test_case_id}_{hex}) to avoid race
        # conditions when multiple test cases score concurrently.
        actual_output: Optional[str] = None
        node_executions: List[Dict[str, Any]] = []
        target_type: str = run_snapshot.get("target_type", "workflow")
        resolved_graph_execution_id: Optional[int] = None

        ws_id_prefix = f"eval_{run_id}_{test_case_id}_"

        with get_db() as db:
            # Primary path: deterministic match by websocket_execution_id
            graph_execution = (
                db.query(GraphExecution)
                .filter(
                    GraphExecution.evaluation_run_id == run_id,
                    GraphExecution.websocket_execution_id.like(f"{ws_id_prefix}%"),
                )
                .order_by(GraphExecution.created_at.desc())
                .first()
            )

            if graph_execution is None:
                # Guarded fallback: no deterministic match found — warn and
                # skip rather than risk binding the wrong execution.
                logger.warning(
                    "No GraphExecution matched deterministic pattern '%s' for "
                    "run_id=%s, test_case_id=%s; scoring will proceed without "
                    "execution telemetry",
                    ws_id_prefix,
                    run_id,
                    test_case_id,
                )

            judge_output_policy = run_snapshot.get("judge_output_policy") or {}

            if graph_execution is not None:
                resolved_graph_execution_id = graph_execution.id
                if graph_execution.output_data:
                    actual_output = _extract_judge_output(
                        graph_execution.output_data, judge_output_policy
                    )

                # Snapshot NodeExecution rows into plain dicts
                ne_rows = (
                    db.query(NodeExecution)
                    .filter(NodeExecution.graph_execution_id == graph_execution.id)
                    .all()
                )
                for ne in ne_rows:
                    node_executions.append(
                        {
                            "status": ne.status,
                            "node_type": ne.node_type,
                            "node_name": ne.node_name,
                            "total_cost": ne.total_cost or 0.0,
                            "input_tokens": ne.input_tokens or 0,
                            "output_tokens": ne.output_tokens or 0,
                            "duration_seconds": ne.duration_seconds or 0.0,
                            "time_to_first_token": ne.time_to_first_token,
                            "tokens_per_second": ne.tokens_per_second,
                            "node_metadata": ne.node_metadata or {},
                            "message_structure": ne.message_structure or {},
                            "input_data": ne.input_data,
                            "output_data": ne.output_data,
                            "retry_count": getattr(ne, "retry_count", 0),
                            "error_message": ne.error_message,
                        }
                    )
            else:
                logger.warning(
                    "No GraphExecution found for run_id=%s, test_case_id=%s",
                    run_id,
                    test_case_id,
                )

        # ----- Step 2: Compute pillar scores -----
        cost_score, cost_raw = self._compute_cost_score(node_executions)
        reliability_score, reliability_raw = self._compute_reliability_score(
            node_executions
        )
        latency_score, latency_raw = self._compute_latency_score(node_executions)

        # Normalise expected_output to str (backward compat for old dict values)
        raw_expected = test_case.get("expected_output")
        if isinstance(raw_expected, dict):
            expected_output = json.dumps(raw_expected)
        elif raw_expected:
            expected_output = str(raw_expected)
        else:
            expected_output = None

        # ----- Step 2b: Run all evaluations upfront -----
        eval_results = await self._run_evaluations(
            actual_output=actual_output,
            expected_output=expected_output,
            judge_criteria=test_case.get("judge_criteria"),
            judge_model_config=run_snapshot.get("judge_model_config"),
            max_output_chars=judge_output_policy.get("max_output_chars"),
            context_description=context_description,
            node_executions=node_executions,
            target_type=target_type,
            run_snapshot=run_snapshot,
        )

        # ----- Step 2c: Select quality score from configured provider -----
        quality_score, quality_raw = self._select_quality_score(
            eval_results, run_snapshot
        )

        # ----- Step 3: Guardrail signals and penalty -----
        guardrail_signals = self._extract_guardrail_signals(
            node_executions, graph_execution_id=resolved_graph_execution_id
        )
        quality_score = max(0.0, quality_score - guardrail_signals["penalty"])

        # ----- Step 4: Weighted composite -----
        default_weights = {
            "cost": 0.25,
            "quality": 0.25,
            "reliability": 0.25,
            "latency": 0.25,
        }
        weights = run_snapshot.get("pillar_weights") or default_weights
        composite_score = (
            weights.get("cost", 0.25) * cost_score
            + weights.get("quality", 0.25) * quality_score
            + weights.get("reliability", 0.25) * reliability_score
            + weights.get("latency", 0.25) * latency_score
        )

        # ----- Step 5: Diagnostic sub-metrics -----
        diagnostics = self._compute_diagnostics(
            target_type=target_type,
            node_executions=node_executions,
            cost_score=cost_score,
            quality_score=quality_score,
            reliability_score=reliability_score,
            latency_score=latency_score,
        )
        cost_raw["diagnostics"] = diagnostics.get("cost", {})
        quality_diag = diagnostics.get("quality", {})
        phoenix_supplementary = eval_results.phoenix_supplementary
        if phoenix_supplementary and phoenix_supplementary.get("status") == "ok":
            quality_diag["phoenix"] = phoenix_supplementary
        quality_raw["diagnostics"] = quality_diag
        reliability_raw["diagnostics"] = diagnostics.get("reliability", {})
        latency_raw["diagnostics"] = diagnostics.get("latency", {})

        # ----- Step 6: Giskard integration (optional, non-fatal) -----
        external_eval_raw: Optional[Dict[str, Any]] = None
        giskard_config = (run_snapshot.get("external_integration_config") or {}).get(
            "giskard", {}
        )
        if giskard_config.get("enabled") and target_type in ("agent", "model"):
            try:
                from .giskard_adapter import GiskardEvaluationAdapter

                adapter = GiskardEvaluationAdapter()
                external_eval_raw = await adapter.scan(
                    target_id=run_snapshot.get("target_id"),
                    target_type=target_type,
                    actual_output=actual_output,
                    config=giskard_config,
                )
            except Exception as e:
                logger.warning("Giskard integration failed (non-fatal): %s", e)
                external_eval_raw = {"status": "error", "error": str(e), "findings": []}

        # ----- Step 7: Return result dict -----
        return {
            "composite_score": round(composite_score, 2),
            "cost_score": round(cost_score, 2),
            "quality_score": round(quality_score, 2),
            "reliability_score": round(reliability_score, 2),
            "latency_score": round(latency_score, 2),
            "cost_raw": cost_raw,
            "latency_raw": latency_raw,
            "quality_raw": quality_raw,
            "reliability_raw": reliability_raw,
            "guardrail_signals": guardrail_signals,
            "external_eval_raw": external_eval_raw,
        }

    # ------------------------------------------------------------------
    # Pillar score computations
    # ------------------------------------------------------------------

    def _compute_cost_score(
        self, node_executions: List[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        """Compute cost score based on total cost across node executions.

        Returns:
            Tuple of (score 0-100, raw cost data dict).
        """
        if not node_executions:
            return 100.0, {"total_cost": 0, "input_tokens": 0, "output_tokens": 0}

        total_cost = sum(ne["total_cost"] for ne in node_executions)
        input_tokens = sum(ne["input_tokens"] for ne in node_executions)
        output_tokens = sum(ne["output_tokens"] for ne in node_executions)

        score = max(0.0, 100.0 * (1 - total_cost / MAX_COST_THRESHOLD))

        return score, {
            "total_cost": total_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }

    def _compute_reliability_score(
        self, node_executions: List[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        """Compute reliability score based on node success rate.

        Returns:
            Tuple of (score 0-100, raw reliability data dict).
        """
        if not node_executions:
            return 100.0, {
                "status": "no_nodes",
                "success_rate": 1.0,
                "successful_nodes": 0,
                "total_nodes": 0,
                "retry_count": 0,
            }

        total = len(node_executions)
        successful = sum(1 for ne in node_executions if ne["status"] == "completed")
        success_rate = successful / total

        score = max(0.0, success_rate * 100)

        return score, {
            "status": "completed" if successful == total else "partial",
            "success_rate": success_rate,
            "successful_nodes": successful,
            "total_nodes": total,
            "retry_count": 0,
        }

    def _compute_latency_score(
        self, node_executions: List[Dict[str, Any]]
    ) -> Tuple[float, Dict[str, Any]]:
        """Compute latency score based on total duration, scaled by node count.

        The threshold adapts to workflow complexity: more nodes get a larger
        time budget.  The effective threshold is::

            max(MIN_LATENCY_THRESHOLD, node_count * PER_NODE_LATENCY_BUDGET)

        capped at MAX_LATENCY_THRESHOLD.

        Returns:
            Tuple of (score 0-100, raw latency data dict).
        """
        if not node_executions:
            return 100.0, {
                "duration_seconds": 0.0,
                "ttft_ms": None,
                "tokens_per_second": None,
            }

        total_duration = sum(ne["duration_seconds"] for ne in node_executions)
        node_count = len(node_executions)

        ttft_values = [
            ne["time_to_first_token"]
            for ne in node_executions
            if ne["time_to_first_token"] is not None
        ]
        tps_values = [
            ne["tokens_per_second"]
            for ne in node_executions
            if ne["tokens_per_second"] is not None
        ]

        avg_ttft = (sum(ttft_values) / len(ttft_values)) if ttft_values else None
        avg_tps = (sum(tps_values) / len(tps_values)) if tps_values else None

        # Scale threshold by node count: each node gets PER_NODE_LATENCY_BUDGET seconds
        effective_threshold = min(
            MAX_LATENCY_THRESHOLD,
            max(MIN_LATENCY_THRESHOLD, node_count * PER_NODE_LATENCY_BUDGET),
        )

        score = max(0.0, 100.0 * (1 - total_duration / effective_threshold))

        return score, {
            "duration_seconds": total_duration,
            "ttft_ms": avg_ttft,
            "tokens_per_second": avg_tps,
            "node_count": node_count,
            "effective_threshold": effective_threshold,
        }

    async def _run_evaluations(
        self,
        actual_output: Optional[str],
        expected_output: Optional[str],
        judge_criteria: Optional[Dict[str, Any]],
        judge_model_config: Optional[Dict[str, Any]],
        max_output_chars: Optional[int],
        context_description: Optional[str],
        node_executions: List[Dict[str, Any]],
        target_type: str,
        run_snapshot: dict,
    ) -> ExternalEvaluationResults:
        """Run all evaluation providers upfront before scoring.

        Collects results from the built-in judge and any enabled external
        evaluators (Phoenix, etc.) so that the scoring phase can simply
        select from pre-computed data based on the provider toggle.
        """
        results = ExternalEvaluationResults()

        ext_config = run_snapshot.get("external_integration_config") or {}
        quality_judge_provider = ext_config.get("quality_judge_provider", "builtin")

        # --- Built-in judge (only when selected as provider) ---
        if quality_judge_provider == "builtin" and actual_output is not None:
            try:
                judge_result = await self._judge.judge(
                    actual_output=actual_output,
                    expected_output=expected_output,
                    judge_criteria=judge_criteria,
                    context_description=context_description,
                    judge_model_config=judge_model_config,
                    max_output_chars=max_output_chars,
                )
                results.builtin_judge = {
                    "judge_score": judge_result.quality_score,
                    "reasoning": judge_result.reasoning,
                    "criteria_scores": judge_result.criteria_scores,
                }
            except Exception as e:
                error_msg = str(e) or f"{type(e).__name__} (no message)"
                logger.warning("Built-in judge evaluation failed: %s", error_msg)
                results.builtin_judge = {
                    "judge_score": 50,
                    "reasoning": f"Judge failed: {error_msg}",
                    "criteria_scores": {},
                }

        # --- Phoenix evaluations (if enabled or selected as provider) ---

        try:
            from backend.services.phoenix.config import resolve_phoenix_config
            from backend.services.phoenix.evaluators import PhoenixEvaluatorBridge

            effective_phoenix_config = resolve_phoenix_config(
                override=ext_config.get("phoenix")
            )

            # When Phoenix is the selected quality provider, force-enable
            # Phoenix and its LLM judge regardless of per-run toggle.
            if quality_judge_provider == "phoenix":
                effective_phoenix_config = dataclasses.replace(
                    effective_phoenix_config, enabled=True, eval_llm_judge_enabled=True
                )

            if effective_phoenix_config.enabled:
                phoenix_result = PhoenixEvaluatorBridge.run_supplementary_evals(
                    actual_output=actual_output,
                    context=None,
                    target_type=target_type,
                    node_executions=node_executions,
                    phoenix_config=effective_phoenix_config,
                    judge_model_config=judge_model_config,
                    expected_output=expected_output,
                    judge_criteria=judge_criteria,
                    context_description=context_description,
                )
                results.phoenix_supplementary = phoenix_result

                # Extract Phoenix LLM judge result if it ran
                llm_judge = (phoenix_result.get("evaluations") or {}).get("llm_judge")
                if llm_judge and llm_judge.get("status") == "ok":
                    results.phoenix_judge = {
                        "judge_score": llm_judge.get("quality_score_raw", 50.0),
                        "reasoning": llm_judge.get("explanation", ""),
                        "criteria_scores": llm_judge.get("criteria_scores", {}),
                    }

                    # When Phoenix judge is the primary provider, remove it
                    # from supplementary evaluations so it isn't duplicated
                    # in the diagnostics panel.
                    if quality_judge_provider == "phoenix":
                        evals = phoenix_result.get("evaluations")
                        if isinstance(evals, dict):
                            evals.pop("llm_judge", None)
        except Exception as phoenix_exc:
            logger.warning("Phoenix evaluations failed (non-fatal): %s", phoenix_exc)

        return results

    def _select_quality_score(
        self,
        eval_results: ExternalEvaluationResults,
        run_snapshot: dict,
    ) -> Tuple[float, Dict[str, Any]]:
        """Select quality score from the configured provider.

        Falls back to the built-in judge when the selected provider is
        unavailable.  Applies Phoenix supplementary penalties regardless
        of which provider is selected.
        """
        ext_config = run_snapshot.get("external_integration_config") or {}
        provider = ext_config.get("quality_judge_provider", "builtin")

        no_output_result: Dict[str, Any] = {
            "judge_score": 0,
            "reasoning": "No output to evaluate",
            "criteria_scores": {},
            "provider": "builtin",
        }

        # No built-in result means no actual_output was available
        if eval_results.builtin_judge is None and eval_results.phoenix_judge is None:
            return 0.0, no_output_result

        if provider == "phoenix" and eval_results.phoenix_judge:
            selected = {**eval_results.phoenix_judge, "provider": "phoenix"}
        elif provider == "phoenix":
            logger.warning(
                "Phoenix judge requested but unavailable; falling back to builtin"
            )
            selected = {
                **(eval_results.builtin_judge or no_output_result),
                "provider": "builtin",
            }
            selected["fallback_reason"] = "phoenix_unavailable"
        else:
            selected = {
                **(eval_results.builtin_judge or no_output_result),
                "provider": "builtin",
            }

        score = float(selected.get("judge_score", 0))

        # Apply Phoenix supplementary quality penalty (e.g. hallucination)
        phoenix_sup = eval_results.phoenix_supplementary
        if phoenix_sup and phoenix_sup.get("quality_penalty", 0) > 0:
            score = max(0.0, score - phoenix_sup["quality_penalty"])

        return score, selected

    # ------------------------------------------------------------------
    # Guardrail extraction
    # ------------------------------------------------------------------

    def _extract_guardrail_signals(
        self,
        node_executions: List[Dict[str, Any]],
        graph_execution_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Extract guardrail violations from node metadata and the violations table.

        Checks both ``node_metadata.guardrails.violations`` (inline) and the
        ``guardrail_violations`` table (content filter + policy-based violations
        persisted by ViolationPersistenceService).

        Returns:
            Dict with ``signals`` list, ``penalty`` total, and
            ``total_violations`` count.
        """
        severity_penalty_map = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 2,
            "block": 10,
            "warn": 5,
            "info": 1,
        }

        signals: List[Dict[str, Any]] = []
        total_penalty = 0.0

        # Source 1: inline violations from node_metadata
        for ne in node_executions:
            violations = (
                ne.get("node_metadata", {}).get("guardrails", {}).get("violations", [])
            )
            for violation in violations:
                severity = violation.get("severity", "low")
                penalty = severity_penalty_map.get(severity, 2)
                total_penalty += penalty
                signals.append(
                    {
                        "type": violation.get("type", "unknown"),
                        "severity": severity,
                        "message": violation.get("message", ""),
                        "penalty": penalty,
                    }
                )

        # Source 2: violations persisted to the guardrail_violation_events table
        # (content filter violations, policy-based violations from engine)
        if graph_execution_id is not None:
            try:
                from backend.models.guardrails.violation_event import GuardrailViolationEvent
                from backend.services.database import get_db

                with get_db() as db:
                    db_violations = (
                        db.query(GuardrailViolationEvent)
                        .filter(
                            GuardrailViolationEvent.graph_execution_id == str(graph_execution_id)
                        )
                        .all()
                    )
                    for v in db_violations:
                        severity = v.severity or "warn"
                        penalty = severity_penalty_map.get(severity, 2)
                        total_penalty += penalty
                        signals.append(
                            {
                                "type": v.category or "unknown",
                                "severity": severity,
                                "message": v.message or "",
                                "penalty": penalty,
                                "rule_name": v.rule_name,
                                "action_taken": v.action_taken,
                                "agent_node_name": v.agent_node_name,
                                "policy_name": v.policy_name,
                            }
                        )
            except Exception as e:
                logger.warning("Failed to query guardrail_violation_events table: %s", e)

        return {
            "signals": signals,
            "penalty": total_penalty,
            "total_violations": len(signals),
        }

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def _compute_diagnostics(
        self,
        target_type: str,
        node_executions: List[Dict[str, Any]],
        cost_score: float,
        quality_score: float,
        reliability_score: float,
        latency_score: float,
    ) -> Dict[str, Dict[str, Any]]:
        """Compute diagnostic sub-metrics from actual execution data.

        Only includes metrics derived from real measurements in
        node_executions — no synthetic echoes of pillar scores.

        Returns:
            Nested dict keyed by pillar name, each containing
            diagnostic metric names and values.
        """
        quality_diag: Dict[str, Any] = {}
        cost_diag: Dict[str, Any] = {}
        reliability_diag: Dict[str, Any] = {}
        latency_diag: Dict[str, Any] = {}

        if not node_executions:
            return {
                "quality": quality_diag,
                "cost": cost_diag,
                "reliability": reliability_diag,
                "latency": latency_diag,
            }

        # ── Measured cost diagnostics ──
        total_input = sum(ne.get("input_tokens", 0) for ne in node_executions)
        total_output = sum(ne.get("output_tokens", 0) for ne in node_executions)
        total_tokens = total_input + total_output
        if total_tokens > 0:
            cost_diag["input_token_ratio"] = round(total_input / total_tokens * 100, 1)
            cost_diag["output_token_ratio"] = round(
                total_output / total_tokens * 100, 1
            )

        per_node_costs = [ne.get("total_cost", 0) for ne in node_executions]
        if len(per_node_costs) > 1 and max(per_node_costs) > 0:
            cost_diag["max_node_cost_share"] = round(
                max(per_node_costs) / sum(per_node_costs) * 100, 1
            )

        # ── Measured reliability diagnostics ──
        statuses = [ne.get("status", "") for ne in node_executions]
        error_count = sum(1 for s in statuses if s in ("failed", "error"))
        if error_count > 0:
            reliability_diag["error_count"] = error_count

        retry_count = sum(ne.get("retry_count", 0) for ne in node_executions)
        if retry_count > 0:
            reliability_diag["total_retries"] = retry_count

        # ── Measured latency diagnostics ──
        durations = [ne.get("duration_seconds", 0) for ne in node_executions]
        if len(durations) > 1:
            slowest = max(durations)
            total_dur = sum(durations)
            if total_dur > 0:
                latency_diag["slowest_node_share"] = round(slowest / total_dur * 100, 1)
            latency_diag["node_count"] = len(durations)
            latency_diag["slowest_node_seconds"] = round(slowest, 3)

        ttft_values = [
            ne.get("time_to_first_token")
            for ne in node_executions
            if ne.get("time_to_first_token") is not None
        ]
        if ttft_values:
            latency_diag["max_ttft_ms"] = round(max(ttft_values), 1)

        # ── Measured quality diagnostics (agent tool usage) ──
        if target_type == "agent":
            tool_call_count = sum(
                len(ne.get("node_metadata", {}).get("tool_calls", []))
                for ne in node_executions
            )
            if tool_call_count > 0:
                quality_diag["tool_calls"] = tool_call_count

        return {
            "quality": quality_diag,
            "cost": cost_diag,
            "reliability": reliability_diag,
            "latency": latency_diag,
        }

    # ------------------------------------------------------------------
    # Run-level aggregation
    # ------------------------------------------------------------------

    def aggregate_run_scores(self, run_id: str) -> Dict[str, Any]:
        """Aggregate per-case results into run-level scores and summary stats.

        Computes average pillar scores, summary statistics, and external
        evaluation summary from persisted ``EvaluationResult`` rows, then
        updates the ``EvaluationRun`` record.

        Args:
            run_id: UUID of the evaluation run.

        Returns:
            Dict with the aggregated fields that were written to the run.
        """
        from .repositories import EvaluationResultRepository, EvaluationRunRepository

        result_repo = EvaluationResultRepository()
        run_repo = EvaluationRunRepository()

        results = result_repo.list_by_run(run_id)
        if not results:
            logger.warning("No results to aggregate for run %s", run_id)
            return {}

        # ---- Pillar score averages ----
        pillar_fields = [
            "composite_score",
            "cost_score",
            "quality_score",
            "reliability_score",
            "latency_score",
        ]
        averages: Dict[str, Optional[float]] = {}
        for pf in pillar_fields:
            values = [getattr(r, pf) for r in results if getattr(r, pf) is not None]
            averages[pf] = round(sum(values) / len(values), 2) if values else None

        # ---- Summary stats ----
        total = len(results)
        scored = sum(
            1
            for r in results
            if r.composite_score is not None and float(r.composite_score) > 0
        )
        failed = total - scored

        all_composites: List[float] = [
            float(r.composite_score) for r in results if r.composite_score is not None
        ]
        summary_stats: Dict[str, Any] = {
            "total_cases": total,
            "scored_cases": scored,
            "failed_cases": failed,
            "min_composite": round(min(all_composites), 2) if all_composites else None,
            "max_composite": round(max(all_composites), 2) if all_composites else None,
            "median_composite": round(
                sorted(all_composites)[len(all_composites) // 2], 2
            )
            if all_composites
            else None,
            "guardrail_violation_total": sum(
                len((getattr(r, "guardrail_signals", None) or {}).get("signals", []))
                for r in results
            ),
        }

        # ---- External eval summary ----
        external_summaries = [
            r.external_eval_raw
            for r in results
            if r.external_eval_raw is not None
            and r.external_eval_raw.get("status") != "error"
        ]
        external_eval_summary: Optional[Dict[str, Any]] = None
        if external_summaries:
            total_findings = sum(len(s.get("findings", [])) for s in external_summaries)
            external_eval_summary = {
                "cases_with_external_eval": len(external_summaries),
                "total_findings": total_findings,
            }

        # ---- Persist to EvaluationRun ----
        update_payload: Dict[str, Any] = {}
        for pf in pillar_fields:
            if averages.get(pf) is not None:
                update_payload[pf] = averages[pf]
        update_payload["summary_stats"] = summary_stats
        if external_eval_summary is not None:
            update_payload["external_eval_summary"] = external_eval_summary

        if update_payload:
            run_repo.update_scores(run_id, update_payload)
            logger.info(
                "Aggregated run-level scores for run %s: %s", run_id, update_payload
            )

        return update_payload


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _extract_judge_output(
    output_data: Any, policy: Optional[Dict[str, Any]] = None
) -> str:
    """Extract the most relevant output text from a GraphExecution's output_data.

    The stored output_data is typically a dict containing *all* node outputs
    plus a ``final_output`` key.  Sending the entire dict to the LLM judge
    can exceed context limits, so we extract only the meaningful part.

    The extraction strategy is controlled by ``policy``:

    - ``{"strategy": "final_node"}`` (default) — use the pre-extracted
      ``final_output`` or fall back to the last node output.
    - ``{"strategy": "specific_node", "node_id": "<id>"}`` — use the
      output of the named node.
    - ``{"strategy": "all_nodes"}`` — concatenate all node outputs
      (still subject to the judge's truncation guardrail).
    """
    if isinstance(output_data, str):
        return output_data

    if not isinstance(output_data, dict):
        return str(output_data)

    strategy = (policy or {}).get("strategy", "final_node")
    node_outputs = output_data.get("node_outputs")

    # --- specific_node: use a named node's output ---
    if strategy == "specific_node":
        target_node_id = (policy or {}).get("node_id", "")
        if isinstance(node_outputs, dict) and target_node_id in node_outputs:
            return _stringify_node_output(node_outputs[target_node_id])
        # Node not found — log and fall through to final_node strategy
        logger.warning(
            "Judge output policy requested node '%s' but it was not found "
            "in node_outputs (keys: %s); falling back to final_node",
            target_node_id,
            list(node_outputs.keys()) if isinstance(node_outputs, dict) else "N/A",
        )

    # --- all_nodes: concatenate every node's output ---
    if strategy == "all_nodes" and isinstance(node_outputs, dict) and node_outputs:
        sections = []
        for node_id, node_out in node_outputs.items():
            sections.append(f"### Node: {node_id}\n{_stringify_node_output(node_out)}")
        return "\n\n".join(sections)

    # --- final_node (default): pre-extracted final output or last node ---
    final_output = output_data.get("final_output")
    if final_output is not None:
        if isinstance(final_output, str):
            return final_output
        return json.dumps(final_output, default=str)

    # Fall back to the last node output (most likely the answer node)
    if isinstance(node_outputs, dict) and node_outputs:
        last_key = list(node_outputs.keys())[-1]
        return _stringify_node_output(node_outputs[last_key])

    # Last resort: stringify the whole dict (judge truncation will cap it)
    return json.dumps(output_data, default=str)


def _stringify_node_output(node_out: Any) -> str:
    """Convert a single node output value to a string for the judge."""
    if isinstance(node_out, str):
        return node_out
    if isinstance(node_out, dict):
        raw = node_out.get("raw") or node_out.get("content") or node_out.get("output")
        if raw is not None:
            return str(raw)
        return json.dumps(node_out, default=str)
    return str(node_out)


def _resolve_target_description(run_snapshot: Dict[str, Any]) -> Optional[str]:
    """Resolve the workflow or agent description for judge context.

    Looks up the Workflow (and optionally GraphDefinition) description
    from the database using the run snapshot's target identifiers.
    Returns None when no description is available.
    """
    workflow_id = run_snapshot.get("workflow_id")
    target_id = run_snapshot.get("target_id", "")
    target_type = run_snapshot.get("target_type", "workflow")

    if not workflow_id and not target_id:
        return None

    try:
        from backend.models.workflows.graph_definition import GraphDefinition
        from backend.models.workflows.workflow import Workflow
        from backend.services.database import get_db

        with get_db() as db:
            # Try workflow description first
            if workflow_id:
                wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
                if wf and wf.description:
                    return str(wf.description)

            # Fall back to graph definition description
            lookup_id = workflow_id or target_id
            gd = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.workflow_id == lookup_id,
                    GraphDefinition.is_latest == True,  # noqa: E712
                )
                .first()
            )
            if gd and gd.description:
                return str(gd.description)

            # If target_id is a graph definition ID directly
            if target_id and target_type == "workflow":
                gd = (
                    db.query(GraphDefinition)
                    .filter(GraphDefinition.id == target_id)
                    .first()
                )
                if gd and gd.description:
                    return str(gd.description)

    except Exception as exc:
        logger.debug("Could not resolve target description for judge context: %s", exc)

    return None
