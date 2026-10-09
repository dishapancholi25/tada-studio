"""Output schema registry for node types."""

# Import definitions to trigger registration
from . import definitions  # noqa: F401
from .registry import (
    FieldType,
    NodeOutputSchema,
    OutputField,
    get_all_schemas,
    get_output_schema,
    register_output_schema,
)

__all__ = [
    "FieldType",
    "OutputField",
    "NodeOutputSchema",
    "register_output_schema",
    "get_output_schema",
    "get_all_schemas",
]
