"""Tests for the local/dev-only execution_feedback seed script."""

import uuid

import pytest

from backend.models import ExecutionFeedback, GraphExecution, Workflow
from backend.scripts.seed_execution_feedback import ProductionGuardError, remove, seed
from backend.tests.conftest import TEST_USER_CLAIMS


@pytest.fixture(autouse=True)
def _redirect_get_db_to_test_engine(monkeypatch, test_db_engine):
    """Point the seed script's ``get_db()`` at the isolated test database.

    Mirrors the redirect fixture in ``test_metrics_service.py``: the session
    module resolved `get_engine` at import time, so only patching the
    package-level attribute is not enough.
    """
    import backend.services.database.session as session_module

    monkeypatch.setattr(session_module, "get_engine", lambda: test_db_engine)
    session_module.reset_session_factory()
    yield
    session_module.reset_session_factory()


@pytest.fixture
def owner_user_id():
    return TEST_USER_CLAIMS["sub"]


def _make_workflow(db, owner_user_id, suffix):
    workflow = Workflow(name=f"seed-test-{suffix}-{uuid.uuid4().hex[:6]}", created_by_user_id=owner_user_id)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


class TestSeedExecutionFeedback:
    def test_seed_creates_expected_positive_and_negative_rows(
        self, test_db_session, owner_user_id, monkeypatch
    ):
        monkeypatch.setenv("ENVIRONMENT", "development")
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "creates")

        try:
            seed(workflow.id, positive=8, negative=2, force=True)

            rows = (
                db.query(ExecutionFeedback)
                .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
                .filter(GraphExecution.workflow_id == workflow.id)
                .all()
            )
            assert len(rows) == 10
            assert sum(1 for r in rows if r.rating == "positive") == 8
            assert sum(1 for r in rows if r.rating == "negative") == 2
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_(
                    db.query(GraphExecution.id).filter(GraphExecution.workflow_id == workflow.id)
                )
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_seed_is_idempotent_on_rerun(self, test_db_session, owner_user_id, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "idempotent")

        try:
            seed(workflow.id, positive=8, negative=2, force=True)
            seed(workflow.id, positive=8, negative=2, force=True)

            total = (
                db.query(ExecutionFeedback)
                .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
                .filter(GraphExecution.workflow_id == workflow.id)
                .count()
            )
            assert total == 10
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_(
                    db.query(GraphExecution.id).filter(GraphExecution.workflow_id == workflow.id)
                )
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_seed_refuses_in_production(self, test_db_session, owner_user_id, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "prod-guard")

        try:
            with pytest.raises(ProductionGuardError):
                seed(workflow.id, positive=8, negative=2, force=True)

            total = (
                db.query(ExecutionFeedback)
                .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
                .filter(GraphExecution.workflow_id == workflow.id)
                .count()
            )
            assert total == 0
        finally:
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_seed_requires_explicit_opt_in_even_in_dev(self, test_db_session, owner_user_id, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("ALLOW_ANALYTICS_SEED", raising=False)
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "no-force")

        try:
            with pytest.raises(ProductionGuardError):
                seed(workflow.id, positive=8, negative=2, force=False)
        finally:
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_remove_deletes_only_seeded_rows(self, test_db_session, owner_user_id, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "remove")
        execution = GraphExecution(
            graph_id=workflow.id,
            graph_name="real-user-feedback",
            graph_definition={},
            workflow_id=workflow.id,
            status="completed",
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        real_feedback = ExecutionFeedback(
            graph_execution_id=execution.id, rating="positive", user_id=owner_user_id
        )
        db.add(real_feedback)
        db.commit()

        try:
            seed(workflow.id, positive=8, negative=2, force=True)
            remove(workflow.id, force=True)

            remaining = (
                db.query(ExecutionFeedback)
                .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
                .filter(GraphExecution.workflow_id == workflow.id)
                .all()
            )
            assert len(remaining) == 1
            assert remaining[0].user_id == owner_user_id
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_(
                    db.query(GraphExecution.id).filter(GraphExecution.workflow_id == workflow.id)
                )
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()
