"""Aggregates product-quality and usage metrics for a single workflow.

Three data sources per workflow, ALL scoped to real chat traffic
(``trigger_type='chat'``) so editor/API/evaluation/scheduler runs never
contribute to a metric a chat user wouldn't recognize:

- "runtime" trio (Response Time, Confidence Score Reliability, User
  Satisfaction) is computed directly from that workflow's chat-triggered
  graph_executions / node_executions / execution_feedback rows.
- Accuracy = share of real chat responses counted "correct". Primarily read
  from ``chat_response_scores`` (see ``backend.services.evaluation.chat_scoring``),
  where a response counts correct when quality_score >= ACCURACY_THRESHOLD.
  Thumbs-up/thumbs-down feedback (``execution_feedback.rating``, most-recent-
  per-execution wins any conflict) overrides the judge outright when present:
  it forces a response correct/incorrect regardless of quality_score, rescues
  an otherwise-excluded judge-failure sentinel row, and can even stand in for
  a chat execution the judge never scored at all. Both sources are scoped to
  ``trigger_type='chat'`` executions, deliberately EXCLUDING standalone/bulk
  evaluation runs, so this reflects only live chat traffic.
- Correctness is read from the workflow's most recently COMPLETED evaluation
  run's EvaluationResult rows (still evaluation-run scoped) when one exists.
  Otherwise it falls back to the average ``quality_score`` across judged
  ``chat_response_scores`` (the chat judge never grades a dedicated
  'Correctness' criterion, so the overall score is used as a proxy) so a
  workflow with only live chat traffic isn't stuck at "insufficient_data"
  forever. If neither source has data, the corresponding metric is reported
  as "insufficient_data" rather than fabricated.
- Faithfulness = (judged, grounded chat responses whose "Faithfulness" criterion
  score -- see ``chat_scoring.py``'s ``_GROUNDED_CRITERIA`` -- is >=
  ``FAITHFULNESS_THRESHOLD``) / (total judged, grounded chat responses) x 100,
  mirroring the literal supported-statements/total-statements formula at
  response granularity (no statement-level splitting exists in this codebase,
  so one judged response stands in for one "statement"). This threshold is
  independent of ``ACCURACY_THRESHOLD``. Ungrounded chat turns never get this
  criterion (nothing to check claims against), so they're excluded rather than
  counted as faithful or unfaithful. Hallucination Rate is derived as
  ``100 - Faithfulness`` (same sample), not an independent judge call.
- Groundedness is a DIFFERENT metric from Faithfulness, despite both coming from
  grounded chat responses: Faithfulness is a THRESHOLDED share of a holistic
  0-100 rubric criterion (one response = pass/fail), while Groundedness is the
  AVERAGE of the judge's own claim-level coverage ratio
  (``chat_response_scores.groundedness_score`` = supported_claims / total_claims,
  produced by the same merged judge call, see ``judge.py``'s
  ``include_groundedness``) expressed as a percentage -- no threshold, no
  pass/fail, just the mean coverage across judged, grounded chat responses.
"""

import os
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.models import (
    ChatResponseScore,
    EvaluationResult,
    EvaluationRun,
    ExecutionFeedback,
    GraphExecution,
    NodeExecution,
    Workflow,
)
from backend.services.config import get_logger
from backend.services.database import get_db

from .insights_service import WorkflowNotFoundError

logger = get_logger("analytics.metrics")

# Business-confirmed cutoff: a chat response counts as "correct" only when the
# judge's quality_score is 90 or above. Overridable via env if this changes.
ACCURACY_THRESHOLD = float(os.getenv("ANALYTICS_ACCURACY_THRESHOLD", "90"))

# Separate cutoff for Faithfulness: a response's Faithfulness criterion score
# must meet this to count as "factually supported". Independent of
# ACCURACY_THRESHOLD so the two can be tuned separately.
FAITHFULNESS_THRESHOLD = float(os.getenv("ANALYTICS_FAITHFULNESS_THRESHOLD", "90"))

STATUS_AVAILABLE = "available"
STATUS_INSUFFICIENT_DATA = "insufficient_data"

_COMPLETED = "completed"


