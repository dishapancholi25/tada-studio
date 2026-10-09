# I/O Service Module

## Overview

The I/O (Input/Output) service module provides comprehensive data processing capabilities for workflow execution in
AgenticStudio. It handles building node inputs from various sources, processing workflow outputs with flexible formatting,
extracting fields from structured data, and maintaining real-time execution state tracking.

**Location:** `backend/services/io/`

**Primary Responsibilities:**

- Building node inputs from multiple sources (start, previous, specific nodes, custom templates)
- Processing END node outputs with configurable formatting
- Extracting fields from structured node outputs using field paths
- Processing template strings with variable substitution
- Tracking real-time state updates during workflow execution
- Extracting values for database column and parameter mappings

**Key Use Cases:**

- Constructing input messages for agent and tool nodes
- Formatting final workflow results according to END node configuration
- Extracting specific fields from node outputs for downstream processing
- Applying dynamic templates with workflow state variables
- Providing real-time execution tracking for WebSocket updates

## Architecture

### Module Structure

```
backend/services/io/
├── __init__.py                  # Public API exports
├── input_builder.py             # Legacy InputBuilder (delegates to executor)
├── output_processor.py          # END node output formatting
├── template_processor.py        # Template variable substitution
├── state_processor.py           # Real-time state tracking
├── extractors/                  # Field extraction utilities
│   ├── __init__.py
│   ├── field.py                 # FieldExtractor - main field extraction
│   ├── nested.py                # NestedFieldExtractor - dot notation
│   ├── mapping.py               # MappingValueExtractor - column mappings
│   └── final.py                 # FinalOutputExtractor - final output
└── input/                       # Complete input building (newer)
    ├── __init__.py
    ├── builder.py               # Complete InputBuilder implementation
    ├── sources.py               # Input source handlers
    └── combiners.py             # Multi-source combination
```

**File Descriptions:**

- **input_builder.py**: Simple wrapper that delegates to the execution engine's `_build_node_input` method for backwards
  compatibility during refactoring
- **output_processor.py**: Formats END node output based on configuration (full, summary, compact, custom structures)
- **template_processor.py**: Processes template strings containing `{{variable}}` placeholders with values from workflow
  state
- **state_processor.py**: Processes state updates for real-time execution tracking and WebSocket events
- **extractors/field.py**: Extracts fields from complex node outputs using field paths
- **extractors/nested.py**: Extracts nested fields using dot notation (e.g., "user.profile.name")
- **extractors/mapping.py**: Extracts values for database column/parameter mappings from various sources
- **extractors/final.py**: Extracts the final output from completed workflow state
- **input/builder.py**: Complete input building implementation supporting multiple sources and combination strategies
- **input/sources.py**: Handler classes for different input sources (start, previous, specific, custom, field)
- **input/combiners.py**: Utilities for combining inputs from multiple sources

### Design Patterns

**Strategy Pattern**: Input sources use the Strategy pattern with an `InputSource` base class and concrete
implementations for each source type (start, previous, specific, custom, field).

**Extractor Pattern**: Multiple extractor classes (`FieldExtractor`, `NestedFieldExtractor`, `MappingValueExtractor`,
`FinalOutputExtractor`) encapsulate field extraction logic with single responsibility.

**Template Method Pattern**: `OutputProcessor` uses static methods to build different output structures, with
`_build_output` routing to specific builders based on configuration.

**Dependency Injection**: Components accept dependencies through constructors:

- `TemplateProcessor` uses `FieldExtractor`
- `InputBuilder` (new version) accepts `FieldExtractor`
- `StateProcessor` accepts `active_executions` dictionary

### Integration with Broader System

The I/O service module integrates with the execution engine as a core component:

```
ExecutionEngine
├── StateProcessor (tracks execution state)
├── TemplateProcessor (processes templates)
├── FieldExtractor (extracts fields)
├── MappingValueExtractor (extracts mapping values)
└── InputBuilder (builds node inputs)
```

**Component Relationships:**

```
┌─────────────────────────────────────────────────────┐
│           Execution Engine                          │
│  ┌────────────────────────────────────────────┐    │
│  │  Node Execution                             │    │
│  │  ┌──────────────┐    ┌──────────────────┐ │    │
│  │  │ InputBuilder │───▶│  Node Function   │ │    │
│  │  └──────────────┘    └──────────────────┘ │    │
│  │         │                      │           │    │
│  │         ▼                      ▼           │    │
│  │  ┌──────────────┐    ┌──────────────────┐ │    │
│  │  │   Extractors │    │ StateProcessor   │ │    │
│  │  └──────────────┘    └──────────────────┘ │    │
│  │                              │             │    │
│  │                              ▼             │    │
│  │                     ┌──────────────────┐  │    │
│  │                     │ OutputProcessor  │  │    │
│  │                     └──────────────────┘  │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**Data Flow:**

1. Workflow starts → `InputBuilder` constructs first node's input
2. Node executes → `StateProcessor` tracks state updates
3. Node completes → Output stored in state with extractable fields
4. Next node → `InputBuilder` + `FieldExtractor` build input from previous output
5. Workflow completes → `OutputProcessor` formats final result
6. Throughout → `TemplateProcessor` handles `{{variable}}` substitutions

### Dependencies

**Internal Dependencies:**

- `backend.models.workflow`: `EnhancedNodeData`, `GraphData`, `EndNodeConfig`, `NodeType`
- `backend.services.workflow.state`: `WorkflowState` (TypedDict for state management)
- `backend.services.config`: `get_logger()` for logging
- `backend.services.execution`: `get_executor()` for legacy delegation

**External Dependencies:**

- `langchain_core.messages`: `HumanMessage`, `AIMessage` for message handling
- `re`: Standard library for regex pattern matching (template variables)
- `typing`: Type hints (`Any`, `Dict`, `List`, `Optional`, `TYPE_CHECKING`)

**Database Dependencies:**
None directly. The I/O service operates on in-memory state and passes extracted values to node executors that interact
with databases.

**Environment Variables and Configuration:**
No environment variables. Configuration comes from:

- Node configurations (`input_source_config`, `end_node_config`)
- Workflow state
- Logger configuration from `backend.services.config`

## Public API

### Exported Classes

- `InputBuilder` - Builds input messages for node execution from various sources
- `OutputProcessor` - Processes END node output with configurable formatting
- `TemplateProcessor` - Processes template strings with `{{variable}}` substitution
- `StateProcessor` - Processes state updates for real-time execution tracking
- `FieldExtractor` - Extracts fields from node output using field paths
- `NestedFieldExtractor` - Extracts nested fields using dot notation
- `MappingValueExtractor` - Extracts values for column/parameter mappings
- `FinalOutputExtractor` - Extracts final output from workflow state

### Exported Functions

None. The module exports only classes.

### Constants and Configuration

No exported constants. Configuration is provided through:

- `EndNodeConfig` dataclass (from `backend.models.workflow`)
- Node input source configurations
- Workflow state dictionaries

### Exceptions

The I/O service module does not define custom exceptions. It relies on:

- Standard Python exceptions (`KeyError`, `AttributeError`, `TypeError`)
- LangChain exceptions for message handling
- Execution engine exceptions for workflow errors

## Core Classes

### `InputBuilder`

Builds input data for node execution from various sources.

**Purpose:** Construct the input message that a node receives during workflow execution. This can come from the workflow
start, previous node outputs, specific nodes, custom templates, or extracted fields.

**Responsibilities:**

- Extract input from workflow start (original message)
- Extract input from previous node's output
- Extract input from specific node(s)
- Apply custom templates with variable substitution
- Extract fields from workflow state
- Integrate memory context into input

**Note:** The module exports two versions:

- Legacy version in `input_builder.py` (delegates to execution engine)
- Complete version in `input/builder.py` (full implementation)

The legacy version is exported from `__init__.py` for backwards compatibility.

**Initialisation:**

```python
def __init__(self, field_extractor: Any = None) -> None:
    """
    Initialise input builder.

    Args:
        field_extractor: Optional FieldExtractor for structured data extraction
    """
```

**Key Methods:**

#### `build()`

```python
def build(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    graph: GraphData,
) -> str:
    """Build input message for a node."""
```

**Parameters:**

- `node` (EnhancedNodeData) - The node to build input for
- `state` (WorkflowState) - Current workflow state containing messages, node outputs, and execution context
- `graph` (GraphData) - The graph definition with nodes and connections

**Returns:**

- `str` - Input message string ready for node execution

**Raises:**
No specific exceptions. May raise `KeyError` if state is malformed.

**Example:**

```python
from backend.services.io import InputBuilder
from backend.services.workflow.state import WorkflowState

