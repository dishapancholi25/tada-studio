"""
HTTP request tool extractor for HTTP/API request tools.

This extractor handles HTTP request tools with their specific
request/response format and metadata structure.
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


logger = logging.getLogger(__name__)


class HttpRequestExtractor(BaseExtractor, ValidationMixin):
    """
    Extractor for HTTP request tools.

    Tools handled:
        - http_request
        - API request tools

    Input formats supported:
        1. Full metadata format with "request" field
        2. Legacy "parameters" field
        3. Legacy "request" field without metadata
        4. HTTP fields in kwargs (url, method, headers, body, etc.)

    Output format:
        Returns full HTTP metadata structure with request/response
        or standard output format for legacy data.
    """

    def __init__(self):
        """Initialize the HTTP request extractor."""
        super().__init__(name="HttpRequestExtractor")

    def extract_input(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """
        Extract input from HTTP request tools.

        Supports multiple input formats for backward compatibility.

        Args:
            tool_exec: Tool execution data

        Returns:
            Extracted HTTP request input data

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            if not self.validate_tool_exec(tool_exec):
                raise ExtractionError(
                    message="Invalid tool execution data",
                    extractor=self.name,
                )

            self.logger.debug("[TOOL-EXTRACTOR] Extracting HTTP request input")

            # Try different extraction strategies
            result = self._extract_metadata_format(tool_exec)
            if result:
                return result

            result = self._extract_legacy_formats(tool_exec)
            if result:
                return result

            result = self._extract_from_kwargs(tool_exec)
            if result:
                return result

            # Last resort: empty dict
            self.logger.warning("[TOOL-EXTRACTOR] No HTTP request data found")
            return {}

        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Failed to extract HTTP request input: {str(e)}",
                extractor=self.name,
                original_error=e,
            )

    def _extract_metadata_format(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """Extract from full HTTP metadata structure."""
        if tool_exec.get("tool") == "http_request" and "request" in tool_exec:
            request_data = tool_exec["request"]
            self.logger.debug("[TOOL-EXTRACTOR] Found full HTTP metadata structure")
            if self.is_valid_http_request(request_data):
                return request_data  # type: ignore
        return {}

    def _extract_legacy_formats(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """Extract from legacy parameter or request fields."""
        # Legacy "parameters" field
        if "parameters" in tool_exec:
            self.logger.debug("[TOOL-EXTRACTOR] Found legacy 'parameters' field")
            return {"parameters": tool_exec["parameters"]}

        # Direct "request" field (without full metadata)
        if "request" in tool_exec:
            request_data = tool_exec["request"]
            self.logger.debug("[TOOL-EXTRACTOR] Found direct 'request' field")
            if isinstance(request_data, dict):
                return {"request": request_data}

        return {}

    def _extract_from_kwargs(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """Extract HTTP-specific fields from kwargs."""
        kwargs = self.safe_get(tool_exec, "kwargs", {})
        if not isinstance(kwargs, dict):
            return {}

        # Extract HTTP-specific fields
        http_fields = ["url", "method", "headers", "body", "params", "query_params"]
        request_data: Dict[str, Any] = {}

        for field in http_fields:
            if field in kwargs:
                request_data[field] = kwargs[field]

        if request_data:
            self.logger.debug(
                f"[TOOL-EXTRACTOR] Extracted {len(request_data)} HTTP fields from kwargs"
            )
            return request_data  # type: ignore

        # If no HTTP-specific fields, return all kwargs
        if kwargs:
            self.logger.debug(
                "[TOOL-EXTRACTOR] No HTTP fields found, returning all kwargs"
            )
            return kwargs  # type: ignore

        return {}

    def extract_output(self, tool_exec: ToolExecutionData) -> ToolOutputData:
        """
        Extract output from HTTP request tools.

        Returns full HTTP metadata for tools in the new format,
        or falls back to standard output extraction.

        Args:
            tool_exec: Tool execution data

        Returns:
            Extracted HTTP response data or standard output

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            self.logger.debug("[TOOL-EXTRACTOR] Extracting HTTP request output")

            # Check for full HTTP metadata structure
            if (
                tool_exec.get("tool") == "http_request"
                and "request" in tool_exec
                and "response" in tool_exec
            ):
                self.logger.debug(
                    "[TOOL-EXTRACTOR] Returning full HTTP metadata structure"
                )

                # Return the complete HTTP metadata structure
                http_metadata: HttpRequestMetadata = {
                    "tool": "http_request",
                    "request": tool_exec.get("request", {}),
                    "response": tool_exec.get("response", {}),
                    "config": tool_exec.get("config", {}),
                    "timestamp": tool_exec.get("timestamp", ""),
                    "call_id": tool_exec.get("call_id", ""),
                    "duration": tool_exec.get("duration", 0),
                    "execution_index": tool_exec.get("execution_index", 0),
                }
                return http_metadata  # type: ignore

            # Fallback to standard output extraction
            self.logger.debug("[TOOL-EXTRACTOR] Using standard output extraction")
            return super().extract_output(tool_exec)

        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Failed to extract HTTP request output: {str(e)}",
                extractor=self.name,
                original_error=e,
            )
