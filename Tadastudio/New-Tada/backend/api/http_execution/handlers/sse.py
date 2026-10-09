"""Server-Sent Events (SSE) handler for HTTP execution API.

This module provides real-time execution streaming via SSE,
allowing clients to receive live updates during workflow execution.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import unquote

from backend.services.execution.history import ExecutionHistoryService
from backend.api.graph.services.execution_manager import execution_manager
from backend.services.config import get_logger
from backend.services.dependency_injection import (
    get_execution_engine,
    get_graph_manager,
)

from ..exceptions import (
    AuthenticationRequiredException,
    InvalidAuthenticationTokenException,
    RateLimitExceededException,
    WorkflowNotPublishedException,
)
from ..models import SSEEvent
from ..services.authentication import http_auth_service
from ..utils.constants import (
    EXECUTION_ID_DATE_FORMAT,
    EXECUTION_ID_PREFIX,
    SSE_POLL_INTERVAL,
    sanitize_graph_name,
)


logger = get_logger(__name__)


class SSEHandler:
    """Handler for Server-Sent Events streaming of execution progress.

    This class manages SSE connections and streams execution updates in real-time,
    providing event-by-event notifications to connected clients.
    """

    @staticmethod
    async def stream_execution(
        graph_name: str,
        message: str,
        token: Optional[str] = None,
        file_data: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream execution progress via Server-Sent Events.

        This generator function yields SSE-formatted events as the execution progresses.
        Events include: acknowledged, started, node_executing, completed, failed, error, done.

        Args:
            graph_name: Name of the workflow to execute
            message: Input message for the workflow
            token: Pre-extracted token value (PAT or JWT)
            file_data: Optional file data for FILE_READ nodes

        Yields:
            SSE-formatted event strings

        Example:
            >>> async for event in SSEHandler.stream_execution("my-workflow", "Hello"):
            ...     print(event)  # "data: {...}\n\n"
        """
        logger.info(f"[SSE] Starting SSE stream for workflow '{graph_name}'")

        try:
            # Send initial acknowledgment
            yield SSEHandler._format_event(
                {
                    "event": "acknowledged",
                    "message": "Request received",
                    "graph": graph_name,
                }
            )

            # URL decode the graph name
            decoded_name = unquote(graph_name)

            # Perform security checks
            try:
                published_workflow, _ = http_auth_service.perform_full_security_check(
                    decoded_name,
                    token,
                    None,
                    log_success=False,
                )
            except WorkflowNotPublishedException:
                yield SSEHandler._format_error(
                    f'Workflow "{decoded_name}" is not published. '
                    "Only published workflows can be executed via HTTP."
                )
                return
            except AuthenticationRequiredException:
                yield SSEHandler._format_error(
                    "Authentication token required for this workflow"
                )
                return
            except InvalidAuthenticationTokenException:
                yield SSEHandler._format_error(
                    "Invalid or expired authentication token"
                )
                return
            except RateLimitExceededException as e:
                yield SSEHandler._format_error(
                    f"Rate limit exceeded for {e.limit_type}. "
                    f"Try again in {e.retry_after} seconds."
                )
                return

            # Load workflow
            graph = SSEHandler._load_workflow(decoded_name)
            if not graph:
                yield SSEHandler._format_error(f"Graph not found: {decoded_name}")
                return

            # Generate execution ID
            execution_id = SSEHandler._generate_execution_id(decoded_name)

            # Send execution started event
            yield SSEHandler._format_event(
                {
                    "event": "started",
                    "execution_id": execution_id,
                }
            )

            # Pre-register the execution
            SSEHandler._preregister_execution(execution_id, decoded_name)

            # Broadcast to WebSocket listeners
            await SSEHandler._broadcast_execution_start(
                execution_id, decoded_name, message
            )

            # Execute in thread pool
            input_data = {"message": message}
            if file_data:
                input_data["file_info"] = file_data
            execution_manager.submit_execution(
                graph,
                input_data,
                execution_id,
                trigger_type="api",
            )

            # Stream execution updates
            async for event in SSEHandler._stream_execution_updates(execution_id):
                yield event

            # Send done event
            yield SSEHandler._format_event({"event": "done"})

            logger.info(f"[SSE] Completed SSE stream for execution {execution_id}")

        except Exception as e:
            logger.error(f"[SSE] SSE execution error: {e}")
            yield SSEHandler._format_error(
                "Execution failed. Check server logs for details."
            )

    @staticmethod
    def _format_event(event_data: SSEEvent) -> str:
        """Format an event as SSE data.

        Args:
            event_data: Event dictionary

        Returns:
            SSE-formatted string

        Example:
            >>> formatted = SSEHandler._format_event({"event": "started", "id": "123"})
            >>> print(formatted)  # 'data: {"event": "started", "id": "123"}\n\n'
        """
        # Remove None values
        cleaned_data = {k: v for k, v in event_data.items() if v is not None}
        return f"data: {json.dumps(cleaned_data)}\n\n"

    @staticmethod
    def _format_error(message: str) -> str:
        """Format an error event.

        Args:
            message: Error message

        Returns:
            SSE-formatted error event
        """
        return SSEHandler._format_event({"event": "error", "message": message})

    @staticmethod
    def _load_workflow(graph_name: str) -> Optional[Any]:
        """Load workflow from graph manager.

        Args:
            graph_name: Name of the workflow

        Returns:
            Graph object if found, None otherwise
        """
        logger.debug(f"[SSE] Loading workflow '{graph_name}'")

        graph = get_graph_manager().get_graph(graph_name)
        if not graph:
            logger.debug("[SSE] Workflow not in memory, loading from disk")
            graph = get_graph_manager().load_graph(graph_name, "default")

        if graph:
            logger.info(f"[SSE] Workflow '{graph_name}' loaded successfully")
        else:
            logger.error(f"[SSE] Workflow '{graph_name}' not found")

        return graph

    @staticmethod
    def _generate_execution_id(graph_name: str) -> str:
        """Generate a unique execution ID.

        Args:
            graph_name: Name of the workflow

        Returns:
            Execution ID string
        """
        timestamp = datetime.now().strftime(EXECUTION_ID_DATE_FORMAT)
        execution_id = (
            f"{EXECUTION_ID_PREFIX}{timestamp}_{sanitize_graph_name(graph_name)}"
        )
        logger.debug(f"[SSE] Generated execution ID: {execution_id}")
        return execution_id

    @staticmethod
    def _preregister_execution(execution_id: str, graph_name: str) -> None:
        """Pre-register execution in the execution engine.

        Args:
            execution_id: Execution identifier
            graph_name: Name of the workflow
        """
        logger.debug(f"[SSE] Pre-registering execution {execution_id}")

        get_execution_engine().active_executions[execution_id] = {
            "execution_id": execution_id,
            "status": "pending",
            "start_time": str(datetime.now()),
            "graph_name": graph_name,
            "current_node": None,
            "node_execution_map": {},
            "db_execution_id": None,
            "source": "http-sse",  # Mark as SSE-triggered
        }

        logger.info(f"[SSE] Execution {execution_id} pre-registered")

    @staticmethod
    async def _broadcast_execution_start(
        execution_id: str, graph_name: str, message: str
    ) -> None:
        """Broadcast execution start to WebSocket listeners.

        Args:
            execution_id: Execution identifier
            graph_name: Name of the workflow
            message: Input message
        """
        try:
            from backend.services.websocket import manager as ws_manager

            await ws_manager.broadcast_http_execution_start(
                execution_id=execution_id,
                graph_name=graph_name,
                input_data={"message": message},
            )
            logger.info(
                f"[SSE] Broadcast execution start for {graph_name} ({execution_id})"
            )
        except ImportError as e:
            logger.error(f"[SSE] Failed to import websocket manager: {e}")
        except Exception as e:
            logger.error(f"[SSE] Failed to broadcast execution start: {e}")

    @staticmethod
    async def _stream_execution_updates(execution_id: str) -> AsyncGenerator[str, None]:
        """Stream execution status updates.

        Polls the execution status and yields events for node changes and completion.

        Args:
            execution_id: Execution identifier

        Yields:
            SSE-formatted event strings
        """
        logger.debug(f"[SSE] Starting update stream for execution {execution_id}")

        last_node = None

        while True:
            await asyncio.sleep(SSE_POLL_INTERVAL)

            # Check execution status
            exec_data = get_execution_engine().active_executions.get(execution_id)

            # If execution not found, it was removed from active_executions (completed/failed)
            if not exec_data:
                logger.debug(
                    f"[SSE] Execution {execution_id} not found in active executions"
                )
                break

            if exec_data:
                status = exec_data.get("status")
                current_node = exec_data.get("current_node")

                # Send node update if changed
                if current_node and current_node != last_node:
                    logger.debug(
                        f"[SSE] Execution {execution_id} now at node: {current_node}"
                    )
                    yield SSEHandler._format_event(
                        {
                            "event": "node_executing",
                            "node": current_node,
                            "status": status,
                        }
                    )
                    last_node = current_node

                # Check if completed
                if status == "completed":
                    output = await SSEHandler._get_execution_output(exec_data)
                    logger.info(f"[SSE] Execution {execution_id} completed")
                    yield SSEHandler._format_event(
                        {
                            "event": "completed",
                            "execution_id": execution_id,
                            "output": output,
                        }
                    )
                    break

                elif status == "failed":
                    error_msg = exec_data.get("error", "Execution failed")
                    logger.error(f"[SSE] Execution {execution_id} failed: {error_msg}")
                    yield SSEHandler._format_event(
                        {
                            "event": "failed",
                            "execution_id": execution_id,
                            "error": error_msg,
                        }
                    )
                    break

    @staticmethod
    async def _get_execution_output(exec_data: dict) -> Optional[Any]:
        """Get the final execution output.

        Args:
            exec_data: Execution state data

        Returns:
            Execution output if available
        """
        db_execution_id = exec_data.get("db_execution_id")
        if not db_execution_id:
            logger.debug("[SSE] No db_execution_id available for output extraction")
            return None

        try:
            execution_data = ExecutionHistoryService.get_graph_execution(
                db_execution_id
            )

            if execution_data and execution_data.get("node_executions"):
                # Find END node output
                for node_exec in execution_data["node_executions"]:
                    if node_exec.get("node_type") == "END" and node_exec.get(
                        "output_data"
                    ):
                        logger.debug("[SSE] Found END node output")
                        return node_exec["output_data"]

            logger.debug("[SSE] No END node output found")
        except Exception as e:
            logger.error(f"[SSE] Failed to get execution output: {e}")

        return None


# Singleton instance
sse_handler = SSEHandler()


def get_sse_handler() -> SSEHandler:
    """Get the SSE handler instance.

    Returns:
        SSEHandler instance

    Example:
        >>> from backend.api.http_execution.handlers.sse import get_sse_handler
        >>> handler = get_sse_handler()
        >>> async for event in handler.stream_execution("my-workflow", "Hello"):
        ...     print(event)
    """
    return sse_handler
