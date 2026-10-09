"""Pattern rule matching for input and output text.

Applies regex-based pattern rules to detect and optionally
redact or block content that matches configured patterns.
"""

import logging
import re
from typing import List

from backend.models.workflow.configs.guardrails import PatternRule
from backend.services.guardrails.models import GuardrailResult, Violation

logger = logging.getLogger(__name__)


def apply_pattern_rules(
    content: str,
    rules: List[PatternRule],
    direction: str,
) -> GuardrailResult:
    """Apply pattern rules to text content.

    Args:
        content: The text content to check
        rules: List of pattern rules to apply
        direction: "input" or "output" - used to filter which rules apply

    Returns:
        GuardrailResult with any violations found
    """
    if not content or not rules:
        return GuardrailResult(passed=True)

    violations: List[Violation] = []
    sanitized = content
    has_block = False
    has_redact = False

    for rule in rules:
        # Skip rules that don't apply to this direction
        if rule.applies_to not in ("both", direction):
            continue

        if not rule.patterns:
            continue

        # Collect matches across all patterns in the rule
        total_matches: list = []
        matched_patterns: list = []
        for entry in rule.patterns:
            regex = entry.regex if hasattr(entry, "regex") else str(entry)
            if not regex:
                continue
            try:
                matches = re.findall(regex, content, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                logger.warning(
                    f"[PATTERN-RULE] Invalid regex pattern '{regex}': {e}"
                )
                continue
            if matches:
                total_matches.extend(matches)
                label = entry.label if hasattr(entry, "label") else ""
                matched_patterns.append(label or regex)

        if not total_matches:
            continue

        violation_message = (
            rule.message or f"Content matched pattern rule '{rule.name}'"
        )

        if rule.action == "block":
            has_block = True
            violations.append(
                Violation(
                    category=direction,
                    rule_name=rule.name or "pattern_rule",
                    severity="block",
                    message=violation_message,
                    details={"patterns": matched_patterns, "match_count": len(total_matches)},
                )
            )
        elif rule.action == "redact":
            has_redact = True
            for entry in rule.patterns:
                regex = entry.regex if hasattr(entry, "regex") else str(entry)
                if not regex:
                    continue
                try:
                    sanitized = re.sub(
                        regex,
                        "[REDACTED]",
                        sanitized,
                        flags=re.IGNORECASE | re.MULTILINE,
                    )
                except re.error:
                    pass
            violations.append(
                Violation(
                    category=direction,
                    rule_name=rule.name or "pattern_rule",
                    severity="warn",
                    message=f"Content redacted: {violation_message}",
                    details={"patterns": matched_patterns, "match_count": len(total_matches)},
                )
            )
        elif rule.action == "warn":
            violations.append(
                Violation(
                    category=direction,
                    rule_name=rule.name or "pattern_rule",
                    severity="warn",
                    message=violation_message,
                    details={"patterns": matched_patterns, "match_count": len(total_matches)},
                )
            )

    if has_block:
        return GuardrailResult(
            passed=False,
            violations=violations,
            action_taken="blocked",
        )

    if has_redact:
        return GuardrailResult(
            passed=True,
            violations=violations,
            action_taken="redacted",
            sanitized_content=sanitized,
        )

    if violations:
        return GuardrailResult(
            passed=True,
            violations=violations,
            action_taken="warned",
        )

    return GuardrailResult(passed=True)
