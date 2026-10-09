"""Tests for the read-only per-workflow analytics metrics endpoint/service."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.models import (
    ChatResponseScore,
    ChatSession,
    Document,
    DocumentCollection,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
    ExecutionFeedback,
    GraphDefinition,
    GraphExecution,
    NodeExecution,
    User,
    Workflow,
)
from backend.tests.conftest import TEST_USER_CLAIMS


@pytest.fixture(autouse=True)
def _redirect_get_db_to_test_engine(monkeypatch, test_db_engine):
    """Ensure ``get_db()`` (used inside the analytics service) hits the isolated
    test database, not whatever the real ``DatabaseConfig.from_env()`` resolves to.

    ``test_client``'s engine mock (``db_module.get_engine = mock_get_engine``)
    only rebinds the *package-level* attribute; ``backend/services/database/session.py``
    imported ``get_engine`` directly at module load time, so its internal calls
    are unaffected by that monkeypatch. Without this fixture, ``get_db()`` silently
    falls back to the real configured database instead of the test one.
    """
    import backend.services.database.session as session_module

    monkeypatch.setattr(session_module, "get_engine", lambda: test_db_engine)
    session_module.reset_session_factory()
    yield
    session_module.reset_session_factory()


def _make_workflow(db, owner_user_id, name_suffix):
    workflow = Workflow(name=f"analytics-test-{name_suffix}-{uuid.uuid4().hex[:6]}", created_by_user_id=owner_user_id)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def _make_graph_execution(db, workflow_id, status, duration_seconds, *, trigger_type=None, evaluation_run_id=None):
    execution = GraphExecution(
        graph_id=workflow_id,
        graph_name="analytics-test-graph",
        graph_definition={},
        workflow_id=workflow_id,
        status=status,
        duration_seconds=duration_seconds,
        trigger_type=trigger_type,
        evaluation_run_id=evaluation_run_id,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def _make_chat_response_score(
    db,
    graph_execution_id,
    quality_score,
    *,
    reasoning="Looks good",
    judged_with_context=False,
    criteria_scores=None,
    groundedness_score=None,
):
    score = ChatResponseScore(
        graph_execution_id=graph_execution_id,
        quality_score=quality_score,
        quality_raw={"reasoning": reasoning, "criteria_scores": criteria_scores or {}},
        judged_with_context=judged_with_context,
        groundedness_score=groundedness_score,
    )
    db.add(score)
    db.commit()
    return score


def _make_node_execution(db, graph_execution_id, status, order):
    node = NodeExecution(
        graph_execution_id=graph_execution_id,
        node_id=f"node-{order}",
        node_name=f"Node {order}",
        node_type="agent",
        execution_order=order,
        status=status,
    )
    db.add(node)
    db.commit()
    return node


def _make_chat_session(db, workflow_id, user_id, *, last_message_at, is_deleted=False):
    session = ChatSession(
        title="analytics-test-session",
        workflow_id=workflow_id,
        workflow_name="analytics-test-graph",
        user_id=user_id,
        last_message_at=last_message_at,
        is_deleted=is_deleted,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def owner_user_id():
    return TEST_USER_CLAIMS["sub"]


class TestWorkflowMetricsFullyPopulated:
    """A workflow with both plain executions and a completed evaluation run."""

    def test_all_five_metrics_available(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "full")

        # Runtime trio source data: 2 completed chat executions (10s, 20s) + 1 failed (excluded)
        exec1 = _make_graph_execution(db, workflow.id, "completed", 10.0, trigger_type="chat")
        exec2 = _make_graph_execution(db, workflow.id, "completed", 20.0, trigger_type="chat")
        _make_graph_execution(db, workflow.id, "failed", None, trigger_type="chat")

        _make_node_execution(db, exec1.id, "completed", 1)
        _make_node_execution(db, exec1.id, "completed", 2)
        _make_node_execution(db, exec2.id, "failed", 1)

        db.add(ExecutionFeedback(graph_execution_id=exec1.id, rating="positive", user_id=owner_user_id))
        db.add(ExecutionFeedback(graph_execution_id=exec2.id, rating="negative", user_id=owner_user_id))
        db.commit()

        # Accuracy source data: 2 chat-triggered executions judged in place, 1 passes threshold.
        # duration_seconds=None keeps these out of the response_time average above.
        chat_exec1 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        chat_exec2 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        _make_chat_response_score(db, chat_exec1.id, 90.0)
        _make_chat_response_score(db, chat_exec2.id, 40.0)

        # Judge trio source data: one completed evaluation run with 2 results
        dataset = EvaluationDataset(name=f"analytics-ds-{uuid.uuid4().hex[:6]}", target_type="workflow")
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        run = EvaluationRun(
            name="analytics-test-run",
            target_id=workflow.id,
            target_type="workflow",
            dataset_id=dataset.id,
            workflow_id=workflow.id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        db.add(
            EvaluationResult(
                run_id=run.id,
                quality_score=90.0,
                quality_raw={"criteria_scores": {"Correctness": 95.0}},
            )
        )
        db.add(
            EvaluationResult(
                run_id=run.id,
                quality_score=40.0,
                quality_raw={"criteria_scores": {"correctness": 30.0}},
            )
        )
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            entry = response.json()

            assert entry["evaluation"]["run_id"] == run.id

            metrics = entry["metrics"]
            assert metrics["response_time"]["status"] == "available"
            assert metrics["response_time"]["value"] == pytest.approx(15.0)
            assert metrics["response_time"]["sample_size"] == 2

            assert metrics["confidence_score_reliability"]["status"] == "available"
            assert metrics["confidence_score_reliability"]["value"] == pytest.approx(200 / 3, rel=1e-3)
            assert metrics["confidence_score_reliability"]["sample_size"] == 3

            assert metrics["user_satisfaction"]["status"] == "available"
            assert metrics["user_satisfaction"]["value"] == pytest.approx(50.0)

            assert metrics["accuracy"]["status"] == "available"
            # 2 of 4: chat_exec1 (90 >= threshold), exec1 (positive feedback, no judge score);
            # chat_exec2 (40, below threshold) and exec2 (negative feedback) are the misses.
            # exec1/exec2 count via the expanded feedback-only scope even without a judge score.
            assert metrics["accuracy"]["value"] == pytest.approx(50.0)
            assert metrics["accuracy"]["sample_size"] == 4

            assert metrics["correctness"]["status"] == "available"
            assert metrics["correctness"]["value"] == pytest.approx((95.0 + 30.0) / 2)

            # Neither chat score above was judged with document context.
            assert metrics["faithfulness"]["status"] == "insufficient_data"
            assert metrics["hallucination_rate"]["status"] == "insufficient_data"
        finally:
            db.query(ChatResponseScore).filter(
                ChatResponseScore.graph_execution_id.in_([chat_exec1.id, chat_exec2.id])
            ).delete(synchronize_session=False)
            db.query(EvaluationResult).filter(EvaluationResult.run_id == run.id).delete()
            db.query(EvaluationRun).filter(EvaluationRun.id == run.id).delete()
            db.query(EvaluationDataset).filter(EvaluationDataset.id == dataset.id).delete()
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_([exec1.id, exec2.id])
            ).delete(synchronize_session=False)
            db.query(NodeExecution).filter(
                NodeExecution.graph_execution_id.in_([exec1.id, exec2.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestWorkflowMetricsNeverEvaluated:
    """A workflow that has run but never completed an evaluation."""

    def test_runtime_available_judge_insufficient(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "no-eval")
        _make_graph_execution(db, workflow.id, "completed", 5.0, trigger_type="chat")

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            entry = response.json()

            assert entry["evaluation"] is None
            metrics = entry["metrics"]
            assert metrics["response_time"]["status"] == "available"
            for key in ("accuracy", "correctness", "faithfulness", "hallucination_rate"):
                assert metrics[key]["status"] == "insufficient_data"
                assert metrics[key]["value"] is None
                assert metrics[key]["sample_size"] == 0
        finally:
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestWorkflowMetricsJudgeFailureSentinel:
    """A completed evaluation run where the judge itself errored on every result
    (e.g. missing LLM credentials) must not be reported as a real 0% accuracy score."""

    def test_all_results_judge_failed_is_insufficient_not_zero(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "judge-failed")
        dataset = EvaluationDataset(name=f"analytics-ds-{uuid.uuid4().hex[:6]}", target_type="workflow")
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        run = EvaluationRun(
            name="analytics-test-run-judge-failed",
            target_id=workflow.id,
            target_type="workflow",
            dataset_id=dataset.id,
            workflow_id=workflow.id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        for _ in range(2):
            db.add(
                EvaluationResult(
                    run_id=run.id,
                    quality_score=50.0,
                    quality_raw={
                        "reasoning": "Judge failed: Azure OpenAI requires an endpoint",
                        "criteria_scores": {},
                    },
                )
            )
        db.commit()

        # Accuracy source data: chat-triggered executions where the judge itself errored.
        chat_exec1 = _make_graph_execution(db, workflow.id, "completed", 5.0, trigger_type="chat")
        chat_exec2 = _make_graph_execution(db, workflow.id, "completed", 5.0, trigger_type="chat")
        _make_chat_response_score(
            db, chat_exec1.id, 50.0, reasoning="Judge failed: Azure OpenAI requires an endpoint"
        )
        _make_chat_response_score(
            db, chat_exec2.id, 50.0, reasoning="Judge failed: Azure OpenAI requires an endpoint"
        )

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["accuracy"]["status"] == "insufficient_data"
            assert metrics["accuracy"]["value"] is None
            assert metrics["accuracy"]["sample_size"] == 0
            assert "failed to produce judge output" in metrics["accuracy"]["note"]

            assert metrics["correctness"]["status"] == "insufficient_data"
        finally:
            db.query(ChatResponseScore).filter(
                ChatResponseScore.graph_execution_id.in_([chat_exec1.id, chat_exec2.id])
            ).delete(synchronize_session=False)
            db.query(EvaluationResult).filter(EvaluationResult.run_id == run.id).delete()
            db.query(EvaluationRun).filter(EvaluationRun.id == run.id).delete()
            db.query(EvaluationDataset).filter(EvaluationDataset.id == dataset.id).delete()
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_mixed_judge_failure_and_real_scores_excludes_only_failures(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "judge-partial-fail")

        # Accuracy source data: one genuine chat score + one where the judge itself errored.
        chat_exec1 = _make_graph_execution(db, workflow.id, "completed", 5.0, trigger_type="chat")
        chat_exec2 = _make_graph_execution(db, workflow.id, "completed", 5.0, trigger_type="chat")
        _make_chat_response_score(db, chat_exec1.id, 90.0, reasoning="Looks great")
        _make_chat_response_score(
            db, chat_exec2.id, 50.0, reasoning="Judge failed: Azure OpenAI requires an endpoint"
        )

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            # Only the genuine 90.0 result counts; the failed one is excluded, not averaged in.
            assert metrics["accuracy"]["status"] == "available"
            assert metrics["accuracy"]["sample_size"] == 1
            assert metrics["accuracy"]["value"] == pytest.approx(100.0)
        finally:
            db.query(ChatResponseScore).filter(
                ChatResponseScore.graph_execution_id.in_([chat_exec1.id, chat_exec2.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestChatAccuracyFeedbackOverride:
    """Thumbs-up/down feedback overrides the judge's quality_score for Accuracy,
    including rescuing judge-failure rows and standing in for never-judged executions."""

    def test_thumbs_up_rescues_below_threshold_score(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "acc-fb-up-rescue")
        exec1 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        _make_chat_response_score(db, exec1.id, 40.0)
        db.add(ExecutionFeedback(graph_execution_id=exec1.id, rating="positive", user_id=owner_user_id))
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["accuracy"]["status"] == "available"
            assert metrics["accuracy"]["sample_size"] == 1
            assert metrics["accuracy"]["value"] == pytest.approx(100.0)
        finally:
            db.query(ExecutionFeedback).filter(ExecutionFeedback.graph_execution_id == exec1.id).delete()
            db.query(ChatResponseScore).filter(ChatResponseScore.graph_execution_id == exec1.id).delete()
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_thumbs_down_overrides_above_threshold_score(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "acc-fb-down-override")
        exec1 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        _make_chat_response_score(db, exec1.id, 95.0)
        db.add(ExecutionFeedback(graph_execution_id=exec1.id, rating="negative", user_id=owner_user_id))
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["accuracy"]["status"] == "available"
            assert metrics["accuracy"]["sample_size"] == 1
            assert metrics["accuracy"]["value"] == pytest.approx(0.0)
        finally:
            db.query(ExecutionFeedback).filter(ExecutionFeedback.graph_execution_id == exec1.id).delete()
            db.query(ChatResponseScore).filter(ChatResponseScore.graph_execution_id == exec1.id).delete()
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_feedback_rescues_judge_failure_sentinel_row(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "acc-fb-rescue-failure")
        exec1 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        exec2 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        _make_chat_response_score(
            db, exec1.id, 50.0, reasoning="Judge failed: Azure OpenAI requires an endpoint"
        )
        _make_chat_response_score(
            db, exec2.id, 50.0, reasoning="Judge failed: Azure OpenAI requires an endpoint"
        )
        db.add(ExecutionFeedback(graph_execution_id=exec1.id, rating="positive", user_id=owner_user_id))
        db.add(ExecutionFeedback(graph_execution_id=exec2.id, rating="negative", user_id=owner_user_id))
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            # Both judge-failed rows are rescued into the sample by feedback: 1 of 2 correct.
            assert metrics["accuracy"]["status"] == "available"
            assert metrics["accuracy"]["sample_size"] == 2
            assert metrics["accuracy"]["value"] == pytest.approx(50.0)
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_([exec1.id, exec2.id])
            ).delete(synchronize_session=False)
            db.query(ChatResponseScore).filter(
                ChatResponseScore.graph_execution_id.in_([exec1.id, exec2.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_most_recent_feedback_wins_on_conflict(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "acc-fb-conflict")
        exec1 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        _make_chat_response_score(db, exec1.id, 40.0)
        earlier = datetime.now(timezone.utc) - timedelta(hours=1)
        later = datetime.now(timezone.utc)
        db.add(
            ExecutionFeedback(
                graph_execution_id=exec1.id, rating="positive", user_id=owner_user_id, created_at=earlier
            )
        )
        db.add(
            ExecutionFeedback(
                graph_execution_id=exec1.id, rating="negative", user_id="other-user", created_at=later
            )
        )
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            # The later "negative" row wins over the earlier "positive" row.
            assert metrics["accuracy"]["status"] == "available"
            assert metrics["accuracy"]["sample_size"] == 1
            assert metrics["accuracy"]["value"] == pytest.approx(0.0)
        finally:
            db.query(ExecutionFeedback).filter(ExecutionFeedback.graph_execution_id == exec1.id).delete()
            db.query(ChatResponseScore).filter(ChatResponseScore.graph_execution_id == exec1.id).delete()
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_feedback_only_execution_counts_without_any_judge_score(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "acc-fb-only")
        positive_exec = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        negative_exec = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        # Neither execution has a ChatResponseScore row (chat judging never ran for them).
        db.add(
            ExecutionFeedback(graph_execution_id=positive_exec.id, rating="positive", user_id=owner_user_id)
        )
        db.add(
            ExecutionFeedback(graph_execution_id=negative_exec.id, rating="negative", user_id=owner_user_id)
        )
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["accuracy"]["status"] == "available"
            assert metrics["accuracy"]["sample_size"] == 2
            assert metrics["accuracy"]["value"] == pytest.approx(50.0)
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_([positive_exec.id, negative_exec.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestFaithfulnessAndHallucinationRate:
    """Faithfulness/Hallucination Rate are derived from the judge's Faithfulness
    criterion, which only exists on chat responses judged WITH document context.
    Faithfulness = (responses scored >= ACCURACY_THRESHOLD) / total x 100."""

    def test_grounded_responses_ratio_faithfulness_and_derive_hallucination(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "faith-grounded")
        exec1 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        exec2 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        # >= 90 (ACCURACY_THRESHOLD) counts as factually supported.
        _make_chat_response_score(
            db, exec1.id, 88.0, judged_with_context=True, criteria_scores={"Faithfulness": 90.0}
        )
        _make_chat_response_score(
            db, exec2.id, 60.0, judged_with_context=True, criteria_scores={"Faithfulness": 70.0}
        )

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["faithfulness"]["status"] == "available"
            assert metrics["faithfulness"]["value"] == pytest.approx(50.0)
            assert metrics["faithfulness"]["sample_size"] == 2

            assert metrics["hallucination_rate"]["status"] == "available"
            assert metrics["hallucination_rate"]["value"] == pytest.approx(50.0)
            assert metrics["hallucination_rate"]["sample_size"] == 2
            assert metrics["groundedness"]["status"] == "insufficient_data"
        finally:
            db.query(ChatResponseScore).filter(
                ChatResponseScore.graph_execution_id.in_([exec1.id, exec2.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_ungrounded_responses_excluded_from_faithfulness(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "faith-mixed")
        grounded = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        ungrounded = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        _make_chat_response_score(
            db, grounded.id, 95.0, judged_with_context=True, criteria_scores={"Faithfulness": 95.0}
        )
        # No document context -> no Faithfulness criterion at all; must not be
        # counted as either 0 or 100.
        _make_chat_response_score(
            db, ungrounded.id, 90.0, judged_with_context=False, criteria_scores={"Helpfulness": 90.0}
        )

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["faithfulness"]["status"] == "available"
            assert metrics["faithfulness"]["value"] == pytest.approx(100.0)
            assert metrics["faithfulness"]["sample_size"] == 1
            assert metrics["hallucination_rate"]["value"] == pytest.approx(0.0)
            assert metrics["groundedness"]["status"] == "insufficient_data"
        finally:
            db.query(ChatResponseScore).filter(
                ChatResponseScore.graph_execution_id.in_([grounded.id, ungrounded.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_groundedness_averages_claim_coverage_scores(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "groundedness-avg")
        exec1 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        exec2 = _make_graph_execution(db, workflow.id, "completed", None, trigger_type="chat")
        _make_chat_response_score(
            db,
            exec1.id,
            95.0,
            judged_with_context=True,
            criteria_scores={"Faithfulness": 95.0},
            groundedness_score=1.0,
        )
        _make_chat_response_score(
            db,
            exec2.id,
            75.0,
            judged_with_context=True,
            criteria_scores={"Faithfulness": 70.0},
            groundedness_score=0.5,
        )

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["groundedness"]["status"] == "available"
            assert metrics["groundedness"]["value"] == pytest.approx(75.0)
            assert metrics["groundedness"]["sample_size"] == 2
            assert metrics["groundedness"]["source"] == "chat_response_scores.groundedness_score"
        finally:
            db.query(ChatResponseScore).filter(
                ChatResponseScore.graph_execution_id.in_([exec1.id, exec2.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_no_grounded_responses_is_insufficient_data(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "faith-none")
        _make_graph_execution(db, workflow.id, "completed", 1.0, trigger_type="chat")

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]
            assert metrics["faithfulness"]["status"] == "insufficient_data"
            assert metrics["hallucination_rate"]["status"] == "insufficient_data"
            assert metrics["groundedness"]["status"] == "insufficient_data"
        finally:
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestUserSatisfaction:
    """Dedicated coverage for the execution_feedback-derived satisfaction metric."""

    def test_no_feedback_is_insufficient_data(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "sat-none")
        _make_graph_execution(db, workflow.id, "completed", 1.0, trigger_type="chat")

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            metric = response.json()["metrics"]["user_satisfaction"]
            assert metric["value"] is None
            assert metric["status"] == "insufficient_data"
            assert metric["sample_size"] == 0
        finally:
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_only_positive_feedback_is_100(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "sat-positive")
        exec1 = _make_graph_execution(db, workflow.id, "completed", 1.0, trigger_type="chat")
        exec2 = _make_graph_execution(db, workflow.id, "completed", 1.0, trigger_type="chat")
        db.add(ExecutionFeedback(graph_execution_id=exec1.id, rating="positive", user_id=owner_user_id))
        db.add(ExecutionFeedback(graph_execution_id=exec2.id, rating="positive", user_id=owner_user_id))
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            metric = response.json()["metrics"]["user_satisfaction"]
            assert metric["status"] == "available"
            assert metric["value"] == pytest.approx(100.0)
            assert metric["sample_size"] == 2
            assert metric["extra"]["positive_count"] == 2
            assert metric["extra"]["negative_count"] == 0
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_([exec1.id, exec2.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_only_negative_feedback_is_0(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "sat-negative")
        exec1 = _make_graph_execution(db, workflow.id, "completed", 1.0, trigger_type="chat")
        db.add(ExecutionFeedback(graph_execution_id=exec1.id, rating="negative", user_id=owner_user_id))
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            metric = response.json()["metrics"]["user_satisfaction"]
            assert metric["status"] == "available"
            assert metric["value"] == pytest.approx(0.0)
            assert metric["sample_size"] == 1
            assert metric["extra"]["negative_count"] == 1
        finally:
            db.query(ExecutionFeedback).filter(ExecutionFeedback.graph_execution_id == exec1.id).delete()
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_mixed_feedback_eight_positive_two_negative_is_80(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "sat-mixed")
        executions = [
            _make_graph_execution(db, workflow.id, "completed", 1.0, trigger_type="chat") for _ in range(10)
        ]
        ratings = ["positive"] * 8 + ["negative"] * 2
        for execution, rating in zip(executions, ratings):
            db.add(ExecutionFeedback(graph_execution_id=execution.id, rating=rating, user_id=owner_user_id))
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            metric = response.json()["metrics"]["user_satisfaction"]
            assert metric["status"] == "available"
            assert metric["value"] == pytest.approx(80.0)
            assert metric["sample_size"] == 10
            assert metric["extra"]["positive_count"] == 8
            assert metric["extra"]["negative_count"] == 2
            assert metric["extra"]["positive_percentage"] == pytest.approx(80.0)
            assert metric["extra"]["negative_percentage"] == pytest.approx(20.0)
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_([e.id for e in executions])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_feedback_from_other_workflow_is_not_counted(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "sat-isolated")
        other_workflow = _make_workflow(db, owner_user_id, "sat-other")
        exec1 = _make_graph_execution(db, workflow.id, "completed", 1.0, trigger_type="chat")
        other_exec = _make_graph_execution(db, other_workflow.id, "completed", 1.0, trigger_type="chat")
        db.add(ExecutionFeedback(graph_execution_id=exec1.id, rating="positive", user_id=owner_user_id))
        db.add(ExecutionFeedback(graph_execution_id=other_exec.id, rating="negative", user_id=owner_user_id))
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            metric = response.json()["metrics"]["user_satisfaction"]
            assert metric["sample_size"] == 1
            assert metric["value"] == pytest.approx(100.0)
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_([exec1.id, other_exec.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(
                GraphExecution.workflow_id.in_([workflow.id, other_workflow.id])
            ).delete(synchronize_session=False)
            db.query(Workflow).filter(Workflow.id.in_([workflow.id, other_workflow.id])).delete(
                synchronize_session=False
            )
            db.commit()


class TestRuntimeTrioChatScoping:
    """Response Time / Confidence Score Reliability / User Satisfaction must only
    reflect chat traffic, not editor/API/evaluation runs."""

    def test_non_chat_execution_excluded_from_runtime_trio(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "runtime-chat-scope")

        chat_exec = _make_graph_execution(db, workflow.id, "completed", 10.0, trigger_type="chat")
        _make_node_execution(db, chat_exec.id, "completed", 1)
        db.add(ExecutionFeedback(graph_execution_id=chat_exec.id, rating="positive", user_id=owner_user_id))

        # Editor execution deliberately skews every aggregate if wrongly included:
        # a much larger duration, a failed node, and negative feedback.
        editor_exec = _make_graph_execution(db, workflow.id, "completed", 999.0, trigger_type="editor")
        _make_node_execution(db, editor_exec.id, "failed", 1)
        db.add(ExecutionFeedback(graph_execution_id=editor_exec.id, rating="negative", user_id=owner_user_id))
        db.commit()

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["response_time"]["value"] == pytest.approx(10.0)
            assert metrics["response_time"]["sample_size"] == 1

            assert metrics["confidence_score_reliability"]["value"] == pytest.approx(100.0)
            assert metrics["confidence_score_reliability"]["sample_size"] == 1

            assert metrics["user_satisfaction"]["value"] == pytest.approx(100.0)
            assert metrics["user_satisfaction"]["sample_size"] == 1
        finally:
            db.query(ExecutionFeedback).filter(
                ExecutionFeedback.graph_execution_id.in_([chat_exec.id, editor_exec.id])
            ).delete(synchronize_session=False)
            db.query(NodeExecution).filter(
                NodeExecution.graph_execution_id.in_([chat_exec.id, editor_exec.id])
            ).delete(synchronize_session=False)
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


class TestWorkflowMetricsAccess:
    """Workflows the caller has no access to must be forbidden, not returned."""

    def test_non_owned_workflow_is_forbidden(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        other_user_id = f"other-user-{uuid.uuid4().hex[:6]}"
        db.add(User(id=other_user_id, email=f"{other_user_id}@example.test", name="Other User"))
        db.commit()
        other_workflow = _make_workflow(db, other_user_id, "not-mine")

        try:
            response = test_client.get(f"/api/analytics/workflows/{other_workflow.id}/metrics")
            assert response.status_code == 403
        finally:
            db.query(Workflow).filter(Workflow.id == other_workflow.id).delete()
            db.query(User).filter(User.id == other_user_id).delete()
            db.commit()

    def test_nonexistent_workflow_returns_404(self, test_client):
        response = test_client.get(f"/api/analytics/workflows/{uuid.uuid4()}/metrics")
        assert response.status_code == 404

    def test_malformed_workflow_id_returns_400(self, test_client):
        response = test_client.get("/api/analytics/workflows/not-a-uuid/metrics")
        assert response.status_code == 400


class TestWorkflowUsageMetrics:
    """The 4 chat/execution usage counts folded into the same payload."""

    def test_usage_counts_now_mode(self, test_client, test_db_session, owner_user_id, monkeypatch):
        monkeypatch.setenv("ANALYTICS_USAGE_REF_TIME", "now")
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "usage-now")
        now = datetime.now(timezone.utc)
        user_a = f"user-a-{uuid.uuid4().hex[:6]}"
        user_b = f"user-b-{uuid.uuid4().hex[:6]}"
        user_c = f"user-c-{uuid.uuid4().hex[:6]}"

        # user_a: one recent + one stale session (distinct user counted once)
        _make_chat_session(db, workflow.id, user_a, last_message_at=now)
        _make_chat_session(db, workflow.id, user_a, last_message_at=now - timedelta(hours=48))
        # user_b: one recent session
        _make_chat_session(db, workflow.id, user_b, last_message_at=now)
        # user_c: deleted session -> excluded everywhere
        _make_chat_session(db, workflow.id, user_c, last_message_at=now, is_deleted=True)

        _make_graph_execution(db, workflow.id, "completed", 1.0, trigger_type="chat")
        _make_graph_execution(db, workflow.id, "failed", None, trigger_type="chat")
        # Non-chat executions (editor/API/evaluation runs) must NOT count as query responses.
        _make_graph_execution(db, workflow.id, "completed", 2.0, trigger_type="editor")

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]

            assert metrics["total_users"]["status"] == "available"
            assert metrics["total_users"]["value"] == pytest.approx(2.0)
            # Only the two recent, non-deleted sessions fall inside the 24h window.
            assert metrics["active_sessions"]["value"] == pytest.approx(2.0)
            assert metrics["query_responses"]["value"] == pytest.approx(2.0)
            assert metrics["monthly_new_users"]["value"] == pytest.approx(2.0)
        finally:
            db.query(ChatSession).filter(ChatSession.workflow_id == workflow.id).delete()
            db.query(GraphExecution).filter(GraphExecution.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_zero_counts_are_available(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "usage-empty")

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]
            for key in ("total_users", "active_sessions", "query_responses", "monthly_new_users"):
                assert metrics[key]["status"] == "available"
                assert metrics[key]["value"] == pytest.approx(0.0)
        finally:
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_active_sessions_max_row_mode(self, test_client, test_db_session, owner_user_id, monkeypatch):
        monkeypatch.setenv("ANALYTICS_USAGE_REF_TIME", "max_row")
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "usage-maxrow")
        # All timestamps are well in the past; only max_row mode (ref_time = latest
        # last_message_at) counts anything as "active".
        base = datetime.now(timezone.utc) - timedelta(days=100)
        _make_chat_session(db, workflow.id, f"user-{uuid.uuid4().hex[:6]}", last_message_at=base)
        _make_chat_session(
            db, workflow.id, f"user-{uuid.uuid4().hex[:6]}", last_message_at=base - timedelta(hours=12)
        )
        _make_chat_session(
            db, workflow.id, f"user-{uuid.uuid4().hex[:6]}", last_message_at=base - timedelta(hours=48)
        )

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]
            # base and base-12h are within 24h of the latest row (base); base-48h is not.
            assert metrics["active_sessions"]["value"] == pytest.approx(2.0)
        finally:
            db.query(ChatSession).filter(ChatSession.workflow_id == workflow.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()


def _make_collection(db, name_suffix):
    collection = DocumentCollection(name=f"analytics-coll-{name_suffix}-{uuid.uuid4().hex[:6]}")
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


def _make_document(db, collection_id, name_suffix):
    document = Document(collection_id=collection_id, name=f"analytics-doc-{name_suffix}-{uuid.uuid4().hex[:6]}")
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def _make_graph_definition(db, workflow_id, nodes, *, version, is_latest, created_at=None):
    definition = GraphDefinition(
        name=f"analytics-def-{uuid.uuid4().hex[:6]}",
        workflow_id=workflow_id,
        definition_json={"nodes": nodes},
        version=version,
        is_latest=is_latest,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return definition


class TestWorkflowDocumentsIngested:
    """documents_ingested counts documents reachable via DOCUMENT_SEARCH/DOCUMENT_RETRIEVE
    nodes on the latest graph_definitions version, deduped across paths."""

    def test_no_document_nodes_returns_zero(self, test_client, test_db_session, owner_user_id):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "docs-none")
        definition = _make_graph_definition(
            db, workflow.id, [{"type": "AGENT", "data": {}}], version=1, is_latest=True
        )

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]
            assert metrics["documents_ingested"]["status"] == "available"
            assert metrics["documents_ingested"]["value"] == pytest.approx(0.0)
        finally:
            db.query(GraphDefinition).filter(GraphDefinition.id == definition.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_dedupes_document_reachable_via_multiple_paths(
        self, test_client, test_db_session, owner_user_id
    ):
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "docs-dedup")
        shared_collection = _make_collection(db, "shared")
        only_search_collection = _make_collection(db, "search-only")

        shared_doc = _make_document(db, shared_collection.id, "shared")
        search_only_doc = _make_document(db, only_search_collection.id, "search-only")
        direct_id_doc = _make_document(db, only_search_collection.id, "direct-id")

        nodes = [
            {
                "type": "DOCUMENT_SEARCH",
                "data": {},
                "document_search_config": {
                    "document_collections": [shared_collection.id, only_search_collection.id],
                    "document_ids": [direct_id_doc.id],
                },
            },
            {
                "type": "DOCUMENT_RETRIEVE",
                "data": {},
                # Same collection as DOCUMENT_SEARCH above -> shared_doc must not be double-counted.
                "document_retrieve_config": {"collection_ids": [shared_collection.id]},
            },
            {"type": "DOCUMENT_RETRIEVE", "data": {}, "document_retrieve_config": None},
        ]
        definition = _make_graph_definition(db, workflow.id, nodes, version=1, is_latest=True)

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]
            # shared_doc (via both paths, counted once) + search_only_doc + direct_id_doc = 3
            assert metrics["documents_ingested"]["status"] == "available"
            assert metrics["documents_ingested"]["value"] == pytest.approx(3.0)
        finally:
            db.query(GraphDefinition).filter(GraphDefinition.id == definition.id).delete()
            db.query(Document).filter(
                Document.id.in_([shared_doc.id, search_only_doc.id, direct_id_doc.id])
            ).delete(synchronize_session=False)
            db.query(DocumentCollection).filter(
                DocumentCollection.id.in_([shared_collection.id, only_search_collection.id])
            ).delete(synchronize_session=False)
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()

    def test_picks_true_latest_when_multiple_is_latest_rows_exist(
        self, test_client, test_db_session, owner_user_id
    ):
        """Regression guard for the documented UAT caveat: is_latest=true is not
        guaranteed unique per workflow, so version/created_at must break the tie."""
        db = test_db_session
        workflow = _make_workflow(db, owner_user_id, "docs-dup-latest")
        collection = _make_collection(db, "dup-latest")
        doc = _make_document(db, collection.id, "dup-latest")

        stale_nodes = [
            {
                "type": "DOCUMENT_SEARCH",
                "data": {},
                "document_search_config": {"document_collections": [collection.id], "document_ids": []},
            }
        ]
        true_latest_nodes = [{"type": "AGENT", "data": {}}]

        now = datetime.now(timezone.utc)
        stale_definition = _make_graph_definition(
            db, workflow.id, stale_nodes, version=1, is_latest=True, created_at=now - timedelta(days=1)
        )
        true_latest_definition = _make_graph_definition(
            db, workflow.id, true_latest_nodes, version=2, is_latest=True, created_at=now
        )

        try:
            response = test_client.get(f"/api/analytics/workflows/{workflow.id}/metrics")
            assert response.status_code == 200
            metrics = response.json()["metrics"]
            # If the stale (version=1) row were mistakenly used, this would be 1, not 0.
            assert metrics["documents_ingested"]["status"] == "available"
            assert metrics["documents_ingested"]["value"] == pytest.approx(0.0)
        finally:
            db.query(GraphDefinition).filter(
                GraphDefinition.id.in_([stale_definition.id, true_latest_definition.id])
            ).delete(synchronize_session=False)
            db.query(Document).filter(Document.id == doc.id).delete()
            db.query(DocumentCollection).filter(DocumentCollection.id == collection.id).delete()
            db.query(Workflow).filter(Workflow.id == workflow.id).delete()
            db.commit()
