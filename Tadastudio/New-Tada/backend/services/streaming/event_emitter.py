"""Streaming event emitter for granular workflow visibility.

Uses LangGraph's get_stream_writer() to emit custom events that flow
through the "custom" stream mode to WebSocket clients.

Events emitted:
- tool_call_start: When a tool execution begins
- tool_call_progress: Progress updates during tool execution
- tool_call_complete: When a tool execution finishes successfully
- tool_call_error: When a tool execution fails
- subagent_start: When delegation to a sub-agent begins
- subagent_complete: When a sub-agent finishes execution
- content_chunk: Token-by-token streaming for agents without tools (e.g., subagents)
"""

import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from langgraph.config import get_stream_writer

from ..config import get_logger

logger = get_logger("streaming.event_emitter")


class StreamWriterRegistry:
    """Thread-safe registry for stream writers by execution_id.

    This registry allows subagent tool executions to access the parent workflow's
    stream writer even when running in an isolated context (fresh contextvars.Context).

    The problem: Subagent delegation uses run_async_in_sync_isolated() which creates
    a fresh context to prevent PostgreSQL checkpointer conflicts. This also strips
    the LangGraph stream writer context variable.

    The solution: Register stream writers by execution_id before subgraph execution,
    and look them up by execution_id as a fallback when the context variable isn't available.
    """

    _registry: Dict[str, Callable] = {}
    _lock = threading.Lock()

    @classmethod
    def register(cls, execution_id: str, writer: Callable) -> None:
        """Register a stream writer for an execution.

        Args:
            execution_id: Unique identifier for the workflow execution
            writer: The stream writer function from LangGraph
        """
        with cls._lock:
            cls._registry[execution_id] = writer
            logger.info(
                f"[STREAM-REGISTRY] Registered writer for exec_id={execution_id}, "
                f"total_registered={len(cls._registry)}"
            )

    @classmethod
    def unregister(cls, execution_id: str) -> None:
        """Unregister a stream writer when execution completes.

        Args:
            execution_id: Unique identifier for the workflow execution
        """
        with cls._lock:
            if execution_id in cls._registry:
                del cls._registry[execution_id]
                logger.debug(
                    f"Unregistered stream writer for execution: {execution_id}"
                )

    @classmethod
    def get(cls, execution_id: str) -> Optional[Callable]:
        """Get a stream writer by execution_id.

        Args:
            execution_id: Unique identifier for the workflow execution

        Returns:
            The stream writer function, or None if not registered
        """
        with cls._lock:
            writer = cls._registry.get(execution_id)
            if writer:
                logger.debug(
                    f"[STREAM-REGISTRY] Found writer for exec_id={execution_id}"
                )
            else:
                logger.warning(
                    f"[STREAM-REGISTRY] No writer found for exec_id={execution_id}, "
                    f"registered_ids={list(cls._registry.keys())}"
                )
            return writer


