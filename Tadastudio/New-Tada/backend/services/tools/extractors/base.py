"""
Base extractor interface for tool execution data.

This module provides the abstract base class for tool input/output extractors,
along with validation utilities and error handling.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..extraction_models import ToolExecutionData, ToolInputData, ToolOutputData


logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """
    Exception raised when tool data extraction fails.

    Attributes:
        message: Error description
        tool_name: Name of the tool being extracted
        extractor: Name of the extractor that failed
        original_error: Original exception if any
    """

    def __init__(
        self,
        message: str,
        tool_name: str = "",
        extractor: str = "",
        original_error: Exception = None,
    ):
        """Initialize extraction error."""
        self.message = message
        self.tool_name = tool_name
        self.extractor = extractor
        self.original_error = original_error
        super().__init__(self.message)


class BaseExtractor(ABC):
    """
    Abstract base class for tool execution data extractors.

    Extractors are responsible for extracting input and output data
    from tool execution dictionaries. Different tools store their data
    in different formats, so specialized extractors handle each format.

    Attributes:
        name: Human-readable name of this extractor
    """

    def __init__(self, name: str):
        """
        Initialize the base extractor.

        Args:
            name: Human-readable name for this extractor
        """
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def extract_input(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """
        Extract input data from a tool execution.

        Args:
            tool_exec: Tool execution data dictionary

        Returns:
            Extracted input data

        Raises:
            ExtractionError: If extraction fails
        """
        pass

    def extract_output(self, tool_exec: ToolExecutionData) -> ToolOutputData:
        """
        Extract output data from a tool execution.

        This default implementation works for most tools. Subclasses
        can override for specialized output extraction.

        Args:
            tool_exec: Tool execution data dictionary

        Returns:
            Extracted output data

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            self.logger.debug(f"[TOOL-EXTRACTOR] Extracting output with {self.name}")

            # Build output data with common fields
            output_data: ToolOutputData = {
                "result": tool_exec.get(
                    "results", tool_exec.get("output", tool_exec.get("response", ""))
                ),
                "execution_time": tool_exec.get("execution_time", 0),
                "tool_call_id": tool_exec.get("call_id", ""),
                "timestamp": tool_exec.get("timestamp", ""),
            }

            # Add optional provider-specific data
            if "provider" in tool_exec:
                output_data["provider"] = tool_exec["provider"]
            if "formatted_results" in tool_exec:
                output_data["formatted_results"] = tool_exec["formatted_results"]
            if "formatted_output" in tool_exec:
                output_data["formatted_output"] = tool_exec["formatted_output"]
            if "status_code" in tool_exec:
                output_data["status_code"] = tool_exec["status_code"]

            return output_data

        except Exception as e:
            raise ExtractionError(
                message=f"Failed to extract output data: {str(e)}",
                extractor=self.name,
                original_error=e,
            )

    def validate_tool_exec(self, tool_exec: ToolExecutionData) -> bool:
        """
        Validate that tool execution data has minimum required fields.

        Args:
            tool_exec: Tool execution data to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(tool_exec, dict):
            self.logger.warning("[TOOL-EXTRACTOR] Invalid tool_exec: not a dictionary")
            return False

        # At minimum, we need some data in the dictionary
        if not tool_exec:
            self.logger.warning("[TOOL-EXTRACTOR] Invalid tool_exec: empty dictionary")
            return False

        return True

    def safe_get(
        self, tool_exec: ToolExecutionData, key: str, default: Any = None
    ) -> Any:
        """
        Safely get a value from tool execution data with logging.

        Args:
            tool_exec: Tool execution data
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            Value from tool_exec or default
        """
        value = tool_exec.get(key, default)
        if value is None and default is None:
            self.logger.debug(
                f"[TOOL-EXTRACTOR] Key '{key}' not found in tool execution data"
            )
        return value


class ValidationMixin:
    """
    Mixin providing common validation methods for extractors.

    This mixin can be used by extractor classes to add validation
    capabilities for common data types and structures.
    """

    @staticmethod
    def is_valid_query(query: Any) -> bool:
        """
        Check if a query value is valid.

        Args:
            query: Query value to validate

        Returns:
            True if query is a non-empty string
        """
        return isinstance(query, str) and len(query.strip()) > 0

    @staticmethod
    def is_valid_http_request(request_data: Any) -> bool:
        """
        Check if HTTP request data is valid.

        Args:
            request_data: Request data to validate

        Returns:
            True if request data contains required fields
        """
        if not isinstance(request_data, dict):
            return False

        # At minimum, we should have a URL or method
        return "url" in request_data or "method" in request_data

    @staticmethod
    def extract_nested_value(
        data: Dict[str, Any], *keys: str, default: Any = None
    ) -> Any:
        """
        Extract a value from nested dictionary structure.

        Args:
            data: Dictionary to search
            *keys: Sequence of keys to traverse
            default: Default value if path not found

        Returns:
            Value at the nested path or default

        Example:
            extract_nested_value(data, "kwargs", "query") -> data["kwargs"]["query"]
        """
        current = data
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current
