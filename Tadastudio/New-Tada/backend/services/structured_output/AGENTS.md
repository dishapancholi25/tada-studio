# Structured Output Service

## Overview

The structured output service provides functionality to dynamically generate Pydantic models from user-defined schemas
for use with LangGraph's `with_structured_output()` method. This enables LLM responses to conform to specific structured
formats, ensuring consistent and parseable outputs from agent nodes.

**Location:** `backend/services/structured_output/`

**Primary responsibilities:**

- Define field types and schema structures for structured outputs
- Generate Pydantic models dynamically from schema definitions
- Validate schema configurations and field definitions
- Generate Python code previews for debugging and documentation
- Provide integration utilities for LangGraph agent execution

**Key use cases:**

- Creating structured response formats for LLM agents
- Enforcing consistent output schemas across workflow executions
- Validating user-defined output structures before execution
- Generating code previews for debugging and documentation purposes

## Architecture

### Module Structure

```
backend/services/structured_output/
├── __init__.py                  # Public API and facade class
├── schemas.py                   # Pydantic schema definitions
├── generator.py                 # Core model generation logic
├── validators.py                # Schema and field validation
├── code_generator.py            # Python code preview generation
├── type_mapping.py              # Field type to Python type conversion
└── utils.py                     # High-level convenience functions
```

**File purposes:**

- **`__init__.py`** - Exports public API and provides `StructuredOutputGenerator` facade class for backward
  compatibility
- **`schemas.py`** - Defines `FieldType` enum, `StructuredOutputField`, and `StructuredOutputSchema` Pydantic models
- **`generator.py`** - Contains `generate_pydantic_model()` function that creates dynamic Pydantic models
- **`validators.py`** - Validation logic for model names, field names, default values, and schema completeness
- **`code_generator.py`** - Generates Python code strings representing Pydantic models for preview/debugging
- **`type_mapping.py`** - Maps `FieldType` enums to Python type annotations and provides type introspection utilities
- **`utils.py`** - High-level `validate_schema()` wrapper function combining Pydantic and business rule validation

### Design Patterns

**Facade Pattern:**
The `StructuredOutputGenerator` class in `__init__.py` provides a unified interface to the modular implementation,
maintaining backward compatibility whilst delegating to specialised functions.

**Strategy Pattern:**
Type validation and default value checking use specialised validator functions based on the field type category (
optional, list, dict, basic types).

**Factory Pattern:**
The `generate_pydantic_model()` function acts as a factory, dynamically creating Pydantic model classes at runtime using
Pydantic's `create_model()` utility.

**Component Relationships:**

```
┌─────────────────────────────────────────────────────────────┐
│              StructuredOutputGenerator (Facade)              │
│                      (__init__.py)                           │
└────────────┬─────────────────┬────────────────┬─────────────┘
             │                 │                │
             v                 v                v
    ┌────────────────┐  ┌──────────────┐  ┌──────────────┐
    │   generator    │  │ code_generator│  │    utils     │
    │   .generate_   │  │  .generate_   │  │  .validate_  │
    │pydantic_model()│  │  model_code() │  │   schema()   │
    └────────┬───────┘  └───────┬──────┘  └───────┬──────┘
             │                  │                  │
             v                  v                  v
    ┌────────────────────────────────────────────────────────┐
    │              Shared Components                          │
    ├──────────────┬──────────────┬───────────────┬──────────┤
    │  schemas.py  │validators.py │type_mapping.py│          │
    │  (Models)    │(Validation)  │(Type Utils)   │          │
    └──────────────┴──────────────┴───────────────┴──────────┘
```

### Dependencies

**Internal dependencies:**

- `backend.models.workflow.AgentConfig` - Agent configuration models (used by handlers)
- `backend.services.config.get_logger` - Logging infrastructure

**External dependencies:**

- `pydantic` (BaseModel, Field, create_model, ValidationError) - Model creation and validation
- `typing` (Type, List, Dict, Any, Optional, Union) - Type annotations
- `enum` (Enum) - FieldType enumeration
- `langchain_core.language_models` - LLM integration in execution handlers
- `langchain_core.messages` - Message types for LLM communication

**Database dependencies:**
None. This service is stateless and does not interact with databases directly.

**Environment variables and configuration:**
None. Configuration is passed through function parameters and schema definitions.

## Public API

### Exported Classes

- `StructuredOutputGenerator` - Facade class providing static methods for model generation, code preview, and validation
- `StructuredOutputSchema` - Pydantic model defining a complete structured output schema
- `StructuredOutputField` - Pydantic model defining a single field within a schema
- `FieldType` - Enum of supported field types (str, int, float, bool, lists, dicts, optionals)

### Exported Functions

- `generate_pydantic_model()` - Generate a Pydantic model from a schema definition
- `generate_model_code()` - Generate Python code string for preview/debugging
- `validate_schema()` - Validate a schema dictionary and return validation results

### Constants and Configuration

**FieldType enum values:**

- `STR` - String type (`str`)
- `INT` - Integer type (`int`)
- `FLOAT` - Float type (`float`)
- `BOOL` - Boolean type (`bool`)
- `LIST_STR` - List of strings (`List[str]`)
- `LIST_INT` - List of integers (`List[int]`)
- `LIST_FLOAT` - List of floats (`List[float]`)
- `DICT_STR_ANY` - Dictionary with string keys and any values (`Dict[str, Any]`)
- `OPTIONAL_STR` - Optional string (`Optional[str]`)
- `OPTIONAL_INT` - Optional integer (`Optional[int]`)
- `OPTIONAL_FLOAT` - Optional float (`Optional[float]`)

### Exceptions

This module does not define custom exceptions. It raises standard Python exceptions:

- `ValueError` - Raised when schema validation fails or model name is invalid
- `pydantic.ValidationError` - Raised when Pydantic schema instantiation fails

## Core Classes

### `FieldType`

Enumeration of supported field types for structured outputs.

**Purpose:** Defines the available field types that can be used in structured output schemas, ensuring type safety and
consistent type mapping.

**Responsibilities:**

- Define all supported field types
- Provide string representations for serialisation
- Enable type checking and validation

**Usage:**

```python
from backend.services.structured_output import FieldType

# Access field types
field_type = FieldType.STR
optional_int = FieldType.OPTIONAL_INT
list_of_strings = FieldType.LIST_STR
```

**Available Types:**

| FieldType Value            | Python Type       | Description                    |
|----------------------------|-------------------|--------------------------------|
| `FieldType.STR`            | `str`             | Basic string type              |
| `FieldType.INT`            | `int`             | Integer type                   |
| `FieldType.FLOAT`          | `float`           | Floating-point type            |
| `FieldType.BOOL`           | `bool`            | Boolean type                   |
| `FieldType.LIST_STR`       | `List[str]`       | List of strings                |
| `FieldType.LIST_INT`       | `List[int]`       | List of integers               |
| `FieldType.LIST_FLOAT`     | `List[float]`     | List of floats                 |
| `FieldType.DICT_STR_ANY`   | `Dict[str, Any]`  | Dictionary with string keys    |
| `FieldType.OPTIONAL_STR`   | `Optional[str]`   | Optional string (can be None)  |
| `FieldType.OPTIONAL_INT`   | `Optional[int]`   | Optional integer (can be None) |
| `FieldType.OPTIONAL_FLOAT` | `Optional[float]` | Optional float (can be None)   |

---

### `StructuredOutputField`

Schema definition for a single field in a structured output.

**Purpose:** Represents a field within a structured output schema, including its name, type, description, and default
value configuration.

**Responsibilities:**

- Store field metadata (name, type, description)
- Track whether field is required or optional
- Store default values for optional fields
- Validate field name is a valid Python identifier

