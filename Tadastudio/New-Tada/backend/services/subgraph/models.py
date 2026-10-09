"""
State models and type definitions for LangGraph subgraph execution.

This module defines TypedDict classes for subagent and subworkflow state,
along with supporting data models for tool execution tracking.
"""

from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ToolExecution(TypedDict, total=False):
    """
    Structured type for tool execution tracking.

    Attributes:
        tool: The name of the tool executed
        input: Input data passed to the tool
        output: Output/results from the tool
        results: Alternative field for results
        response: Response data (for HTTP tools)
        request: Request data (for HTTP tools)
        query: Query string (for search tools)
        provider: Provider name (for search tools)
        formatted_results: Formatted search results
        action: Action performed (for MCP tools)
        target: Target of the action (for MCP tools)
        server: Server name (for MCP tools)
        connection_type: Connection type (for MCP tools)
        arguments: Arguments passed (for MCP tools)
        formatted_output: Formatted output (for MCP tools)
        kwargs: Keyword arguments
        args: Positional arguments
        duration: Execution duration in seconds
        timestamp: Execution timestamp
        error: Error message if execution failed
    """

    tool: str
    input: Dict[str, Any]
    output: Any
    results: Any
    response: Dict[str, Any]
    request: Dict[str, Any]
    query: str
    provider: str
    formatted_results: str
    action: str
    target: str
    server: str
    connection_type: str
    arguments: Dict[str, Any]
    formatted_output: str
    kwargs: Dict[str, Any]
    args: Any
    duration: float
    timestamp: float
    error: str


class ToolNodeMapping(TypedDict, total=False):
    """
    Mapping information for a tool to its node representation.

    Attributes:
        node_id: The unique ID of the tool node
        node_name: The display name of the tool node
        node_type: The type of the tool node (NodeType enum value)
    """

    node_id: str
    node_name: str
    node_type: str


class SubAgentState(TypedDict):
    """State for sub-agent execution within a subgraph.

    This state is passed between the parent graph and subgraph.

    Attributes:
        task_description: The task to be performed by the sub-agent
        task_id: Optional unique identifier for the task
        parent_execution_id: Execution ID of the parent graph
        parent_db_execution_id: Database execution ID of the parent
        parent_node_id: Node ID of the parent orchestrator
        parent_node_execution_id: Database execution record ID of the parent agent
        parent_node_name: Display name of the parent node
        execution_order: Current execution order counter
        invocation_index: Which invocation of this subagent (1st, 2nd, etc.)
        start_time: ISO format start time
        end_time: ISO format end time
        agent_node_id: The sub-agent's node ID
        agent_node_name: The sub-agent's display name
        agent_config: Configuration for the agent
        graph_name: Name of the parent graph for tool resolution
        tool_node_mapping: Maps tool names to their node IDs
        tool_execution_tracker: Internal list for tracking tool executions (passed by reference)
        response: Text response from the agent
        structured_output: Structured output data
        tool_executions: List of tool executions performed
        error: Error message if execution failed
        paused: Whether the sub-agent execution is paused
        paused_for_review: Whether paused specifically for human review
        review_data: Review context data when paused for review
        messages: Conversation message history
        metadata: Additional execution metadata
    """

    # Task information
    task_description: str
    task_id: Optional[str]

    # Execution context
    parent_execution_id: str
    parent_db_execution_id: Optional[str]
    parent_node_id: str
    parent_node_execution_id: Optional[str]
    parent_node_name: str

    # Execution tracking
    execution_order: int
    invocation_index: Optional[int]
    start_time: Optional[str]
    end_time: Optional[str]

    # Agent information
    agent_node_id: str
    agent_node_name: str
    agent_config: Optional[Dict[str, Any]]

    # User identity for OAuth token lookup (MCP tools, etc.)
    user_id: Optional[str]

    # Graph context for tool resolution
    graph_name: Optional[str]
    tool_node_mapping: Optional[Dict[str, str]]
    tool_execution_tracker: List[Dict[str, Any]]

    # Results
    response: Optional[str]
    structured_output: Optional[Dict[str, Any]]
    tool_executions: List[Dict[str, Any]]
    error: Optional[str]

    # Review/pause state for sub-agents
    paused: Optional[bool]
    paused_for_review: Optional[bool]
    review_data: Optional[Dict[str, Any]]

    # Review node state (for dedicated review node pattern)
    # Stores output, config, iteration, history for review loop
    review_state: Optional[Dict[str, Any]]
    # Routing decision from review node: "continue" or "retry"
    __review_route: Optional[str]

    # Messages for conversation context
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Metadata
    metadata: Dict[str, Any]


class SubWorkflowState(TypedDict):
    """State for sub-workflow execution within a subgraph.

    Extends SubAgentState conceptually with workflow-specific fields.

    Attributes:
        task_description: The task description for the workflow
        workflow_input: Additional parameters from agent
        parent_execution_id: Execution ID of the parent graph
        parent_db_execution_id: Database execution ID of the parent
        parent_node_id: Node ID of the parent orchestrator
        parent_node_name: Display name of the parent node
        execution_order: Current execution order counter
        start_time: ISO format start time
        end_time: ISO format end time
        workflow_node_id: The workflow node's ID
        workflow_node_name: The workflow's display name
        workflow_config: Configuration for the workflow
        graph_name: Name of the parent graph
        workflow_output: Output from the END node
        nodes_executed: List of node names executed
        structured_output: Structured output data
        error: Error message if execution failed
        response: Response text (for compatibility)
        messages: Conversation message history
        metadata: Additional execution metadata
    """

    # Task information
    task_description: str
    workflow_input: Dict[str, Any]

    # Execution context
    parent_execution_id: str
    parent_db_execution_id: Optional[str]
    parent_node_id: str
    parent_node_name: str

    # Execution tracking
    execution_order: int
    start_time: Optional[str]
    end_time: Optional[str]

    # Workflow information
    workflow_node_id: str
    workflow_node_name: str
    workflow_config: Optional[Dict[str, Any]]

    # Graph context
    graph_name: Optional[str]

    # Results
    workflow_output: Optional[str]
    nodes_executed: List[str]
    structured_output: Optional[Dict[str, Any]]
    error: Optional[str]
    response: Optional[str]  # For compatibility

    # Messages for conversation context
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Metadata
    metadata: Dict[str, Any]


class TokenCounts(TypedDict, total=False):
    """
    Token usage information from LLM execution.

    Attributes:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        total_tokens: Total tokens used (input + output)
    """

    input_tokens: int
    output_tokens: int
    total_tokens: int
