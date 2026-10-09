"""Evaluation trigger service.

Handles automatic evaluation triggering on workflow publish and modify events.
Provides debounced scheduling, dispatch, and startup reconciliation.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from backend.services.config import get_logger

logger = get_logger("evaluation.trigger")

DEBOUNCE_WINDOW_SECONDS = int(os.getenv("EVAL_DEBOUNCE_WINDOW_SECONDS", "60"))
RECONCILE_MAX_AGE_HOURS = int(os.getenv("EVAL_RECONCILE_MAX_AGE_HOURS", "24"))
AUTO_TRIGGER_TYPES = ("publish_event", "modify_event")


class EvaluationTriggerService:
    """Manages automatic evaluation triggers with debouncing.

    Responsibilities:
        - Fire evaluations on workflow publish events
        - Fire evaluations on workflow modify events (if auto-eval enabled)
        - Debounce rapid modifications to avoid redundant runs
        - Dispatch evaluation runs to the orchestrator
        - Reconcile missed runs on application startup
    """

    def __init__(self):
        self._pending_triggers: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def trigger_on_publish(
        self,
        workflow_id: str,
        revision: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Trigger an evaluation run when a workflow is published.

        Always schedules a trigger regardless of auto-eval config,
        since publishing is an explicit user action.

        Args:
            workflow_id: The workflow UUID.
            revision: Optional version/revision string.
            user_id: Optional user who published.
        """
        logger.info(
            "Evaluation trigger on publish: workflow_id=%s, revision=%s, user_id=%s",
            workflow_id,
            revision,
            user_id,
        )
        config = await self._get_auto_eval_config(workflow_id)
        debounce = (config or {}).get(
            "debounce_window_seconds", DEBOUNCE_WINDOW_SECONDS
        )
        await self._schedule_trigger(
            workflow_id=workflow_id,
            revision=revision,
            user_id=user_id,
            trigger_type="publish_event",
            debounce_seconds=debounce,
        )

    async def trigger_on_modify(
        self,
        workflow_id: str,
        revision: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Trigger an evaluation run when a workflow is modified.

        Only fires if auto-eval is enabled for the workflow.

        Args:
            workflow_id: The workflow UUID.
            revision: Optional version/revision string.
            user_id: Optional user who modified.
        """
        config = await self._get_auto_eval_config(workflow_id)
        if not config or not config.get("enabled", False):
            logger.debug(
                "Auto-eval not enabled for workflow %s, skipping modify trigger",
                workflow_id,
            )
            return

        logger.info(
            "Evaluation trigger on modify: workflow_id=%s, revision=%s, user_id=%s",
            workflow_id,
            revision,
            user_id,
        )
        debounce = config.get("debounce_window_seconds", DEBOUNCE_WINDOW_SECONDS)
        await self._schedule_trigger(
            workflow_id=workflow_id,
            revision=revision,
            user_id=user_id,
            trigger_type="modify_event",
            debounce_seconds=debounce,
        )

    async def _schedule_trigger(
        self,
        workflow_id: str,
        revision: Optional[str],
        user_id: Optional[str],
        trigger_type: str,
        debounce_seconds: int = DEBOUNCE_WINDOW_SECONDS,
    ) -> None:
        """Schedule a debounced evaluation trigger.

        Cancels any existing pending trigger for the same (workflow, trigger_type)
        combination and schedules a new one after the debounce window. Using a
        combined debounce key prevents a publish event from cancelling a pending
        modify event (or vice versa).

        Args:
            workflow_id: The workflow UUID.
            revision: Optional version/revision string.
            user_id: Optional triggering user.
            trigger_type: "publish_event" or "modify_event".
            debounce_seconds: Per-workflow debounce window in seconds.
        """
        debounce_key = f"{workflow_id}:{trigger_type}"

        async with self._lock:
            # Cancel existing pending trigger for the same workflow+trigger_type
            existing = self._pending_triggers.get(debounce_key)
            if existing and not existing.done():
                existing.cancel()
                logger.debug(
                    "Cancelled pending trigger for %s (replaced by new %s trigger)",
                    debounce_key,
                    trigger_type,
                )

            task = asyncio.create_task(
                self._delayed_trigger(
                    workflow_id=workflow_id,
                    revision=revision,
                    user_id=user_id,
                    trigger_type=trigger_type,
                    debounce_key=debounce_key,
                    debounce_seconds=debounce_seconds,
                )
            )
            self._pending_triggers[debounce_key] = task

    async def _delayed_trigger(
        self,
        workflow_id: str,
        revision: Optional[str],
        user_id: Optional[str],
        trigger_type: str,
        debounce_key: str = "",
        debounce_seconds: int = DEBOUNCE_WINDOW_SECONDS,
    ) -> None:
        """Wait for the debounce window then dispatch the evaluation.

        Args:
            workflow_id: The workflow UUID.
            revision: Optional version/revision string.
            user_id: Optional triggering user.
            trigger_type: "publish_event" or "modify_event".
            debounce_key: Combined key used for pending trigger tracking.
            debounce_seconds: Per-workflow debounce window in seconds.
        """
        try:
            await asyncio.sleep(debounce_seconds)
        except asyncio.CancelledError:
            logger.debug(
                "Delayed trigger cancelled for %s", debounce_key or workflow_id
            )
            return

        # Remove from pending
        async with self._lock:
            self._pending_triggers.pop(debounce_key or workflow_id, None)

        await self._dispatch_evaluation(
            workflow_id=workflow_id,
            revision=revision,
            user_id=user_id,
            trigger_type=trigger_type,
        )

    async def _dispatch_evaluation(
        self,
        workflow_id: str,
        revision: Optional[str],
        user_id: Optional[str],
        trigger_type: str,
    ) -> None:
        """Create an evaluation run record and dispatch execution.

        Looks up auto-eval config and dataset, creates the run in the DB,
        then fires off execution as a background task.

        Args:
            workflow_id: The workflow UUID.
            revision: Optional version/revision string.
            user_id: Optional triggering user.
            trigger_type: "publish" or "modify".
        """
        config = await self._get_auto_eval_config(workflow_id)
        dataset_id = config.get("dataset_id") if config else None

        if not dataset_id:
            self._notify_no_config(workflow_id, trigger_type)
            return

        from .repositories import EvaluationRunRepository

        run_repo = EvaluationRunRepository()

        # Resolve the latest graph_definition_id for version tracking
        graph_definition_id = None
        try:
            from backend.models.workflows import GraphDefinition
            from backend.services.database import get_db

            with get_db() as db:
                latest_gd = (
                    db.query(GraphDefinition)
                    .filter(
                        GraphDefinition.workflow_id == workflow_id,
                        GraphDefinition.is_latest.is_(True),
                    )
                    .first()
                )
                if latest_gd:
                    graph_definition_id = str(latest_gd.id)
        except Exception as exc:
            logger.warning(
                "Failed to resolve graph_definition_id for workflow %s: %s",
                workflow_id,
                exc,
            )

        run_name = f"auto-{trigger_type}-{workflow_id[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        run_data: Dict[str, Any] = {
            "name": run_name,
            "target_id": workflow_id,
            "target_type": "workflow",
            "dataset_id": dataset_id,
            "workflow_id": workflow_id,
            "trigger": trigger_type,
            "trigger_revision": revision,
            "triggered_by_user_id": user_id,
            "status": "pending",
            "trigger_delivery_status": "queued",
            "environment": config.get("environment", "dev"),
            "pillar_weights": config.get("pillar_weights"),
            "judge_model_config": config.get("judge_model_config"),
            "concurrency_limit": config.get("concurrency_limit", 5),
        }

        # Propagate quality_judge_provider into external_integration_config
        quality_judge_provider = config.get("quality_judge_provider")
        if quality_judge_provider:
            run_data["external_integration_config"] = {
                "quality_judge_provider": quality_judge_provider,
            }

        if graph_definition_id:
            run_data["graph_definition_id"] = graph_definition_id

        try:
            run = run_repo.create(run_data)
            run_id = str(run.id)
            logger.info(
                "Dispatched evaluation run %s for workflow %s (trigger=%s)",
                run_id,
                workflow_id,
                trigger_type,
            )
            asyncio.create_task(self._execute_run(run_id))
        except Exception as exc:
            logger.error(
                "Failed to create evaluation run for workflow %s: %s",
                workflow_id,
                exc,
            )

    async def _execute_run(self, run_id: str) -> None:
        """Execute an evaluation run and check for regressions.

        Updates trigger delivery status, runs the orchestrator, then
        invokes the regression policy service.

        Args:
            run_id: The evaluation run UUID.
        """
        # Update delivery status to dispatched
        try:
            from backend.models.evaluation import EvaluationRun
            from backend.services.database import get_db

            with get_db() as db:
                run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
                if run:
                    run.trigger_delivery_status = "dispatched"
                    db.commit()
        except Exception as exc:
            logger.warning(
                "Failed to update delivery status for run %s: %s", run_id, exc
            )

        # Execute via orchestrator
        try:
            from .orchestrator import EvaluationOrchestrator

            orchestrator = EvaluationOrchestrator()
            await orchestrator.start_run(run_id)
        except Exception as exc:
            logger.error("Orchestrator failed for run %s: %s", run_id, exc)
            return

        # Check for regressions
        try:
            from .regression import RegressionPolicyService

            regression_service = RegressionPolicyService()
            await regression_service.check_regression(run_id)
        except ImportError:
            logger.debug("RegressionPolicyService not available yet")
        except Exception as exc:
            logger.warning(
                "Regression check failed for run %s (non-fatal): %s", run_id, exc
            )

    async def _get_auto_eval_config(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve auto-evaluation configuration for a workflow.

        Reads the ``auto_eval_config`` JSON column from the Workflow model.
        The column stores a dict with at least ``enabled`` and ``dataset_id``,
        plus optional runtime settings (``environment``, ``pillar_weights``,
        ``concurrency_limit``, ``judge_model_config``).

        Args:
            workflow_id: The workflow UUID.

        Returns:
            Auto-eval configuration dict, or None if the workflow does not
            exist or has no auto-eval settings configured.
        """
        try:
            from backend.models.workflows import Workflow
            from backend.services.database import get_db

            with get_db() as db:
                workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
                if not workflow:
                    logger.warning(
                        "Workflow not found for auto-eval config: %s", workflow_id
                    )
                    return None

                config = getattr(workflow, "auto_eval_config", None)
                if not config or not isinstance(config, dict):
                    return None

                # Require at minimum 'enabled' and 'dataset_id'
                if not config.get("enabled") or not config.get("dataset_id"):
                    return None

                return config
        except Exception as exc:
            logger.warning(
                "Failed to get auto-eval config for workflow %s: %s", workflow_id, exc
            )
            return None

    def _notify_no_config(self, workflow_id: str, trigger_type: str) -> None:
        """Log that no auto-eval config/dataset was found.

        Args:
            workflow_id: The workflow UUID.
            trigger_type: The trigger type that was attempted.
        """
        logger.info(
            "No auto-eval config or dataset found for workflow %s (trigger=%s), skipping",
            workflow_id,
            trigger_type,
        )

    def reconcile_missed_runs_on_startup(self) -> None:
        """Mark queued auto-triggered runs as missed on startup.

        Called synchronously during application startup to implement
        at-most-once delivery: only auto-triggered runs (publish_event /
        modify_event) that were queued but never dispatched before a restart
        are marked as missed. Manual and other trigger types are left
        untouched. An age threshold prevents marking very old stale rows.

        Only ``trigger_delivery_status`` is updated to ``missed_restart``;
        the run ``status`` is NOT forced to ``cancelled`` so that callers
        can still inspect and optionally re-trigger.
        """
        try:
            from backend.models.evaluation import EvaluationRun
            from backend.services.database import get_db

            age_cutoff = datetime.now(timezone.utc) - timedelta(
                hours=RECONCILE_MAX_AGE_HOURS
            )

            with get_db() as db:
                missed_runs = (
                    db.query(EvaluationRun)
                    .filter(
                        EvaluationRun.trigger_delivery_status == "queued",
                        EvaluationRun.status == "pending",
                        EvaluationRun.trigger.in_(AUTO_TRIGGER_TYPES),
                        EvaluationRun.created_at >= age_cutoff,
                    )
                    .all()
                )

                if not missed_runs:
                    return

                for run in missed_runs:
                    run.trigger_delivery_status = "missed_restart"

                db.commit()

                # Emit notification for missed runs
                for run in missed_runs:
                    logger.warning(
                        "Missed auto-triggered evaluation run on startup: "
                        "run_id=%s, workflow_id=%s, trigger=%s",
                        run.id,
                        run.workflow_id,
                        run.trigger,
                    )

                logger.info(
                    "Reconciled %d missed auto-triggered evaluation runs on startup",
                    len(missed_runs),
                )
        except Exception as exc:
            logger.warning("Failed to reconcile missed evaluation runs: %s", exc)
