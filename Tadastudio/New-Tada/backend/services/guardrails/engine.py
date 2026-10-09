"""Guardrails engine — main orchestrator for all guardrail evaluations.

Provides a unified interface for checking inputs, outputs, tool calls,
token budgets, and behavioral patterns. Handles pipeline-based configuration
resolution via LayeredPolicyResolver.
"""

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from backend.models.workflow.configs.guardrails import (
    GuardrailsConfig,
    ToolCallPolicy,
)
from backend.services.guardrails.evaluators.input import InputGuardrailEvaluator
from backend.services.guardrails.evaluators.output import OutputGuardrailEvaluator
from backend.services.guardrails.evaluators.token_budget import TokenBudgetEvaluator
from backend.services.guardrails.evaluators.tool_call import ToolCallGuardrailEvaluator
from backend.services.guardrails.exceptions import GuardrailViolationError
from backend.services.guardrails.filters.evaluator import CustomFilterEvaluator
from backend.services.guardrails.models import GuardrailResult, Violation

if TYPE_CHECKING:
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

logger = logging.getLogger(__name__)

# Action priority for merging across pipeline stages
_ACTION_PRIORITY = {
    "none": 0,
    "warned": 1,
    "transformed": 2,
    "redacted": 3,
    "blocked": 4,
}


def _normalize_pipeline(
    pipeline: Union[List[GuardrailsConfig], GuardrailsConfig, None],
) -> List[GuardrailsConfig]:
    """Normalise the pipeline argument into a list of configs.

    Accepts a list, a single config (backward compat for T4 callers that
    still pass one config), or None.
    """
    if pipeline is None:
        return []
    if isinstance(pipeline, list):
        return pipeline
    return [pipeline]


@dataclass
class ResolvedGuardrails:
    """Result of unified guardrails resolution.

    Separates agent-level pipeline (for input/output checkpoints) from
    per-tool pipelines (for tool_call/tool_ingress/tool_egress/tool_injection
    checkpoints), so tool-assigned policies only apply to their tool.
    """

    agent_pipeline: List[GuardrailsConfig] = field(default_factory=list)
    tool_pipelines: Dict[str, List[GuardrailsConfig]] = field(default_factory=dict)

    def pipeline_for_tool(self, tool_node_id: Optional[str]) -> List[GuardrailsConfig]:
        """Get pipeline for a specific tool, falling back to agent pipeline."""
        if tool_node_id and tool_node_id in self.tool_pipelines:
            return self.tool_pipelines[tool_node_id]
        return self.agent_pipeline


