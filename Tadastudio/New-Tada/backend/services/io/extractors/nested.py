"""
Nested Field Extractor.

Extracts nested fields from dictionaries using dot notation.
"""

from typing import Any, Optional


class NestedFieldExtractor:
    """
    Extracts nested fields from dictionaries using dot notation.

    Supports paths like "user.profile.name" for deep dictionary access.
    """

    @staticmethod
    def extract(data: Any, field_path: str) -> Optional[Any]:
        """
        Extract a nested field from a dict using dot notation.

        Args:
            data: The data to extract from
            field_path: Dot-separated path (e.g., "user.profile.name")

        Returns:
            The extracted value or None if not found
        """
        if not isinstance(data, dict):
            return None

        # Split path and traverse
        path_parts = field_path.split(".")
        value = data

        for part in path_parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        # Don't return dicts as they can't be inserted into DB
        if isinstance(value, dict):
            return None

        return value