# Initialise builder
builder = InputBuilder()

# Build input for a node
input_message = builder.build(
    node=current_node,
    state=workflow_state,
    graph=graph_data,
)

# Use the input in node execution
result = node.execute(input_message)
```

**Behaviour:**

- If `node.input_source_config` is None, defaults to "previous" mode
- Reads `source_mode` from config to determine input source
- Routes to appropriate source handler based on mode
- Returns empty string if source extraction fails
- Logs configuration and extraction details for debugging

**Use Cases:**

- Building input for agent nodes that need context from previous outputs
- Starting workflow execution with the original user message
- Passing specific node outputs to database or tool nodes
- Applying custom message templates with dynamic content

#### `build_with_memory()`

```python
def build_with_memory(
    self,
    node: EnhancedNodeData,
    state: WorkflowState,
    graph: GraphData,
    memory_context: str = "",
) -> str:
    """Build input message with memory context prepended."""
```

**Parameters:**

- `node` (EnhancedNodeData) - The node to build input for
- `state` (WorkflowState) - Current workflow state
- `graph` (GraphData) - The graph definition
- `memory_context` (str) - Memory context to prepend to input (default: "")

**Returns:**

- `str` - Input message with memory context prepended

**Raises:**
No specific exceptions.

**Example:**

```python
from backend.services.io import InputBuilder

builder = InputBuilder()

# Build input with conversation history
memory_context = "Previous conversation:\nUser: Hello\nAI: Hi there!"
input_message = builder.build_with_memory(
    node=agent_node,
    state=workflow_state,
    graph=graph_data,
    memory_context=memory_context,
)

# Result: "{memory_context}\n\nCurrent Message: {input_message}"
```

**Behaviour:**

- Calls `build()` to get base input message
- If `memory_context` is provided, prepends it with "\n\nCurrent Message: " separator
- Logs when memory context is applied

**Use Cases:**

- Adding conversation history to agent inputs
- Providing context from previous workflow executions
- Implementing memory-aware agents

**Class Attributes:**

- `field_extractor: FieldExtractor` - Field extractor for structured data (complete version only)
- `start_source: StartInputSource` - Handler for start input source (complete version only)
- `previous_source: PreviousInputSource` - Handler for previous input source (complete version only)
- `specific_source: SpecificNodeInputSource` - Handler for specific node input (complete version only)
- `custom_source: CustomTemplateInputSource` - Handler for custom templates (complete version only)
- `field_source: FieldInputSource` - Handler for field extraction (complete version only)

---

### `OutputProcessor`

Processes END node output according to configuration.

**Purpose:** Format workflow execution results for return to the caller. Supports multiple output structures (full,
summary, compact, custom) and filtering by node selection.

**Responsibilities:**

- Filter node outputs based on input source configuration
- Format outputs according to structure configuration (full/summary/compact/custom)
- Add execution metadata when configured
- Include or exclude node names as configured
- Handle backwards compatibility with legacy output format

**Initialisation:**

This class uses only static methods and does not require initialisation.

**Key Methods:**

#### `process()`

```python
@staticmethod
def process(
    state: WorkflowState,
    end_node: EnhancedNodeData,
    graph: GraphData,
) -> Dict[str, Any]:
    """Process END node output based on configuration."""
```

**Parameters:**

- `state` (WorkflowState) - Current workflow state containing node outputs and results
- `end_node` (EnhancedNodeData) - The END node with configuration
- `graph` (GraphData) - The graph definition with nodes and connections

**Returns:**

- `Dict[str, Any]` - Formatted output dictionary respecting EndNodeConfig settings

**Raises:**
No specific exceptions. May raise `KeyError` if state is malformed.

**Example:**

```python
from backend.services.io import OutputProcessor
from backend.models.workflow import EndNodeConfig

# Configure END node for summary output
end_node.end_node_config = EndNodeConfig(
    input_source="all",
    output_structure="summary",
    include_metadata=True,
    include_node_names=True,
)

# Process final output
final_output = OutputProcessor.process(
    state=workflow_state,
    end_node=end_node,
    graph=graph_data,
)

# Result structure depends on configuration:
# "summary" -> [{"node": "Node1", "response": "...", "tools_used": 2}, ...]
# "compact" -> {"Node1": "response1", "Node2": "response2"}
# "full" -> {"nodes": [{"node": "Node1", "response": "...", "structured": {...}, "fields": {...}, "tools": [...]}]}
```

**Behaviour:**

- Reads `EndNodeConfig` from `end_node.end_node_config` or uses defaults
- Filters node outputs based on `input_source` setting:
  - "all": All node outputs
  - "previous": Nodes directly connected to END node
  - "specific"/"multiple": Nodes specified in `source_node_ids`
- Builds output based on `output_structure` setting:
  - "full": Comprehensive with all node details, structured data, fields, tools
  - "summary": Simplified with node names, responses, tool usage counts
  - "compact": Minimal dictionary mapping node names to responses
  - "custom": Falls back to legacy format `{"results": [...], "node_outputs": {...}}`
- Adds metadata if `include_metadata` is True
- Uses node names or IDs based on `include_node_names` setting

**Use Cases:**

- Formatting API responses from workflow executions
- Extracting specific node outputs for downstream processing
- Providing comprehensive execution details for debugging
- Creating minimal responses for efficient data transfer

#### Internal Methods

The `OutputProcessor` includes several internal static methods for processing:

- `_get_config()` - Extract or create EndNodeConfig from node
- `_filter_nodes()` - Filter node IDs based on input_source configuration
- `_build_output()` - Route to appropriate output builder
- `_build_full_output()` - Build comprehensive output structure
- `_build_summary_output()` - Build simplified summary
- `_build_compact_output()` - Build minimal output dictionary
- `_add_metadata()` - Add execution metadata to output

These are implementation details not intended for external use.

---

### `TemplateProcessor`

Processes template strings with `{{variable}}` placeholders.

**Purpose:** Replace template variables with values from workflow state. Supports special variables like `{{message}}`
and `{{original_message}}` as well as direct state fields and node output fields.

**Responsibilities:**

- Find all `{{variable}}` patterns in template strings
- Extract values for special variables (message, original_message)
- Extract values from direct state fields
- Extract values from node output fields
- Replace placeholders with extracted values

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise the template processor."""
```

**Key Methods:**

#### `process()`

```python
def process(
    self,
    template: str,
    state: WorkflowState,
) -> str:
    """Replace {{variable}} templates with values from state."""
```

**Parameters:**

- `template` (str) - Template string with `{{variable}}` placeholders
- `state` (WorkflowState) - Current workflow state

**Returns:**

- `str` - String with variables replaced with values

**Raises:**
No specific exceptions.

**Example:**

```python
from backend.services.io import TemplateProcessor

processor = TemplateProcessor()

# Template with multiple variable types
template = """
Process this request: {{message}}

Original input was: {{original_message}}

User ID: {{user_id}}
Country: {{Country}}
"""

# Process with state
result = processor.process(template, workflow_state)

# Result:
# """
# Process this request: What's the weather?
#
# Original input was: Hello, I need weather information
#
# User ID: 12345
# Country: Australia
# """
```

**Behaviour:**

- Uses regex pattern `r"\{\{(\w+)\}\}"` to find template variables
- Processes special variables first:
  - `{{message}}`: Last message content from state
  - `{{original_message}}`: First message content from state
- Checks direct state fields next (e.g., `{{user_id}}`)
- Searches node outputs for fields last (e.g., `{{Country}}`)
- Returns empty string for variables not found
- Preserves template structure, only replaces variables

**Use Cases:**

- Creating dynamic prompts with workflow context
- Formatting output messages with extracted data
- Building parameterised queries with state values
- Constructing custom messages from multiple sources

#### Internal Methods

- `_find_template_variables()` - Find all `{{variable}}` patterns using regex
- `_extract_variable_value()` - Route variable extraction to appropriate method
- `_extract_last_message()` - Extract last message from state
- `_extract_first_message()` - Extract first message from state
- `_extract_from_node_outputs()` - Search node outputs for field

**Properties:**

- `field_extractor: FieldExtractor` - Used to extract fields from node outputs

---

### `StateProcessor`

Processes state updates for real-time workflow tracking.

**Purpose:** Update active execution tracking and prepare data for WebSocket events during workflow execution.

**Responsibilities:**

- Process state update dictionaries from workflow execution
- Update current node tracking in active executions
- Update metadata in active executions
- Guard against invalid state updates (non-dict types)
- Log state changes for debugging

**Initialisation:**

```python
def __init__(self, active_executions: Dict[str, Any]) -> None:
    """
    Initialise the state processor.

    Args:
        active_executions: Dictionary tracking active executions
    """
```

