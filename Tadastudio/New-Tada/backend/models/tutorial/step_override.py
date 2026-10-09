"""Tutorial step override model for admin-customizable tutorial positioning and text."""

import uuid

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from ...services.database import Base


class TutorialStepOverride(Base):
    """Stores admin customizations for tutorial step positions and text.

    Attributes:
        id: UUID primary key
        tutorial_id: Tutorial identifier (e.g. 'home', 'workflow-canvas')
        step_index: Zero-based step index within the tutorial
        popover_offset_x: Horizontal pixel offset for the instruction popover
        popover_offset_y: Vertical pixel offset for the instruction popover
        pointer_offset_x: Horizontal pixel offset for the pointer
        pointer_offset_y: Vertical pixel offset for the pointer
        title: Override for the step title (null = use default)
        description: Override for the step description (null = use default)
        interaction_hint: Override for the interaction hint (null = use default)
        updated_by: Email of the admin who last saved this override
        created_at: Timestamp when the override was created
        updated_at: Timestamp when the override was last updated
    """

    __tablename__ = "tutorial_step_overrides"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tutorial_id = Column(String, nullable=False, index=True)
    step_index = Column(Integer, nullable=False)
    breakpoint = Column(String, nullable=False, default="desktop")

    popover_offset_x = Column(Integer, nullable=False, default=0)
    popover_offset_y = Column(Integer, nullable=False, default=0)
    pointer_offset_x = Column(Integer, nullable=False, default=0)
    pointer_offset_y = Column(Integer, nullable=False, default=0)

    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    interaction_hint = Column(Text, nullable=True)

    updated_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "tutorial_id",
            "step_index",
            "breakpoint",
            name="uq_tutorial_step_override_bp",
        ),
    )
