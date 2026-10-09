"""
Response content extraction utilities.

This module provides functions to extract content from various response types
(AIMessage, BaseMessage, dict, str) in a consistent way.
"""

from typing import Any, List

from langchain_core.messages import AIMessage
from backend.services.config import get_logger


extractor_logger = get_logger("common.response_extractor")


def extract_response_content(
    response: Any,
    agent_name: str,
    tool_execution_tracker: List[dict],
) -> str:
    """
    Extract text content from a response object.

    Handles different response types (AIMessage, objects with content attribute,
    strings) and provides fallback logic if the response is empty.

    Args:
        response: The response object from agent execution
        agent_name: Name of the agent (for logging)
        tool_execution_tracker: List of tool executions (for fallback)

    Returns:
        The extracted response content as a string

    Raises:
        ValueError: If response cannot be extracted and no fallback is available
    """
    response_content = None

    # Try to extract content based on response type
    if isinstance(response, AIMessage):
        response_content = response.content
        extractor_logger.info(f"Agent {agent_name} response type: AIMessage")
        extractor_logger.debug(
            f"Response content (first 200 chars): {response_content[:200] if response_content else 'EMPTY'}"
        )

        # Check for unprocessed tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            extractor_logger.warning(
                f"Agent {agent_name} has {len(response.tool_calls)} unprocessed tool calls"
            )
            if not response_content:
                response_content = (
                    "Agent made tool calls but did not provide a final response."
                )

    elif hasattr(response, "content"):
        response_content = response.content
        extractor_logger.info(
            f"Agent {agent_name} response type: {type(response).__name__} with content attribute"
        )
        extractor_logger.debug(
            f"Response content (first 200 chars): {response_content[:200] if response_content else 'EMPTY'}"
        )

    else:
        response_content = str(response)
        extractor_logger.warning(
            f"Agent {agent_name} unexpected response type: {type(response).__name__}"
        )
        extractor_logger.debug(
            f"Stringified response (first 200 chars): {response_content[:200]}"
        )

    # Check if response is empty and try fallbacks
    if not response_content or response_content.strip() == "":
        extractor_logger.error(f"Agent {agent_name} returned empty response!")

        # Try to use tool execution results as fallback
        if tool_execution_tracker:
            response_content = _extract_from_tool_results(
                tool_execution_tracker, agent_name
            )

        # Final fallback
        if not response_content or response_content.strip() == "":
            response_content = (
                "I was unable to complete the task. Please check the logs for details."
            )
            extractor_logger.error(f"Agent {agent_name}: Using default error message")

    return response_content


def _extract_from_tool_results(
    tool_execution_tracker: List[dict], agent_name: str
) -> str:
    """
    Extract response content from tool execution results.

    Used as a fallback when the agent response is empty but tools were executed.

    Args:
        tool_execution_tracker: List of tool executions
        agent_name: Name of the agent (for logging)

    Returns:
        A response constructed from tool results, or empty string if no results
    """
    extractor_logger.info(
        f"Tool executions found for {agent_name}: {len(tool_execution_tracker)}"
    )

    tool_results = []
    for exec_data in tool_execution_tracker:
        # Tool results may be in 'result', 'results', or 'output'
        if "result" in exec_data:
            tool_results.append(exec_data["result"])
        elif "results" in exec_data:
            tool_results.append(exec_data["results"])
        elif "output" in exec_data:
            tool_results.append(exec_data["output"])
        elif "error" in exec_data:
            tool_results.append(f"Tool error: {exec_data['error']}")

    if tool_results:
        response_content = (
            f"Based on my research: {' '.join(str(r) for r in tool_results)}"
        )
        extractor_logger.info(
            f"Using tool results as response: {response_content[:200]}"
        )
        return response_content

    return ""
