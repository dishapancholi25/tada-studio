"""Review configuration for agent output gating.

This module defines the ReviewConfig dataclass for configuring
agent output review before execution proceeds. Supports both
human-in-the-loop review and automated LLM review.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .llm import LLMConfig


@dataclass
class ReviewConfig:
    """Configuration for agent output review gating.

    Supports both human-in-the-loop review and automated LLM review.
    When enabled, agent output is reviewed before proceeding to the
    next node in the workflow.

    Attributes:
        review_enabled: Enable/disable review for this agent
        review_mode: Review type - "human" or "llm"
        review_prompt: Guidance for human reviewers OR prompt for LLM reviewer
        max_iterations: Maximum feedback cycles before auto-approve
        timeout_seconds: Timeout for human review (None = no timeout)
        auto_approve_on_timeout: If True, auto-approve on timeout; else auto-fail
        auto_approve_on_max_iterations: If True, auto-approve when max iterations reached
        reviewer_llm_config: LLM configuration for LLM review mode
    """

    review_enabled: bool = False
    review_mode: str = "human"  # "human" | "llm"
    review_prompt: str = (
        "Please review the agent's output and provide feedback if needed."
    )
    max_iterations: int = 3
    timeout_seconds: Optional[int] = None
    auto_approve_on_timeout: bool = False
    auto_approve_on_max_iterations: bool = True
    reviewer_llm_config: Optional[LLMConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the config
        """
        result = {
            "review_enabled": self.review_enabled,
            "review_mode": self.review_mode,
            "review_prompt": self.review_prompt,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "auto_approve_on_timeout": self.auto_approve_on_timeout,
            "auto_approve_on_max_iterations": self.auto_approve_on_max_iterations,
        }
        if self.reviewer_llm_config:
            result["reviewer_llm_config"] = self.reviewer_llm_config.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewConfig":
        """Create ReviewConfig from dictionary.

        Args:
            data: Dictionary containing review configuration

        Returns:
            ReviewConfig instance
        """
        if not data:
            return cls()

        reviewer_llm_config = None
        if data.get("reviewer_llm_config"):
            llm_data = data["reviewer_llm_config"]
            if isinstance(llm_data, dict):
                reviewer_llm_config = LLMConfig(**llm_data)
            elif isinstance(llm_data, LLMConfig):
                reviewer_llm_config = llm_data

        return cls(
            review_enabled=data.get("review_enabled", False),
            review_mode=data.get("review_mode", "human"),
            review_prompt=data.get(
                "review_prompt",
                "Please review the agent's output and provide feedback if needed.",
            ),
            max_iterations=data.get("max_iterations", 3),
            timeout_seconds=data.get("timeout_seconds"),
            auto_approve_on_timeout=data.get("auto_approve_on_timeout", False),
            auto_approve_on_max_iterations=data.get(
                "auto_approve_on_max_iterations", True
            ),
            reviewer_llm_config=reviewer_llm_config,
        )
