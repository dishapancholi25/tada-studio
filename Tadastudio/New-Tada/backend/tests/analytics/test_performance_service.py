"""Tests for the read-only per-workflow Performance & Latency endpoint/service."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.models import GraphExecution, NodeExecution, Workflow
from backend.tests.conftest import TEST_USER_CLAIMS


def _delete_workflow_executions(db, workflow_id):
    """Delete node_executions before graph_executions to satisfy the FK constraint."""
    graph_execution_ids = [
        row[0] for row in db.query(GraphExecution.id).filter(GraphExecution.workflow_id == workflow_id)
    ]
    if graph_execution_ids:
        db.query(NodeExecution).filter(NodeExecution.graph_execution_id.in_(graph_execution_ids)).delete(
            synchronize_session=False
        )
    db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow_id).delete()


@pytest.fixture(autouse=True)
def _redirect_get_db_to_test_engine(monkeypatch, test_db_engine):
    """Point ``get_db()`` (used inside the analytics service) at the isolated
    test database instead of the real configured one. See the identical
    fixture in ``test_metrics_service.py`` for the full rationale."""
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
        name=f"perf-test-{name_suffix}-{uuid.uuid4().hex[:6]}",
        created_by_user_id=owner_user_id,
        is_deleted=is_deleted,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def _make_graph_execution(db, workflow_id, status="completed"):
    execution = GraphExecution(
        graph_id=workflow_id,
        graph_name="perf-test-graph",
        graph_definition={},
        workflow_id=workflow_id,
        status=status,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def _make_node_execution(db, graph_execution_id, status, duration_seconds, order=1, created_at=None):
    node = NodeExecution(
        graph_execution_id=graph_execution_id,
        node_id=f"node-{order}",
        node_name=f"Node {order}",
        node_type="agent",
        execution_order=order,
        status=status,
        duration_seconds=duration_seconds,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(node)
    db.commit()
    return node


class TestWorkflowPerformanceNotFound:
    def test_unknown_workflow_id_returns_404(self, test_client):
        response = test_client.get(f"/api/analytics/workflows/{uuid.uuid4()}/performance")
        assert response.status_code == 404

    def test_soft_deleted_workflow_returns_404(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "deleted", is_deleted=True)
        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/performance")
            assert response.status_code == 404
        finally:
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestWorkflowPerformanceLatencyAndReliability:
    def test_latency_excludes_stopped_and_failed_rows(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "latency")
        exec1 = _make_graph_execution(db, workflow.id)

        _make_node_execution(db, exec1.id, "completed", 10.0, order=1)
        _make_node_execution(db, exec1.id, "completed", 20.0, order=2)
        _make_node_execution(db, exec1.id, "completed", 30.0, order=3)
        _make_node_execution(db, exec1.id, "stopped", 999.0, order=4)
        _make_node_execution(db, exec1.id, "failed", 999.0, order=5)

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/performance")
            assert response.status_code == 200
            payload = response.json()
            assert payload["workflow_id"] == workflow.id

            latency = payload["latency"]
            # Only the 3 completed rows count toward latency; stopped/failed excluded.
            assert latency["total_rows"] == 3
            assert latency["rows_with_duration"] == 3
            assert latency["coverage_pct"] == pytest.approx(100.0)
            assert latency["avg_seconds"] == pytest.approx(20.0)
            assert latency["p50_seconds"] == pytest.approx(20.0)

            reliability = payload["reliability"]
            # All 5 rows (regardless of status) count toward reliability.
            assert reliability["total_executions"] == 5
            assert reliability["completed"] == 3
            assert reliability["stopped"] == 1
            assert reliability["failed"] == 1
            assert reliability["success_rate_pct"] == pytest.approx(60.0)
        finally:
            _delete_workflow_executions(db, workflow.id)
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_reliability_matches_manual_count_of_completed_rows(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "manual-count")
        exec1 = _make_graph_execution(db, workflow.id)

        statuses = ["completed"] * 6 + ["failed"] * 2 + ["stopped"] * 1
        for i, status in enumerate(statuses):
            _make_node_execution(db, exec1.id, status, 5.0 if status == "completed" else None, order=i)

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/performance")
            assert response.status_code == 200
            payload = response.json()

            manual_completed = sum(1 for s in statuses if s == "completed")
            manual_total = len(statuses)
            expected_rate = round(100.0 * manual_completed / manual_total, 2)

            reliability = payload["reliability"]
            assert reliability["completed"] == manual_completed
            assert reliability["total_executions"] == manual_total
            assert reliability["success_rate_pct"] == pytest.approx(expected_rate)

            # Latency section must be built only from the 6 completed rows.
            assert payload["latency"]["total_rows"] == manual_completed
        finally:
            _delete_workflow_executions(db, workflow.id)
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_zero_executions_returns_explicit_empty_state(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "empty")

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/performance")
            assert response.status_code == 200
            payload = response.json()
            assert payload["latency"]["total_rows"] == 0
            assert payload["latency"]["coverage_pct"] == 0.0
            assert payload["latency"]["avg_seconds"] is None
            assert payload["reliability"]["total_executions"] == 0
            assert payload["reliability"]["success_rate_pct"] is None
            assert payload["daily_trend"] == []
        finally:
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestWorkflowPerformanceDailyTrend:
    def test_groups_completed_rows_by_date(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "trend")
        exec1 = _make_graph_execution(db, workflow.id)

        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(days=1)

        _make_node_execution(db, exec1.id, "completed", 10.0, order=1, created_at=today)
        _make_node_execution(db, exec1.id, "completed", 20.0, order=2, created_at=today)
        _make_node_execution(db, exec1.id, "completed", 40.0, order=3, created_at=yesterday)
        # Excluded from the trend entirely (not completed).
        _make_node_execution(db, exec1.id, "failed", None, order=4, created_at=today)

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/performance")
            assert response.status_code == 200
            trend = response.json()["daily_trend"]
            assert len(trend) == 2

            by_date = {row["execution_date"]: row for row in trend}
            today_row = by_date[today.date().isoformat()]
            yesterday_row = by_date[yesterday.date().isoformat()]

            assert today_row["samples"] == 2
            assert today_row["avg_seconds"] == pytest.approx(15.0)
            assert yesterday_row["samples"] == 1
            assert yesterday_row["avg_seconds"] == pytest.approx(40.0)
        finally:
            _delete_workflow_executions(db, workflow.id)
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()
