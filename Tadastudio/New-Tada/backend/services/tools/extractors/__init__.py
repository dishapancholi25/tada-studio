"""
Tool execution data extractors.

This package provides a modular system for extracting input and output
data from tool executions. Different tools store their data in different
formats, and this system standardizes the extraction process.

Main Functions:
    extract_tool_input: Extract input data from a tool execution
    extract_tool_output: Extract output data from a tool execution

Example:
    from backend.services.tools.extractors import (
        extract_tool_input,
        extract_tool_output
    )

    # Extract data from a tool execution
    tool_exec = {"tool": "search_web", "kwargs": {"query": "python"}}
    input_data = extract_tool_input("search_web", tool_exec)
    output_data = extract_tool_output(tool_exec)
"""

import logging
from typing import Any, Dict

from ..extraction_models import (
    HttpRequestMetadata,
    ToolExecutionData,
    ToolInputData,
    ToolOutputData,
)
from .base import BaseExtractor, ExtractionError, ValidationMixin
from .fallback import FallbackExtractor
from .http_request import HttpRequestExtractor
from .query_based import QueryBasedExtractor
from .registry import ExtractorRegistry, get_registry, reset_registry
from .structured import StructuredToolExtractor


logger = logging.getLogger(__name__)


def extract_tool_input(tool_name: str, tool_exec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract input data from a tool execution based on the tool name.

    This is the main entry point for extracting tool input data.
    It uses the extractor registry to find the appropriate extractor
    for the given tool name and delegates the extraction.

    Args:
        tool_name: The name of the tool being executed
        tool_exec: The tool execution data dictionary

    Returns:
        A dictionary containing the extracted input data

    Raises:
        ExtractionError: If extraction fails critically

    Example:
        >>> tool_exec = {"kwargs": {"query": "test"}}
        >>> extract_tool_input("search_web", tool_exec)
        {"query": "test"}
    """
    try:
        # Get the registry and appropriate extractor
        registry = get_registry()
        extractor = registry.get_extractor(tool_name)

        # Log the extraction attempt
        logger.debug(
            f"[TOOL-EXTRACTOR] Extracting input for '{tool_name}' using {extractor.name}"
        )

        # Extract and return input data
        input_data = extractor.extract_input(tool_exec)  # type: ignore

        logger.debug(
            f"[TOOL-EXTRACTOR] Successfully extracted input with {len(input_data)} fields"
        )

        return input_data

    except ExtractionError as e:
        # Log the error but don't raise - return empty dict as fallback
        logger.error(
            f"[TOOL-EXTRACTOR] Extraction error for '{tool_name}': {e.message}"
        )
        if e.original_error:
            logger.error(f"[TOOL-EXTRACTOR] Original error: {str(e.original_error)}")
        # Return empty dict as safe fallback
        return {}
    except Exception as e:
        # Unexpected error - log and return empty dict
        logger.error(
            f"[TOOL-EXTRACTOR] Unexpected error extracting input for '{tool_name}': {str(e)}",
            exc_info=True,
        )
        return {}


def extract_tool_output(tool_exec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract output data from a tool execution.

    This function extracts output data from a tool execution.
    For most tools, it uses the standard output extraction logic.
    For HTTP tools, it may return the full metadata structure.

    Args:
        tool_exec: The tool execution data dictionary

    Returns:
        A dictionary containing the extracted output data

    Raises:
        ExtractionError: If extraction fails critically

    Example:
        >>> tool_exec = {"output": "result", "execution_time": 1.5}
        >>> extract_tool_output(tool_exec)
        {"result": "result", "execution_time": 1.5, ...}
    """
    try:
        # Get tool name to determine extractor
        tool_name = tool_exec.get("tool", "")

        # Get the registry and appropriate extractor
        registry = get_registry()
        extractor = registry.get_extractor(tool_name)

        # Log the extraction attempt
        logger.debug(
            f"[TOOL-EXTRACTOR] Extracting output for '{tool_name}' using {extractor.name}"
        )

        # Extract and return output data
        output_data = extractor.extract_output(tool_exec)  # type: ignore

        logger.debug(
            f"[TOOL-EXTRACTOR] Successfully extracted output with {len(output_data)} fields"
        )

        return output_data

    except ExtractionError as e:
        # Log the error but don't raise - return minimal data as fallback
        logger.error(f"[TOOL-EXTRACTOR] Extraction error: {e.message}")
        if e.original_error:
            logger.error(f"[TOOL-EXTRACTOR] Original error: {str(e.original_error)}")
        # Return minimal output structure as safe fallback
        return {
            "result": tool_exec.get("output", tool_exec.get("result", "")),
            "execution_time": tool_exec.get("execution_time", 0),
            "tool_call_id": tool_exec.get("call_id", ""),
            "timestamp": tool_exec.get("timestamp", ""),
        }
    except Exception as e:
        # Unexpected error - log and return minimal data
        logger.error(
            f"[TOOL-EXTRACTOR] Unexpected error extracting output: {str(e)}",
            exc_info=True,
        )
        return {
            "result": tool_exec.get("output", tool_exec.get("result", "")),
            "execution_time": 0,
            "tool_call_id": "",
            "timestamp": "",
        }


# Public API
__all__ = [
    # Main extraction functions
    "extract_tool_input",
    "extract_tool_output",
    # Base classes
    "BaseExtractor",
    "ExtractionError",
    "ValidationMixin",
    # Extractor implementations
    "StructuredToolExtractor",
    "QueryBasedExtractor",
    "HttpRequestExtractor",
    "FallbackExtractor",
    # Registry
    "ExtractorRegistry",
    "get_registry",
    "reset_registry",
    # Type definitions
    "ToolExecutionData",
    "ToolInputData",
    "ToolOutputData",
    "HttpRequestMetadata",
]
