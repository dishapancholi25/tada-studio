"""Evaluation result model."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class EvaluationResult(Base, UUIDPrimaryKeyMixin):
    """Model for storing individual evaluation results per test case.

    Each result captures scoring across multiple pillars for a single
    test case execution within an evaluation run.

    Attributes:
        id: Unique result identifier (UUID).
        run_id: Parent evaluation run ID.
        test_case_id: Associated test case ID.
        graph_execution_id: Associated graph execution ID.
        composite_score: Overall composite score.
        cost_score: Cost pillar score.
        quality_score: Quality pillar score.
        reliability_score: Reliability pillar score.
        latency_score: Latency pillar score.
        cost_raw: Raw cost metrics JSON.
        latency_raw: Raw latency metrics JSON.
        quality_raw: Raw quality metrics JSON.
        reliability_raw: Raw reliability metrics JSON.
        guardrail_signals: Guardrail evaluation signals JSON.
        external_eval_raw: Raw external evaluation data JSON.
        trace_reference: Reference to execution trace JSON.
        created_at: Record creation timestamp.
    """

    __tablename__ = "evaluation_results"

    run_id = Column(
        String,
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id = Column(
        String,
        ForeignKey("evaluation_test_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    graph_execution_id = Column(
        String,
        ForeignKey("graph_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Scores
    composite_score = Column(Float, nullable=True)
    cost_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    reliability_score = Column(Float, nullable=True)
    latency_score = Column(Float, nullable=True)

    # Raw metrics
    cost_raw = Column(JSON, nullable=True)
    latency_raw = Column(JSON, nullable=True)
    quality_raw = Column(JSON, nullable=True)
    reliability_raw = Column(JSON, nullable=True)
    guardrail_signals = Column(JSON, nullable=True)
    external_eval_raw = Column(JSON, nullable=True)
    trace_reference = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    run = relationship("EvaluationRun", back_populates="results")
    test_case = relationship("EvaluationTestCase")
    graph_execution = relationship("GraphExecution")
