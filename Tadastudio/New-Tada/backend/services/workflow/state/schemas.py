"""
TypedDict state schemas for LangGraph workflow execution.

This module defines the structured state that flows through LangGraph workflow graphs.
The state is managed by LangGraph's state management system and flows through each node.

Core Concepts:
    - WorkflowState: The main state dictionary that flows through the entire workflow
    - NodeOutput: Structure for capturing output from individual node executions
    - Reducers: Custom functions that control how state updates are merged

Example:
    >>> from backend.services.workflow.state import WorkflowState, NodeOutput
    >>> from langgraph.graph import StateGraph
    >>>
    >>> # Define workflow with WorkflowState
    >>> workflow = StateGraph(WorkflowState)
    >>>
    >>> # Nodes return updates to the state
    >>> def my_node(state: WorkflowState) -> dict:
    ...     node_output: NodeOutput = {
    ...         "raw": "Hello World",
    ...         "structured": {"key": "value"},
    ...         "fields": {"extracted": "data"}
    ...     }
    ...     return {"node_outputs": {node_id: node_output}}

Related Modules:
    - backend.services.workflow.state.reducers: Custom reducer functions
    - backend.services.execution.state: Execution tracking utilities
    - langgraph.graph.state: LangGraph's state management system
"""

from typing import Annotated, Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# Import reducer functions - these are used in Annotated type hints
from .reducers import (
    last_value_reducer,
    max_execution_order,
    merge_metadata,
    merge_node_outputs,
    merge_results,
    merge_review_state,
)


class NodeOutput(TypedDict, total=False):
    """
    Output structure from a single node execution.

    This structure captures the different output formats that a node can produce,
    allowing downstream nodes to access data in the most appropriate format.

    Attributes:
        raw: The raw text output from the node (e.g., LLM response text)
        structured: Parsed structured/JSON output if the node produces structured data
        fields: Extracted fields as a dictionary for easy downstream consumption

    Example:
        >>> output: NodeOutput = {
        ...     "raw": "The answer is 42",
        ...     "structured": {"answer": 42, "confidence": 0.95},
        ...     "fields": {"answer": 42}
        ... }

    Note:
        - All fields are optional (total=False)
        - Nodes may populate only the fields relevant to their output type
        - The 'fields' dict is typically used for template variable replacement
    """

    raw: str
    structured: Optional[Dict[str, Any]]
    fields: Dict[str, Any]


class NodeResult(TypedDict, total=False):
    """
    Result entry for tracking execution history.

    This structure stores information about a completed node execution,
    useful for debugging, audit trails, and result aggregation.

    Attributes:
        agent: Name of the agent (if this was an agent node)
        response: The text response/output from the node
        tools: List of tool names that were used during execution
        tool_executions: Detailed information about each tool execution

    Example:
        >>> result: NodeResult = {
        ...     "agent": "ResearchAgent",
        ...     "response": "Found 5 relevant papers",
        ...     "tools": ["web_search", "document_reader"],
        ...     "tool_executions": [{"tool": "web_search", "status": "success"}]
        ... }

    Note:
        - Accumulated in the WorkflowState.results list
        - Useful for generating execution summaries
    """

    agent: Optional[str]
    response: str
    tools: List[str]
    tool_executions: List[Dict[str, Any]]


class WorkflowMetadata(TypedDict, total=False):
    """
    Metadata for workflow execution tracking and debugging.

    This structure stores execution metadata that helps track the workflow's
    progress, timing, and any errors that occurred.

    Attributes:
        execution_started: ISO 8601 timestamp when execution began
        execution_ended: ISO 8601 timestamp when execution completed
        current_node_name: Display name of the currently executing node
        current_node_type: Type of current node (AGENT, CONDITION, etc.)
        initial_input: The original input that started the workflow
        error: Error message if the workflow encountered an error
        token_counts: Token usage statistics (prompt, completion, total)

    Example:
        >>> metadata: WorkflowMetadata = {
        ...     "execution_started": "2025-10-13T10:30:00Z",
        ...     "current_node_name": "DataProcessor",
        ...     "current_node_type": "AGENT",
        ...     "initial_input": {"message": "Process this data"},
        ...     "token_counts": {"prompt": 150, "completion": 200, "total": 350}
        ... }
    """

    execution_started: str
    execution_ended: Optional[str]
    current_node_name: Optional[str]
    current_node_type: Optional[str]
    initial_input: Dict[str, Any]
    error: Optional[str]
    token_counts: Optional[Dict[str, int]]


