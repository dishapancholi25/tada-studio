"""Pydantic models for execution history API responses.

This module defines the response schemas used by the execution history API endpoints.
All models use `from_attributes = True` to support automatic conversion from ORM objects.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class NodeExecutionResponse(BaseModel):
    """Response model for a single node execution.

    Attributes:
        id: Unique identifier for the node execution
        node_id: Identifier of the node in the graph definition
        node_name: Human-readable name of the node
        node_type: Type of node (e.g., AGENT, HTTP_REQUEST, MCP_SERVER)
        execution_order: Order in which this node was executed
        status: Current status (e.g., running, completed, failed)
        start_time: When the node execution started
        end_time: When the node execution completed
        duration_seconds: Total execution time in seconds
        input_data: Input data provided to the node
        output_data: Output data produced by the node
        error_message: Error message if execution failed
        node_metadata: Additional node-specific metadata
        is_sub_agent: Whether this is a sub-agent node
        review_iteration: Agent review iteration number for tool tracking
        created_at: Record creation timestamp
    """

    id: str
    node_id: str
    node_name: str
    node_type: str
    execution_order: int
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    node_metadata: Optional[Dict[str, Any]]
    is_sub_agent: bool = False
    review_iteration: Optional[int] = None
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class GraphExecutionResponse(BaseModel):
    """Response model for a complete graph execution.

    Attributes:
        id: Unique identifier for the graph execution
        graph_id: Identifier of the graph that was executed
        graph_name: Human-readable name of the graph
        graph_definition: Full graph definition/structure
        status: Current status (e.g., running, completed, failed)
        start_time: When the graph execution started
        end_time: When the graph execution completed
        duration_seconds: Total execution time in seconds
        input_data: Input data provided to the graph
        output_data: Output data produced by the graph
        error_message: Error message if execution failed
        user_id: User who initiated the execution
        node_executions: List of all node executions in this graph
        created_at: Record creation timestamp
    """

    id: str
    graph_id: str
    graph_name: str
    graph_definition: Dict[str, Any]
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: Optional[float]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    user_id: Optional[str]
    node_executions: List[NodeExecutionResponse]
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class SubmitFeedbackRequest(BaseModel):
    """Request model for submitting execution feedback.

    Attributes:
        rating: Feedback type - "positive" (thumbs up) or "negative" (thumbs down).
        node_execution_id: Optional node execution ID for node-level feedback.
        comment: Optional user note explaining the rating.
    """

    rating: str  # "positive" or "negative"
    node_execution_id: Optional[str] = None
    comment: Optional[str] = None


class ExecutionFeedbackResponse(BaseModel):
    """Response model for execution feedback.

    Attributes:
        id: Feedback identifier.
        graph_execution_id: The execution that was rated.
        node_execution_id: Optional node execution ID (None = workflow-level).
        rating: Feedback type.
        comment: Optional note.
        user_id: User who gave the feedback.
        graph_definition_id: Graph definition version when feedback was given.
        created_at: When the feedback was submitted.
    """

    id: str
    graph_execution_id: str
    node_execution_id: Optional[str] = None
    rating: str
    comment: Optional[str] = None
    user_id: str
    graph_definition_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ExecutionSummaryResponse(BaseModel):
    """Response model for execution summary statistics.

    Attributes:
        graph_id: Graph identifier
        total_executions: Total number of executions
        successful_executions: Number of successful executions
        failed_executions: Number of failed executions
        average_duration_seconds: Average execution time
        min_duration_seconds: Minimum execution time
        max_duration_seconds: Maximum execution time
        last_execution_time: Timestamp of most recent execution
        last_execution_status: Status of most recent execution
    """

    graph_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration_seconds: Optional[float]
    min_duration_seconds: Optional[float]
    max_duration_seconds: Optional[float]
    last_execution_time: Optional[datetime]
    last_execution_status: Optional[str]

    class Config:
        """Pydantic configuration."""

        from_attributes = True
