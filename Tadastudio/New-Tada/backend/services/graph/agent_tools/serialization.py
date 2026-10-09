"""Tool serialization and wrapping logic.

This module handles creating serializable tool wrappers that track execution
and handle complex input/output scenarios.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool, Tool

from backend.services.config import get_logger


logger = get_logger(__name__)
serialization_logger = logging.getLogger("tool_serialization")
context_logger = logging.getLogger("context_serialization")


def normalize_mcp_tool_input(input_data: Any, primary_arg: str) -> Any:
    """
    Best-effort coercion of agent-provided MCP tool inputs.

    Args:
        input_data: The raw input data from the agent
        primary_arg: The primary argument name for the MCP tool

    Returns:
        Normalized input dict
    """
    if isinstance(input_data, dict):
        if primary_arg not in input_data:
            if "input" in input_data and len(input_data) == 1:
                return {primary_arg: input_data["input"]}
        return input_data

    if isinstance(input_data, (list, tuple)):
        if not input_data:
            return {primary_arg: None}
        value = input_data[-1] if len(input_data) > 1 else input_data[0]
        return {primary_arg: value}

    if input_data is None:
        return {}

    return {primary_arg: input_data}


def _clean_input_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean input data of non-serializable objects.

    Args:
        input_data: Raw input dictionary

    Returns:
        Cleaned input dictionary
    """
    clean_input = {}
    for k, v in input_data.items():
        # Skip callback managers and other problematic objects
        if hasattr(v, "__class__") and any(
            word in v.__class__.__name__ for word in ["Callback", "Manager"]
        ):
            context_logger.debug(
                f"Skipping non-serializable field: {k} ({v.__class__.__name__})"
            )
            continue
        clean_input[k] = v

    context_logger.debug(f"Cleaned input: {clean_input}")
    return clean_input


def _handle_http_execution_tracking(
    original_tool_name: str,
    result: Any,
    tracking_entry: Optional[Dict[str, Any]],
    tool_execution_tracker: Optional[List],
    wrapper_func: Any,
) -> None:
    """
    Handle execution tracking for HTTP request tools.

    Args:
        original_tool_name: Name of the tool
        result: Execution result
        tracking_entry: Basic tracking entry
        tool_execution_tracker: List to append tracking data to
        wrapper_func: Wrapper function to store metadata on
    """
    try:
        from backend.tools.http_request import (
            get_http_execution_for_node,
            get_last_http_execution,
        )

        # Extract node_id from tool_name (format: http_request_<node_id>)
        node_id = original_tool_name.replace("http_request_", "")

        # Try to get metadata for specific node first
        execution_metadata = get_http_execution_for_node(node_id)
        if not execution_metadata:
            # Fallback to last execution
            execution_metadata = get_last_http_execution()

        if execution_metadata and tool_execution_tracker is not None:
            # Replace tracking entry with full HTTP metadata
            http_tracking_entry = {
                "tool": original_tool_name,
                "request": execution_metadata.get("request", {}),
                "response": execution_metadata.get("response", {}),
                "config": execution_metadata.get("config", {}),
                "timestamp": execution_metadata.get(
                    "timestamp", datetime.now().isoformat()
                ),
                "call_id": execution_metadata.get(
                    "call_id",
                    tracking_entry.get("call_id", "") if tracking_entry else "",
                ),
                "duration": execution_metadata.get("response", {}).get("elapsed", 0),
                "execution_index": 0,
            }
            tool_execution_tracker.append(http_tracking_entry)
            context_logger.info(
                "Captured HTTP request execution metadata from thread-local storage"
            )
            context_logger.info(
                f"HTTP metadata: URL={execution_metadata.get('request', {}).get('url')}, "
                f"method={execution_metadata.get('request', {}).get('method')}"
            )

            # Store it on the wrapper for later retrieval
            wrapper_func._last_execution = execution_metadata
            wrapper_func._tool_name = original_tool_name
        elif not execution_metadata:
            context_logger.warning(
                f"No HTTP execution metadata found in thread-local storage for {original_tool_name}"
            )
            # Fall back to basic tracking entry
            if tracking_entry is not None and tool_execution_tracker is not None:
                tracking_entry["results"] = (
                    result if isinstance(result, str) else str(result)
                )
                tool_execution_tracker.append(tracking_entry)

    except Exception as e:
        context_logger.error(f"Error retrieving HTTP execution metadata: {e}")
        # Fall back to basic tracking entry
        if tracking_entry is not None and tool_execution_tracker is not None:
            tracking_entry["results"] = (
                result if isinstance(result, str) else str(result)
            )
            tool_execution_tracker.append(tracking_entry)


