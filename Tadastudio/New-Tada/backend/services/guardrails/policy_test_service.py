"""Policy testing sandbox service.

Evaluates a guardrail policy config against sample content WITHOUT
writing to the guardrail_violations table. Uses the existing
GuardrailsEngine evaluators directly.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PolicyTestService:
    """Evaluates a guardrail policy config against sample content.

    Uses the existing GuardrailsEngine evaluators directly.
    Never writes to guardrail_violations table.
    """

    @staticmethod
    async def test(
        config: Dict[str, Any],
        sample_input: Optional[str] = None,
        sample_output: Optional[str] = None,
        include_behavioral: bool = False,
    ) -> Dict[str, Any]:
        """Evaluate policy config against sample content.

        Args:
            config: Full GuardrailsConfig dict
            sample_input: Optional input text to test
            sample_output: Optional output text to test
            include_behavioral: Whether to trigger LLM judge calls

        Returns:
            Dict with results per check type and total violation count
        """
        from backend.models.workflow.configs.guardrails import GuardrailsConfig
        from backend.services.guardrails import get_guardrails_engine

        guardrails_config = GuardrailsConfig.from_dict(config)
        engine = get_guardrails_engine()
        results: List[Dict[str, Any]] = []
        total_violations = 0
        llm_called = False

        if sample_input:
            try:
                # Run static checks only first (pattern, custom filters without behavioral)
                check_config = GuardrailsConfig(
                    enabled=guardrails_config.enabled,
                    enforcement_mode=guardrails_config.enforcement_mode,
                    pattern_rules=guardrails_config.pattern_rules,
                    tool_call_policy=guardrails_config.tool_call_policy,
                    custom_filters=guardrails_config.custom_filters,
                )
                result = await engine.check_input(sample_input, check_config)
                violations = [v.to_dict() for v in result.violations]
                total_violations += len(violations)
                results.append({
                    "check_type": "input",
                    "passed": result.passed,
                    "violations": violations,
                    "action_taken": result.action_taken or "none",
                    "sanitized_content": result.sanitized_content,
                    "passed_content": result.sanitized_content or sample_input,
                    "llm_judge_called": False,
                })

                # Behavioral check (LLM judge)
                if include_behavioral and guardrails_config.has_behavioral_checks:
                    try:
                        behavioral_config = GuardrailsConfig(
                            enabled=True,
                            enforcement_mode=guardrails_config.enforcement_mode,
                            detect_prompt_injection=guardrails_config.detect_prompt_injection,
                            detect_jailbreak_attempts=guardrails_config.detect_jailbreak_attempts,
                            system_prompt_protection=guardrails_config.system_prompt_protection,
                            max_input_length=guardrails_config.max_input_length,
                            max_output_length=guardrails_config.max_output_length,
                            judge_llm_config=guardrails_config.judge_llm_config,
                            detect_toxicity=guardrails_config.detect_toxicity,
                            anonymize_pii=guardrails_config.anonymize_pii,
                            use_faker=guardrails_config.use_faker,
                            pii_entity_types=guardrails_config.pii_entity_types,
                            detect_secrets=guardrails_config.detect_secrets,
                            ban_topics=guardrails_config.ban_topics,
                            allowed_languages=guardrails_config.allowed_languages,
                            detect_gibberish=guardrails_config.detect_gibberish,
                            ban_code=guardrails_config.ban_code,
                            max_input_tokens=guardrails_config.max_input_tokens,
                            prompt_injection_threshold=guardrails_config.prompt_injection_threshold,
                            jailbreak_threshold=guardrails_config.jailbreak_threshold,
                            toxicity_threshold=guardrails_config.toxicity_threshold,
                        )
                        behavioral_result = await engine.check_input(sample_input, behavioral_config)
                        llm_called = True
                        b_violations = [v.to_dict() for v in behavioral_result.violations]
                        total_violations += len(b_violations)
                        results.append({
                            "check_type": "behavioral",
                            "passed": behavioral_result.passed,
                            "violations": b_violations,
                            "action_taken": behavioral_result.action_taken or "none",
                            "sanitized_content": None,
                            "passed_content": sample_input,
                            "llm_judge_called": True,
                        })
                    except Exception as e:
                        logger.warning("[GUARDRAIL-SANDBOX] Behavioral check failed: %s", e)
                        results.append({
                            "check_type": "behavioral",
                            "passed": True,
                            "violations": [],
                            "action_taken": "none",
                            "sanitized_content": None,
                            "passed_content": sample_input,
                            "llm_judge_called": True,
                            "error": str(e),
                        })

            except Exception as e:
                logger.warning("[GUARDRAIL-SANDBOX] Input check failed: %s", e)
                results.append({
                    "check_type": "input",
                    "passed": True,
                    "violations": [],
                    "action_taken": "none",
                    "sanitized_content": None,
                    "passed_content": sample_input,
                    "llm_judge_called": False,
                    "error": str(e),
                })

        if sample_output:
            try:
                check_config = GuardrailsConfig(
                    enabled=guardrails_config.enabled,
                    enforcement_mode=guardrails_config.enforcement_mode,
                    pattern_rules=guardrails_config.pattern_rules,
                    custom_filters=guardrails_config.custom_filters,
                    max_output_length=guardrails_config.max_output_length,
                    anonymize_pii=guardrails_config.anonymize_pii,
                    output_scanners=guardrails_config.output_scanners,
                )
                result = await engine.check_output(sample_output, check_config)
                violations = [v.to_dict() for v in result.violations]
                total_violations += len(violations)
                results.append({
                    "check_type": "output",
                    "passed": result.passed,
                    "violations": violations,
                    "action_taken": result.action_taken or "none",
                    "sanitized_content": result.sanitized_content,
                    "passed_content": result.sanitized_content or sample_output,
                    "llm_judge_called": False,
                })
            except Exception as e:
                logger.warning("[GUARDRAIL-SANDBOX] Output check failed: %s", e)
                results.append({
                    "check_type": "output",
                    "passed": True,
                    "violations": [],
                    "action_taken": "none",
                    "sanitized_content": None,
                    "passed_content": sample_output,
                    "llm_judge_called": False,
                    "error": str(e),
                })

        cost_warning = None
        if include_behavioral and llm_called:
            cost_warning = "Live LLM call was made for behavioral checks. Standard inference costs apply."

        return {
            "results": results,
            "total_violations": total_violations,
            "execution_cost_warning": cost_warning,
        }