class MemoryContext(TypedDict, total=False):
    """
    Memory context for conversation history and memory-enabled agents.

    This structure stores conversation history and metadata for agents
    that maintain memory across multiple interactions.

    Attributes:
        conversation_id: Unique identifier for the conversation
        messages: List of conversation messages (role + content)
        summary: Optional summarized version of the conversation history
        metadata: Additional metadata about the conversation

    Example:
        >>> memory: MemoryContext = {
        ...     "conversation_id": "conv-123",
        ...     "messages": [
        ...         {"role": "user", "content": "Hello"},
        ...         {"role": "assistant", "content": "Hi there!"}
        ...     ],
        ...     "summary": "User greeted assistant",
        ...     "metadata": {"topic": "greeting"}
        ... }
    """

    conversation_id: str
    messages: List[Dict[str, str]]
    summary: Optional[str]
    metadata: Dict[str, Any]


class OrchestrationContext(TypedDict, total=False):
    """
    Context for orchestrator nodes managing subagents.

    This structure tracks information about orchestrator nodes that
    delegate work to subagents and aggregate their results.

    Attributes:
        orchestrator_id: Unique identifier for the orchestrator
        orchestrator_name: Display name of the orchestrator
        delegation_count: Number of times subagents have been delegated to
        subagent_executions: List of subagent execution records
        subagent_results: Aggregated results from all subagent executions

    Example:
        >>> context: OrchestrationContext = {
        ...     "orchestrator_id": "orch-1",
        ...     "orchestrator_name": "MainOrchestrator",
        ...     "delegation_count": 3,
        ...     "subagent_executions": [{"agent": "Agent1", "status": "completed"}],
        ...     "subagent_results": {"Agent1": {"output": "Result"}}
        ... }
    """

    orchestrator_id: str
    orchestrator_name: str
    delegation_count: int
    subagent_executions: List[Dict[str, Any]]
    subagent_results: Dict[str, Any]


