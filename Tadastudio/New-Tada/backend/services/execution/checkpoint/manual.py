"""
Manual Checkpoint Executor.

This module handles manual checkpoint nodes that pause execution and wait
for human input via the interrupt mechanism. The user provides input through
the API or UI, which then resumes execution.
"""

from typing import TYPE_CHECKING, Any, Dict

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

from .base import CheckpointExecutor

if TYPE_CHECKING:
    from backend.models import GraphData

manual_checkpoint_logger = get_logger("execution.checkpoint.manual")


class ManualCheckpointExecutor(CheckpointExecutor):
    """
    Executes manual checkpoint nodes that pause for human input.

    Manual checkpoints use LangGraph's interrupt() mechanism to pause
    execution. The workflow waits until the user provides input via
    the resume API endpoint.

    Example flow:
        1. Workflow reaches checkpoint node
        2. Checkpoint calls interrupt() with prompt
        3. Execution pauses, returns to API caller
        4. User provides input via /resume endpoint
        5. Execution continues with user input
    """

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
        input_message: str,
    ) -> Dict[str, Any]:
        """
        Execute manual checkpoint node.

        Args:
            node: The checkpoint node to execute
            state: Current workflow state
            graph: The graph definition
            input_message: Input message for the checkpoint prompt

        Returns:
            State updates dictionary with user input
        """
        manual_checkpoint_logger.info(f"Executing manual checkpoint: {node.name}")

        # Extract checkpoint configuration
        prompt_text = self._get_prompt_text(node)
        manual_checkpoint_logger.info(f"Checkpoint prompt: {prompt_text}")

        # Get current iteration (for loop support)
        current_iteration = self.get_current_iteration(node, state)

        # Check if resuming from existing paused checkpoint
        existing_checkpoint = self.check_existing_checkpoint(
            node, state, current_iteration
        )
        is_resuming = existing_checkpoint is not None

        if is_resuming:
            manual_checkpoint_logger.info(
                f"Resuming existing checkpoint: {node.name}, "
                f"iteration {current_iteration}"
            )
            node_exec_id = existing_checkpoint.get("id")
        else:
            manual_checkpoint_logger.info(
                f"New checkpoint execution: {node.name}, iteration {current_iteration}"
            )
            # Create new checkpoint node execution in database
            node_exec_id = self.create_checkpoint_node_execution(
                node, state, input_message, current_iteration
            )

        # Send WebSocket notifications
        if node_exec_id:
            # Notify that checkpoint node started (if not resuming)
            if not is_resuming:
                await self.send_node_start_notification(node, state, node_exec_id)

        # Send paused notification (skip if resuming - already paused)
        if not is_resuming and node_exec_id:
            await self.send_node_paused_notification(node, state, node_exec_id)

        # Use LangGraph's interrupt to pause execution
        from langgraph.types import interrupt

        answer = interrupt(
            {
                "type": "checkpoint",
                "prompt": prompt_text,
                "node_id": node.uniq_id,
                "node_name": node.name,
            }
        )

        # On resume, complete the checkpoint node
        manual_checkpoint_logger.info(f"Checkpoint resumed with answer: {answer}")

        # Complete node execution in database
        if node_exec_id:
            self.complete_checkpoint_node(
                node_exec_id,
                {"user_input": answer},
            )

            # Send completion notification
            await self.send_completion_notification(
                node, state, {"user_input": answer}, input_message, node_exec_id
            )

        # Build and return result
        return self.build_checkpoint_result(answer, state, node, current_iteration)

    def _get_prompt_text(self, node: EnhancedNodeData) -> str:
        """
        Extract prompt text from checkpoint configuration.

        Args:
            node: The checkpoint node

        Returns:
            Prompt text to display to user
        """
        default_prompt = "Please review and provide input to continue."

        if hasattr(node, "checkpoint_config") and node.checkpoint_config:
            return node.checkpoint_config.prompt or default_prompt

        return default_prompt
