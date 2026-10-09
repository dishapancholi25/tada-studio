#!/usr/bin/env python3
"""Seed local/dev-only execution_feedback rows for the User Satisfaction metric.

Refuses to run unless ENVIRONMENT is a non-production value AND the caller
opts in explicitly (--force or ALLOW_ANALYTICS_SEED=true), so it can never
run unattended against a production database.

Usage (PowerShell):
    python -m backend.scripts.seed_execution_feedback --workflow-id <id> --force
    python -m backend.scripts.seed_execution_feedback --workflow-id <id> --positive 8 --negative 2 --force
    python -m backend.scripts.seed_execution_feedback --workflow-id <id> --remove --force
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.models import ExecutionFeedback, GraphExecution, Workflow  # noqa: E402
from backend.services.database import get_db  # noqa: E402

SEED_USER_ID = "seed-dev-user"
SEED_MARKER = "[seed:dev-satisfaction]"
_NON_PRODUCTION_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}


class ProductionGuardError(RuntimeError):
    """Raised when the seed would run against a production-configured environment."""


def _assert_safe_to_seed(force: bool) -> None:
    environment = os.getenv("ENVIRONMENT", "development").lower()
    if environment not in _NON_PRODUCTION_ENVIRONMENTS:
        raise ProductionGuardError(
            f"ENVIRONMENT={environment!r} is not a recognized non-production value; refusing to seed."
        )
    if not (force or os.getenv("ALLOW_ANALYTICS_SEED", "").lower() == "true"):
        raise ProductionGuardError(
            "Seeding requires --force or ALLOW_ANALYTICS_SEED=true as an explicit opt-in."
        )


def _pick_workflow_id(db, workflow_id: str | None) -> str:
    if workflow_id:
        return workflow_id
    workflow = db.query(Workflow).filter(Workflow.is_deleted.is_(False)).order_by(Workflow.created_at.desc()).first()
    if not workflow:
        raise ValueError("No workflows exist; pass --workflow-id or create a workflow first.")
    return workflow.id


def _ensure_executions(db, workflow_id: str, needed: int) -> list[str]:
    """Return ids of `needed` graph_executions for this workflow, creating minimal
    completed ones if too few already exist (dev DBs are often empty)."""
    existing = (
        db.query(GraphExecution.id)
        .filter(GraphExecution.workflow_id == workflow_id)
        .order_by(GraphExecution.created_at.desc())
        .limit(needed)
        .all()
    )
    ids = [row[0] for row in existing]
    while len(ids) < needed:
        execution = GraphExecution(
            graph_id=workflow_id,
            graph_name="seed-dev-satisfaction",
            graph_definition={},
            workflow_id=workflow_id,
            status="completed",
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        ids.append(execution.id)
    return ids


def seed(workflow_id: str | None, positive: int, negative: int, force: bool) -> None:
    _assert_safe_to_seed(force)
    with get_db() as db:
        target_workflow_id = _pick_workflow_id(db, workflow_id)
        execution_ids = _ensure_executions(db, target_workflow_id, positive + negative)

        # Idempotent: skip executions that already carry a seed feedback row.
        already_seeded = {
            row[0]
            for row in db.query(ExecutionFeedback.graph_execution_id)
            .filter(
                ExecutionFeedback.graph_execution_id.in_(execution_ids),
                ExecutionFeedback.user_id == SEED_USER_ID,
            )
            .all()
        }

        ratings = ["positive"] * positive + ["negative"] * negative
        inserted = 0
        for execution_id, rating in zip(execution_ids, ratings):
            if execution_id in already_seeded:
                continue
            db.add(
                ExecutionFeedback(
                    graph_execution_id=execution_id,
                    rating=rating,
                    user_id=SEED_USER_ID,
                    comment=SEED_MARKER,
                )
            )
            inserted += 1
        db.commit()

        _report(db, target_workflow_id, inserted)


def remove(workflow_id: str | None, force: bool) -> None:
    _assert_safe_to_seed(force)
    with get_db() as db:
        target_workflow_id = _pick_workflow_id(db, workflow_id)
        deleted = (
            db.query(ExecutionFeedback)
            .filter(
                ExecutionFeedback.user_id == SEED_USER_ID,
                ExecutionFeedback.graph_execution_id.in_(
                    db.query(GraphExecution.id).filter(GraphExecution.workflow_id == target_workflow_id)
                ),
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"Removed {deleted} seeded execution_feedback row(s) for workflow {target_workflow_id}.")


def _report(db, workflow_id: str, inserted: int) -> None:
    total = (
        db.query(ExecutionFeedback)
        .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
        .filter(GraphExecution.workflow_id == workflow_id)
        .count()
    )
    positive_total = (
        db.query(ExecutionFeedback)
        .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
        .filter(GraphExecution.workflow_id == workflow_id, ExecutionFeedback.rating == "positive")
        .count()
    )
    negative_total = total - positive_total
    percentage = round(100.0 * positive_total / total, 2) if total else None
    print(f"Inserted {inserted} new row(s) for workflow {workflow_id}.")
    print(f"total_feedback={total} positive={positive_total} negative={negative_total} satisfaction={percentage}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-id", default=None, help="Target workflow id (defaults to most recent).")
    parser.add_argument("--positive", type=int, default=8, help="Number of positive feedback rows (default: 8).")
    parser.add_argument("--negative", type=int, default=2, help="Number of negative feedback rows (default: 2).")
    parser.add_argument("--remove", action="store_true", help="Remove previously seeded rows instead of inserting.")
    parser.add_argument(
        "--force", action="store_true", help="Explicit opt-in required (or set ALLOW_ANALYTICS_SEED=true)."
    )
    args = parser.parse_args()

    try:
        if args.remove:
            remove(args.workflow_id, args.force)
        else:
            seed(args.workflow_id, args.positive, args.negative, args.force)
    except ProductionGuardError as exc:
        print(f"Refusing to run: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
