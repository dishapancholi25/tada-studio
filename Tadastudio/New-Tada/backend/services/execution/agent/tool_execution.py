"""Tool execution and tracking for agent execution.

This module handles wrapping tools with execution tracking for different tool types
including HTTP requests, web search, MCP servers, and more.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import ToolMessage
from langchain_core.tools import StructuredTool


logger = logging.getLogger("agent_execution")


class ToolExecutionTracker:
    """Handles tool execution and tracking."""

    @staticmethod
    def wrap_tools_with_tracking(
        tools: List[Any],
        tool_execution_tracker: Optional[List] = None,
    ) -> List[Any]:
        """Wrap tools to track their executions.

        Args:
            tools: List of tools to wrap
            tool_execution_tracker: Optional list to append execution data to

        Returns:
            List of wrapped tools
        """
        if tool_execution_tracker is None:
            return tools

        wrapped_tools = []
        for tool in tools:
            if not hasattr(tool, "name"):
                wrapped_tools.append(tool)
                continue

            tool_name = tool.name

            # Document search and database query tools are already tracked
            # in _create_serializable_tools, don't double-wrap
            if tool_name in [
                "search_documents",
                "query_database",
            ] or tool_name.startswith("http_request_"):
                wrapped_tools.append(tool)
            elif tool_name.startswith("search_web_"):
                # Track web search tool executions
                wrapped_tool = _create_web_search_tracker(tool, tool_execution_tracker)
                wrapped_tools.append(wrapped_tool)
            else:
                # Pass through other tools without wrapping
                wrapped_tools.append(tool)

        return wrapped_tools

    @staticmethod
    def execute_tool_calls(
        tool_calls: List[Dict],
        tools: List[Any],
        messages: List[Any],
        tool_execution_tracker: Optional[List] = None,
    ) -> None:
        """Execute tool calls and append results to messages.

        Args:
            tool_calls: List of tool call dictionaries
            tools: List of available tools
            messages: Message list to append results to
            tool_execution_tracker: Optional list to track executions
        """
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            logger.info(f"Executing tool: {tool_name} with args: {tool_args}")

            # Find and execute the tool
            tool_executed = False
            for tool in tools:
                if tool.name == tool_name:
                    try:
                        # Special handling for HTTP request tools
                        if tool_name.startswith("http_request_"):
                            tool_result = _execute_http_request_tool(
                                tool, tool_args, tool_call, tool_execution_tracker
                            )
                        else:
                            tool_result = tool.invoke(tool_args)

                        # Track additional tool types
                        if tool_execution_tracker is not None:
                            _track_tool_execution(
                                tool_name,
                                tool_args,
                                tool_result,
                                tool_call,
                                tool_execution_tracker,
                            )

                        messages.append(
                            ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_call["id"],
                            )
                        )
                        tool_executed = True
                        break
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        messages.append(
                            ToolMessage(
                                content=f"Error: {str(e)}",
                                tool_call_id=tool_call["id"],
                            )
                        )
                        tool_executed = True
                        break

            if not tool_executed:
                logger.warning(f"Tool {tool_name} not found in available tools")


def _create_web_search_tracker(
    tool: Any, tool_execution_tracker: List
) -> StructuredTool:
    """Create a wrapped web search tool that tracks executions.

    Args:
        tool: Original web search tool
        tool_execution_tracker: List to append execution data to

    Returns:
        Wrapped StructuredTool
    """
    tool_name = tool.name

    def tracked_web_search(query: str) -> str:
        """Execute web search and track the execution."""
        # Call the original tool
        search_result = tool.invoke({"query": query})

        # Detect provider from result structure
        provider = "unknown"
        raw_results = []

        # Parse the result text to detect provider
        if isinstance(search_result, str):
            if "Tavily search for" in search_result or "AI Answer:" in search_result:
                provider = "tavily"
            elif (
                "Search Results (5 found):" in search_result
                or "DuckDuckGo" in search_result
            ):
                provider = "duckduckgo"

            # Also check if we got structured results from Tavily
            if hasattr(tool, "func") and hasattr(tool.func, "_last_execution"):
                metadata = tool.func._last_execution
                provider = metadata.get("provider", provider)
                raw_results = metadata.get("raw_results", [])

        # Track the execution with enhanced metadata
        tool_execution_tracker.append(
            {
                "tool": tool_name,
                "query": query,
                "results": search_result
                if isinstance(search_result, str)
                else str(search_result),
                "provider": provider,
                "raw_results": raw_results,
                "formatted_results": search_result,
                "timestamp": datetime.now().isoformat(),
                "call_id": f"react_{datetime.now().timestamp()}",
            }
        )
        return search_result

    # Create a new StructuredTool with the tracked function
    return StructuredTool(
        name=tool.name,
        description=tool.description,
        func=tracked_web_search,
        args_schema=tool.args_schema if hasattr(tool, "args_schema") else None,
    )


def _execute_http_request_tool(
    tool: Any,
    tool_args: Dict,
    tool_call: Dict,
    tool_execution_tracker: Optional[List],
) -> str:
    """Execute HTTP request tool with special handling.

    Args:
        tool: HTTP request tool
        tool_args: Tool arguments
        tool_call: Tool call dictionary
        tool_execution_tracker: Optional execution tracker

    Returns:
        Tool execution result
    """
    # HTTP request tool expects a 'parameters' string with JSON
    # Convert the tool_args dict to a JSON string
    tool_result = tool.invoke({"parameters": json.dumps(tool_args)})

    # Track HTTP request tool executions with structured metadata
    if tool_execution_tracker is not None:
        _track_http_request_execution(
            tool.name, tool_args, tool_result, tool_call, tool_execution_tracker
        )

    return tool_result


def _track_http_request_execution(
    tool_name: str,
    tool_args: Dict,
    tool_result: str,
    tool_call: Dict,
    tool_execution_tracker: List,
) -> None:
    """Track HTTP request execution with metadata.

    Args:
        tool_name: Name of the HTTP request tool
        tool_args: Tool arguments
        tool_result: Tool execution result
        tool_call: Tool call dictionary
        tool_execution_tracker: List to append execution data to
    """
    http_exec_data = {
        "tool": tool_name,
        "kwargs": tool_args,
        "parameters": tool_args.get("parameters", "")
        if isinstance(tool_args, dict)
        else str(tool_args),
        "results": tool_result if isinstance(tool_result, str) else str(tool_result),
        "timestamp": datetime.now().isoformat(),
        "call_id": tool_call["id"],
    }

    # Try to get structured execution metadata from thread-local storage
    try:
        from backend.tools.http_request import (
            get_http_execution_for_node,
            get_last_http_execution,
        )

        # Extract node_id from tool_name (format: http_request_<node_id>)
        node_id = tool_name.replace("http_request_", "")

        # Try to get metadata for specific node first
        last_exec = get_http_execution_for_node(node_id)
        if not last_exec:
            # Fallback to last execution
            last_exec = get_last_http_execution()

        if last_exec:
            # Replace basic execution data with full HTTP metadata
            http_exec_data = {
                "tool": tool_name,  # Keep the specific tool name with node ID
                "request": last_exec.get("request", {}),
                "response": last_exec.get("response", {}),
                "config": last_exec.get("config", {}),
                "timestamp": last_exec.get("timestamp", datetime.now().isoformat()),
                "call_id": last_exec.get("call_id", tool_call["id"]),
                "duration": last_exec.get("response", {}).get("elapsed", 0),
                "execution_index": 0,  # Regular execution happens sequentially
            }
            logger.info(f"Captured structured HTTP execution metadata for {tool_name}")
            logger.info(
                f"HTTP metadata: request method={http_exec_data['request'].get('method')}, "
                f"status={http_exec_data['response'].get('status_code')}"
            )
        else:
            logger.warning(f"No HTTP execution metadata found for {tool_name}")
    except Exception as e:
        logger.error(f"Failed to get HTTP execution metadata: {e}")

    tool_execution_tracker.append(http_exec_data)


def _track_tool_execution(
    tool_name: str,
    tool_args: Dict,
    tool_result: Any,
    tool_call: Dict,
    tool_execution_tracker: List,
) -> None:
    """Track tool execution for various tool types.

    Args:
        tool_name: Name of the tool
        tool_args: Tool arguments
        tool_result: Tool execution result
        tool_call: Tool call dictionary
        tool_execution_tracker: List to append execution data to
    """
    # Skip tools already tracked elsewhere
    if tool_name in ["search_documents", "query_database"] or tool_name.startswith(
        "http_request_"
    ):
        return

    # Track web search executions
    if tool_name.startswith("search_web_"):
        _track_web_search_execution(
            tool_name, tool_args, tool_result, tool_call, tool_execution_tracker
        )
    # Track MCP tool executions
    elif tool_name.startswith("mcp_adapter_") or tool_name.startswith("mcp_server_"):
        _track_mcp_execution(
            tool_name, tool_args, tool_result, tool_call, tool_execution_tracker
        )


def _track_web_search_execution(
    tool_name: str,
    tool_args: Dict,
    tool_result: Any,
    tool_call: Dict,
    tool_execution_tracker: List,
) -> None:
    """Track web search tool execution.

    Args:
        tool_name: Name of the web search tool
        tool_args: Tool arguments
        tool_result: Tool execution result
        tool_call: Tool call dictionary
        tool_execution_tracker: List to append execution data to
    """
    # Detect provider from result
    provider = "unknown"
    raw_results = []

    if isinstance(tool_result, str):
        # Check result content to determine provider
        if "AI Answer:" in tool_result or "Relevance:" in tool_result:
            provider = "tavily"
        elif "Search Results (5 found):" in tool_result:
            provider = "duckduckgo"

        # Log to help debug
        logger.info(f"Web search result detected as {provider} based on content")

    tool_execution_tracker.append(
        {
            "tool": tool_name,
            "query": tool_args.get("query", "")
            if isinstance(tool_args, dict)
            else str(tool_args),
            "results": tool_result
            if isinstance(tool_result, str)
            else str(tool_result),
            "provider": provider,
            "raw_results": raw_results,
            "formatted_results": tool_result,
            "timestamp": datetime.now().isoformat(),
            "call_id": tool_call["id"],
        }
    )


def _track_mcp_execution(
    tool_name: str,
    tool_args: Dict,
    tool_result: Any,
    tool_call: Dict,
    tool_execution_tracker: List,
) -> None:
    """Track MCP tool execution.

    Args:
        tool_name: Name of the MCP tool
        tool_args: Tool arguments
        tool_result: Tool execution result
        tool_call: Tool call dictionary (contains tool object)
        tool_execution_tracker: List to append execution data to
    """
    logger.info(f"[MCP TRACKING] MCP tool called: {tool_name}")
    logger.info(f"[MCP TRACKING] Tool args: {tool_args}")

    # Track MCP tool executions
    # Extract MCP execution details if available
    mcp_exec_data = {
        "tool": tool_name,
        "input": tool_args,
        "results": tool_result if isinstance(tool_result, str) else str(tool_result),
        "timestamp": datetime.now().isoformat(),
        "call_id": tool_call["id"],
    }

    # Note: We can't access the tool object from tool_call dict here
    # This would need to be passed differently if detailed metadata is needed
    logger.info("[MCP TRACKING] No _last_execution attribute access available")

    logger.info(
        f"[MCP TRACKING] Adding MCP execution to tracker: "
        f"{mcp_exec_data.get('action', 'N/A')} - {mcp_exec_data.get('target', 'N/A')}"
    )
    tool_execution_tracker.append(mcp_exec_data)
    logger.info(
        f"[MCP TRACKING] Tool execution tracker now has "
        f"{len(tool_execution_tracker)} entries"
    )
