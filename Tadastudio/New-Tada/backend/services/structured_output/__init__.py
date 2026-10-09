"""
Structured Output Service for LangGraph Agent Nodes.

This service provides functionality to generate Pydantic models dynamically
from user-defined schemas for structured data output using with_structured_output().

Main Components:
    - Schemas: Data models for defining structured outputs
    - Generator: Core model generation functionality
    - Validators: Schema and field validation
    - Code Generator: Python code preview/debugging
    - Utilities: High-level convenience functions

Usage:
    >>> from backend.services.structured_output import (
    ...     StructuredOutputGenerator,
    ...     StructuredOutputSchema,
    ...     StructuredOutputField,
    ...     FieldType,
    ...     validate_schema,
    ... )
    >>> schema = StructuredOutputSchema(
    ...     id="person_001",
    ...     model_name="Person",
    ...     fields=[...]
    ... )
    >>> model = StructuredOutputGenerator.generate_pydantic_model(schema)
"""

from .code_generator import generate_model_code
from .generator import generate_pydantic_model
from .schemas import FieldType, StructuredOutputField, StructuredOutputSchema
from .utils import validate_schema
import re
from typing import Iterable, List, Optional


class StructuredOutputGenerator:
    """
    Main generator class for creating Pydantic models from schemas.

    This class provides a facade for the structured output functionality,
    maintaining backward compatibility with the original API while using
    the refactored modular implementation.
    """

    @staticmethod
    def generate_pydantic_model(schema: StructuredOutputSchema):
        """
        Generate a Pydantic model from schema definition.

        Args:
            schema: StructuredOutputSchema defining the model structure

        Returns:
            Dynamically created Pydantic model class

        Raises:
            ValueError: If schema validation fails
        """
        return generate_pydantic_model(schema)

    @staticmethod
    def _generate_model_code(schema: StructuredOutputSchema) -> str:
        """
        Generate Python code for the Pydantic model (for preview/debugging).

        Args:
            schema: The schema to generate code for

        Returns:
            Python code string representing the Pydantic model
        """
        return generate_model_code(schema)

    @staticmethod
    def validate_schema(schema_dict: dict) -> dict:
        """
        Validate a schema dictionary and return validation results.

        Args:
            schema_dict: Dictionary representation of schema

        Returns:
            Dict with 'valid' boolean, 'errors' list, and 'schema' object
        """
        return validate_schema(schema_dict)

    @staticmethod
    def create_schema(
        model_name: str,
        fields: Iterable[dict],
        schema_id: Optional[str] = None,
        description: str = "Structured output schema",
    ):
        """
        Create a Pydantic model from a name and collection of field dictionaries.
        This mirrors the legacy `create_schema` API that callers in the async
        executor expect, while delegating to the new generator/validator stack.
        """
        # Generate a stable id if not provided
        safe_model_name = model_name or "Output"
        normalised_id = (
            schema_id
            or re.sub(r"[^a-zA-Z0-9]+", "_", safe_model_name).strip("_")
            or "output_schema"
        )

        structured_fields: List[StructuredOutputField] = []
        for field in fields:
            field_type_value = field.get("type", "str")
            try:
                parsed_type = FieldType(field_type_value)
            except ValueError:
                parsed_type = FieldType.STR

            try:
                structured_fields.append(
                    StructuredOutputField(
                        name=field.get("name", ""),
                        type=parsed_type,
                        description=field.get("description", ""),
                        required=field.get("required", True),
                        default=field.get("default", None),
                    )
                )
            except Exception as e:
                raise ValueError(
                    f"Invalid structured output field definition: {field}"
                ) from e

        schema = StructuredOutputSchema(
            id=normalised_id,
            model_name=safe_model_name,
            description=description or "Structured output schema",
            fields=structured_fields,
        )

        return generate_pydantic_model(schema)


__all__ = [
    "StructuredOutputGenerator",
    "StructuredOutputSchema",
    "StructuredOutputField",
    "FieldType",
    "generate_pydantic_model",
    "generate_model_code",
    "validate_schema",
]
