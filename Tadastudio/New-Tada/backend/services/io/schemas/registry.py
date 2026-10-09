"""Output schema registry for declaring what each node type produces."""

from enum import Enum

from pydantic import BaseModel


class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    ANY = "any"


class OutputField(BaseModel):
    """Schema for a single output field."""

    name: str
    type: FieldType
    description: str
    nullable: bool = False
    children: list["OutputField"] | None = None
    items_type: FieldType | None = None

    model_config = {"frozen": False}


class NodeOutputSchema(BaseModel):
    """Complete output schema for a node type."""

    node_type: str
    description: str
    fields: list[OutputField]
    raw_description: str = "String representation of the output"
    supports_dynamic_schema: bool = False
    raw_is_redundant: bool = False

    model_config = {"frozen": False}


# Forward ref resolution
OutputField.model_rebuild()

# The registry
_OUTPUT_SCHEMA_REGISTRY: dict[str, NodeOutputSchema] = {}


def register_output_schema(schema: NodeOutputSchema) -> NodeOutputSchema:
    """Register a node type's output schema."""
    _OUTPUT_SCHEMA_REGISTRY[schema.node_type] = schema
    return schema


def get_output_schema(node_type: str) -> NodeOutputSchema | None:
    """Retrieve schema for a node type."""
    return _OUTPUT_SCHEMA_REGISTRY.get(node_type)


def get_all_schemas() -> dict[str, NodeOutputSchema]:
    """Get all registered schemas."""
    return dict(_OUTPUT_SCHEMA_REGISTRY)
