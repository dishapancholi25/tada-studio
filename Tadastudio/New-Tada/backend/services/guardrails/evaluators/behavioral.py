"""Behavioral guardrail evaluator — thin orchestrator.

Routes evaluation to the appropriate backend:
1. LLM Guard input scanners (``input_scanners`` module) — fast, offline,
   ML-based detection for toxicity, PII, secrets, prompt injection, and
   jailbreak. This is the primary, always-on gate for adversarial input.
2. LLM-as-judge (``llm_judge`` module) — context-aware adversarial
   detection; an OPT-IN second opinion that runs only when a policy sets
   ``judge_llm_config``. Never the sole detector.
"""

import logging
from typing import TYPE_CHECKING, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import TAG_NOSTREAM

from backend.models.workflow.configs.guardrails import GuardrailsConfig
from backend.services.guardrails.evaluators.input_scanners import (
    classify_with_input_scanners,
)
from backend.services.guardrails.evaluators.llm_judge import (
    JUDGE_SYSTEM_PROMPT,
    build_classification_prompt,
    build_judge_llm,
    content_filter_violations,
    format_judge_error,
    parse_judge_response,
)
from backend.services.guardrails.models import GuardrailResult, Violation

if TYPE_CHECKING:
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

logger = logging.getLogger(__name__)

__all__ = [
    "BehavioralGuardrailEvaluator",
]


