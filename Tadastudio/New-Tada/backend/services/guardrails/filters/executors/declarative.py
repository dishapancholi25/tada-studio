"""Declarative filter template executor.

Executes predefined filter templates with user-configured parameters.
Templates include PII detection (regex), word count limits (logic),
and LLM-based checks (toxicity, topic guard, language detection).
"""

import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List

from backend.services.guardrails.models import GuardrailResult, Violation

if TYPE_CHECKING:
    from backend.models.workflow.configs.guardrails import CustomFilter
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService

logger = logging.getLogger(__name__)

# PII regex patterns by category and sensitivity
PII_PATTERNS: Dict[str, Dict[str, str]] = {
    "ssn": {
        "low": r"\b\d{3}-\d{2}-\d{4}\b",
        "medium": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        "high": r"\b\d{9}\b|\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
    },
    "credit_card": {
        "low": r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",
        "medium": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "high": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b|\b\d{16}\b",
    },
    "email": {
        "low": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "medium": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "high": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    },
    "phone": {
        "low": r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "medium": r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b",
        "high": r"\b\+?\d[\d\s\-().]{7,}\d\b",
    },
    "ip_address": {
        "low": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "medium": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "high": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    },
}


class DeclarativeFilterExecutor:
    """Execute declarative filter templates with user-configured parameters."""

    def __init__(
        self,
        llm_factory: "LLMFactory | None" = None,
        model_service: "ModelDeploymentService | None" = None,
    ):
        self.llm_factory = llm_factory
        self.model_service = model_service

    async def execute(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Execute a declarative filter template.

        Args:
            filter_def: Custom filter with template_id and template_params
            content: Content to evaluate
            direction: "ingress" or "egress"

        Returns:
            GuardrailResult
        """
        # Legacy templates superseded by first-class LLM Guard scanners.
        # Kept for backward compat with existing policies; log deprecation.
        _DEPRECATED_TEMPLATES = {
            "pii_detector": "Use the built-in 'PII Detection' (anonymize_pii) LLM Guard scanner instead.",
            "toxicity_check": "Use the built-in 'Toxicity Detection' (detect_toxicity) LLM Guard scanner instead.",
        }

        handlers = {
            "pii_detector": self._handle_pii_detection,
            "toxicity_check": self._handle_toxicity_check,
            "topic_guard": self._handle_topic_guard,
            "language_detector": self._handle_language_detection,
            "word_count_limit": self._handle_word_count_limit,
        }

        if filter_def.template_id in _DEPRECATED_TEMPLATES:
            logger.warning(
                "[GUARDRAILS] Deprecated template '%s' in filter '%s'. %s",
                filter_def.template_id,
                filter_def.name,
                _DEPRECATED_TEMPLATES[filter_def.template_id],
            )

        handler = handlers.get(filter_def.template_id)
        if not handler:
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=f"{filter_def.name}_unknown_template",
                        severity="warn",
                        message=f"Unknown template '{filter_def.template_id}'",
                        details={"filter_id": filter_def.id},
                    )
                ],
                action_taken="warned",
            )

        try:
            return await handler(filter_def, content, direction)
        except Exception as e:
            logger.error(
                f"[GUARDRAILS] Template filter '{filter_def.name}' error: {e}",
                exc_info=True,
            )
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=f"{filter_def.name}_error",
                        severity="warn",
                        message=f"Template filter error: {e}",
                        details={"filter_id": filter_def.id, "error": str(e)},
                    )
                ],
                action_taken="warned",
            )

    async def _handle_pii_detection(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Detect PII using regex patterns."""
        params = filter_def.template_params
        categories: List[str] = params.get("categories", ["email", "phone", "ssn"])
        sensitivity: str = params.get("sensitivity", "medium")

        found_pii: List[Dict[str, Any]] = []
        sanitized = content

        for category in categories:
            patterns = PII_PATTERNS.get(category)
            if not patterns:
                continue
            pattern = patterns.get(sensitivity, patterns.get("medium", ""))
            if not pattern:
                continue

            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                found_pii.append({"category": category, "count": len(matches)})
                if filter_def.action == "transform":
                    sanitized = re.sub(
                        pattern,
                        f"[{category.upper()}_REDACTED]",
                        sanitized,
                        flags=re.IGNORECASE,
                    )

        if not found_pii:
            return GuardrailResult(passed=True)

        pii_summary = ", ".join(f"{p['category']}({p['count']})" for p in found_pii)
        message = filter_def.message or f"PII detected: {pii_summary}"

        if filter_def.action == "transform":
            return GuardrailResult(
                passed=True,
                violations=[
                    Violation(
                        category="custom_filter",
                        rule_name=filter_def.name,
                        severity="warn",
                        message=message,
                        details={"filter_id": filter_def.id, "pii_found": found_pii},
                    )
                ],
                action_taken="transformed",
                sanitized_content=sanitized,
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
                        details={"filter_id": filter_def.id, "pii_found": found_pii},
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
                    details={"filter_id": filter_def.id, "pii_found": found_pii},
                )
            ],
            action_taken="warned",
        )

    async def _handle_word_count_limit(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Check word count against limit."""
        params = filter_def.template_params
        max_words: int = int(params.get("max_words", 500))
        word_count = len(content.split())

        if word_count <= max_words:
            return GuardrailResult(passed=True)

        message = (
            filter_def.message
            or f"Word count {word_count} exceeds limit of {max_words}"
        )

        if filter_def.action == "transform":
            words = content.split()
            truncated = " ".join(words[:max_words]) + "..."
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
                            "word_count": word_count,
                            "max_words": max_words,
                        },
                    )
                ],
                action_taken="transformed",
                sanitized_content=truncated,
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
                            "word_count": word_count,
                            "max_words": max_words,
                        },
                    )
                ],
                action_taken="blocked",
            )

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
                        "word_count": word_count,
                        "max_words": max_words,
                    },
                )
            ],
            action_taken="warned",
        )

    async def _handle_toxicity_check(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Check for toxic content via LLM classification.

        Delegates to the LLM judge executor with a generated toxicity prompt.
        """
        from backend.services.guardrails.filters.executors.llm_judge import (
            LLMJudgeFilterExecutor,
        )

        params = filter_def.template_params
        categories: List[str] = params.get(
            "categories", ["hate", "threat", "profanity"]
        )
        threshold: float = float(params.get("threshold", 0.5))

        # Build a toxicity-specific policy prompt
        categories_str = ", ".join(categories)
        policy_prompt = (
            f"Check if the content contains toxic or harmful language. "
            f"Categories to check: {categories_str}. "
            f"Flag content that is clearly toxic with confidence above {threshold}."
        )

        # Create a temporary filter def with the generated prompt
        from dataclasses import replace

        judge_filter = replace(
            filter_def,
            judge_prompt=policy_prompt,
            judge_threshold=threshold,
        )

        executor = LLMJudgeFilterExecutor(
            llm_factory=self.llm_factory,
            model_service=self.model_service,
        )
        return await executor.execute(judge_filter, content, direction)

    async def _handle_topic_guard(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Guard topics via LLM classification."""
        from backend.services.guardrails.filters.executors.llm_judge import (
            LLMJudgeFilterExecutor,
        )

        params = filter_def.template_params
        mode: str = params.get("mode", "blocklist")
        topics: List[str] = params.get("topics", [])

        if not topics:
            return GuardrailResult(passed=True)

        topics_str = ", ".join(topics)
        if mode == "blocklist":
            policy_prompt = (
                f"Check if the content discusses any of these forbidden topics: {topics_str}. "
                f"Flag the content if it clearly relates to any of these topics."
            )
        else:
            policy_prompt = (
                f"Check if the content is OFF-TOPIC. The only allowed topics are: {topics_str}. "
                f"Flag the content if it is NOT about any of these allowed topics."
            )

        from dataclasses import replace

        judge_filter = replace(filter_def, judge_prompt=policy_prompt)

        executor = LLMJudgeFilterExecutor(
            llm_factory=self.llm_factory,
            model_service=self.model_service,
        )
        return await executor.execute(judge_filter, content, direction)

    async def _handle_language_detection(
        self,
        filter_def: "CustomFilter",
        content: str,
        direction: str,
    ) -> GuardrailResult:
        """Detect content language via LLM classification."""
        from backend.services.guardrails.filters.executors.llm_judge import (
            LLMJudgeFilterExecutor,
        )

        params = filter_def.template_params
        allowed_languages: List[str] = params.get("allowed_languages", ["en"])

        langs_str = ", ".join(allowed_languages)
        policy_prompt = (
            f"Check if the content is written in one of these allowed languages: {langs_str}. "
            f"Flag the content if it is primarily written in a different language. "
            f"Brief code snippets, URLs, or proper nouns in other languages should NOT be flagged."
        )

        from dataclasses import replace

        judge_filter = replace(filter_def, judge_prompt=policy_prompt)

        executor = LLMJudgeFilterExecutor(
            llm_factory=self.llm_factory,
            model_service=self.model_service,
        )
        return await executor.execute(judge_filter, content, direction)
