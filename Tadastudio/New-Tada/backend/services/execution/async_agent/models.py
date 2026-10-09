"""Pydantic models for async agent execution.

This module defines type-safe data models for agent execution configuration,
results, and intermediate states, providing validation and clear interfaces.
"""

from typing import Any, Dict, List, Optional, Union

from langchain_core.messages import AIMessage
from pydantic import BaseModel, Field


class TokenCounts(BaseModel):
    """Token usage information for an agent execution.

    Tracks input, output, and total token counts along with the model
    identifier for accurate cost and usage tracking.
    """

    input_tokens: int = Field(default=0, ge=0, description="Number of input tokens")
    output_tokens: int = Field(default=0, ge=0, description="Number of output tokens")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens used")
    model: Optional[str] = Field(default=None, description="Model identifier")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="LLM response metadata"
    )

    def add_counts(self, other: "TokenCounts") -> None:
        """Add counts from another TokenCounts instance.

        Args:
            other: TokenCounts to add to this instance
        """
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens
        self.total_tokens += other.total_tokens


class ExecutionConfig(BaseModel):
    """Configuration for async agent execution.

    Controls various aspects of agent execution including output formatting,
    memory usage, token counting, and execution tracking.
    """

    format_output: bool = Field(
        default=True,
        description="Whether to format output using structured outputs if configured",
    )
    db_execution_id: Optional[str] = Field(
        default=None, description="Database execution ID for memory and tracking"
    )
    tool_execution_tracker: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="List to track tool executions (passed by reference)"
    )
    return_token_counts: bool = Field(
        default=False, description="Whether to return token counts with response"
    )
    enable_memory: bool = Field(
        default=True, description="Whether to use memory (if agent has memory enabled)"
    )
    execution_id: Optional[str] = Field(
        default=None, description="WebSocket/thread execution identifier for streaming"
    )
    graph_name: Optional[str] = Field(
        default=None, description="Graph name (for tool lookup and telemetry)"
    )
    node_id: Optional[str] = Field(
        default=None, description="Current agent node id (for streaming attribution)"
    )
    user_id: Optional[str] = Field(
        default=None, description="User ID for OAuth token lookup in MCP tools"
    )
    tool_node_mapping: Optional[Dict[str, Dict[str, str]]] = Field(
        default=None,
        description="Mapping from synthetic tool names to workflow node info (node_id, node_name, node_type)",
    )
    review_iteration: Optional[int] = Field(
        default=None,
        description="Current review iteration number (1-indexed) for tool-to-iteration association",
    )
    node_execution_id: Optional[str] = Field(
        default=None,
        description="Database UUID of the agent's NodeExecution record",
    )
    workflow_id: Optional[str] = Field(
        default=None,
        description="Workflow ID for guardrail violation attribution",
    )
    execution_order: Optional[int] = Field(
        default=None,
        description="Execution order for iteration discrimination in streaming events",
    )
    db_node_id: Optional[str] = Field(
        default=None,
        description="Database node execution ID for precise streaming attribution",
    )
    is_subagent: bool = Field(
        default=False,
        description="Whether this is a subagent execution that needs explicit token streaming",
    )
    invocation_index: Optional[int] = Field(
        default=None,
        description="Which invocation of this subagent (1st, 2nd, etc.) for tool-to-invocation association",
    )
    parent_subagent_id: Optional[str] = Field(
        default=None,
        description="Unique ID of parent subagent invocation (format: {node_id}_iter_{iteration}) for tool-to-subagent association",
    )
    conversation_history: Optional[List[Any]] = Field(
        default=None,
        description="Structured chat conversation history as BaseMessage objects for chat-triggered executions",
    )

    class Config:
        arbitrary_types_allowed = True


class ExecutionResult(BaseModel):
    """Result of async agent execution.

    Contains the agent's response, token usage information, tool execution
    records, and additional metadata about the execution.
    """

    response: Union[str, Dict[str, Any], AIMessage] = Field(
        description="Agent response (format depends on structured output settings)"
    )
    token_counts: Optional[TokenCounts] = Field(
        default=None, description="Token usage information"
    )
    tool_executions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Record of tool executions"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional execution metadata"
    )
    message_structure: Optional[Dict[str, Any]] = Field(
        default=None, description="Full conversation message structure for trace viewer"
    )

    class Config:
        arbitrary_types_allowed = True

    def to_tuple(self) -> tuple:
        """Convert result to (response, token_counts, tool_executions, message_structure, metadata) tuple.

        Returns:
            Tuple of (response, token_counts dict or None, tool_executions list,
            message_structure or None, metadata dict)
        """
        token_dict = self.token_counts.dict() if self.token_counts else None
        return (self.response, token_dict, self.tool_executions, self.message_structure, self.metadata)


class ToolExecutionRecord(BaseModel):
    """Record of a single tool execution.

    Captures complete information about a tool invocation including
    input, output, timing, and error information.
    """

    tool_name: str = Field(description="Name of the tool executed")
    tool_id: Optional[str] = Field(default=None, description="Tool call ID from LLM")
    input_args: Dict[str, Any] = Field(
        default_factory=dict, description="Arguments passed to the tool"
    )
    output: Optional[Any] = Field(default=None, description="Tool execution result")
    error: Optional[str] = Field(
        default=None, description="Error message if tool failed"
    )
    timestamp: Optional[float] = Field(
        default=None, description="Execution timestamp (epoch time)"
    )
    duration: Optional[float] = Field(
        default=None, description="Execution duration in seconds"
    )

    # HTTP-specific fields (for HTTP request tools)
    request: Optional[Dict[str, Any]] = Field(
        default=None, description="HTTP request data (if applicable)"
    )
    response: Optional[Dict[str, Any]] = Field(
        default=None, description="HTTP response data (if applicable)"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None, description="HTTP config data (if applicable)"
    )

    # Streaming status flag
    was_streamed: bool = Field(
        default=False,
        description="Whether streaming events were already emitted for this tool execution",
    )

    class Config:
        arbitrary_types_allowed = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility.

        Returns:
            Dict representation with non-null fields
        """
        result = {
            "tool": self.tool_name,
            "args": self.input_args,
            "input": self.input_args,
            "kwargs": self.input_args,
        }

        if self.tool_id:
            result["id"] = self.tool_id
            result["call_id"] = self.tool_id

        if self.output is not None:
            result["output"] = self.output
            result["result"] = self.output
            result["results"] = self.output

        if self.error:
            result["error"] = self.error

        if self.timestamp:
            result["timestamp"] = self.timestamp

        if self.duration:
            result["duration"] = self.duration

        # HTTP-specific fields
        if self.request:
            result["request"] = self.request
        if self.response:
            result["response"] = self.response
        if self.config:
            result["config"] = self.config

        # Streaming status (always include for explicit duplicate detection)
        result["was_streamed"] = self.was_streamed

        return result