class StreamingEventEmitter:
    """Emits custom streaming events via LangGraph stream writer.

    All emit methods are safe to call even outside of a LangGraph execution
    context - they will simply no-op if no stream writer is available.
    """

    @staticmethod
    def _get_writer(execution_id: Optional[str] = None):
        """Get the stream writer, preferring registry when execution_id is provided.

        IMPORTANT: When execution_id is provided, we check the registry FIRST.
        This ensures sub-agent events go through the bridged writer that's connected
        to WebSocket, rather than the subgraph's own disconnected stream writer.

        The subgraph has its own LangGraph stream writer context (set up during
        ainvoke()), but that writer is NOT connected to WebSocket. By checking
        the registry first, we ensure all events for a given execution flow
        through the parent workflow's bridged writer.

        Args:
            execution_id: Optional execution ID to look up in registry

        Returns:
            The stream writer function, or None if not available.
        """
        # FIRST: If execution_id is provided, prefer registry writer.
        # This ensures sub-agent events go through the bridged writer to WebSocket,
        # not the subgraph's disconnected internal writer.
        if execution_id:
            registry_writer = StreamWriterRegistry.get(execution_id)
            if registry_writer:
                logger.info(
                    f"[STREAM-WRITER] Using registry writer for exec_id={execution_id}"
                )
                return registry_writer
            else:
                logger.debug(
                    f"[STREAM-WRITER] No registry writer for exec_id={execution_id}, trying context"
                )

        # SECOND: Try LangGraph context (for cases without execution_id or registry miss)
        try:
            writer = get_stream_writer()
            if writer:
                logger.debug(
                    f"[STREAM-WRITER] Got writer from LangGraph context (exec_id={execution_id})"
                )
                return writer
            else:
                logger.debug(
                    f"[STREAM-WRITER] LangGraph context returned None (exec_id={execution_id})"
                )
        except Exception as e:
            # Not in a LangGraph execution context
            logger.debug(
                f"[STREAM-WRITER] LangGraph context unavailable: {type(e).__name__} (exec_id={execution_id})"
            )

        return None

    @staticmethod
    def _timestamp() -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def emit_tool_start(
        call_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        agent_id: str,
        agent_name: str,
        tool_node_id: Optional[str] = None,
        tool_node_name: Optional[str] = None,
        tool_node_type: Optional[str] = None,
        execution_id: Optional[str] = None,
        review_iteration: Optional[int] = None,
        node_execution_id: Optional[str] = None,
        invocation_index: Optional[int] = None,
        parent_subagent_id: Optional[str] = None,
    ) -> None:
        """Emit tool call start event.

        Args:
            call_id: Unique identifier for this tool call (from LLM tool_call.id)
            tool_name: Name of the tool being called
            tool_args: Arguments passed to the tool
            agent_id: ID of the agent making the call
            agent_name: Name of the agent making the call
            tool_node_id: Workflow node ID for the tool (for timeline updates)
            tool_node_name: Workflow node name for the tool
            tool_node_type: Workflow node type (e.g., DOCUMENT_SEARCH, HTTP_REQUEST)
            execution_id: Optional execution ID for registry lookup (for subagents)
            parent_subagent_id: Unique ID of parent subagent invocation (format: {node_id}_iter_{iteration})
        """
        logger.info(
            f"[EMIT-TOOL-START] tool={tool_name}, agent={agent_name}, "
            f"exec_id={execution_id}, call_id={call_id}"
        )
        logger.info(
            f"[TOOL-SUBAGENT-LINK] emit_tool_start: tool={tool_name}, "
            f"parent_subagent_id={parent_subagent_id}, invocation_index={invocation_index}, "
            f"agent={agent_name}, call_id={call_id}"
        )
        writer = StreamingEventEmitter._get_writer(execution_id)
        if writer:
            logger.info(f"[EMIT-TOOL-START] Got writer, sending event for {tool_name}")
            event = {
                "event_type": "tool_call_start",
                "call_id": call_id,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "tool_node_id": tool_node_id,
                "tool_node_name": tool_node_name,
                "tool_node_type": tool_node_type,
                "review_iteration": review_iteration,
                "node_execution_id": node_execution_id,
                "invocation_index": invocation_index,
                "parent_subagent_id": parent_subagent_id,
                "timestamp": StreamingEventEmitter._timestamp(),
            }
            writer(event)
            logger.info(
                f"[EMIT-TOOL-START] Sent tool_call_start: {tool_name} (call_id={call_id})"
            )
        else:
            logger.warning(
                f"[EMIT-TOOL-START] No writer available for {tool_name}, "
                f"exec_id={execution_id} - event will not be streamed"
            )

    @staticmethod
    def emit_tool_progress(
        call_id: str,
        tool_name: str,
        message: str,
        progress: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
        execution_id: Optional[str] = None,
    ) -> None:
        """Emit tool execution progress event.

        Args:
            call_id: Unique identifier for this tool call
            tool_name: Name of the tool being executed
            message: Progress message (e.g., "Searching 3 collections...")
            progress: Optional progress percentage (0-100)
            metadata: Optional additional metadata
            execution_id: Optional execution ID for registry lookup (for subagents)
        """
        writer = StreamingEventEmitter._get_writer(execution_id)
        if writer:
            event = {
                "event_type": "tool_call_progress",
                "call_id": call_id,
                "tool_name": tool_name,
                "message": message,
                "progress": progress,
                "metadata": metadata,
                "timestamp": StreamingEventEmitter._timestamp(),
            }
            writer(event)
            logger.debug(f"Emitted tool_call_progress: {tool_name} - {message}")

    # Maximum size for full_result in streaming events (200KB)
    _MAX_FULL_RESULT_SIZE = 200 * 1024

    @staticmethod
    def emit_tool_complete(
        call_id: str,
        tool_name: str,
        result_preview: Optional[str] = None,
        duration_ms: float = 0,
        tool_node_id: Optional[str] = None,
        tool_node_name: Optional[str] = None,
        tool_node_type: Optional[str] = None,
        execution_id: Optional[str] = None,
        review_iteration: Optional[int] = None,
        node_execution_id: Optional[str] = None,
        invocation_index: Optional[int] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        parent_subagent_id: Optional[str] = None,
        full_result: Optional[str] = None,
        tool_input: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit tool call completion event.

        Args:
            call_id: Unique identifier for this tool call
            tool_name: Name of the tool that completed
            result_preview: First 500 chars of the result (for display)
            duration_ms: Execution duration in milliseconds
            tool_node_id: Workflow node ID for the tool (for timeline updates)
            tool_node_name: Workflow node name for the tool
            tool_node_type: Workflow node type (e.g., DOCUMENT_SEARCH, HTTP_REQUEST)
            execution_id: Optional execution ID for registry lookup (for subagents)
            agent_id: Parent agent's node ID (for grouping tools by subagent)
            agent_name: Parent agent's name
            parent_subagent_id: Unique ID of parent subagent invocation (format: {node_id}_iter_{iteration})
            full_result: Full tool result for real-time execution panel display (capped at 200KB)
            tool_input: Tool input arguments for real-time execution panel display
        """
        writer = StreamingEventEmitter._get_writer(execution_id)
        if writer:
            # Truncate result preview
            preview = result_preview[:500] if result_preview else None

            # Cap full result to prevent oversized WebSocket messages
            result_truncated = False
            capped_full_result = None
            if full_result:
                if len(full_result) > StreamingEventEmitter._MAX_FULL_RESULT_SIZE:
                    capped_full_result = full_result[
                        : StreamingEventEmitter._MAX_FULL_RESULT_SIZE
                    ]
                    result_truncated = True
                else:
                    capped_full_result = full_result

            event = {
                "event_type": "tool_call_complete",
                "call_id": call_id,
                "tool_name": tool_name,
                "result_preview": preview,
                "full_result": capped_full_result,
                "tool_input": tool_input,
                "result_truncated": result_truncated,
                "duration_ms": duration_ms,
                "tool_node_id": tool_node_id,
                "tool_node_name": tool_node_name,
                "tool_node_type": tool_node_type,
                "review_iteration": review_iteration,
                "node_execution_id": node_execution_id,
                "invocation_index": invocation_index,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "parent_subagent_id": parent_subagent_id,
                "timestamp": StreamingEventEmitter._timestamp(),
            }
            writer(event)
            logger.debug(
                f"Emitted tool_call_complete: {tool_name} ({duration_ms:.0f}ms)"
            )

    @staticmethod
    def emit_tool_error(
        call_id: str,
        tool_name: str,
        error: str,
        duration_ms: float = 0,
        tool_node_id: Optional[str] = None,
        tool_node_name: Optional[str] = None,
        tool_node_type: Optional[str] = None,
        execution_id: Optional[str] = None,
        review_iteration: Optional[int] = None,
        node_execution_id: Optional[str] = None,
        invocation_index: Optional[int] = None,
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        parent_subagent_id: Optional[str] = None,
    ) -> None:
        """Emit tool call error event.

        Args:
            call_id: Unique identifier for this tool call
            tool_name: Name of the tool that failed
            error: Error message
            duration_ms: Execution duration in milliseconds
            tool_node_id: Workflow node ID for the tool (for timeline updates)
            tool_node_name: Workflow node name for the tool
            tool_node_type: Workflow node type (e.g., DOCUMENT_SEARCH, HTTP_REQUEST)
            execution_id: Optional execution ID for registry lookup (for subagents)
            agent_id: Parent agent's node ID (for grouping tools by subagent)
            agent_name: Parent agent's name
            parent_subagent_id: Unique ID of parent subagent invocation (format: {node_id}_iter_{iteration})
        """
        writer = StreamingEventEmitter._get_writer(execution_id)
        if writer:
            event = {
                "event_type": "tool_call_error",
                "call_id": call_id,
                "tool_name": tool_name,
                "error": error,
                "duration_ms": duration_ms,
                "tool_node_id": tool_node_id,
                "tool_node_name": tool_node_name,
                "tool_node_type": tool_node_type,
                "review_iteration": review_iteration,
                "node_execution_id": node_execution_id,
                "invocation_index": invocation_index,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "parent_subagent_id": parent_subagent_id,
                "timestamp": StreamingEventEmitter._timestamp(),
            }
            writer(event)
            logger.debug(f"Emitted tool_call_error: {tool_name} - {error}")

    @staticmethod
    def emit_guardrail_violation(
        category: str,
        rule_name: str,
        message: str,
        severity: str = "block",
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        execution_id: Optional[str] = None,
        node_execution_id: Optional[str] = None,
        filter_id: Optional[str] = None,
        filter_type: Optional[str] = None,
        violation_db_id: Optional[str] = None,
        policy_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        enforcement_mode: Optional[str] = None,
    ) -> None:
        """Emit guardrail violation event.

        Args:
            category: Violation category (input, output, tool_call, token_budget, behavioral, custom_filter)
            rule_name: Name of the rule that was violated
            message: Human-readable violation description
            severity: Violation severity (block, warn, info)
            agent_id: Agent node ID where violation occurred
            agent_name: Agent name where violation occurred
            tool_name: Tool name if tool_call violation
            execution_id: Execution ID for registry lookup
            node_execution_id: Database UUID of the agent's NodeExecution record
            filter_id: Custom filter ID if custom_filter violation
            filter_type: Custom filter type (python_code, llm_judge, declarative) if applicable
            violation_db_id: Database UUID of the persisted GuardrailViolationEvent record
            policy_name: Name of the guardrail policy that triggered the violation
            enforcement_mode: Policy enforcement mode (enforce, audit, disabled)
        """
        writer = StreamingEventEmitter._get_writer(execution_id)
        if writer:
            event = {
                "event_type": "guardrail_violation",
                "category": category,
                "rule_name": rule_name,
                "message": message,
                "severity": severity,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "tool_name": tool_name,
                "node_execution_id": node_execution_id,
                "filter_id": filter_id,
                "filter_type": filter_type,
                "violation_db_id": violation_db_id,
                "policy_name": policy_name,
                "details": details,
                "enforcement_mode": enforcement_mode,
                "timestamp": StreamingEventEmitter._timestamp(),
            }
            writer(event)
            logger.info(
                f"Emitted guardrail_violation: {category}/{rule_name} - {message}"
            )

    @staticmethod
    def emit_subagent_start(
        subagent_id: str,
        subagent_name: str,
        task_description: str,
        parent_agent_id: str,
        parent_agent_name: str,
        iteration: int = 1,
        execution_id: Optional[str] = None,
        subagent_node_type: Optional[str] = None,
    ) -> None:
        """Emit sub-agent delegation start event.

        Args:
            subagent_id: ID of the sub-agent being delegated to
            subagent_name: Name of the sub-agent
            task_description: Description of the task being delegated
            parent_agent_id: ID of the orchestrator agent
            parent_agent_name: Name of the orchestrator agent
            iteration: Iteration number for distinguishing multiple invocations
            execution_id: Optional execution ID for registry lookup (for subagents)
            subagent_node_type: Node type of the subagent (e.g., "AGENT", "TOOL")
        """
        writer = StreamingEventEmitter._get_writer(execution_id)
        if writer:
            event = {
                "event_type": "subagent_start",
                "subagent_id": subagent_id,
                "subagent_name": subagent_name,
                "task_description": task_description,
                "parent_agent_id": parent_agent_id,
                "parent_agent_name": parent_agent_name,
                "iteration": iteration,
                "subagent_node_type": subagent_node_type,
                "timestamp": StreamingEventEmitter._timestamp(),
            }
            writer(event)
            logger.info(
                f"[SUBAGENT-NESTING-DEBUG] BE emit_subagent_start: "
                f"subagent_id={subagent_id}, name={subagent_name}, iteration={iteration}, "
                f"node_type={subagent_node_type}, timestamp={event['timestamp']}"
            )
            logger.debug(
                f"Emitted subagent_start: {subagent_name} iteration={iteration} (task: {task_description[:50]}...)"
            )

    @staticmethod
    def emit_subagent_complete(
        subagent_id: str,
        subagent_name: str,
        success: bool,
        response_preview: Optional[str] = None,
        duration_ms: float = 0,
        tools_used: Optional[list[str]] = None,
        iteration: int = 1,
        execution_id: Optional[str] = None,
    ) -> None:
        """Emit sub-agent completion event.

        Args:
            subagent_id: ID of the sub-agent that completed
            subagent_name: Name of the sub-agent
            success: Whether the sub-agent completed successfully
            response_preview: First 500 chars of the response
            duration_ms: Execution duration in milliseconds
            tools_used: List of tool names used by the sub-agent
            iteration: Iteration number for distinguishing multiple invocations
            execution_id: Optional execution ID for registry lookup (for subagents)
        """
        writer = StreamingEventEmitter._get_writer(execution_id)
        if writer:
            # Truncate response preview
            preview = response_preview[:500] if response_preview else None

            event = {
                "event_type": "subagent_complete",
                "subagent_id": subagent_id,
                "subagent_name": subagent_name,
                "success": success,
                "response_preview": preview,
                "duration_ms": duration_ms,
                "tools_used": tools_used or [],
                "iteration": iteration,
                "timestamp": StreamingEventEmitter._timestamp(),
            }
            writer(event)
            status = "success" if success else "failed"
            logger.debug(
                f"Emitted subagent_complete: {subagent_name} iteration={iteration} ({status}, {duration_ms:.0f}ms)"
            )

    @staticmethod
    def emit_content_chunk(
        content: str,
        agent_name: str,
        node_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        execution_order: Optional[int] = None,
        db_node_id: Optional[str] = None,
    ) -> None:
        """Emit a content chunk event for token-by-token streaming.

        Used for agents without tools that run outside LangGraph's stream mode,
        particularly subagents running in isolated contexts via asyncio.run().

        LangGraph's messages stream mode doesn't capture output from subagents
        because they run in a fresh context. This method explicitly emits content
        chunks through the stream writer registry.

        Args:
            content: The text content chunk (a single token or small piece of text)
            agent_name: Name of the agent producing the content
            node_id: Workflow node ID for the agent
            execution_id: Execution ID for registry lookup
            execution_order: Execution order for iteration discrimination (review loops)
            db_node_id: Database node execution ID for precise streaming attribution
        """
        # Only emit if there's actual content
        if not content:
            return

        writer = StreamingEventEmitter._get_writer(execution_id)
        if writer:
            event = {
                "event_type": "content_chunk",
                "content": content,
                "agent_name": agent_name,
                "node_id": node_id,
                "execution_order": execution_order,
                "db_node_id": db_node_id,
                "timestamp": StreamingEventEmitter._timestamp(),
            }
            writer(event)


# Singleton instance for easy import
streaming_emitter = StreamingEventEmitter()
