"""Pydantic models for execution API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CheckpointInfo(BaseModel):
    """Information about a checkpoint node."""

    node_id: str = Field(..., description="The ID of the checkpoint node")
    node_name: str = Field(..., description="The name of the checkpoint node")
    checkpoint_id: Optional[str] = Field(
        None, description="The LangGraph checkpoint ID"
    )
    prompt: Optional[str] = Field(None, description="The prompt displayed to the user")
    last_input: Optional[Dict[str, Any]] = Field(
        None, description="The last input data to the checkpoint"
    )
    previous_output: Optional[Dict[str, Any]] = Field(
        None, description="Output from the previous node"
    )


class ProgressInfo(BaseModel):
    """Execution progress information."""

    completed_nodes: int = Field(..., description="Number of completed nodes")
    total_nodes: int = Field(..., description="Total number of nodes in the graph")
    percentage: float = Field(..., description="Completion percentage (0-100)")


class PausedExecutionSummaryResponse(BaseModel):
    """Summary response for a paused execution."""

    execution_id: str = Field(..., description="The database execution ID")
    thread_id: Optional[str] = Field(None, description="The LangGraph thread ID")
    websocket_execution_id: Optional[str] = Field(
        None, description="The websocket execution ID"
    )
    graph_name: str = Field(..., description="Name of the graph/workflow")
    paused_at: Optional[datetime] = Field(
        None, description="When the execution was paused"
    )
    checkpoint: Optional[CheckpointInfo] = Field(
        None, description="Information about the checkpoint that caused the pause"
    )
    progress: ProgressInfo = Field(..., description="Execution progress information")

    class Config:
        """Pydantic config."""

        from_attributes = True


class PaginationInfo(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")
    has_more: bool = Field(..., description="Whether there are more items available")
    next_skip: Optional[int] = Field(None, description="Skip value for the next page")


class PausedExecutionsResponse(BaseModel):
    """Response containing paused executions with pagination."""

    executions: List[PausedExecutionSummaryResponse] = Field(
        ..., description="List of paused execution summaries"
    )
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


class AllPausedExecutionsResponse(BaseModel):
    """Response containing all paused executions grouped by graph."""

    total_paused: int = Field(..., description="Total number of paused executions")
    by_graph: Dict[str, List[PausedExecutionSummaryResponse]] = Field(
        ..., description="Paused executions grouped by graph name"
    )


class NodeExecutionDetail(BaseModel):
    """Detailed information about a node execution."""

    id: str = Field(..., description="The database node execution ID")
    node_id: str = Field(..., description="The node ID from the graph definition")
    node_name: str = Field(..., description="The display name of the node")
    node_type: str = Field(
        ..., description="The type of node (e.g., CHECKPOINT, AGENT)"
    )
    status: str = Field(..., description="The execution status")
    execution_order: int = Field(
        ..., description="The order in which this node executed"
    )
    start_time: Optional[datetime] = Field(None, description="When the node started")
    end_time: Optional[datetime] = Field(None, description="When the node completed")
    duration_seconds: Optional[float] = Field(None, description="Execution duration")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Node input data")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Node output data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    is_sub_agent: bool = Field(False, description="Whether this is a sub-agent node")
    parent_agent_id: Optional[str] = Field(
        None, description="Parent agent ID if sub-agent"
    )
    total_tokens: Optional[int] = Field(None, description="Total tokens used")


class ExecutionDetail(BaseModel):
    """Detailed information about a graph execution."""

    id: str = Field(..., description="The database execution ID")
    thread_id: Optional[str] = Field(None, description="The LangGraph thread ID")
    websocket_execution_id: Optional[str] = Field(
        None, description="The websocket execution ID"
    )
    graph_name: str = Field(..., description="Name of the graph/workflow")
    status: str = Field(..., description="The execution status")
    created_at: datetime = Field(..., description="When the execution was created")
    input_data: Optional[Dict[str, Any]] = Field(
        None, description="Input data to the execution"
    )
    output_data: Optional[Dict[str, Any]] = Field(
        None, description="Output data from the execution"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if execution failed"
    )


class ExecutionStateResponse(BaseModel):
    """Complete execution state including all node executions."""

    execution: ExecutionDetail = Field(..., description="The execution information")
    nodes: List[NodeExecutionDetail] = Field(
        ..., description="List of node executions in order"
    )
    checkpoint_state: Optional[CheckpointInfo] = Field(
        None, description="Information about the paused checkpoint"
    )
    can_resume: bool = Field(
        ..., description="Whether the execution can be resumed from a checkpoint"
    )
    graph_definition: Dict[str, Any] = Field(
        ..., description="The graph definition used for this execution"
    )


class CancelExecutionResponse(BaseModel):
    """Response for cancellation request."""

    status: str = Field(..., description="The new status (cancelled)")
    execution_id: str = Field(..., description="The execution ID that was cancelled")
    message: str = Field(..., description="Success message")


class StopExecutionResponse(BaseModel):
    """Response for stop request."""

    status: str = Field(..., description="The resulting status (stopping/stopped)")
    execution_id: str = Field(..., description="The database execution ID")
    thread_id: str = Field(..., description="The active thread identifier")


class PauseExecutionResponse(BaseModel):
    """Response for pause request."""

    status: str = Field(..., description="The resulting status (pause_pending/paused)")
    execution_id: str = Field(..., description="The database execution ID")
    thread_id: str = Field(..., description="The active thread identifier")


class ManualResumeResponse(BaseModel):
    """Response for manual resume request."""

    status: str = Field(..., description="Execution status after resuming")
    execution_id: str = Field(..., description="The database execution ID")
    thread_id: str = Field(..., description="The active thread identifier")
    result: Optional[Dict[str, Any]] = Field(
        None, description="Optional payload returned from the resume operation"
    )


class CheckpointDataResponse(BaseModel):
    """Response containing checkpoint data for resuming."""

    execution_id: str = Field(..., description="The database execution ID")
    thread_id: Optional[str] = Field(None, description="The LangGraph thread ID")
    websocket_execution_id: Optional[str] = Field(
        None, description="The websocket execution ID"
    )
    checkpoint: CheckpointInfo = Field(
        ..., description="The checkpoint information for resuming"
    )
    graph_name: str = Field(..., description="Name of the graph/workflow")
