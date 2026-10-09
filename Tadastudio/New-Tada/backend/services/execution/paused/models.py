"""Internal data models for paused execution service."""

from typing import Any, Dict, Optional


class PausedExecutionSummary:
    """
    Internal model for summarizing a paused execution.

    This class aggregates data from a GraphExecution and its associated
    checkpoint NodeExecution to provide a convenient summary view.

    Args:
        execution: The GraphExecution database model
        checkpoint_node: Optional NodeExecution representing the checkpoint

    Attributes:
        execution_id: Database ID of the execution
        thread_id: LangGraph thread ID
        websocket_execution_id: WebSocket connection identifier
        graph_name: Name of the workflow/graph
        paused_at: Timestamp when execution was paused
        checkpoint: Dictionary with checkpoint details (node_id, name, etc.)
        progress: Dictionary with completion statistics
    """

    def __init__(
        self,
        execution: Any,  # GraphExecution model
        checkpoint_node: Optional[Any] = None,  # NodeExecution model
    ):
        """
        Initialize a paused execution summary.

        Args:
            execution: GraphExecution database model instance
            checkpoint_node: Optional NodeExecution for the checkpoint node
        """
        self.execution_id = execution.id
        self.thread_id = execution.thread_id
        self.websocket_execution_id = execution.websocket_execution_id
        self.graph_name = execution.graph_name
        self.paused_at = (
            checkpoint_node.start_time if checkpoint_node else execution.created_at
        )
        self.checkpoint = None

        if checkpoint_node:
            self.checkpoint = self._build_checkpoint_info(checkpoint_node)

        self.progress = self._calculate_progress(execution)

    def _build_checkpoint_info(self, checkpoint_node: Any) -> Dict[str, Any]:
        """
        Build checkpoint information dictionary from checkpoint node.

        Args:
            checkpoint_node: NodeExecution representing the checkpoint

        Returns:
            Dictionary with checkpoint details
        """
        checkpoint_id = None
        checkpoint_type = "checkpoint"  # Default type
        review_payload = None

        if checkpoint_node.node_metadata:
            checkpoint_id = checkpoint_node.node_metadata.get("checkpoint_id")
            prompt = checkpoint_node.node_metadata.get("prompt")

            # Check if this is an agent review checkpoint
            if isinstance(prompt, dict) and prompt.get("type") == "agent_review":
                checkpoint_type = "agent_review"
                review_payload = prompt

        result = {
            "node_id": checkpoint_node.node_id,
            "node_name": checkpoint_node.node_name,
            "checkpoint_id": checkpoint_id,
            "last_input": checkpoint_node.input_data,
            "type": checkpoint_type,
        }

        # Include review_payload only for agent reviews
        if review_payload:
            result["review_payload"] = review_payload

        return result

    def _calculate_progress(self, execution: Any) -> Dict[str, Any]:
        """
        Calculate execution progress metrics.

        Args:
            execution: GraphExecution database model instance

        Returns:
            Dictionary with completed_nodes, total_nodes, and percentage
        """
        total_nodes = 0
        if execution.graph_definition:
            nodes = execution.graph_definition.get("nodes", [])
            total_nodes = len(nodes)

        completed_nodes = sum(
            1 for n in execution.node_executions if n.status == "completed"
        )

        percentage = 0.0
        if total_nodes > 0:
            percentage = round((completed_nodes / total_nodes * 100), 1)

        return {
            "completed_nodes": completed_nodes,
            "total_nodes": total_nodes,
            "percentage": percentage,
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the summary to a dictionary for API responses.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "execution_id": self.execution_id,
            "thread_id": self.thread_id,
            "websocket_execution_id": self.websocket_execution_id,
            "graph_name": self.graph_name,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "checkpoint": self.checkpoint,
            "progress": self.progress,
        }
