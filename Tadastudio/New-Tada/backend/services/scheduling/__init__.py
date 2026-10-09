"""Workflow scheduling service using APScheduler."""

import os

from .scheduler_service import WorkflowSchedulerService

scheduler_service = WorkflowSchedulerService()


def is_scheduling_enabled() -> bool:
    """Single source of truth for the workflow scheduling feature toggle.

    Workflow scheduling is enabled by default. Set `SCHEDULING_ENABLED` to a
    falsey value to turn it off without changing code.
    """
    return os.getenv("SCHEDULING_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


__all__ = ["WorkflowSchedulerService", "scheduler_service", "is_scheduling_enabled"]
