"""Data models for LLM service."""

from dataclasses import dataclass, field
from typing import Any, List

from backend.models.workflow.configs.llm import LLMConfig


@dataclass
class LLMInstance:
    """Wrapper for LLM instance with metadata."""

    llm: Any
    config: LLMConfig
    tools: List[Any] = field(default_factory=list)
    supports_tool_calling: bool = False
