"""Checkpoint handling logic for paused executions."""

from typing import Any, Dict, List, Optional

from backend.models import NodeExecution
from backend.services.config import get_logger


# Get logger
logger = get_logger(__name__)


class CheckpointHandler:
    """
    Handler for checkpoint-related operations in paused executions.

    This class encapsulates the logic for retrieving and processing
    checkpoint information from both database records and the LangGraph
    execution engine.
    """

    def __init__(self, execution_engine: Any):
        """
        Initialize the checkpoint handler.

        Args:
            execution_engine: The LangGraph execution engine instance
        """
        self.execution_engine = execution_engine

    def get_checkpoint_info(
        self, checkpoint_node: NodeExecution, thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract checkpoint information from a checkpoint node.

        This method retrieves checkpoint details from both the node metadata
        and the LangGraph engine, preferring the LangGraph checkpoint ID when
        available.

        Args:
            checkpoint_node: The NodeExecution representing the checkpoint
            thread_id: Optional LangGraph thread ID for checkpoint lookup

        Returns:
            Dictionary with checkpoint details (node_id, node_name,
            checkpoint_id, prompt)
        """
        checkpoint_id = None
        is_manual = False

        # Try to get checkpoint_id from LangGraph first
        if thread_id:
            checkpoint_id = self._get_checkpoint_id_from_langgraph(thread_id)

        # Fall back to node_metadata if no checkpoint_id from LangGraph
        if not checkpoint_id and checkpoint_node.node_metadata:
            checkpoint_id = checkpoint_node.node_metadata.get("checkpoint_id")
            logger.debug(
                f"[CHECKPOINT-HANDLER] Using checkpoint_id from node_metadata: "
                f"{checkpoint_id}"
            )
            is_manual = checkpoint_node.node_metadata.get("manual_pause", False)

        # Extract prompt from metadata
        prompt = None
        if checkpoint_node.node_metadata:
            prompt = checkpoint_node.node_metadata.get("prompt")

        return {
            "node_id": checkpoint_node.node_id,
            "node_name": checkpoint_node.node_name,
            "checkpoint_id": checkpoint_id,
            "prompt": prompt,
            "manual": is_manual,
        }

    def get_checkpoint_info_for_resume(
        self,
        checkpoint_node: NodeExecution,
        previous_node: Optional[NodeExecution],
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get checkpoint information formatted for resuming an execution.

        This extends get_checkpoint_info with additional fields needed
        for resumption, including the previous node's output and a default
        prompt if none is specified.

        Args:
            checkpoint_node: The NodeExecution representing the checkpoint
            previous_node: The NodeExecution that ran before the checkpoint
            thread_id: Optional LangGraph thread ID for checkpoint lookup

        Returns:
            Dictionary with checkpoint details including previous_output
        """
        checkpoint_info = self.get_checkpoint_info(checkpoint_node, thread_id)

        # Add previous node's output
        checkpoint_info["previous_output"] = (
            previous_node.output_data if previous_node else None
        )

        # Ensure there's a prompt with a default if not specified
        if not checkpoint_info.get("prompt"):
            checkpoint_info["prompt"] = "Please review and provide input to continue."

        return checkpoint_info

    def can_resume_from_checkpoint(self, thread_id: Optional[str]) -> bool:
        """
        Check if an execution can be resumed from a checkpoint.

        Args:
            thread_id: The LangGraph thread ID

        Returns:
            True if a checkpoint exists and the execution can be resumed
        """
        if not thread_id:
            logger.debug("[CHECKPOINT-HANDLER] Cannot resume: no thread_id provided")
            return False

        try:
            if not hasattr(self.execution_engine, "get_checkpoints"):
                logger.warning(
                    "[CHECKPOINT-HANDLER] Execution engine does not support "
                    "get_checkpoints method"
                )
                return False

            checkpoints = self.execution_engine.get_checkpoints(thread_id)
            can_resume = len(checkpoints) > 0

            logger.debug(
                f"[CHECKPOINT-HANDLER] Checked resume capability for thread "
                f"{thread_id}: {can_resume} ({len(checkpoints)} checkpoints found)"
            )

            return can_resume

        except Exception as e:
            logger.warning(
                f"[CHECKPOINT-HANDLER] Could not check checkpoint availability "
                f"for thread {thread_id}: {e}"
            )
            return False

    def _get_checkpoint_id_from_langgraph(self, thread_id: str) -> Optional[str]:
        """
        Retrieve the most recent checkpoint ID from LangGraph.

        Args:
            thread_id: The LangGraph thread ID

        Returns:
            The checkpoint ID if found, None otherwise
        """
        try:
            if not hasattr(self.execution_engine, "get_checkpoints"):
                logger.debug(
                    "[CHECKPOINT-HANDLER] Execution engine does not support "
                    "get_checkpoints method"
                )
                return None

            checkpoints = self.execution_engine.get_checkpoints(thread_id)

            if checkpoints and len(checkpoints) > 0:
                # Get the most recent checkpoint (first in list)
                checkpoint_id = checkpoints[0].get("checkpoint_id")
                logger.debug(
                    f"[CHECKPOINT-HANDLER] Found checkpoint_id from LangGraph: "
                    f"{checkpoint_id}"
                )
                return checkpoint_id

            logger.debug(
                f"[CHECKPOINT-HANDLER] No checkpoints found in LangGraph "
                f"for thread {thread_id}"
            )
            return None

        except Exception as e:
            logger.warning(
                f"[CHECKPOINT-HANDLER] Could not get checkpoint_id from "
                f"LangGraph for thread {thread_id}: {e}"
            )
            return None

    def build_node_execution_details(
        self, node_executions: List[NodeExecution]
    ) -> List[Dict[str, Any]]:
        """
        Build detailed information for a list of node executions.

        Args:
            node_executions: List of NodeExecution database models

        Returns:
            List of dictionaries with detailed node execution information
        """
        nodes = []
        for node in node_executions:
            nodes.append(
                {
                    "id": node.id,
                    "node_id": node.node_id,
                    "node_name": node.node_name,
                    "node_type": node.node_type,
                    "status": node.status,
                    "execution_order": node.execution_order,
                    "start_time": node.start_time.isoformat()
                    if node.start_time
                    else None,
                    "end_time": node.end_time.isoformat() if node.end_time else None,
                    "duration_seconds": node.duration_seconds,
                    "input_data": node.input_data,
                    "output_data": node.output_data,
                    "error_message": node.error_message,
                    "is_sub_agent": node.is_sub_agent,
                    "parent_agent_id": node.parent_agent_id,
                    "total_tokens": node.total_tokens,
                }
            )

        logger.debug(
            f"[CHECKPOINT-HANDLER] Built details for {len(nodes)} node executions"
        )

        return nodes