class BehavioralGuardrailEvaluator:
    """Evaluates input content for behavioral safety violations.

    Delegates to LLM Guard input scanners or an LLM-as-judge depending
    on which detection flags are enabled in the configuration.
    """

    def __init__(
        self,
        llm_factory: Optional["LLMFactory"] = None,
        model_service: Optional["ModelDeploymentService"] = None,
    ):
        self.llm_factory = llm_factory
        self.model_service = model_service

    async def evaluate(
        self,
        content: str,
        config: GuardrailsConfig,
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> GuardrailResult:
        """Check content for behavioral violations.

        Runs the offline LLM Guard scanners whenever any scanner (including
        prompt injection / jailbreak) is enabled — this is the primary gate.
        The LLM-as-judge runs only as an opt-in second opinion when the policy
        sets ``judge_llm_config``.

        Args:
            content: The input content to evaluate
            config: Behavioral guardrails configuration
            vault_id: Optional vault session id for PII anonymization

        Returns:
            GuardrailResult with any violations found
        """
        if not content:
            return GuardrailResult(passed=True)

        violations: List[Violation] = []
        sanitized_content: Optional[str] = None

        # Check input length (synchronous, no model needed)
        if len(content) > config.max_input_length:
            violations.append(
                Violation(
                    category="behavioral",
                    rule_name="max_input_length",
                    severity="block",
                    message=f"Input exceeds maximum length ({len(content)} > {config.max_input_length})",
                    details={
                        "length": len(content),
                        "max_length": config.max_input_length,
                    },
                )
            )

        # Determine which detection paths to use.
        has_non_adversarial_scanners = (
            (config.detect_toxicity and config.detect_toxicity != "off")
            or (config.anonymize_pii and config.anonymize_pii != "off")
            or (config.detect_secrets and config.detect_secrets != "off")
            or (config.detect_gibberish and config.detect_gibberish != "off")
            or (config.ban_code and config.ban_code != "off")
            or bool(config.ban_topics)
            or bool(config.allowed_languages)
            or config.max_input_tokens is not None
        )
        wants_adversarial_detection = (
            (config.detect_prompt_injection and config.detect_prompt_injection != "off")
            or (config.detect_jailbreak_attempts and config.detect_jailbreak_attempts != "off")
        )

        # --- Scanner path (offline ML — the PRIMARY, always-on gate) ---
        # Run the LLM Guard ML scanners whenever ANY scanner is enabled,
        # including prompt_injection / jailbreak. They run offline (no network,
        # no provider content filter), so adversarial detection is a hard gate
        # that never depends on a reachable or uncensored judge LLM.
        returned_vault_id: Optional[str] = None
        returned_vault_secret: Optional[str] = None
        if has_non_adversarial_scanners or wants_adversarial_detection:
            try:
                (
                    scanner_violations,
                    scanner_sanitized,
                    returned_vault_id,
                    returned_vault_secret,
                ) = await classify_with_input_scanners(
                    content, config, vault_id, vault_secret
                )
                violations.extend(scanner_violations)
                if scanner_sanitized is not None:
                    sanitized_content = scanner_sanitized
            except Exception as e:
                logger.warning(
                    f"[GUARDRAILS] LLM Guard input scanner failed: {e}",
                    exc_info=True,
                )

        # --- LLM-as-judge (OPTIONAL second opinion — opt-in via judge_llm_config) ---
        # The offline ML scanners above are the reliable gate for prompt
        # injection / jailbreak. The judge runs ONLY when a policy explicitly
        # configures one, as an additional context-aware check — never as the
        # default detector. This avoids a judge round-trip (and provider
        # content-filter noise) on every adversarial policy.
        if wants_adversarial_detection and config.judge_llm_config:
            logger.debug("[GUARDRAILS] Running opt-in LLM-as-judge second opinion")

            if not self.llm_factory or not self.model_service:
                logger.warning(
                    "[GUARDRAILS] Judge configured but LLM factory/model service "
                    "unavailable; skipping judge (ML scanner remains the gate)"
                )
                return self._build_result(
                    violations,
                    sanitized_content=sanitized_content,
                    vault_id=returned_vault_id,
                    vault_secret=returned_vault_secret,
                )

            try:
                llm = await build_judge_llm(
                    self.llm_factory, self.model_service, config.judge_llm_config
                )
                prompt = build_classification_prompt(content, config)
                messages = [
                    SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
                response = await llm.ainvoke(messages, config={"tags": [TAG_NOSTREAM]})
                judge_violations = parse_judge_response(response.content, config)
                violations.extend(judge_violations)
            except Exception as e:
                logger.error(f"[GUARDRAILS] Judge LLM call failed: {e}", exc_info=True)
                # A provider content-filter rejection of the judge request IS a
                # positive adversarial detection → fail CLOSED with the mapped
                # category/severity. Otherwise it's a genuine outage, and since
                # the offline ML scanner above is the hard gate we degrade to a
                # non-blocking warning rather than failing the whole request.
                cf_violations = content_filter_violations(e, config)
                if cf_violations:
                    violations.extend(cf_violations)
                else:
                    violations.append(
                        Violation(
                            category="behavioral",
                            rule_name="judge_error",
                            severity="warn",
                            message=format_judge_error(e),
                            details={"error": str(e)},
                        )
                    )
                return self._build_result(
                    violations,
                    sanitized_content=sanitized_content,
                    vault_id=returned_vault_id,
                    vault_secret=returned_vault_secret,
                )

        return self._build_result(
            violations,
            sanitized_content=sanitized_content,
            vault_id=returned_vault_id,
            vault_secret=returned_vault_secret,
        )

    @staticmethod
    def _build_result(
        violations: List[Violation],
        sanitized_content: Optional[str] = None,
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
    ) -> GuardrailResult:
        """Build a GuardrailResult from a list of violations."""
        if any(v.severity == "block" for v in violations):
            return GuardrailResult(
                passed=False,
                violations=violations,
                action_taken="blocked",
                sanitized_content=sanitized_content,
                vault_id=vault_id,
                vault_secret=vault_secret,
            )
        if violations:
            return GuardrailResult(
                passed=True,
                violations=violations,
                action_taken="warned",
                sanitized_content=sanitized_content,
                vault_id=vault_id,
                vault_secret=vault_secret,
            )
        return GuardrailResult(
            passed=True,
            sanitized_content=sanitized_content,
            vault_id=vault_id,
            vault_secret=vault_secret,
        )
