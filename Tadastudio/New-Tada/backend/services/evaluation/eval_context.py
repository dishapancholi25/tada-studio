"""Evaluation context tracking via contextvars.

Allows evaluation orchestrator to mark the current async context as
belonging to an evaluation run so that downstream LLM calls can be
transparently routed through the bounded dispatch queue.
"""

from contextvars import ContextVar
from typing import Optional

# When set, LLM calls in the current async context should be dispatched
# through the evaluation LLM dispatch queue.
_evaluation_run_id: ContextVar[Optional[str]] = ContextVar(
    "_evaluation_run_id", default=None
)


def set_evaluation_context(run_id: str) -> None:
    """Mark the current async context as belonging to an evaluation run."""
    _evaluation_run_id.set(run_id)


def clear_evaluation_context() -> None:
    """Clear the evaluation context."""
    _evaluation_run_id.set(None)


def get_evaluation_run_id() -> Optional[str]:
    """Return the current evaluation run ID, or None if not in an evaluation."""
    return _evaluation_run_id.get()


def is_evaluation_context() -> bool:
    """Return True if the current context is inside an evaluation run."""
    return _evaluation_run_id.get() is not None
