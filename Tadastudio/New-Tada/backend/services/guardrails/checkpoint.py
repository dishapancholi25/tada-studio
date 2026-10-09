"""Unified guardrail checkpoint — single entry point for all guardrail checks.

Provides GuardrailContext (execution metadata bundle) and GuardrailCheckpoint
(routes to evaluators, reports violations, applies enforcement) so that every
call site in the execution pipeline reduces to a single method call.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from backend.models.workflow.configs.guardrails import GuardrailsConfig
from backend.services.guardrails.engine import _normalize_pipeline
from backend.services.guardrails.exceptions import GuardrailViolationError
from backend.services.guardrails.models import GuardrailResult, Violation
from backend.services.guardrails.violation_persistence import (
    ViolationPersistenceService,
)
from backend.services.streaming.event_emitter import StreamingEventEmitter

logger = logging.getLogger(__name__)


@dataclass
class GuardrailContext:
    """Bundles execution metadata passed to every guardrail check.

    Built once at the start of agent execution and threaded through
    all checkpoint calls, eliminating per-call-site parameter lists.
    """

    execution_id: Optional[str] = None
    db_execution_id: Optional[str] = None
    node_execution_id: Optional[str] = None
    workflow_id: Optional[str] = None
    agent_node_id: Optional[str] = None
    agent_node_name: Optional[str] = None
    user_id: Optional[str] = None
    tool_name: Optional[str] = None


# Checkpoint types that route to check_input
_INPUT_CHECKPOINTS = {"input", "tool_ingress", "tool_injection"}
# Checkpoint types that route to check_output
_OUTPUT_CHECKPOINTS = {"output", "tool_egress"}


class GuardrailCheckpoint:
    """Single entry point for all guardrail checks during execution.

    Routes to the correct evaluator, persists and emits violations,
    and applies enforcement (raise on enforce, warn on audit).

    Usage::

        checkpoint = GuardrailCheckpoint(engine)
        ctx = GuardrailContext(execution_id=..., ...)

        # Input check
        result = await checkpoint.check("user message", config, "input", ctx, state=gs)

        # Tool call validation
        result = await checkpoint.check("", config, "tool_call", ctx,
                                        tool_name="http_request", tool_args={...})

        # Output check
        result = await checkpoint.check(response, config, "output", ctx,
                                        state=gs, prompt=original_msg)
    """

    def __init__(self, engine: Any):
        """
        Args:
            engine: GuardrailsEngine instance (avoids circular import at module level).
        """
        self.engine = engine

    async def check(
        self,
        content: str,
        pipeline: Union[List[GuardrailsConfig], GuardrailsConfig, None],
        checkpoint: str,
        ctx: GuardrailContext,
        *,
        state: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        tool_node_type: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> GuardrailResult:
        """Run a guardrail check, report violations, and apply enforcement.

        Args:
            content: Text to check (user message, tool args JSON, LLM response, etc.)
            pipeline: Ordered list of GuardrailsConfig, a single config (compat), or None.
            checkpoint: Checkpoint type — one of:
                "input", "output", "tool_call", "tool_ingress",
                "tool_egress", "tool_injection", "token_budget",
                "content_filter".
            ctx: Execution context metadata.
            state: Mutable guardrails_state dict (for PII vault cross-phase).
            tool_name: Tool name (for tool_call / tool_ingress / tool_egress).
            tool_args: Tool arguments dict (for tool_call checkpoint).
            tool_node_type: Node type string for tool call routing.
            prompt: Original user prompt (for output relevance checks).

        Returns:
            GuardrailResult — callers should check .sanitized_content for
            transformed text and .passed for block status.

        Raises:
            GuardrailViolationError: In enforce mode when violations block.
        """
        norm_pipeline = _normalize_pipeline(pipeline)
        if not norm_pipeline:
            return GuardrailResult(passed=True)

        # Derive an active config for reporting (first enabled, non-disabled entry)
        active_config: Optional[GuardrailsConfig] = None
        for _cfg in norm_pipeline:
            if _cfg.enabled and _cfg.enforcement_mode != "disabled":
                active_config = _cfg
                break

        # ── Route to correct evaluator (engine handles per-policy iteration) ──
        effective_tool = tool_name or ctx.tool_name
        try:
            result = await self._evaluate(
                content,
                norm_pipeline,
                checkpoint,
                state,
                tool_name,
                tool_args,
                tool_node_type,
                prompt,
            )
        except GuardrailViolationError as exc:
            # Enforce-mode raise from engine — persist and emit before propagating
            blocked_result = GuardrailResult(
                passed=False,
                violations=exc.violations,
                action_taken="blocked",
            )
            if blocked_result.violations:
                self._report_violations(
                    blocked_result, active_config, checkpoint, ctx, effective_tool
                )
            raise

        # ── Report violations (persist + emit) ──────────────────────────
        if result.violations:
            self._report_violations(
                result, active_config, checkpoint, ctx, effective_tool
            )

        return result

    # ── Private helpers ──────────────────────────────────────────────────

    async def _evaluate(
        self,
        content: str,
        pipeline: List[GuardrailsConfig],
        checkpoint: str,
        state: Optional[Dict[str, Any]],
        tool_name: Optional[str],
        tool_args: Optional[Dict[str, Any]],
        tool_node_type: Optional[str],
        prompt: Optional[str],
    ) -> GuardrailResult:
        """Delegate to the appropriate engine method based on checkpoint type."""
        gs = state if state is not None else {}

        if checkpoint == "tool_call":
            return self.engine.check_tool_call(
                tool_name or "",
                tool_args or {},
                pipeline,
                tool_node_type=tool_node_type,
            )

        if checkpoint == "token_budget":
            # content is unused; we pass it as the usage dict via tool_args
            return self.engine.check_token_budget(tool_args or {}, pipeline)

        if checkpoint in _INPUT_CHECKPOINTS:
            return await self.engine.check_input(content, pipeline, guardrails_state=gs)

        if checkpoint in _OUTPUT_CHECKPOINTS:
            return await self.engine.check_output(
                content,
                pipeline,
                guardrails_state=gs,
                prompt=prompt,
            )

        if checkpoint == "content_filter":
            # Content filter violations are pre-built by the caller;
            # this checkpoint just handles reporting (violations passed in result).
            return GuardrailResult(passed=True)

        logger.warning("[GUARDRAIL-CHECKPOINT] Unknown checkpoint type: %s", checkpoint)
        return GuardrailResult(passed=True)

    @staticmethod
    def _report_violations(
        result: GuardrailResult,
        config: Optional[GuardrailsConfig],
        checkpoint: str,
        ctx: GuardrailContext,
        tool_name: Optional[str] = None,
    ) -> None:
        """Persist violations to DB and emit WebSocket events."""
        for v in result.violations:
            violation_db_id = ViolationPersistenceService.persist_violation(
                v,
                category=checkpoint,
                action_taken=result.action_taken,
                policy_id=v.policy_id or (config.policy_id if config else None) or None,
                policy_name=v.policy_name
                or (config.policy_name if config else None)
                or None,
                graph_execution_id=ctx.db_execution_id,
                node_execution_id=ctx.node_execution_id,
                workflow_id=ctx.workflow_id,
                agent_node_id=ctx.agent_node_id,
                agent_node_name=ctx.agent_node_name,
                user_id=ctx.user_id,
                tool_name=tool_name,
            )
            StreamingEventEmitter.emit_guardrail_violation(
                category=checkpoint,
                rule_name=v.rule_name or "unknown",
                message=v.message or "Policy violation",
                severity=v.severity or "block",
                agent_id=ctx.agent_node_id,
                agent_name=ctx.agent_node_name,
                execution_id=ctx.execution_id,
                node_execution_id=ctx.node_execution_id,
                violation_db_id=violation_db_id,
                policy_name=v.policy_name
                or (config.policy_name if config else None)
                or None,
                details=v.details,
                enforcement_mode=v.enforcement_mode or (config.enforcement_mode if config else None),
                tool_name=tool_name,
            )

    @staticmethod
    def report_prebuilt_violations(
        violations: List[Violation],
        config: GuardrailsConfig,
        checkpoint: str,
        ctx: GuardrailContext,
        action_taken: str = "blocked",
        tool_name: Optional[str] = None,
    ) -> List[Optional[str]]:
        """Persist and emit pre-built violations (e.g. provider content filter).

        Returns list of violation DB IDs.
        """
        db_ids: List[Optional[str]] = []
        for v in violations:
            db_id = ViolationPersistenceService.persist_violation(
                v,
                category=checkpoint,
                action_taken=action_taken,
                policy_id=v.policy_id or (config.policy_id if config else None) or None,
                policy_name=v.policy_name
                or (config.policy_name if config else None)
                or None,
                graph_execution_id=ctx.db_execution_id,
                node_execution_id=ctx.node_execution_id,
                workflow_id=ctx.workflow_id,
                agent_node_id=ctx.agent_node_id,
                agent_node_name=ctx.agent_node_name,
                user_id=ctx.user_id,
                tool_name=tool_name,
            )
            StreamingEventEmitter.emit_guardrail_violation(
                category=checkpoint,
                rule_name=v.rule_name or "unknown",
                message=v.message or "Policy violation",
                severity=v.severity or "block",
                agent_id=ctx.agent_node_id,
                agent_name=ctx.agent_node_name,
                execution_id=ctx.execution_id,
                node_execution_id=ctx.node_execution_id,
                violation_db_id=db_id,
                policy_name=v.policy_name
                or (config.policy_name if config else None)
                or None,
                details=v.details,
                enforcement_mode=v.enforcement_mode or (config.enforcement_mode if config else None),
                tool_name=tool_name,
            )
            db_ids.append(db_id)
        return db_ids
