"""Regression policy service.

Compares evaluation run scores against baselines to detect regressions
and classify their severity.
"""

import os
from typing import Optional

from backend.services.config import get_logger

logger = get_logger("evaluation.regression")

MODERATE_REGRESSION_THRESHOLD = float(
    os.getenv("EVAL_MODERATE_REGRESSION_THRESHOLD", "10.0")
)
SEVERE_REGRESSION_THRESHOLD = float(
    os.getenv("EVAL_SEVERE_REGRESSION_THRESHOLD", "20.0")
)


class RegressionPolicyService:
    """Detects and classifies regressions in evaluation runs.

    Responsibilities:
        - Compare a completed run's score against a baseline
        - Classify regression severity (moderate, severe)
        - Apply environment-specific policy (log/warn)
        - Persist regression metadata on the run record
    """

    async def check_regression(self, run_id: str) -> None:
        """Check a completed run for score regression against baseline.

        Loads the run, verifies it is the latest revision, finds the
        baseline score, classifies severity, and persists the result.

        Args:
            run_id: The evaluation run UUID.
        """
        from backend.models.evaluation import EvaluationRun
        from backend.services.database import get_db

        with get_db() as db:
            run = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
            if not run:
                logger.warning("Run not found for regression check: %s", run_id)
                return

            if run.composite_score is None:
                logger.debug(
                    "Run %s has no composite score, skipping regression check", run_id
                )
                return

            # Determine and persist latest-revision authority
            is_latest = await self._check_is_latest_revision(run, db)
            run.is_latest_revision = is_latest

            if not is_latest:
                logger.debug(
                    "Run %s is not the latest revision, skipping regression check",
                    run_id,
                )
                db.commit()
                return

            baseline_score = await self._get_baseline_score(run, db)
            if baseline_score is None:
                logger.info(
                    "No baseline score found for run %s, skipping regression check",
                    run_id,
                )
                return

            score_drop = baseline_score - run.composite_score
            severity = self._classify_severity(score_drop)

            if severity:
                # Tentatively mark as regressed; _apply_environment_policy()
                # refines regression_flag and regression_ack_required below.
                run.regression_flag = True
                run.regression_severity = severity
                logger.warning(
                    "Regression detected for run %s: score_drop=%.4f, severity=%s "
                    "(baseline=%.4f, current=%.4f)",
                    run_id,
                    score_drop,
                    severity,
                    baseline_score,
                    run.composite_score,
                )
                # Apply environment policy — sets regression_flag based on
                # environment + severity combination
                self._apply_environment_policy(run, severity)
            else:
                run.regression_flag = False
                run.regression_severity = None
                run.regression_ack_required = False
                logger.info(
                    "No regression for run %s (baseline=%.4f, current=%.4f, drop=%.4f)",
                    run_id,
                    baseline_score,
                    run.composite_score,
                    score_drop,
                )

            db.commit()

    async def _check_is_latest_revision(self, run, db) -> bool:
        """Check if the run is for the latest revision of its target.

        Compares the run's trigger_revision against the most recent
        completed triggered run for the same target.

        Args:
            run: The EvaluationRun instance.
            db: Active SQLAlchemy session.

        Returns:
            True if this is the latest revision or no comparison exists.
        """
        from backend.models.evaluation import EvaluationRun

        if not run.trigger_revision:
            return True

        latest = (
            db.query(EvaluationRun)
            .filter(
                EvaluationRun.target_id == run.target_id,
                EvaluationRun.target_type == run.target_type,
                EvaluationRun.status.in_(["completed", "completed_with_failures"]),
                EvaluationRun.trigger.in_(["publish_event", "modify_event"]),
                EvaluationRun.id != run.id,
            )
            .order_by(EvaluationRun.completed_at.desc())
            .first()
        )

        if not latest:
            return True

        # If no revision on the latest, assume current is latest
        if not latest.trigger_revision:
            return True

        return run.trigger_revision >= latest.trigger_revision

    async def _get_baseline_score(self, run, db) -> Optional[float]:
        """Get the baseline composite score for comparison.

        First checks for a pinned baseline on the dataset, then falls
        back to the most recent comparable completed run.

        Args:
            run: The EvaluationRun instance.
            db: Active SQLAlchemy session.

        Returns:
            Baseline composite score, or None if no baseline exists.
        """
        from backend.models.evaluation import EvaluationDataset, EvaluationRun

        # Check for pinned baseline on the dataset
        if run.dataset_id:
            dataset = (
                db.query(EvaluationDataset)
                .filter(EvaluationDataset.id == run.dataset_id)
                .first()
            )
            if dataset and dataset.baseline_run_id:
                baseline_run = (
                    db.query(EvaluationRun)
                    .filter(EvaluationRun.id == dataset.baseline_run_id)
                    .first()
                )
                if baseline_run and baseline_run.composite_score is not None:
                    logger.debug(
                        "Using pinned baseline run %s (score=%.4f) for run %s",
                        baseline_run.id,
                        baseline_run.composite_score,
                        run.id,
                    )
                    return baseline_run.composite_score

        # Fallback: most recent comparable completed run
        fallback = (
            db.query(EvaluationRun)
            .filter(
                EvaluationRun.target_id == run.target_id,
                EvaluationRun.target_type == run.target_type,
                EvaluationRun.dataset_id == run.dataset_id,
                EvaluationRun.status.in_(["completed", "completed_with_failures"]),
                EvaluationRun.composite_score.isnot(None),
                EvaluationRun.id != run.id,
            )
            .order_by(EvaluationRun.completed_at.desc())
            .first()
        )

        if fallback:
            logger.debug(
                "Using fallback baseline run %s (score=%.4f) for run %s",
                fallback.id,
                fallback.composite_score,
                run.id,
            )
            return fallback.composite_score

        return None

    def _classify_severity(self, score_drop: float) -> Optional[str]:
        """Classify the severity of a score regression.

        Args:
            score_drop: The difference (baseline - current). Positive means regression.

        Returns:
            "severe", "moderate", or None if no regression.
        """
        if score_drop >= SEVERE_REGRESSION_THRESHOLD:
            return "severe"
        if score_drop >= MODERATE_REGRESSION_THRESHOLD:
            return "moderate"
        return None

    def _apply_environment_policy(self, run, severity: str) -> None:
        """Apply environment-specific policy for a detected regression.

        Policy matrix:
            - dev/uat: warning-only, no hard regression flag
            - prod + moderate: warning with acknowledgement-gated state
            - prod + severe: hard regression flag (``regression_flag=True``)

        Args:
            run: The EvaluationRun instance.
            severity: Regression severity ("moderate" or "severe").
        """
        environment = getattr(run, "environment", "dev")
        run_id = str(run.id)

        if environment in ("dev", "uat"):
            # Warning-only for non-production environments
            run.regression_flag = False
            run.regression_ack_required = False
            logger.warning(
                "Regression detected in %s environment for run %s "
                "(severity=%s, target=%s). Warning only — no gating applied.",
                environment,
                run_id,
                severity,
                run.target_id,
            )
        elif environment == "prod" and severity == "severe":
            # Hard flag for production severe regressions
            run.regression_flag = True
            run.regression_ack_required = True
            logger.error(
                "SEVERE regression detected in %s environment for run %s "
                "(target=%s). Hard regression flag set — acknowledgement required.",
                environment,
                run_id,
                run.target_id,
            )
        elif environment == "prod" and severity == "moderate":
            # Acknowledgement-gated warning for production moderate regressions
            run.regression_flag = False
            run.regression_ack_required = True
            logger.warning(
                "Moderate regression detected in %s environment for run %s "
                "(target=%s). Acknowledgement required before proceeding.",
                environment,
                run_id,
                run.target_id,
            )
        else:
            # Default: warning-only for unknown environments
            run.regression_flag = False
            run.regression_ack_required = False
            logger.warning(
                "Regression detected in %s environment for run %s "
                "(severity=%s, target=%s). Warning only.",
                environment,
                run_id,
                severity,
                run.target_id,
            )
