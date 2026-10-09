"""
Type definitions for tool execution data extraction.

This module provides TypedDict definitions for tool execution data structures,
improving type safety and code clarity throughout the tool extraction system.
"""

from typing import Any, Dict, TypedDict


class ToolExecutionData(TypedDict, total=False):
    """
    Data structure for tool execution information.

    This TypedDict represents the various formats that tool execution
    data can take, with all fields optional since different tools
    use different structures.

    Attributes:
        tool: Name of the tool that was executed
        input: Direct input data (some tools)
        kwargs: Keyword arguments passed to the tool
        query: Query string (search/query-based tools)
        parameters: Request parameters (HTTP tools)
        request: HTTP request data
        response: HTTP response data
        config: Tool configuration
        output: Tool output/result
        results: Tool results (alternative name)
        result: Tool result (alternative name)
        formatted_results: Pre-formatted results
        formatted_output: Pre-formatted output
        execution_time: Execution duration in seconds
        execution_time_ms: Execution duration in milliseconds
        timestamp: ISO timestamp of execution
        call_id: Unique identifier for this tool call
        duration: Duration of execution
        execution_index: Index in execution sequence
        status_code: HTTP status code (HTTP tools)
        provider: Provider name (search tools)
    """

    tool: str
    input: Any
    kwargs: Dict[str, Any]
    query: str
    parameters: Dict[str, Any]
    request: Dict[str, Any]
    response: Dict[str, Any]
    config: Dict[str, Any]
    output: Any
    results: Any
    result: Any
    formatted_results: str
    formatted_output: str
    execution_time: float
    execution_time_ms: float
    timestamp: str
    call_id: str
    duration: float
    execution_index: int
    status_code: int
    provider: str


class ToolInputData(TypedDict, total=False):
    """
    Extracted input data from a tool execution.

    This represents the cleaned/extracted input parameters
    that were passed to a tool.

    Attributes:
        query: Search/query string
        url: HTTP request URL
        method: HTTP request method
        headers: HTTP request headers
        body: HTTP request body
        params: Request parameters
        query_params: Query parameters
        input: Generic input field
        parameters: Generic parameters field
        request: Full request object
    """

    query: str
    url: str
    method: str
    headers: Dict[str, Any]
    body: Any
    params: Dict[str, Any]
    query_params: Dict[str, Any]
    input: Any
    parameters: Dict[str, Any]
    request: Dict[str, Any]


class ToolOutputData(TypedDict, total=False):
    """
    Extracted output data from a tool execution.

    This represents the cleaned/extracted output and metadata
    from a tool execution.

    Attributes:
        result: The tool's result/output
        execution_time: Time taken to execute (seconds)
        tool_call_id: Unique identifier for this tool call
        timestamp: ISO timestamp of execution
        provider: Provider used (for search tools)
        formatted_results: Pre-formatted results
        formatted_output: Pre-formatted output
        status_code: HTTP status code
        tool: Tool name (for HTTP metadata format)
        request: HTTP request data (for HTTP metadata format)
        response: HTTP response data (for HTTP metadata format)
        config: Tool configuration (for HTTP metadata format)
        call_id: Tool call ID (for HTTP metadata format)
        duration: Execution duration (for HTTP metadata format)
        execution_index: Execution sequence index (for HTTP metadata format)
    """

    result: Any
    execution_time: float
    tool_call_id: str
    timestamp: str
    provider: str
    formatted_results: str
    formatted_output: str
    status_code: int
    # HTTP metadata format fields
    tool: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    config: Dict[str, Any]
    call_id: str
    duration: float
    execution_index: int


class HttpRequestMetadata(TypedDict, total=False):
    """
    Full HTTP request metadata structure.

    This is the complete metadata format returned for HTTP request tools,
    containing both request and response data along with execution metadata.

    Attributes:
        tool: Always "http_request"
        request: HTTP request details
        response: HTTP response details
        config: HTTP tool configuration
        timestamp: ISO timestamp of execution
        call_id: Unique identifier for this tool call
        duration: Request duration
        execution_index: Index in execution sequence
    """

    tool: str  # Should be "http_request"
    request: Dict[str, Any]
    response: Dict[str, Any]
    config: Dict[str, Any]
    timestamp: str
    call_id: str
    duration: float
    execution_index: int
