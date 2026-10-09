"""Pydantic models for checkpoint API endpoints.

This module defines request and response models for checkpoint management endpoints,
providing validation and serialization for checkpoint-related operations.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class CheckpointResponse(BaseModel):
    """Response model for checkpoint data.

    Attributes:
        checkpoint_id: Unique identifier for the checkpoint.
        thread_id: Thread identifier for the execution.
        timestamp: ISO-8601 formatted timestamp of checkpoint creation.
        metadata: Optional additional checkpoint metadata.

    Example:
        >>> response = CheckpointResponse(
        ...     checkpoint_id="cp_123",
        ...     thread_id="thread_456",
        ...     timestamp="2025-10-19T12:00:00Z"
        ... )
    """

    checkpoint_id: str = Field(
        ..., description="Unique identifier for the checkpoint", min_length=1
    )
    thread_id: str = Field(
        ..., description="Thread identifier for the execution", min_length=1
    )
    timestamp: str = Field(
        ..., description="ISO-8601 formatted timestamp of checkpoint creation"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Optional additional checkpoint metadata"
    )


class ResumeExecutionRequest(BaseModel):
    """Request model for resuming execution from a checkpoint.

    Attributes:
        graph_name: Name of the workflow graph to resume.
        thread_id: Thread identifier for the paused execution.
        checkpoint_id: Checkpoint identifier to resume from.
        new_input: Optional new input data to provide when resuming.

    Example:
        >>> request = ResumeExecutionRequest(
        ...     graph_name="my-workflow",
        ...     thread_id="thread_456",
        ...     checkpoint_id="cp_123",
        ...     new_input={"value": "user response"}
        ... )
    """

    graph_name: str = Field(
        ..., description="Name of the workflow graph to resume", min_length=1
    )
    thread_id: str = Field(
        ..., description="Thread identifier for the paused execution", min_length=1
    )
    checkpoint_id: str = Field(
        ..., description="Checkpoint identifier to resume from", min_length=1
    )
    new_input: Optional[Dict[str, Any]] = Field(
        None, description="Optional new input data to provide when resuming"
    )


class CheckpointStatusResponse(BaseModel):
    """Response model for checkpoint system status.

    Attributes:
        checkpointing_enabled: Whether checkpointing is enabled in the system.
        engine_type: Type of execution engine being used.
        engine_supports_checkpoints: Whether the engine supports checkpoints.

    Example:
        >>> status = CheckpointStatusResponse(
        ...     checkpointing_enabled=True,
        ...     engine_type="langgraph",
        ...     engine_supports_checkpoints=True
        ... )
    """

    checkpointing_enabled: bool = Field(
        ..., description="Whether checkpointing is enabled in the system"
    )
    engine_type: str = Field(..., description="Type of execution engine being used")
    engine_supports_checkpoints: bool = Field(
        ..., description="Whether the engine supports checkpoints"
    )
