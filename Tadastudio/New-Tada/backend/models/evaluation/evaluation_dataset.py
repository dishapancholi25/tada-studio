"""Evaluation dataset model."""

from sqlalchemy import Column, ForeignKey, Index, JSON, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class EvaluationDataset(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Model for storing evaluation datasets.

    A dataset groups test cases used to evaluate a workflow or agent.

    Attributes:
        id: Unique dataset identifier (UUID).
        name: Human-readable dataset name.
        description: Optional longer description.
        target_type: Type of target being evaluated (e.g. "workflow", "agent").
        created_by_user_id: User who created this dataset.
        generation_method: How the dataset was generated ("manual", "ai", etc.).
        generation_prompt: Prompt used for AI-generated datasets.
        baseline_run_id: Optional reference to a baseline evaluation run.
        is_deleted: Soft-delete flag.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "evaluation_datasets"
    __table_args__ = (
        Index(
            "uq_eval_dataset_name_user_active",
            "name",
            "created_by_user_id",
            unique=True,
            postgresql_where=Column("is_deleted") == False,  # noqa: E712
        ),
    )

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=True, index=True)
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tags = Column(JSON, nullable=True)
    created_by_user_id = Column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    generation_method = Column(
        String, nullable=False, default="manual", server_default="manual"
    )
    generation_prompt = Column(Text, nullable=True)
    baseline_run_id = Column(
        String,
        ForeignKey(
            "evaluation_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_eval_dataset_baseline_run",
        ),
        nullable=True,
        index=True,
    )
    visible_to_groups = Column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    # Relationships
    test_cases = relationship(
        "EvaluationTestCase", back_populates="dataset", cascade="all, delete-orphan"
    )
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    workflow = relationship("Workflow", foreign_keys=[workflow_id])
    baseline_run = relationship("EvaluationRun", foreign_keys=[baseline_run_id])
    runs = relationship(
        "EvaluationRun",
        back_populates="dataset",
        foreign_keys="EvaluationRun.dataset_id",
    )
