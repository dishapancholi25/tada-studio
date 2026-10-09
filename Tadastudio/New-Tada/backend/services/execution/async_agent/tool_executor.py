"""Tool executor for async agent execution.

This module handles tool execution and implements the ReAct pattern
(Reasoning and Acting) where the LLM can make multiple tool calls and
incorporate the results into its final response.
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langgraph.errors import GraphInterrupt

from backend.models.workflow.configs.guardrails import GuardrailsConfig
from backend.services.config import get_logger
from backend.services.guardrails.checkpoint import GuardrailCheckpoint, GuardrailContext
from backend.services.guardrails.exceptions import GuardrailViolationError
from backend.services.streaming import streaming_emitter

from .exceptions import ToolExecutionError
from .http_metadata_handler import HTTPMetadataHandler
from .models import ToolExecutionRecord
from .utils import is_http_request_tool


# Get logger for this module
tool_executor_logger = get_logger("async_agent.tool_executor")

# Thresholds for stuck-loop detection
_LOOP_INTERVENTION_THRESHOLD = 3  # Inject guidance after this many consecutive identical calls
_LOOP_FORCE_EXIT_THRESHOLD = 5  # Force-exit the loop after this many


def _hash_tool_call(name: str, args: dict) -> Tuple[str, str]:
    """Return (tool_name, args_hash) for a tool call."""
    args_hash = hashlib.md5(
        json.dumps(args, sort_keys=True, default=str).encode()
    ).hexdigest()
    return (name, args_hash)


def _detect_stuck_loop(
    call_history: List[List[Tuple[str, str]]],
    threshold: int = _LOOP_INTERVENTION_THRESHOLD,
) -> Optional[Tuple[str, int]]:
    """Check if any tool+args combo appears in the last `threshold` consecutive iterations.

    Args:
        call_history: Per-iteration list of (tool_name, args_hash) tuples.
        threshold: Minimum consecutive occurrences to flag as stuck.

    Returns:
        (tool_name, consecutive_count) if stuck, else None.
    """
    if len(call_history) < threshold:
        return None

    recent_calls = set(call_history[-1])
    for name, args_hash in recent_calls:
        consecutive = 0
        for past_calls in reversed(call_history):
            if (name, args_hash) in past_calls:
                consecutive += 1
            else:
                break
        if consecutive >= threshold:
            return (name, consecutive)

    return None


class AsyncToolExecutor:
    """Executes tools and implements ReAct pattern.

    This class handles tool execution for agents, including:
    - Tool binding to LLM
    - Tool call detection and execution
    - ReAct pattern (multi-turn tool use)
    - Execution tracking and error handling
    """

    def __init__(self, http_metadata_handler: Optional[HTTPMetadataHandler] = None):
        """Initialize the tool executor.

        Args:
            http_metadata_handler: Optional HTTP metadata handler
        """
        self.logger = tool_executor_logger
        self.http_handler = http_metadata_handler or HTTPMetadataHandler()

    async def execute_with_tools(
        self,
        llm: BaseChatModel,
        messages: List[BaseMessage],
        tools: List[Any],
        tracker: Optional[List[Dict[str, Any]]] = None,
        agent_name: str = "unknown",
        max_iterations: int = 50,
        ws_notifier: Optional[Any] = None,
        execution_id: Optional[str] = None,
        node_id: Optional[str] = None,
        graph_name: Optional[str] = None,
        tool_node_mapping: Optional[Dict[str, Dict[str, str]]] = None,
        review_iteration: Optional[int] = None,
        node_execution_id: Optional[str] = None,
        invocation_index: Optional[int] = None,
        parent_subagent_id: Optional[str] = None,
        guardrails_config: Optional[List[GuardrailsConfig]] = None,
        guardrails_state: Optional[Dict[str, Any]] = None,
        emit_content_chunks: bool = True,
        db_execution_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        guardrail_checkpoint: Optional[GuardrailCheckpoint] = None,
        guardrail_ctx: Optional[GuardrailContext] = None,
        tool_guardrails_map: Optional[Dict[str, List[GuardrailsConfig]]] = None,
    ) -> AIMessage:
        """Execute LLM with tools and handle tool calls (ReAct pattern).

        This method implements a loop that continues until the LLM returns
        a text response (no more tool calls) or max_iterations is reached:
        1. Binds tools to the LLM
        2. Invokes the LLM
        3. If tools are called, executes them and calls LLM again with results
        4. Repeats steps 2-3 until LLM returns final response
        5. Returns the final response (with optional streaming)

        Args:
            llm: The LLM instance
            messages: Input messages
            tools: Available tools
            tracker: Optional list to track tool executions (modified in place)
            agent_name: Name of the agent (for logging)
            max_iterations: Maximum iterations to prevent infinite loops (default: 10)
            ws_notifier: Optional WebSocket notifier for streaming tokens
            execution_id: Execution ID for WebSocket events
            node_id: Node ID for WebSocket events
            graph_name: Graph name for WebSocket events
            tool_node_mapping: Optional mapping from synthetic tool names to node info
            review_iteration: Current review iteration number (1-indexed)
            node_execution_id: Database UUID of the agent's NodeExecution record

        Returns:
            Final AI message response

        Raises:
            ToolExecutionError: If tool execution fails critically or max iterations exceeded
        """
        # Determine if streaming is enabled
        streaming_enabled = (
            ws_notifier is not None and execution_id is not None and node_id is not None
        )
        try:
            # Augment tool_node_mapping with MCP tool metadata from actual tool instances.
            # OAuth MCP tools are loaded lazily (after graph build), so the mapping built
            # earlier only has the synthetic server-level name (e.g., "mcp_server_notion_mcp_server").
            # Here we add entries for each individual MCP tool (e.g., "notion-search") so that
            # streaming events include the correct tool_node_id for canvas indicators.
            if tools:
                if tool_node_mapping is None:
                    tool_node_mapping = {}
                for tool in tools:
                    t_name = getattr(tool, "name", None)
                    mcp_node_id = getattr(tool, "_mcp_server_node_id", None)
                    if t_name and mcp_node_id and t_name not in tool_node_mapping:
                        tool_node_mapping[t_name] = {
                            "node_id": mcp_node_id,
                            "node_name": getattr(tool, "_mcp_server_node_name", t_name),
                            "node_type": getattr(
                                tool, "_mcp_server_node_type", "MCP_SERVER"
                            ),
                            "is_mcp_tool": True,
                        }

            # Bind tools to LLM
            llm_with_tools = llm.bind_tools(tools)

            # Track cumulative token usage across all ReAct iterations
            cumulative_usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }

            # ReAct loop: continue until LLM returns text response (no more tool calls)
            response = None  # Tracks last LLM response for max-iterations fallback
            call_history: List[List[Tuple[str, str]]] = []  # Per-iteration tool call fingerprints
            loop_intervention_msg: Optional[SystemMessage] = None  # Track injected intervention
            for iteration in range(max_iterations):
                self.logger.info(
                    f"[TOOL-EXECUTOR] Iteration {iteration + 1}/{max_iterations} - "
                    f"Invoking LLM with {len(tools)} tools for {agent_name}"
                )

                # Use streaming to get response with retry for transient timeouts
                response = await self._invoke_llm_with_retry(
                    llm_with_tools,
                    messages,
                    streaming_enabled,
                    ws_notifier,
                    execution_id,
                    node_id,
                    graph_name,
                    agent_name,
                    emit_content_chunks=emit_content_chunks,
                )

                # Accumulate token usage from this iteration
                iter_usage = getattr(response, "usage_metadata", None)
                if iter_usage:
                    cumulative_usage["input_tokens"] += iter_usage.get(
                        "input_tokens", 0
                    )
                    cumulative_usage["output_tokens"] += iter_usage.get(
                        "output_tokens", 0
                    )
                    cumulative_usage["total_tokens"] += iter_usage.get(
                        "total_tokens", 0
                    )

                # Check if tools were called
                if not hasattr(response, "tool_calls") or not response.tool_calls:
                    # LLM returned final response without tool calls
                    if iteration == 0:
                        self.logger.warning(
                            f"[TOOL-EXECUTOR] {agent_name} did not invoke any tools "
                            f"despite having {len(tools)} available"
                        )
                    else:
                        self.logger.info(
                            f"[TOOL-EXECUTOR] {agent_name} completed after {iteration + 1} "
                            f"iteration(s) with final response"
                        )

                    # Log response details
                    content_preview = (
                        response.content[:200]
                        if hasattr(response, "content")
                        else str(response)[:200]
                    )
                    self.logger.info(
                        f"[TOOL-EXECUTOR] Final response from {agent_name}: {content_preview}"
                    )

                    # Attach cumulative token usage across all ReAct iterations
                    if iteration > 0 and any(cumulative_usage.values()):
                        return AIMessage(
                            content=response.content,
                            tool_calls=getattr(response, "tool_calls", None) or [],
                            response_metadata=getattr(
                                response, "response_metadata", None
                            )
                            or {},
                            usage_metadata=cumulative_usage,
                        )
                    return response

                # Tools were called - process them
                num_calls = len(response.tool_calls)
                self.logger.info(
                    f"[TOOL-EXECUTOR] Iteration {iteration + 1}: {agent_name} invoked "
                    f"{num_calls} tool(s)"
                )

                # Log each tool call
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})
                    self.logger.info(
                        f"[TOOL-EXECUTOR] Tool call: {tool_name} with args: {tool_args}"
                    )

                # Execute the tool calls
                tool_messages = await self.process_tool_calls(
                    response.tool_calls,
                    tools,
                    tracker,
                    agent_name,
                    node_id or "",
                    tool_node_mapping=tool_node_mapping,
                    execution_id=execution_id,
                    review_iteration=review_iteration,
                    node_execution_id=node_execution_id,
                    invocation_index=invocation_index,
                    parent_subagent_id=parent_subagent_id,
                    guardrails_config=guardrails_config,
                    guardrails_state=guardrails_state,
                    db_execution_id=db_execution_id,
                    workflow_id=workflow_id,
                    guardrail_checkpoint=guardrail_checkpoint,
                    guardrail_ctx=guardrail_ctx,
                    tool_guardrails_map=tool_guardrails_map,
                )

                # Add AI message with tool calls to conversation
                messages.append(response)

                # Add tool results
                messages.extend(tool_messages)

                # Track tool call fingerprints for stuck-loop detection
                iteration_calls = [
                    _hash_tool_call(tc.get("name", ""), tc.get("args", {}))
                    for tc in response.tool_calls
                ]
                call_history.append(iteration_calls)

                stuck = _detect_stuck_loop(call_history, _LOOP_INTERVENTION_THRESHOLD)
                if stuck:
                    tool_name, consecutive_count = stuck
                    if consecutive_count >= _LOOP_FORCE_EXIT_THRESHOLD:
                        self.logger.warning(
                            f"[TOOL-EXECUTOR] Forced exit: '{tool_name}' called identically "
                            f"{consecutive_count} consecutive times for {agent_name}"
                        )
                        break
                    # Remove prior intervention message to avoid accumulation
                    if loop_intervention_msg and loop_intervention_msg in messages:
                        messages.remove(loop_intervention_msg)
                    loop_intervention_msg = SystemMessage(
                        content=(
                            f"You have called '{tool_name}' with identical arguments "
                            f"{consecutive_count} times consecutively. This appears to be a loop. "
                            f"Try different arguments, use a different tool, or provide your final answer."
                        )
                    )
                    messages.append(loop_intervention_msg)
                    self.logger.info(
                        f"[TOOL-EXECUTOR] Stuck-loop detected: '{tool_name}' x{consecutive_count} "
                        f"for {agent_name}, injected guidance"
                    )

                self.logger.info(
                    f"[TOOL-EXECUTOR] Added {len(tool_messages)} tool results to conversation, "
                    f"continuing to iteration {iteration + 2}"
                )

            # Max iterations reached without final response
            error_msg = (
                f"Max iterations ({max_iterations}) reached for {agent_name} "
                f"without receiving final text response. LLM may be stuck in tool calling loop."
            )
            self.logger.error(f"[TOOL-EXECUTOR] {error_msg}")

            # Return the last response we have, but log the issue
            if response is not None and hasattr(response, "content"):
                # Attach cumulative token usage across all ReAct iterations
                if any(cumulative_usage.values()):
                    return AIMessage(
                        content=response.content,
                        tool_calls=getattr(response, "tool_calls", None) or [],
                        response_metadata=getattr(response, "response_metadata", None)
                        or {},
                        usage_metadata=cumulative_usage,
                    )
                return response
            raise ToolExecutionError(error_msg, agent_name=agent_name)

        except asyncio.CancelledError:
            # Re-raise CancelledError for hard stop support
            self.logger.info(
                f"[TOOL-EXECUTOR] Tool execution cancelled for {agent_name} (hard stop)"
            )
            raise
        except GraphInterrupt:
            # Re-raise GraphInterrupt to propagate pause to parent workflow
            self.logger.info(
                f"[TOOL-EXECUTOR] GraphInterrupt in execute_with_tools for {agent_name}, "
                "propagating to parent workflow"
            )
            raise
        except Exception as e:
            error_msg = f"Tool execution failed for {agent_name}: {str(e)}"
            self.logger.error(f"[TOOL-EXECUTOR] {error_msg}", exc_info=True)
            raise ToolExecutionError(error_msg, agent_name=agent_name) from e

    async def process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        tools: List[Any],
        tracker: Optional[List[Dict[str, Any]]] = None,
        agent_name: str = "unknown",
        agent_id: str = "",
        tool_node_mapping: Optional[Dict[str, Dict[str, str]]] = None,
        execution_id: Optional[str] = None,
        review_iteration: Optional[int] = None,
        node_execution_id: Optional[str] = None,
        invocation_index: Optional[int] = None,
        parent_subagent_id: Optional[str] = None,
        guardrails_config: Optional[List[GuardrailsConfig]] = None,
        guardrails_state: Optional[Dict[str, Any]] = None,
        db_execution_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        guardrail_checkpoint: Optional[GuardrailCheckpoint] = None,
        guardrail_ctx: Optional[GuardrailContext] = None,
        tool_guardrails_map: Optional[Dict[str, List[GuardrailsConfig]]] = None,
    ) -> List[ToolMessage]:
        """Process and execute tool calls in parallel.

        Args:
            tool_calls: List of tool calls from LLM
            tools: Available tools
            tracker: Optional tracker for executions (modified in place)
            agent_name: Agent name for logging
            agent_id: Agent node ID for streaming events
            tool_node_mapping: Optional mapping from synthetic tool names to node info
            execution_id: Optional execution ID for stream writer registry fallback
            review_iteration: Current review iteration number (1-indexed)
            node_execution_id: Database UUID of the agent's NodeExecution record
            db_execution_id: Database UUID of the GraphExecution record (FK for violations)

        Returns:
            List of ToolMessage objects with execution results
        """
        # Execute all tool calls in parallel using asyncio.gather
        self.logger.info(
            f"[TOOL-EXECUTOR] Executing {len(tool_calls)} tool calls in parallel for {agent_name}"
        )
        results = await asyncio.gather(
            *[
                self._execute_single_tool(
                    tc,
                    tools,
                    agent_name,
                    agent_id,
                    tool_node_mapping,
                    execution_id,
                    review_iteration=review_iteration,
                    node_execution_id=node_execution_id,
                    invocation_index=invocation_index,
                    parent_subagent_id=parent_subagent_id,
                    guardrails_config=guardrails_config,
                    guardrails_state=guardrails_state,
                    db_execution_id=db_execution_id,
                    workflow_id=workflow_id,
                    guardrail_checkpoint=guardrail_checkpoint,
                    guardrail_ctx=guardrail_ctx,
                    tool_guardrails_map=tool_guardrails_map,
                )
                for tc in tool_calls
            ],
            return_exceptions=True,
        )

        # Check for GraphInterrupt first - if any tool raised it, propagate after all complete
        for result_or_exc in results:
            if isinstance(result_or_exc, GraphInterrupt):
                self.logger.info(
                    "[TOOL-EXECUTOR] GraphInterrupt from parallel tool execution, propagating"
                )
                raise result_or_exc

        # Process results in order (asyncio.gather preserves order)
        tool_messages = []
        for tool_call, result_or_exc in zip(tool_calls, results):
            tool_id = tool_call.get("id", "")
            tool_name = tool_call.get("name", "unknown")

            if isinstance(result_or_exc, BaseException):
                # Handle exception case - create error record
                error_msg = f"Error executing tool: {str(result_or_exc)}"
                self.logger.error(
                    f"[TOOL-EXECUTOR] Tool {tool_name} failed in parallel execution: {result_or_exc}"
                )
                timestamp = asyncio.get_event_loop().time()
                execution_record = ToolExecutionRecord(
                    tool_name=tool_name,
                    tool_id=tool_id,
                    input_args=tool_call.get("args", {}),
                    timestamp=timestamp,
                    error=str(result_or_exc),
                    output=error_msg,
                )
                result = error_msg
            else:
                result, execution_record = result_or_exc

            # Create ToolMessage
            tool_message = ToolMessage(
                content=str(result),
                tool_call_id=tool_id,
            )
            tool_messages.append(tool_message)

            # Add to tracker if provided
            if tracker is not None:
                record_dict = execution_record.to_dict()
                tracker.append(record_dict)
                self.logger.debug(
                    f"[TOOL-EXECUTOR] Added execution record to tracker "
                    f"(total: {len(tracker)})"
                )

        self.logger.info(
            f"[TOOL-EXECUTOR] Completed {len(tool_calls)} parallel tool calls for {agent_name}"
        )
        return tool_messages

    async def _execute_single_tool(
        self,
        tool_call: Dict[str, Any],
        tools: List[Any],
        agent_name: str,
        agent_id: str = "",
        tool_node_mapping: Optional[Dict[str, Dict[str, str]]] = None,
        execution_id: Optional[str] = None,
        review_iteration: Optional[int] = None,
        node_execution_id: Optional[str] = None,
        invocation_index: Optional[int] = None,
        parent_subagent_id: Optional[str] = None,
        guardrails_config: Optional[List[GuardrailsConfig]] = None,
        guardrails_state: Optional[Dict[str, Any]] = None,
        db_execution_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        guardrail_checkpoint: Optional[GuardrailCheckpoint] = None,
        guardrail_ctx: Optional[GuardrailContext] = None,
        tool_guardrails_map: Optional[Dict[str, List[GuardrailsConfig]]] = None,
    ) -> Tuple[str, ToolExecutionRecord]:
        """Execute a single tool call with streaming events.

        Args:
            tool_call: Tool call dictionary from LLM
            tools: Available tools
            agent_name: Agent name for logging
            agent_id: Agent node ID for streaming events
            tool_node_mapping: Optional mapping from synthetic tool names to node info
            execution_id: Optional execution ID for stream writer registry fallback
            review_iteration: Current review iteration number (1-indexed)
            node_execution_id: Database UUID of the agent's NodeExecution record
            guardrails_config: Optional agent-level guardrails configuration (fallback)
            tool_guardrails_map: Optional per-tool guardrails configs (tool_node_id → config)
            db_execution_id: Database UUID of the GraphExecution record (FK for violations)
            workflow_id: Workflow ID for guardrail violation attribution

        Returns:
            Tuple of (result_string, ToolExecutionRecord)
        """
        tool_name = tool_call.get("name", "unknown")
        tool_args = tool_call.get("args", {})
        tool_id = tool_call.get("id", "")

        # Look up node info from mapping for real-time timeline updates
        node_info = (tool_node_mapping or {}).get(tool_name, {})
        tool_node_id = node_info.get("node_id")
        tool_node_name = node_info.get("node_name", tool_name)
        tool_node_type = node_info.get("node_type")

        # Select per-tool guardrails config if available, otherwise fall back to agent pipeline
        effective_guardrails = (
            tool_guardrails_map.get(tool_node_id)
            if tool_guardrails_map and tool_node_id
            else None
        ) or guardrails_config  # unmapped tools inherit agent pipeline

        # Build per-tool guardrail context (adds tool_name to the shared ctx)
        tool_ctx = GuardrailContext(
            execution_id=guardrail_ctx.execution_id if guardrail_ctx else execution_id,
            db_execution_id=guardrail_ctx.db_execution_id if guardrail_ctx else db_execution_id,
            node_execution_id=guardrail_ctx.node_execution_id if guardrail_ctx else node_execution_id,
            workflow_id=guardrail_ctx.workflow_id if guardrail_ctx else workflow_id,
            agent_node_id=guardrail_ctx.agent_node_id if guardrail_ctx else agent_id,
            agent_node_name=guardrail_ctx.agent_node_name if guardrail_ctx else agent_name,
            user_id=guardrail_ctx.user_id if guardrail_ctx else None,
            tool_name=tool_name,
        )

        # Guardrails: validate tool call + ingress via unified checkpoint
        if guardrail_checkpoint and effective_guardrails:
            # 1. Tool call policy validation (SSRF, SQL, file restrictions)
            try:
                await guardrail_checkpoint.check(
                    "", effective_guardrails, "tool_call", tool_ctx,
                    tool_name=tool_name, tool_args=tool_args,
                    tool_node_type=tool_node_type,
                )
            except GuardrailViolationError as gve:
                blocked_msg = f"Tool call blocked by guardrail: {gve.violations[0].message if gve.violations else 'Policy violation'}"
                self.logger.warning(f"[TOOL-EXECUTOR] {blocked_msg}")
                timestamp = asyncio.get_event_loop().time()
                execution_record = ToolExecutionRecord(
                    tool_name=tool_name, tool_id=tool_id,
                    input_args=tool_args, timestamp=timestamp,
                    error=blocked_msg, output=blocked_msg,
                )
                return blocked_msg, execution_record

            # 2. Tool ingress — filter input data sent to the tool
            args_text = json.dumps(tool_args) if tool_args else ""
            if args_text:
                _tool_gs = guardrails_state if guardrails_state is not None else {}
                try:
                    ingress_result = await guardrail_checkpoint.check(
                        args_text, effective_guardrails, "tool_ingress", tool_ctx,
                        state=_tool_gs,
                    )
                except GuardrailViolationError as gve:
                    blocked_msg = f"Tool input blocked by guardrail: {gve.violations[0].message if gve.violations else 'Policy violation'}"
                    self.logger.warning(f"[TOOL-EXECUTOR] {blocked_msg}")
                    timestamp = asyncio.get_event_loop().time()
                    execution_record = ToolExecutionRecord(
                        tool_name=tool_name, tool_id=tool_id,
                        input_args=tool_args, timestamp=timestamp,
                        error=blocked_msg, output=blocked_msg,
                    )
                    return blocked_msg, execution_record

                if not ingress_result.passed:
                    violation_msg = ingress_result.violations[0].message if ingress_result.violations else "Tool input blocked"
                    blocked_msg = f"Tool input blocked by guardrail: {violation_msg}"
                    self.logger.warning(f"[TOOL-EXECUTOR] {blocked_msg}")
                    timestamp = asyncio.get_event_loop().time()
                    execution_record = ToolExecutionRecord(
                        tool_name=tool_name, tool_id=tool_id,
                        input_args=tool_args, timestamp=timestamp,
                        error=blocked_msg, output=blocked_msg,
                    )
                    return blocked_msg, execution_record

                # Apply sanitized content (e.g. PII-anonymized args) for tool execution
                if ingress_result.sanitized_content is not None:
                    try:
                        tool_args = json.loads(ingress_result.sanitized_content)
                    except (json.JSONDecodeError, TypeError):
                        self.logger.debug(
                            f"[TOOL-EXECUTOR] Could not parse sanitized args as JSON for {tool_name}, "
                            "using original args"
                        )

        # Track execution time
        start_time = time.time()

        # Emit tool call start event (with node info for timeline updates)
        streaming_emitter.emit_tool_start(
            call_id=tool_id,
            tool_name=tool_name,
            tool_args=tool_args,
            agent_id=agent_id,
            agent_name=agent_name,
            tool_node_id=tool_node_id,
            tool_node_name=tool_node_name,
            tool_node_type=tool_node_type,
            execution_id=execution_id,
            review_iteration=review_iteration,
            node_execution_id=node_execution_id,
            invocation_index=invocation_index,
            parent_subagent_id=parent_subagent_id,
        )
        tool_executor_logger.info(
            f"[TOOL-SUBAGENT-LINK] _execute_single_tool: "
            f"tool={tool_name}, parent_subagent_id={parent_subagent_id}, "
            f"invocation_index={invocation_index}"
        )

        # Create execution record
        timestamp = asyncio.get_event_loop().time()
        execution_record = ToolExecutionRecord(
            tool_name=tool_name,
            tool_id=tool_id,
            input_args=tool_args,
            timestamp=timestamp,
        )

        # Find and execute the tool
        for tool in tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                result, metadata = await self._execute_tool_with_error_handling(
                    tool, tool_args, tool_name, execution_record, tool_id
                )

                # Guardrails: tool egress — filter output data received from the tool
                # (e.g. PII deanonymization, content filtering of tool results)
                if (
                    guardrail_checkpoint
                    and effective_guardrails
                    and result
                    and not execution_record.error
                ):
                    _tool_gs = guardrails_state if guardrails_state is not None else {}
                    try:
                        egress_result = await guardrail_checkpoint.check(
                            str(result), effective_guardrails, "tool_egress", tool_ctx,
                            state=_tool_gs,
                        )
                        if egress_result.sanitized_content is not None:
                            self.logger.info(
                                f"[TOOL-EXECUTOR] Tool output sanitized by guardrails for {tool_name}"
                            )
                            result = egress_result.sanitized_content
                            execution_record.output = result
                    except GuardrailViolationError as gve:
                        violation_msg = gve.violations[0].message if gve.violations else str(gve)
                        self.logger.warning(
                            f"[TOOL-EXECUTOR] Tool output blocked by guardrails for "
                            f"{tool_name}: {violation_msg}"
                        )
                        blocked_msg = f"Tool output blocked by guardrail: {violation_msg}"
                        result = blocked_msg
                        execution_record.output = blocked_msg
                        execution_record.error = blocked_msg

                # Guardrails: tool result injection — scan tool output for prompt injection
                # before it becomes a ToolMessage fed back to the LLM.
                if (
                    guardrail_checkpoint
                    and effective_guardrails
                    and result
                    and not execution_record.error
                ):
                    _pi_state = guardrails_state if guardrails_state is not None else {}
                    try:
                        await guardrail_checkpoint.check(
                            str(result), effective_guardrails, "tool_injection", tool_ctx,
                            state=_pi_state,
                        )
                    except GuardrailViolationError as gve:
                        pi_msg = gve.violations[0].message if gve.violations else str(gve)
                        blocked_msg = f"Tool result blocked (prompt injection detected): {pi_msg}"
                        result = blocked_msg
                        execution_record.output = blocked_msg
                        execution_record.error = blocked_msg
                    except Exception as _pi_err:
                        self.logger.debug(
                            f"[TOOL-EXECUTOR] Tool result injection scan failed for {tool_name}: {_pi_err}"
                        )

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Handle HTTP metadata if applicable
                if metadata and is_http_request_tool(tool_name):
                    self._apply_http_metadata(execution_record, metadata, tool_id)

                # Emit completion or error event based on result (with node info)
                if execution_record.error:
                    streaming_emitter.emit_tool_error(
                        call_id=tool_id,
                        tool_name=tool_name,
                        error=str(execution_record.error),
                        duration_ms=duration_ms,
                        tool_node_id=tool_node_id,
                        tool_node_name=tool_node_name,
                        tool_node_type=tool_node_type,
                        execution_id=execution_id,
                        review_iteration=review_iteration,
                        node_execution_id=node_execution_id,
                        invocation_index=invocation_index,
                        agent_id=agent_id,
                        agent_name=agent_name,
                        parent_subagent_id=parent_subagent_id,
                    )
                    execution_record.was_streamed = True
                else:
                    streaming_emitter.emit_tool_complete(
                        call_id=tool_id,
                        tool_name=tool_name,
                        result_preview=str(result) if result else None,
                        duration_ms=duration_ms,
                        tool_node_id=tool_node_id,
                        tool_node_name=tool_node_name,
                        tool_node_type=tool_node_type,
                        execution_id=execution_id,
                        review_iteration=review_iteration,
                        node_execution_id=node_execution_id,
                        invocation_index=invocation_index,
                        agent_id=agent_id,
                        agent_name=agent_name,
                        parent_subagent_id=parent_subagent_id,
                        full_result=str(result) if result else None,
                        tool_input=tool_args,
                    )
                    execution_record.was_streamed = True

                return result, execution_record

        # Tool not found — if a matching tool was found, we already returned above
        duration_ms = (time.time() - start_time) * 1000
        error_msg = f"Tool {tool_name} not found"
        self.logger.error(f"[TOOL-EXECUTOR] {error_msg} for {agent_name}")
        execution_record.error = "Tool not found"
        execution_record.output = error_msg

        # Emit error event (with node info for timeline)
        streaming_emitter.emit_tool_error(
            call_id=tool_id,
            tool_name=tool_name,
            error=error_msg,
            duration_ms=duration_ms,
            tool_node_id=tool_node_id,
            tool_node_name=tool_node_name,
            tool_node_type=tool_node_type,
            execution_id=execution_id,
            review_iteration=review_iteration,
            node_execution_id=node_execution_id,
            invocation_index=invocation_index,
            agent_id=agent_id,
            agent_name=agent_name,
            parent_subagent_id=parent_subagent_id,
        )
        execution_record.was_streamed = True

        return error_msg, execution_record

    async def _execute_tool_with_error_handling(
        self,
        tool: Any,
        tool_args: Dict[str, Any],
        tool_name: str,
        execution_record: ToolExecutionRecord,
        _tool_call_id: str = "",
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Execute tool with error handling.

        Args:
            tool: Tool to execute
            tool_args: Tool arguments
            tool_name: Tool name
            execution_record: Record to populate
            tool_call_id: Tool call ID for streaming progress events

        Returns:
            Tuple of (result_string, metadata_dict or None)
        """
        try:
            # Execute with HTTP metadata capture
            # Note: Tools that want to emit progress events can use streaming_emitter
            # directly with their tool name
            result, metadata = await self.http_handler.execute_with_metadata(
                tool, tool_args, tool_name
            )

            # Record success
            execution_record.output = result
            self.logger.info(
                f"[TOOL-EXECUTOR] Tool {tool_name} executed successfully: "
                f"{str(result)[:200]}"
            )

            return result, metadata

        except asyncio.CancelledError:
            # Re-raise CancelledError for hard stop support
            self.logger.info(
                f"[TOOL-EXECUTOR] Tool {tool_name} execution cancelled (hard stop)"
            )
            raise
        except GraphInterrupt:
            # Re-raise GraphInterrupt to propagate pause to parent workflow
            # This allows sub-agent review interrupts to pause the entire workflow
            self.logger.info(
                f"[TOOL-EXECUTOR] GraphInterrupt received from {tool_name}, "
                "propagating to parent workflow"
            )
            raise
        except Exception as e:
            # Record error
            error_msg = f"Error executing tool: {str(e)}"
            execution_record.error = str(e)
            execution_record.output = error_msg

            self.logger.error(
                f"[TOOL-EXECUTOR] Tool {tool_name} failed: {str(e)}",
                exc_info=True,
            )

            return error_msg, None

    def _apply_http_metadata(
        self,
        execution_record: ToolExecutionRecord,
        metadata: Dict[str, Any],
        _tool_call_id: str,
    ) -> None:
        """Apply HTTP metadata to execution record.

        Args:
            execution_record: Record to update (modified in place)
            metadata: HTTP metadata dictionary
            _tool_call_id: Tool call ID from LLM (reserved for future use)
        """
        self.logger.info("[TOOL-EXECUTOR] Applying HTTP metadata to execution record")

        # Update record with HTTP-specific fields
        execution_record.request = metadata.get("request", {})
        execution_record.response = metadata.get("response", {})
        execution_record.config = metadata.get("config", {})
        execution_record.timestamp = metadata.get(
            "timestamp", execution_record.timestamp
        )
        execution_record.duration = metadata.get("response", {}).get("elapsed", 0)

        self.logger.debug("[TOOL-EXECUTOR] HTTP metadata applied to execution record")

    async def _astream_with_watchdog(
        self,
        async_iterable,
        timeout_seconds: float = 90.0,
        agent_name: str = "unknown",
    ):
        """Wrap an async stream with a per-chunk watchdog timeout.

        Yields chunks from the stream, raising asyncio.TimeoutError if
        no chunk arrives within timeout_seconds. This catches stalled
        Azure OpenAI streams where the TCP connection stays alive but
        SSE events stop arriving.

        The timeout resets on each chunk, so long responses with steady
        chunk delivery are not affected.
        """
        aiter = async_iterable.__aiter__()
        while True:
            try:
                chunk = await asyncio.wait_for(
                    aiter.__anext__(), timeout=timeout_seconds
                )
                yield chunk
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                self.logger.warning(
                    f"[TOOL-EXECUTOR] Stream watchdog timeout ({timeout_seconds}s) "
                    f"for {agent_name} - no chunk received, stream appears stalled"
                )
                raise

    async def _invoke_with_streaming(
        self,
        llm_with_tools: Any,
        messages: List[BaseMessage],
        streaming_enabled: bool,
        _ws_notifier: Optional[Any],
        execution_id: Optional[str],
        node_id: Optional[str],
        _graph_name: Optional[str],
        agent_name: str,
        emit_content_chunks: bool = True,
    ) -> AIMessage:
        """Invoke LLM with streaming support for responses.

        Uses astream() to get the response and emits text tokens to WebSocket
        in real-time. Tool-calling chunks are not emitted to avoid showing
        intermediate JSON.

        Args:
            llm_with_tools: LLM with tools bound
            messages: Input messages
            streaming_enabled: Whether streaming is enabled
            _ws_notifier: WebSocket notifier (reserved for future use)
            execution_id: Execution ID
            node_id: Node ID
            _graph_name: Graph name (reserved for future use)
            agent_name: Agent name for logging

        Returns:
            AI message response
        """
        # If streaming not enabled or LLM doesn't support astream, use ainvoke
        if not streaming_enabled or not hasattr(llm_with_tools, "astream"):
            return await llm_with_tools.ainvoke(messages)

        try:
            # Stream the response to collect chunks
            # NOTE: For subagents running in isolated contexts (via asyncio.run),
            # LangGraph's stream mode doesn't capture their output. We explicitly
            # emit content chunks to the StreamWriterRegistry for WebSocket delivery.
            collected_chunks: List[str] = []
            final_response: Optional[AIMessage] = None
            has_tool_calls = False
            first_token_time: Optional[float] = None
            stream_start_time = time.perf_counter()

            async for chunk in self._astream_with_watchdog(
                llm_with_tools.astream(messages),
                timeout_seconds=90.0,
                agent_name=agent_name,
            ):
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                # Check if this chunk contains tool calls
                # During streaming, tool calls come in via tool_call_chunks attribute
                if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                    has_tool_calls = True
                if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                    has_tool_calls = True

                # Extract text content from chunk
                content = None
                if hasattr(chunk, "content"):
                    content = chunk.content
                    if isinstance(content, list):
                        content = "".join(
                            part if isinstance(part, str) else str(part)
                            for part in content
                        )

                if content:
                    collected_chunks.append(content)
                    # Emit content chunk for subagents in isolated contexts.
                    # Skip when LangGraph's "messages" stream mode is already
                    # capturing these tokens (emit_content_chunks=False).
                    if emit_content_chunks and execution_id:
                        streaming_emitter.emit_content_chunk(
                            content=content,
                            agent_name=agent_name,
                            node_id=node_id,
                            execution_id=execution_id,
                        )

                # Accumulate chunks for final response
                if final_response is None:
                    final_response = chunk
                else:
                    # LangChain AIMessageChunk supports addition to accumulate
                    try:
                        final_response = final_response + chunk
                    except Exception:
                        # Fallback: just keep the latest chunk
                        final_response = chunk

            self.logger.info(
                f"[TOOL-EXECUTOR] Streaming completed for {agent_name}: "
                f"collected_chunks={len(collected_chunks)}, has_tool_calls={has_tool_calls}"
            )

            # Build the final response from accumulated chunks
            if final_response is not None:
                # Extract content from accumulated response
                response_content = getattr(final_response, "content", "")
                if isinstance(response_content, list):
                    response_content = "".join(
                        part if isinstance(part, str) else str(part)
                        for part in response_content
                    )

                # Extract tool_calls from accumulated response
                tool_calls = getattr(final_response, "tool_calls", None) or []

                self.logger.debug(
                    f"[TOOL-EXECUTOR] Accumulated response - content length: {len(response_content)}, "
                    f"tool_calls: {len(tool_calls)}"
                )

                # Return the accumulated response as an AIMessage, preserving metadata
                response_metadata = dict(
                    getattr(final_response, "response_metadata", None) or {}
                )
                usage_metadata = getattr(final_response, "usage_metadata", None)
                # Attach TTFT (in milliseconds) to response metadata
                if first_token_time is not None:
                    response_metadata["time_to_first_token"] = (
                        first_token_time - stream_start_time
                    ) * 1000
                return AIMessage(
                    content=response_content,
                    tool_calls=tool_calls,
                    response_metadata=response_metadata,
                    usage_metadata=usage_metadata,
                )
            else:
                # No chunks received - use collected chunks as fallback
                full_content = "".join(collected_chunks)
                self.logger.warning(
                    f"[TOOL-EXECUTOR] No final_response, using collected chunks: {len(full_content)} chars"
                )
                return AIMessage(content=full_content)

        except Exception as stream_err:
            self.logger.warning(
                f"[TOOL-EXECUTOR] Streaming failed for {agent_name}, "
                f"falling back to ainvoke: {stream_err}"
            )
            return await llm_with_tools.ainvoke(messages)

    async def _invoke_llm_with_retry(
        self,
        llm_with_tools: Any,
        messages: List[BaseMessage],
        streaming_enabled: bool,
        ws_notifier: Optional[Any],
        execution_id: Optional[str],
        node_id: Optional[str],
        graph_name: Optional[str],
        agent_name: str,
        max_retries: int = 2,
        emit_content_chunks: bool = True,
    ) -> AIMessage:
        """Invoke LLM with retry logic for transient timeout errors.

        Wraps _invoke_with_streaming with exponential backoff retry on
        httpx timeout errors. These are transient and often resolve on retry
        when the Azure OpenAI service is under load.

        Args:
            llm_with_tools: LLM with tools bound
            messages: Input messages
            streaming_enabled: Whether streaming is enabled
            ws_notifier: WebSocket notifier
            execution_id: Execution ID
            node_id: Node ID
            graph_name: Graph name
            agent_name: Agent name for logging
            max_retries: Maximum number of retry attempts (default 2, so 3 total attempts)

        Returns:
            AI message response

        Raises:
            httpx.ReadTimeout: If all retry attempts are exhausted
        """
        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                return await self._invoke_with_streaming(
                    llm_with_tools,
                    messages,
                    streaming_enabled,
                    ws_notifier,
                    execution_id,
                    node_id,
                    graph_name,
                    agent_name,
                    emit_content_chunks=emit_content_chunks,
                )
            except (
                httpx.ReadTimeout,
                httpx.ConnectTimeout,
                httpx.WriteTimeout,
                asyncio.TimeoutError,
            ) as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = 2 ** (attempt + 1)  # 2s, 4s
                    self.logger.warning(
                        f"[TOOL-EXECUTOR] LLM timeout for {agent_name} "
                        f"(attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {wait_time}s: {type(e).__name__}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"[TOOL-EXECUTOR] LLM timeout for {agent_name} "
                        f"after {max_retries + 1} attempts: {type(e).__name__}"
                    )
                    raise
        # Should not be reached, but satisfies type checker
        raise last_error  # type: ignore[misc]
