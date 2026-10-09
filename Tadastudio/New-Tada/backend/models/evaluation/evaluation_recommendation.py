"""Evaluation recommendation model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class EvaluationRecommendation(Base, UUIDPrimaryKeyMixin):
    """Model for storing evaluation-generated recommendations.

    Recommendations are generated after an evaluation run completes,
    suggesting improvements based on the results.

    Attributes:
        id: Unique recommendation identifier (UUID).
        run_id: Parent evaluation run ID.
        target_node_id: Optional specific node the recommendation targets.
        recommendation_type: Type of recommendation.
        risk_tier: Risk level (low, medium, high, critical).
        title: Short recommendation title.
        rationale: Detailed explanation.
        expected_impact: Expected improvement metrics JSON.
        proposed_change: Proposed configuration/code change JSON.
        status: Recommendation status (pending, applied, dismissed).
        applied_at: When the recommendation was applied.
        applied_by_user_id: User who applied the recommendation.
        applied_version: Graph version number the change was applied to.
        applied_graph_definition_id: Graph definition ID of the applied version.
        created_at: Record creation timestamp.
    """

    __tablename__ = "evaluation_recommendations"

    run_id = Column(
        String,
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id = Column(String, nullable=True)
    recommendation_type = Column(String, nullable=False)
    risk_tier = Column(String, nullable=False)
    title = Column(String, nullable=False)
    rationale = Column(Text, nullable=True)
    expected_impact = Column(JSON, nullable=True)
    proposed_change = Column(JSON, nullable=True)
    status = Column(String, default="pending", nullable=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    applied_by_user_id = Column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    applied_version = Column(Integer, nullable=True)
    applied_graph_definition_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    run = relationship("EvaluationRun", back_populates="recommendations")
    applied_by_user = relationship("User", foreign_keys=[applied_by_user_id])