def _create_tool_wrapper(
    original_tool: Any,
    original_tool_name: str,
    tool_execution_tracker: Optional[List] = None,
) -> Any:
    """
    Create a wrapper function for a tool that handles execution tracking.

    Args:
        original_tool: The original tool to wrap
        original_tool_name: Name of the tool
        tool_execution_tracker: Optional list to track executions

    Returns:
        Wrapper function
    """

    def wrapper_func(*args, **kwargs):
        context_logger.info(f"=== TOOL EXECUTION: {original_tool_name} ===")
        context_logger.info(f"Input args: {args}, kwargs: {kwargs}")

        # Check if this is being called from structured output context
        is_structured_call = kwargs.get("_from_structured_output", False)
        if "_from_structured_output" in kwargs:
            kwargs.pop("_from_structured_output")

        # Handle positional arguments
        if args and not kwargs:
            input_data = args[0] if len(args) == 1 else args
            context_logger.info(
                f"Positional arg input - type: {type(input_data)}, data: {input_data}"
            )
        # Handle old style (single input_data)
        elif len(kwargs) == 1 and "input_data" in kwargs:
            input_data = kwargs["input_data"]
            context_logger.info(
                f"Old style input - type: {type(input_data)}, data: {input_data}"
            )
        else:
            # New style - filter out system kwargs
            system_keys = {
                "args",
                "config",
                "callbacks",
                "tags",
                "metadata",
                "run_name",
                "run_id",
            }
            input_data = {k: v for k, v in kwargs.items() if k not in system_keys}
            context_logger.info(f"New style input - filtered data: {input_data}")

        # Handle MCP tool input normalization
        mcp_primary_arg = getattr(original_tool, "_mcp_primary_arg", None)
        if mcp_primary_arg:
            context_logger.debug(
                f"[MCP] Normalizing raw input for {original_tool_name} "
                f"using primary arg '{mcp_primary_arg}'"
            )
            input_data = normalize_mcp_tool_input(input_data, mcp_primary_arg)

        # Prepare tracking entry
        tracking_entry = None
        if tool_execution_tracker is not None and not is_structured_call:
            tracking_entry = {
                "tool": original_tool_name,
                "kwargs": input_data
                if isinstance(input_data, dict)
                else {"input": input_data},
                "node_id": getattr(original_tool, "_mcp_node_id", None),
                "node_name": getattr(original_tool, "_mcp_node_name", None),
                "timestamp": datetime.now().isoformat(),
            }

        try:
            # Clean input_data if dict
            if isinstance(input_data, dict):
                clean_input = _clean_input_data(input_data)

                # Handle single argument tools (except HTTP request with parameter schemas)
                if len(clean_input) == 1 and not original_tool_name.startswith(
                    "http_request_"
                ):
                    value = list(clean_input.values())[0]
                    context_logger.info(f"Single argument tool, invoking with: {value}")
                    result = original_tool.invoke(value)
                elif clean_input:
                    # For HTTP request tools, pass kwargs directly
                    if original_tool_name.startswith("http_request_"):
                        context_logger.info(
                            f"HTTP request tool, invoking with kwargs: {clean_input}"
                        )
                        result = original_tool.invoke(clean_input)
                    else:
                        context_logger.info(
                            f"Multi-argument tool, invoking with dict: {clean_input}"
                        )
                        result = original_tool.invoke(clean_input)
                else:
                    context_logger.info(f"No clean input, using original: {input_data}")
                    result = original_tool.invoke(input_data)
            else:
                context_logger.info(
                    f"Non-dict input, invoking directly with: {input_data}"
                )
                result = original_tool.invoke(input_data)

            context_logger.info("Tool execution successful")
            context_logger.debug(f"Result: {str(result)[:200]}...")

            # Handle execution tracking
            if original_tool_name.startswith("http_request_"):
                _handle_http_execution_tracking(
                    original_tool_name,
                    result,
                    tracking_entry,
                    tool_execution_tracker,
                    wrapper_func,
                )
            else:
                # For non-HTTP tools, add results to tracking entry
                if tracking_entry is not None and tool_execution_tracker is not None:
                    tracking_entry["results"] = (
                        result if isinstance(result, str) else str(result)
                    )
                    tool_execution_tracker.append(tracking_entry)

            return result

        except Exception as e:
            context_logger.error(
                f"Error executing {original_tool_name}: {str(e)}", exc_info=True
            )
            if tracking_entry is not None and tool_execution_tracker is not None:
                tracking_entry["error"] = str(e)
                tool_execution_tracker.append(tracking_entry)
            return f"Error executing {original_tool_name}: {str(e)}"

    return wrapper_func


def create_serializable_tools(
    tools: List[Any], tool_execution_tracker: Optional[List] = None
) -> List[Any]:
    """
    Create tools that won't cause JSON serialization issues.

    This function wraps tools to:
    1. Handle complex input/output scenarios
    2. Track tool executions
    3. Remove non-serializable objects
    4. Preserve structured tool schemas

    Args:
        tools: List of tools to wrap
        tool_execution_tracker: Optional list to track tool executions

    Returns:
        List of wrapped, serializable tools
    """
    serialization_logger.info("=== CREATING SERIALIZABLE TOOLS ===")
    serialization_logger.info(f"Input tools count: {len(tools)}")

    clean_tools = []

    for tool in tools:
        try:
            # Get tool properties
            tool_name = getattr(tool, "name", "unknown")
            tool_description = getattr(tool, "description", "")

            serialization_logger.info(f"Processing tool: {tool_name}")
            serialization_logger.debug(f"Tool type: {type(tool)}")
            serialization_logger.debug(f"Tool description: {tool_description[:100]}...")

            # Create wrapper
            wrapper = _create_tool_wrapper(tool, tool_name, tool_execution_tracker)

            # Create clean tool preserving structured schema if available
            if hasattr(tool, "args_schema") and tool.args_schema:
                # For StructuredTools with schemas, preserve the schema
                clean_tool = StructuredTool(
                    name=tool_name,
                    description=tool_description,
                    func=wrapper,
                    args_schema=tool.args_schema,
                )
            else:
                # For simple tools without schemas
                clean_tool = Tool(
                    name=tool_name,
                    description=tool_description,
                    func=wrapper,
                )

            clean_tools.append(clean_tool)
            serialization_logger.info(f"Created clean tool: {tool_name}")

        except Exception as e:
            serialization_logger.error(
                f"Failed to create clean tool for {getattr(tool, 'name', 'unknown')}: {e}",
                exc_info=True,
            )
            continue

    serialization_logger.info("=== SERIALIZABLE TOOLS COMPLETE ===")
    serialization_logger.info(f"Created {len(clean_tools)} clean tools")

    return clean_tools