**Key Methods:**

#### `process_update()`

```python
async def process_update(
    self,
    state_update: Dict[str, Any],
    execution_id: str,
    db_execution_id: Optional[int],
) -> None:
    """Process state updates for real-time tracking."""
```

**Parameters:**

- `state_update` (Dict[str, Any]) - State update data from workflow execution
- `execution_id` (str) - Execution identifier (UUID)
- `db_execution_id` (Optional[int]) - Optional database execution ID

**Returns:**

- `None` - Updates `active_executions` in place

**Raises:**
No specific exceptions. Guards against non-dict state updates.

**Example:**

```python
from backend.services.io import StateProcessor

# Initialise with active executions tracker
active_executions = {}
processor = StateProcessor(active_executions)

# Track new execution
execution_id = "exec-123"
active_executions[execution_id] = {
    "current_node": None,
    "current_node_name": None,
}

# Process state update
await processor.process_update(
    state_update={
        "current_node": "node-456",
        "metadata": {"current_node_name": "Agent Node 1"},
    },
    execution_id=execution_id,
    db_execution_id=789,
)

# active_executions now updated:
# {
#     "exec-123": {
#         "current_node": "node-456",
#         "current_node_name": "Agent Node 1"
#     }
# }
```

**Behaviour:**

- Checks if `state_update` is a dictionary; skips non-dict updates
- Only processes updates for tracked executions (checks `execution_id in active_executions`)
- Updates `current_node` if present in state_update
- Updates `current_node_name` from metadata if present
- Logs debug information about state updates
- Does not raise errors for missing or malformed data

**Use Cases:**

- Real-time workflow execution tracking
- Providing current node information to WebSocket clients
- Debugging workflow execution state transitions
- Preparing data for execution progress events

#### Internal Methods

- `_update_current_node()` - Update current_node in execution tracking
- `_update_metadata()` - Update metadata fields in execution tracking

**Class Attributes:**

- `active_executions: Dict[str, Any]` - Dictionary tracking active executions

---

### `FieldExtractor`

Extracts fields from node output using field paths.

**Purpose:** Extract specific fields from complex node outputs that may contain raw responses, structured data, and
extracted fields.

**Responsibilities:**

- Handle complex node outputs with multiple data locations
- Extract fields using simple names or nested paths
- Try multiple extraction strategies (structured, fields, direct)
- Return default values when extraction fails
- Integrate with NestedFieldExtractor for dot notation

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise the field extractor."""
```

**Key Methods:**

#### `extract()`

```python
def extract(
    self,
    output: Any,
    field_path: Optional[str],
    default_value: Any = None,
) -> Any:
    """Extract a field from node output using a field path."""
```

**Parameters:**

- `output` (Any) - The node output (typically dict with "raw", "structured", "fields" keys)
- `field_path` (Optional[str]) - Path to field (e.g., "Country" or "data.user.name")
- `default_value` (Any) - Default value if extraction fails (default: None)

**Returns:**

- `Any` - The extracted value or default_value

**Raises:**
No specific exceptions.

**Example:**

```python
from backend.services.io import FieldExtractor

extractor = FieldExtractor()

# Node output structure
node_output = {
    "raw": "User John Smith lives in Australia",
    "structured": {
        "name": "John Smith",
        "country": "Australia"
    },
    "fields": {
        "Country": "Australia",
        "Name": "John Smith"
    }
}

# Extract simple field
country = extractor.extract(node_output, "Country", "Unknown")
# Returns: "Australia"

# Extract nested field
name = extractor.extract(node_output, "structured.name", "Unknown")
# Returns: "John Smith"

# Extract whole output (no field path)
whole = extractor.extract(node_output, None, "")
# Returns: "User John Smith lives in Australia" (the raw content)

# Extract non-existent field
age = extractor.extract(node_output, "age", 0)
# Returns: 0 (default value)
```

**Behaviour:**

- If `field_path` is None/empty, extracts whole output (tries "raw", then "structured")
- For dict outputs, tries extraction in order:
    1. From `output["structured"]` using nested extraction
    2. From `output["fields"]` using nested extraction
    3. Direct field access using nested extraction
- Returns `default_value` if all extraction attempts fail
- Uses `NestedFieldExtractor` for handling dot notation paths
- Does not raise exceptions; returns default on failure

**Use Cases:**

- Extracting structured data from LLM responses
- Getting specific fields for database inserts
- Accessing nested data structures from complex outputs
- Providing fallback values when fields are missing

#### Internal Methods

- `_extract_whole_output()` - Extract entire output when no field path specified
- `_extract_from_dict_output()` - Try multiple extraction strategies for dict outputs

**Properties:**

- `nested_extractor: NestedFieldExtractor` - Used for nested path extraction

---

### `NestedFieldExtractor`

Extracts nested fields from dictionaries using dot notation.

**Purpose:** Navigate nested dictionary structures using dot-separated paths like "user.profile.name".

**Responsibilities:**

- Parse dot-separated field paths
- Traverse nested dictionaries
- Return None for invalid paths or non-dict data
- Prevent returning dictionaries (only primitive values)

**Initialisation:**

This class uses only static methods and does not require initialisation.

**Key Methods:**

#### `extract()`

```python
@staticmethod
def extract(data: Any, field_path: str) -> Optional[Any]:
    """Extract a nested field from a dict using dot notation."""
```

**Parameters:**

- `data` (Any) - The data to extract from (should be dict)
- `field_path` (str) - Dot-separated path (e.g., "user.profile.name")

**Returns:**

- `Optional[Any]` - The extracted value or None if not found

**Raises:**
No exceptions. Returns None on failure.

**Example:**

```python
from backend.services.io import NestedFieldExtractor

# Nested data structure
data = {
    "user": {
        "profile": {
            "name": "John Smith",
            "age": 30
        },
        "email": "john@example.com"
    },
    "status": "active"
}

# Extract nested fields
name = NestedFieldExtractor.extract(data, "user.profile.name")
# Returns: "John Smith"

email = NestedFieldExtractor.extract(data, "user.email")
# Returns: "john@example.com"

status = NestedFieldExtractor.extract(data, "status")
# Returns: "active"

# Non-existent path
invalid = NestedFieldExtractor.extract(data, "user.profile.address")
# Returns: None

# Attempting to extract dict (prevented)
profile = NestedFieldExtractor.extract(data, "user.profile")
# Returns: None (dicts cannot be inserted into DB)
```

**Behaviour:**

- Returns None if `data` is not a dictionary
- Splits `field_path` by "." to get path components
- Traverses dictionary following path components
- Returns None if any path component is missing
- Returns None if final value is a dictionary (prevents dict insertion issues)
- Returns primitive values (strings, numbers, booleans, lists of primitives)

**Use Cases:**

- Accessing deeply nested API response data
- Extracting values from structured LLM outputs
- Navigating complex configuration objects
- Retrieving database-compatible primitive values

---

### `MappingValueExtractor`

Extracts values for column/parameter mappings from various sources.

**Purpose:** Support database nodes and other nodes that need to map values from different sources (static, previous
node, specific nodes, workflow start) to columns or parameters.

**Responsibilities:**

- Extract static values (including SQL functions)
- Extract from previous node output
- Extract from specific node with field path
- Extract from workflow start message
- Track SQL expression indices
- Normalise SQL function names

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise the mapping value extractor."""
```

**Key Methods:**

#### `extract()`

```python
def extract(
    self,
    source_mode: str,
    state: WorkflowState,
    static_value: Any = None,
    default_value: Any = None,
    source_node_id: Optional[str] = None,
    source_field_path: Optional[str] = None,
    idx: int = 0,
    sql_expressions: Optional[List[int]] = None,
) -> Any:
    """Extract a value for a column/parameter mapping based on source configuration."""
```

**Parameters:**

- `source_mode` (str) - How to get the value: "static", "previous", "specific", "start"
- `state` (WorkflowState) - Current workflow state
- `static_value` (Any) - Static value to use if source_mode is "static" (default: None)
- `default_value` (Any) - Default value if extraction fails (default: None)
- `source_node_id` (Optional[str]) - ID of node to extract from if source_mode is "specific" (default: None)
- `source_field_path` (Optional[str]) - Path to field in node output (default: None)
- `idx` (int) - Index for SQL expression tracking (default: 0)
- `sql_expressions` (Optional[List[int]]) - List to track SQL expression indices (default: None)

**Returns:**

- `Any` - The extracted value

**Raises:**
No specific exceptions.

**Example:**

```python
from backend.services.io import MappingValueExtractor

extractor = MappingValueExtractor()

