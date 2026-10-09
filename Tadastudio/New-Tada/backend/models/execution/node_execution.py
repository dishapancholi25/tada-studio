"""Node execution tracking model."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from ...services.database import Base
from ..base import TimestampMixin, UUIDPrimaryKeyMixin


class NodeExecution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model for storing individual node execution details.

    Tracks the execution of individual nodes within a graph, including
    timing, input/output, token usage, costs, and performance metrics.

    Attributes:
        id: Unique node execution identifier (UUID).
        graph_execution_id: Parent graph execution ID.
        node_id: Node identifier within the graph.
        node_name: Human-readable node name.
        node_type: Type of node (agent, flow, condition, tool).
        execution_order: Sequential order of execution.
        status: Execution status (pending, running, completed, failed, skipped).
        start_time: When node execution started.
        end_time: When node execution completed.
        duration_seconds: Total execution time in seconds.
        input_data: JSON input data for the node.
        output_data: JSON output data from the node.
        error_message: Error message if execution failed.
        node_metadata: Additional node-specific metadata.
        is_sub_agent: Whether this is a sub-agent execution.
        parent_agent_id: ID of parent agent that executed this tool.
        input_tokens: Number of input tokens used.
        output_tokens: Number of output tokens generated.
        total_tokens: Total tokens (input + output).
        token_metadata: Detailed token breakdown.
        llm_metadata: LLM configuration (model, temperature, provider, costs).
        message_structure: System/user/assistant messages with tokens.
        tool_metadata: Tool invocation details, arguments, results.
        orchestration_metadata: Delegation, subagent coordination.
        memory_metadata: Memory operations, context management.
        environment_metadata: Runtime info, feature flags.
        prompt_cost: Cost of prompt tokens.
        completion_cost: Cost of completion tokens.
        total_cost: Total cost for this node.
        time_to_first_token: TTFT in milliseconds.
        tokens_per_second: Generation speed.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    """

    __tablename__ = "node_executions"

    graph_execution_id = Column(
        String, ForeignKey("graph_executions.id"), nullable=False, index=True
    )

    # Node information
    node_id = Column(String, nullable=False)
    node_name = Column(String, nullable=False)
    node_type = Column(String, nullable=False)

    # Execution details
    execution_order = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Input/Output
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Additional metadata
    node_metadata = Column(JSON, nullable=True)
    is_sub_agent = Column(Boolean, default=False, nullable=True)

    # Parent agent tracking
    parent_agent_id = Column(
        String, ForeignKey("node_executions.id", ondelete="SET NULL"), nullable=True
    )

    # Review iteration tracking (for multi-iteration review flows)
    review_iteration = Column(Integer, nullable=True)

    # Invocation index tracking (for multi-call subagent flows)
    invocation_index = Column(Integer, nullable=True)

    # Node version tracking — SHA256 of the node's config at execution time
    node_config_hash = Column(String(64), nullable=True, index=True)

    # Token counting fields
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    token_metadata = Column(JSON, nullable=True)

    # Enhanced metadata for trace viewer
    llm_metadata = Column(JSON, nullable=True)
    message_structure = Column(JSON, nullable=True)
    tool_metadata = Column(JSON, nullable=True)
    orchestration_metadata = Column(JSON, nullable=True)
    memory_metadata = Column(JSON, nullable=True)
    environment_metadata = Column(JSON, nullable=True)

    # Computed cost tracking
    prompt_cost = Column(Float, nullable=True)
    completion_cost = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)

    # Performance metrics
    time_to_first_token = Column(Float, nullable=True)
    tokens_per_second = Column(Float, nullable=True)

    # Relationships
    graph_execution = relationship("GraphExecution", back_populates="node_executions")
    files = relationship(
        "ExecutionFile", back_populates="node_execution", cascade="all, delete-orphan"
    )
