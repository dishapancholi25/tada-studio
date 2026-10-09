"""Per-workflow Performance & Latency dashboard card.

Three sections, all scoped to a single workflow_id and to the same rolling
30-day window (see ``_ref_time_mode`` — reuses the ``ANALYTICS_USAGE_REF_TIME``
convention from ``metrics_service`` so "now" vs "frozen UAT dump" is one
decision, not three):

- latency summary + daily trend: node_executions.status = 'completed' only
  (verified against UAT: status also takes 'failed', 'stopped', 'cancelled',
  'running', 'paused' — those are timeout/error/in-flight artifacts, not real
  latency samples, so they must not skew avg/percentiles).
- reliability: ALL node_executions statuses for the workflow, so failures are
  visible; success_rate_pct = completed / total_executions.

node_executions and graph_executions both have a ``status`` column — every
query below qualifies it (``ne.status`` vs ``ge.status``) to avoid Postgres's
"column reference is ambiguous" error.
"""

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import Workflow
from backend.services.config import get_logger
from backend.services.database import get_db

from .insights_service import WorkflowNotFoundError

logger = get_logger("analytics.performance")

WINDOW_DAYS = 30

_COMPLETED = "completed"
_STOPPED = "stopped"
_FAILED = "failed"

# Mirrors metrics_service._usage_ref_time_mode(): 'now' anchors the 30-day
# window to NOW() (production); 'max_row' anchors it to the workflow's latest
# node_executions.created_at (frozen UAT/test dumps with no recent activity).
_REF_TIME_NOW = "NOW() - INTERVAL '30 days'"
_REF_TIME_MAX_ROW = (
    "(SELECT MAX(ne2.created_at) FROM node_executions ne2 "
    "JOIN graph_executions ge2 ON ne2.graph_execution_id = ge2.id "
    "WHERE ge2.workflow_id = :workflow_id) - INTERVAL '30 days'"
)


def _ref_time_mode() -> str:
    return os.getenv("ANALYTICS_USAGE_REF_TIME", "now").strip().lower()


def _window_start_expr() -> str:
    return _REF_TIME_MAX_ROW if _ref_time_mode() == "max_row" else _REF_TIME_NOW


def _get_active_workflow(workflow_id: str, db: Session) -> Workflow:
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.is_deleted.is_(False))
        .first()
    )
    if not workflow:
        raise WorkflowNotFoundError(workflow_id)
    return workflow


def _latency_summary_sql() -> Any:
    return text(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(ne.duration_seconds) AS rows_with_duration,
            AVG(ne.duration_seconds) AS avg_seconds,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ne.duration_seconds) AS p50_seconds,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ne.duration_seconds) AS p95_seconds,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ne.duration_seconds) AS p99_seconds
        FROM node_executions ne
        JOIN graph_executions ge ON ne.graph_execution_id = ge.id
        WHERE ge.workflow_id = :workflow_id
          AND ne.status = :completed_status
          AND ne.created_at >= {_window_start_expr()}
        """
    )


def _daily_trend_sql() -> Any:
    return text(
        f"""
        SELECT
            DATE(ne.created_at) AS execution_date,
            COUNT(*) AS samples,
            AVG(ne.duration_seconds) AS avg_seconds,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ne.duration_seconds) AS p50_seconds,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ne.duration_seconds) AS p95_seconds
        FROM node_executions ne
        JOIN graph_executions ge ON ne.graph_execution_id = ge.id
        WHERE ge.workflow_id = :workflow_id
          AND ne.status = :completed_status
          AND ne.created_at >= {_window_start_expr()}
        GROUP BY DATE(ne.created_at)
        ORDER BY execution_date
        """
    )


def _reliability_sql() -> Any:
    return text(
        f"""
        SELECT
            ne.status AS status,
            COUNT(*) AS cnt
        FROM node_executions ne
        JOIN graph_executions ge ON ne.graph_execution_id = ge.id
        WHERE ge.workflow_id = :workflow_id
          AND ne.created_at >= {_window_start_expr()}
        GROUP BY ne.status
        """
    )


def get_workflow_performance(workflow_id: str) -> dict[str, Any]:
    """Return latency summary, daily trend, and reliability for one workflow.

    Caller must have already verified the requesting user has access to
    ``workflow_id`` (see ``require_workflow_access_by_id``); this function only
    checks that the workflow exists and is not soft-deleted.

    Raises:
        WorkflowNotFoundError: if the workflow is missing or soft-deleted.
    """
    with get_db() as db:
        workflow = _get_active_workflow(workflow_id, db)
        params = {"workflow_id": workflow_id, "completed_status": _COMPLETED}

        summary_row = db.execute(_latency_summary_sql(), params).one()
        total_rows = int(summary_row.total_rows or 0)
        rows_with_duration = int(summary_row.rows_with_duration or 0)
        latency = {
            "total_rows": total_rows,
            "rows_with_duration": rows_with_duration,
            "coverage_pct": round(100.0 * rows_with_duration / total_rows, 2) if total_rows else 0.0,
            "avg_seconds": round(float(summary_row.avg_seconds), 2) if summary_row.avg_seconds is not None else None,
            "p50_seconds": round(float(summary_row.p50_seconds), 2) if summary_row.p50_seconds is not None else None,
            "p95_seconds": round(float(summary_row.p95_seconds), 2) if summary_row.p95_seconds is not None else None,
            "p99_seconds": round(float(summary_row.p99_seconds), 2) if summary_row.p99_seconds is not None else None,
        }

        trend_rows = db.execute(_daily_trend_sql(), params).fetchall()
        daily_trend = [
            {
                "execution_date": row.execution_date.isoformat(),
                "samples": int(row.samples),
                "avg_seconds": round(float(row.avg_seconds), 2) if row.avg_seconds is not None else None,
                "p50_seconds": round(float(row.p50_seconds), 2) if row.p50_seconds is not None else None,
                "p95_seconds": round(float(row.p95_seconds), 2) if row.p95_seconds is not None else None,
            }
            for row in trend_rows
        ]

        status_counts = {
            row.status: int(row.cnt) for row in db.execute(_reliability_sql(), params).fetchall()
        }
        total_executions = sum(status_counts.values())
        completed = status_counts.get(_COMPLETED, 0)
        stopped = status_counts.get(_STOPPED, 0)
        failed = status_counts.get(_FAILED, 0)
        # Statuses outside completed/stopped/failed (e.g. running/cancelled/paused)
        # are folded into "other" rather than silently dropped from the total.
        other = total_executions - completed - stopped - failed
        reliability = {
            "total_executions": total_executions,
            "completed": completed,
            "stopped": stopped,
            "failed": failed,
            "other": other,
            "success_rate_pct": round(100.0 * completed / total_executions, 2) if total_executions else None,
        }

        return {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "window_days": WINDOW_DAYS,
            "ref_time_mode": _ref_time_mode(),
            "latency": latency,
            "daily_trend": daily_trend,
            "reliability": reliability,
        }