**Initialisation:**

```python
def __init__(
    self,
    name: str,
    type: FieldType,
    description: str,
    required: bool = True,
    default: Optional[Any] = None,
) -> None:
    """
    Args:
        name: Field name (must be valid Python identifier)
        type: Field type from FieldType enum
        description: Description of the field for LLM understanding
        required: Whether the field is required (default: True)
        default: Default value if not required (default: None)
    """
```

**Key Methods:**

#### `validate_name()`

```python
def validate_name(self) -> bool:
    """Validate that field name is a valid Python identifier."""
```

**Returns:**

- `bool` - True if field name is a valid Python identifier that doesn't start with underscore

**Behaviour:**

- Checks if name is a valid Python identifier using `str.isidentifier()`
- Ensures name doesn't start with underscore (reserved for private fields)
- Does not raise exceptions, returns boolean result

**Example:**

```python
from backend.services.structured_output import StructuredOutputField, FieldType

# Create a required field
field = StructuredOutputField(
    name="firstName",
    type=FieldType.STR,
    description="The person's first name",
    required=True,
)

# Validate the field name
is_valid = field.validate_name()  # Returns True

# Create an optional field with default
optional_field = StructuredOutputField(
    name="age",
    type=FieldType.OPTIONAL_INT,
    description="The person's age",
    required=False,
    default=None,
)
```

**Use Cases:**

- Defining fields for structured LLM outputs
- Building schema definitions for agent responses
- Specifying required vs. optional data in outputs

---

### `StructuredOutputSchema`

Complete schema definition for a structured output.

**Purpose:** Represents a complete structured output schema containing multiple fields, model name, and metadata.

**Responsibilities:**

- Store schema metadata (id, model name, description)
- Maintain list of fields in the schema
- Validate model name is a valid Python class name
- Provide schema structure for model generation

**Initialisation:**

```python
def __init__(
    self,
    id: str,
    model_name: str,
    fields: List[StructuredOutputField],
    description: str = "",
) -> None:
    """
    Args:
        id: Unique identifier for the schema
        model_name: Name of the Pydantic model (must be valid Python class name)
        fields: List of fields in the model
        description: Description of what this structured output represents (default: "")
    """
```

**Key Methods:**

#### `validate_model_name()`

```python
def validate_model_name(self) -> bool:
    """Validate that model name is a valid Python class name."""
```

**Returns:**

- `bool` - True if model name is a valid Python class name

**Behaviour:**

- Checks if model name is a valid Python identifier
- Ensures first character is uppercase (PEP 8 class naming convention)
- Ensures name doesn't start with underscore
- Does not raise exceptions, returns boolean result

**Example:**

```python
from backend.services.structured_output import (
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

# Define fields
fields = [
    StructuredOutputField(
        name="firstName",
        type=FieldType.STR,
        description="The person's first name",
        required=True,
    ),
    StructuredOutputField(
        name="lastName",
        type=FieldType.STR,
        description="The person's last name",
        required=True,
    ),
    StructuredOutputField(
        name="age",
        type=FieldType.OPTIONAL_INT,
        description="The person's age",
        required=False,
        default=None,
    ),
]

# Create schema
schema = StructuredOutputSchema(
    id="person_schema_001",
    model_name="PersonInfo",
    description="Information about a person",
    fields=fields,
)

# Validate model name
is_valid = schema.validate_model_name()  # Returns True
```

**Use Cases:**

- Defining complete structured output schemas for agents
- Validating schema definitions before model generation
- Storing schema configurations for workflow nodes

---

### `StructuredOutputGenerator`

Main generator class for creating Pydantic models from schemas.

**Purpose:** Provides a unified facade interface for structured output functionality, maintaining backward compatibility
whilst delegating to modular implementations.

**Responsibilities:**

- Generate Pydantic models from schema definitions
- Generate Python code previews for debugging
- Validate schema dictionaries
- Provide static method interface for all structured output operations

**Note:** This is a facade class with all static methods. It does not maintain state and should not be instantiated (
though instantiation is harmless).

**Key Methods:**

#### `generate_pydantic_model()`

```python
@staticmethod
def generate_pydantic_model(schema: StructuredOutputSchema) -> Type[BaseModel]:
    """Generate a Pydantic model from schema definition."""
```

**Parameters:**

- `schema` (StructuredOutputSchema) - Schema defining the model structure

**Returns:**

- `Type[BaseModel]` - Dynamically created Pydantic model class

**Raises:**

- `ValueError` - If schema validation fails or model name is invalid

**Example:**

```python
from backend.services.structured_output import (
    StructuredOutputGenerator,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

# Define schema
schema = StructuredOutputSchema(
    id="product_001",
    model_name="Product",
    description="Product information",
    fields=[
        StructuredOutputField(
            name="name",
            type=FieldType.STR,
            description="Product name",
            required=True,
        ),
        StructuredOutputField(
            name="price",
            type=FieldType.FLOAT,
            description="Product price in USD",
            required=True,
        ),
        StructuredOutputField(
            name="tags",
            type=FieldType.LIST_STR,
            description="Product tags",
            required=False,
            default=[],
        ),
    ],
)

# Generate Pydantic model
ProductModel = StructuredOutputGenerator.generate_pydantic_model(schema)

# Create instance
product = ProductModel(
    name="Laptop",
    price=999.99,
    tags=["electronics", "computers"],
)

# Access generated model metadata
print(ProductModel.__schema_id__)  # "product_001"
print(ProductModel.__name__)  # "Product"
```

**Behaviour:**

- Validates model name format
- Validates all fields for correctness
- Creates Pydantic model with proper field definitions
- Adds `additionalProperties: false` to prevent extra fields
- Attaches metadata attributes (`__schema_id__`, `__schema_description__`)
- Configures model with `extra='forbid'` to reject unknown fields

**Use Cases:**

- Creating structured output models for LangGraph agents
- Generating runtime Pydantic models from user-defined schemas
- Enforcing strict output formats for LLM responses

---

#### `_generate_model_code()`

```python
@staticmethod
def _generate_model_code(schema: StructuredOutputSchema) -> str:
    """Generate Python code for the Pydantic model (for preview/debugging)."""
```

**Parameters:**

- `schema` (StructuredOutputSchema) - The schema to generate code for

**Returns:**

- `str` - Python code string representing the Pydantic model

**Example:**

```python
from backend.services.structured_output import (
    StructuredOutputGenerator,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

schema = StructuredOutputSchema(
    id="user_001",
    model_name="User",
    description="User account information",
    fields=[
        StructuredOutputField(
            name="username",
            type=FieldType.STR,
            description="User's username",
            required=True,
        ),
        StructuredOutputField(
            name="email",
            type=FieldType.STR,
            description="User's email address",
            required=True,
        ),
    ],
)

# Generate code preview
code = StructuredOutputGenerator._generate_model_code(schema)
print(code)
```

**Output:**

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class User(BaseModel):
    """User account information"""
    username: str = Field(description="User's username")
    email: str = Field(description="User's email address")


# Example usage:
# instance = User(
#     username="username_value",
#     email="email_value",
# )
```

**Behaviour:**

- Generates properly formatted Python code
- Includes necessary imports
- Adds model docstring if description provided
- Includes example usage in comments
- Escapes special characters in descriptions

**Use Cases:**

- Debugging schema definitions
- Providing code previews in the UI
- Documenting generated models
- Troubleshooting model generation issues

---

#### `validate_schema()`

```python
@staticmethod
def validate_schema(schema_dict: dict) -> dict:
    """Validate a schema dictionary and return validation results."""
