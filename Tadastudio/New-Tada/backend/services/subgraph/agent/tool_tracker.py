"""
Tool execution tracking for agent subgraphs.

This module handles creating database records and sending WebSocket notifications
for tool executions performed by sub-agents.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.execution.history import ExecutionHistoryService
from backend.services.common.utils.tool_type_mapper import (
    extract_base_tool_name,
    get_tool_node_type,
)
from backend.services.common.utils.websocket_notifier import (
    send_node_complete_notification,
)
from backend.services.config import get_logger


tool_tracker_logger = get_logger("subgraph.agent.tool_tracker")


class ResolutionStrategy(Enum):
    """How the tool node was resolved."""

    DIRECT_MAPPING = "direct_mapping"  # Found in tool_node_mapping
    DELEGATION_PARSE = "delegation_parse"  # Parsed from delegate_to_*
    FALLBACK = "fallback"  # Used agent node as fallback


@dataclass
class ToolNodeInfo:
    """Result of resolving a tool to its workflow node.

    Attributes:
        node_id: The resolved node's unique identifier
        node_name: Human-readable name of the node
        node_type: Type of the node (AGENT, DOCUMENT_SEARCH, etc.), or None if unknown
        is_delegation: True if this is a delegate_to_* tool
        is_fallback: True if resolution fell back to using agent node ID
        resolution_strategy: How the node was resolved
        fallback_reason: Explanation if fallback was used (for debugging)
    """

    node_id: str
    node_name: str
    node_type: Optional[NodeType]
    is_delegation: bool
    is_fallback: bool
    resolution_strategy: ResolutionStrategy
    fallback_reason: Optional[str] = None


def _find_agent_by_normalized_name(
    graph_manager: Any,
    graph_name: str,
    normalized_name: str,
) -> Optional[EnhancedNodeData]:
    """Find an agent node by its normalized name.

    Args:
        graph_manager: Graph manager instance
        graph_name: Name of the graph
        normalized_name: Lowercase name with underscores replaced by spaces

    Returns:
        The matching agent node, or None if not found
    """
    try:
        graph = graph_manager.get_graph(graph_name)
        if not graph or not graph.nodes:
            return None

        for node in graph.nodes:
            if node.type == NodeType.AGENT:
                node_name_normalized = node.name.lower()
                if node_name_normalized == normalized_name:
                    return node
        return None
    except Exception as e:
        tool_tracker_logger.error(f"Error finding agent by name: {e}")
        return None


def _record_fallback_metric(
    tool_name: str,
    agent_name: str,
    graph_name: Optional[str],
) -> None:
    """Record metric for fallback resolution (for production monitoring).

    This function records a counter metric when tool resolution falls back
    to using the agent node ID. This allows monitoring fallback frequency
    in production dashboards.

    Args:
        tool_name: Name of the tool that couldn't be resolved
        agent_name: Name of the agent node used as fallback
        graph_name: Name of the workflow graph
    """
    try:
        from backend.services.metrics.collector import MetricCollector
        from backend.services.metrics.models import MetricType

        collector = MetricCollector()
        collector.record(
            name="tool_resolution_fallback",
            value=1.0,
            metric_type=MetricType.COUNTER,
            labels={
                "tool_name": tool_name,
                "agent_name": agent_name,
                "graph_name": graph_name or "unknown",
            },
        )
        tool_tracker_logger.debug(
            f"[TOOL MAPPING] Recorded fallback metric for tool: {tool_name}"
        )
    except ImportError:
        # Metrics module not available, silently skip
        pass
    except Exception as e:
        tool_tracker_logger.debug(
            f"[TOOL MAPPING] Failed to record fallback metric: {e}"
        )


async def track_tool_executions(
    tool_execution_tracker: List[Dict[str, Any]],
    agent_node: EnhancedNodeData,
    parent_db_execution_id: Optional[str],
    parent_node_execution_id: Optional[str],
    parent_execution_id: str,
    execution_order: int,
    tool_node_mapping: Dict[str, Any],
    graph_name: Optional[str],
    graph_manager: Any,
    review_iteration: Optional[int] = None,
    invocation_index: Optional[int] = None,
    parent_subagent_id: Optional[str] = None,
) -> int:
    """
    Create database records and send notifications for tool executions.

    Args:
        tool_execution_tracker: List of tool execution data
        agent_node: The agent that executed the tools
        parent_db_execution_id: Parent graph's database execution ID
        parent_node_execution_id: Database execution ID for the agent node
        parent_execution_id: Parent graph's execution ID (for WebSocket)
        execution_order: Starting execution order
        tool_node_mapping: Mapping of tool names to node info
        graph_name: Name of the parent graph
        graph_manager: Graph manager for node lookup
        review_iteration: Review iteration number (1-indexed) for tool-to-iteration association
        invocation_index: Invocation index (for multi-call subagent flows)
        parent_subagent_id: Unique ID of parent subagent invocation (format: {node_id}_iter_{iteration})

    Returns:
        Updated execution order after processing all tools
    """
    tool_tracker_logger.info(
        f"[TOOL-TRACKING-DEBUG] track_tool_executions called - "
        f"tracker length: {len(tool_execution_tracker) if tool_execution_tracker else 0}, "
        f"parent_db_execution_id: {parent_db_execution_id}, "
        f"parent_node_execution_id: {parent_node_execution_id}, "
        f"parent_execution_id: {parent_execution_id}, "
        f"graph_name: {graph_name}, "
        f"execution_order: {execution_order}, "
        f"parent_subagent_id: {parent_subagent_id}"
    )

    if not tool_execution_tracker:
        tool_tracker_logger.warning(
            "[TOOL-TRACKING-DEBUG] Early return - tool_execution_tracker is empty or None"
        )
        return execution_order

    if not parent_db_execution_id:
        tool_tracker_logger.warning(
            "[TOOL-TRACKING-DEBUG] Early return - parent_db_execution_id is None or empty. "
            "Cannot create database records without parent execution ID!"
        )
        return execution_order

    if not parent_node_execution_id:
        tool_tracker_logger.warning(
            "[TOOL-TRACKING-DEBUG] parent_node_execution_id missing; tool executions will be stored without parent linkage."
        )

    tool_tracker_logger.info(
        f"[TOOL-TRACKING-DEBUG] Creating {len(tool_execution_tracker)} tool node executions for agent: {agent_node.name}"
    )

    current_order = execution_order

    for tool_exec in tool_execution_tracker:
        tool_name = tool_exec.get("tool", "")
        if not tool_name:
            continue

        try:
            # Extract tool information
            tool_info = _extract_tool_info(
                tool_exec,
                tool_name,
                tool_node_mapping,
                graph_name,
                graph_manager,
                agent_node,
                current_order,
            )

            # Create database record
            tool_node_exec_id = await _create_tool_execution_record(
                tool_info,
                parent_db_execution_id,
                current_order,
                agent_node,
                parent_node_execution_id,
                review_iteration=review_iteration,
                invocation_index=invocation_index,
            )

            # Send WebSocket notification
            if tool_node_exec_id:
                await _send_tool_notification(
                    tool_info,
                    tool_exec,
                    parent_execution_id,
                    agent_node,
                    invocation_index=invocation_index,
                )

            tool_tracker_logger.info(f"Created tool execution record for {tool_name}")

            # Increment execution order for next tool
            current_order += 1

        except Exception as e:
            tool_tracker_logger.error(
                f"Failed to create tool execution record for {tool_name}: {e}"
            )

    return current_order


def _extract_tool_info(
    tool_exec: Dict[str, Any],
    tool_name: str,
    tool_node_mapping: Dict[str, Any],
    graph_name: Optional[str],
    graph_manager: Any,
    agent_node: EnhancedNodeData,
    execution_order: int,
) -> Dict[str, Any]:
    """
    Extract tool information including node ID, name, and type.

    Args:
        tool_exec: Tool execution data
        tool_name: The synthetic tool name
        tool_node_mapping: Mapping of tool names to node info
        graph_name: Name of the parent graph
        graph_manager: Graph manager for node lookup
        agent_node: The agent node
        execution_order: Current execution order

    Returns:
        Dictionary containing tool node information
    """
    tool_tracker_logger.info(
        f"[TOOL MAPPING] Processing tool execution for: {tool_name}"
    )
    tool_tracker_logger.info(f"[TOOL MAPPING] Available mappings: {tool_node_mapping}")

    # Extract base tool name
    base_tool_name = extract_base_tool_name(tool_name)
    tool_tracker_logger.info(
        f"[TOOL MAPPING] Base tool name extracted: {base_tool_name} from {tool_name}"
    )

    # Get tool node info from mapping (returns ToolNodeInfo dataclass)
    tool_node_info = _resolve_tool_node_info(
        base_tool_name,
        tool_name,
        tool_node_mapping,
        graph_name,
        graph_manager,
        agent_node,
        execution_order,
    )

    # Extract input/output data
    input_data, output_data = _extract_tool_io_data(tool_exec, tool_name)

    # Determine correct node type
    if tool_node_info.node_type:
        correct_node_type = (
            tool_node_info.node_type.value
            if hasattr(tool_node_info.node_type, "value")
            else str(tool_node_info.node_type)
        )
        tool_tracker_logger.info(
            f"[TOOL DB] Using actual node type: '{correct_node_type}' for tool '{tool_node_info.node_name}'"
        )
    else:
        correct_node_type = get_tool_node_type(base_tool_name)
        tool_tracker_logger.info(
            f"[TOOL DB] Determined node_type '{correct_node_type}' from base tool name '{base_tool_name}'"
        )

    return {
        "node_id": tool_node_info.node_id,
        "node_name": tool_node_info.node_name,
        "node_type": correct_node_type,
        "base_tool_name": base_tool_name,
        "synthetic_tool_name": tool_name,
        "input_data": input_data,
        "output_data": output_data,
        "is_delegation": tool_node_info.is_delegation,
        "is_fallback": tool_node_info.is_fallback,
        "resolution_strategy": tool_node_info.resolution_strategy.value,
        "fallback_reason": tool_node_info.fallback_reason,
    }


def _resolve_tool_node_info(
    base_tool_name: str,
    synthetic_tool_name: str,
    tool_node_mapping: Dict[str, Any],
    graph_name: Optional[str],
    graph_manager: Any,
    agent_node: EnhancedNodeData,
    execution_order: int,
) -> ToolNodeInfo:
    """
    Resolve tool node ID, name, type, and delegation flag from mapping.

    Resolution strategies (in order):
    1. Direct mapping lookup - Check tool_node_mapping for base or synthetic name
    2. Delegation pattern parsing - Parse delegate_to_* tools to find target agent
    3. Fallback - Use agent node ID with warning logging and metrics

    Args:
        base_tool_name: Base tool name (e.g., "document_search")
        synthetic_tool_name: Full synthetic name (e.g., "document_search_abc123")
        tool_node_mapping: Mapping of tool names to node info
        graph_name: Name of the parent graph
        graph_manager: Graph manager for node lookup
        agent_node: The agent node executing the tool
        execution_order: Current execution order

    Returns:
        ToolNodeInfo dataclass with resolution details
    """
    # Strategy 1: Try direct mapping lookup (both base name and synthetic name)
    mapping_entry = tool_node_mapping.get(base_tool_name) or tool_node_mapping.get(
        synthetic_tool_name
    )

    if mapping_entry:
        if isinstance(mapping_entry, dict):
            # New format with node_id, node_name, and node_type
            node_id = mapping_entry.get("node_id", agent_node.uniq_id)
            node_type = mapping_entry.get("node_type")

            # For MCP tools, preserve the specific tool name (e.g., "notion-search")
            # rather than using the generic MCP server name
            if mapping_entry.get("is_mcp_tool"):
                node_name = synthetic_tool_name
                tool_tracker_logger.info(
                    f"[TOOL MAPPING] Found MCP tool mapping: '{synthetic_tool_name}' -> "
                    f"Server ID: {node_id}, Type: {node_type}"
                )
            else:
                node_name = mapping_entry.get("node_name", synthetic_tool_name)
                tool_tracker_logger.info(
                    f"[TOOL MAPPING] Found mapping (new format): {base_tool_name} -> "
                    f"ID: {node_id}, Name: {node_name}, Type: {node_type}"
                )

            return ToolNodeInfo(
                node_id=node_id,
                node_name=node_name,
                node_type=node_type,
                is_delegation=False,
                is_fallback=False,
                resolution_strategy=ResolutionStrategy.DIRECT_MAPPING,
            )
        else:
            # Old format - just the node ID string
            actual_node_id = mapping_entry
            tool_tracker_logger.info(
                f"[TOOL MAPPING] Found mapping (old format): {base_tool_name} -> {actual_node_id}"
            )

            # Try to fetch the node to get name and type
            node_name = synthetic_tool_name
            node_type = None

            if graph_name and graph_manager:
                try:
                    actual_node = graph_manager.get_node(graph_name, actual_node_id)
                    if actual_node:
                        node_name = actual_node.name
                        node_type = actual_node.type
                        tool_tracker_logger.info(
                            f"[TOOL MAPPING] Using actual node - ID: {actual_node_id}, "
                            f"Name: {node_name}, Type: {node_type}"
                        )
                    else:
                        tool_tracker_logger.warning(
                            f"[TOOL MAPPING] Node {actual_node_id} not found in graph"
                        )
                except Exception as e:
                    tool_tracker_logger.error(
                        f"[TOOL MAPPING] Error getting actual node: {e}"
                    )

            return ToolNodeInfo(
                node_id=actual_node_id,
                node_name=node_name,
                node_type=node_type,
                is_delegation=False,
                is_fallback=False,
                resolution_strategy=ResolutionStrategy.DIRECT_MAPPING,
            )

    # Strategy 2: Check if this is a delegation tool (delegate_to_*)
    if base_tool_name.startswith("delegate_to_"):
        # Extract target agent name: "delegate_to_math_expert" -> "math expert"
        target_name_parts = base_tool_name.replace("delegate_to_", "").split("_")
        target_name_normalized = " ".join(target_name_parts).lower()

        # Look up actual agent node from graph
        if graph_manager and graph_name:
            target_node = _find_agent_by_normalized_name(
                graph_manager, graph_name, target_name_normalized
            )
            if target_node:
                tool_tracker_logger.info(
                    f"[TOOL MAPPING] Resolved delegation tool '{base_tool_name}' to agent: "
                    f"ID={target_node.uniq_id}, Name={target_node.name}"
                )
                return ToolNodeInfo(
                    node_id=target_node.uniq_id,
                    node_name=target_node.name,
                    node_type=NodeType.AGENT,
                    is_delegation=True,
                    is_fallback=False,
                    resolution_strategy=ResolutionStrategy.DELEGATION_PARSE,
                )
            else:
                tool_tracker_logger.warning(
                    f"[TOOL MAPPING] Could not find agent for delegation tool: {base_tool_name}, "
                    f"searched for '{target_name_normalized}'"
                )
        else:
            tool_tracker_logger.warning(
                f"[TOOL MAPPING] Cannot resolve delegation tool '{base_tool_name}' - "
                f"graph_manager or graph_name not available"
            )

        # Delegation tool that couldn't be resolved - still mark as delegation but use fallback
        fallback_reason = (
            f"delegation target agent '{target_name_normalized}' not found"
            if graph_manager and graph_name
            else "graph_manager or graph_name not available"
        )

        tool_tracker_logger.warning(
            f"[TOOL MAPPING] FALLBACK RESOLUTION: Using agent node as fallback for delegation tool. "
            f"Tool: '{synthetic_tool_name}', Agent: '{agent_node.name}' ({agent_node.uniq_id}), "
            f"Reason: {fallback_reason}"
        )
        _record_fallback_metric(base_tool_name, agent_node.name, graph_name)

        return ToolNodeInfo(
            node_id=agent_node.uniq_id,
            node_name=synthetic_tool_name,
            node_type=None,
            is_delegation=True,
            is_fallback=True,
            resolution_strategy=ResolutionStrategy.FALLBACK,
            fallback_reason=fallback_reason,
        )

    # Strategy 3: Explicit fallback with warning logging and metrics
    fallback_reason = (
        f"no mapping found for '{base_tool_name}' or '{synthetic_tool_name}'"
        if graph_manager and graph_name
        else "graph_manager or graph_name not available"
    )

    tool_tracker_logger.warning(
        f"[TOOL MAPPING] FALLBACK RESOLUTION: Using agent node as fallback. "
        f"Tool: '{synthetic_tool_name}', Base: '{base_tool_name}', "
        f"Agent: '{agent_node.name}' ({agent_node.uniq_id}), "
        f"Reason: {fallback_reason}"
    )
    _record_fallback_metric(base_tool_name, agent_node.name, graph_name)

    return ToolNodeInfo(
        node_id=agent_node.uniq_id,
        node_name=synthetic_tool_name,
        node_type=None,
        is_delegation=False,
        is_fallback=True,
        resolution_strategy=ResolutionStrategy.FALLBACK,
        fallback_reason=fallback_reason,
    )


def _extract_tool_io_data(tool_exec: Dict[str, Any], tool_name: str) -> tuple:
    """
    Extract input and output data from tool execution record.

    Returns:
        Tuple of (input_data, output_data)
    """
    # Handle different tool types
    if "request" in tool_exec and isinstance(tool_exec["request"], dict):
        # HTTP request tool
        tool_input = {"request": tool_exec["request"]}
        tool_output = tool_exec.get("response", {})
        tool_tracker_logger.info(
            f"[TOOL DB] Using HTTP request metadata as input_data for {tool_name}"
        )

    elif "query" in tool_exec and (
        tool_name.startswith("search_web_") or tool_name.startswith("web_search_")
    ):
        # Web search tool
        tool_input = {
            "query": tool_exec.get("query"),
            "provider": tool_exec.get("provider", "unknown"),
        }
        tool_output = tool_exec.get("formatted_results", tool_exec.get("results", ""))
        tool_tracker_logger.info(
            f"[TOOL DB] Using web search metadata as input_data for {tool_name}"
        )

    elif "action" in tool_exec and (
        tool_name.startswith("mcp_adapter_") or tool_name.startswith("mcp_server_")
    ):
        # MCP tool
        tool_input = {
            "action": tool_exec.get("action"),
            "target": tool_exec.get("target"),
            "server": tool_exec.get("server"),
            "connection_type": tool_exec.get("connection_type"),
            "arguments": tool_exec.get("arguments"),
        }
        tool_output = tool_exec.get("formatted_output", tool_exec.get("results", ""))
        tool_tracker_logger.info(
            f"[TOOL DB] Using MCP metadata as input_data for {tool_name}"
        )

    else:
        # Regular tool
        tool_input = tool_exec.get(
            "input", tool_exec.get("kwargs", tool_exec.get("args", {}))
        )
        tool_output = tool_exec.get("output", tool_exec.get("results", ""))

    return tool_input, tool_output


async def _create_tool_execution_record(
    tool_info: Dict[str, Any],
    parent_db_execution_id: str,
    execution_order: int,
    agent_node: EnhancedNodeData,
    parent_node_execution_id: Optional[str],
    review_iteration: Optional[int] = None,
    invocation_index: Optional[int] = None,
) -> Optional[int]:
    """
    Create database execution record for a tool.

    Args:
        tool_info: Tool execution information
        parent_db_execution_id: Parent graph's database execution ID
        execution_order: Execution order in the graph
        agent_node: The agent that executed the tool
        parent_node_execution_id: Database ID of the parent agent node execution
        review_iteration: Review iteration number (1-indexed) for tool-to-iteration association
        invocation_index: Invocation index (for multi-call subagent flows)

    Returns:
        The tool node execution ID, or None if creation failed
    """
    is_delegation = tool_info.get("is_delegation", False)

    tool_tracker_logger.info(
        f"[TOOL DB] parent_agent_id (node execution): {parent_node_execution_id}, "
        f"is_delegation: {is_delegation}"
    )

    # Skip creating records for delegations - database_tracker.py already handles
    # sub-agent execution tracking. Creating another record here would duplicate.
    if is_delegation:
        tool_tracker_logger.info(
            f"[TOOL DB] Skipping record creation for delegation tool {tool_info['node_name']} - "
            "sub-agent record created by database_tracker"
        )
        return None

    try:
        node_metadata = {
            "tool_type": tool_info["node_type"],
            "parent_agent": agent_node.name,
            "parent_agent_id": agent_node.uniq_id,
            "is_sub_agent_tool": not is_delegation,  # False for delegations
            "is_delegation": is_delegation,
            "synthetic_tool_name": tool_info["synthetic_tool_name"],
        }

        # For document search tools, add embedding cost from execution storage
        if tool_info["node_type"] == "DOCUMENT_SEARCH":
            try:
                from backend.tools.document_search.execution import (
                    get_last_document_search_execution,
                )

                doc_search_meta = get_last_document_search_execution()
                if doc_search_meta:
                    node_metadata["embedding_tokens"] = doc_search_meta.embedding_tokens
                    node_metadata["embedding_cost"] = doc_search_meta.embedding_cost
                    node_metadata["embedding_model"] = doc_search_meta.embedding_model
            except Exception as e:
                tool_tracker_logger.debug(
                    f"Could not retrieve doc search embedding cost: {e}"
                )

        tool_node_exec = ExecutionHistoryService.create_node_execution(
            graph_execution_id=parent_db_execution_id,
            node_id=tool_info["node_id"],
            node_name=tool_info["node_name"],
            node_type=tool_info["node_type"],
            execution_order=execution_order,
            input_data=tool_info["input_data"] if tool_info["input_data"] else None,
            node_metadata=node_metadata,
            is_sub_agent=is_delegation,  # True for delegation tools
            parent_agent_id=parent_node_execution_id,
            review_iteration=review_iteration,
            invocation_index=invocation_index,
        )

        if not tool_node_exec:
            return None

        tool_node_exec_id = tool_node_exec["id"]

        # Start and complete the execution immediately
        ExecutionHistoryService.start_node_execution(tool_node_exec_id)

        # Promote embedding cost to total_cost so it's included in workflow cost aggregation
        tool_llm_metadata = None
        embedding_cost = node_metadata.get("embedding_cost")
        if embedding_cost:
            tool_llm_metadata = {"total_cost": embedding_cost}

        ExecutionHistoryService.complete_node_execution(
            node_execution_id=tool_node_exec_id,
            status="completed",
            output_data=tool_info["output_data"]
            if isinstance(tool_info["output_data"], (dict, list))
            else {"result": str(tool_info["output_data"])},
            llm_metadata=tool_llm_metadata,
        )

        return tool_node_exec_id

    except Exception as e:
        tool_tracker_logger.error(f"Failed to create tool execution record: {e}")
        return None


async def _send_tool_notification(
    tool_info: Dict[str, Any],
    tool_exec: Dict[str, Any],
    parent_execution_id: str,
    agent_node: EnhancedNodeData,
    invocation_index: Optional[int] = None,
) -> None:
    """Send WebSocket notification for tool execution.

    NOTE: on_node_start and on_node_complete are now sent via streaming events
    in real-time for tools invoked through LLM tool calls. This function only
    sends on_node_complete for tools that didn't emit streaming events
    (e.g., non-LLM tool invocations or when streaming is disabled).

    Args:
        tool_info: Tool execution information
        tool_exec: Tool execution data
        parent_execution_id: Parent graph's execution ID (for WebSocket)
        agent_node: The agent that executed the tool
        invocation_index: Invocation index (for multi-call subagent flows)
    """
    # Check if streaming events were already emitted for this tool
    # If was_streamed is True, skip duplicate notification
    if tool_exec.get("was_streamed", False):
        tool_tracker_logger.debug(
            f"Skipping duplicate notification for {tool_info.get('node_name', 'unknown')} - "
            f"already sent via streaming (was_streamed=True)"
        )
        return

    # Calculate duration if available
    duration = tool_exec.get("duration", 0.0)
    if not duration and tool_exec.get("timestamp"):
        try:
            # Ensure timestamp is numeric before arithmetic
            if isinstance(tool_exec["timestamp"], (int, float)):
                duration = asyncio.get_event_loop().time() - tool_exec["timestamp"]
            else:
                duration = 0.0
        except (TypeError, ValueError):
            duration = 0.0

    # Prepare output data
    output_data = tool_info["output_data"]
    if not isinstance(output_data, dict):
        output_data = {"result": str(output_data)}

    is_delegation = tool_info.get("is_delegation", False)

    await send_node_complete_notification(
        execution_id=parent_execution_id,
        node_id=tool_info["node_id"],
        node_name=tool_info["node_name"],
        output=output_data,
        node_type=tool_info["node_type"],
        duration_seconds=duration,
        input_data=tool_info["input_data"],
        is_sub_agent=is_delegation,  # True for delegation tools
        parent_agent_id=agent_node.uniq_id,
        step=invocation_index,
    )

    tool_tracker_logger.info(
        f"Sent WebSocket notification for tool {tool_info['node_name']} "
        f"(synthetic: {tool_info['synthetic_tool_name']}) "
        f"with node_id {tool_info['node_id']}, is_delegation={is_delegation}"
    )