# Extract static value
user_id = extractor.extract(
    source_mode="static",
    state=workflow_state,
    static_value="12345",
)
# Returns: "12345"

# Extract SQL function
sql_expressions = []
timestamp = extractor.extract(
    source_mode="static",
    state=workflow_state,
    static_value="NOW()",
    idx=0,
    sql_expressions=sql_expressions,
)
# Returns: "NOW()" (normalised)
# sql_expressions: [0] (marked as SQL expression)

# Extract from previous node
previous_output = extractor.extract(
    source_mode="previous",
    state=workflow_state,
    default_value="",
)
# Returns: Last node's output

# Extract from specific node with field path
country = extractor.extract(
    source_mode="specific",
    state=workflow_state,
    source_node_id="node-123",
    source_field_path="Country",
    default_value="Unknown",
)
# Returns: "Australia" (extracted from node-123's output)

# Extract from workflow start
original_message = extractor.extract(
    source_mode="start",
    state=workflow_state,
    default_value="",
)
# Returns: Original workflow input message
```

**Behaviour:**

- Routes to appropriate extraction method based on `source_mode`
- For "static" mode:
  - Detects SQL functions (CURRENT_TIMESTAMP, CURRENT_DATE, CURRENT_TIME, NOW())
  - Normalises SQL functions to uppercase
  - Tracks SQL expression indices in provided list
- For "previous" mode:
  - Extracts from last result in `state["results"]`
  - Returns `default_value` if no results exist
- For "specific" mode:
  - Looks up node output by `source_node_id`
  - Uses `FieldExtractor` to extract field by path
  - Returns `default_value` if node not found
- For "start" mode:
  - Extracts first HumanMessage from messages
  - Falls back to `state["original_message"]`
  - Returns `default_value` if neither exists

**Use Cases:**

- Building database INSERT/UPDATE queries with dynamic values
- Mapping workflow inputs to API parameters
- Extracting values from multiple nodes for aggregation
- Handling SQL functions vs. static values in queries

#### Internal Methods

- `_extract_static()` - Extract static value, handle SQL functions
- `_extract_from_previous()` - Extract from previous node result
- `_extract_from_specific()` - Extract from specific node with field path
- `_extract_from_start()` - Extract from workflow start message

**Properties:**

- `field_extractor: FieldExtractor` - Used for extracting fields from node outputs

---

### `FinalOutputExtractor`

Extracts the final output from workflow state.

**Purpose:** Determine the final output value from a completed workflow by trying multiple sources in priority order.

**Responsibilities:**

- Extract last AI message as final output
- Fall back to last node output if no messages
- Return None if no output found
- Handle both message-based and output-based workflows

**Initialisation:**

This class uses only static methods and does not require initialisation.

**Key Methods:**

#### `extract()`

```python
@staticmethod
def extract(state: WorkflowState) -> Optional[Any]:
    """Extract the final output from the workflow state."""
```

**Parameters:**

- `state` (WorkflowState) - The completed workflow state

**Returns:**

- `Optional[Any]` - The final output or None if not found

**Raises:**
No specific exceptions.

**Example:**

```python
from backend.services.io import FinalOutputExtractor

# After workflow completes
final_output = FinalOutputExtractor.extract(workflow_state)

if final_output:
    print(f"Workflow result: {final_output}")
else:
    print("No output found")

# Example with messages
state_with_messages = {
    "messages": [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there! How can I help?"),
    ],
    "node_outputs": {}
}
output = FinalOutputExtractor.extract(state_with_messages)
# Returns: "Hi there! How can I help?"

# Example with node outputs
state_with_outputs = {
    "messages": [],
    "node_outputs": {
        "node-1": {"raw": "First output"},
        "node-2": {"raw": "Final output"},
    }
}
output = FinalOutputExtractor.extract(state_with_outputs)
# Returns: "Final output"
```

**Behaviour:**

- Tries extraction in priority order:
    1. Last message (if it's an AIMessage) - returns `content`
    2. Last node output - returns `raw` field
- Returns None if neither source exists
- Does not modify state
- Does not raise exceptions

**Use Cases:**

- Extracting final workflow result for API responses
- Determining workflow completion status
- Getting the last AI response in conversational workflows
- Retrieving final processed output from multi-node workflows

## Configuration

### Configuration Classes

The I/O service uses configuration from external modules:

#### `EndNodeConfig`

Defined in `backend.models.workflow.configs.end_node`:

```python
@dataclass
class EndNodeConfig:
    """Configuration for END node output handling."""

    input_source: str = "all"
    source_node_ids: List[str] = field(default_factory=list)
    output_structure: str = "full"
    include_metadata: bool = True
    include_node_names: bool = True
    custom_output_template: Optional[str] = None
    include_fields: List[str] = field(default_factory=list)
    exclude_fields: List[str] = field(default_factory=list)
    wrap_response: bool = True
    response_key: str = "result"
```

**Fields:**

- `input_source` - Input source mode: "all", "previous", "specific", "multiple" (default: "all")
- `source_node_ids` - Node IDs for specific/multiple modes (default: [])
- `output_structure` - Output format: "full", "summary", "compact", "custom" (default: "full")
- `include_metadata` - Include execution metadata (default: True)
- `include_node_names` - Include node names in output (default: True)
- `custom_output_template` - Custom JSON template string (default: None)
- `include_fields` - Only include these fields from outputs (default: [])
- `exclude_fields` - Exclude these fields from outputs (default: [])
- `wrap_response` - Wrap in standard response structure (default: True)
- `response_key` - Key name for the main result (default: "result")

#### Input Source Configurations

Node input source configurations are defined in node data structures:

```python
class InputSourceConfig:
    """Configuration for node input sources."""

    source_mode: str  # "start", "previous", "specific", "custom", "field"
    source_node_id: Optional[str]  # For "specific" mode
    source_field_path: Optional[str]  # Field path for extraction
    custom_template: Optional[str]  # For "custom" mode
```

### Environment Variables

None. The I/O service does not use environment variables.

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.io import (
    InputBuilder,
    OutputProcessor,
    TemplateProcessor,
    StateProcessor,
    FieldExtractor,
)

# Initialise components
input_builder = InputBuilder()
template_processor = TemplateProcessor()
field_extractor = FieldExtractor()
state_processor = StateProcessor(active_executions={})

# OutputProcessor uses static methods, no initialisation needed
```

**Advanced Initialisation (Execution Engine):**

```python
from backend.services.io import (
    FieldExtractor,
    MappingValueExtractor,
    StateProcessor,
    TemplateProcessor,
)
from backend.services.io.input import InputBuilder

class ExecutionEngine:
    """Execution engine with I/O services."""

    def __init__(self, graph_manager):
        self.active_executions = {}

        # Initialise I/O processing services
        self.state_processor = StateProcessor(self.active_executions)
        self.template_processor = TemplateProcessor()
        self.field_extractor = FieldExtractor()
        self.mapping_extractor = MappingValueExtractor()
        self.input_builder = InputBuilder(self.field_extractor)
```

**Dependency Injection:**

```python
from backend.services.io import FieldExtractor
from backend.services.io.input import InputBuilder

# Create field extractor
field_extractor = FieldExtractor()

# Inject into input builder
input_builder = InputBuilder(field_extractor=field_extractor)

# Use in workflow execution
input_message = input_builder.build(node, state, graph)
```

## Error Handling

### Exception Hierarchy

The I/O service module does not define custom exceptions. It relies on standard Python exceptions:

```
Exception
├── KeyError (state field not found)
├── AttributeError (accessing missing attribute)
├── TypeError (type mismatch in processing)
└── ValueError (invalid configuration value)
```

External exceptions from dependencies:

- LangChain message exceptions
- Execution engine exceptions

### Error Handling Patterns

**Graceful Degradation:**

```python
from backend.services.io import FieldExtractor

extractor = FieldExtractor()

# Always provide default values
value = extractor.extract(
    output=node_output,
    field_path="Country",
    default_value="Unknown",  # Prevents None returns
)

# Safe to use in all contexts
print(f"Country: {value}")  # Never raises exception
```

**State Update Guards:**

```python
from backend.services.io import StateProcessor

processor = StateProcessor(active_executions={})

# Process update safely handles non-dict updates
await processor.process_update(
    state_update=potentially_invalid_update,  # May not be dict
    execution_id="exec-123",
    db_execution_id=456,
)
# Logs warning and continues if non-dict
```

**Template Processing:**

```python
from backend.services.io import TemplateProcessor

processor = TemplateProcessor()

# Missing variables return empty strings, not errors
template = "User: {{username}}, Age: {{age}}"
result = processor.process(template, state)
# If variables missing: "User: , Age: "
# No exception raised
```

