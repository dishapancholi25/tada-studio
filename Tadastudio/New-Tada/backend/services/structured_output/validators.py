"""
Validation logic for structured output schemas and field values.

This module provides validation functions for schema components,
breaking down complex validation logic into focused, testable functions.
"""

from typing import Any, List, get_origin

from .schemas import FieldType, StructuredOutputSchema
from .type_mapping import (
    get_inner_type,
    get_python_type,
    is_dict_type,
    is_list_type,
    is_optional_type,
)


def validate_optional_default(python_type: type, default_value: Any) -> None:
    """
    Validate default value for Optional types.

    Args:
        python_type: The Optional[T] type
        default_value: The default value to validate

    Raises:
        ValueError: If default value doesn't match the Optional type
    """
    if default_value is None:
        return

    # Check the non-None type
    inner_type = get_inner_type(python_type)
    if not isinstance(default_value, inner_type):
        raise ValueError(
            f"Default value {default_value} doesn't match Optional inner type"
        )


def validate_list_default(python_type: type, default_value: Any) -> None:
    """
    Validate default value for List types.

    Args:
        python_type: The List[T] type
        default_value: The default value to validate

    Raises:
        ValueError: If default value is not a valid list for the type
    """
    if not isinstance(default_value, list):
        raise ValueError("Default value must be a list")

    # Check first element if list is not empty
    if default_value:
        inner_type = get_inner_type(python_type)
        # Resolve subscripted generics (e.g. Dict[str, Any] from
        # List[Dict[str, Any]]) to their runtime origin class, since
        # ``isinstance`` rejects subscripted generics with a TypeError.
        check_type = get_origin(inner_type) or inner_type
        if not isinstance(default_value[0], check_type):
            raise ValueError("List elements don't match expected type")


def validate_dict_default(default_value: Any) -> None:
    """
    Validate default value for Dict types.

    Args:
        default_value: The default value to validate

    Raises:
        ValueError: If default value is not a dict
    """
    if not isinstance(default_value, dict):
        raise ValueError("Default value must be a dict")


def validate_basic_type_default(python_type: type, default_value: Any) -> None:
    """
    Validate default value for basic types (str, int, float, bool).

    Args:
        python_type: The basic Python type
        default_value: The default value to validate

    Raises:
        ValueError: If default value doesn't match the type
    """
    if not isinstance(default_value, python_type):
        raise ValueError(f"Default value {default_value} doesn't match type")


def validate_default_value(field_type: FieldType, default_value: Any) -> bool:
    """
    Validate that default value matches field type.

    This function delegates to specialized validators based on the type category.
    Complexity reduced from 11 to <= 5 per function.

    Args:
        field_type: The field type enum
        default_value: The default value to validate

    Returns:
        True if validation succeeds

    Raises:
        ValueError: If validation fails with specific error message
    """
    python_type = get_python_type(field_type)

    if is_optional_type(python_type):
        validate_optional_default(python_type, default_value)
    elif is_list_type(python_type):
        validate_list_default(python_type, default_value)
    elif is_dict_type(python_type):
        validate_dict_default(default_value)
    else:
        validate_basic_type_default(python_type, default_value)

    return True


def validate_fields(schema: StructuredOutputSchema) -> List[str]:
    """
    Validate all fields in a schema and return list of errors.

    Args:
        schema: The schema to validate

    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    field_names = set()

    for field in schema.fields:
        # Validate field name
        if not field.validate_name():
            errors.append(f"Invalid field name: {field.name}")

        # Check for duplicates
        if field.name in field_names:
            errors.append(f"Duplicate field name: {field.name}")
        field_names.add(field.name)

        # Validate default value type consistency
        if not field.required and field.default is not None:
            try:
                validate_default_value(field.type, field.default)
            except ValueError as e:
                errors.append(f"Invalid default value for {field.name}: {str(e)}")

    return errors


def validate_model_name(model_name: str) -> tuple[bool, str | None]:
    """
    Validate that model name is a valid Python identifier.

    Args:
        model_name: The name to validate

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid.
    """
    if not model_name:
        return False, "Schema name is required"

    if not model_name.isidentifier():
        return (
            False,
            "Schema name must be a valid Python identifier (letters, numbers, underscores; cannot start with a number)",
        )

    if model_name.startswith("_"):
        return False, "Schema name cannot start with an underscore"

    return True, None
