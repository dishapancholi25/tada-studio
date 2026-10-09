"""Execution handler for HTTP execution API.

This module handles the core workflow execution logic for HTTP-triggered executions,
including execution triggering, polling, and output extraction.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, Optional, Union
from urllib.parse import unquote

from backend.services.execution.history import ExecutionHistoryService
from fastapi import Request
from backend.api.graph.services.execution_manager import execution_manager
from backend.services.config import get_logger
from backend.services.dependency_injection import (
    get_execution_engine,
    get_graph_manager,
)
from backend.services.memory import get_memory_manager
from backend.models.workflow.enums import NodeType
from backend.services.websocket import manager as ws_manager

from ..exceptions import (
    ExecutionFailedException,
    ExecutionTimeoutException,
    InvalidInputException,
    WorkflowNotFoundException,
)
from ..models import ClientContext, ExecutionState, HttpExecutionResponse
from ..services.authentication import http_auth_service
from ..utils.constants import (
    ENABLE_WEBSOCKET_BROADCAST,
    EXECUTION_ID_DATE_FORMAT,
    EXECUTION_ID_PREFIX,
    EXECUTION_POLL_INTERVAL,
    sanitize_graph_name,
)
from ..utils.output import extract_execution_output
from ..utils.request import extract_client_info
from .checkpoint import checkpoint_handler


logger = get_logger(__name__)


class HttpExecutionHandler:
    """Handler for HTTP-triggered workflow executions.

    This class manages the entire execution lifecycle:
    1. Security checks (authentication, rate limiting)
    2. Execution triggering
    3. Status polling (for sync mode)
    4. Output extraction
    5. WebSocket broadcasting
    """

    @staticmethod
    async def trigger_execution(
        graph_name: str,
        message: Optional[str] = None,
        file_data: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None,
        async_mode: bool = False,
        timeout: int = 300,
        broadcast_to_ui: bool = True,
        clear_memory: bool = False,
        fastapi_request: Optional[Request] = None,
    ) -> Union[HttpExecutionResponse, Dict[str, Any]]:
        """Trigger workflow execution via HTTP.

        This is the main entry point for HTTP executions. It performs security
        checks, triggers execution, and either returns immediately (async mode)
        or waits for completion (sync mode).

        Args:
            graph_name: Name of the workflow to execute
            message: Optional text message input
            file_data: Optional file data for FILE_READ nodes
            token: Optional PAT authentication token
            async_mode: If true, return immediately with execution ID
            timeout: Timeout in seconds for sync mode
            broadcast_to_ui: If true, broadcast to WebSocket listeners
            fastapi_request: FastAPI request object for client metadata

        Returns:
            HttpExecutionResponse with execution status and results

        Raises:
            Various exceptions for validation/security failures

        Example:
            >>> response = await HttpExecutionHandler.trigger_execution(
            ...     "my-workflow",
            ...     message="Hello",
            ...     async_mode=False,
            ...     timeout=300
            ... )
        """
        logger.info(f"[HTTP-EXEC] Triggering execution for workflow '{graph_name}'")

        # URL decode the graph name
        graph_name = unquote(graph_name)

        # Extract client context
        client_ip, user_agent = extract_client_info(fastapi_request)
        client_context: ClientContext = {
            "client_ip": client_ip,
            "user_agent": user_agent,
            "token": token,
            "graph_name": graph_name,
            "execution_id": "",  # Will be set below
        }

        # Perform security checks
        published_workflow, _ = http_auth_service.perform_full_security_check(
            graph_name, token, client_ip, log_success=False
        )

        # Load workflow by UUID with user's workspace for proper multi-tenant isolation
        # (graph_name parameter might be UUID or custom slug, but we load by workflow_id)
        logger.debug(
            f"[HTTP-EXEC] Loading workflow by UUID: {published_workflow.workflow_id} "
            f"for user: {published_workflow.user_id}"
        )
        graph = get_graph_manager().load_graph_by_workflow_id(
            workflow_id=published_workflow.workflow_id,
            username=published_workflow.user_id,
        )

        if not graph:
            logger.error(
                f"[HTTP-EXEC] Workflow '{published_workflow.graph_name}' "
                f"(UUID: {published_workflow.workflow_id}) not found"
            )
            raise WorkflowNotFoundException(published_workflow.graph_name)

        # Use the actual workflow name for execution IDs and logging (human-readable)
        workflow_name = published_workflow.graph_name
        logger.info(f"[HTTP-EXEC] Loaded workflow '{workflow_name}' successfully")

        # Optionally clear all agent (and sub-agent) memory before executing.
        # Used to start a fresh chat (e.g. TADA Chat "New Chat") so cross-execution
        # memory does not carry over. Best-effort: never blocks execution.
        if clear_memory:
            await HttpExecutionHandler._clear_workflow_agent_memories(
                graph, workflow_name
            )

        # Prepare input data
        input_data = HttpExecutionHandler._prepare_input_data(message, file_data)

        # Generate execution ID using workflow name (not UUID - for readability)
        execution_id = HttpExecutionHandler._generate_execution_id(workflow_name)
        client_context["execution_id"] = execution_id

        # Log the access attempt
        http_auth_service.log_access_attempt(
            published_workflow=published_workflow,
            graph_name=graph_name,
            client_context=client_context,
            response_status=200,
            execution_id=execution_id,
        )

        # Pre-register the execution
        HttpExecutionHandler._preregister_execution(execution_id, workflow_name)
        ws_manager.register_pending(execution_id, published_workflow.user_id, ttl=30)

        # Broadcast to WebSocket if enabled
        if broadcast_to_ui and ENABLE_WEBSOCKET_BROADCAST:
            await HttpExecutionHandler._broadcast_execution_start(
                execution_id, workflow_name, input_data
            )

        # Execute in thread pool with user and workflow tracking
        future = execution_manager.submit_execution(
            graph=graph,
            initial_input=input_data,
            execution_id=execution_id,
            user_id=published_workflow.user_id,
            workflow_id=published_workflow.workflow_id,
            graph_definition_id=None,  # Published workflows don't have graph_definition_id yet
            trigger_type="api",
        )

        # If async mode, return immediately
        if async_mode:
            logger.info(f"[HTTP-EXEC] Async execution started: {execution_id}")
            return HttpExecutionResponse(
                success=True,
                execution_id=execution_id,
                status="running",
                status_endpoint=f"/api/graph/execution/{execution_id}/status",
                message=f"Workflow '{graph_name}' execution started successfully",
            )

        # Otherwise, wait for completion
        logger.info(f"[HTTP-EXEC] Sync execution started: {execution_id}, waiting...")
        return await HttpExecutionHandler._wait_for_completion(
            execution_id, workflow_name, timeout, future
        )

    @staticmethod
    async def _clear_workflow_agent_memories(graph: Any, workflow_name: str) -> None:
        """Clear stored conversation memory for every agent in a workflow.

        Iterates all AGENT nodes (main agents and sub-agents alike, since both are
        AGENT-type nodes in the graph) and permanently deletes their conversation
        memories across all executions. Best-effort: any failure is logged and
        never blocks workflow execution.

        Args:
            graph: Loaded GraphData for the workflow
            workflow_name: Human-readable workflow name for logging
        """
        try:
            agent_ids = [
                node.uniq_id
                for node in getattr(graph, "nodes", [])
                if getattr(node, "type", None) == NodeType.AGENT
            ]

            if not agent_ids:
                logger.info(
                    f"[HTTP-EXEC] clear_memory requested for '{workflow_name}' "
                    f"but no agent nodes were found"
                )
                return

            memory_manager = get_memory_manager()
            total_cleared = 0
            for agent_id in agent_ids:
                try:
                    total_cleared += await memory_manager.clear_agent_memory(agent_id)
                except Exception as agent_error:  # noqa: BLE001
                    logger.warning(
                        f"[HTTP-EXEC] Failed to clear memory for agent "
                        f"{agent_id}: {agent_error}"
                    )

            logger.info(
                f"[HTTP-EXEC] Cleared {total_cleared} memories across "
                f"{len(agent_ids)} agent(s) for workflow '{workflow_name}'"
            )
        except Exception as e:  # noqa: BLE001
            logger.error(
                f"[HTTP-EXEC] Unexpected error clearing agent memories for "
                f"'{workflow_name}': {e}"
            )

    @staticmethod
    def _load_workflow(graph_name: str) -> Any:
        """Load workflow from graph manager.

        Args:
            graph_name: Name of the workflow

        Returns:
            Graph object

        Raises:
            WorkflowNotFoundException: If workflow not found
        """
        logger.debug(f"[HTTP-EXEC] Loading workflow '{graph_name}'")

        graph = get_graph_manager().get_graph(graph_name)
        if not graph:
            # Try loading from disk
            logger.debug("[HTTP-EXEC] Workflow not in memory, loading from disk")
            graph = get_graph_manager().load_graph(graph_name, "default")

        if not graph:
            logger.error(f"[HTTP-EXEC] Workflow '{graph_name}' not found")
            raise WorkflowNotFoundException(graph_name)

        logger.info(f"[HTTP-EXEC] Workflow '{graph_name}' loaded successfully")
        return graph

    @staticmethod
    def _prepare_input_data(
        message: Optional[str], file_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare input data for execution.

        Args:
            message: Optional text message
            file_data: Optional file data

        Returns:
            Input data dictionary

        Raises:
            InvalidInputException: If neither message nor file provided
        """
        if not message and not file_data:
            logger.error("[HTTP-EXEC] No input provided (neither message nor file)")
            raise InvalidInputException("Either message or file must be provided")

        input_data: Dict[str, Any] = {}
        if message:
            input_data["message"] = message
            logger.debug(f"[HTTP-EXEC] Added message to input (length: {len(message)})")

        if file_data:
            input_data["file_info"] = file_data
            logger.debug(
                f"[HTTP-EXEC] Added file_info to input: {file_data.get('name', 'unknown')}"
            )

        return input_data

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
        logger.debug(f"[HTTP-EXEC] Generated execution ID: {execution_id}")
        return execution_id

    @staticmethod
    def _preregister_execution(execution_id: str, graph_name: str) -> None:
        """Pre-register execution in the execution engine.

        Args:
            execution_id: Execution identifier
            graph_name: Name of the workflow
        """
        logger.debug(f"[HTTP-EXEC] Pre-registering execution {execution_id}")

        get_execution_engine().active_executions[execution_id] = {
            "execution_id": execution_id,
            "status": "pending",
            "start_time": str(datetime.now()),
            "graph_name": graph_name,
            "current_node": None,
            "node_execution_map": {},
            "db_execution_id": None,
            "source": "http",  # Mark as HTTP-triggered
        }

        logger.info(f"[HTTP-EXEC] Execution {execution_id} pre-registered")

    @staticmethod
    async def _broadcast_execution_start(
        execution_id: str, graph_name: str, input_data: Dict[str, Any]
    ) -> None:
        """Broadcast execution start to WebSocket listeners.

        Args:
            execution_id: Execution identifier
            graph_name: Name of the workflow
            input_data: Execution input data
        """
        try:
            await ws_manager.broadcast_http_execution_start(
                execution_id=execution_id,
                graph_name=graph_name,
                input_data=input_data,
            )
            logger.info(
                f"[HTTP-EXEC] Broadcast execution start for {graph_name} ({execution_id})"
            )
        except ImportError as e:
            logger.error(f"[HTTP-EXEC] Failed to import websocket manager: {e}")
        except Exception as e:
            logger.error(f"[HTTP-EXEC] Failed to broadcast execution start: {e}")

    @staticmethod
    async def _wait_for_completion(
        execution_id: str, graph_name: str, timeout: int, future: Any
    ) -> HttpExecutionResponse:
        """Wait for execution to complete and return results.

        This method polls the execution status until it completes, fails, or times out.

        Args:
            execution_id: Execution identifier
            graph_name: Workflow name
            timeout: Timeout in seconds
            future: Future object from thread pool

        Returns:
            HttpExecutionResponse with execution results

        Raises:
            ExecutionTimeoutException: If execution exceeds timeout
            ExecutionFailedException: If execution fails
        """
        logger.debug(
            f"[HTTP-EXEC] Waiting for execution {execution_id} (timeout: {timeout}s)"
        )

        start_time = time.time()

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.error(
                    f"[HTTP-EXEC] Execution {execution_id} timed out after {timeout}s"
                )
                raise ExecutionTimeoutException(timeout, execution_id)

            # Check execution status
            exec_data = get_execution_engine().active_executions.get(execution_id)

            # If execution not found, check if future is done
            if not exec_data:
                if future.done():
                    logger.debug(
                        f"[HTTP-EXEC] Execution {execution_id} completed (future done)"
                    )
                    return await HttpExecutionHandler._handle_future_completion(
                        future, execution_id
                    )
                await asyncio.sleep(EXECUTION_POLL_INTERVAL)
                continue

            status = exec_data.get("status")
            logger.debug(f"[HTTP-EXEC] Execution {execution_id} status: {status}")

            # Handle paused status (checkpoint)
            if status == "paused":
                return await HttpExecutionHandler._handle_checkpoint_pause(
                    exec_data, execution_id, graph_name
                )

            # Handle completed/failed status
            if status in ["completed", "failed"]:
                return await HttpExecutionHandler._handle_execution_complete(
                    exec_data, execution_id, status
                )

            # Wait before checking again
            await asyncio.sleep(EXECUTION_POLL_INTERVAL)

    @staticmethod
    async def _handle_future_completion(
        future: Any, execution_id: str
    ) -> HttpExecutionResponse:
        """Handle completion when future is done but execution not in active list.

        Args:
            future: Future object
            execution_id: Execution identifier

        Returns:
            HttpExecutionResponse
        """
        try:
            result = future.result()
            if result is not None:
                logger.info(f"[HTTP-EXEC] Got result from future for {execution_id}")
                return result
        except Exception as e:
            logger.error(
                f"[HTTP-EXEC] Error getting future result for {execution_id}: {e}"
            )

        # The future result is None — execution was removed from active_executions
        # before the poll loop captured it. Use the same retrieval path as
        # _handle_execution_complete: query ExecutionHistoryService by the
        # websocket execution ID (exec_* prefix is supported by get_graph_execution_dict).
        try:
            execution_data = ExecutionHistoryService.get_graph_execution_dict(
                execution_id
            )
            if execution_data:
                output = extract_execution_output(execution_data)
                if output is not None:
                    logger.info(
                        f"[HTTP-EXEC] Retrieved output from history for {execution_id}"
                    )
                    return HttpExecutionResponse(
                        success=True,
                        execution_id=execution_id,
                        status="completed",
                        output=output,
                    )
        except Exception as e:
            logger.error(
                f"[HTTP-EXEC] Failed to retrieve history for {execution_id}: {e}"
            )

        # Return default completion response
        return HttpExecutionResponse(
            success=True,
            execution_id=execution_id,
            status="completed",
            message="Workflow completed",
        )

    @staticmethod
    async def _handle_checkpoint_pause(
        exec_data: ExecutionState, execution_id: str, graph_name: str
    ) -> HttpExecutionResponse:
        """Handle execution pause at checkpoint.

        Args:
            exec_data: Execution state data
            execution_id: Execution identifier
            graph_name: Workflow name

        Returns:
            HttpExecutionResponse with checkpoint data
        """
        logger.info(f"[HTTP-EXEC] Execution {execution_id} paused at checkpoint")

        db_execution_id = exec_data.get("db_execution_id")
        paused_data = exec_data.get("paused", {})
        checkpoint_id = paused_data.get("checkpoint_id")
        thread_id = execution_id  # Thread ID is the execution ID

        # Get checkpoint node details
        checkpoint_data = None
        if db_execution_id:
            checkpoint_data = checkpoint_handler.get_checkpoint_node_data(
                db_execution_id
            )

        if not checkpoint_data:
            # Fallback if we can't get checkpoint data
            checkpoint_data = {
                "node_name": "Checkpoint",
                "checkpoint_input": "",
                "node_id": "",
            }

        # Store state for resumption
        checkpoint_handler.store_checkpoint_state(
            thread_id=thread_id,
            graph_name=graph_name,
            checkpoint_id=checkpoint_id,
            execution_id=execution_id,
            db_execution_id=db_execution_id,
            checkpoint_node=checkpoint_data["node_name"],
            checkpoint_input=checkpoint_data["checkpoint_input"],
        )

        # Return checkpoint response
        return checkpoint_handler.create_checkpoint_response(
            execution_id=execution_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            checkpoint_node=checkpoint_data["node_name"],
            checkpoint_input=checkpoint_data["checkpoint_input"],
            graph_name=graph_name,
        )

    @staticmethod
    async def _handle_execution_complete(
        exec_data: ExecutionState, execution_id: str, status: str
    ) -> HttpExecutionResponse:
        """Handle completed or failed execution.

        Args:
            exec_data: Execution state data
            execution_id: Execution identifier
            status: Execution status ("completed" or "failed")

        Returns:
            HttpExecutionResponse with execution output

        Raises:
            ExecutionFailedException: If execution failed
        """
        logger.info(f"[HTTP-EXEC] Execution {execution_id} {status}")

        if status == "failed":
            error_msg = exec_data.get("error", "Execution failed")
            logger.error(f"[HTTP-EXEC] Execution {execution_id} failed: {error_msg}")
            raise ExecutionFailedException(execution_id, error_msg)

        # Get execution output
        db_execution_id = exec_data.get("db_execution_id")
        output = None

        if db_execution_id:
            try:
                execution_data = ExecutionHistoryService.get_graph_execution_dict(
                    db_execution_id
                )
                output = extract_execution_output(execution_data)
                logger.debug(
                    f"[HTTP-EXEC] Extracted output for {execution_id}: {bool(output)}"
                )
            except Exception as e:
                logger.error(
                    f"[HTTP-EXEC] Failed to get execution results for {execution_id}: {e}"
                )

        # Return success response
        if output is not None:
            return HttpExecutionResponse(
                success=True,
                execution_id=execution_id,
                status="completed",
                output=output,
            )
        else:
            return HttpExecutionResponse(
                success=True,
                execution_id=execution_id,
                status="completed",
                message="Workflow completed successfully",
            )


# Singleton instance
http_execution_handler = HttpExecutionHandler()


def get_http_execution_handler() -> HttpExecutionHandler:
    """Get the HTTP execution handler instance.

    Returns:
        HttpExecutionHandler instance

    Example:
        >>> from backend.api.http_execution.handlers.execution import get_http_execution_handler
        >>> handler = get_http_execution_handler()
        >>> response = await handler.trigger_execution(...)
    """
    return http_execution_handler
