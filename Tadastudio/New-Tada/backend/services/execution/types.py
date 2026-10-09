"""
Type definitions for execution engine.

This module defines TypedDicts and Protocols used throughout the execution engine
to provide clear type hints and better IDE support.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, TypedDict


class ExecutionConfig(TypedDict, total=False):
    """
    Configuration for workflow execution.

    Attributes:
        execution_id: Unique identifier for this execution
        user_id: User executing the workflow
        workflow_id: Workflow UUID
        graph_definition_id: Graph definition UUID (for versioning)
        thread_id: Thread ID for checkpointing
        checkpoint_id: Optional checkpoint to resume from
        enable_checkpointing: Whether to enable checkpointing
        checkpoint_interval: How often to checkpoint (in nodes)
        max_retries: Maximum retry attempts for failed nodes
        timeout_seconds: Overall execution timeout
        enable_websocket: Whether to send WebSocket notifications
        metadata: Additional metadata to track
    """

    execution_id: str
    user_id: Optional[str]
    workflow_id: Optional[str]
    graph_definition_id: Optional[str]
    thread_id: Optional[str]
    checkpoint_id: Optional[str]
    enable_checkpointing: bool
    checkpoint_interval: int
    max_retries: int
    timeout_seconds: int
    enable_websocket: bool
    metadata: Dict[str, Any]


class ExecutionResult(TypedDict, total=False):
    """
    Result of workflow execution.

    Attributes:
        status: Execution status (success, failed, interrupted)
        output: Final output value
        error: Error message (if failed)
        execution_id: Execution identifier
        start_time: Execution start timestamp
        end_time: Execution end timestamp
        duration_seconds: Total execution duration
        nodes_executed: Number of nodes executed
        checkpoints_created: Number of checkpoints created
        final_state: Final workflow state
        metadata: Additional result metadata
    """

    status: str
    output: Any
    error: Optional[str]
    execution_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    nodes_executed: int
    checkpoints_created: int
    final_state: Dict[str, Any]
    metadata: Dict[str, Any]


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    WAITING_FOR_CHECKPOINT = "waiting_for_checkpoint"


class NodeExecutionContext(TypedDict, total=False):
    """
    Context for individual node execution.

    Attributes:
        node_id: Node identifier
        node_name: Node display name
        node_type: Node type (AGENT, HTTP_REQUEST, etc.)
        execution_id: Parent execution identifier
        user_id: User executing the workflow
        start_time: Node execution start time
        input_data: Input data passed to node
        parent_outputs: Outputs from parent nodes
        execution_order: Order of execution within workflow
        retry_count: Number of retry attempts
        database_node_id: Database record ID for this node execution
    """

    node_id: str
    node_name: str
    node_type: str
    execution_id: str
    user_id: Optional[str]
    start_time: datetime
    input_data: Dict[str, Any]
    parent_outputs: Dict[str, Any]
    execution_order: int
    retry_count: int
    database_node_id: Optional[int]


class CheckpointMetadata(TypedDict, total=False):
    """
    Metadata stored with checkpoints.

    Attributes:
        execution_id: Execution identifier
        workflow_id: Workflow identifier
        user_id: User identifier
        checkpoint_type: Type of checkpoint (auto, manual, email)
        created_at: Checkpoint creation timestamp
        node_id: Node ID where checkpoint was created
        node_name: Node name where checkpoint was created
        resume_data: Data needed to resume execution
        parent_checkpoint_id: Parent checkpoint (for nested workflows)
    """

    execution_id: str
    workflow_id: Optional[str]
    user_id: Optional[str]
    checkpoint_type: str
    created_at: str
    node_id: str
    node_name: str
    resume_data: Dict[str, Any]
    parent_checkpoint_id: Optional[str]


class GraphBuildContext(TypedDict, total=False):
    """
    Context for building StateGraph.

    Attributes:
        graph_name: Name of the graph
        start_node_id: ID of the start node
        nodes: List of all nodes
        edges: List of all edges
        tool_nodes: Mapping of tool names to nodes
        enable_native_tools: Whether to use native ToolNode
        conditional_edges: List of conditional edges
    """

    graph_name: str
    start_node_id: str
    nodes: List[Any]
    edges: List[Any]
    tool_nodes: Dict[str, Any]
    enable_native_tools: bool
    conditional_edges: List[Any]


class ConditionEvaluationContext(TypedDict, total=False):
    """
    Context for condition evaluation.

    Attributes:
        condition_type: Type of condition (value, branch, llm, expression)
        condition_config: Condition configuration
        state: Current workflow state
        node_outputs: Previous node outputs
        execution_id: Execution identifier
        node_id: Condition node identifier
    """

    condition_type: str
    condition_config: Dict[str, Any]
    state: Dict[str, Any]
    node_outputs: List[Dict[str, Any]]
    execution_id: str
    node_id: str


class NodeExecutorProtocol(Protocol):
    """
    Protocol for node executors.

    Any class implementing these methods can be used as a node executor.
    """

    async def execute(
        self,
        node: Any,
        state: Any,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a node and return state updates."""
        ...

    async def validate_config(self, node: Any) -> bool:
        """Validate node configuration."""
        ...


class GraphBuilderProtocol(Protocol):
    """
    Protocol for graph builders.

    Defines the interface for building StateGraphs from graph definitions.
    """

    def build_state_graph(self, graph: Any, execution_id: str) -> Any:
        """Build a StateGraph from a graph definition."""
        ...

    def create_node_function(self, node: Any, execution_id: str) -> callable:
        """Create a function for a node."""
        ...

    def create_condition_function(self, node: Any, execution_id: str) -> callable:
        """Create a condition evaluation function."""
        ...


class ConditionEvaluatorProtocol(Protocol):
    """
    Protocol for condition evaluators.

    Defines the interface for evaluating different condition types.
    """

    async def evaluate(self, condition_config: Dict[str, Any], state: Any) -> bool:
        """Evaluate a condition and return boolean result."""
        ...

    def get_next_node(
        self, condition_result: bool, condition_config: Dict[str, Any]
    ) -> str:
        """Determine the next node based on condition result."""
        ...


# Type aliases for common types
StateDict = Dict[str, Any]
NodeOutputDict = Dict[str, Any]
ConfigDict = Dict[str, Any]
MetadataDict = Dict[str, Any]
