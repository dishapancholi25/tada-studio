"""
State extraction utilities for subworkflow resumption.

This module handles extracting and formatting results from completed
subworkflow executions.
"""

from typing import Any, Dict, Optional

from .utils import log_info


def extract_subworkflow_result(
    final_state: Optional[Dict[str, Any]], chunk_count: int
) -> Dict[str, Any]:
    """
    Extract the result from a completed subworkflow execution.

    Args:
        final_state: The final state from the subworkflow
        chunk_count: Number of chunks processed during execution

    Returns:
        A dictionary containing the workflow output and metadata
    """
    workflow_output = ""
    if final_state:
        workflow_output = final_state.get("workflow_output", "")

    result = {
        "workflow_output": workflow_output,
        "completed": True,
        "chunks_processed": chunk_count,
    }

    log_info(f"Extracted subworkflow result: {result}")
    return result


def extract_parent_completion_info(
    checkpoint_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Extract parent workflow completion information from checkpoint metadata.

    Args:
        checkpoint_metadata: Metadata about the checkpoint

    Returns:
        Dictionary containing tool call ID and other parent info
    """
    parent_tool_call = checkpoint_metadata.get("parent_tool_call", {})
    tool_call_id = parent_tool_call.get("id")

    return {
        "tool_call_id": tool_call_id,
        "parent_tool_call": parent_tool_call,
    }


def format_parent_completion_result(
    subworkflow_result: Dict[str, Any], tool_call_id: Optional[str]
) -> Dict[str, Any]:
    """
    Format the completion result for the parent workflow.

    Args:
        subworkflow_result: The result from the subworkflow
        tool_call_id: The tool call ID that should receive the result

    Returns:
        Formatted completion result
    """
    return {
        "status": "completed",
        "subworkflow_result": subworkflow_result,
        "tool_call_id": tool_call_id,
    }
