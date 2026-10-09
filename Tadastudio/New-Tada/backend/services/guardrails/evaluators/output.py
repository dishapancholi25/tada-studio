"""Output guardrail evaluator.

Validates agent output before it is returned, applying content
filters, output length checks, and LLM Guard output scanners.

Delegates scanner execution to the active ``ScannerBackend`` (local,
API, or hybrid) via ``backends/__init__.py``.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.models.workflow.configs.guardrails import GuardrailsConfig, OutputScanners
from backend.services.guardrails.backends import get_scanner_backend
from backend.services.guardrails.backends.protocol import ScannerResult
from backend.services.guardrails.models import GuardrailResult, Violation
from backend.services.guardrails.pattern_rules import apply_pattern_rules

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config → scanner dict builder
# ---------------------------------------------------------------------------


def _build_output_scanner_dict(
    config: GuardrailsConfig,
    vault_id: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    """Translate OutputScanners + behavioral flags into a scanner config dict."""
    scanners: Dict[str, Dict[str, Any]] = {}
    output_scanners: Optional[OutputScanners] = config.output_scanners

    if output_scanners:
        if output_scanners.detect_toxicity and output_scanners.detect_toxicity != "off":
            scanners["toxicity"] = {"threshold": output_scanners.toxicity_threshold}
        if output_scanners.detect_refusal and output_scanners.detect_refusal != "off":
            scanners["no_refusal"] = {}
        if (
            output_scanners.detect_sensitive_data
            and output_scanners.detect_sensitive_data != "off"
        ):
            scanners["sensitive"] = {}
        if output_scanners.ban_topics:
            scanners["ban_topics"] = {"topics": output_scanners.ban_topics}
        if output_scanners.allowed_languages:
            scanners["language"] = {
                "valid_languages": output_scanners.allowed_languages
            }
        if output_scanners.check_relevance and output_scanners.check_relevance != "off":
            scanners["relevance"] = {}
        if (
            output_scanners.detect_gibberish
            and output_scanners.detect_gibberish != "off"
        ):
            scanners["gibberish"] = {}
        if output_scanners.ban_competitors:
            scanners["ban_competitors"] = {
                "competitors": output_scanners.ban_competitors
            }
        if output_scanners.detect_bias and output_scanners.detect_bias != "off":
            scanners["bias"] = {}
        if (
            output_scanners.check_factual_consistency
            and output_scanners.check_factual_consistency != "off"
        ):
            scanners["factual_consistency"] = {}

    # Deanonymize only when vault was used on input (anonymize action)
    if vault_id and config.anonymize_pii == "anonymize":
        scanners["deanonymize"] = {}

    return scanners


# ---------------------------------------------------------------------------
# ScannerResult → Violation mapping
# ---------------------------------------------------------------------------

_VIOLATION_MAP: Dict[str, tuple] = {
    "toxicity": (
        "output",
        "output_toxicity",
        "block",
        "Toxic content detected in output",
    ),
    "no_refusal": ("output", "no_refusal", "warn", "LLM refusal detected in output"),
    "sensitive": (
        "output",
        "sensitive_data",
        "warn",
        "Sensitive data detected in output",
    ),
    "ban_topics": (
        "output",
        "output_ban_topics",
        "block",
        "Banned topic detected in output",
    ),
    "language": (
        "output",
        "output_language",
        "block",
        "Disallowed language detected in output",
    ),
    "relevance": (
        "output",
        "output_relevance",
        "warn",
        "Output may not be relevant to the prompt",
    ),
    "gibberish": (
        "output",
        "output_gibberish",
        "block",
        "Gibberish detected in output",
    ),
    "ban_competitors": (
        "output",
        "output_ban_competitors",
        "warn",
        "Competitor mention detected in output",
    ),
    "bias": ("output", "output_bias", "warn", "Bias detected in output"),
    "factual_consistency": (
        "output",
        "output_factual_consistency",
        "warn",
        "Factual inconsistency detected in output",
    ),
}

# Human-readable action labels keyed by severity
_SEVERITY_ACTION_LABEL: Dict[str, str] = {
    "block": "blocked",
    "warn": "warned",
    "info": "noted",
}


# Maps scanner_name → OutputScanners config field for dynamic severity override
_SCANNER_TO_CONFIG_FIELD: Dict[str, str] = {
    "toxicity": "detect_toxicity",
    "no_refusal": "detect_refusal",
    "sensitive": "detect_sensitive_data",
    "relevance": "check_relevance",
    "gibberish": "detect_gibberish",
    "bias": "detect_bias",
    "factual_consistency": "check_factual_consistency",
}


def _result_to_violation(
    result: ScannerResult, output_scanners: Optional[OutputScanners] = None
) -> Optional[Violation]:
    """Convert a failed ScannerResult into a Violation, or None if it passed."""
    if result.is_valid:
        return None

    # deanonymize is a transform, not a violation scanner
    if result.scanner_name == "deanonymize":
        return None

    mapping = _VIOLATION_MAP.get(result.scanner_name)
    if mapping is None:
        logger.warning(
            "[GUARDRAILS] No violation mapping for output scanner: %s",
            result.scanner_name,
        )
        return None

    category, rule_name, severity, message_template = mapping

    # Override severity from config action when available
    config_field = _SCANNER_TO_CONFIG_FIELD.get(result.scanner_name)
    if config_field and output_scanners:
        action_val = getattr(output_scanners, config_field, None)
        if action_val and action_val in ("block", "warn"):
            severity = action_val

    action_label = _SEVERITY_ACTION_LABEL.get(severity, severity)
    details: Dict[str, Any] = {
        "confidence": result.risk_score,
        "detection_method": "llm_guard",
    }
    if result.metadata:
        details["scanner_metadata"] = result.metadata

    return Violation(
        category=category,
        rule_name=rule_name,
        severity=severity,
        message=f"{message_template} — {action_label} (risk score: {result.risk_score:.2f})",
        details=details,
    )


# ---------------------------------------------------------------------------
# OutputGuardrailEvaluator
# ---------------------------------------------------------------------------


class OutputGuardrailEvaluator:
    """Evaluates agent output against content filters and length limits."""

    async def evaluate(
        self,
        content: str,
        config: GuardrailsConfig,
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> GuardrailResult:
        """Evaluate agent output against guardrails.

        Pattern rules are applied first; the sanitized result is used for the
        output length check.  LLM Guard output scanners run on the **raw LLM
        output** (before pattern-rule redaction), so they see the original
        content with PII placeholders intact.  Deanonymize runs last as a
        pure transform.

        Args:
            content: The agent output text
            config: Guardrails configuration
            vault_id: Optional vault session id for PII deanonymization
            prompt: Original user prompt (needed by relevance, factual consistency)

        Returns:
            GuardrailResult with any violations found
        """
        result = GuardrailResult(passed=True)

        # Apply pattern rules
        if config.pattern_rules:
            filter_result = apply_pattern_rules(content, config.pattern_rules, "output")
            result = result.merge(filter_result)

        # LLM Guard scanners run on raw content (not post-pattern text)
        effective_content = (
            result.sanitized_content
            if result.sanitized_content is not None
            else content
        )

        # Check output length
        if config.max_output_length:
            length_result = self._check_output_length(
                effective_content, config.max_output_length
            )
            result = result.merge(length_result)

        # Run LLM Guard output scanners when any scanner flag is enabled
        # OR when deanonymize is needed.
        scanner_dict = _build_output_scanner_dict(config, vault_id)
        if scanner_dict:
            scanner_result = await self._run_output_scanners(
                content,
                scanner_dict,
                vault_id=vault_id,
                vault_secret=vault_secret,
                prompt=prompt,
                output_scanners=config.output_scanners,
            )
            result = result.merge(scanner_result)

        return result

    @staticmethod
    def _check_output_length(content: str, max_length: int) -> GuardrailResult:
        """Check if output content exceeds maximum length."""
        if not content or len(content) <= max_length:
            return GuardrailResult(passed=True)

        return GuardrailResult(
            passed=False,
            violations=[
                Violation(
                    category="behavioral",
                    rule_name="max_output_length",
                    severity="block",
                    message=f"Output exceeds maximum length ({len(content)} > {max_length})",
                    details={"length": len(content), "max_length": max_length},
                )
            ],
            action_taken="blocked",
        )

    @staticmethod
    async def _run_output_scanners(
        content: str,
        scanner_dict: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None,
        vault_secret: Optional[str] = None,
        prompt: Optional[str] = None,
        output_scanners: Optional[OutputScanners] = None,
    ) -> GuardrailResult:
        """Run output scanners via the active backend and map results to violations."""
        backend = get_scanner_backend()
        scan_result = await backend.scan_output(
            prompt=prompt or "",
            content=content,
            scanners=scanner_dict,
            vault_id=vault_id,
            vault_secret=vault_secret,
        )

        violations: List[Violation] = []
        sanitized_content: Optional[str] = None

        for result in scan_result.results:
            # Capture deanonymized content
            if result.scanner_name == "deanonymize" and result.sanitized:
                sanitized_content = result.sanitized
                continue

            violation = _result_to_violation(result, output_scanners=output_scanners)
            if violation is not None:
                violations.append(violation)

        if any(v.severity == "block" for v in violations):
            return GuardrailResult(
                passed=False,
                violations=violations,
                action_taken="blocked",
                sanitized_content=sanitized_content,
            )
        if violations:
            return GuardrailResult(
                passed=True,
                violations=violations,
                action_taken="warned",
                sanitized_content=sanitized_content,
            )
        return GuardrailResult(passed=True, sanitized_content=sanitized_content)
