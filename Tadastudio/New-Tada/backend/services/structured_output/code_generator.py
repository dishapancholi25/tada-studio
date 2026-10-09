"""
Python code generation for structured output models.

This module provides functionality to generate Python code strings representing
Pydantic models for preview, debugging, and documentation purposes.
"""

from typing import List

from .schemas import FieldType, StructuredOutputSchema


def generate_field_line(
    field_name: str,
    field_type_str: str,
    description: str,
    is_required: bool,
    default_value: any = None,
) -> str:
    """
    Generate a single field definition line.

    Args:
        field_name: Name of the field
        field_type_str: String representation of the field type
        description: Field description
        is_required: Whether field is required
        default_value: Default value if not required

    Returns:
        Python code string for the field definition
    """
    # Escape quotes in description
    desc = description.replace('"', '\\"')

    if is_required:
        return f'    {field_name}: {field_type_str} = Field(description="{desc}")'
    else:
        default_repr = repr(default_value) if default_value is not None else "None"
        return (
            f"    {field_name}: {field_type_str} = "
            f'Field(default={default_repr}, description="{desc}")'
        )


def generate_example_value(field_type: FieldType, field_name: str) -> str:
    """
    Generate an example value for a field based on its type.

    Args:
        field_type: The field type enum
        field_name: Name of the field (used for string examples)

    Returns:
        String representation of an example value
    """
    if field_type == FieldType.STR:
        return f'"{field_name.lower()}_value"'
    elif field_type == FieldType.INT:
        return "123"
    elif field_type == FieldType.FLOAT:
        return "45.67"
    elif field_type == FieldType.BOOL:
        return "True"
    elif field_type in [FieldType.LIST_STR, FieldType.LIST_INT, FieldType.LIST_FLOAT]:
        return "[]"
    elif field_type == FieldType.DICT_STR_ANY:
        return "{}"
    elif field_type == FieldType.LIST_DICT_STR_ANY:
        return "[]"
    else:
        return "None"


def generate_usage_example(model_name: str, fields: List[tuple]) -> List[str]:
    """
    Generate example usage comment lines.

    Args:
        model_name: Name of the model class
        fields: List of (field_name, field_type, field_name_str) tuples

    Returns:
        List of comment lines showing example usage
    """
    if not fields:
        return []

    lines = [
        "",
        "",
        "# Example usage:",
        f"# instance = {model_name}(",
    ]

    for i, (field_name, field_type) in enumerate(fields):
        example_value = generate_example_value(field_type, field_name)
        comma = "," if i < len(fields) - 1 else ""
        lines.append(f"#     {field_name}={example_value}{comma}")

    lines.append("# )")
    return lines


def generate_model_code(schema: StructuredOutputSchema) -> str:
    """
    Generate Python code for the Pydantic model (for preview/debugging).

    This function is split into smaller helper functions to reduce complexity
    from 12 to <= 5 per function.

    Args:
        schema: The schema to generate code for

    Returns:
        Python code string representing the Pydantic model

    Examples:
        >>> code = generate_model_code(schema)
        >>> print(code)
        from pydantic import BaseModel, Field
        ...
    """
    # Generate header
    lines = [
        "from pydantic import BaseModel, Field",
        "from typing import List, Dict, Any, Optional",
        "",
        f"class {schema.model_name}(BaseModel):",
    ]

    # Add docstring
    if schema.description:
        lines.append(f'    """{schema.description}"""')

    # Generate field definitions
    for field in schema.fields:
        # Automatically wrap non-required fields in Optional[] for display
        field_type_str = field.type.value
        if not field.required and not field_type_str.startswith("Optional["):
            field_type_str = f"Optional[{field_type_str}]"

        field_line = generate_field_line(
            field_name=field.name,
            field_type_str=field_type_str,
            description=field.description,
            is_required=field.required,
            default_value=field.default,
        )
        lines.append(field_line)

    # Generate example usage
    fields_for_example = [(f.name, f.type) for f in schema.fields]
    example_lines = generate_usage_example(schema.model_name, fields_for_example)
    lines.extend(example_lines)

    return "\n".join(lines)
