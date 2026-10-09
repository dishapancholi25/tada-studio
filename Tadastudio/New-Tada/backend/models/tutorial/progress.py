"""Tutorial progress model for per-user tutorial completion tracking."""

import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from ...services.database import Base


class TutorialProgress(Base):
    """Stores per-user tutorial completion state.

    Replaces the frontend localStorage-based persistence so that tutorial
    progress is consistent across browsers and machines.

    Attributes:
        id: UUID primary key
        user_id: User identifier (sub claim from JWT)
        completed_tutorials: JSON object mapping tutorial_id -> true
        last_step_reached: JSON object mapping tutorial_id -> step index
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
    """

    __tablename__ = "tutorial_progress"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, unique=True, index=True)
    completed_tutorials = Column(JSONB, nullable=False, server_default="{}")
    last_step_reached = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