**Output Processing:**

```python
from backend.services.io import OutputProcessor
from backend.models.workflow import EndNodeConfig

try:
    # Process output
    output = OutputProcessor.process(
        state=workflow_state,
        end_node=end_node,
        graph=graph_data,
    )
    return {"success": True, "output": output}

except KeyError as e:
    # State missing required field
    logger.error(f"Invalid state structure: {e}")
    return {"success": False, "error": "Invalid workflow state"}

except AttributeError as e:
    # Invalid node or config structure
    logger.error(f"Invalid configuration: {e}")
    return {"success": False, "error": "Invalid END node configuration"}
```

**Recommended Error Handling Pattern:**

```python
from backend.services.io import (
    InputBuilder,
    FieldExtractor,
    OutputProcessor,
)
from backend.services.config import get_logger

logger = get_logger("workflow.execution")

def execute_workflow(workflow_id: str, input_data: dict) -> dict:
    """Execute workflow with comprehensive error handling."""

    try:
        # Build input
        input_builder = InputBuilder()
        input_message = input_builder.build(
            node=start_node,
            state=state,
            graph=graph,
        )

        # Execute workflow (implementation details omitted)
        final_state = run_workflow(graph, input_message)

        # Process output
        final_output = OutputProcessor.process(
            state=final_state,
            end_node=end_node,
            graph=graph,
        )

        return {"success": True, "output": final_output}

    except KeyError as e:
        logger.error(f"State error in workflow {workflow_id}: {e}")
        return {"success": False, "error": f"Invalid state: {e}"}

    except AttributeError as e:
        logger.error(f"Configuration error in workflow {workflow_id}: {e}")
        return {"success": False, "error": f"Invalid configuration: {e}"}

    except Exception as e:
        logger.error(f"Unexpected error in workflow {workflow_id}: {e}")
        return {"success": False, "error": "Internal error"}
```

## Integration Patterns

### Integration with API Layer

The I/O service is primarily used through the execution engine, not directly from API routes:

```python
# backend/api/graph/execution.py
from fastapi import APIRouter, Depends
from backend.services.execution import get_executor

router = APIRouter()

@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    input_data: dict,
) -> dict:
    """Execute a workflow and return formatted output."""

    # Get executor (contains I/O services)
    executor = get_executor()

    # Execute workflow (uses InputBuilder internally)
    result = await executor.execute_workflow(
        workflow_id=workflow_id,
        input_data=input_data,
    )

    # Result already formatted by OutputProcessor
    return result
```

### Integration with Other Services

**Integration with Execution Engine:**

```python
# backend/services/execution/engine.py
from backend.services.io import (
    FieldExtractor,
    MappingValueExtractor,
    StateProcessor,
    TemplateProcessor,
)
from backend.services.io.input import InputBuilder

class ExecutionEngine:
    """Execution engine integrating I/O services."""

    def __init__(self, graph_manager):
        self.graph_manager = graph_manager
        self.active_executions = {}

        # Initialise I/O processing services
        self.state_processor = StateProcessor(self.active_executions)
        self.template_processor = TemplateProcessor()
        self.field_extractor = FieldExtractor()
        self.mapping_extractor = MappingValueExtractor()
        self.input_builder = InputBuilder(self.field_extractor)

    async def execute_node(self, node, state, graph):
        """Execute a single node."""

        # Build input using InputBuilder
        input_message = self.input_builder.build(node, state, graph)

        # Execute node
        output = await node.execute(input_message)

        # Update state tracking
        await self.state_processor.process_update(
            state_update={"current_node": node.uniq_id},
            execution_id=state["execution_id"],
            db_execution_id=state.get("db_execution_id"),
        )

        return output
```

**Integration with Node Executors:**

```python
# backend/services/nodes/executors/database/executor.py
from backend.services.io import MappingValueExtractor

class DatabaseNodeExecutor:
    """Executes database operations using MappingValueExtractor."""

    def __init__(self):
        self.mapping_extractor = MappingValueExtractor()

    async def execute(self, node, state, graph):
        """Execute database insert with column mappings."""

        # Extract values for each column mapping
        column_values = {}
        sql_expressions = []

        for idx, mapping in enumerate(node.column_mappings):
            value = self.mapping_extractor.extract(
                source_mode=mapping.source_mode,
                state=state,
                static_value=mapping.static_value,
                default_value=mapping.default_value,
                source_node_id=mapping.source_node_id,
                source_field_path=mapping.source_field_path,
                idx=idx,
                sql_expressions=sql_expressions,
            )
            column_values[mapping.column_name] = value

        # Build and execute query
        query = self._build_insert_query(
            table=node.table_name,
            columns=column_values,
            sql_expressions=sql_expressions,
        )
        result = await self._execute_query(query)

        return result
```

**Integration with Template-Based Nodes:**

```python
# backend/services/nodes/executors/agent.py
from backend.services.io import TemplateProcessor

class AgentNodeExecutor:
    """Executes agent nodes with template processing."""

    def __init__(self):
        self.template_processor = TemplateProcessor()

    async def execute(self, node, state, graph):
        """Execute agent with template-processed prompt."""

        # Check if node uses template
        if node.use_template and node.prompt_template:
            # Process template with state variables
            processed_prompt = self.template_processor.process(
                template=node.prompt_template,
                state=state,
            )
        else:
            # Use input builder result
            processed_prompt = state.get("input_message", "")

        # Execute agent with processed prompt
        response = await self._invoke_agent(
            prompt=processed_prompt,
            config=node.config,
        )

        return response
```

### Dependency Flow

**Service Dependencies:**

```
I/O Service Module
├── Depends on:
│   ├── backend.models.workflow (data structures)
│   ├── backend.services.workflow.state (WorkflowState)
│   ├── backend.services.config (logging)
│   └── langchain_core.messages (message types)
│
└── Depended on by:
    ├── backend.services.execution.engine (ExecutionEngine)
    ├── backend.services.nodes.executors.* (node executors)
    └── backend.services.execution.checkpoint (checkpoint executors)
```

**Data Flow:**

```
Workflow Start
      │
      ├─→ InputBuilder.build()
      │   ├─ Extract from workflow start
      │   └─ Returns: input message
      │
      ├─→ Node Execution
      │   └─ Produces: node output
      │
      ├─→ StateProcessor.process_update()
      │   ├─ Tracks: current node
      │   └─ Updates: active executions
      │
      ├─→ InputBuilder.build() (next node)
      │   ├─ Extract from previous output
      │   ├─ FieldExtractor.extract()
      │   └─ Returns: input message
      │
      └─→ OutputProcessor.process()
          ├─ Filter nodes
          ├─ Format output structure
          └─ Returns: final formatted output
```

### Common Integration Patterns

#### Pattern 1: Node Input Building

```python
from backend.services.io.input import InputBuilder
from backend.services.io import FieldExtractor

# Initialise with dependencies
field_extractor = FieldExtractor()
input_builder = InputBuilder(field_extractor)

# Build input for each node
for node in execution_order:
    # Build input from appropriate source
    input_message = input_builder.build(
        node=node,
        state=current_state,
        graph=graph_data,
    )

    # Execute node with built input
    output = await node.execute(input_message)

    # Store output in state
    current_state["node_outputs"][node.uniq_id] = output
```

#### Pattern 2: Field Extraction for Database Operations

```python
from backend.services.io import FieldExtractor, MappingValueExtractor

# Extract fields for database insert
field_extractor = FieldExtractor()
mapping_extractor = MappingValueExtractor()

# Get structured data from previous node
previous_output = state["node_outputs"]["extraction-node"]
country = field_extractor.extract(previous_output, "Country", "Unknown")
city = field_extractor.extract(previous_output, "City", "Unknown")

# Get values from various sources for column mappings
user_id = mapping_extractor.extract(
    source_mode="static",
    state=state,
    static_value="12345",
)

timestamp = mapping_extractor.extract(
    source_mode="static",
    state=state,
    static_value="NOW()",
)

# Build and execute insert
values = {
    "user_id": user_id,
    "country": country,
    "city": city,
    "created_at": timestamp,
}
```

#### Pattern 3: Template Processing with State

```python
from backend.services.io import TemplateProcessor

# Process custom prompts with workflow data
processor = TemplateProcessor()

# Template with multiple variable sources
template = """
Analyse the following request:

Original Request: {{original_message}}
Current Context: {{message}}

User Information:
- Country: {{Country}}
- Status: {{user_status}}

Please provide analysis.
"""

# Process with current state
processed_prompt = processor.process(template, workflow_state)

# Use in agent execution
response = await agent.invoke(processed_prompt)
```

