"""
High-level utility functions for structured output schema validation.

This module provides convenience functions for validating schemas from dictionaries
and other common operations.
"""

import logging
from typing import Any, Dict

from pydantic import ValidationError

from .schemas import StructuredOutputSchema
from .validators import validate_fields, validate_model_name

logger = logging.getLogger(__name__)


def validate_schema(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a schema dictionary and return validation results.

    This is a high-level wrapper that validates both the Pydantic schema
    structure and additional business rules.

    Args:
        schema_dict: Dictionary representation of schema

    Returns:
        Dict with keys:
            - 'valid' (bool): Whether schema is valid
            - 'errors' (List[str]): List of error messages
            - 'schema' (StructuredOutputSchema | None): Parsed schema if valid

    Examples:
        >>> result = validate_schema({
        ...     "id": "test_001",
        ...     "model_name": "TestModel",
        ...     "fields": [...]
        ... })
        >>> if result['valid']:
        ...     schema = result['schema']
    """
    try:
        schema = StructuredOutputSchema(**schema_dict)

        # Additional validations
        errors = []

        is_valid, error_msg = validate_model_name(schema.model_name)
        if not is_valid:
            errors.append(error_msg)

        field_errors = validate_fields(schema)
        errors.extend(field_errors)

        if not schema.fields:
            errors.append("Schema must have at least one field")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "schema": schema if len(errors) == 0 else None,
        }

    except ValidationError as e:
        # Pydantic validation errors are safe to expose (schema structure issues)
        return {
            "valid": False,
            "errors": [f"Schema validation error: {str(e)}"],
            "schema": None,
        }
    except Exception as e:
        logger.error("Unexpected error validating schema: %s", e)
        return {
            "valid": False,
            "errors": ["Unexpected error during schema validation"],
            "schema": None,
        }
