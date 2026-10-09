"""Chat response score model."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class ChatResponseScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """LLM-judge score for a single chat-triggered execution's response.

    Populated best-effort right after a chat execution finalizes (see
    ``backend.services.evaluation.chat_scoring``), independently of the
    standalone/bulk evaluation module. This is the source for the dashboard
    Accuracy metric, which must reflect real chat traffic rather than
    evaluation-run results.

    Attributes:
        id: Unique score identifier (UUID).
        graph_execution_id: The chat-triggered execution that was judged (unique).
        quality_score: Judge's overall 0-100 quality score.
        quality_raw: Full judge output (reasoning, criteria_scores).
        judged_with_context: Whether retrieved DOCUMENT_SEARCH context was supplied
            to the judge (groundedness scoring) vs. reference-free scoring.
        groundedness_score: Judge's claim-coverage groundedness score (0.0-1.0),
            populated only when judged_with_context is True.
        groundedness_raw: Full groundedness judge output (total_claims,
            supported_claims, claim_breakdown, groundedness_reason).
        created_at: Record creation timestamp.
    """

    __tablename__ = "chat_response_scores"

    graph_execution_id = Column(
        String,
        ForeignKey("graph_executions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    quality_score = Column(Float, nullable=True)
    quality_raw = Column(JSON, nullable=True)
    judged_with_context = Column(Boolean, nullable=True)
    groundedness_score = Column(Float, nullable=True)
    groundedness_raw = Column(JSON, nullable=True)

    graph_execution = relationship("GraphExecution")
