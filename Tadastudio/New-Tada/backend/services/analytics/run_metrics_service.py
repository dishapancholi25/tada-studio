"""Per-workflow Run Metrics dashboard card (5 metrics), scoped to a single workflow_id.

SQL below is verified against the database and must be reproduced as-is: do not
alter the 30-day / 7-day / 14-day / 12-month windows or the status filters.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import Workflow
from backend.services.config import get_logger
from backend.services.database import get_db

from .insights_service import WorkflowNotFoundError

logger = get_logger("analytics.run_metrics")

_RUNS_TODAY_SQL = text(
    """
    SELECT COUNT(*) AS runs_today
    FROM graph_executions
    WHERE workflow_id = :workflow_id AND created_at::date = CURRENT_DATE
    """
)

_ACTIVE_RUNS_SQL = text(
    """
    SELECT COUNT(*) AS active_runs
    FROM graph_executions
    WHERE workflow_id = :workflow_id AND status = 'running'
    """
)

_FAILED_RUNS_30D_SQL = text(
    """
    SELECT COUNT(*) AS failed_runs
    FROM graph_executions
    WHERE workflow_id = :workflow_id
      AND status = 'failed'
      AND created_at >= CURRENT_DATE - INTERVAL '30 days'
    """
)

_SUCCESS_RATE_SQL = text(
    """
    WITH current_30d AS (
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed') AS success_count,
            COUNT(*) AS total_count
        FROM graph_executions
        WHERE workflow_id = :workflow_id
          AND created_at >= CURRENT_DATE - INTERVAL '30 days'
    ),
    last_7d AS (
        SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / NULLIF(COUNT(*), 0), 1)
            AS success_rate_recent
        FROM graph_executions
        WHERE workflow_id = :workflow_id
          AND created_at >= CURRENT_DATE - INTERVAL '7 days'
    ),
    prior_7d AS (
        SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'completed') / NULLIF(COUNT(*), 0), 1)
            AS success_rate_prior
        FROM graph_executions
        WHERE workflow_id = :workflow_id
          AND created_at >= CURRENT_DATE - INTERVAL '14 days'
          AND created_at < CURRENT_DATE - INTERVAL '7 days'
    )
    SELECT
        ROUND(100.0 * c.success_count / NULLIF(c.total_count, 0), 1) AS success_rate_30d,
        r.success_rate_recent,
        p.success_rate_prior,
        ROUND(r.success_rate_recent - p.success_rate_prior, 1) AS delta_vs_last_7d
    FROM current_30d c, last_7d r, prior_7d p
    """
)

_RUN_VOLUME_WEEKLY_SQL = text(
    """
    SELECT
        date_trunc('week', created_at)::date AS period_start,
        COUNT(*) FILTER (WHERE status = 'completed') AS successful,
        COUNT(*) FILTER (WHERE status = 'failed') AS failed,
        COUNT(*) AS total
    FROM graph_executions
    WHERE workflow_id = :workflow_id
      AND created_at >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY 1
    ORDER BY 1
    """
)

_RUN_VOLUME_MONTHLY_SQL = text(
    """
    SELECT
        date_trunc('month', created_at)::date AS period_start,
        COUNT(*) FILTER (WHERE status = 'completed') AS successful,
        COUNT(*) FILTER (WHERE status = 'failed') AS failed,
        COUNT(*) AS total
    FROM graph_executions
    WHERE workflow_id = :workflow_id
      AND created_at >= CURRENT_DATE - INTERVAL '12 months'
    GROUP BY 1
    ORDER BY 1
    """
)


def _get_active_workflow(workflow_id: str, db: Session) -> Workflow:
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.is_deleted.is_(False))
        .first()
    )
    if not workflow:
        raise WorkflowNotFoundError(workflow_id)
    return workflow


def _run_volume_rows(db: Session, sql: Any, workflow_id: str) -> list[dict[str, Any]]:
    return [
        {
            "period_start": row.period_start.isoformat(),
            "successful": int(row.successful),
            "failed": int(row.failed),
            "total": int(row.total),
        }
        for row in db.execute(sql, {"workflow_id": workflow_id}).fetchall()
    ]


def get_workflow_run_metrics(workflow_id: str) -> dict[str, Any]:
    """Return the 5 run-dashboard metrics for one workflow.

    Caller must have already verified the requesting user has access to
    ``workflow_id`` (see ``require_workflow_access_by_id``); this function only
    checks that the workflow exists and is not soft-deleted.

    Raises:
        WorkflowNotFoundError: if the workflow is missing or soft-deleted.
    """
    with get_db() as db:
        workflow = _get_active_workflow(workflow_id, db)
        params = {"workflow_id": workflow_id}

        runs_today = db.execute(_RUNS_TODAY_SQL, params).scalar() or 0
        active_runs = db.execute(_ACTIVE_RUNS_SQL, params).scalar() or 0
        failed_runs_30d = db.execute(_FAILED_RUNS_30D_SQL, params).scalar() or 0

        success_row = db.execute(_SUCCESS_RATE_SQL, params).one()
        success_rate = {
            "success_rate_30d": float(success_row.success_rate_30d)
            if success_row.success_rate_30d is not None
            else None,
            "success_rate_recent_7d": float(success_row.success_rate_recent)
            if success_row.success_rate_recent is not None
            else None,
            "success_rate_prior_7d": float(success_row.success_rate_prior)
            if success_row.success_rate_prior is not None
            else None,
            "delta_vs_last_7d": float(success_row.delta_vs_last_7d)
            if success_row.delta_vs_last_7d is not None
            else None,
        }

        run_volume_trend = {
            "weekly": _run_volume_rows(db, _RUN_VOLUME_WEEKLY_SQL, workflow_id),
            "monthly": _run_volume_rows(db, _RUN_VOLUME_MONTHLY_SQL, workflow_id),
        }

        return {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "runs_today": int(runs_today),
            "active_runs": int(active_runs),
            "failed_runs_30d": int(failed_runs_30d),
            "success_rate": success_rate,
            "run_volume_trend": run_volume_trend,
        }
