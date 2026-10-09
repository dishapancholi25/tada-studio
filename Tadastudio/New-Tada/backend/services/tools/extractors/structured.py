"""
Structured tool extractor for tools with kwargs-based input.

This extractor handles tools that use structured kwargs for their input,
such as search_documents, delegate, and create_sub_agent.
"""

import logging

from ..extraction_models import ToolExecutionData, ToolInputData
from .base import BaseExtractor, ExtractionError, ValidationMixin


logger = logging.getLogger(__name__)


class StructuredToolExtractor(BaseExtractor, ValidationMixin):
    """
    Extractor for structured tools that use kwargs for input.

    Tools handled:
        - search_documents
        - delegate
        - create_sub_agent
        - Any tool with structured kwargs

    Input format:
        {
            "tool": "search_documents",
            "kwargs": {
                "query": "...",
                "collection_id": "...",
                ...
            }
        }
    """

    def __init__(self):
        """Initialize the structured tool extractor."""
        super().__init__(name="StructuredToolExtractor")

    def extract_input(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """
        Extract input from structured tools with kwargs.

        Args:
            tool_exec: Tool execution data

        Returns:
            Extracted input data from kwargs

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            if not self.validate_tool_exec(tool_exec):
                raise ExtractionError(
                    message="Invalid tool execution data",
                    extractor=self.name,
                )

            self.logger.debug(
                "[TOOL-EXTRACTOR] Extracting structured input from kwargs"
            )

            # Extract kwargs directly
            kwargs = self.safe_get(tool_exec, "kwargs", {})

            if not isinstance(kwargs, dict):
                self.logger.warning(
                    "[TOOL-EXTRACTOR] kwargs is not a dictionary, using empty dict"
                )
                kwargs = {}

            self.logger.debug(f"[TOOL-EXTRACTOR] Extracted {len(kwargs)} kwargs fields")

            # Return kwargs as-is for structured tools
            return kwargs  # type: ignore

        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Failed to extract structured input: {str(e)}",
                extractor=self.name,
                original_error=e,
            )
