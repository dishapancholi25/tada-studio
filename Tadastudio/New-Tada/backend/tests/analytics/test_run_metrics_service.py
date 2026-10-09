"""Tests for the read-only per-workflow Run Metrics endpoint/service."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.models import GraphExecution, Workflow
from backend.tests.conftest import TEST_USER_CLAIMS


def _delete_workflow_executions(db, workflow_id):
    db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow_id).delete()


@pytest.fixture(autouse=True)
def _redirect_get_db_to_test_engine(monkeypatch, test_db_engine):
    """Point ``get_db()`` (used inside the analytics service) at the isolated
    test database instead of the real configured one. See the identical
    fixture in ``test_performance_service.py`` for the full rationale."""
    import backend.services.database.session as session_module

    monkeypatch.setattr(session_module, "get_engine", lambda: test_db_engine)
    session_module.reset_session_factory()
    yield
    session_module.reset_session_factory()


@pytest.fixture
def owner_user_id():
    return TEST_USER_CLAIMS["sub"]


def _make_workflow(db, owner_user_id, name_suffix, is_deleted=False):
    workflow = Workflow(
        name=f"run-metrics-test-{name_suffix}-{uuid.uuid4().hex[:6]}",
        created_by_user_id=owner_user_id,
        is_deleted=is_deleted,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def _make_graph_execution(db, workflow_id, status="completed", created_at=None):
    execution = GraphExecution(
        graph_id=workflow_id,
        graph_name="run-metrics-test-graph",
        graph_definition={},
        workflow_id=workflow_id,
        status=status,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


class TestRunMetricsValidationAndNotFound:
    def test_malformed_workflow_id_returns_400(self, test_client):
        response = test_client.get("/api/analytics/workflows/not-a-uuid/run-metrics")
        assert response.status_code == 400

    def test_unknown_workflow_id_returns_404(self, test_client):
        response = test_client.get(f"/api/analytics/workflows/{uuid.uuid4()}/run-metrics")
        assert response.status_code == 404

    def test_soft_deleted_workflow_returns_404(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "deleted", is_deleted=True)
        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/run-metrics")
            assert response.status_code == 404
        finally:
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestRunsTodayActiveFailed:
    def test_counts_match_manual_tally(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "counts")
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Today: 2 completed, 1 running, 1 failed.
        _make_graph_execution(db, workflow.id, "completed", now)
        _make_graph_execution(db, workflow.id, "completed", now)
        _make_graph_execution(db, workflow.id, "running", now)
        _make_graph_execution(db, workflow.id, "failed", now)
        # Yesterday: 1 running (not "today"), 1 failed (within 30d).
        _make_graph_execution(db, workflow.id, "running", yesterday)
        _make_graph_execution(db, workflow.id, "failed", yesterday)
        # Outside the 30-day failed window: must not count toward failed_runs_30d.
        _make_graph_execution(db, workflow.id, "failed", now - timedelta(days=40))

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/run-metrics")
            assert response.status_code == 200
            payload = response.json()
            assert payload["workflow_id"] == workflow.id
            assert payload["runs_today"] == 4
            assert payload["active_runs"] == 2
            assert payload["failed_runs_30d"] == 2
        finally:
            _delete_workflow_executions(db, workflow.id)
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestSuccessRate:
    def test_recent_prior_and_delta_match_manual_calculation(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "success-rate")
        now = datetime.now(timezone.utc)

        # Last 7 days: 7 completed, 3 failed -> 70.0%
        for _ in range(7):
            _make_graph_execution(db, workflow.id, "completed", now - timedelta(days=1))
        for _ in range(3):
            _make_graph_execution(db, workflow.id, "failed", now - timedelta(days=2))

        # 7-14 days ago (prior week): 4 completed, 4 failed -> 50.0%
        for _ in range(4):
            _make_graph_execution(db, workflow.id, "completed", now - timedelta(days=8))
        for _ in range(4):
            _make_graph_execution(db, workflow.id, "failed", now - timedelta(days=9))

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/run-metrics")
            assert response.status_code == 200
            success_rate = response.json()["success_rate"]

            # current_30d totals 18 rows, 11 completed -> round(100*11/18, 1)
            assert success_rate["success_rate_30d"] == pytest.approx(61.1)
            assert success_rate["success_rate_recent_7d"] == pytest.approx(70.0)
            assert success_rate["success_rate_prior_7d"] == pytest.approx(50.0)
            assert success_rate["delta_vs_last_7d"] == pytest.approx(20.0)
        finally:
            _delete_workflow_executions(db, workflow.id)
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestRunVolumeTrend:
    def test_weekly_bucket_matches_manual_count(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "volume-weekly")
        now = datetime.now(timezone.utc)

        for _ in range(5):
            _make_graph_execution(db, workflow.id, "completed", now)
        for _ in range(2):
            _make_graph_execution(db, workflow.id, "failed", now)
        _make_graph_execution(db, workflow.id, "running", now)

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/run-metrics")
            assert response.status_code == 200
            weekly = response.json()["run_volume_trend"]["weekly"]
            assert len(weekly) == 1
            assert weekly[0]["successful"] == 5
            assert weekly[0]["failed"] == 2
            assert weekly[0]["total"] == 8
        finally:
            _delete_workflow_executions(db, workflow.id)
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_monthly_buckets_split_across_two_calendar_months(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "volume-monthly")
        now = datetime.now(timezone.utc)
        # 35 days always lands in an earlier calendar month than "now".
        earlier_month = now - timedelta(days=35)

        _make_graph_execution(db, workflow.id, "completed", now)
        _make_graph_execution(db, workflow.id, "completed", now)
        _make_graph_execution(db, workflow.id, "failed", now)

        _make_graph_execution(db, workflow.id, "completed", earlier_month)
        _make_graph_execution(db, workflow.id, "failed", earlier_month)
        _make_graph_execution(db, workflow.id, "failed", earlier_month)

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/run-metrics")
            assert response.status_code == 200
            monthly = response.json()["run_volume_trend"]["monthly"]
            assert len(monthly) == 2

            by_start = sorted(monthly, key=lambda row: row["period_start"])
            earlier_row, current_row = by_start[0], by_start[1]

            assert earlier_row["successful"] == 1
            assert earlier_row["failed"] == 2
            assert earlier_row["total"] == 3

            assert current_row["successful"] == 2
            assert current_row["failed"] == 1
            assert current_row["total"] == 3
        finally:
            _delete_workflow_executions(db, workflow.id)
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestZeroRuns:
    def test_workflow_with_no_runs_returns_zeros_not_error(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "empty")

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/run-metrics")
            assert response.status_code == 200
            payload = response.json()

            assert payload["runs_today"] == 0
            assert payload["active_runs"] == 0
            assert payload["failed_runs_30d"] == 0

            success_rate = payload["success_rate"]
            assert success_rate["success_rate_30d"] is None
            assert success_rate["success_rate_recent_7d"] is None
            assert success_rate["success_rate_prior_7d"] is None
            assert success_rate["delta_vs_last_7d"] is None

            assert payload["run_volume_trend"]["weekly"] == []
            assert payload["run_volume_trend"]["monthly"] == []
        finally:
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()
