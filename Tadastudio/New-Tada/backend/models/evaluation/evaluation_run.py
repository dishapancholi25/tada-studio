"""Evaluation run model."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class EvaluationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing evaluation run metadata and results.

    An evaluation run executes a dataset's test cases against a target
    workflow/agent and collects scoring results.

    Attributes:
        id: Unique run identifier (UUID).
        name: Human-readable run name.
        target_id: ID of the target being evaluated.
        target_type: Type of target (e.g. "workflow", "agent").
        dataset_id: Associated evaluation dataset.
        concurrency_limit: Max parallel test case executions.
        case_timeout_seconds: Per-case timeout.
        max_case_retries: Max retries per failed case.
        status: Run status (pending, running, completed, failed).
        completed_cases: Number of completed test cases.
        failed_cases: Number of failed test cases.
        total_cases: Total test cases in this run.
        regression_flag: Whether regression was detected.
        regression_severity: Severity level if regression detected.
        regression_ack_required: Whether user acknowledgement is required before proceeding (prod+moderate/severe).
        trigger: How the run was triggered (manual, ci, scheduled).
        trigger_revision: Git/version revision that triggered the run.
        is_latest_revision: Whether this is the latest revision run.
        trigger_delivery_status: Status of trigger notification delivery.
        pillar_weights: JSON weights for scoring pillars.
        judge_model_config: Configuration for the judge model.
        judge_output_policy: Controls which part of execution output the judge evaluates.
        external_integration_config: Config for external evaluation integrations.
        external_eval_summary: Summary from external evaluations.
        ab_peer_run_id: Self-referential FK for A/B comparison runs.
        composite_score: Overall composite score.
        cost_score: Cost pillar score.
        quality_score: Quality pillar score.
        reliability_score: Reliability pillar score.
        latency_score: Latency pillar score.
        summary_stats: Aggregated statistics JSON.
        environment: Target environment (dev, staging, prod).
        workflow_id: Associated workflow.
        triggered_by_user_id: User who triggered the run.
        started_at: When execution started.
        completed_at: When execution completed.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "evaluation_runs"

    # Core identification
    name = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)

    # Dataset link
    dataset_id = Column(
        String,
        ForeignKey("evaluation_datasets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Execution configuration
    concurrency_limit = Column(Integer, default=5)
    case_timeout_seconds = Column(Integer, nullable=True)
    max_case_retries = Column(Integer, nullable=True)

    # Status tracking
    status = Column(String, default="pending")
    completed_cases = Column(Integer, default=0)
    failed_cases = Column(Integer, default=0)
    total_cases = Column(Integer, nullable=True)

    # Regression detection
    regression_flag = Column(Boolean, default=False)
    regression_severity = Column(String, nullable=True)
    regression_ack_required = Column(Boolean, default=False)

    # Trigger metadata
    trigger = Column(String, default="manual")
    trigger_revision = Column(String, nullable=True)
    is_latest_revision = Column(Boolean, default=False)
    trigger_delivery_status = Column(String, nullable=True)

    # Configuration JSON fields
    pillar_weights = Column(JSON, nullable=True)
    judge_model_config = Column(JSON, nullable=True)
    judge_output_policy = Column(JSON, nullable=True)
    external_integration_config = Column(JSON, nullable=True)
    external_eval_summary = Column(JSON, nullable=True)

    # A/B comparison
    ab_peer_run_id = Column(
        String,
        ForeignKey(
            "evaluation_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_eval_run_ab_peer",
        ),
        nullable=True,
        index=True,
    )

    # Scores
    composite_score = Column(Float, nullable=True)
    cost_score = Column(Float, nullable=True)
    quality_score = Column(Float, nullable=True)
    reliability_score = Column(Float, nullable=True)
    latency_score = Column(Float, nullable=True)
    summary_stats = Column(JSON, nullable=True)

    # Environment and workflow context
    environment = Column(String, default="dev")
    workflow_id = Column(
        String,
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    graph_definition_id = Column(
        String,
        ForeignKey("graph_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    triggered_by_user_id = Column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    dataset = relationship(
        "EvaluationDataset", back_populates="runs", foreign_keys=[dataset_id]
    )
    results = relationship(
        "EvaluationResult", back_populates="run", cascade="all, delete-orphan"
    )
    recommendations = relationship(
        "EvaluationRecommendation", back_populates="run", cascade="all, delete-orphan"
    )
    ab_peer_run = relationship(
        "EvaluationRun",
        foreign_keys=[ab_peer_run_id],
        remote_side="EvaluationRun.id",
        uselist=False,
    )
    workflow = relationship("Workflow", foreign_keys=[workflow_id])
    graph_definition = relationship(
        "GraphDefinition", foreign_keys=[graph_definition_id]
    )
    triggered_by_user = relationship("User", foreign_keys=[triggered_by_user_id])
