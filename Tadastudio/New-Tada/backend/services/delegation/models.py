"""Data models and types for delegation service.

This module provides type-safe data structures for delegation operations.
"""

from typing import Any, Dict, Optional, TypedDict

from backend.models.workflow import EnhancedNodeData, NodeType


class DelegationContext(TypedDict, total=False):
    """Context information for delegation execution.

    Attributes:
        execution_id: Parent execution ID
        db_execution_id: Database execution ID
        execution_order: Current execution order
        graph_name: Name of the graph being executed
        tool_node_mapping: Mapping of tool names to node IDs
        parent_node_execution_id: Database execution record ID of the parent agent
    """

    execution_id: Optional[str]
    db_execution_id: Optional[str]
    execution_order: int
    graph_name: Optional[str]
    tool_node_mapping: Dict[str, Dict[str, Any]]
    parent_node_execution_id: Optional[str]
    user_id: Optional[str]


class DelegationRequest:
    """Request for delegating a task to an agent.

    Attributes:
        agent_node: The agent node to delegate to
        task_description: Description of the task
        orchestrator_id: ID of the orchestrator agent
        context: Execution context information
    """

    def __init__(
        self,
        agent_node: EnhancedNodeData,
        task_description: str,
        orchestrator_id: str,
        context: Optional[DelegationContext] = None,
    ):
        """Initialize delegation request.

        Args:
            agent_node: The agent node to delegate to
            task_description: Description of the task
            orchestrator_id: ID of the orchestrator agent
            context: Execution context information

        Raises:
            ValueError: If agent_node is not an AGENT type
        """
        if agent_node.type != NodeType.AGENT:
            raise ValueError(f"Node {agent_node.name} is not an AGENT node")

        self.agent_node = agent_node
        self.task_description = task_description
        self.orchestrator_id = orchestrator_id
        self.context = context or {}


class DelegationResult:
    """Result of a delegation operation.

    Attributes:
        success: Whether the delegation was successful
        response: Response from the delegated agent
        error: Error message if delegation failed
        metadata: Additional metadata about the execution
    """

    def __init__(
        self,
        success: bool,
        response: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize delegation result.

        Args:
            success: Whether the delegation was successful
            response: Response from the delegated agent
            error: Error message if delegation failed
            metadata: Additional metadata about the execution
        """
        self.success = success
        self.response = response
        self.error = error
        self.metadata = metadata or {}

    def format_for_agent(self, agent_name: str) -> str:
        """Format the result for display to an agent.

        Args:
            agent_name: Name of the agent that was delegated to

        Returns:
            Formatted string response
        """
        if self.success and self.response:
            return f"{agent_name} completed the task with the following result:\n\n{self.response}"
        elif self.error:
            return f"Error delegating to {agent_name}: {self.error}"
        else:
            return f"Error delegating to {agent_name}: Unknown error"


class ToolNodeInfo(TypedDict):
    """Information about a tool node.

    Attributes:
        node_id: Unique ID of the node
        node_name: Display name of the node
        node_type: Type of the node (NodeType enum value)
    """

    node_id: str
    node_name: str
    node_type: NodeType


class SubworkflowRequest:
    """Request for executing a subworkflow.

    Attributes:
        subworkflow_node: The subworkflow node to execute
        task_description: Description of the task
        orchestrator_id: ID of the orchestrator agent
        workflow_input: Additional input parameters
        context: Execution context information
    """

    def __init__(
        self,
        subworkflow_node: EnhancedNodeData,
        task_description: str,
        orchestrator_id: str,
        workflow_input: Optional[Dict[str, Any]] = None,
        context: Optional[DelegationContext] = None,
    ):
        """Initialize subworkflow request.

        Args:
            subworkflow_node: The subworkflow node to execute
            task_description: Description of the task
            orchestrator_id: ID of the orchestrator agent
            workflow_input: Additional input parameters
            context: Execution context information

        Raises:
            ValueError: If subworkflow_node is not a SUBWORKFLOW type
        """
        if subworkflow_node.type != NodeType.SUBWORKFLOW:
            raise ValueError(f"Node {subworkflow_node.name} is not a SUBWORKFLOW node")

        self.subworkflow_node = subworkflow_node
        self.task_description = task_description
        self.orchestrator_id = orchestrator_id
        self.workflow_input = workflow_input or {}
        self.context = context or {}
