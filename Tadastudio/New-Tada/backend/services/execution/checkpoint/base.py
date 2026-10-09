"""
Base Checkpoint Executor.

This module provides the base class for all checkpoint node executors,
containing common functionality for checkpoint pause/resume operations.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

from backend.models.workflow import EnhancedNodeData
from backend.services.execution.history import ExecutionHistoryService
from backend.services.common.utils.websocket_notifier import ws_notifier
from backend.services.config import get_logger
from backend.services.execution.state import StateExecutionTracker
from backend.services.workflow.state import WorkflowState

if TYPE_CHECKING:
    from backend.models import GraphData

checkpoint_logger = get_logger("execution.checkpoint")


class CheckpointExecutor(ABC):
    """
    Base class for checkpoint node executors.

    Provides common functionality for:
    - Checkpoint iteration tracking (for loops)
    - Database node execution management
    - WebSocket notifications
    - State updates and execution order management

    Subclasses implement specific checkpoint types (manual, email, etc.)
    """

    def __init__(self, active_executions: Dict[str, Any]):
        """
        Initialize checkpoint executor.

        Args:
            active_executions: Reference to engine's active executions dict
        """
        self.active_executions = active_executions

    @abstractmethod
    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
        input_message: str,
    ) -> Dict[str, Any]:
        """
        Execute checkpoint node.

        Args:
            node: The checkpoint node to execute
            state: Current workflow state
            graph: The graph definition
            input_message: Input message for the checkpoint

        Returns:
            State updates dictionary with checkpoint results
        """
        pass

    def get_current_iteration(
        self, node: EnhancedNodeData, state: WorkflowState
    ) -> int:
        """
        Get current iteration for this checkpoint node.

        Handles checkpoint iteration tracking for loops - each time a checkpoint
        is reached in a loop, it gets a new iteration number.

        Args:
            node: The checkpoint node
            state: Current workflow state

        Returns:
            Current iteration number (1-indexed)
        """
        checkpoint_iterations = state.get("checkpoint_iterations", {})
        return checkpoint_iterations.get(node.uniq_id, 0) + 1

    def check_existing_checkpoint(
        self, node: EnhancedNodeData, state: WorkflowState, current_iteration: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check if we're resuming from an existing paused checkpoint.

        Args:
            node: The checkpoint node
            state: Current workflow state
            current_iteration: Current iteration number

        Returns:
            Existing checkpoint data if found, None otherwise
        """
        db_execution_id = state.get("db_execution_id")
        if not db_execution_id:
            return None

        try:
            node_execs = ExecutionHistoryService.get_node_executions(db_execution_id)
            for ne in node_execs:
                if (
                    ne.get("node_id") == node.uniq_id
                    and ne.get("node_type") == "CHECKPOINT"
                    and ne.get("status") == "paused"
                ):
                    checkpoint_logger.info(
                        f"Found existing paused checkpoint: node={node.name}, "
                        f"db_id={ne['id']}"
                    )
                    return ne
        except Exception as e:
            checkpoint_logger.debug(f"Error checking for existing checkpoint: {e}")

        return None

    def create_checkpoint_node_execution(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        input_message: str,
        current_iteration: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Create database record for checkpoint node execution.

        Args:
            node: The checkpoint node
            state: Current workflow state
            input_message: Input message
            current_iteration: Current iteration number
            metadata: Optional metadata to store

        Returns:
            Node execution ID if created, None otherwise
        """
        db_execution_id = state.get("db_execution_id")
        if not db_execution_id:
            return None

        try:
            current_order = StateExecutionTracker.get_execution_order(state)
            checkpoint_metadata = {
                "iteration": current_iteration,
                **(metadata or {}),
            }

            node_exec = ExecutionHistoryService.create_node_execution(
                graph_execution_id=db_execution_id,
                node_id=node.uniq_id,
                node_name=node.name,
                node_type="CHECKPOINT",
                execution_order=current_order,
                input_data={"message": input_message},
                node_metadata=checkpoint_metadata,
            )
            node_exec_id = node_exec["id"]
            ExecutionHistoryService.start_node_execution(node_exec_id)

            # Track for pause handling
            exec_id = state.get("execution_id")
            if exec_id in self.active_executions:
                self.active_executions[exec_id]["node_execution_map"][node.uniq_id] = (
                    node_exec_id
                )

            checkpoint_logger.info(
                f"Created checkpoint node execution: {node.name} (ID: {node_exec_id})"
            )
            return node_exec_id

        except Exception as e:
            checkpoint_logger.error(f"Failed to create checkpoint node execution: {e}")
            return None

    async def send_node_start_notification(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
    ):
        """
        Send WebSocket notification that checkpoint node started.

        Args:
            node: The checkpoint node
            state: Current workflow state
            node_exec_id: Database node execution ID
        """
        ws_execution_id = state.get("execution_id")
        if ws_notifier and ws_execution_id and node_exec_id:
            try:
                await ws_notifier.on_node_start(
                    ws_execution_id,
                    node.uniq_id,
                    node.name,
                    "CHECKPOINT",
                    False,
                    None,
                    node_exec_id,
                )
            except Exception as e:
                checkpoint_logger.error(f"Failed to send node start notification: {e}")

    async def send_node_paused_notification(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
    ):
        """
        Send WebSocket notification that checkpoint node paused.

        Args:
            node: The checkpoint node
            state: Current workflow state
            node_exec_id: Database node execution ID
        """
        ws_execution_id = state.get("execution_id")
        if ws_notifier and ws_execution_id and node_exec_id:
            try:
                await ws_notifier.on_node_paused(
                    ws_execution_id,
                    node.uniq_id,
                    node.name,
                    "CHECKPOINT",
                    node_exec_id,
                    False,
                    None,
                )
                checkpoint_logger.info(
                    f"Sent paused notification for checkpoint: {node.name}"
                )
            except Exception as e:
                checkpoint_logger.error(f"Failed to send paused notification: {e}")

    def complete_checkpoint_node(
        self,
        node_exec_id: Optional[int],
        output_data: Dict[str, Any],
    ):
        """
        Mark checkpoint node as completed in database.

        Args:
            node_exec_id: Database node execution ID
            output_data: Output data from checkpoint
        """
        if not node_exec_id:
            return

        try:
            ExecutionHistoryService.complete_node_execution(
                node_execution_id=node_exec_id,
                status="completed",
                output_data=output_data,
            )
            checkpoint_logger.info(
                f"Completed checkpoint node execution: {node_exec_id}"
            )
        except Exception as e:
            checkpoint_logger.error(
                f"Failed to complete checkpoint node execution: {e}"
            )

    async def send_completion_notification(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        output_data: Dict[str, Any],
        input_message: str,
        node_exec_id: Optional[int],
    ):
        """
        Send WebSocket notification that checkpoint completed.

        Args:
            node: The checkpoint node
            state: Current workflow state
            output_data: Output data from checkpoint
            input_message: Input message
            node_exec_id: Database node execution ID
        """
        ws_execution_id = state.get("execution_id")
        if ws_notifier and ws_execution_id:
            try:
                await ws_notifier.on_node_complete(
                    ws_execution_id,
                    node.uniq_id,
                    node.name,
                    output_data,
                    "CHECKPOINT",
                    None,
                    {"message": input_message},
                    None,
                    None,
                    None,
                    None,
                    None,
                    False,
                    None,
                    node_exec_id,
                )
            except Exception as e:
                checkpoint_logger.error(f"Failed to send completion notification: {e}")

    def build_checkpoint_result(
        self,
        answer: Any,
        state: WorkflowState,
        node: EnhancedNodeData,
        current_iteration: int,
        extra_result_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build standard checkpoint result dictionary.

        Args:
            answer: The answer/input from checkpoint resume
            state: Current workflow state
            node: The checkpoint node
            current_iteration: Current iteration number
            extra_result_data: Optional extra data for result

        Returns:
            State updates dictionary
        """
        import json

        from langchain_core.messages import HumanMessage

        # Convert answer to string
        answer_text = answer if isinstance(answer, str) else json.dumps(answer)

        # Update execution order
        current_order = StateExecutionTracker.get_execution_order(state)
        order_update = StateExecutionTracker.set_execution_order(
            state, current_order + 1
        )

        # Append to messages
        new_messages = list(state.get("messages", []))
        new_messages.append(HumanMessage(content=answer_text))

        # Update checkpoint iterations
        checkpoint_iterations = state.get("checkpoint_iterations", {})
        updated_iterations = {**checkpoint_iterations, node.uniq_id: current_iteration}

        # Build result
        result = {
            "node_output": {"raw": answer_text, "structured": None, "fields": {}},
            "messages": new_messages,
            "checkpoint_iterations": updated_iterations,
            **order_update,
        }

        # Add extra result data if provided
        if extra_result_data:
            result["result"] = {
                "node": node.name,
                "output": answer_text,
                **extra_result_data,
            }

        return result
