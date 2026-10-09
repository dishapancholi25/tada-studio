"""
Fallback extractor for unrecognized or custom tools.

This extractor provides a catch-all mechanism for tools that don't
match any specific extractor pattern.
"""

import logging

from ..extraction_models import ToolExecutionData, ToolInputData
from .base import BaseExtractor, ExtractionError, ValidationMixin


logger = logging.getLogger(__name__)


class FallbackExtractor(BaseExtractor, ValidationMixin):
    """
    Fallback extractor for unrecognized tools.

    This extractor attempts multiple generic extraction strategies
    when no specific extractor matches the tool.

    Input formats supported:
        1. Direct "input" field
        2. "kwargs" field (most common fallback)
        3. Empty dict if nothing found

    This is the extractor of last resort.
    """

    def __init__(self):
        """Initialize the fallback extractor."""
        super().__init__(name="FallbackExtractor")

    def extract_input(self, tool_exec: ToolExecutionData) -> ToolInputData:
        """
        Extract input using generic fallback strategies.

        Tries:
        1. Direct "input" field
        2. "kwargs" field
        3. Returns empty dict

        Args:
            tool_exec: Tool execution data

        Returns:
            Extracted input data (best effort)

        Raises:
            ExtractionError: If extraction fails
        """
        try:
            if not self.validate_tool_exec(tool_exec):
                raise ExtractionError(
                    message="Invalid tool execution data",
                    extractor=self.name,
                )

            tool_name = tool_exec.get("tool", "unknown")
            self.logger.debug(
                f"[TOOL-EXTRACTOR] Using fallback extraction for tool: {tool_name}"
            )

            # Strategy 1: Check for direct "input" field
            if "input" in tool_exec:
                input_value = tool_exec["input"]
                self.logger.debug("[TOOL-EXTRACTOR] Found direct 'input' field")
                # Wrap non-dict inputs
                if isinstance(input_value, dict):
                    return input_value  # type: ignore
                else:
                    return {"input": input_value}

            # Strategy 2: Check for kwargs (most common)
            kwargs = self.safe_get(tool_exec, "kwargs", {})
            if isinstance(kwargs, dict) and kwargs:
                self.logger.debug(
                    f"[TOOL-EXTRACTOR] Found kwargs with {len(kwargs)} fields"
                )
                return kwargs  # type: ignore

            # Strategy 3: Last resort - empty dict
            self.logger.warning(
                f"[TOOL-EXTRACTOR] No input data found for tool '{tool_name}', returning empty dict"
            )
            return {}

        except ExtractionError:
            raise
        except Exception as e:
            raise ExtractionError(
                message=f"Failed to extract fallback input: {str(e)}",
                extractor=self.name,
                original_error=e,
            )
