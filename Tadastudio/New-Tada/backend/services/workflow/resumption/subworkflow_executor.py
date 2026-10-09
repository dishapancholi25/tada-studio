"""
Subworkflow execution utilities for checkpoint resumption.

This module handles building and executing subworkflow applications
from checkpoints.
"""

from typing import Any, Dict, Optional, Tuple

from langgraph.types import Command

from .utils import DEFAULT_RECURSION_LIMIT, log_error, log_info


class SubworkflowExecutor:
    """Handles building and executing subworkflows."""

    def __init__(self, graph_manager):
        """
        Initialize the subworkflow executor.

        Args:
            graph_manager: The graph manager for accessing graphs
        """
        self.graph_manager = graph_manager

    def build_subworkflow_app(
        self,
        subworkflow_node: Any,
        parent_graph_name: str,
        checkpointer: Any,
    ) -> Any:
        """
        Build a subworkflow application from a node.

        Args:
            subworkflow_node: The subworkflow node configuration
            parent_graph_name: Name of the parent graph
            checkpointer: The checkpoint saver instance

        Returns:
            The compiled subworkflow application
        """
        from backend.services.subgraph import SubgraphBuilder

        log_info(f"Building subworkflow app: {subworkflow_node.name}")

        builder = SubgraphBuilder(self.graph_manager)
        subworkflow_app = builder.create_subworkflow_graph(
            subworkflow_node=subworkflow_node,
            graph_name=parent_graph_name,
            checkpointer=checkpointer,
        )

        log_info("Subworkflow app built successfully")
        return subworkflow_app

    async def execute_subworkflow(
        self,
        subworkflow_app: Any,
        subworkflow_thread_id: str,
        checkpoint_id: str,
        new_input: Any,
    ) -> Tuple[Optional[Dict[str, Any]], int]:
        """
        Execute a subworkflow from a checkpoint.

        Args:
            subworkflow_app: The compiled subworkflow application
            subworkflow_thread_id: The subworkflow's thread ID
            checkpoint_id: The checkpoint ID to resume from
            new_input: The input to resume with

        Returns:
            A tuple of (final_state, chunk_count)
        """
        resume_config = {
            "configurable": {
                "thread_id": subworkflow_thread_id,
                "checkpoint_id": checkpoint_id,
            },
            "recursion_limit": DEFAULT_RECURSION_LIMIT,
        }

        log_info(f"Executing subworkflow with config: {resume_config}")

        final_state = None
        chunk_count = 0

        try:
            async for chunk in subworkflow_app.astream(
                Command(resume=new_input), config=resume_config
            ):
                chunk_count += 1
                log_info(f"Subworkflow chunk {chunk_count}: {list(chunk.keys())}")

                # Check for completion
                if self._is_end_chunk(chunk):
                    log_info("Subworkflow reached END")
                    final_state = chunk
                    break

                # Update state
                final_state = self._update_state(final_state, chunk)

            log_info(f"Subworkflow completed after {chunk_count} chunks")
            return final_state, chunk_count

        except Exception as e:
            log_error(f"Error executing subworkflow: {e}", exc=e)
            raise

    def _is_end_chunk(self, chunk: Dict[str, Any]) -> bool:
        """
        Check if a chunk represents the end of execution.

        Args:
            chunk: The chunk to check

        Returns:
            True if this is an end chunk
        """
        return any(key.endswith("END") or key == "__end__" for key in chunk.keys())

    def _update_state(
        self, current_state: Optional[Dict[str, Any]], chunk: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update the current state with a new chunk.

        Args:
            current_state: The current state (may be None)
            chunk: The new chunk to merge

        Returns:
            The updated state
        """
        if current_state is None:
            current_state = {}

        for key, value in chunk.items():
            if isinstance(value, dict):
                current_state.update(value)

        return current_state
