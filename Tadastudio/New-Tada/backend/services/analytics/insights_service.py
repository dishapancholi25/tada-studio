"""Monthly Documents/Queries/Sessions counts for a single workflow, powering the
"AI Application Insights" dashboard chart.

``documents_monthly`` mirrors the reachability logic of
``metrics_service._compute_documents_ingested`` (documents reachable from the
workflow's latest DOCUMENT_SEARCH / DOCUMENT_RETRIEVE nodes) so the two
endpoints report a consistent definition of "documents", grouped by
``documents.uploaded_at`` instead of a point-in-time total. Previously this
counted ``file_info`` attachments on chat messages, which reflects file
uploads attached to a chat turn, not RAG document ingestion, and stayed at 0
for workflows that only ingest documents via DOCUMENT_SEARCH/DOCUMENT_RETRIEVE
(the normal path) -- see task history for the reconciliation that surfaced
this mismatch.
"""

import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.models import Workflow
from backend.services.config import get_logger
from backend.services.database import get_db

logger = get_logger("analytics.insights")

# 'api'-triggered executions vastly outnumber 'chat' ones and don't represent
# genuine user-facing usage (data-backed decision). Configurable rather than
# hardcoded so it can be revisited without a code change.
QUERIES_TRIGGER_TYPE = os.getenv("ANALYTICS_QUERIES_TRIGGER_TYPE", "chat")

_INSIGHTS_SQL = text(
    """
    WITH target_workflow AS (
        SELECT id FROM workflows WHERE id = :workflow_id AND is_deleted = false
    ),
    queries_monthly AS (
        SELECT date_trunc('month', ge.start_time) AS month, COUNT(*) AS queries
        FROM graph_executions ge
        WHERE ge.workflow_id IN (SELECT id FROM target_workflow)
          AND ge.trigger_type = :queries_trigger_type
        GROUP BY 1
    ),
    sessions_monthly AS (
        SELECT date_trunc('month', cs.created_at) AS month, COUNT(*) AS sessions
        FROM chat_sessions cs
        WHERE cs.workflow_id IN (SELECT id FROM target_workflow)
          AND cs.is_deleted = false
        GROUP BY 1
    ),
    latest_defs AS (
        SELECT DISTINCT ON (workflow_id) *
        FROM graph_definitions
        WHERE workflow_id IN (SELECT id FROM target_workflow) AND is_latest = true
        ORDER BY workflow_id, version DESC, created_at DESC
    ),
    search_nodes AS (
        SELECT node -> 'document_search_config' AS config
        FROM latest_defs gd,
             jsonb_array_elements(gd.definition_json::jsonb -> 'nodes') AS node
        WHERE node ->> 'type' = 'DOCUMENT_SEARCH'
    ),
    retrieve_nodes AS (
        SELECT node -> 'document_retrieve_config' AS config
        FROM latest_defs gd,
             jsonb_array_elements(gd.definition_json::jsonb -> 'nodes') AS node
        WHERE node ->> 'type' = 'DOCUMENT_RETRIEVE'
          AND node -> 'document_retrieve_config' IS NOT NULL
    ),
    via_collections AS (
        SELECT DISTINCT d.id AS document_id, d.uploaded_at
        FROM search_nodes sn,
             jsonb_array_elements_text(sn.config -> 'document_collections') AS coll
        JOIN documents d ON d.collection_id = coll
    ),
    via_document_ids AS (
        SELECT DISTINCT d.id AS document_id, d.uploaded_at
        FROM search_nodes sn,
             jsonb_array_elements_text(sn.config -> 'document_ids') AS docid
        JOIN documents d ON d.id::text = docid
    ),
    via_retrieve_collections AS (
        SELECT DISTINCT d.id AS document_id, d.uploaded_at
        FROM retrieve_nodes rn,
             jsonb_array_elements_text(rn.config -> 'collection_ids') AS coll
        JOIN documents d ON d.collection_id = coll
    ),
    documents_monthly AS (
        SELECT date_trunc('month', uploaded_at) AS month, COUNT(DISTINCT document_id) AS documents
        FROM (
            SELECT document_id, uploaded_at FROM via_collections
            UNION SELECT document_id, uploaded_at FROM via_document_ids
            UNION SELECT document_id, uploaded_at FROM via_retrieve_collections
        ) combined
        GROUP BY 1
    )
    SELECT
        to_char(m.month, 'Mon') AS month,
        COALESCE(d.documents, 0) AS documents,
        COALESCE(q.queries, 0) AS queries,
        COALESCE(s.sessions, 0) AS sessions
    FROM (
        SELECT month FROM queries_monthly
        UNION SELECT month FROM sessions_monthly
        UNION SELECT month FROM documents_monthly
    ) m
    LEFT JOIN queries_monthly q ON q.month = m.month
    LEFT JOIN sessions_monthly s ON s.month = m.month
    LEFT JOIN documents_monthly d ON d.month = m.month
    ORDER BY m.month
    """
)


class WorkflowNotFoundError(Exception):
    """Raised when the workflow doesn't exist or is soft-deleted."""


def _get_active_workflow(workflow_id: str, db: Session) -> Workflow:
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.is_deleted.is_(False))
        .first()
    )
    if not workflow:
        raise WorkflowNotFoundError(workflow_id)
    return workflow


def get_application_insights(workflow_id: str) -> dict[str, Any]:
    """Return monthly Documents/Queries/Sessions counts for one workflow.

    Caller must have already verified the requesting user has access to
    ``workflow_id`` (see ``require_workflow_access_by_id``); this function only
    checks that the workflow exists and is not soft-deleted.

    Raises:
        WorkflowNotFoundError: if the workflow is missing or soft-deleted.
    """
    with get_db() as db:
        workflow = _get_active_workflow(workflow_id, db)

        rows = db.execute(
            _INSIGHTS_SQL,
            {
                "workflow_id": workflow_id,
                "queries_trigger_type": QUERIES_TRIGGER_TYPE,
            },
        ).fetchall()

        return {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "data": [
                {
                    "month": row.month,
                    "documents": int(row.documents),
                    "queries": int(row.queries),
                    "sessions": int(row.sessions),
                }
                for row in rows
            ],
        }