#### Pattern 4: Real-Time State Tracking

```python
from backend.services.io import StateProcessor

# Initialise state tracking
active_executions = {}
state_processor = StateProcessor(active_executions)

# Start tracking execution
execution_id = "exec-abc-123"
active_executions[execution_id] = {
    "current_node": None,
    "current_node_name": None,
    "start_time": datetime.utcnow(),
}

# Process state updates during execution
for state_update in workflow_execution_stream():
    await state_processor.process_update(
        state_update=state_update,
        execution_id=execution_id,
        db_execution_id=db_id,
    )

    # Send WebSocket update
    await send_websocket_update(
        execution_id=execution_id,
        current_node=active_executions[execution_id]["current_node_name"],
    )
```

## Usage Examples

### Example 1: Basic Input Building

Complete example of building node input from previous node output:

```python
from backend.services.io import InputBuilder
from backend.models.workflow import EnhancedNodeData, GraphData
from backend.services.workflow.state import WorkflowState

# Step 1: Initialise InputBuilder
builder = InputBuilder()

# Step 2: Prepare workflow state
state: WorkflowState = {
    "messages": [],
    "node_outputs": {
        "node-1": {
            "raw": "The user is located in Sydney, Australia.",
            "structured": {"city": "Sydney", "country": "Australia"},
        }
    },
    "execution_id": "exec-123",
}

# Step 3: Define current node
current_node = EnhancedNodeData(
    uniq_id="node-2",
    name="Agent Node 2",
    node_type="agent",
    input_source_config=None,  # Defaults to "previous"
)

# Step 4: Build input
input_message = builder.build(
    node=current_node,
    state=state,
    graph=graph_data,
)

# Result: "The user is located in Sydney, Australia."
print(f"Input for {current_node.name}: {input_message}")
```

### Example 2: Advanced Field Extraction

Complete example showing field extraction from complex structured output:

```python
from backend.services.io import FieldExtractor, NestedFieldExtractor

# Step 1: Initialise extractors
field_extractor = FieldExtractor()
nested_extractor = NestedFieldExtractor()

# Step 2: Complex node output
node_output = {
    "raw": "User profile: John Smith, 30 years old, located in Australia",
    "structured": {
        "user": {
            "name": "John Smith",
            "age": 30,
            "location": {
                "country": "Australia",
                "city": "Sydney",
                "postcode": "2000"
            }
        },
        "status": "active"
    },
    "fields": {
        "Name": "John Smith",
        "Country": "Australia",
        "Age": 30
    }
}

# Step 3: Extract simple fields
name = field_extractor.extract(node_output, "Name", "Unknown")
print(f"Name: {name}")  # "John Smith"

country = field_extractor.extract(node_output, "Country", "Unknown")
print(f"Country: {country}")  # "Australia"

# Step 4: Extract nested fields
city = field_extractor.extract(node_output, "user.location.city", "Unknown")
print(f"City: {city}")  # "Sydney"

postcode = field_extractor.extract(node_output, "user.location.postcode", "0000")
print(f"Postcode: {postcode}")  # "2000"

# Step 5: Extract with default value
email = field_extractor.extract(node_output, "user.email", "no-email@example.com")
print(f"Email: {email}")  # "no-email@example.com" (default)

# Step 6: Extract whole output
whole = field_extractor.extract(node_output, None, "")
print(f"Whole: {whole}")  # "User profile: John Smith, 30 years old, located in Australia"
```

### Example 3: Complete Workflow with I/O Processing

Complete example showing typical I/O service usage in workflow execution:

```python
from backend.services.io import (
    InputBuilder,
    OutputProcessor,
    StateProcessor,
    FieldExtractor,
)
from backend.models.workflow import EndNodeConfig, EnhancedNodeData
from backend.services.workflow.state import WorkflowState
import asyncio

async def complete_workflow_example():
    """Example showing complete workflow with I/O processing."""

    # Step 1: Initialise I/O services
    active_executions = {}
    input_builder = InputBuilder()
    state_processor = StateProcessor(active_executions)
    field_extractor = FieldExtractor()

    # Step 2: Set up execution tracking
    execution_id = "exec-456"
    active_executions[execution_id] = {
        "current_node": None,
        "current_node_name": None,
    }

    # Step 3: Initialise workflow state
    state: WorkflowState = {
        "messages": [],
        "node_outputs": {},
        "execution_id": execution_id,
        "original_message": "Get weather for Sydney",
    }

    # Step 4: Execute first node
    node1 = EnhancedNodeData(
        uniq_id="node-1",
        name="Location Extractor",
        node_type="agent",
    )

    # Build input for first node
    input1 = input_builder.build(node1, state, graph_data)
    print(f"Node 1 input: {input1}")  # "Get weather for Sydney"

    # Simulate node execution
    output1 = {
        "raw": "The location is Sydney, Australia",
        "structured": {"city": "Sydney", "country": "Australia"},
    }
    state["node_outputs"][node1.uniq_id] = output1

    # Track state update
    await state_processor.process_update(
        state_update={"current_node": node1.uniq_id},
        execution_id=execution_id,
        db_execution_id=123,
    )

    # Step 5: Execute second node
    node2 = EnhancedNodeData(
        uniq_id="node-2",
        name="Weather Fetcher",
        node_type="agent",
    )

    # Build input from previous output
    input2 = input_builder.build(node2, state, graph_data)
    print(f"Node 2 input: {input2}")  # "The location is Sydney, Australia"

    # Simulate node execution
    output2 = {
        "raw": "Weather in Sydney: 22°C, Sunny",
        "structured": {"temperature": 22, "condition": "Sunny"},
    }
    state["node_outputs"][node2.uniq_id] = output2

    # Track state update
    await state_processor.process_update(
        state_update={"current_node": node2.uniq_id},
        execution_id=execution_id,
        db_execution_id=123,
    )

    # Step 6: Process final output with END node
    end_node = EnhancedNodeData(
        uniq_id="end-node",
        name="END",
        node_type="end",
        end_node_config=EndNodeConfig(
            input_source="all",
            output_structure="summary",
            include_metadata=True,
            include_node_names=True,
        ),
    )

    # Store results for END node processing
    state["results"] = [
        {"agent": "Location Extractor", "output": output1["raw"]},
        {"agent": "Weather Fetcher", "output": output2["raw"]},
    ]

    final_output = OutputProcessor.process(
        state=state,
        end_node=end_node,
        graph=graph_data,
    )

    print("Final output:", final_output)
    # Result:
    # [
    #     {"node": "Location Extractor", "response": "The location is Sydney, Australia"},
    #     {"node": "Weather Fetcher", "response": "Weather in Sydney: 22°C, Sunny"}
    # ]

    return {"success": True, "output": final_output}

# Run the example
result = asyncio.run(complete_workflow_example())
```

### Example 4: Database Integration with Mapping Extraction

Show how to use MappingValueExtractor for database operations:

```python
from backend.services.io import MappingValueExtractor, FieldExtractor
from backend.services.workflow.state import WorkflowState

async def database_integration_example():
    """Example showing database column mapping extraction."""

    # Step 1: Initialise extractors
    mapping_extractor = MappingValueExtractor()
    field_extractor = FieldExtractor()

    # Step 2: Workflow state with previous node outputs
    state: WorkflowState = {
        "node_outputs": {
            "extraction-node": {
                "raw": "User: John Smith, Country: Australia",
                "structured": {
                    "name": "John Smith",
                    "country": "Australia",
                    "age": 30,
                },
                "fields": {
                    "Name": "John Smith",
                    "Country": "Australia",
                    "Age": 30,
                }
            }
        },
        "execution_id": "exec-789",
        "original_message": "Add user John Smith from Australia",
    }

    # Step 3: Define column mappings for database INSERT
    column_mappings = [
        {
            "column_name": "user_id",
            "source_mode": "static",
            "static_value": "USER-12345",
        },
        {
            "column_name": "name",
            "source_mode": "specific",
            "source_node_id": "extraction-node",
            "source_field_path": "Name",
        },
        {
            "column_name": "country",
            "source_mode": "specific",
            "source_node_id": "extraction-node",
            "source_field_path": "Country",
        },
        {
            "column_name": "age",
            "source_mode": "specific",
            "source_node_id": "extraction-node",
            "source_field_path": "Age",
        },
        {
            "column_name": "created_at",
            "source_mode": "static",
            "static_value": "NOW()",
        },
    ]

    # Step 4: Extract values for each column
    column_values = {}
    sql_expressions = []

    for idx, mapping in enumerate(column_mappings):
        value = mapping_extractor.extract(
            source_mode=mapping["source_mode"],
            state=state,
            static_value=mapping.get("static_value"),
            default_value=None,
            source_node_id=mapping.get("source_node_id"),
            source_field_path=mapping.get("source_field_path"),
            idx=idx,
            sql_expressions=sql_expressions,
        )
        column_values[mapping["column_name"]] = value

    # Step 5: Build INSERT query
    print("Column values:")
    print(column_values)
    # {
    #     "user_id": "USER-12345",
    #     "name": "John Smith",
    #     "country": "Australia",
    #     "age": 30,
    #     "created_at": "NOW()"
    # }

    print(f"SQL expression indices: {sql_expressions}")
    # [4] (created_at is SQL function)

    # Step 6: Build parameterised query
    columns = []
    placeholders = []
    params = []

    for idx, (column, value) in enumerate(column_values.items()):
        columns.append(column)
        if idx in sql_expressions:
            # SQL function - use directly
            placeholders.append(value)
        else:
            # Parameterised value
            placeholders.append("?")
            params.append(value)

    query = f"INSERT INTO users ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

    print(f"Query: {query}")
    # "INSERT INTO users (user_id, name, country, age, created_at) VALUES (?, ?, ?, ?, NOW())"

    print(f"Params: {params}")
    # ["USER-12345", "John Smith", "Australia", 30]

    # Execute query (implementation details omitted)
    # result = await db.execute(query, params)

    return {"success": True, "query": query, "params": params}

# Run the example
result = asyncio.run(database_integration_example())
```

