"""
Pydantic schema models for structured output definitions.

This module defines the data models used to describe structured outputs
for LangGraph agent nodes using with_structured_output().
"""

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Supported field types for structured outputs."""

    STR = "str"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    LIST_STR = "List[str]"
    LIST_INT = "List[int]"
    LIST_FLOAT = "List[float]"
    DICT_STR_ANY = "Dict[str, Any]"
    LIST_DICT_STR_ANY = "List[Dict[str, Any]]"
    OPTIONAL_STR = "Optional[str]"
    OPTIONAL_INT = "Optional[int]"
    OPTIONAL_FLOAT = "Optional[float]"


class StructuredOutputField(BaseModel):
    """Schema for a field in a structured output."""

    name: str = Field(description="Field name (must be valid Python identifier)")
    type: FieldType = Field(description="Field type")
    description: str = Field(
        description="Description of the field for LLM understanding"
    )
    required: bool = Field(default=True, description="Whether the field is required")
    default: Optional[Any] = Field(
        default=None, description="Default value if not required"
    )

    def validate_name(self) -> bool:
        """Validate that field name is a valid Python identifier."""
        return self.name.isidentifier() and not self.name.startswith("_")


class StructuredOutputSchema(BaseModel):
    """Schema for a complete structured output definition."""

    id: str = Field(description="Unique identifier for the schema")
    model_name: str = Field(
        description="Name of the Pydantic model (must be valid Python class name)"
    )
    description: str = Field(
        default="", description="Description of what this structured output represents"
    )
    fields: List[StructuredOutputField] = Field(
        description="List of fields in the model"
    )

    def validate_model_name(self) -> bool:
        """Validate that model name is a valid Python identifier."""
        return self.model_name.isidentifier() and not self.model_name.startswith("_")
