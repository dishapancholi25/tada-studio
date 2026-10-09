"""
Base interfaces and protocols for node executors.

This module defines the abstract base class and protocol for node executors,
establishing a consistent interface for all node types (agent, HTTP, file, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol

from backend.models.workflow import EnhancedNodeData
from backend.services.workflow.state import WorkflowState


class NodeExecutorProtocol(Protocol):
    """
    Protocol defining the interface for node executors.

    This protocol can be used for type hints and duck typing,
    allowing any class that implements these methods to be used
    as a node executor without inheriting from BaseNodeExecutor.
    """

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a node and return state updates."""
        ...

    async def validate_config(self, node: EnhancedNodeData) -> bool:
        """Validate node configuration."""
        ...


class BaseNodeExecutor(ABC):
    """
    Abstract base class for all node executors.

    Provides a consistent interface for executing different node types
    (agent, HTTP request, file operations, database queries, etc.).

    Each concrete executor must implement the execute() method to handle
    its specific node type. Executors receive shared dependencies through
    constructor injection (execution_history_service, ws_notifier, etc.).

    Attributes:
        execution_history_service: Service for tracking execution history
        ws_notifier: WebSocket notifier for real-time updates
        subgraph_executor: Executor for handling subgraphs
        graph_manager: Manager for graph operations

    Example:
        >>> class AgentNodeExecutor(BaseNodeExecutor):
        ...     async def execute(self, node, state, graph, execution_id, user_id=None):
        ...         # Execute agent node
        ...         return {"output": "result"}
        ...
        ...     async def validate_config(self, node):
        ...         return node.config.get("agent_name") is not None
    """

    def __init__(
        self,
        execution_history_service: Any,
        ws_notifier: Any,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        """
        Initialize the node executor with shared dependencies.

        Args:
            execution_history_service: Service for tracking execution history
            ws_notifier: WebSocket notifier for real-time updates
            subgraph_executor: Optional executor for handling subgraphs
            graph_manager: Optional manager for graph operations
        """
        self.execution_history_service = execution_history_service
        self.ws_notifier = ws_notifier
        self.subgraph_executor = subgraph_executor
        self.graph_manager = graph_manager

    @abstractmethod
    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute the node and return state updates.

        This is the main execution method that must be implemented by all
        concrete node executors. It should:
        1. Validate node configuration
        2. Extract input from state
        3. Execute the node's specific logic
        4. Send WebSocket notifications
        5. Track execution in database
        6. Return state updates

        Args:
            node: The node to execute
            state: Current workflow state
            graph: The StateGraph instance
            execution_id: Unique execution identifier
            user_id: Optional user identifier

        Returns:
            Dictionary of state updates to apply

        Raises:
            NodeExecutionError: If execution fails

        Example:
            >>> result = await executor.execute(
            ...     node=agent_node,
            ...     state=current_state,
            ...     graph=state_graph,
            ...     execution_id="exec-123",
            ...     user_id="user-456"
            ... )
            >>> print(result)
            {"output": "Agent response", "node_outputs": [...]}
        """
        pass

    async def validate_config(self, node: EnhancedNodeData) -> bool:
        """
        Validate node configuration before execution.

        This method can be overridden by concrete executors to provide
        node-type-specific validation logic.

        Args:
            node: The node to validate

        Returns:
            True if configuration is valid, False otherwise

        Example:
            >>> is_valid = await executor.validate_config(node)
            >>> if not is_valid:
            ...     raise ConfigurationError("Invalid node config")
        """
        return True

    async def pre_execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        execution_id: str,
    ) -> None:
        """
        Execute setup tasks before node execution.

        Can be overridden to perform setup tasks like:
        - Logging
        - WebSocket notification (node start)
        - Resource allocation

        Args:
            node: The node about to execute
            state: Current workflow state
            execution_id: Unique execution identifier
        """
        pass

    async def post_execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        execution_id: str,
        result: Dict[str, Any],
        duration_seconds: float,
    ) -> None:
        """
        Execute cleanup tasks after successful node execution.

        Can be overridden to perform cleanup tasks like:
        - Logging
        - WebSocket notification (node complete)
        - Metrics collection
        - Resource cleanup

        Args:
            node: The node that executed
            state: Current workflow state
            execution_id: Unique execution identifier
            result: Execution result
            duration_seconds: Execution duration
        """
        pass

    async def on_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        execution_id: str,
        error: Exception,
    ) -> None:
        """
        Handle node execution failure.

        Can be overridden to handle errors like:
        - Logging error details
        - WebSocket notification (node error)
        - Error recovery attempts
        - Cleanup

        Args:
            node: The node that failed
            state: Current workflow state
            execution_id: Unique execution identifier
            error: The exception that occurred
        """
        pass

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"{self.__class__.__name__}()"
