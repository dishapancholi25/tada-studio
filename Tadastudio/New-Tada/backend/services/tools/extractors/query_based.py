"""
Query-based tool extractor for search and query tools.

This extractor handles tools that primarily use a query string,
such as web search and database query tools.
"""

import logging

from ..extraction_models import ToolExecutionData, ToolInputData
from .base import BaseExtractor, ExtractionError, ValidationMixin


logger = logging.getLogger(__name__)


class QueryBasedExtractor(BaseExtractor, ValidationMixin):
    """
    Extractor for query-based tools like search and database queries.

    Tools handled:
        - query_database
        - search_web
        - web_search
        - Any tool with a primary query parameter

    Input formats supported:
        1. Direct query: {"query": "..."}
        2. Nested in kwargs: {"kwargs": {"query": "..."}}
        3. Input alias: {"kwargs": {"input": "..."}}
    """

    def __init__(self):
        """Initialize the query-based extractor."""
        super().__init__(name="QueryBasedExtractor")

    def extract_input(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """
        Extract input from query-based tools.

        Tries multiple extraction strategies in order:
        1. Direct "query" field
        2. Query in kwargs
        3. "input" field in kwargs (alias for query)
        4. Fallback to all kwargs

        Args:
            tool_exec: Tool execution data

        Returns:
            Extracted input data with query field

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            if not self.validate_tool_exec(tool_exec):
                raise ExtractionError(
                    message="Invalid tool execution data",
                    extractor=self.name,
                )

            self.logger.debug("[TOOL-EXTRACTOR] Extracting query-based input")

            # Try direct query field first
            result = self._extract_direct_query(tool_exec)
            if result:
                return result

            # Try kwargs-based extraction
            result = self._extract_from_kwargs(tool_exec)
            if result:
                return result

            # Last resort: return empty dict
            self.logger.warning(
                "[TOOL-EXTRACTOR] No query data found in tool execution"
            )
            return {}

        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Failed to extract query-based input: {str(e)}",
                extractor=self.name,
                original_error=e,
            )

    def _extract_direct_query(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """Extract query from direct query field."""
        if "query" in tool_exec:
            query = tool_exec["query"]
            self.logger.debug("[TOOL-EXTRACTOR] Found direct query field")
            if self.is_valid_query(query):
                return {"query": query}
        return {}

    def _extract_from_kwargs(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """Extract query from kwargs (query or input field)."""
        kwargs = self.safe_get(tool_exec, "kwargs", {})
        if not isinstance(kwargs, dict):
            return {}

        # Check for query in kwargs
        if "query" in kwargs and self.is_valid_query(kwargs["query"]):
            self.logger.debug("[TOOL-EXTRACTOR] Found query in kwargs")
            return {"query": kwargs["query"]}

        # Check for input alias in kwargs
        if "input" in kwargs and self.is_valid_query(kwargs["input"]):
            self.logger.debug(
                "[TOOL-EXTRACTOR] Found input field in kwargs (using as query)"
            )
            return {"query": kwargs["input"]}

        # Return all kwargs as fallback
        if kwargs:
            self.logger.debug(
                "[TOOL-EXTRACTOR] No explicit query found, returning all kwargs"
            )
            return kwargs  # type: ignore

        return {}
