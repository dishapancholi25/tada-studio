"""Tests for the per-workflow monthly Application Insights endpoint/service."""

import uuid
from datetime import datetime, timezone

import pytest

from backend.models import (
    ChatSession,
    Document,
    DocumentCollection,
    GraphDefinition,
    GraphExecution,
    User,
    Workflow,
)
from backend.tests.conftest import TEST_USER_CLAIMS


def _find_month(data, month):
    return next(row for row in data if row["month"] == month)


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
        name=f"insights-test-{name_suffix}-{uuid.uuid4().hex[:6]}",
        created_by_user_id=owner_user_id,
        is_deleted=is_deleted,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def _make_execution(
    db, workflow_id, *, trigger_type=None, output_data=None, status="completed"
):
    execution = GraphExecution(
        graph_id=workflow_id,
        graph_name="insights-test-graph",
        graph_definition={},
        workflow_id=workflow_id,
        status=status,
        trigger_type=trigger_type,
        output_data=output_data,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def _make_collection(db, name_suffix):
    collection = DocumentCollection(name=f"insights-coll-{name_suffix}-{uuid.uuid4().hex[:6]}")
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def _make_document(db, collection_id, name_suffix):
    document = Document(collection_id=collection_id, name=f"insights-doc-{name_suffix}-{uuid.uuid4().hex[:6]}")
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def _make_graph_definition(db, workflow_id, nodes, *, version=1, is_latest=True):
    definition = GraphDefinition(
        name=f"insights-def-{uuid.uuid4().hex[:6]}",
        workflow_id=workflow_id,
        definition_json={"nodes": nodes},
        version=version,
        is_latest=is_latest,
    )
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return definition


def _make_chat_session(db, workflow_id, user_id, *, is_deleted=False):
    session = ChatSession(
        title="insights-test-session",
        workflow_id=workflow_id,
        workflow_name="insights-test-graph",
        user_id=user_id,
        last_message_at=datetime.now(timezone.utc),
        is_deleted=is_deleted,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


class TestApplicationInsightsZeroMonths:
    def test_month_with_only_sessions_has_zero_documents_and_queries(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "zero-months")
        _make_chat_session(db, workflow.id, owner_user_id)

        try:
            response = test_client.get(
                f"/api/analytics/workflows/{workflow.id}/insights"
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["workflow_id"] == workflow.id
            assert len(payload["data"]) == 1
            row = payload["data"][0]
            assert row["sessions"] == 1
            assert row["documents"] == 0
            assert row["queries"] == 0
        finally:
            db.query(ChatSession).filter(
                ChatSession.workflow_id == workflow.id
            ).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestApplicationInsightsNotFoundOrDeleted:
    def test_nonexistent_workflow_returns_404(self, test_client):
        response = test_client.get(
            f"/api/analytics/workflows/{uuid.uuid4()}/insights"
        )
        assert response.status_code == 404

    def test_deleted_workflow_returns_404(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "deleted", is_deleted=True)

        try:
            response = test_client.get(
                f"/api/analytics/workflows/{workflow.id}/insights"
            )
            assert response.status_code == 404
        finally:
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_non_owned_workflow_is_forbidden(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        other_user_id = f"other-user-{uuid.uuid4().hex[:6]}"
        db.add(
            User(
                id=other_user_id,
                email=f"{other_user_id}@example.test",
                name="Other User",
            )
        )
        db.commit()
        other_workflow = _make_workflow(db, other_user_id, "not-mine")

        try:
            response = test_client.get(
                f"/api/analytics/workflows/{other_workflow.id}/insights"
            )
            assert response.status_code == 403
        finally:
            db.query(Workflow).filter(Workflow.id == other_workflow.id).delete()
            db.query(User).filter(User.id == other_user_id).delete()
            db.commit()


class TestApplicationInsightsDocuments:
    """documents_monthly mirrors metrics_service._compute_documents_ingested:
    documents reachable via the latest DOCUMENT_SEARCH/DOCUMENT_RETRIEVE nodes,
    grouped by documents.uploaded_at (not chat file_info attachments)."""

    def test_documents_reachable_via_document_search_node_are_counted(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "docs-search")
        collection = _make_collection(db, "search")
        doc = _make_document(db, collection.id, "search")
        definition = _make_graph_definition(
            db,
            workflow.id,
            [
                {
                    "type": "DOCUMENT_SEARCH",
                    "data": {},
                    "document_search_config": {
                        "document_collections": [collection.id],
                        "document_ids": [],
                    },
                }
            ],
        )

        try:
            response = test_client.get(
                f"/api/analytics/workflows/{workflow.id}/insights"
            )
            assert response.status_code == 200
            row = _find_month(
                response.json()["data"], datetime.now(timezone.utc).strftime("%b")
            )
            assert row["documents"] == 1
        finally:
            db.query(GraphDefinition).filter(GraphDefinition.id == definition.id).delete()
            db.query(Document).filter(Document.id == doc.id).delete()
            db.query(DocumentCollection).filter(DocumentCollection.id == collection.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_chat_file_attachment_alone_is_not_counted(
        self, test_client, test_db_session, owner_user_id
    ):
        """A file_info attachment on a chat message (no DOCUMENT_SEARCH/DOCUMENT_RETRIEVE
        node) must NOT count as a document -- that's a different signal (RAG ingestion)."""
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "file-attachment-only")
        _make_execution(
            db,
            workflow.id,
            trigger_type="chat",
            output_data={"node_outputs": {"n1": {"file_info": {"name": "good.pdf"}}}},
        )

        try:
            response = test_client.get(
                f"/api/analytics/workflows/{workflow.id}/insights"
            )
            assert response.status_code == 200
            row = _find_month(
                response.json()["data"], datetime.now(timezone.utc).strftime("%b")
            )
            assert row["documents"] == 0
        finally:
            db.query(GraphExecution).filter(
                GraphExecution.workflow_id == workflow.id
            ).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestApplicationInsightsTriggerTypeFiltering:
    def test_only_chat_trigger_counted_as_queries(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "trigger-filter")
        _make_execution(db, workflow.id, trigger_type="chat")
        _make_execution(db, workflow.id, trigger_type="api")
        _make_execution(db, workflow.id, trigger_type="api")
        _make_execution(db, workflow.id, trigger_type="editor")

        try:
            response = test_client.get(
                f"/api/analytics/workflows/{workflow.id}/insights"
            )
            assert response.status_code == 200
            row = _find_month(
                response.json()["data"], datetime.now(timezone.utc).strftime("%b")
            )
            assert row["queries"] == 1
        finally:
            db.query(GraphExecution).filter(
                GraphExecution.workflow_id == workflow.id
            ).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()