def _metric(
    value: float | None,
    unit: str,
    sample_size: int,
    source: str,
    note: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single metric dict; status is derived from sample availability."""
    status = STATUS_AVAILABLE if sample_size > 0 and value is not None else STATUS_INSUFFICIENT_DATA
    return {
        "value": round(value, 2) if value is not None else None,
        "unit": unit,
        "sample_size": sample_size,
        "status": status,
        "source": source,
        "note": note,
        "extra": extra,
    }


def _get_active_workflow(workflow_id: str, db: Session) -> Workflow:
    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.is_deleted.is_(False))
        .first()
    )
    if not workflow:
        raise WorkflowNotFoundError(workflow_id)
    return workflow


def _compute_response_time(workflow_id: str, db: Session) -> dict[str, Any]:
    count = (
        db.query(func.count(GraphExecution.id))
        .filter(
            GraphExecution.workflow_id == workflow_id,
            GraphExecution.trigger_type == "chat",
            GraphExecution.status == _COMPLETED,
            GraphExecution.duration_seconds.isnot(None),
        )
        .scalar()
        or 0
    )
    if count == 0:
        return _metric(
            None,
            "seconds",
            0,
            "graph_executions.duration_seconds (trigger_type=chat)",
            note="No completed chat executions with recorded duration for this workflow yet.",
        )

    avg_duration, p95_duration = (
        db.query(
            func.avg(GraphExecution.duration_seconds),
            func.percentile_cont(0.95).within_group(GraphExecution.duration_seconds),
        )
        .filter(
            GraphExecution.workflow_id == workflow_id,
            GraphExecution.trigger_type == "chat",
            GraphExecution.status == _COMPLETED,
            GraphExecution.duration_seconds.isnot(None),
        )
        .one()
    )
    return _metric(
        float(avg_duration),
        "seconds",
        count,
        "graph_executions.duration_seconds (trigger_type=chat)",
        extra={"p95_seconds": round(float(p95_duration), 2) if p95_duration is not None else None},
    )


def _compute_reliability(workflow_id: str, db: Session) -> dict[str, Any]:
    total = (
        db.query(func.count(NodeExecution.id))
        .join(GraphExecution, NodeExecution.graph_execution_id == GraphExecution.id)
        .filter(GraphExecution.workflow_id == workflow_id, GraphExecution.trigger_type == "chat")
        .scalar()
        or 0
    )
    if total == 0:
        return _metric(
            None,
            "%",
            0,
            "node_executions.status (trigger_type=chat)",
            note="No node executions recorded for this workflow's chat traffic yet. "
            "This measures execution step success rate, not model confidence calibration.",
        )

    successful = (
        db.query(func.count(NodeExecution.id))
        .join(GraphExecution, NodeExecution.graph_execution_id == GraphExecution.id)
        .filter(
            GraphExecution.workflow_id == workflow_id,
            GraphExecution.trigger_type == "chat",
            NodeExecution.status == _COMPLETED,
        )
        .scalar()
        or 0
    )
    return _metric(
        100.0 * successful / total,
        "%",
        total,
        "node_executions.status (trigger_type=chat)",
        note="Execution step success rate (nodes completed / nodes run) across chat traffic; "
        "not a model confidence calibration score.",
    )


def _compute_satisfaction(workflow_id: str, db: Session) -> dict[str, Any]:
    total = (
        db.query(func.count(ExecutionFeedback.id))
        .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
        .filter(GraphExecution.workflow_id == workflow_id, GraphExecution.trigger_type == "chat")
        .scalar()
        or 0
    )
    if total == 0:
        return _metric(
            None,
            "%",
            0,
            "execution_feedback.rating (trigger_type=chat)",
            note="No user feedback (thumbs up/down) has been submitted for this workflow's chat traffic yet.",
        )

    positive = (
        db.query(func.count(ExecutionFeedback.id))
        .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
        .filter(
            GraphExecution.workflow_id == workflow_id,
            GraphExecution.trigger_type == "chat",
            ExecutionFeedback.rating == "positive",
        )
        .scalar()
        or 0
    )
    negative = total - positive
    return _metric(
        100.0 * positive / total,
        "%",
        total,
        "execution_feedback.rating (trigger_type=chat)",
        # Negative breakdown so the UI can render both positive/negative cards
        # without re-deriving it from `value` (which is only the positive share).
        extra={
            "positive_count": positive,
            "negative_count": negative,
            "positive_percentage": round(100.0 * positive / total, 2),
            "negative_percentage": round(100.0 * negative / total, 2),
        },
    )


def _latest_completed_run(workflow_id: str, db: Session) -> EvaluationRun | None:
    return (
        db.query(EvaluationRun)
        .filter(EvaluationRun.workflow_id == workflow_id, EvaluationRun.status == _COMPLETED)
        .order_by(EvaluationRun.completed_at.desc().nullslast(), EvaluationRun.created_at.desc())
        .first()
    )


def _extract_criterion(quality_raw: dict[str, Any] | None, name: str) -> float | None:
    """Case-insensitively look up a criterion score inside quality_raw.criteria_scores."""
    if not isinstance(quality_raw, dict):
        return None
    criteria = quality_raw.get("criteria_scores")
    if not isinstance(criteria, dict):
        return None
    for key, val in criteria.items():
        if isinstance(key, str) and key.strip().lower() == name:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return None


# Reasoning prefixes written only by the judge's own error-fallback paths
# (scoring.py's exception handler, judge.py's JSON-parse failure handler);
# a result with one of these is NOT a real quality_score=50, it's a sentinel
# meaning the judge crashed/returned unparseable output for that test case.
_JUDGE_FAILURE_REASONING_PREFIXES = ("Judge failed:", "Failed to parse judge response:")


def _is_judge_failure(scored: EvaluationResult | ChatResponseScore) -> bool:
    reasoning = scored.quality_raw.get("reasoning") if isinstance(scored.quality_raw, dict) else None
    return isinstance(reasoning, str) and reasoning.startswith(_JUDGE_FAILURE_REASONING_PREFIXES)


def _chat_response_scores(workflow_id: str, db: Session) -> list[ChatResponseScore]:
    """Real chat-triggered response scores for a workflow.

    Deliberately scoped to trigger_type='chat' AND evaluation_run_id IS NULL so
    standalone/bulk evaluation runs (which re-execute the graph against authored
    test cases, not real user traffic) never contribute to this metric.
    """
    return (
        db.query(ChatResponseScore)
        .join(GraphExecution, ChatResponseScore.graph_execution_id == GraphExecution.id)
        .filter(
            GraphExecution.workflow_id == workflow_id,
            GraphExecution.trigger_type == "chat",
            GraphExecution.evaluation_run_id.is_(None),
        )
        .all()
    )


def _execution_feedback_overrides(execution_ids: set[str], db: Session) -> dict[str, str]:
    """Most-recent feedback rating per execution_id, keyed for O(1) lookup.

    Reads oldest-first so a later dict assignment for the same execution_id
    overwrites an earlier one -- the last write is the most recent rating,
    resolving any positive/negative conflict without extra grouping logic.
    """
    if not execution_ids:
        return {}
    rows = (
        db.query(ExecutionFeedback.graph_execution_id, ExecutionFeedback.rating)
        .filter(ExecutionFeedback.graph_execution_id.in_(execution_ids))
        .order_by(ExecutionFeedback.created_at.asc())
        .all()
    )
    overrides: dict[str, str] = {}
    for execution_id, rating in rows:
        overrides[execution_id] = rating
    return overrides


def _chat_execution_ids_with_feedback(workflow_id: str, db: Session) -> set[str]:
    """Chat-scoped execution ids with any feedback, judged by the chat judge or not.

    Same trigger_type/evaluation_run_id scope as _chat_response_scores, so an
    execution with feedback but no ChatResponseScore row (chat judging never
    ran for it) is still discoverable as an Accuracy input.
    """
    rows = (
        db.query(ExecutionFeedback.graph_execution_id)
        .join(GraphExecution, ExecutionFeedback.graph_execution_id == GraphExecution.id)
        .filter(
            GraphExecution.workflow_id == workflow_id,
            GraphExecution.trigger_type == "chat",
            GraphExecution.evaluation_run_id.is_(None),
        )
        .distinct()
        .all()
    )
    return {row[0] for row in rows}


def _compute_chat_accuracy(workflow_id: str, db: Session) -> dict[str, Any]:
    """Accuracy = share of real chat responses counted "correct".

    Thumbs-up/thumbs-down feedback overrides the judge outright when present
    (most-recent feedback wins any positive/negative conflict on the same
    execution) -- this can rescue an otherwise-excluded judge-failure
    sentinel row, or stand in entirely for an execution the chat judge never
    scored. Only when an execution has no feedback does it fall back to
    quality_score >= ACCURACY_THRESHOLD (judge-failure rows still excluded
    from that fallback, as before).
    """
    scores_rows = _chat_response_scores(workflow_id, db)
    scores_by_id = {r.graph_execution_id: r for r in scores_rows}

    feedback_only_ids = _chat_execution_ids_with_feedback(workflow_id, db) - scores_by_id.keys()
    all_ids = scores_by_id.keys() | feedback_only_ids
    overrides = _execution_feedback_overrides(all_ids, db)

    passing = 0
    total = 0
    excluded_failures = 0
    for execution_id in all_ids:
        rating = overrides.get(execution_id)
        if rating is not None:
            total += 1
            passing += rating == "positive"
            continue
        row = scores_by_id[execution_id]
        if _is_judge_failure(row):
            excluded_failures += 1
            continue
        if row.quality_score is None:
            continue
        total += 1
        passing += row.quality_score >= ACCURACY_THRESHOLD

    source = "chat_response_scores.quality_score + execution_feedback.rating"
    if total == 0:
        note = "No judged chat responses or feedback for this workflow yet."
        if excluded_failures:
            note = (
                f"All {excluded_failures} judged chat response(s) failed to produce judge output "
                "(see each score's reasoning, e.g. missing LLM credentials/endpoint) and none had "
                "feedback to rescue them -- this is not a quality signal, not a real score of 0%."
            )
        return _metric(None, "%", 0, source, note=note)

    note = (
        "Share of chat responses counted correct: thumbs-up/down feedback (most recent per "
        "execution) overrides the judge when present -- including standing in for responses the "
        f"judge never scored; otherwise quality_score >= {ACCURACY_THRESHOLD}."
    )
    if excluded_failures:
        note += f" {excluded_failures} judge-failed result(s) with no feedback excluded."
    return _metric(100.0 * passing / total, "%", total, source, note=note)


def _compute_correctness(results: list[EvaluationResult]) -> dict[str, Any]:
    scores = [v for r in results if (v := _extract_criterion(r.quality_raw, "correctness")) is not None]
    if not scores:
        return _metric(
            None,
            "score (0-100)",
            0,
            "evaluation_results.quality_raw.criteria_scores.Correctness",
            note="No test case in the workflow's latest completed evaluation run scored a "
            "'Correctness' criterion.",
        )
    return _metric(
        sum(scores) / len(scores),
        "score (0-100)",
        len(scores),
        "evaluation_results.quality_raw.criteria_scores.Correctness",
    )


def _compute_chat_correctness(workflow_id: str, db: Session) -> dict[str, Any]:
    """Fallback Correctness for workflows with no completed evaluation run yet.

    Bulk evaluation runs grade a dedicated 'Correctness' criterion, but the
    chat judge never does (it grades Coherence/Relevance/Helpfulness or
    Faithfulness, see chat_scoring.py) -- so the closest equivalent from
    quality_raw is the judge's own overall quality_score, averaged across
    judged chat responses.
    """
    scores_rows = _chat_response_scores(workflow_id, db)
    usable = [r for r in scores_rows if not _is_judge_failure(r)]
    scores = [r.quality_score for r in usable if r.quality_score is not None]
    if not scores:
        return _metric(
            None,
            "score (0-100)",
            0,
            "chat_response_scores.quality_score",
            note="No judged chat responses for this workflow yet.",
        )
    return _metric(
        sum(scores) / len(scores),
        "score (0-100)",
        len(scores),
        "chat_response_scores.quality_score",
        note="Workflow has no completed evaluation run yet; average quality_score across "
        "judged chat responses is used as a proxy for Correctness.",
    )


def _grounded_usable_scores(workflow_id: str, db: Session) -> list[ChatResponseScore]:
    """Chat response scores that carried document context AND were not judge failures.

    Both Faithfulness and Groundedness operate on exactly this subset:
    - ``judged_with_context`` filters to executions where a DOCUMENT_SEARCH /
      DOCUMENT_RETRIEVE result was available (ungrounded turns are excluded,
      not counted as 0 or 100 / 0.0).
    - ``_is_judge_failure`` removes sentinel rows where the judge crashed so
      a quality_score=50 placeholder never contaminates either metric.
    """
    rows = [r for r in _chat_response_scores(workflow_id, db) if r.judged_with_context]
    return [r for r in rows if not _is_judge_failure(r)]


def _compute_faithfulness(workflow_id: str, db: Session) -> dict[str, Any]:
    """Faithfulness = (responses scored >= threshold as factually supported) / total x 100.

    Only chat responses judged WITH retrieved document context carry a
    Faithfulness criterion at all (see chat_scoring.py's _GROUNDED_CRITERIA) --
    ungrounded turns (greetings, clarifying questions) are excluded, not
    counted as 0 or 100. Each judged response stands in for one "statement" in
    the literal supported/total formula, since this codebase has no
    statement-level splitting; a response counts as "factually supported"
    when its Faithfulness criterion score >= FAITHFULNESS_THRESHOLD (a cutoff
    independent of ACCURACY_THRESHOLD).
    """
    usable = _grounded_usable_scores(workflow_id, db)
    scores = [v for r in usable if (v := _extract_criterion(r.quality_raw, "faithfulness")) is not None]
    if not scores:
        return _metric(
            None,
            "%",
            0,
            "chat_response_scores.quality_raw.criteria_scores.Faithfulness",
            note="No grounded (retrieved document context) chat responses judged for this "
            "workflow yet.",
        )
    supported = sum(1 for s in scores if s >= FAITHFULNESS_THRESHOLD)
    return _metric(
        100.0 * supported / len(scores),
        "%",
        len(scores),
        "chat_response_scores.quality_raw.criteria_scores.Faithfulness",
        note=f"Share of judged, grounded chat responses with Faithfulness criterion score >= "
        f"{FAITHFULNESS_THRESHOLD} (factually supported); ungrounded turns are excluded.",
    )


def _compute_groundedness(workflow_id: str, db: Session) -> dict[str, Any]:
    """Groundedness = average claim-coverage ratio across judged, grounded chat responses.

    Unlike Faithfulness (a threshold pass/fail share of a holistic 0-100 rubric
    criterion), Groundedness is read directly from the judge's own claim-level
    ``groundedness_score`` (supported_claims / total_claims, 0.0-1.0) and averaged
    rather than thresholded, since it's already a continuous coverage ratio. Only
    chat responses judged WITH retrieved document context carry a groundedness
    score at all (``judged_with_context``); ungrounded turns are excluded, not
    counted as 0.
    """
    usable = _grounded_usable_scores(workflow_id, db)
    scores = [r.groundedness_score for r in usable if r.groundedness_score is not None]
    if not scores:
        logger.info(
            "Groundedness unavailable for workflow %s: no grounded chat responses with groundedness scores",
            workflow_id,
        )
        return _metric(
            None,
            "%",
            0,
            "chat_response_scores.groundedness_score",
            note="No grounded (retrieved document context) chat responses judged for this "
            "workflow yet.",
        )
    average_groundedness = 100.0 * sum(scores) / len(scores)
    logger.info(
        "Groundedness computed for workflow %s: sample_size=%s average_pct=%.2f",
        workflow_id,
        len(scores),
        average_groundedness,
    )
    return _metric(
        average_groundedness,
        "%",
        len(scores),
        "chat_response_scores.groundedness_score",
        note="Average claim-coverage ratio (supported claims / total claims) across judged, "
        "grounded chat responses.",
    )


def _compute_hallucination_rate(faithfulness_metric: dict[str, Any]) -> dict[str, Any]:
    """Derived as 100 - Faithfulness (same sample); not an independent judge call."""
    if faithfulness_metric["value"] is None:
        return _metric(
            None,
            "%",
            0,
            "derived: 100 - faithfulness",
            note=faithfulness_metric["note"],
        )
    return _metric(
        100.0 - faithfulness_metric["value"],
        "%",
        faithfulness_metric["sample_size"],
        "derived: 100 - faithfulness",
        note="Derived as 100 minus Faithfulness (share of factually supported responses, same "
        "grounded-chat-response sample); alert threshold is > 5%.",
    )


def _count_metric(value: int, unit: str, source: str, note: str | None = None) -> dict[str, Any]:
    """Build a raw-count metric. Unlike ``_metric``, a count of 0 is a valid
    answer (an empty-but-real workflow), so status is always ``available``."""
    return {
        "value": float(value),
        "unit": unit,
        "sample_size": int(value),
        "status": STATUS_AVAILABLE,
        "source": source,
        "note": note,
        "extra": None,
    }


def _usage_ref_time_mode() -> str:
    """'now' (production) anchors the 24h/month windows to now(); 'max_row'
    anchors them to the latest row's timestamp (frozen UAT dump)."""
    return os.getenv("ANALYTICS_USAGE_REF_TIME", "now").strip().lower()


def _compute_total_users(workflow_id: str, db: Session) -> dict[str, Any]:
    count = (
        db.execute(
            text(
                "SELECT COUNT(DISTINCT user_id) FROM chat_sessions "
                "WHERE workflow_id = :workflow_id AND is_deleted = false"
            ),
            {"workflow_id": workflow_id},
        ).scalar()
        or 0
    )
    return _count_metric(count, "users", "chat_sessions.user_id")


def _compute_active_sessions(workflow_id: str, db: Session) -> dict[str, Any]:
    if _usage_ref_time_mode() == "max_row":
        sql = text(
            "WITH latest AS ("
            "    SELECT MAX(last_message_at) AS ref_time FROM chat_sessions "
            "    WHERE workflow_id = :workflow_id"
            ") "
            "SELECT COUNT(*) FROM chat_sessions, latest "
            "WHERE is_deleted = false AND workflow_id = :workflow_id "
            "AND last_message_at >= latest.ref_time - interval '24 hours'"
        )
    else:
        sql = text(
            "SELECT COUNT(*) FROM chat_sessions "
            "WHERE is_deleted = false AND workflow_id = :workflow_id "
            "AND last_message_at >= now() - interval '24 hours'"
        )
    count = db.execute(sql, {"workflow_id": workflow_id}).scalar() or 0
    return _count_metric(count, "sessions", "chat_sessions.last_message_at (24h window)")


def _compute_query_responses(workflow_id: str, db: Session) -> dict[str, Any]:
    """Count of real chat turns, matching the chat scope of the other usage
    KPIs (Total Users, Active Sessions, Monthly New Users) -- editor/API/
    evaluation/scheduler executions are not "query responses" a chat user saw.
    """
    count = (
        db.execute(
            text(
                "SELECT COUNT(*) FROM graph_executions "
                "WHERE workflow_id = :workflow_id AND trigger_type = 'chat'"
            ),
            {"workflow_id": workflow_id},
        ).scalar()
        or 0
    )
    return _count_metric(count, "responses", "graph_executions (trigger_type=chat)")


def _compute_documents_ingested(workflow_id: str, db: Session) -> dict[str, Any]:
    """Count distinct documents attached to this workflow via its DOCUMENT_SEARCH /
    DOCUMENT_RETRIEVE nodes (latest graph_definitions version only).

    Two things that aren't obvious from the query alone: (1) is_latest is not
    guaranteed unique per workflow_id in this table, so the true latest version is
    picked with DISTINCT ON (workflow_id) ordered by version/created_at rather than
    trusting `is_latest = true` alone; (2) a document can be reachable via more than
    one path (document_search_config.document_collections, .document_ids, and
    document_retrieve_config.collection_ids all use different key names) so the three
    paths are combined with UNION (not UNION ALL) to dedupe before counting.

    Deliberately excludes AGENT nodes' own (legacy) agent_config.document_search_enabled
    / document_collections / document_ids: verified against UAT data that zero AGENT
    nodes currently use that path, so it's not a double-count risk today, but it would
    undercount a workflow that starts relying on it instead of a DOCUMENT_SEARCH node.
    """
    sql = text(
        """
        WITH latest_defs AS (
            SELECT DISTINCT ON (workflow_id) *
            FROM graph_definitions
            WHERE is_latest = true
            ORDER BY workflow_id, version DESC, created_at DESC
        ),
        search_nodes AS (
            SELECT gd.workflow_id, node -> 'document_search_config' AS config
            FROM latest_defs gd,
                 jsonb_array_elements(gd.definition_json::jsonb -> 'nodes') AS node
            WHERE gd.workflow_id = :workflow_id
              AND node ->> 'type' = 'DOCUMENT_SEARCH'
        ),
        retrieve_nodes AS (
            SELECT gd.workflow_id, node -> 'document_retrieve_config' AS config
            FROM latest_defs gd,
                 jsonb_array_elements(gd.definition_json::jsonb -> 'nodes') AS node
            WHERE gd.workflow_id = :workflow_id
              AND node ->> 'type' = 'DOCUMENT_RETRIEVE'
              AND node -> 'document_retrieve_config' IS NOT NULL
        ),
        via_collections AS (
            SELECT DISTINCT d.id AS document_id
            FROM search_nodes sn,
                 jsonb_array_elements_text(sn.config -> 'document_collections') AS coll
            JOIN documents d ON d.collection_id = coll
        ),
        via_document_ids AS (
            SELECT DISTINCT docid::character varying AS document_id
            FROM search_nodes sn,
                 jsonb_array_elements_text(sn.config -> 'document_ids') AS docid
        ),
        via_retrieve_collections AS (
            SELECT DISTINCT d.id AS document_id
            FROM retrieve_nodes rn,
                 jsonb_array_elements_text(rn.config -> 'collection_ids') AS coll
            JOIN documents d ON d.collection_id = coll
        )
        SELECT COUNT(DISTINCT document_id)
        FROM (
            SELECT document_id FROM via_collections
            UNION SELECT document_id FROM via_document_ids
            UNION SELECT document_id FROM via_retrieve_collections
        ) combined
        """
    )
    count = db.execute(sql, {"workflow_id": workflow_id}).scalar() or 0
    return _count_metric(
        count,
        "documents",
        "graph_definitions.definition_json (DOCUMENT_SEARCH/DOCUMENT_RETRIEVE nodes)",
    )


def _compute_monthly_new_users(workflow_id: str, db: Session) -> dict[str, Any]:
    if _usage_ref_time_mode() == "max_row":
        sql = text(
            "WITH latest AS ("
            "    SELECT MAX(created_at) AS ref_time FROM chat_sessions "
            "    WHERE workflow_id = :workflow_id"
            "), "
            "first_touch AS ("
            "    SELECT user_id, MIN(created_at) AS first_session_at FROM chat_sessions "
            "    WHERE workflow_id = :workflow_id AND is_deleted = false "
            "    GROUP BY user_id"
            ") "
            "SELECT COUNT(*) FROM first_touch, latest "
            "WHERE first_session_at >= date_trunc('month', latest.ref_time)"
        )
    else:
        sql = text(
            "WITH first_touch AS ("
            "    SELECT user_id, MIN(created_at) AS first_session_at FROM chat_sessions "
            "    WHERE workflow_id = :workflow_id AND is_deleted = false "
            "    GROUP BY user_id"
            ") "
            "SELECT COUNT(*) FROM first_touch "
            "WHERE first_session_at >= date_trunc('month', now())"
        )
    count = db.execute(sql, {"workflow_id": workflow_id}).scalar() or 0
    return _count_metric(count, "users", "chat_sessions (first session this month)")


def get_workflow_metrics(workflow_id: str) -> dict[str, Any]:
    """Return the product-quality and usage metrics for one workflow.

    Caller must have already verified the requesting user has access to
    ``workflow_id`` (see ``require_workflow_access_by_id``); this function only
    checks that the workflow exists and is not soft-deleted.

    Raises:
        WorkflowNotFoundError: if the workflow is missing or soft-deleted.
    """
    with get_db() as db:
        workflow = _get_active_workflow(workflow_id, db)

        latest_run = _latest_completed_run(workflow.id, db)
        run_results = (
            db.query(EvaluationResult).filter(EvaluationResult.run_id == latest_run.id).all()
            if latest_run
            else []
        )

        faithfulness_metric = _compute_faithfulness(workflow.id, db)

        metrics = {
            "response_time": _compute_response_time(workflow.id, db),
            "confidence_score_reliability": _compute_reliability(workflow.id, db),
            "user_satisfaction": _compute_satisfaction(workflow.id, db),
            "accuracy": _compute_chat_accuracy(workflow.id, db),
            "correctness": (
                _compute_correctness(run_results)
                if latest_run
                else _compute_chat_correctness(workflow.id, db)
            ),
            "faithfulness": faithfulness_metric,
            "hallucination_rate": _compute_hallucination_rate(faithfulness_metric),
            "groundedness": _compute_groundedness(workflow.id, db),
            "total_users": _compute_total_users(workflow.id, db),
            "active_sessions": _compute_active_sessions(workflow.id, db),
            "query_responses": _compute_query_responses(workflow.id, db),
            "monthly_new_users": _compute_monthly_new_users(workflow.id, db),
            "documents_ingested": _compute_documents_ingested(workflow.id, db),
        }

        return {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "evaluation": (
                {
                    "run_id": latest_run.id,
                    "completed_at": latest_run.completed_at.isoformat()
                    if latest_run.completed_at
                    else None,
                }
                if latest_run
                else None
            ),
            "metrics": metrics,
        }
