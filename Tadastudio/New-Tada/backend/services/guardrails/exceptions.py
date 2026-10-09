"""Exceptions for the guardrails service."""

from typing import List, Optional

from backend.services.guardrails.models import Violation


class GuardrailViolationError(Exception):
    """Raised when a guardrail violation is detected in enforce mode.

    This exception propagates up through the node executor and workflow executor,
    causing the execution to fail rather than continue with blocked content.
    """

    def __init__(self, message: str, violations: Optional[List[Violation]] = None):
        super().__init__(message)
        self.violations = violations or []
