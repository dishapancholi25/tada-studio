"""Best-effort LLM-judge scoring of real chat responses.

Independent of the standalone/bulk evaluation module (``orchestrator.py``,
which re-executes the graph against authored test cases): this scores the
*actual* response a chat-triggered execution already produced, in place.
Three context sources are assembled for the judge: the user's own chat
message (so it can tell whether the response is relevant, rather than
grading it in a vacuum), the responding agent's own ``system_prompt``/persona
(so a deliberately branded or role-specific reply isn't penalized against a
generic "helpful assistant" baseline), and retrieved DOCUMENT_SEARCH/
DOCUMENT_RETRIEVE context for groundedness/faithfulness judging when
available, falling back to conversational criteria otherwise (chat turns have
no pre-authored task/expected output). Results back the dashboard Accuracy
metric via ``ChatResponseScore``, scoped separately from evaluation runs.
"""

import os
from typing import TYPE_CHECKING, Any, Optional

from backend.models import ChatResponseScore, NodeExecution, Workflow
from backend.models.workflow import NodeType
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.evaluation.judge import EvaluationJudge

# Keeps a long system_prompt from crowding out the actual response/context
# in the judge's prompt.
MAX_PERSONA_CHARS = 2000

if TYPE_CHECKING:
    from backend.models import GraphData

logger = get_logger("evaluation.chat_scoring")

# Off by default: judging every chat turn adds an LLM call (cost + latency)
# on top of the workflow's own response, so this must be an explicit opt-in.
CHAT_JUDGE_ENABLED = (
    os.getenv("ANALYTICS_CHAT_JUDGE_ENABLED", "false").strip().lower() == "true"
)

_DOCUMENT_NODE_TYPES = (NodeType.DOCUMENT_SEARCH, NodeType.DOCUMENT_RETRIEVE)
_DOCUMENT_OUTPUT_KEYS = ("raw", "result")

# Steers the judge toward groundedness when DOCUMENT_SEARCH context is available,
# instead of its default generic coherence/relevance criteria.
_GROUNDED_CRITERIA = {
    "Faithfulness": (
        "Does the response only make claims supported by the provided context, "
        "with no fabricated or unsupported information?"
    ),
    "Relevance": "Does the response address the user's question using the provided context?",
}

# EvaluationJudge's built-in defaults assume a "task" (e.g. bulk test-case grading),
# which unfairly penalizes normal conversational turns (greetings, clarifying
# questions, short acknowledgements) that have no task to follow. Chat turns are
# judged against the user's actual message instead, so criteria stay conversational.
_CHAT_CRITERIA = {
    "Helpfulness": (
        "Does the response appropriately and naturally address the user's message, "
        "consistent with the agent's defined role/persona provided in the context "
        "(if any)? A response that reflects a specific configured persona should not "
        "be judged against a generic assistant's expected behavior."
    ),
    "Coherence": "Is the response clear, polite, and well-structured?",
}


def _extract_document_context(
    graph: "GraphData", node_outputs: dict[str, Any], execution_id: str
) -> Optional[str]:
    """Collect this execution's document search/retrieve output, if any.

    Checks in-memory ``node_outputs`` first (covers DOCUMENT_SEARCH/
    DOCUMENT_RETRIEVE used as standalone flow nodes), then falls back to the
    NodeExecution DB rows for this execution. The fallback matters because
    when document search/retrieve is bound as an AGENT tool call (the common
    case), its result is consumed inside the agent's own tool loop and never
    lands in state.node_outputs -- only in node_executions.output_data.
    """
    doc_node_ids = {n.uniq_id for n in graph.nodes if n.type in _DOCUMENT_NODE_TYPES}

    def _pick_text(output_data: Any) -> Optional[str]:
        if not isinstance(output_data, dict):
            return None
        for key in _DOCUMENT_OUTPUT_KEYS:
            value = output_data.get(key)
            if value:
                return str(value)
        return None

    parts = [
        text
        for node_id in doc_node_ids
        if (text := _pick_text(node_outputs.get(node_id)))
    ]
    if parts:
        return "\n\n".join(parts)

    with get_db() as db:
        rows = (
            db.query(NodeExecution)
            .filter(
                NodeExecution.graph_execution_id == execution_id,
                NodeExecution.node_type.in_([t.value for t in _DOCUMENT_NODE_TYPES]),
                NodeExecution.status == "completed",
            )
            .all()
        )
        parts = [text for row in rows if (text := _pick_text(row.output_data))]

    return "\n\n".join(parts) if parts else None