## Performance Considerations

### Performance Characteristics

**InputBuilder:**

- Complexity: O(1) for most operations
- Memory: Minimal (stores references only)
- I/O: None (operates on in-memory state)
- Bottleneck: Graph traversal for finding incoming nodes (O(e) where e = number of connections)

**OutputProcessor:**

- Complexity: O(n) where n = number of node outputs
- Memory: Creates new output structure proportional to filtered nodes
- I/O: None (operates on in-memory state)
- Bottleneck: Iterating through node outputs and results

**TemplateProcessor:**

- Complexity: O(m × n) where m = number of variables, n = number of node outputs
- Memory: Minimal (regex matching and string operations)
- I/O: None (operates on in-memory state)
- Bottleneck: Searching node outputs for variables (linear search)

**FieldExtractor:**

- Complexity: O(d) where d = depth of nested path
- Memory: Minimal (traverses existing structures)
- I/O: None (operates on in-memory state)
- Bottleneck: None for typical use cases

**StateProcessor:**

- Complexity: O(1) for updates
- Memory: Minimal (updates dictionary in place)
- I/O: None (operates on in-memory state)
- Async: Non-blocking updates

### Optimisation Tips

#### Tip 1: Cache Field Extractors

**Problem:**

```python
# Creating new extractor for each extraction
for node_output in node_outputs:
    extractor = FieldExtractor()  # Inefficient
    value = extractor.extract(node_output, "field", "default")
```

**Solution:**

```python
# Reuse single extractor instance
extractor = FieldExtractor()
for node_output in node_outputs:
    value = extractor.extract(node_output, "field", "default")
```

#### Tip 2: Minimise Template Variable Searches

**Problem:**

```python
# Processing same template multiple times
for item in items:
    # Template searched for variables on each iteration
    result = processor.process("{{message}} - {{status}}", state)
```

**Solution:**

```python
# Process template once if state doesn't change
processed = processor.process("{{message}} - {{status}}", state)
for item in items:
    # Use pre-processed result
    use_result(processed)
```

#### Tip 3: Use Appropriate Output Structure

**Problem:**

```python
# Using "full" when only responses needed
end_node_config = EndNodeConfig(
    output_structure="full",  # Returns all details
)
# Results in large output with unnecessary data
```

**Solution:**

```python
# Use "compact" for minimal output
end_node_config = EndNodeConfig(
    output_structure="compact",  # Only node responses
)
# Results in minimal output: {"Node1": "response1", "Node2": "response2"}
```

#### Tip 4: Filter Nodes Early

**Problem:**

```python
# Processing all nodes then filtering
end_node_config = EndNodeConfig(
    input_source="all",  # Processes all nodes
)
# Then manually filter output
filtered = {k: v for k, v in output.items() if k in needed_nodes}
```

**Solution:**

```python
# Filter at source
end_node_config = EndNodeConfig(
    input_source="specific",
    source_node_ids=["node-1", "node-3"],  # Only these nodes
)
# Output already filtered
```

### Async/Await Support

StateProcessor supports async operations:

```python
from backend.services.io import StateProcessor
import asyncio

async def async_state_tracking_example():
    """Example showing async state processing."""

    active_executions = {}
    processor = StateProcessor(active_executions)

    # Track execution
    execution_id = "exec-async-123"
    active_executions[execution_id] = {}

    # Async state updates
    await processor.process_update(
        state_update={"current_node": "node-1"},
        execution_id=execution_id,
        db_execution_id=456,
    )

    # Can be called concurrently with other async operations
    await asyncio.gather(
        processor.process_update(
            state_update={"current_node": "node-2"},
            execution_id=execution_id,
            db_execution_id=456,
        ),
        send_websocket_notification(execution_id),
        update_database_status(execution_id),
    )

# Run async example
asyncio.run(async_state_tracking_example())
```

### Batch Operations

Extractors support batch operations through iteration:

```python
from backend.services.io import FieldExtractor

# Batch field extraction
extractor = FieldExtractor()
outputs = [output1, output2, output3, output4]
fields_to_extract = ["Country", "City", "Age"]

# Extract multiple fields from multiple outputs
results = []
for output in outputs:
    extracted = {}
    for field in fields_to_extract:
        extracted[field] = extractor.extract(output, field, "Unknown")
    results.append(extracted)

# More efficient than creating new extractors
```

## Testing Patterns

### Unit Testing

```python
import pytest
from backend.services.io import (
    FieldExtractor,
    NestedFieldExtractor,
    TemplateProcessor,
    OutputProcessor,
)
from backend.models.workflow import EndNodeConfig

@pytest.fixture
def field_extractor():
    """Field extractor fixture."""
    return FieldExtractor()

@pytest.fixture
def sample_node_output():
    """Sample node output for testing."""
    return {
        "raw": "User in Australia",
        "structured": {
            "country": "Australia",
            "city": "Sydney"
        },
        "fields": {
            "Country": "Australia",
            "City": "Sydney"
        }
    }

def test_field_extraction_simple(field_extractor, sample_node_output):
    """Test simple field extraction."""
    result = field_extractor.extract(sample_node_output, "Country", "Unknown")
    assert result == "Australia"

def test_field_extraction_nested(field_extractor, sample_node_output):
    """Test nested field extraction."""
    result = field_extractor.extract(sample_node_output, "structured.city", "Unknown")
    assert result == "Sydney"

def test_field_extraction_default(field_extractor, sample_node_output):
    """Test extraction with default value."""
    result = field_extractor.extract(sample_node_output, "NonExistent", "DefaultValue")
    assert result == "DefaultValue"

def test_nested_field_extractor():
    """Test nested field extractor."""
    data = {
        "user": {
            "profile": {
                "name": "John Smith"
            }
        }
    }
    result = NestedFieldExtractor.extract(data, "user.profile.name")
    assert result == "John Smith"

def test_template_processor():
    """Test template processing."""
    processor = TemplateProcessor()
    state = {
        "messages": [],
        "user_id": "12345",
    }
    template = "User ID: {{user_id}}"
    result = processor.process(template, state)
    assert result == "User ID: 12345"

def test_output_processor_summary():
    """Test output processor with summary structure."""
    state = {
        "node_outputs": {
            "node-1": {"raw": "Output 1"},
            "node-2": {"raw": "Output 2"},
        },
        "results": [
            {"agent": "Node 1", "output": "Output 1"},
            {"agent": "Node 2", "output": "Output 2"},
        ],
    }

    end_node = type('obj', (object,), {
        'uniq_id': 'end',
        'end_node_config': EndNodeConfig(
            input_source="all",
            output_structure="summary",
        )
    })()

    graph = type('obj', (object,), {
        'nodes': [],
        'connections': []
    })()

    result = OutputProcessor.process(state, end_node, graph)
    assert isinstance(result, list)
    assert len(result) == 2
```

### Mocking Dependencies

