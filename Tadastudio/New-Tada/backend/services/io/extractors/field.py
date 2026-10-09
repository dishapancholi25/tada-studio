"""
Field Extractor.

Extracts fields from node output using field paths.
"""

from typing import Any, Optional

from .nested import NestedFieldExtractor


class FieldExtractor:
    """
    Extracts fields from node output using field paths.

    Handles complex node outputs with structured data, fields, and raw content.
    """

    def __init__(self):
        """Initialize the field extractor."""
        self.nested_extractor = NestedFieldExtractor()

    def extract(
        self, output: Any, field_path: Optional[str], default_value: Any = None
    ) -> Any:
        """
        Extract a field from node output using a field path.

        Args:
            output: The node output (dict or value)
            field_path: Path to field (e.g., "Country" or "data.user.name")
            default_value: Default value if extraction fails

        Returns:
            The extracted value
        """
        if not field_path:
            return self._extract_whole_output(output, default_value)

        if isinstance(output, dict):
            return self._extract_from_dict_output(output, field_path, default_value)

        return default_value

    def _extract_whole_output(self, output: Any, default_value: Any) -> Any:
        """
        Extract whole output when no field path is specified.

        Args:
            output: The node output
            default_value: Default value if extraction fails

        Returns:
            The extracted value
        """
        if isinstance(output, dict):
            # Try to get a simple value, not a complex dict
            if "raw" in output:
                return output["raw"]
            elif "structured" in output and not isinstance(output["structured"], dict):
                return output["structured"]
            return default_value
        return output

    def _extract_from_dict_output(
        self, output: dict, field_path: str, default_value: Any
    ) -> Any:
        """
        Extract field from dictionary output.

        Tries multiple locations: structured, fields, and direct access.

        Args:
            output: Dictionary output from node
            field_path: Path to field
            default_value: Default value if extraction fails

        Returns:
            The extracted value
        """
        # Try to get from 'structured' first
        if "structured" in output and output["structured"]:
            value = self.nested_extractor.extract(output["structured"], field_path)
            if value is not None:
                return value

        # Then try 'fields'
        if "fields" in output and output["fields"]:
            value = self.nested_extractor.extract(output["fields"], field_path)
            if value is not None:
                return value

        # Try direct field access for backwards compatibility
        value = self.nested_extractor.extract(output, field_path)
        if value is not None:
            return value

        return default_value