def _extract_agent_persona(
    graph: "GraphData", node_outputs: dict[str, Any]
) -> Optional[str]:
    """Return the responding agent's own system_prompt, if resolvable.

    Assumes the last entry in ``node_outputs`` (insertion-ordered) is the
    AGENT node that produced the final response -- same assumption
    ``FinalOutputExtractor`` makes for the response text itself. Without this,
    the judge has no way to know a reply is intentionally persona-specific
    (e.g. a branded self-introduction) and grades it against a generic
    "helpful assistant" baseline instead.
    """
    if not node_outputs:
        return None

    last_node_id = list(node_outputs.keys())[-1]
    node = next((n for n in graph.nodes if n.uniq_id == last_node_id), None)
    if not node or node.type != NodeType.AGENT or not node.agent_config:
        return None

    system_prompt = node.agent_config.system_prompt
    if not system_prompt:
        return None

    return system_prompt[:MAX_PERSONA_CHARS]


def _resolve_judge_model_config(workflow_id: Optional[str]) -> Optional[dict[str, Any]]:
    """Reuse the workflow's auto-eval judge model, if configured, for consistency."""
    if not workflow_id:
        return None
    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if workflow and isinstance(workflow.auto_eval_config, dict):
            return workflow.auto_eval_config.get("judge_model_config")
    return None


async def score_chat_response(
    graph: "GraphData",
    db_execution_id: Any,
    final_result: dict[str, Any],
    user_message: str = "",
) -> None:
    """Judge a chat-triggered execution's response in place and store the score.

    Best-effort: any failure (LLM unavailable, judge parse error, etc.) is
    logged and swallowed so it can never affect the chat response itself.
    """
    if not CHAT_JUDGE_ENABLED:
        return

    execution_id = str(db_execution_id)
    response_text = final_result.get("final_output")
    if not response_text or not isinstance(response_text, str):
        logger.warning(
            f"Skipping chat response judging for execution {execution_id}: "
            "no usable final_output string."
        )
        return

    try:
        node_outputs = final_result.get("node_outputs") or {}
        doc_context = _extract_document_context(graph, node_outputs, execution_id)
        agent_persona = _extract_agent_persona(graph, node_outputs)
        judge_model_config = _resolve_judge_model_config(graph.workflow_id)
        judge_criteria = _GROUNDED_CRITERIA if doc_context else _CHAT_CRITERIA

        # Without the user's own message, the judge has no way to tell whether
        # the response is relevant (e.g. "Hello!" looks unprompted/off-topic on
        # its own, even though it's the correct reply to "hi"). Without the
        # agent's own persona, the judge also can't tell a deliberately
        # branded/role-specific reply from an oddly verbose generic one.
        context_parts = []
        if user_message:
            context_parts.append(f"User message: {user_message}")
        if agent_persona:
            context_parts.append(f"Agent's defined role/system prompt:\n{agent_persona}")
        if doc_context:
            context_parts.append(f"Retrieved document context:\n{doc_context}")
        context_text = "\n\n".join(context_parts) or None

        judge_result = await EvaluationJudge().judge(
            actual_output=response_text,
            expected_output=None,
            judge_criteria=judge_criteria,
            context_description=context_text,
            judge_model_config=judge_model_config,
            include_groundedness=doc_context is not None,
        )
        logger.info(
            "Chat response judged for execution %s: has_doc_context=%s quality_score=%s groundedness_score=%s",
            execution_id,
            doc_context is not None,
            judge_result.quality_score,
            judge_result.groundedness_score,
        )

        quality_raw = {
            "reasoning": judge_result.reasoning,
            "criteria_scores": judge_result.criteria_scores,
        }
        groundedness_raw = (
            {
                "total_claims": judge_result.total_claims,
                "supported_claims": judge_result.supported_claims,
                "claim_breakdown": judge_result.claim_breakdown,
                "groundedness_reason": judge_result.groundedness_reason,
            }
            if doc_context is not None
            else None
        )

        with get_db() as db:
            existing = (
                db.query(ChatResponseScore)
                .filter(ChatResponseScore.graph_execution_id == execution_id)
                .first()
            )
            if existing:
                existing.quality_score = judge_result.quality_score
                existing.quality_raw = quality_raw
                existing.judged_with_context = doc_context is not None
                existing.groundedness_score = judge_result.groundedness_score
                existing.groundedness_raw = groundedness_raw
            else:
                db.add(
                    ChatResponseScore(
                        graph_execution_id=execution_id,
                        quality_score=judge_result.quality_score,
                        quality_raw=quality_raw,
                        judged_with_context=doc_context is not None,
                        groundedness_score=judge_result.groundedness_score,
                        groundedness_raw=groundedness_raw,
                    )
                )
            logger.info(
                "Persisted chat response score for execution %s: judged_with_context=%s groundedness_score=%s",
                execution_id,
                doc_context is not None,
                judge_result.groundedness_score,
            )
    except Exception as exc:
        logger.warning(
            f"Chat response judging failed for execution {execution_id} (non-fatal): {exc}"
        )