class GuardrailsEngine:
    """Main guardrails orchestrator.

    Stateless evaluator that delegates to specialized evaluators based
    on the type of check being performed. Resolves guardrail pipelines
    via LayeredPolicyResolver.
    """

    def __init__(
        self,
        llm_factory: Optional["LLMFactory"] = None,
        model_service: Optional["ModelDeploymentService"] = None,
    ):
        self.input_evaluator = InputGuardrailEvaluator(
            llm_factory=llm_factory,
            model_service=model_service,
        )
        self.output_evaluator = OutputGuardrailEvaluator()
        self.tool_call_evaluator = ToolCallGuardrailEvaluator()
        self.token_budget_evaluator = TokenBudgetEvaluator()
        self.custom_filter_evaluator = CustomFilterEvaluator(
            llm_factory=llm_factory,
            model_service=model_service,
        )

    def resolve_unified(
        self,
        *,
        workflow_id: Optional[str] = None,
        node_id: Optional[str] = None,
        model_id: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        inline_config: Optional[GuardrailsConfig] = None,
        agent_guardrails_enabled: bool = True,
    ) -> ResolvedGuardrails:
        """Single resolution entry point for all guardrail config scenarios.

        Returns a :class:`ResolvedGuardrails` containing:
        - ``agent_pipeline``: ordered list of GuardrailsConfig for input/output checkpoints
        - ``tool_pipelines``: per-tool ordered lists of GuardrailsConfig

        Args:
            workflow_id: Workflow ID for scoped policy lookup.
            node_id: Agent node ID for node-level assignments.
            model_id: Model deployment ID for model-level policies.
            tool_names: Tool node IDs for per-tool policy resolution.
            inline_config: Kept in signature for call-site compat; ignored.
                # TODO(T6): remove inline_config arg once _get_guardrails_config() is deleted
            agent_guardrails_enabled: Whether guardrails are enabled at the agent level.
                When False, only compulsory (admin-enforced) policies apply.
        """
        try:
            from backend.services.guardrails.resolver import LayeredPolicyResolver

            if not agent_guardrails_enabled:
                # Only compulsory policies apply when guardrails are disabled
                all_compulsory = LayeredPolicyResolver._get_compulsory_policies()
                compulsory_configs: List[GuardrailsConfig] = []
                for layer in all_compulsory:
                    if layer.get("applies_to") and "agent" not in layer["applies_to"]:
                        continue
                    cfg = GuardrailsConfig.from_dict(layer.get("config", {}))
                    cfg.priority = 0
                    cfg.policy_id = layer.get("policy_id", "")
                    cfg.policy_name = layer.get("policy_name", "")
                    compulsory_configs.append(cfg)
                return ResolvedGuardrails(agent_pipeline=compulsory_configs)

            # Resolve agent-level pipeline
            agent_pipeline = LayeredPolicyResolver.resolve_as_pipeline(
                workflow_id=workflow_id,
                node_id=node_id,
                model_id=model_id,
            )

            # Resolve per-tool pipelines
            tool_pipelines: Dict[str, List[GuardrailsConfig]] = {}
            if tool_names:
                tool_pipelines = LayeredPolicyResolver.resolve_tool_pipelines(
                    tool_names
                )

            return ResolvedGuardrails(
                agent_pipeline=agent_pipeline,
                tool_pipelines=tool_pipelines,
            )

        except Exception as e:
            logger.warning("[GUARDRAILS] Pipeline resolution failed: %s", e)
            return ResolvedGuardrails()

    async def check_input(
        self,
        content: str,
        pipeline: Union[List[GuardrailsConfig], GuardrailsConfig, None],
        guardrails_state: Optional[Dict[str, Any]] = None,
    ) -> GuardrailResult:
        """Check user input against an ordered pipeline of guardrail policies.

        Iterates through each enabled policy in priority order. Content flows
        from one policy to the next (sanitized output becomes the next input).

        Args:
            content: User input text.
            pipeline: Ordered list of configs, a single config (compat), or None.
            guardrails_state: Optional mutable dict for cross-phase state
                (e.g. vault_id for PII deanonymization in output phase).

        Returns:
            GuardrailResult with accumulated violations.

        Raises:
            GuardrailViolationError: When an ``enforce`` policy blocks.
        """
        # Legacy single-config compat: return blocked result instead of raising
        # so existing callers can continue their reporting flow until T4 migration.
        single_config_compat = isinstance(pipeline, GuardrailsConfig)
        configs = _normalize_pipeline(pipeline)
        if not configs:
            return GuardrailResult(passed=True)

        current_content = content
        all_violations: List[Violation] = []
        final_action = "none"

        for cfg in configs:
            if not cfg.enabled or cfg.enforcement_mode == "disabled":
                continue

            # Per-policy state bucket
            policy_state: Dict[str, Any] = {}
            if guardrails_state is not None:
                policy_state = guardrails_state.setdefault("policies", {}).setdefault(
                    cfg.policy_id or "default", {}
                )

            result = await self.input_evaluator.evaluate(current_content, cfg)

            # Stamp policy attribution on violations
            for v in result.violations:
                v.policy_id = cfg.policy_id
                v.policy_name = cfg.policy_name
                v.enforcement_mode = cfg.enforcement_mode

            # Custom ingress filters
            if cfg.custom_filters:
                effective_content = result.sanitized_content or current_content
                filter_result = await self.custom_filter_evaluator.evaluate(
                    effective_content, cfg.custom_filters, "ingress"
                )
                for v in filter_result.violations:
                    v.policy_id = cfg.policy_id
                    v.policy_name = cfg.policy_name
                    v.enforcement_mode = cfg.enforcement_mode
                result = result.merge(filter_result)

            # Vault / state threading
            if result.vault_id and guardrails_state is not None:
                policy_state["vault_id"] = result.vault_id
                policy_state["vault_secret"] = result.vault_secret
                guardrails_state["vault_id"] = result.vault_id
                guardrails_state["vault_secret"] = result.vault_secret

            # Enforcement
            if not result.passed and cfg.enforcement_mode == "enforce":
                all_violations.extend(result.violations)
                if single_config_compat:
                    return GuardrailResult(
                        passed=False,
                        violations=all_violations,
                        action_taken="blocked",
                        sanitized_content=result.sanitized_content,
                    )
                raise GuardrailViolationError(
                    f"Guardrail violation (input) policy={cfg.policy_name or cfg.policy_id}: "
                    + (
                        result.violations[0].message
                        if result.violations
                        else "Policy violation"
                    ),
                    violations=all_violations,
                )

            if not result.passed and cfg.enforcement_mode == "audit":
                logger.warning(
                    "[GUARDRAILS-AUDIT] Input violations (not enforced, policy=%s): %s",
                    cfg.policy_id,
                    [v.to_dict() for v in result.violations],
                )
                result.passed = True
                result.action_taken = "warned"

            # Accumulate
            all_violations.extend(result.violations)
            if _ACTION_PRIORITY.get(result.action_taken, 0) > _ACTION_PRIORITY.get(
                final_action, 0
            ):
                final_action = result.action_taken

            # Chain content
            if result.sanitized_content is not None:
                current_content = result.sanitized_content

        return GuardrailResult(
            passed=True,
            violations=all_violations,
            action_taken=final_action,
            sanitized_content=current_content if current_content != content else None,
        )

    async def check_output(
        self,
        content: str,
        pipeline: Union[List[GuardrailsConfig], GuardrailsConfig, None],
        guardrails_state: Optional[Dict[str, Any]] = None,
        prompt: Optional[str] = None,
    ) -> GuardrailResult:
        """Check agent output against an ordered pipeline of guardrail policies.

        Iterates through each enabled policy in priority order. Content flows
        from one policy to the next (sanitized output becomes the next input).

        Args:
            content: Agent output text.
            pipeline: Ordered list of configs, a single config (compat), or None.
            guardrails_state: Optional mutable dict for cross-phase state
                (e.g. vault_id for PII deanonymization).
            prompt: Original user prompt (for output relevance checks).

        Returns:
            GuardrailResult with accumulated violations.

        Raises:
            GuardrailViolationError: When an ``enforce`` policy blocks.
        """
        # Legacy single-config compat: return blocked result instead of raising
        # so existing callers can continue their reporting flow until T4 migration.
        single_config_compat = isinstance(pipeline, GuardrailsConfig)
        configs = _normalize_pipeline(pipeline)
        if not configs:
            return GuardrailResult(passed=True)

        current_content = content
        all_violations: List[Violation] = []
        final_action = "none"

        for cfg in configs:
            if not cfg.enabled or cfg.enforcement_mode == "disabled":
                continue

            # Per-policy state bucket
            policy_state: Dict[str, Any] = {}
            if guardrails_state is not None:
                policy_state = guardrails_state.setdefault("policies", {}).setdefault(
                    cfg.policy_id or "default", {}
                )

            # Read vault credentials — prefer per-policy state, fall back to top-level
            vault_id = policy_state.get("vault_id") or (
                guardrails_state.get("vault_id") if guardrails_state else None
            )
            vault_secret = policy_state.get("vault_secret") or (
                guardrails_state.get("vault_secret") if guardrails_state else None
            )

            result = await self.output_evaluator.evaluate(
                current_content,
                cfg,
                vault_id=vault_id,
                vault_secret=vault_secret,
                prompt=prompt,
            )

            # Stamp policy attribution on violations
            for v in result.violations:
                v.policy_id = cfg.policy_id
                v.policy_name = cfg.policy_name
                v.enforcement_mode = cfg.enforcement_mode

            # Custom egress filters
            if cfg.custom_filters:
                effective_content = result.sanitized_content or current_content
                filter_result = await self.custom_filter_evaluator.evaluate(
                    effective_content, cfg.custom_filters, "egress"
                )
                for v in filter_result.violations:
                    v.policy_id = cfg.policy_id
                    v.policy_name = cfg.policy_name
                    v.enforcement_mode = cfg.enforcement_mode
                result = result.merge(filter_result)

            # Vault / state threading
            if result.vault_id and guardrails_state is not None:
                policy_state["vault_id"] = result.vault_id
                policy_state["vault_secret"] = result.vault_secret
                guardrails_state["vault_id"] = result.vault_id
                guardrails_state["vault_secret"] = result.vault_secret

            # Enforcement
            if not result.passed and cfg.enforcement_mode == "enforce":
                all_violations.extend(result.violations)
                if single_config_compat:
                    return GuardrailResult(
                        passed=False,
                        violations=all_violations,
                        action_taken="blocked",
                        sanitized_content=result.sanitized_content,
                    )
                raise GuardrailViolationError(
                    f"Guardrail violation (output) policy={cfg.policy_name or cfg.policy_id}: "
                    + (
                        result.violations[0].message
                        if result.violations
                        else "Policy violation"
                    ),
                    violations=all_violations,
                )

            if not result.passed and cfg.enforcement_mode == "audit":
                logger.warning(
                    "[GUARDRAILS-AUDIT] Output violations (not enforced, policy=%s): %s",
                    cfg.policy_id,
                    [v.to_dict() for v in result.violations],
                )
                result.passed = True
                result.action_taken = "warned"

            # Accumulate
            all_violations.extend(result.violations)
            if _ACTION_PRIORITY.get(result.action_taken, 0) > _ACTION_PRIORITY.get(
                final_action, 0
            ):
                final_action = result.action_taken

            # Chain content
            if result.sanitized_content is not None:
                current_content = result.sanitized_content

        return GuardrailResult(
            passed=True,
            violations=all_violations,
            action_taken=final_action,
            sanitized_content=current_content if current_content != content else None,
        )

    def check_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        pipeline: Union[List[GuardrailsConfig], GuardrailsConfig, None],
        tool_call_count: int = 0,
        tool_node_type: Optional[str] = None,
    ) -> GuardrailResult:
        """Check a tool call against an ordered pipeline of guardrail policies.

        Validates tool arguments against each policy's tool call policy.

        Args:
            tool_name: Name of the tool being called.
            tool_args: Arguments passed to the tool.
            pipeline: Ordered list of configs, a single config (compat), or None.
            tool_call_count: Current cumulative tool call count.
            tool_node_type: Optional node type for precise routing.

        Returns:
            GuardrailResult with accumulated violations.

        Raises:
            GuardrailViolationError: When an ``enforce`` policy blocks.
        """
        # Legacy single-config compat: return blocked result instead of raising
        # so existing callers can continue their reporting flow until T4 migration.
        single_config_compat = isinstance(pipeline, GuardrailsConfig)
        configs = _normalize_pipeline(pipeline)
        if not configs:
            return GuardrailResult(passed=True)

        all_violations: List[Violation] = []
        final_action = "none"

        for cfg in configs:
            if not cfg.enabled or cfg.enforcement_mode == "disabled":
                continue

            policy = cfg.tool_call_policy or ToolCallPolicy()

            result = self.tool_call_evaluator.evaluate(
                tool_name, tool_args, policy, tool_call_count, tool_node_type
            )

            # Stamp policy attribution
            for v in result.violations:
                v.policy_id = cfg.policy_id
                v.policy_name = cfg.policy_name
                v.enforcement_mode = cfg.enforcement_mode

            # Enforcement
            if not result.passed and cfg.enforcement_mode == "enforce":
                all_violations.extend(result.violations)
                if single_config_compat:
                    return GuardrailResult(
                        passed=False,
                        violations=all_violations,
                        action_taken="blocked",
                    )
                raise GuardrailViolationError(
                    f"Guardrail violation (tool_call) policy={cfg.policy_name or cfg.policy_id}: "
                    + (
                        result.violations[0].message
                        if result.violations
                        else "Policy violation"
                    ),
                    violations=all_violations,
                )

            if not result.passed and cfg.enforcement_mode == "audit":
                logger.warning(
                    "[GUARDRAILS-AUDIT] Tool call violations (not enforced, policy=%s): tool=%s, violations=%s",
                    cfg.policy_id,
                    tool_name,
                    [v.to_dict() for v in result.violations],
                )
                result.passed = True
                result.action_taken = "warned"

            # Accumulate
            all_violations.extend(result.violations)
            if _ACTION_PRIORITY.get(result.action_taken, 0) > _ACTION_PRIORITY.get(
                final_action, 0
            ):
                final_action = result.action_taken

        return GuardrailResult(
            passed=True,
            violations=all_violations,
            action_taken=final_action,
        )

    def check_token_budget(
        self,
        current_usage: Dict[str, Any],
        pipeline: Union[List[GuardrailsConfig], GuardrailsConfig, None],
    ) -> GuardrailResult:
        """Check token usage against an ordered pipeline of guardrail policies.

        Args:
            current_usage: Dictionary with cumulative token counts.
            pipeline: Ordered list of configs, a single config (compat), or None.

        Returns:
            GuardrailResult with accumulated violations.

        Raises:
            GuardrailViolationError: When an ``enforce`` policy blocks.
        """
        # Legacy single-config compat: return blocked result instead of raising
        # so existing callers can continue their reporting flow until T4 migration.
        single_config_compat = isinstance(pipeline, GuardrailsConfig)
        configs = _normalize_pipeline(pipeline)
        if not configs:
            return GuardrailResult(passed=True)

        all_violations: List[Violation] = []
        final_action = "none"

        for cfg in configs:
            if not cfg.enabled or cfg.enforcement_mode == "disabled":
                continue

            if not cfg.token_budget:
                continue

            result = self.token_budget_evaluator.evaluate(
                current_usage, cfg.token_budget
            )

            # Stamp policy attribution
            for v in result.violations:
                v.policy_id = cfg.policy_id
                v.policy_name = cfg.policy_name
                v.enforcement_mode = cfg.enforcement_mode

            # Enforcement
            if not result.passed and cfg.enforcement_mode == "enforce":
                all_violations.extend(result.violations)
                if single_config_compat:
                    return GuardrailResult(
                        passed=False,
                        violations=all_violations,
                        action_taken="blocked",
                    )
                raise GuardrailViolationError(
                    f"Guardrail violation (token_budget) policy={cfg.policy_name or cfg.policy_id}: "
                    + (
                        result.violations[0].message
                        if result.violations
                        else "Policy violation"
                    ),
                    violations=all_violations,
                )

            if not result.passed and cfg.enforcement_mode == "audit":
                logger.warning(
                    "[GUARDRAILS-AUDIT] Token budget violations (not enforced, policy=%s): %s",
                    cfg.policy_id,
                    [v.to_dict() for v in result.violations],
                )
                result.passed = True
                result.action_taken = "warned"

            # Accumulate
            all_violations.extend(result.violations)
            if _ACTION_PRIORITY.get(result.action_taken, 0) > _ACTION_PRIORITY.get(
                final_action, 0
            ):
                final_action = result.action_taken

        return GuardrailResult(
            passed=True,
            violations=all_violations,
            action_taken=final_action,
        )
