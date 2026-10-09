"""LLM-as-judge filter executor for user-defined policy prompts.

Evaluates content against natural language policy descriptions using
an LLM judge. Reuses the proven pattern from BehavioralGuardrailEvaluator.
"""

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.guardrails.models import GuardrailResult, Violation

if TYPE_CHECKING:
    from backend.models.workflow.configs.guardrails import CustomFilter
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

logger = logging.getLogger(__name__)

MAX_JUDGE_INPUT_LENGTH = 10_000

JUDGE_SYSTEM_PROMPT = """You are a content policy evaluator. Given a policy description and content to evaluate, determine if the content violates the policy.

You MUST respond with valid JSON only. No other text, no markdown formatting.

Response format:
{
    "violated": true or false,
    "confidence": 0.0 to 1.0,
    "reasoning": "Brief explanation of your evaluation",
    "suggested_replacement": "Modified content that complies with the policy, or null if not applicable"
}

Guidelines:
- Be conservative: only flag clear violations
- Set confidence based on how certain you are (0.0 = unsure, 1.0 = certain)
- For "suggested_replacement": only provide a replacement if the content can be reasonably modified to comply. Set to null if the content should simply be blocked.
- Evaluate the content objectively against the stated policy"""


class LLMJudgeFilterExecutor:
    """Execute LLM-as-judge evaluation with user-defined policy prompts."""

    def __init__(
        self,
        llm_factory: Optional["LLMFactory"] = None,
        model_service: Optional["ModelDeploymentService"] = None,
    ):
        self.llm_factory = llm_factory
        self.model_service = model_service

    async def _build_judge_llm(self, llm_config: Any) -> Any:
        """Build an LLM instance for judge evaluation."""
        from backend.models.workflow.configs.llm import LLMConfig

        if not self.llm_factory or not self.model_service:
            raise ValueError("LLM factory and model service required for judge filters")

        if isinstance(llm_config, dict):
            llm_config = LLMConfig(**llm_config)

        # Override for efficiency
        llm_config.max_tokens = 500
        llm_config.temperature = 0.0

        enriched_config = self.model_service.enrich_llm_config(llm_config)
        llm_instance = self.llm_factory.create_llm_instance(enriched_config)

        if not llm_instance or not llm_instance.llm:
            raise ValueError("Failed to create judge LLM instance")

        # Disable streaming to prevent leaking into agent output
        llm_instance.llm.streaming = False
        return llm_instance.llm

    def _get_default_llm_config(self) -> Any:
        """Get default LLM configuration from system default deployment.
        
        Returns:
            LLMConfig instance using the default LLM deployment
            
        Raises:
            ValueError: If no default deployment is configured
        """
        from backend.models.workflow.configs.llm import LLMConfig
        
        # Get default deployment for LLM model type
        default_deployment = self.model_service.get_default_deployment(
            model_type="llm", include_credentials=False
        )
        
        if not default_deployment:
            raise ValueError("No default LLM deployment configured in system")
        
        # Build LLMConfig from deployment
        return LLMConfig(
            provider=default_deployment.get("provider"),
            model_name=default_deployment.get("model_name"),
            model_deployment_id=default_deployment.get("id"),
        )

    async def execute(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Evaluate content against the user's policy prompt via LLM judge.

        Args:
            filter_def: The custom filter definition with judge_prompt and config
            content: Content to evaluate
            direction: "ingress" or "egress"

        Returns:
            GuardrailResult with violations if policy is violated
        """
        try:
            from langgraph.constants import TAG_NOSTREAM
        except ImportError:
            TAG_NOSTREAM = "nostream"

        if not filter_def.judge_prompt:
            return GuardrailResult(passed=True)

        # Use default LLM if no config specified
        llm_config = filter_def.judge_llm_config
        if not llm_config:
            logger.info(
                "[GUARDRAILS] No LLM config specified for judge filter '%s', using default deployment",
                filter_def.name,
            )
            try:
                llm_config = self._get_default_llm_config()
            except Exception as e:
                logger.warning(
                    f"[GUARDRAILS] Failed to get default LLM for filter '{filter_def.name}': {e}"
                )
                return GuardrailResult(
                    passed=True,
                    warnings=[f"Judge filter skipped: {e}"],
                )

        if not filter_def.judge_llm_config:
            logger.warning(
                f"[GUARDRAILS] LLM judge filter '{filter_def.name}' has no judge_llm_config, skipping"
            )
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=f"{filter_def.name}_no_config",
                        severity="warn",
                        message=f"Filter '{filter_def.name}' has no judge LLM configured",
                        details={"filter_id": filter_def.id},
                    )
                ],
                action_taken="warned",
            )

        try:
            llm = await self._build_judge_llm(llm_config)

            truncated_content = content[:MAX_JUDGE_INPUT_LENGTH]
            user_prompt = (
                f"Policy to enforce:\n{filter_def.judge_prompt}\n\n"
                f"Content direction: {direction}\n\n"
                f"Content to evaluate:\n---\n{truncated_content}\n---\n\n"
                f"Evaluate whether this content violates the policy. Respond with JSON only."
            )

            messages = [
                SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            response = await llm.ainvoke(messages, config={"tags": [TAG_NOSTREAM]})
            return self._parse_response(response.content, filter_def)

        except Exception as e:
            logger.error(
                f"[GUARDRAILS] LLM judge filter '{filter_def.name}' failed: {e}",
                exc_info=True,
            )
            clean_message = self._format_judge_error(e, filter_def.name)
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=f"{filter_def.name}_error",
                        severity="warn",
                        message=clean_message,
                        details={"filter_id": filter_def.id, "error": str(e)},
                    )
                ],
                action_taken="warned",
            )

    def _parse_response(
        self,
        response_content: str,
        filter_def: "CustomFilter",
    ) -> GuardrailResult:
        """Parse judge LLM JSON response into a GuardrailResult."""
        try:
            content = response_content.strip()

            # Handle markdown code blocks
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                content = content[start:end].strip()

            result = json.loads(content)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"[GUARDRAILS] Failed to parse judge response for '{filter_def.name}': {e}, "
                f"content: {response_content[:200]}"
            )
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=f"{filter_def.name}_parse_error",
                        severity="warn",
                        message=f"Could not parse judge response for filter '{filter_def.name}'",
                        details={
                            "error": str(e),
                            "raw_response": response_content[:500],
                        },
                    )
                ],
                action_taken="warned",
            )

        # Check if violated and confidence exceeds threshold
        violated = result.get("violated", False)
        confidence = float(result.get("confidence", 0.0))

        if not violated or confidence < filter_def.judge_threshold:
            return GuardrailResult(passed=True)

        reasoning = result.get("reasoning", "Policy violation detected")
        message = filter_def.message or reasoning

        # Determine action based on filter config
        if filter_def.action == "transform":
            replacement = result.get("suggested_replacement")
            if replacement and isinstance(replacement, str):
                return GuardrailResult(
                    passed=True,
                    violations=[
                        Violation(
                            category="custom_filter",
                            rule_name=filter_def.name,
                            severity="warn",
                            message=message,
                            details={
                                "filter_id": filter_def.id,
                                "confidence": confidence,
                                "reasoning": reasoning,
                                "action": "transform",
                            },
                        )
                    ],
                    action_taken="transformed",
                    sanitized_content=replacement,
                )
            # No replacement available — fall back to block
            return GuardrailResult(
                passed=False,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=filter_def.name,
                        severity="block",
                        message=f"{message} (no replacement available, blocking)",
                        details={
                            "filter_id": filter_def.id,
                            "confidence": confidence,
                            "reasoning": reasoning,
                        },
                    )
                ],
                action_taken="blocked",
            )

        if filter_def.action == "block":
            return GuardrailResult(
                passed=False,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=filter_def.name,
                        severity="block",
                        message=message,
                        details={
                            "filter_id": filter_def.id,
                            "confidence": confidence,
                            "reasoning": reasoning,
                        },
                    )
                ],
                action_taken="blocked",
            )

        # warn
        return GuardrailResult(
            passed=True,
            violations=[
                Violation(
                    category="custom_filter",
                    rule_name=filter_def.name,
                    severity="warn",
                    message=message,
                    details={
                        "filter_id": filter_def.id,
                        "confidence": confidence,
                        "reasoning": reasoning,
                    },
                )
            ],
            action_taken="warned",
        )

    @staticmethod
    def _format_judge_error(exc: Exception, filter_name: str) -> str:
        """Format judge error message, with Azure content filter extraction."""
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            if body.get("code") == "content_filter":
                inner = body.get("innererror", {})
                filter_result = inner.get("content_filter_result", {})
                triggered = [
                    cat
                    for cat, details in filter_result.items()
                    if isinstance(details, dict)
                    and (details.get("filtered") or details.get("detected"))
                ]
                if triggered:
                    return (
                        f"Judge filter '{filter_name}' blocked by content filter "
                        f"({', '.join(triggered)} detected)"
                    )
                return f"Judge filter '{filter_name}' blocked by content filter"

            msg = body.get("message", "")
            if msg:
                return f"Judge filter '{filter_name}' failed: {msg[:200]}"

        exc_msg = str(exc)
        if exc_msg:
            return f"Judge filter '{filter_name}' failed: {exc_msg[:200]}"
        return f"Judge filter '{filter_name}' failed: {type(exc).__name__}"