```

**Parameters:**

- `schema_dict` (dict) - Dictionary representation of schema

**Returns:**

- `dict` - Dictionary with keys:
  - `valid` (bool) - Whether schema is valid
  - `errors` (List[str]) - List of error messages (empty if valid)
  - `schema` (StructuredOutputSchema | None) - Parsed schema object if valid, None otherwise

**Example:**

```python
from backend.services.structured_output import StructuredOutputGenerator

# Valid schema
schema_dict = {
    "id": "test_001",
    "model_name": "TestModel",
    "description": "Test schema",
    "fields": [
        {
            "name": "field1",
            "type": "str",
            "description": "Test field",
            "required": True,
        }
    ],
}

result = StructuredOutputGenerator.validate_schema(schema_dict)
if result["valid"]:
    schema = result["schema"]
    print(f"Schema {schema.model_name} is valid")
else:
    print(f"Validation errors: {result['errors']}")

# Invalid schema (duplicate fields)
invalid_dict = {
    "id": "test_002",
    "model_name": "InvalidModel",
    "fields": [
        {"name": "field1", "type": "str", "description": "First", "required": True},
        {"name": "field1", "type": "int", "description": "Duplicate", "required": True},
    ],
}

result = StructuredOutputGenerator.validate_schema(invalid_dict)
# result["valid"] == False
# result["errors"] == ["Duplicate field name: field1"]
```

**Behaviour:**

- Validates Pydantic schema structure
- Checks model name format (valid class name, starts with uppercase)
- Validates field names (valid identifiers, no duplicates)
- Validates default values match field types
- Ensures at least one field exists
- Returns detailed error messages for debugging

**Raises:**
Does not raise exceptions; validation errors are returned in the result dictionary.

**Use Cases:**

- Validating user-provided schemas before model generation
- API endpoint validation
- Providing user feedback on schema errors
- Pre-flight checks before workflow execution

## Functions

### `generate_pydantic_model()`

Generate a Pydantic model from a schema definition.

**Signature:**

```python
def generate_pydantic_model(schema: StructuredOutputSchema) -> Type[BaseModel]:
    """
    Generate a Pydantic model from schema definition.

    Args:
        schema: StructuredOutputSchema defining the model structure

    Returns:
        Dynamically created Pydantic model class

    Raises:
        ValueError: If schema validation fails
    """
