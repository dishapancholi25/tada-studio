"""Data models for guardrail evaluation results.

Defines the result and violation types returned by guardrail evaluators.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Violation:
    """A single guardrail violation.

    Attributes:
        category: Violation category (input, output, tool_call, token_budget, behavioral)
        rule_name: Name of the rule that was violated
        severity: How the violation should be handled (block, warn, info)
        message: Human-readable description of the violation
        details: Additional context about the violation
        timestamp: When the violation occurred (ISO format)
        policy_id: ID of the policy that produced this violation
        policy_name: Human-readable name of the source policy
    """

    category: str
    rule_name: str
    severity: str  # "block" | "warn" | "info"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    policy_id: str = ""
    policy_name: str = ""
    enforcement_mode: str = ""  # "enforce" | "audit" | "disabled" | ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "enforcement_mode": self.enforcement_mode,
        }


@dataclass
class GuardrailResult:
    """Result of a guardrail evaluation.

    Attributes:
        passed: Whether the check passed (no blocking violations)
        violations: List of violations found
        action_taken: What action was taken (none, blocked, redacted, warned)
        sanitized_content: Content after redaction, if applicable
    """

    passed: bool = True
    violations: List[Violation] = field(default_factory=list)
    action_taken: str = "none"  # "none" | "blocked" | "redacted" | "warned"
    sanitized_content: Optional[str] = None
    vault_id: Optional[str] = None
    vault_secret: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "action_taken": self.action_taken,
            "sanitized_content": self.sanitized_content,
        }
        if self.vault_id:
            result["vault_id"] = self.vault_id
        # vault_secret is intentionally excluded from serialization
        return result

    def merge(self, other: "GuardrailResult") -> "GuardrailResult":
        """Merge another result into this one.

        The merged result fails if either result fails.
        Violations are concatenated. The most severe action is kept.
        """
        action_priority = {
            "none": 0,
            "warned": 1,
            "transformed": 2,
            "redacted": 3,
            "blocked": 4,
        }
        merged_action = (
            self.action_taken
            if action_priority.get(self.action_taken, 0)
            >= action_priority.get(other.action_taken, 0)
            else other.action_taken
        )
        return GuardrailResult(
            passed=self.passed and other.passed,
            violations=self.violations + other.violations,
            action_taken=merged_action,
            sanitized_content=other.sanitized_content or self.sanitized_content,
            vault_id=other.vault_id or self.vault_id,
            vault_secret=other.vault_secret or self.vault_secret,
        )