```python
import pytest
from unittest.mock import Mock, patch
from backend.services.io import InputBuilder
from backend.services.io.input import InputBuilder as CompleteInputBuilder

@patch('backend.services.execution.get_executor')
def test_input_builder_legacy(mock_get_executor):
    """Test legacy InputBuilder with mocked executor."""

    # Mock executor
    mock_executor = Mock()
    mock_executor._build_node_input.return_value = "Test input message"
    mock_get_executor.return_value = mock_executor

    # Create builder
    builder = InputBuilder()

    # Mock inputs
    mock_node = Mock()
    mock_node.name = "TestNode"
    mock_state = {}
    mock_graph = Mock()

    # Call build
    result = builder.build(mock_node, mock_state, mock_graph)

    # Verify
    assert result == "Test input message"
    mock_executor._build_node_input.assert_called_once_with(
        mock_node, mock_state, mock_graph
    )

def test_complete_input_builder_with_mock_extractor():
    """Test complete InputBuilder with mocked FieldExtractor."""

    # Mock field extractor
    mock_extractor = Mock()
    mock_extractor.extract.return_value = "Extracted value"

    # Create builder with mock
    builder = CompleteInputBuilder(field_extractor=mock_extractor)

    # Verify injection
    assert builder.field_extractor == mock_extractor
```

### Integration Testing

```python
import pytest
from backend.services.io import (
    InputBuilder,
    OutputProcessor,
    FieldExtractor,
)
from backend.models.workflow import EndNodeConfig, EnhancedNodeData

@pytest.mark.integration
async def test_complete_io_workflow():
    """Integration test for complete I/O workflow."""

    # Set up components
    input_builder = InputBuilder()
    field_extractor = FieldExtractor()

    # Create workflow state
    state = {
        "messages": [],
        "node_outputs": {},
        "original_message": "Test message",
        "execution_id": "test-exec",
    }

    # Execute first node
    node1 = EnhancedNodeData(
        uniq_id="node-1",
        name="Node 1",
        node_type="agent",
    )

    # Build input
    input1 = input_builder.build(node1, state, mock_graph)
    assert input1 == "Test message"

    # Simulate node execution
    state["node_outputs"]["node-1"] = {
        "raw": "Processed output",
        "fields": {"Result": "Success"}
    }

    # Extract field
    result = field_extractor.extract(
        state["node_outputs"]["node-1"],
        "Result",
        "Unknown"
    )
    assert result == "Success"

    # Process final output
    end_node = EnhancedNodeData(
        uniq_id="end",
        name="END",
        node_type="end",
        end_node_config=EndNodeConfig(
            input_source="all",
            output_structure="compact",
        ),
    )

    state["results"] = [
        {"agent": "Node 1", "output": "Processed output"}
    ]

    final = OutputProcessor.process(state, end_node, mock_graph)
    assert "Node 1" in final
    assert final["Node 1"] == "Processed output"
```

## Best Practices

### Do's

✅ **Always provide default values for extraction**

```python
from backend.services.io import FieldExtractor

extractor = FieldExtractor()

# Good: Always specify default value
country = extractor.extract(output, "Country", "Unknown")

# This prevents None values that could cause issues downstream
if country != "Unknown":
    process_country(country)
```

✅ **Reuse extractor instances**

```python
from backend.services.io import FieldExtractor

# Good: Create once, reuse multiple times
extractor = FieldExtractor()
for output in outputs:
    value = extractor.extract(output, "field", "default")

# Bad: Creating new instance each time
for output in outputs:
    extractor = FieldExtractor()  # Wasteful
    value = extractor.extract(output, "field", "default")
```

✅ **Use appropriate output structures**

```python
from backend.models.workflow import EndNodeConfig

# Good: Use "compact" for minimal output
compact_config = EndNodeConfig(
    output_structure="compact",
    include_metadata=False,
)

# Good: Use "full" when debugging or need complete details
debug_config = EndNodeConfig(
    output_structure="full",
    include_metadata=True,
    include_node_names=True,
)

# Good: Use "summary" for balanced output
api_config = EndNodeConfig(
    output_structure="summary",
    include_metadata=False,
)
```

✅ **Filter nodes at the source**

```python
from backend.models.workflow import EndNodeConfig

# Good: Filter specific nodes
end_config = EndNodeConfig(
    input_source="specific",
    source_node_ids=["analysis-node", "summary-node"],
    output_structure="compact",
)

# This is more efficient than filtering after processing
```

✅ **Handle state updates safely**

```python
from backend.services.io import StateProcessor

processor = StateProcessor(active_executions)

# Good: StateProcessor already handles non-dict updates
await processor.process_update(
    state_update=update_data,  # May be any type
    execution_id=execution_id,
    db_execution_id=db_id,
)
# No need to check type - processor guards against non-dict
```

### Don'ts

❌ **Don't extract fields without default values in production**

```python
from backend.services.io import FieldExtractor

extractor = FieldExtractor()

# Bad: No default value
country = extractor.extract(output, "Country")
# Could return None and cause AttributeError downstream

# Good: Always provide default
country = extractor.extract(output, "Country", "Unknown")
```

❌ **Don't process templates multiple times unnecessarily**

```python
from backend.services.io import TemplateProcessor

processor = TemplateProcessor()

# Bad: Processing same template in loop
for item in items:
    # Template is re-parsed and re-processed each time
    message = processor.process("{{message}}", state)
    send_message(message)

# Good: Process once if state doesn't change
message = processor.process("{{message}}", state)
for item in items:
    send_message(message)
```

❌ **Don't use "full" output structure when not needed**

```python
from backend.models.workflow import EndNodeConfig

# Bad: Using "full" for API response
api_config = EndNodeConfig(
    output_structure="full",  # Returns all node details, tools, etc.
    include_metadata=True,
)
# Results in unnecessarily large responses

# Good: Use appropriate structure
api_config = EndNodeConfig(
    output_structure="compact",  # Minimal output
    include_metadata=False,
)
```

❌ **Don't manually traverse nested structures**

```python
# Bad: Manual nested traversal
try:
    country = output["structured"]["location"]["country"]
except (KeyError, TypeError):
    country = "Unknown"

# Good: Use NestedFieldExtractor
from backend.services.io import NestedFieldExtractor

country = NestedFieldExtractor.extract(
    output.get("structured", {}),
    "location.country"
) or "Unknown"
```

❌ **Don't ignore extraction failures silently**

```python
from backend.services.io import FieldExtractor

extractor = FieldExtractor()

# Bad: Ignoring that extraction might fail
country = extractor.extract(output, "Country")
insert_into_database(country)  # Could insert None

# Good: Check result or use meaningful default
country = extractor.extract(output, "Country", "Unknown")
if country != "Unknown":
    insert_into_database(country)
else:
    logger.warning("Country field not found in output")
```

## Related Documentation

### Related Services

- [Execution Service](execution.md) - Workflow execution engine that uses I/O services
- [Graph Service](graph.md) - Graph building and management
- [Workflow Service](workflow.md) - Workflow state and resumption management

### Related API Modules

- [Graph API](../../../backend/api/graph/graph.md) - Workflow execution endpoints that return I/O-formatted outputs
- [Workflow API](../../../backend/api/workflow/workflow.md) - Workflow management endpoints

### Architecture Documentation

- [Service Layer Architecture](../architecture/service-layer.md) - Overall service layer design
- [Execution Flow](../architecture/execution-flow.md) - How I/O services fit into execution

### External Documentation

- [LangChain Messages](https://python.langchain.com/docs/modules/model_io/messages/) - Message types used in state
- [LangGraph State](https://langchain-ai.github.io/langgraph/reference/graphs/#state) - State management concepts

## Summary

The I/O service module provides essential data processing capabilities for AgenticStudio workflow execution. It handles the
complex task of building node inputs from various sources, extracting fields from structured outputs, processing
templates with dynamic variables, and formatting final outputs according to configuration.

The module demonstrates clean separation of concerns through focused classes:

- **InputBuilder** handles all input construction logic
- **OutputProcessor** manages output formatting
- **Extractors** encapsulate field extraction strategies
- **TemplateProcessor** handles template substitution
- **StateProcessor** manages real-time tracking

**Key Features:**

- Multiple input source strategies (start, previous, specific, custom, field)
- Flexible output formatting (full, summary, compact, custom)
- Nested field extraction with dot notation
- Template processing with workflow state variables
- Real-time state tracking for WebSocket updates
- Database column mapping value extraction
- No custom exceptions - relies on graceful degradation

**Primary Use Cases:**

- Building contextual inputs for agent and tool nodes
- Extracting structured data from LLM responses
- Formatting workflow results for API consumption
- Processing dynamic templates with state variables
- Tracking execution progress in real-time

**When to Use This Service:**

- Building workflow execution systems
- Implementing node-based processing pipelines
- Creating flexible output formatting for APIs
- Extracting and mapping data between workflow stages
- Tracking real-time workflow execution status