```

**Parameters:**

- `schema` (StructuredOutputSchema) - Complete schema definition including model name, fields, and metadata

**Returns:**

- `Type[BaseModel]` - Dynamically created Pydantic model class ready for use with `with_structured_output()`

**Raises:**

- `ValueError` - If model name is invalid or field validation fails

**Example:**

```python
from backend.services.structured_output import (
    generate_pydantic_model,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

# Create schema
schema = StructuredOutputSchema(
    id="email_schema",
    model_name="EmailMessage",
    description="Structured email message",
    fields=[
        StructuredOutputField(
            name="subject",
            type=FieldType.STR,
            description="Email subject line",
            required=True,
        ),
        StructuredOutputField(
            name="body",
            type=FieldType.STR,
            description="Email body content",
            required=True,
        ),
        StructuredOutputField(
            name="recipients",
            type=FieldType.LIST_STR,
            description="List of recipient email addresses",
            required=True,
        ),
        StructuredOutputField(
            name="priority",
            type=FieldType.OPTIONAL_INT,
            description="Priority level (1-5)",
            required=False,
            default=3,
        ),
    ],
)

# Generate model
EmailModel = generate_pydantic_model(schema)

# Use the model
email = EmailModel(
    subject="Meeting Tomorrow",
    body="Let's meet at 2pm in conference room A.",
    recipients=["alice@example.com", "bob@example.com"],
    priority=2,
)

# Model automatically validates
print(email.model_dump_json(indent=2))
```

**Use Cases:**

- Creating models for LangGraph's `with_structured_output()`
- Runtime model generation from database-stored schemas
- Dynamic response format configuration

---

### `generate_model_code()`

Generate Python code string representing a Pydantic model.

**Signature:**

```python
def generate_model_code(schema: StructuredOutputSchema) -> str:
    """
    Generate Python code for the Pydantic model (for preview/debugging).

    Args:
        schema: The schema to generate code for

    Returns:
        Python code string representing the Pydantic model
    """
```

**Parameters:**

- `schema` (StructuredOutputSchema) - Schema definition to generate code from

**Returns:**

- `str` - Properly formatted Python code representing the Pydantic model

**Example:**

```python
from backend.services.structured_output import (
    generate_model_code,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

schema = StructuredOutputSchema(
    id="task_001",
    model_name="Task",
    description="A task item",
    fields=[
        StructuredOutputField(
            name="title",
            type=FieldType.STR,
            description="Task title",
            required=True,
        ),
        StructuredOutputField(
            name="completed",
            type=FieldType.BOOL,
            description="Whether task is completed",
            required=False,
            default=False,
        ),
    ],
)

# Generate code preview
code = generate_model_code(schema)
print(code)

# Output:
# from pydantic import BaseModel, Field
# from typing import List, Dict, Any, Optional
#
# class Task(BaseModel):
#     """A task item"""
#     title: str = Field(description="Task title")
#     completed: bool = Field(default=False, description="Whether task is completed")
#
#
# # Example usage:
# # instance = Task(
# #     title="title_value",
# #     completed=True,
# # )
```

**Use Cases:**

- Debugging schema definitions in development
- Providing code previews in the frontend UI
- Generating documentation for schemas
- Code review and troubleshooting

---

### `validate_schema()`

Validate a schema dictionary and return validation results.

**Signature:**

```python
def validate_schema(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a schema dictionary and return validation results.

    Args:
        schema_dict: Dictionary representation of schema

    Returns:
        Dict with keys:
            - 'valid' (bool): Whether schema is valid
            - 'errors' (List[str]): List of error messages
            - 'schema' (StructuredOutputSchema | None): Parsed schema if valid
    """
```

**Parameters:**

- `schema_dict` (Dict[str, Any]) - Dictionary containing schema definition

**Returns:**

- `Dict[str, Any]` - Validation result with `valid`, `errors`, and `schema` keys

**Example:**

```python
from backend.services.structured_output import validate_schema

# Example 1: Valid schema
valid_schema = {
    "id": "contact_001",
    "model_name": "Contact",
    "description": "Contact information",
    "fields": [
        {
            "name": "name",
            "type": "str",
            "description": "Contact name",
            "required": True,
        },
        {
            "name": "phone",
            "type": "Optional[str]",
            "description": "Phone number",
            "required": False,
            "default": None,
        },
    ],
}

result = validate_schema(valid_schema)
assert result["valid"] == True
assert result["schema"] is not None
assert len(result["errors"]) == 0

# Example 2: Invalid schema (bad field name)
invalid_schema = {
    "id": "bad_001",
    "model_name": "BadModel",
    "fields": [
        {
            "name": "123invalid",  # Cannot start with number
            "type": "str",
            "description": "Invalid field name",
            "required": True,
        }
    ],
}

result = validate_schema(invalid_schema)
assert result["valid"] == False
assert "Invalid field name" in result["errors"][0]
assert result["schema"] is None

# Example 3: No fields
empty_schema = {
    "id": "empty_001",
    "model_name": "EmptyModel",
    "fields": [],
}

result = validate_schema(empty_schema)
assert result["valid"] == False
assert "must have at least one field" in result["errors"][0]
```

**Use Cases:**

- API endpoint validation before processing
- User input validation in the frontend
- Pre-flight checks before workflow compilation
- Providing detailed error feedback to users

## Configuration

### Configuration Classes

This service does not use configuration classes. All configuration is passed through schema definitions.

### Environment Variables

This service does not use environment variables.

### Initialisation Patterns

**Basic Initialisation (Functional API):**

```python
from backend.services.structured_output import (
    generate_pydantic_model,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

# Create schema
schema = StructuredOutputSchema(
    id="example_001",
    model_name="ExampleModel",
    fields=[
        StructuredOutputField(
            name="field1",
            type=FieldType.STR,
            description="Example field",
            required=True,
        )
    ],
)

# Generate model
Model = generate_pydantic_model(schema)
```

**Initialisation via Facade (Backward Compatible):**

```python
from backend.services.structured_output import StructuredOutputGenerator

# Using static methods
Model = StructuredOutputGenerator.generate_pydantic_model(schema)
code = StructuredOutputGenerator._generate_model_code(schema)
```

**From Dictionary (API Usage):**

```python
from backend.services.structured_output import validate_schema, generate_pydantic_model

# Validate dictionary first
schema_dict = {
    "id": "api_001",
    "model_name": "ApiResponse",
    "fields": [...],
}

result = validate_schema(schema_dict)
if result["valid"]:
    schema = result["schema"]
    Model = generate_pydantic_model(schema)
else:
    print(f"Validation errors: {result['errors']}")
```

## Error Handling

### Exception Hierarchy

```
Exception
└── ValueError
    └── (Raised for invalid schemas, model names, field validation)

pydantic.ValidationError
└── (Raised when schema dict doesn't match StructuredOutputSchema model)
```

### Exception Details

#### `ValueError`

Raised when schema validation fails or model generation encounters invalid configuration.

**When raised:**

- Invalid model name (not a valid class name, doesn't start with uppercase, starts with underscore)
- Field validation errors (invalid field names, duplicate names, type mismatches)
- Default value doesn't match field type

**Example:**

```python
from backend.services.structured_output import (
    generate_pydantic_model,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

try:
    # Invalid model name (lowercase)
    schema = StructuredOutputSchema(
        id="bad_001",
        model_name="badModelName",  # Should start with uppercase
        fields=[
            StructuredOutputField(
                name="field1",
                type=FieldType.STR,
                description="Test",
                required=True,
            )
        ],
    )
    Model = generate_pydantic_model(schema)
except ValueError as e:
    print(f"Schema validation error: {e}")
    # Output: "Invalid model name: badModelName"
```

#### `pydantic.ValidationError`

Raised when attempting to instantiate `StructuredOutputSchema` or `StructuredOutputField` with invalid data.

**When raised:**

- Missing required fields in schema dictionary
- Wrong data types for schema fields
- Invalid enum values

**Example:**

```python
from pydantic import ValidationError
from backend.services.structured_output import StructuredOutputSchema

try:
    # Missing required 'fields' key
    schema = StructuredOutputSchema(
        id="test_001",
        model_name="TestModel",
        # fields=[]  # Missing!
    )
except ValidationError as e:
    print(f"Pydantic validation error: {e}")
```

### Error Handling Patterns

**Recommended Pattern for API Endpoints:**

```python
from backend.services.structured_output import (
    StructuredOutputGenerator,
    validate_schema,
    generate_pydantic_model,
)
from pydantic import ValidationError

async def create_structured_output(schema_dict: dict):
    """API endpoint for creating structured output model."""

    # Step 1: Validate the schema
    validation_result = validate_schema(schema_dict)
    if not validation_result["valid"]:
        return {
            "success": False,
            "errors": validation_result["errors"],
        }

    # Step 2: Generate the model
    try:
        schema = validation_result["schema"]
        model = generate_pydantic_model(schema)

        return {
            "success": True,
            "model_name": model.__name__,
            "schema_id": model.__schema_id__,
        }

    except ValueError as e:
        # Schema validation failed during generation
        return {
            "success": False,
            "errors": [f"Model generation failed: {str(e)}"],
        }

    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error generating model: {e}", exc_info=True)
        return {
            "success": False,
            "errors": [f"Unexpected error: {str(e)}"],
        }
```

**Recommended Pattern for Agent Execution:**

```python
from backend.services.structured_output import (
    StructuredOutputSchema,
    generate_pydantic_model,
)
from langchain_core.language_models import BaseChatModel

def setup_agent_with_structured_output(
    llm: BaseChatModel,
    schema_config: dict,
) -> BaseChatModel:
    """Configure LLM with structured output."""

    try:
        # Create schema from config
        schema = StructuredOutputSchema(**schema_config)

        # Generate Pydantic model
        model = generate_pydantic_model(schema)

        # Bind to LLM
        return llm.with_structured_output(model)

    except ValueError as e:
        logger.error(f"Invalid schema configuration: {e}")
        raise

    except Exception as e:
        logger.error(f"Failed to setup structured output: {e}", exc_info=True)
        raise
```

## Integration Patterns

### Integration with API Layer

The structured output service integrates with the API layer through validation and preview endpoints
in [backend/api/graph/routes.py:404-413](backend/api/graph/routes.py#L404-L413).

**Example from API routes:**

```python
from fastapi import APIRouter
from typing import Any, Dict

from backend.api.graph.handlers.validation import (
    handle_validate_structured_output_schema,
    handle_preview_structured_output_code,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])

@router.post("/structured-outputs/validate")
async def validate_structured_output_schema(schema_data: Dict[str, Any]):
    """Validate a structured output schema."""
    return await handle_validate_structured_output_schema(schema_data)

@router.post("/structured-outputs/preview")
async def preview_structured_output_code(schema_data: Dict[str, Any]):
    """Preview the generated Pydantic model code for a schema."""
    return await handle_preview_structured_output_code(schema_data)
```

**Handler implementation:**

```python
# From backend/api/graph/handlers/validation.py

from backend.services.structured_output import StructuredOutputGenerator

async def handle_validate_structured_output_schema(
    schema_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate a structured output schema."""

    try:
        result = StructuredOutputGenerator.validate_schema(schema_data)
        return {"success": True, "validation_result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def handle_preview_structured_output_code(
    schema_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Preview the generated Pydantic model code for a schema."""

    try:
        # Validate first
        validation_result = StructuredOutputGenerator.validate_schema(schema_data)
        if not validation_result["valid"]:
            return {"success": False, "errors": validation_result["errors"]}

        # Generate code preview
        schema = validation_result["schema"]
        model_code = StructuredOutputGenerator._generate_model_code(schema)

        return {
            "success": True,
            "model_code": model_code,
            "tool_code": None,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Integration with Agent Execution Services

The service integrates with agent execution through specialised handler classes in the execution service.

**Synchronous Agent Execution:**

```python
# From backend/services/execution/agent/structured_output_handler.py

from backend.services.structured_output import (
    StructuredOutputGenerator,
    StructuredOutputSchema,
)

class StructuredOutputHandler:
    """Handles structured output processing for agents."""

    @staticmethod
    def get_pydantic_model(schema_dict: Dict[str, Any]) -> Any:
        """Generate Pydantic model from schema dictionary."""
        schema = StructuredOutputSchema(**schema_dict)
        pydantic_model = StructuredOutputGenerator.generate_pydantic_model(schema)
        return pydantic_model

    @staticmethod
    def process_with_structured_output(
        llm: Any,
        pydantic_model: Any,
        raw_response: Any,
        tool_results: Optional[List[Any]] = None,
    ) -> AIMessage:
        """Process a response with structured output formatting."""
        # Apply structured output to LLM
        structured_llm = llm.with_structured_output(pydantic_model)

        # Build formatting prompt
        format_prompt = build_format_prompt(raw_response, tool_results)

        # Get structured result
        result = structured_llm.invoke([
            SystemMessage(content="Extract and organize information."),
            HumanMessage(content=format_prompt),
        ])

        # Convert to JSON string
        json_output = result.model_dump_json(indent=2)
        return AIMessage(content=json_output), result
```

**Asynchronous Agent Execution:**

```python
# From backend/services/execution/async_agent/structured_output_handler.py

from backend.services.structured_output import StructuredOutputGenerator

class StructuredOutputHandler:
    """Handles structured output execution for async agents."""

    def __init__(self):
        self.generator = StructuredOutputGenerator()

    async def execute_with_structured_output(
        self,
        llm: BaseChatModel,
        messages: List[BaseMessage],
        agent_config: AgentConfig,
    ) -> Any:
        """Execute LLM with structured output constraints."""

        # Get structured output configuration
        structured_outputs = agent_config.structured_outputs
        structured_config = structured_outputs[0]

        # Create schema
        schema = self._create_schema(structured_config)

        # Bind schema to LLM
        llm_with_structure = llm.with_structured_output(schema)

        # Execute asynchronously
        response = await llm_with_structure.ainvoke(messages)
        return response

    def _create_schema(self, structured_config: Dict[str, Any]) -> Any:
        """Create structured output schema from configuration."""
        schema_name = structured_config.get("name", "Output")
        schema_fields = structured_config.get("fields", [])

        # Use generator to create schema
        schema = self.generator.create_schema(schema_name, schema_fields)
        return schema
```

### Dependency Flow

**Service Dependencies:**

```
┌──────────────────────────────────────────────────────────┐
│         API Layer (backend/api/graph/)                   │
│  - validation.py (handlers)                              │
│  - routes.py (endpoints)                                 │
└─────────────────────┬────────────────────────────────────┘
                      │
                      v
┌──────────────────────────────────────────────────────────┐
│   Structured Output Service (backend/services/           │
│                              structured_output/)          │
│  - StructuredOutputGenerator                             │
│  - validate_schema()                                     │
│  - generate_pydantic_model()                             │
└─────────────────────┬────────────────────────────────────┘
                      │
                      v
┌──────────────────────────────────────────────────────────┐
│    Execution Service (backend/services/execution/)       │
│  - agent/structured_output_handler.py                    │
│  - async_agent/structured_output_handler.py              │
└──────────────────────────────────────────────────────────┘
```

**Data Flow:**

1. User defines schema in frontend
2. Frontend sends schema to API endpoint (`/api/graph/structured-outputs/validate`)
3. API handler calls `validate_schema()` to verify schema
4. Schema is stored in workflow/agent configuration
5. During workflow execution, execution handler retrieves schema config
6. Execution handler calls `generate_pydantic_model()` to create runtime model
7. Model is bound to LLM using `with_structured_output()`
8. LLM produces structured output conforming to the model

### Common Integration Patterns

#### Pattern 1: Validation Before Storage

Validate schemas before storing them in workflow configurations.

```python
from backend.services.structured_output import validate_schema

async def save_agent_configuration(agent_config: dict):
    """Save agent configuration with structured output validation."""

    # If agent has structured outputs, validate them
    if "structured_outputs" in agent_config:
        for output_schema in agent_config["structured_outputs"]:
            result = validate_schema(output_schema)
            if not result["valid"]:
                return {
                    "success": False,
                    "errors": result["errors"],
                }

    # Save configuration
    save_to_database(agent_config)
    return {"success": True}
```

#### Pattern 2: Runtime Model Generation

Generate models at runtime during workflow execution.

```python
from backend.services.structured_output import generate_pydantic_model, StructuredOutputSchema

def execute_agent_with_structured_output(agent_config: dict, llm: Any, messages: list):
    """Execute agent with structured output."""

    # Get structured output configuration
    structured_config = agent_config["structured_outputs"][0]

    # Create schema
    schema = StructuredOutputSchema(**structured_config)

    # Generate model
    model = generate_pydantic_model(schema)

    # Apply to LLM
    structured_llm = llm.with_structured_output(model)

    # Execute
    response = structured_llm.invoke(messages)

    # Response is guaranteed to conform to the model
    return response
```

#### Pattern 3: Code Preview for Debugging

Generate code previews for debugging and documentation.

```python
from backend.services.structured_output import generate_model_code

def debug_schema(schema_dict: dict):
    """Debug a schema by generating and printing the code."""

    from backend.services.structured_output import validate_schema

    # Validate
    result = validate_schema(schema_dict)
    if not result["valid"]:
        print(f"Schema validation failed: {result['errors']}")
        return

    # Generate code preview
    schema = result["schema"]
    code = generate_model_code(schema)

    print("Generated Pydantic Model:")
    print("=" * 60)
    print(code)
    print("=" * 60)
```

## Usage Examples

### Example 1: Basic Usage

Create a simple structured output schema and generate a Pydantic model.

```python
from backend.services.structured_output import (
    generate_pydantic_model,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

# Step 1: Define the schema
schema = StructuredOutputSchema(
    id="greeting_001",
    model_name="Greeting",
    description="A friendly greeting message",
    fields=[
        StructuredOutputField(
            name="message",
            type=FieldType.STR,
            description="The greeting message text",
            required=True,
        ),
        StructuredOutputField(
            name="language",
            type=FieldType.STR,
            description="Language of the greeting",
            required=True,
        ),
    ],
)

# Step 2: Generate the Pydantic model
GreetingModel = generate_pydantic_model(schema)

# Step 3: Create an instance
greeting = GreetingModel(
    message="Hello, world!",
    language="English",
)

# Step 4: Use the model
print(f"Greeting: {greeting.message}")
print(f"Language: {greeting.language}")
print(f"JSON: {greeting.model_dump_json(indent=2)}")

# Output:
# Greeting: Hello, world!
# Language: English
# JSON: {
#   "message": "Hello, world!",
#   "language": "English"
# }
```

### Example 2: Advanced Usage with Optional Fields and Lists

Create a complex schema with optional fields, lists, and default values.

```python
from backend.services.structured_output import (
    StructuredOutputGenerator,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
    generate_model_code,
)

# Step 1: Define a complex schema
schema = StructuredOutputSchema(
    id="article_001",
    model_name="BlogArticle",
    description="Blog article with metadata",
    fields=[
        StructuredOutputField(
            name="title",
            type=FieldType.STR,
            description="Article title",
            required=True,
        ),
        StructuredOutputField(
            name="content",
            type=FieldType.STR,
            description="Article main content",
            required=True,
        ),
        StructuredOutputField(
            name="tags",
            type=FieldType.LIST_STR,
            description="Article tags for categorisation",
            required=False,
            default=[],
        ),
        StructuredOutputField(
            name="wordCount",
            type=FieldType.OPTIONAL_INT,
            description="Approximate word count",
            required=False,
            default=None,
        ),
        StructuredOutputField(
            name="published",
            type=FieldType.BOOL,
            description="Whether article is published",
            required=False,
            default=False,
        ),
        StructuredOutputField(
            name="metadata",
            type=FieldType.DICT_STR_ANY,
            description="Additional metadata",
            required=False,
            default={},
        ),
    ],
)

# Step 2: Validate the schema
validation_result = StructuredOutputGenerator.validate_schema(schema.model_dump())
print(f"Schema valid: {validation_result['valid']}")

# Step 3: Generate code preview
code = generate_model_code(schema)
print("\nGenerated Code:")
print(code)

# Step 4: Generate the model
ArticleModel = StructuredOutputGenerator.generate_pydantic_model(schema)

# Step 5: Create instances
article1 = ArticleModel(
    title="Introduction to Python",
    content="Python is a powerful programming language...",
    tags=["python", "programming", "tutorial"],
    wordCount=1200,
    published=True,
    metadata={"author": "Jane Doe", "category": "Tutorial"},
)

article2 = ArticleModel(
    title="Draft Article",
    content="This is a draft...",
    # Optional fields use defaults
)

print(f"\nArticle 1: {article1.title} - Published: {article1.published}")
print(f"Article 2: {article2.title} - Published: {article2.published}")
```

### Example 3: Integration with LangGraph Agent

Complete workflow showing integration with a LangGraph agent using structured output.

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.services.structured_output import (
    generate_pydantic_model,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)

# Step 1: Define structured output schema for sentiment analysis
sentiment_schema = StructuredOutputSchema(
    id="sentiment_001",
    model_name="SentimentAnalysis",
    description="Sentiment analysis result",
    fields=[
        StructuredOutputField(
            name="sentiment",
            type=FieldType.STR,
            description="Overall sentiment: positive, negative, or neutral",
            required=True,
        ),
        StructuredOutputField(
            name="confidence",
            type=FieldType.FLOAT,
            description="Confidence score between 0.0 and 1.0",
            required=True,
        ),
        StructuredOutputField(
            name="keywords",
            type=FieldType.LIST_STR,
            description="Key words or phrases that influenced the sentiment",
            required=False,
            default=[],
        ),
        StructuredOutputField(
            name="reasoning",
            type=FieldType.STR,
            description="Brief explanation of the sentiment classification",
            required=True,
        ),
    ],
)

# Step 2: Generate Pydantic model
SentimentModel = generate_pydantic_model(sentiment_schema)

# Step 3: Set up LLM with structured output
llm = ChatOpenAI(model="gpt-4", temperature=0)
structured_llm = llm.with_structured_output(SentimentModel)

# Step 4: Execute agent with structured output
messages = [
    SystemMessage(
        content="You are a sentiment analysis expert. Analyse the sentiment "
        "of the provided text and return results in the required format."
    ),
    HumanMessage(
        content="The product exceeded my expectations! Great quality and fast delivery."
    ),
]

# Step 5: Get structured response
result = structured_llm.invoke(messages)

# Step 6: Access structured data
print(f"Sentiment: {result.sentiment}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Keywords: {', '.join(result.keywords)}")
print(f"Reasoning: {result.reasoning}")

# Step 7: Convert to JSON for storage or API response
json_output = result.model_dump_json(indent=2)
print(f"\nJSON Output:\n{json_output}")

# Output:
# Sentiment: positive
# Confidence: 0.95
# Keywords: exceeded expectations, great quality, fast delivery
# Reasoning: The text contains multiple positive indicators including...
#
# JSON Output:
# {
#   "sentiment": "positive",
#   "confidence": 0.95,
#   "keywords": ["exceeded expectations", "great quality", "fast delivery"],
#   "reasoning": "The text contains multiple positive indicators..."
# }
```

### Example 4: Schema Validation and Error Handling

Complete example showing proper validation and error handling patterns.

```python
from backend.services.structured_output import (
    validate_schema,
    generate_pydantic_model,
    generate_model_code,
)
from pydantic import ValidationError

def process_user_schema(user_input: dict) -> dict:
    """
    Process user-provided schema with comprehensive validation.

    Args:
        user_input: Schema dictionary from user

    Returns:
        Processing result with status and data or errors
    """

    # Step 1: Validate the schema
    print("Step 1: Validating schema...")
    validation_result = validate_schema(user_input)

    if not validation_result["valid"]:
        return {
            "success": False,
            "stage": "validation",
            "errors": validation_result["errors"],
        }

    print("✓ Schema validation passed")

    # Step 2: Generate code preview
    print("\nStep 2: Generating code preview...")
    try:
        schema = validation_result["schema"]
        code = generate_model_code(schema)
        print("✓ Code preview generated")
        print("\nGenerated Code:")
        print("-" * 60)
        print(code)
        print("-" * 60)
    except Exception as e:
        return {
            "success": False,
            "stage": "code_generation",
            "errors": [f"Code generation failed: {str(e)}"],
        }

    # Step 3: Generate Pydantic model
    print("\nStep 3: Generating Pydantic model...")
    try:
        model = generate_pydantic_model(schema)
        print(f"✓ Model '{model.__name__}' generated successfully")
    except ValueError as e:
        return {
            "success": False,
            "stage": "model_generation",
            "errors": [f"Model generation failed: {str(e)}"],
        }

    # Step 4: Test the model
    print("\nStep 4: Testing model instantiation...")
    try:
        # Try creating a test instance (if possible)
        test_data = {}
        for field_name, field_info in model.model_fields.items():
            if field_info.is_required():
                # Add placeholder for required fields
                test_data[field_name] = "test_value"

        test_instance = model(**test_data)
        print(f"✓ Test instance created: {test_instance}")
    except Exception as e:
        print(f"⚠ Warning: Could not create test instance: {e}")

    # Step 5: Return success
    return {
        "success": True,
        "model_name": model.__name__,
        "schema_id": schema.id,
        "field_count": len(schema.fields),
        "code_preview": code,
    }

# Example usage with valid schema
valid_schema = {
    "id": "customer_001",
    "model_name": "Customer",
    "description": "Customer information",
    "fields": [
        {
            "name": "customerId",
            "type": "str",
            "description": "Unique customer identifier",
            "required": True,
        },
        {
            "name": "email",
            "type": "str",
            "description": "Customer email address",
            "required": True,
        },
        {
            "name": "purchaseHistory",
            "type": "List[str]",
            "description": "List of purchase IDs",
            "required": False,
            "default": [],
        },
    ],
}

print("Processing valid schema...")
result = process_user_schema(valid_schema)
print(f"\nResult: {result['success']}")

# Example with invalid schema
invalid_schema = {
    "id": "bad_001",
    "model_name": "BadModel",
    "fields": [
        {
            "name": "field1",
            "type": "str",
            "description": "First field",
            "required": True,
        },
        {
            "name": "field1",  # Duplicate!
            "type": "int",
            "description": "Duplicate field",
            "required": True,
        },
    ],
}

print("\n\n" + "=" * 60)
print("Processing invalid schema...")
result = process_user_schema(invalid_schema)
print(f"\nResult: {result['success']}")
print(f"Errors: {result.get('errors', [])}")
```

## Performance Considerations

### Performance Characteristics

**Model Generation:**

- Complexity: O(n) where n is the number of fields
- Memory: Minimal - creates a single class definition
- Time: Negligible (<1ms for typical schemas with 10-20 fields)

**Schema Validation:**

- Complexity: O(n × m) where n is number of fields and m is average field name length
- Memory: Minimal - validates in-place
- Time: <1ms for typical schemas

**Code Generation:**

- Complexity: O(n) where n is the number of fields
- Memory: O(n × k) where k is average field metadata length
- Time: <1ms for typical schemas

**Type Mapping:**

- Complexity: O(1) - dictionary lookup
- Memory: Negligible
- Time: Negligible

**I/O Characteristics:**
This is a CPU-bound service with no I/O operations. All operations are in-memory computations.

### Optimisation Tips

#### Tip 1: Cache Generated Models

**Problem:**

```python
# Inefficient: Regenerating model on every request
for request in requests:
    schema = get_schema(request.schema_id)
    model = generate_pydantic_model(schema)  # Regenerates every time
    process_with_model(model, request.data)
```

**Solution:**

```python
# Efficient: Cache generated models by schema ID
from functools import lru_cache
from typing import Type
from pydantic import BaseModel

@lru_cache(maxsize=128)
def get_cached_model(schema_id: str) -> Type[BaseModel]:
    """Get or generate cached Pydantic model."""
    schema = get_schema(schema_id)
    return generate_pydantic_model(schema)

# Use cached models
for request in requests:
    model = get_cached_model(request.schema_id)  # Only generates once
    process_with_model(model, request.data)
```

#### Tip 2: Validate Once, Use Many Times

**Problem:**

```python
# Inefficient: Validating on every use
for execution in executions:
    result = validate_schema(schema_dict)
    if result["valid"]:
        model = generate_pydantic_model(result["schema"])
```

**Solution:**

```python
# Efficient: Validate once at configuration time
# At configuration/save time:
result = validate_schema(schema_dict)
if not result["valid"]:
    raise ValueError(f"Invalid schema: {result['errors']}")

# Store the validated schema
save_to_config(result["schema"])

# At execution time, skip validation:
schema = load_from_config()  # Already validated
model = generate_pydantic_model(schema)  # Direct generation
```

#### Tip 3: Batch Validation

**Problem:**

```python
# Inefficient: Validating schemas one at a time
for schema_dict in schema_dicts:
    result = validate_schema(schema_dict)
    results.append(result)
```

**Solution:**

```python
# Efficient: Batch validation with early exit
def validate_schemas_batch(schema_dicts: list) -> dict:
    """Validate multiple schemas efficiently."""
    results = []
    all_valid = True

    for i, schema_dict in enumerate(schema_dicts):
        result = validate_schema(schema_dict)
        results.append(result)

        if not result["valid"]:
            all_valid = False
            # Can exit early if needed
            if stop_on_first_error:
                break

    return {
        "all_valid": all_valid,
        "results": results,
    }
```

### Async/Await Support

This service does not natively support async operations as all operations are CPU-bound and complete in <1ms. However,
it integrates seamlessly with async code:

```python
from backend.services.structured_output import generate_pydantic_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

async def execute_with_structured_output_async(
    llm: BaseChatModel,
    messages: list[BaseMessage],
    schema: StructuredOutputSchema,
) -> Any:
    """Execute LLM with structured output asynchronously."""

    # Model generation is synchronous (fast, CPU-bound)
    model = generate_pydantic_model(schema)

    # Apply to LLM
    structured_llm = llm.with_structured_output(model)

    # Use async LLM invocation (I/O-bound)
    response = await structured_llm.ainvoke(messages)

    return response
```

### Connection Pooling

Not applicable - this service does not manage connections.

### Batch Operations

Not applicable - operations are already optimised for individual schema processing. If batch processing is needed, use
standard Python iteration with optional caching as shown in optimisation tips.

## Testing Patterns

### Unit Testing

```python
import pytest
from pydantic import BaseModel

from backend.services.structured_output import (
    generate_pydantic_model,
    validate_schema,
    generate_model_code,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)


class TestStructuredOutputService:
    """Unit tests for structured output service."""

    @pytest.fixture
    def simple_schema(self):
        """Fixture providing a simple valid schema."""
        return StructuredOutputSchema(
            id="test_001",
            model_name="TestModel",
            description="Test schema",
            fields=[
                StructuredOutputField(
                    name="field1",
                    type=FieldType.STR,
                    description="Test field",
                    required=True,
                )
            ],
        )

    def test_generate_pydantic_model_success(self, simple_schema):
        """Test successful model generation."""
        model = generate_pydantic_model(simple_schema)

        assert model is not None
        assert model.__name__ == "TestModel"
        assert issubclass(model, BaseModel)
        assert "field1" in model.model_fields

    def test_generate_pydantic_model_invalid_name(self):
        """Test model generation with invalid model name."""
        schema = StructuredOutputSchema(
            id="test_002",
            model_name="invalidName",  # Should start with uppercase
            fields=[
                StructuredOutputField(
                    name="field1",
                    type=FieldType.STR,
                    description="Test",
                    required=True,
                )
            ],
        )

        with pytest.raises(ValueError, match="Invalid model name"):
            generate_pydantic_model(schema)

    def test_validate_schema_success(self):
        """Test successful schema validation."""
        schema_dict = {
            "id": "test_003",
            "model_name": "ValidModel",
            "fields": [
                {
                    "name": "field1",
                    "type": "str",
                    "description": "Test field",
                    "required": True,
                }
            ],
        }

        result = validate_schema(schema_dict)

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["schema"] is not None

    def test_validate_schema_duplicate_fields(self):
        """Test schema validation with duplicate field names."""
        schema_dict = {
            "id": "test_004",
            "model_name": "DuplicateModel",
            "fields": [
                {"name": "field1", "type": "str", "description": "First", "required": True},
                {"name": "field1", "type": "int", "description": "Duplicate", "required": True},
            ],
        }

        result = validate_schema(schema_dict)

        assert result["valid"] is False
        assert any("Duplicate field name" in err for err in result["errors"])

    def test_generate_model_code(self, simple_schema):
        """Test code generation."""
        code = generate_model_code(simple_schema)

        assert "class TestModel(BaseModel):" in code
        assert "from pydantic import BaseModel, Field" in code
        assert "field1: str" in code

    def test_model_with_optional_fields(self):
        """Test model generation with optional fields."""
        schema = StructuredOutputSchema(
            id="test_005",
            model_name="OptionalModel",
            fields=[
                StructuredOutputField(
                    name="required_field",
                    type=FieldType.STR,
                    description="Required",
                    required=True,
                ),
                StructuredOutputField(
                    name="optional_field",
                    type=FieldType.OPTIONAL_STR,
                    description="Optional",
                    required=False,
                    default=None,
                ),
            ],
        )

        model = generate_pydantic_model(schema)

        # Should work with only required field
        instance = model(required_field="test")
        assert instance.required_field == "test"
        assert instance.optional_field is None

        # Should work with both fields
        instance2 = model(required_field="test", optional_field="optional")
        assert instance2.optional_field == "optional"
```

### Mocking Dependencies

```python
import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.services.structured_output import (
    StructuredOutputGenerator,
    generate_pydantic_model,
)


def test_with_mocked_pydantic_create_model():
    """Test model generation with mocked Pydantic create_model."""

    with patch("backend.services.structured_output.generator.create_model") as mock_create:
        # Setup mock
        mock_model = MagicMock()
        mock_model.__name__ = "MockedModel"
        mock_create.return_value = mock_model

        # Create schema
        from backend.services.structured_output import (
            StructuredOutputSchema,
            StructuredOutputField,
            FieldType,
        )

        schema = StructuredOutputSchema(
            id="test_001",
            model_name="TestModel",
            fields=[
                StructuredOutputField(
                    name="field1",
                    type=FieldType.STR,
                    description="Test",
                    required=True,
                )
            ],
        )

        # Generate model
        result = generate_pydantic_model(schema)

        # Verify mock was called
        assert mock_create.called
        assert result == mock_model


@patch("backend.services.structured_output.validators.validate_model_name")
@patch("backend.services.structured_output.validators.validate_fields")
def test_with_mocked_validators(mock_validate_fields, mock_validate_model_name):
    """Test with mocked validation functions."""

    # Setup mocks
    mock_validate_model_name.return_value = True
    mock_validate_fields.return_value = []  # No errors

    from backend.services.structured_output import (
        StructuredOutputSchema,
        StructuredOutputField,
        FieldType,
        generate_pydantic_model,
    )

    schema = StructuredOutputSchema(
        id="test_002",
        model_name="TestModel",
        fields=[
            StructuredOutputField(
                name="field1",
                type=FieldType.STR,
                description="Test",
                required=True,
            )
        ],
    )

    # Should succeed with mocked validators
    model = generate_pydantic_model(schema)

    # Verify validators were called
    assert mock_validate_model_name.called
    assert mock_validate_fields.called
```

### Integration Testing

```python
import pytest
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.structured_output import (
    generate_pydantic_model,
    StructuredOutputSchema,
    StructuredOutputField,
    FieldType,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_with_langchain():
    """Integration test with actual LangChain LLM."""

    # Create schema
    schema = StructuredOutputSchema(
        id="integration_001",
        model_name="SentimentResult",
        description="Sentiment analysis result",
        fields=[
            StructuredOutputField(
                name="sentiment",
                type=FieldType.STR,
                description="Sentiment: positive, negative, or neutral",
                required=True,
            ),
            StructuredOutputField(
                name="confidence",
                type=FieldType.FLOAT,
                description="Confidence score 0-1",
                required=True,
            ),
        ],
    )

    # Generate model
    model = generate_pydantic_model(schema)

    # Set up LLM (requires API key in environment)
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    structured_llm = llm.with_structured_output(model)

    # Execute
    messages = [
        SystemMessage(content="Analyse sentiment."),
        HumanMessage(content="This product is amazing!"),
    ]

    result = await structured_llm.ainvoke(messages)

    # Verify result conforms to model
    assert hasattr(result, "sentiment")
    assert hasattr(result, "confidence")
    assert result.sentiment in ["positive", "negative", "neutral"]
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.integration
def test_integration_with_agent_handler():
    """Integration test with agent execution handler."""

    from backend.services.execution.agent.structured_output_handler import (
        StructuredOutputHandler,
    )

    # Schema dictionary as would come from API
    schema_dict = {
        "id": "handler_test_001",
        "model_name": "TestOutput",
        "description": "Test output",
        "fields": [
            {
                "name": "result",
                "type": "str",
                "description": "Result text",
                "required": True,
            }
        ],
    }

    # Use handler to get model
    model = StructuredOutputHandler.get_pydantic_model(schema_dict)

    # Verify model is correct
    assert model.__name__ == "TestOutput"
    assert "result" in model.model_fields

    # Verify instance creation works
    instance = model(result="test value")
    assert instance.result == "test value"
```

## Best Practices

### Do's

✅ **Always validate schemas before model generation**

```python
from backend.services.structured_output import validate_schema, generate_pydantic_model

# Validate first
result = validate_schema(schema_dict)
if result["valid"]:
    model = generate_pydantic_model(result["schema"])
else:
    handle_errors(result["errors"])
```

✅ **Use descriptive field descriptions for better LLM understanding**

```python
StructuredOutputField(
    name="customerEmail",
    type=FieldType.STR,
    description="Customer's email address in valid format (e.g., user@example.com)",
    required=True,
)
```

✅ **Cache generated models when using the same schema repeatedly**

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_model_for_schema(schema_id: str):
    schema = load_schema(schema_id)
    return generate_pydantic_model(schema)
```

✅ **Use appropriate field types for data validation**

```python
# Use Optional types for truly optional fields
StructuredOutputField(
    name="middleName",
    type=FieldType.OPTIONAL_STR,
    description="Middle name (if applicable)",
    required=False,
    default=None,
)

# Use lists for collections
StructuredOutputField(
    name="tags",
    type=FieldType.LIST_STR,
    description="Product tags",
    required=False,
    default=[],
)
```

✅ **Provide meaningful model and field names**

```python
# Good: PascalCase for model names
model_name="CustomerInformation"

# Good: camelCase for field names
field_name="emailAddress"

# Bad: Unclear names
model_name="Data"
field_name="x"
```

✅ **Handle validation errors gracefully in production**

```python
try:
    model = generate_pydantic_model(schema)
except ValueError as e:
    logger.error(f"Schema validation failed: {e}")
    return {"success": False, "error": "Invalid schema configuration"}
```

### Don'ts

❌ **Don't skip schema validation**

```python
# Bad: Skipping validation can cause runtime errors
model = generate_pydantic_model(untrusted_schema)

# Good: Always validate
result = validate_schema(schema_dict)
if result["valid"]:
    model = generate_pydantic_model(result["schema"])
```

❌ **Don't use invalid Python identifiers for names**

```python
# Bad: Invalid field names
StructuredOutputField(name="123invalid", ...)  # Starts with number
StructuredOutputField(name="my-field", ...)    # Contains hyphen
StructuredOutputField(name="_private", ...)    # Starts with underscore

# Good: Valid identifiers
StructuredOutputField(name="field123", ...)
StructuredOutputField(name="myField", ...)
StructuredOutputField(name="publicField", ...)
```

❌ **Don't regenerate models unnecessarily**

```python
# Bad: Regenerating in a loop
for item in items:
    model = generate_pydantic_model(schema)  # Wasteful!
    instance = model(**item)

# Good: Generate once, reuse
model = generate_pydantic_model(schema)
for item in items:
    instance = model(**item)
```

❌ **Don't ignore validation errors**

```python
# Bad: Ignoring validation results
result = validate_schema(schema_dict)
model = generate_pydantic_model(schema_dict)  # Might fail!

# Good: Check validation results
result = validate_schema(schema_dict)
if result["valid"]:
    model = generate_pydantic_model(result["schema"])
else:
    logger.error(f"Validation failed: {result['errors']}")
    raise ValueError("Invalid schema")
```

❌ **Don't use mismatched default values**

```python
# Bad: Default value doesn't match type
StructuredOutputField(
    name="count",
    type=FieldType.INT,
    description="Count",
    required=False,
    default="not a number",  # Type mismatch!
)

# Good: Correct default type
StructuredOutputField(
    name="count",
    type=FieldType.INT,
    description="Count",
    required=False,
    default=0,
)
```

❌ **Don't create schemas with no fields**

```python
# Bad: Empty schema
schema = StructuredOutputSchema(
    id="empty_001",
    model_name="EmptyModel",
    fields=[],  # No fields!
)

# Good: At least one field
schema = StructuredOutputSchema(
    id="minimal_001",
    model_name="MinimalModel",
    fields=[
        StructuredOutputField(
            name="value",
            type=FieldType.STR,
            description="Value",
            required=True,
        )
    ],
)
```

## Related Documentation

### Related Services

- [Execution Service](./execution.md) - Uses structured output for agent response formatting
- [Agent Service](./agent.md) - Integrates structured output in agent compilation
- [Graph Service](./graph.md) - Stores structured output configurations in workflow definitions

### Related API Modules

- [Graph API](../agents-guide/api/graph.md) - Provides endpoints for structured output validation and preview

### Architecture Documentation

- System Architecture - Overview of AgenticStudio architecture and service interactions
- LangGraph Integration - How structured outputs work with LangGraph's `with_structured_output()`

### External Documentation

- [Pydantic Documentation](https://docs.pydantic.dev/) - Underlying model validation library
- [LangChain Structured Output](https://python.langchain.com/docs/how_to/structured_output/) - LangChain integration
  patterns

## Summary

The structured output service provides essential functionality for creating type-safe, validated structured responses
from LLM agents in the AgenticStudio platform. By dynamically generating Pydantic models from user-defined schemas, it
enables consistent and predictable agent outputs that can be reliably processed by downstream systems.

The service follows a modular architecture with clear separation of concerns: schema definitions, type mapping,
validation, model generation, and code preview. This design makes the codebase maintainable, testable, and easy to
extend with new field types or validation rules.

**Key Features:**

- Dynamic Pydantic model generation from schema definitions
- Comprehensive validation of schemas, field names, and default values
- Python code preview generation for debugging and documentation
- Support for basic types, optional types, lists, and dictionaries
- Strict JSON schema generation with `additionalProperties: false`
- Integration with LangGraph's `with_structured_output()` method

**Primary Use Cases:**

- Enforcing structured response formats for LLM agents
- Validating user-defined output schemas before workflow execution
- Generating runtime Pydantic models for agent responses
- Providing code previews and documentation for debugging
- Ensuring type safety and data consistency across workflow executions

**When to Use This Service:**

- When you need LLM agents to return data in a specific, predictable format
- When downstream systems require structured JSON responses
- When you need to validate or transform LLM outputs
- When building workflows that process agent responses programmatically
- When you want to provide users with visual schema editors and previews
