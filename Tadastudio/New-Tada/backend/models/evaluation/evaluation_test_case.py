"""Evaluation test case model."""

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...services.database import Base
from ..base import UUIDPrimaryKeyMixin


class EvaluationTestCase(Base, UUIDPrimaryKeyMixin):
    """Model for storing individual evaluation test cases.

    Each test case belongs to a dataset and defines input data,
    expected outputs, and judge criteria for evaluation.

    Attributes:
        id: Unique test case identifier (UUID).
        dataset_id: Parent dataset ID.
        input_data: JSON input to be sent to the target.
        expected_output: Optional expected output for comparison.
        judge_criteria: Optional criteria for the judge model.
        tags: Optional tags for categorization.
        created_at: Record creation timestamp.
    """

    __tablename__ = "evaluation_test_cases"

    dataset_id = Column(
        String,
        ForeignKey("evaluation_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_data = Column(JSON, nullable=False)
    expected_output = Column(JSON, nullable=True)
    judge_criteria = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    dataset = relationship("EvaluationDataset", back_populates="test_cases")
    files = relationship(
        "TestCaseFile", back_populates="test_case", cascade="all, delete-orphan"
    )
