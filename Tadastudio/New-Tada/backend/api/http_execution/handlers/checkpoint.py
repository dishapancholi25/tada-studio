"""Checkpoint handler for HTTP execution API.

This module handles checkpoint pause/resume functionality for HTTP-triggered
executions, managing checkpoint state storage and resumption.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Union

from backend.api.checkpoints.models import ResumeExecutionRequest
from backend.services.config import get_logger
from backend.services.dependency_injection import get_execution_engine

from ..exceptions import CheckpointNotFoundException
from ..models import (
    CheckpointNodeData,
    CheckpointPausedResponse,
    CheckpointStateData,
    HttpExecutionResponse,
)


logger = get_logger(__name__)


# In-memory storage for paused HTTP executions
# In production, this should be in a database
http_execution_states: Dict[str, CheckpointStateData] = {}


class CheckpointHandler:
    """Handler for checkpoint pause and resume operations.

    This class manages the state of paused HTTP executions and provides
    methods to resume them with user input.
    """

    @staticmethod
    def get_checkpoint_node_data(db_execution_id: int) -> Optional[CheckpointNodeData]:
        """Get the paused checkpoint node's data including its input.

        Queries the execution history to find the checkpoint node that caused
        the pause and extracts its input data.

        Args:
            db_execution_id: Database execution ID

        Returns:
            CheckpointNodeData if found, None otherwise

        Example:
            >>> checkpoint_data = CheckpointHandler.get_checkpoint_node_data(123)
            >>> if checkpoint_data:
            ...     print(f"Paused at: {checkpoint_data['node_name']}")
        """
        logger.debug(
            f"[CHECKPOINT] Getting checkpoint node data for execution {db_execution_id}"
        )

        try:
            from backend.services.execution.history import ExecutionHistoryService

            node_execs = ExecutionHistoryService.get_node_executions(db_execution_id)

            for node in node_execs:
                if (
                    node.get("node_type") == "CHECKPOINT"
                    and node.get("status") == "paused"
                ):
                    # Extract the message from input_data (previous node's output)
                    input_data = node.get("input_data", {})
                    checkpoint_input = input_data.get("message", "")

                    checkpoint_data: CheckpointNodeData = {
                        "node_name": node.get("node_name", "Checkpoint"),
                        "checkpoint_input": checkpoint_input,
                        "node_id": node.get("node_id", ""),
                    }

                    logger.info(
                        f"[CHECKPOINT] Found checkpoint node: {checkpoint_data['node_name']}"
                    )
                    return checkpoint_data

            logger.warning(
                f"[CHECKPOINT] No paused checkpoint found for execution {db_execution_id}"
            )

        except Exception as e:
            logger.error(
                f"[CHECKPOINT] Failed to get checkpoint node data for execution {db_execution_id}: {e}"
            )

        return None

    @staticmethod
    def store_checkpoint_state(
        thread_id: str,
        graph_name: str,
        checkpoint_id: str,
        execution_id: str,
        db_execution_id: Optional[int],
        checkpoint_node: str,
        checkpoint_input: Any,
    ) -> None:
        """Store checkpoint state for later resumption.

        Args:
            thread_id: Thread ID for resumption
            graph_name: Name of the workflow
            checkpoint_id: Checkpoint identifier
            execution_id: Execution identifier
            db_execution_id: Database execution ID
            checkpoint_node: Name of the checkpoint node
            checkpoint_input: Input to the checkpoint node

        Example:
            >>> CheckpointHandler.store_checkpoint_state(
            ...     "thread_123", "my-workflow", "checkpoint_1",
            ...     "exec_123", 456, "User Input", "Previous output"
            ... )
        """
        state_data: CheckpointStateData = {
            "graph_name": graph_name,
            "checkpoint_id": checkpoint_id,
            "execution_id": execution_id,
            "db_execution_id": db_execution_id,
            "paused_at": datetime.now().isoformat(),
            "checkpoint_node": checkpoint_node,
            "checkpoint_input": checkpoint_input,
        }

        http_execution_states[thread_id] = state_data

        logger.info(
            f"[CHECKPOINT] Stored checkpoint state for thread {thread_id} "
            f"(checkpoint: {checkpoint_node})"
        )

    @staticmethod
    def get_checkpoint_state(thread_id: str) -> Optional[CheckpointStateData]:
        """Get stored checkpoint state.

        Args:
            thread_id: Thread ID to look up

        Returns:
            CheckpointStateData if found, None otherwise

        Example:
            >>> state = CheckpointHandler.get_checkpoint_state("thread_123")
            >>> if state:
            ...     print(f"Workflow: {state['graph_name']}")
        """
        state = http_execution_states.get(thread_id)

        if state:
            logger.debug(
                f"[CHECKPOINT] Retrieved checkpoint state for thread {thread_id}"
            )
        else:
            logger.debug(
                f"[CHECKPOINT] No checkpoint state found for thread {thread_id}"
            )

        return state

    @staticmethod
    def delete_checkpoint_state(thread_id: str) -> None:
        """Delete checkpoint state after completion.

        Args:
            thread_id: Thread ID to delete

        Example:
            >>> CheckpointHandler.delete_checkpoint_state("thread_123")
        """
        if thread_id in http_execution_states:
            del http_execution_states[thread_id]
            logger.info(f"[CHECKPOINT] Deleted checkpoint state for thread {thread_id}")
        else:
            logger.debug(
                f"[CHECKPOINT] No checkpoint state to delete for thread {thread_id}"
            )

    @staticmethod
    def create_checkpoint_response(
        execution_id: str,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_node: str,
        checkpoint_input: Any,
        graph_name: str,
    ) -> HttpExecutionResponse:
        """Create a checkpoint paused response.

        Args:
            execution_id: Execution identifier
            thread_id: Thread ID for resumption
            checkpoint_id: Checkpoint identifier
            checkpoint_node: Name of the checkpoint node
            checkpoint_input: Input to the checkpoint
            graph_name: Name of the workflow

        Returns:
            HttpExecutionResponse with checkpoint data

        Example:
            >>> response = CheckpointHandler.create_checkpoint_response(
            ...     "exec_123", "thread_123", "checkpoint_1",
            ...     "User Input", "Previous output", "my-workflow"
            ... )
        """
        checkpoint_response = CheckpointPausedResponse(
            status="paused",
            execution_id=execution_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            checkpoint_node=checkpoint_node,
            checkpoint_input=checkpoint_input,
            resume_endpoint=f"/api/http-execution/resume/{graph_name}",
            resume_instructions="POST to resume_endpoint with thread_id, checkpoint_id, and user_input",
        )

        logger.info(
            f"[CHECKPOINT] Created checkpoint response for execution {execution_id}"
        )

        return HttpExecutionResponse(
            success=True,
            execution_id=execution_id,
            status="paused",
            checkpoint_data=checkpoint_response,
        )

    @staticmethod
    async def resume_checkpoint(
        graph_name: str,
        thread_id: str,
        checkpoint_id: str,
        user_input: Any,
    ) -> Union[HttpExecutionResponse, Dict[str, Any]]:
        """Resume a paused execution from a checkpoint.

        Args:
            graph_name: Name of the workflow
            thread_id: Thread ID of the paused execution
            checkpoint_id: Checkpoint identifier
            user_input: User's response to the checkpoint

        Returns:
            HttpExecutionResponse with completion or new checkpoint data

        Raises:
            CheckpointNotFoundException: If checkpoint state not found

        Example:
            >>> response = await CheckpointHandler.resume_checkpoint(
            ...     "my-workflow", "thread_123", "checkpoint_1", "User response"
            ... )
        """
        logger.info(
            f"[CHECKPOINT] Resuming execution for thread {thread_id} "
            f"(checkpoint: {checkpoint_id})"
        )

        # Verify the thread_id exists in our state storage
        stored_state = CheckpointHandler.get_checkpoint_state(thread_id)
        if not stored_state:
            logger.error(f"[CHECKPOINT] No state found for thread {thread_id}")
            raise CheckpointNotFoundException(thread_id)

        # Verify graph name matches
        if stored_state["graph_name"] != graph_name:
            logger.error(
                f"[CHECKPOINT] Graph name mismatch for thread {thread_id}: "
                f"expected {stored_state['graph_name']}, got {graph_name}"
            )
            raise CheckpointNotFoundException(thread_id)

        # Create resume request
        resume_req = ResumeExecutionRequest(
            graph_name=graph_name,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            new_input={"value": user_input},  # Wrap in value key as expected
        )

        # Use the execution engine to resume
        logger.debug(f"[CHECKPOINT] Calling execution engine to resume {thread_id}")
        result = await get_execution_engine().resume_from_checkpoint(
            graph_name=resume_req.graph_name,
            thread_id=resume_req.thread_id,
            checkpoint_id=resume_req.checkpoint_id,
            new_input=resume_req.new_input,
        )

        # Process the result
        return CheckpointHandler._process_resume_result(result, thread_id, graph_name)

    @staticmethod
    def _process_resume_result(
        result: Any, thread_id: str, graph_name: str
    ) -> Union[HttpExecutionResponse, Dict[str, Any]]:
        """Process the result of a checkpoint resume operation.

        Args:
            result: Result from execution engine
            thread_id: Thread ID
            graph_name: Workflow name

        Returns:
            HttpExecutionResponse with appropriate status
        """
        if not isinstance(result, dict):
            # If result is not a dict, assume completion
            CheckpointHandler.delete_checkpoint_state(thread_id)
            logger.info(
                f"[CHECKPOINT] Execution {thread_id} completed (non-dict result)"
            )
            return HttpExecutionResponse(
                success=True,
                execution_id=thread_id,
                status="completed",
                output=result,
            )

        status = result.get("status")
        logger.debug(f"[CHECKPOINT] Resume result status: {status}")

        if status == "paused":
            # Another checkpoint was hit
            return CheckpointHandler._handle_new_checkpoint(
                result, thread_id, graph_name
            )

        elif status == "completed":
            # Execution completed, clean up state
            CheckpointHandler.delete_checkpoint_state(thread_id)
            logger.info(f"[CHECKPOINT] Execution {thread_id} completed successfully")
            return HttpExecutionResponse(
                success=True,
                execution_id=thread_id,
                status="completed",
                output=result.get("output", result),
            )

        else:
            # Unknown status
            logger.warning(f"[CHECKPOINT] Unknown status from resume: {status}")
            return HttpExecutionResponse(
                success=True,
                execution_id=thread_id,
                status=status or "unknown",
                output=result,
            )

    @staticmethod
    def _handle_new_checkpoint(
        result: Dict[str, Any], thread_id: str, graph_name: str
    ) -> HttpExecutionResponse:
        """Handle a new checkpoint pause after resuming.

        Args:
            result: Result dictionary with new checkpoint info
            thread_id: Thread ID
            graph_name: Workflow name

        Returns:
            HttpExecutionResponse with new checkpoint data
        """
        db_execution_id = result.get("execution_id")
        new_checkpoint_id = result.get("checkpoint_id")

        logger.info(
            f"[CHECKPOINT] Execution {thread_id} hit another checkpoint: {new_checkpoint_id}"
        )

        # Get new checkpoint node details
        checkpoint_data = None
        if db_execution_id:
            checkpoint_data = CheckpointHandler.get_checkpoint_node_data(
                db_execution_id
            )

        if not checkpoint_data:
            checkpoint_data = {
                "node_name": "Checkpoint",
                "checkpoint_input": "",
                "node_id": "",
            }

        # Update stored state
        stored_state = CheckpointHandler.get_checkpoint_state(thread_id)
        if stored_state:
            stored_state["checkpoint_id"] = new_checkpoint_id
            stored_state["checkpoint_node"] = checkpoint_data["node_name"]
            stored_state["checkpoint_input"] = checkpoint_data["checkpoint_input"]
            stored_state["paused_at"] = datetime.now().isoformat()
            http_execution_states[thread_id] = stored_state

        # Return new checkpoint response
        return CheckpointHandler.create_checkpoint_response(
            execution_id=thread_id,
            thread_id=thread_id,
            checkpoint_id=new_checkpoint_id,
            checkpoint_node=checkpoint_data["node_name"],
            checkpoint_input=checkpoint_data["checkpoint_input"],
            graph_name=graph_name,
        )


# Singleton instance
checkpoint_handler = CheckpointHandler()


def get_checkpoint_handler() -> CheckpointHandler:
    """Get the checkpoint handler instance.

    Returns:
        CheckpointHandler instance

    Example:
        >>> from backend.api.http_execution.handlers.checkpoint import get_checkpoint_handler
        >>> handler = get_checkpoint_handler()
        >>> response = await handler.resume_checkpoint(...)
    """
    return checkpoint_handler