class WorkflowState(TypedDict):
    """
    Main state dictionary that flows through the LangGraph workflow.

    This is the core state structure used by LangGraph's state management system.
    Each node receives this state as input and returns updates to merge into it.
    Custom reducer functions (imported from .reducers) control how updates are merged.

    State Fields:
        Core Message Handling:
            - messages: LangChain message history (uses LangGraph's add_messages reducer)
            - original_message: Original input message preserved throughout execution

        Node Tracking:
            - node_outputs: Maps node_id -> NodeOutput (uses merge_node_outputs reducer)
            - results: List of execution history entries (uses merge_results reducer)

        Execution Context:
            - current_node: Currently executing node ID (uses last_value_reducer)
            - execution_id: Unique UUID for this workflow execution
            - db_execution_id: Database ID for persistence
            - graph_name: Name of the graph being executed
            - execution_order: Sequential order counter (uses max_execution_order reducer)

        Metadata & Contexts:
            - metadata: Execution metadata (uses merge_metadata reducer)
            - memory_context: Conversation memory (if enabled)
            - orchestration_context: Orchestrator tracking (if applicable)
            - subgraph_context: Subgraph delegation info (if applicable)

        Custom Data:
            - custom_data: Arbitrary data passed between nodes
            - file_info: File information for FILE_READ nodes

    Reducer Functions:
        The Annotated types use custom reducers that define merge behavior:
        - add_messages: LangGraph's built-in message list reducer
        - merge_node_outputs: Merges node output dictionaries
        - merge_results: Concatenates result lists from parallel nodes
        - last_value_reducer: Keeps the last non-None value
        - max_execution_order: Takes the maximum value
        - merge_metadata: Merges metadata, preferring newer non-None values

    Example:
        >>> from langgraph.graph import StateGraph
        >>> from langchain_core.messages import HumanMessage
        >>>
        >>> # Create initial state
        >>> initial_state: WorkflowState = {
        ...     "messages": [HumanMessage(content="Hello")],
        ...     "original_message": "Hello",
        ...     "node_outputs": {},
        ...     "results": [],
        ...     "current_node": None,
        ...     "execution_id": "exec-123",
        ...     "db_execution_id": 1,
        ...     "graph_name": "my_graph",
        ...     "metadata": {
        ...         "execution_started": "2025-10-13T10:00:00Z",
        ...         "initial_input": {"message": "Hello"}
        ...     },
        ...     "memory_context": None,
        ...     "orchestration_context": None,
        ...     "custom_data": None,
        ...     "execution_order": 0,
        ...     "subgraph_context": None,
        ...     "file_info": None
        ... }
        >>>
        >>> # Create workflow
        >>> workflow = StateGraph(WorkflowState)
        >>> workflow.add_node("my_node", lambda state: {"current_node": "my_node"})

    See Also:
        - backend.services.workflow.state.reducers: Reducer function implementations
        - langgraph.graph.state: LangGraph state management documentation
    """

    # Import reducers at type annotation level
    # These are imported inline in the Annotated types to avoid circular imports

    # Core message handling with LangGraph's message reducer
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Original input preservation
    original_message: str

    # Node outputs tracking - maps node_id to output with merge reducer
    node_outputs: Annotated[Dict[str, NodeOutput], merge_node_outputs]

    # Results accumulator for execution history - with reducer for parallel nodes
    results: Annotated[List[NodeResult], merge_results]

    # Current execution context - with reducer for concurrent updates
    current_node: Annotated[Optional[str], last_value_reducer]
    execution_id: str
    db_execution_id: Optional[int]
    graph_name: str

    # Metadata for tracking and debugging - with reducer for concurrent updates
    metadata: Annotated[WorkflowMetadata, merge_metadata]

    # Optional contexts
    memory_context: Optional[MemoryContext]
    orchestration_context: Optional[OrchestrationContext]

    # Custom data passed between nodes
    custom_data: Optional[Dict[str, Any]]

    # Execution order tracking - with reducer for parallel nodes
    execution_order: Annotated[int, max_execution_order]

    # Subgraph context for delegations
    subgraph_context: Optional[Dict[str, Any]]

    # File information for FILE_READ nodes
    file_info: Optional[Dict[str, Any]]

    # User ID for OAuth token lookup (MCP tools, etc.)
    user_id: Optional[str]

    # Pending review state for agent review resumption
    # Stores agent output and review context when paused for human review
    # Cleared after approval/rejection to allow normal agent execution
    pending_review: Annotated[Optional[Dict[str, Any]], last_value_reducer]

    # Review state for agent review loop - persists across node executions
    # Maps node_id -> {output, config, iteration, history, input_message}
    # Used by Review Node to maintain feedback loop state
    # Cleared (set to None for node_id) when review is approved/completed
    review_state: Annotated[Dict[str, Dict[str, Any]], merge_review_state]

    # Workflow ID for violation attribution and tracking
    workflow_id: Optional[str]

    # Guardrails state for cumulative tracking across the execution
    # Tracks: { "token_budget_used": { "input_tokens": N, "output_tokens": N,
    #            "total_tokens": N, "llm_calls": N },
    #           "tool_calls_count": N, "violations": [...],
    #           "llm_guard_vault": <llm_guard.vault.Vault instance, created per-execution> }
    guardrails_state: Annotated[Optional[Dict[str, Any]], last_value_reducer]

    # Resolved workflow-level guardrails pipeline (list of serialized dicts, each via
    # GuardrailsConfig.to_dict()).  Each entry carries priority, policy_id, policy_name,
    # and enforcement_mode.  Resolved once at execution start and applied as a baseline
    # to all non-agent node ingress/egress.  Agent nodes resolve their own config via the
    # policy service which already includes workflow policies through the layered
    # resolution hierarchy.
    workflow_guardrails_pipeline: Annotated[Optional[List[Dict[str, Any]]], last_value_reducer]


# Type annotations for common state operations
StateUpdate = Dict[str, Any]  # Partial state update dictionary
StateTransition = tuple[str, StateUpdate]  # Tuple of (next_node_id, state_update)
