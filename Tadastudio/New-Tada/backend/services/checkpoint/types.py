"""Type definitions for checkpoint metadata.

This module defines TypedDict classes and types for checkpoint metadata,
providing type safety and documentation for checkpoint-related data structures.
"""

from typing import Any, Dict, Optional, TypedDict


class CheckpointMetadataDict(TypedDict, total=False):
    """Type definition for checkpoint metadata dictionary.

    This TypedDict defines the structure of checkpoint metadata used throughout
    the checkpoint system, including subworkflow and execution context information.

    Attributes:
        checkpoint_id: Unique identifier for the checkpoint.
        thread_id: Thread identifier for this checkpoint.
        subworkflow_checkpoint: Whether this is a subworkflow checkpoint.
        subworkflow_name: Name of the subworkflow (if applicable).
        subworkflow_thread_id: Thread ID for the subworkflow execution.
        checkpoint_node_exec_id: Associated node execution ID.
        parent_execution_id: Parent execution identifier.
        parent_tool_call: JSON tool call details from parent workflow.

    Example:
        >>> metadata: CheckpointMetadataDict = {
        ...     "checkpoint_id": "cp_123",
        ...     "thread_id": "thread_456",
        ...     "subworkflow_checkpoint": True,
        ...     "subworkflow_name": "email-handler",
        ...     "subworkflow_thread_id": "sub_thread_789"
        ... }
    """

    checkpoint_id: str
    thread_id: str
    subworkflow_checkpoint: bool
    subworkflow_name: Optional[str]
    subworkflow_thread_id: Optional[str]
    checkpoint_node_exec_id: Optional[str]
    parent_execution_id: Optional[str]
    parent_tool_call: Optional[Dict[str, Any]]


class CheckpointStatusType:
    """Constants for checkpoint status values.

    This class defines the valid status values for checkpoints,
    ensuring consistency across the checkpoint system.

    Attributes:
        ACTIVE: Checkpoint is active and can be resumed.
        RESUMED: Checkpoint has been resumed.
        COMPLETED: Checkpoint execution has completed.
    """

    ACTIVE = "active"
    RESUMED = "resumed"
    COMPLETED = "completed"


# Type alias for general metadata dictionaries
MetadataDict = Dict[str, Any]
