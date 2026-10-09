"""LLM Guard input scanner utilities for guardrail evaluation.

Provides a unified entry point (``classify_with_input_scanners``) that
builds a scanner config dict from ``BehavioralGuardrails`` flags and
delegates to the active ``ScannerBackend`` (local, API, or hybrid).

The scanner backend is selected at startup via the ``LLM_GUARD_MODE``
environment variable (see ``backends/__init__.py``).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from backend.models.workflow.configs.guardrails import GuardrailsConfig
from backend.services.guardrails.backends import get_scanner_backend
from backend.services.guardrails.backends.protocol import ScannerResult
from backend.services.guardrails.models import Violation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config → scanner dict builder
# ---------------------------------------------------------------------------


def _build_sanitization_scanner_dict(
    config: GuardrailsConfig,
) -> Dict[str, Dict[str, Any]]:
    """Build scanner dict for sanitization scanners (PII, secrets).

    These run first so their sanitized output can be fed to adversarial
    scanners, preventing false positives from PII patterns.
    """
    scanners: Dict[str, Dict[str, Any]] = {}

    if config.anonymize_pii and config.anonymize_pii != "off":
        scanner_config = {
            "action": config.anonymize_pii,
            "use_faker": config.use_faker,
        }
        if config.pii_entity_types:
            scanner_config["entity_types"] = config.pii_entity_types
        scanners["anonymize"] = scanner_config

    if config.detect_secrets and config.detect_secrets != "off":
        scanners["secrets"] = {}

    return scanners


def _build_detection_scanner_dict(
    config: GuardrailsConfig,
) -> Dict[str, Dict[str, Any]]:
    """Build scanner dict for detection scanners (adversarial + content).

    These run second, on sanitized content when available.
    """
    scanners: Dict[str, Dict[str, Any]] = {}

    if config.detect_prompt_injection and config.detect_prompt_injection != "off":
        scanners["prompt_injection"] = {"threshold": config.prompt_injection_threshold}

    if config.detect_jailbreak_attempts and config.detect_jailbreak_attempts != "off":
        scanners["jailbreak"] = {"threshold": config.jailbreak_threshold}

    if config.detect_toxicity and config.detect_toxicity != "off":
        scanners["toxicity"] = {"threshold": config.toxicity_threshold}

    if config.detect_gibberish and config.detect_gibberish != "off":
        scanners["gibberish"] = {}

    if config.ban_code and config.ban_code != "off":
        scanners["ban_code"] = {}

    if config.ban_topics:
        scanners["ban_topics"] = {"topics": config.ban_topics}

    if config.allowed_languages:
        scanners["language"] = {"valid_languages": config.allowed_languages}

    if config.max_input_tokens is not None:
        scanners["token_limit"] = {"limit": config.max_input_tokens}

    return scanners


# ---------------------------------------------------------------------------
# ScannerResult → Violation mapping
# ---------------------------------------------------------------------------

# (scanner_name) → (category, rule_name, default_severity, message_template)
# Severity is overridden dynamically for scanners with configurable actions.
# Message templates should describe what was detected, NOT the action taken —
# the action suffix ("blocked" / "warned") is appended dynamically based on severity.
_VIOLATION_MAP: Dict[str, tuple] = {
    "prompt_injection": (
        "behavioral",
        "prompt_injection",
        "block",
        "Prompt injection detected",
    ),
    "jailbreak": (
        "behavioral",
        "jailbreak_attempt",
        "block",
        "Jailbreak attempt detected",
    ),
    "toxicity": ("behavioral", "toxicity", "block", "Toxic content detected"),
    "gibberish": ("behavioral", "gibberish", "block", "Gibberish content detected"),
    "ban_code": (
        "behavioral",
        "ban_code",
        "block",
        "Code content detected",
    ),
    "ban_topics": ("behavioral", "ban_topics", "block", "Banned topic detected"),
    "language": (
        "behavioral",
        "language_input",
        "block",
        "Input language not in allowed list",
    ),
    "token_limit": ("behavioral", "token_limit", "block", "Input exceeds token limit"),
    "secrets": ("behavioral", "secrets", "block", "Secret/credential detected"),
}

# Human-readable action labels keyed by severity
_SEVERITY_ACTION_LABEL: Dict[str, str] = {
    "block": "blocked",
    "warn": "warned",
    "info": "noted",
}


def _result_to_violation(
    result: ScannerResult, config: GuardrailsConfig
) -> Optional[Violation]:
    """Convert a failed ScannerResult into a Violation, or None if it passed."""
    if result.is_valid:
        return None

    # Dynamic mapping for anonymize scanner — severity depends on configured action
    if result.scanner_name == "anonymize":
        action = (
            config.anonymize_pii
            if config.anonymize_pii and config.anonymize_pii != "off"
            else "anonymize"
        )
        if action == "anonymize":
            severity, message_template = "warn", "PII detected and anonymized"
        elif action == "block":
            severity, message_template = "block", "PII detected"
        else:  # warn
            severity, message_template = "warn", "PII detected"
        category, rule_name = "behavioral", "pii_detected"
    else:
        mapping = _VIOLATION_MAP.get(result.scanner_name)
        if mapping is None:
            logger.warning(
                "[GUARDRAILS] No violation mapping for scanner: %s", result.scanner_name
            )
            return None
        category, rule_name, severity, message_template = mapping

        # Override severity from config action for scanners with action selectors
        _scanner_config_field = {
            "prompt_injection": "detect_prompt_injection",
            "jailbreak": "detect_jailbreak_attempts",
            "toxicity": "detect_toxicity",
            "gibberish": "detect_gibberish",
            "ban_code": "ban_code",
            "secrets": "detect_secrets",
        }
        config_field = _scanner_config_field.get(result.scanner_name)
        if config_field:
            action_val = getattr(config, config_field, None)
            if action_val and action_val in ("block", "warn"):
                severity = action_val

    # Enrich message with action label and risk score
    action_label = _SEVERITY_ACTION_LABEL.get(severity, severity)
    message = (
        f"{message_template} — {action_label} (risk score: {result.risk_score:.2f})"
    )

    details: Dict[str, Any] = {
        "confidence": result.risk_score,
        "detection_method": "llm_guard",
    }

    # Add scanner-specific metadata (threshold, entity_types, etc.)
    if result.metadata:
        details["scanner_metadata"] = result.metadata

    # Add scanner-specific details
    if result.scanner_name == "token_limit" and config.max_input_tokens is not None:
        details["limit"] = config.max_input_tokens

    return Violation(
        category=category,
        rule_name=rule_name,
        severity=severity,
        message=message,
        details=details,
    )


# ---------------------------------------------------------------------------
# Unified scanner entry point
# ---------------------------------------------------------------------------


async def classify_with_input_scanners(
    content: str,
    config: GuardrailsConfig,
    vault_id: Optional[str] = None,
    vault_secret: Optional[str] = None,
) -> Tuple[List[Violation], Optional[str], Optional[str], Optional[str]]:
    """Run LLM Guard input scanners based on *config* flags.

    Executes in two phases:
    1. **Sanitization** — PII anonymization and secret redaction run first
       so that sensitive data patterns are removed from the input.
    2. **Detection** — adversarial and content scanners run on the
       sanitized text, preventing false positives caused by PII/secret
       patterns that confuse the prompt-injection classifier.

    Returns:
        ``(violations, sanitized_content, vault_id, vault_secret)`` where
        *sanitized_content* is the anonymized/redacted text when applicable,
        *vault_id* is the Vault session identifier for PII round-trips,
        and *vault_secret* is the ownership token for the vault session.
    """
    sanitization_scanners = _build_sanitization_scanner_dict(config)
    detection_scanners = _build_detection_scanner_dict(config)
    if not sanitization_scanners and not detection_scanners:
        return [], None, None, None

    backend = get_scanner_backend()
    violations: List[Violation] = []
    sanitized_content: Optional[str] = None
    returned_vault_id: Optional[str] = None
    returned_vault_secret: Optional[str] = None

    # Phase 1: sanitization (PII, secrets) — run on raw content
    if sanitization_scanners:
        sanitize_result = await backend.scan_input(
            content, sanitization_scanners, vault_id=vault_id, vault_secret=vault_secret
        )
        for result in sanitize_result.results:
            violation = _result_to_violation(result, config)
            if violation is not None:
                violations.append(violation)
        if sanitize_result.sanitized_content is not None:
            sanitized_content = sanitize_result.sanitized_content
        returned_vault_id = sanitize_result.vault_id
        returned_vault_secret = sanitize_result.vault_secret

    # Phase 2: detection (adversarial, content) — run on sanitized content
    if detection_scanners:
        detection_input = (
            sanitized_content if sanitized_content is not None else content
        )
        detect_result = await backend.scan_input(detection_input, detection_scanners)
        for result in detect_result.results:
            violation = _result_to_violation(result, config)
            if violation is not None:
                violations.append(violation)

    return (
        violations,
        sanitized_content,
        returned_vault_id,
        returned_vault_secret,
    )
