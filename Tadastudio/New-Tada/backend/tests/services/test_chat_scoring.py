"""Tests for backend.services.evaluation.chat_scoring.

Covers the judge context assembly (user message, agent persona, retrieved
document context) that feeds ``score_chat_response``'s Accuracy judging.
"""

from unittest.mock import AsyncMock, patch

import pytest

from backend.models.workflow import AgentConfig, EnhancedNodeData, GraphData, NodeType
from backend.services.evaluation.chat_scoring import (
    MAX_PERSONA_CHARS,
    _extract_agent_persona,
    score_chat_response,
)
from backend.services.evaluation.judge import JudgeResult


def _agent_node(uniq_id: str, system_prompt: str = "") -> EnhancedNodeData:
    return EnhancedNodeData(
        uniq_id=uniq_id,
        name="Compliance Specialist Agent",
        type=NodeType.AGENT,
        agent_config=AgentConfig(system_prompt=system_prompt),
    )


class TestExtractAgentPersona:
    def test_returns_last_agent_nodes_system_prompt(self):
        graph = GraphData(
            nodes=[
                _agent_node("agent_1", "You are Agent One."),
                _agent_node("agent_2", "You are the Compliance Specialist Agent."),
            ]
        )
        node_outputs = {"agent_1": {"raw": "..."}, "agent_2": {"raw": "..."}}

        assert (
            _extract_agent_persona(graph, node_outputs)
            == "You are the Compliance Specialist Agent."
        )

    def test_no_node_outputs_returns_none(self):
        graph = GraphData(nodes=[_agent_node("agent_1", "You are Agent One.")])

        assert _extract_agent_persona(graph, {}) is None

    def test_last_node_not_found_in_graph_returns_none(self):
        graph = GraphData(nodes=[_agent_node("agent_1", "You are Agent One.")])

        assert _extract_agent_persona(graph, {"unknown_node": {}}) is None

    def test_last_node_not_an_agent_returns_none(self):
        graph = GraphData(
            nodes=[EnhancedNodeData(uniq_id="end_1", name="End", type=NodeType.END)]
        )

        assert _extract_agent_persona(graph, {"end_1": {}}) is None

    def test_agent_with_empty_system_prompt_returns_none(self):
        graph = GraphData(nodes=[_agent_node("agent_1", "")])

        assert _extract_agent_persona(graph, {"agent_1": {}}) is None

    def test_truncates_long_system_prompt(self):
        long_prompt = "x" * (MAX_PERSONA_CHARS + 500)
        graph = GraphData(nodes=[_agent_node("agent_1", long_prompt)])

        result = _extract_agent_persona(graph, {"agent_1": {}})

        assert result == long_prompt[:MAX_PERSONA_CHARS]


async def _run_score_chat_response(graph, final_result, user_message="", judge_result=None):
    judge_result = judge_result or JudgeResult(
        quality_score=90.0, reasoning="ok", criteria_scores={"Helpfulness": 90.0}
    )
    mock_judge = AsyncMock(return_value=judge_result)

    with (
        patch("backend.services.evaluation.chat_scoring.CHAT_JUDGE_ENABLED", True),
        patch(
            "backend.services.evaluation.chat_scoring.EvaluationJudge"
        ) as mock_judge_cls,
        patch("backend.services.evaluation.chat_scoring.get_db") as mock_get_db,
    ):
        mock_judge_cls.return_value.judge = mock_judge
        db_session = mock_get_db.return_value.__enter__.return_value
        # `.first()` backs the existing-ChatResponseScore/workflow lookups;
        # `.all()` backs _extract_document_context's NodeExecution fallback.
        db_session.query.return_value.filter.return_value.first.return_value = None
        db_session.query.return_value.filter.return_value.all.return_value = []

        await score_chat_response(graph, "exec-1", final_result, user_message)

    return mock_judge, db_session


class TestScoreChatResponseContext:
    """Verifies the judge receives the agent's persona in its context."""

    async def _run(self, graph, final_result, user_message="", judge_result=None):
        return await _run_score_chat_response(graph, final_result, user_message, judge_result)

    async def test_persona_included_in_judge_context(self):
        graph = GraphData(
            nodes=[
                _agent_node(
                    "agent_1",
                    "You are the Compliance Specialist Agent. Greet users formally.",
                )
            ]
        )
        final_result = {
            "final_output": "Hello, I am the Compliance Specialist Agent.",
            "node_outputs": {"agent_1": {"raw": "Hello, I am the Compliance Specialist Agent."}},
        }

        mock_judge, _ = await self._run(graph, final_result, user_message="Hi")

        context = mock_judge.call_args.kwargs["context_description"]
        assert "User message: Hi" in context
        assert "Compliance Specialist Agent. Greet users formally." in context

    async def test_no_agent_node_omits_persona_section(self):
        graph = GraphData(nodes=[])
        final_result = {
            "final_output": "Hello!",
            "node_outputs": {},
        }

        mock_judge, _ = await self._run(graph, final_result, user_message="Hi")

        context = mock_judge.call_args.kwargs["context_description"]
        assert "Agent's defined role" not in context


class TestScoreChatResponseGroundedness:
    """Verifies groundedness is requested/persisted only when doc context exists."""

    async def _run(self, graph, final_result, user_message="", judge_result=None):
        return await _run_score_chat_response(graph, final_result, user_message, judge_result)

    async def test_include_groundedness_true_and_persisted_with_doc_context(self):
        graph = GraphData(
            nodes=[
                EnhancedNodeData(
                    uniq_id="doc_1", name="Doc Search", type=NodeType.DOCUMENT_SEARCH
                )
            ]
        )
        final_result = {
            "final_output": "Paris is the capital of France.",
            "node_outputs": {"doc_1": {"raw": "Paris is the capital of France."}},
        }
        judge_result = JudgeResult(
            quality_score=95.0,
            reasoning="ok",
            criteria_scores={"Faithfulness": 95.0},
            total_claims=1,
            supported_claims=1,
            groundedness_score=1.0,
            claim_breakdown=[
                {"claim": "Paris is the capital of France.", "label": "Supported"}
            ],
            groundedness_reason="All claims supported.",
        )

        mock_judge, db_session = await self._run(
            graph,
            final_result,
            user_message="What is the capital of France?",
            judge_result=judge_result,
        )

        assert mock_judge.call_args.kwargs["include_groundedness"] is True

        added = db_session.add.call_args.args[0]
        assert added.groundedness_score == 1.0
        assert added.groundedness_raw == {
            "total_claims": 1,
            "supported_claims": 1,
            "claim_breakdown": judge_result.claim_breakdown,
            "groundedness_reason": "All claims supported.",
        }

    async def test_include_groundedness_false_and_null_without_doc_context(self):
        graph = GraphData(nodes=[])
        final_result = {"final_output": "Hello!", "node_outputs": {}}

        mock_judge, db_session = await self._run(
            graph, final_result, user_message="Hi"
        )

        assert mock_judge.call_args.kwargs["include_groundedness"] is False

        added = db_session.add.call_args.args[0]
        assert added.groundedness_score is None
        assert added.groundedness_raw is None
