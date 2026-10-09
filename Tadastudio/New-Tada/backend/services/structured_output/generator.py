"""
Core Pydantic model generation from structured output schemas.

This module provides the main functionality to dynamically create Pydantic models
from schema definitions for use with LangGraph's with_structured_output().
"""

from typing import Type

from pydantic import BaseModel, Field, create_model

from .schemas import FieldType, StructuredOutputSchema
from .type_mapping import get_python_type
from .validators import validate_fields, validate_model_name


def build_field_definition(
    field_name: str,
    field_type: Type,
    description: str,
    is_required: bool,
    default_value: any = None,
    is_dict_type: bool = False,
) -> tuple:
    """
    Build a field definition tuple for create_model.

    Args:
        field_name: Name of the field
        field_type: Python type annotation
        description: Field description
        is_required: Whether the field is required
        default_value: Default value if not required
        is_dict_type: Whether this is a Dict type (for additionalProperties)

    Returns:
        Tuple of (field_type, Field(...)) for create_model
    """
    # NOTE: we deliberately do NOT emit ``additionalProperties: false`` for
    # open ``Dict[str, Any]`` fields. Doing so tells the LLM it must produce
    # an object with zero keys, which is contradictory for an open dict and
    # causes Azure OpenAI (strict json_schema path) to answer with
    # ``choices: null``. The ``is_dict_type`` parameter is kept for API
    # stability but is intentionally unused.
    _ = is_dict_type

    if is_required:
        return (field_type, Field(description=description))
    return (field_type, Field(default=default_value, description=description))


def generate_pydantic_model(schema: StructuredOutputSchema) -> Type[BaseModel]:
    """
    Generate a Pydantic model from schema definition.

    Args:
        schema: StructuredOutputSchema defining the model structure

    Returns:
        Dynamically created Pydantic model class

    Raises:
        ValueError: If schema validation fails

    Examples:
        >>> schema = StructuredOutputSchema(
        ...     id="person_001",
        ...     model_name="Person",
        ...     description="Person information",
        ...     fields=[...]
        ... )
        >>> PersonModel = generate_pydantic_model(schema)
        >>> instance = PersonModel(firstName="John", lastName="Doe")
    """
    # Validate schema
    is_valid, error_msg = validate_model_name(schema.model_name)
    if not is_valid:
        raise ValueError(error_msg)

    field_errors = validate_fields(schema)
    if field_errors:
        raise ValueError(f"Schema validation errors: {'; '.join(field_errors)}")

    # Build field definitions for create_model
    fields = {}
    for field in schema.fields:
        # Automatically wrap non-required fields in Optional[]
        field_type = get_python_type(field.type, required=field.required)
        is_dict = field.type == FieldType.DICT_STR_ANY

        fields[field.name] = build_field_definition(
            field_name=field.name,
            field_type=field_type,
            description=field.description,
            is_required=field.required,
            default_value=field.default,
            is_dict_type=is_dict,
        )

    # Create the model with docstring
    model = create_model(
        schema.model_name,
        __doc__=schema.description or f"{schema.model_name} structured output",
        **fields,
    )

    # Add schema metadata to the model
    model.__schema_id__ = schema.id
    model.__schema_description__ = schema.description

    # Configure model to add additionalProperties: false at root level
    model.model_config = {"extra": "forbid"}

    return model
