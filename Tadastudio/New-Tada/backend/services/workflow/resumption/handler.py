"""
Subworkflow Resume Handler.

This module handles the special case of resuming from subworkflow checkpoints.
When a subworkflow has a checkpoint, we need to:
1. Resume the subworkflow to completion
2. Get the subworkflow result
3. Continue the parent workflow with that result
"""

from typing import Any, Dict

from .checkpoint_loader import CheckpointLoader
from .state_extractor import (
    extract_parent_completion_info,
    extract_subworkflow_result,
    format_parent_completion_result,
)
from .subworkflow_executor import SubworkflowExecutor
from .utils import log_error, log_info, log_section_header
from .utils import parse_parent_graph_name
from backend.services.execution.checkpointer_manager import get_thread_checkpointer


class SubworkflowResumeHandler:
    """Handles resumption of subworkflow checkpoints."""

    def __init__(self, execution_engine, graph_manager):
        """
        Initialize the handler.

        Args:
            execution_engine: The LangGraph execution engine
            graph_manager: The graph manager for accessing graphs
        """
        self.execution_engine = execution_engine
        self.graph_manager = graph_manager
        self.checkpoint_loader = CheckpointLoader(graph_manager)
        self.subworkflow_executor = SubworkflowExecutor(graph_manager)
        log_info("Initialized SubworkflowResumeHandler")

    async def resume_subworkflow_checkpoint(
        self,
        parent_thread_id: str,
        subworkflow_thread_id: str,
        subworkflow_name: str,
        checkpoint_id: str,
        new_input: Any,
        checkpoint_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Resume a subworkflow from a checkpoint and get its result.

        This function:
        1. Resumes the subworkflow using its own thread ID
        2. Waits for the subworkflow to complete
        3. Returns the subworkflow result

        Args:
            parent_thread_id: The parent workflow's thread ID
            subworkflow_thread_id: The subworkflow's thread ID
            subworkflow_name: Name of the subworkflow
            checkpoint_id: The checkpoint ID to resume from
            new_input: The input to resume with
            checkpoint_metadata: Metadata about the checkpoint

        Returns:
            The subworkflow result
        """
        log_section_header("RESUMING SUBWORKFLOW")
        log_info(
            "Starting subworkflow resumption",
            subworkflow=subworkflow_name,
            subworkflow_thread=subworkflow_thread_id,
            parent_thread=parent_thread_id,
            checkpoint_id=checkpoint_id,
        )

        try:
            # Load parent graph and find subworkflow node
            parent_graph = self.checkpoint_loader.load_parent_graph(parent_thread_id)
            if not parent_graph:
                return {"error": "Could not load parent graph"}

            subworkflow_node = self.checkpoint_loader.find_subworkflow_node(
                parent_graph, subworkflow_name
            )
            if not subworkflow_node:
                return {"error": "Could not find subworkflow node"}

            # Build the subworkflow app

            parent_graph_name = parse_parent_graph_name(parent_thread_id)
            subworkflow_app = self.subworkflow_executor.build_subworkflow_app(
                subworkflow_node=subworkflow_node,
                parent_graph_name=parent_graph_name,
                checkpointer=get_thread_checkpointer(),
            )

            # Execute the subworkflow
            (
                final_state,
                chunk_count,
            ) = await self.subworkflow_executor.execute_subworkflow(
                subworkflow_app=subworkflow_app,
                subworkflow_thread_id=subworkflow_thread_id,
                checkpoint_id=checkpoint_id,
                new_input=new_input,
            )

            # Extract and return the result
            result = extract_subworkflow_result(final_state, chunk_count)
            log_section_header("SUBWORKFLOW RESUMPTION COMPLETE")
            return result

        except Exception as e:
            log_error(f"Error resuming subworkflow: {e}", exc=e)
            return {"error": str(e), "completed": False}

    @staticmethod
    async def complete_parent_workflow(
        parent_thread_id: str,
        subworkflow_result: Dict[str, Any],
        checkpoint_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Complete the parent workflow with the subworkflow result.

        This updates the parent workflow's state with the subworkflow result
        so the agent can continue with the actual result.

        Args:
            parent_thread_id: The parent workflow's thread ID
            subworkflow_result: The result from the subworkflow
            checkpoint_metadata: Metadata about the checkpoint

        Returns:
            The parent workflow completion result
        """
        log_section_header("COMPLETING PARENT WORKFLOW")
        log_info(
            "Completing parent workflow",
            parent_thread=parent_thread_id,
            subworkflow_result=subworkflow_result,
        )

        try:
            # Extract parent completion information
            parent_info = extract_parent_completion_info(checkpoint_metadata)
            tool_call_id = parent_info["tool_call_id"]

            if not tool_call_id:
                log_info("No tool call ID found in metadata")
                return {"error": "No tool call ID found"}

            # Log what should happen (actual implementation would modify checkpoint state)
            log_info(
                f"Tool call {tool_call_id} should receive result: "
                f"{subworkflow_result.get('workflow_output')}"
            )
            log_info("Parent agent should then generate final response")

            result = format_parent_completion_result(subworkflow_result, tool_call_id)
            log_section_header("PARENT WORKFLOW COMPLETION DONE")
            return result

        except Exception as e:
            log_error(f"Error completing parent workflow: {e}", exc=e)
            return {"error": str(e)}
