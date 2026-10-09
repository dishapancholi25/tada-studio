# Conditions Service Module

## Overview

The conditions service module provides a comprehensive framework for evaluating conditions and making routing decisions
in AgenticStudio workflows. It supports multiple condition types including simple comparisons, complex expressions,
multi-branch routing, and LLM-based decision making.

**Location:** [backend/services/conditions/](../../backend/services/conditions/)

**Primary Responsibilities:**

- Extract values from workflow state based on various input sources
- Evaluate conditions using different strategies (simple, expression, LLM)
- Support binary (true/false) and multi-branch routing decisions
- Create condition functions for LangGraph conditional edges
- Provide safe expression evaluation using AST visitor pattern

**Key Use Cases:**

- Workflow branching based on data values or patterns
- Dynamic routing decisions using LLM reasoning
- Complex conditional logic with AND/OR operators
- Safe evaluation of user-defined Python expressions
- Multi-way routing with configurable branch conditions

## Architecture

### Module Structure

```
backend/services/conditions/
├── __init__.py                    # Public API exports
├── evaluator.py                   # Main orchestrator (ConditionEvaluator)
├── factory.py                     # Factory for creating condition functions
├── value_extractor.py             # Value extraction from workflow state
└── evaluators/                    # Specialised evaluator implementations
    ├── __init__.py               # Evaluator exports
    ├── single.py                 # Single condition evaluation
    ├── branch.py                 # Multi-branch evaluation
    ├── expression.py             # Expression-based evaluation with AST safety
    └── llm.py                    # LLM-based evaluation
```

**File Purposes:**

- **evaluator.py**: Central orchestrator that delegates to specialised evaluators based on condition type
- **factory.py**: Creates condition functions compatible with LangGraph conditional edges
- **value_extractor.py**: Extracts values from workflow state using various input sources (previous, specific, start,
  static)
- **evaluators/single.py**: Evaluates individual conditions with operators like ==, !=, >, contains, matches, etc.
- **evaluators/branch.py**: Coordinates value extraction and evaluation for multi-branch routing
- **evaluators/expression.py**: Safely evaluates Python expressions using AST visitor pattern to prevent code injection
- **evaluators/llm.py**: Uses LLM reasoning to make routing decisions based on context

### Design Patterns

**Strategy Pattern**

The module uses the Strategy pattern to handle different condition types. The `ConditionEvaluator` orchestrator
delegates to specialised evaluator classes:

```
ConditionEvaluator (Orchestrator)
├── SingleConditionEvaluator (Strategy)
├── BranchConditionEvaluator (Strategy)
├── ExpressionConditionEvaluator (Strategy)
└── LLMConditionEvaluator (Strategy)
```

**Factory Pattern**

The `ConditionFunctionFactory` creates callable condition functions that can be used as LangGraph conditional edges:

```python
factory = ConditionFunctionFactory(evaluator)
condition_func = factory.create_condition_function(node, graph)
# Returns: Callable[[WorkflowState], str]
```

**Visitor Pattern**

The `SafeExpressionEvaluator` uses the AST Visitor pattern to safely evaluate Python expressions by whitelisting allowed
operations:

```python
class SafeExpressionEvaluator(ast.NodeVisitor):
    def visit_Compare(self, node): ...
    def visit_BoolOp(self, node): ...
    def visit_BinOp(self, node): ...
```

**Orchestrator Pattern**

The `ConditionEvaluator` serves as an orchestrator that coordinates between:

- Value extraction (ValueExtractor)
- Condition evaluation (various evaluator strategies)
- Logic operator handling (AND/OR)

### Component Relationships

```
┌─────────────────────────────────────────────────────────┐
│                  ConditionNodeExecutor                  │
│                   (Node Executor)                       │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  ConditionEvaluator                     │
│                   (Orchestrator)                        │
├─────────────────────────────────────────────────────────┤
│  - ValueExtractor                                       │
│  - SingleConditionEvaluator                            │
│  - BranchConditionEvaluator                            │
│  - ExpressionConditionEvaluator                        │
│  - LLMConditionEvaluator                               │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┼────────────┬──────────────┐
         ▼            ▼            ▼              ▼
┌──────────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│    Single    │ │ Branch  │ │Expression│ │   LLM    │
│  Evaluator   │ │Evaluator│ │Evaluator │ │Evaluator │
└──────────────┘ └─────────┘ └──────────┘ └──────────┘
```

```
┌─────────────────────────────────────────────────────────┐
│                  ExecutionEngine                        │
│                (Graph Orchestrator)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              ConditionFunctionFactory                   │
│                    (Factory)                            │
├─────────────────────────────────────────────────────────┤
│  - ConditionEvaluator                                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
                Returns: Callable[[WorkflowState], str]
                (Used as LangGraph conditional edge)
```

### Dependencies

**Internal Dependencies:**

- `backend.services.workflow.state` - WorkflowState type definition
- `backend.services.execution.logging` - Execution logging utilities
- `backend.services.graph` - GraphManager for LLM access (optional)

**External Dependencies:**

- `ast` - Abstract Syntax Tree for safe expression evaluation
- `operator` - Standard operators for AST evaluation
- `re` - Regular expressions for pattern matching
- `json` - JSON parsing for structured data extraction
- `typing` - Type hints

**Database Dependencies:**
None - this is a stateless service that operates on in-memory workflow state.

**Environment Variables and Configuration:**
None - configuration is provided through method parameters and condition configs.

## Public API

### Exported Classes

- `ConditionEvaluator` - Main orchestrator for all condition evaluation types
- `ConditionFunctionFactory` - Factory for creating LangGraph-compatible condition functions
- `ValueExtractor` - Extracts values from workflow state based on input source configuration
- `SingleConditionEvaluator` - Evaluates individual conditions with various comparison operators
- `BranchConditionEvaluator` - Evaluates branch conditions for multi-way routing
- `ExpressionConditionEvaluator` - Safely evaluates Python expression-based conditions
- `LLMConditionEvaluator` - Uses LLM reasoning for intelligent routing decisions

### Exported Functions

None - this module exports only classes.

### Constants and Configuration

None - configuration is provided at runtime through condition configuration objects.

### Exceptions

This module does not define custom exceptions. It relies on standard Python exceptions:

```
Exception
├── ValueError - Raised for invalid operations, disallowed operators, or configuration errors
├── SyntaxError - Raised for malformed expressions in expression evaluator
├── NameError - Raised when undefined variables are referenced in expressions
├── TypeError - Raised for type mismatches during evaluation
└── AttributeError - Raised for invalid attribute access in expressions
```

## Core Classes

### `ConditionEvaluator`

Central orchestrator for all condition evaluation types in AgenticStudio workflows.

**Purpose:** Provides a unified interface for evaluating different types of conditions (binary, multi-branch,
expression, LLM) by delegating to specialised evaluator implementations.

**Responsibilities:**

- Orchestrate condition evaluation across different condition types
- Extract values from workflow state using ValueExtractor
- Delegate to appropriate evaluator strategy based on condition type
- Handle logic operators (AND/OR) for compound conditions
- Parse condition configurations from both dict and dataclass formats

**Initialisation:**

```python
def __init__(
    self,
    graph_manager=None,
) -> None:
    """
    Initialise the condition evaluator.

    Args:
        graph_manager: Optional GraphManager for LLM evaluation.
                      Required only if LLM-based conditions will be used.
    """
```

**Key Methods:**

#### `evaluate_binary_condition()`

Evaluate a binary (true/false) condition using simple or compound logic.

```python
def evaluate_binary_condition(
    self,
    state: WorkflowState,
    condition_config: Any,
) -> bool:
    """Evaluate a binary condition (true/false)."""
```

**Parameters:**

- `state` (WorkflowState) - The current workflow state containing messages and node outputs
- `condition_config` (Any) - Configuration specifying the condition to evaluate (dict or dataclass)

**Returns:**

- `bool` - True if condition is met, False otherwise

**Raises:**

- `ValueError` - If condition configuration is malformed

**Example:**

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

# Initialise evaluator
evaluator = ConditionEvaluator()

# Create state with data
state = WorkflowState(
    messages=[],
    node_outputs={
        "node_1": {
            "raw": "success",
            "fields": {"status": "completed", "count": 42}
        }
    }
)

# Simple condition config
condition_config = {
    "input_source": "specific",
    "source_node_id": "node_1",
    "field_path": "status",
    "simple_conditions": [
        {
            "operator": "==",
            "value": "completed",
            "value_type": "string"
        }
    ],
    "logic_operator": "AND"
}

# Evaluate condition
result = evaluator.evaluate_binary_condition(state, condition_config)
print(f"Condition result: {result}")  # True
```

**Behaviour:**

- Extracts value from state using ValueExtractor
- If multiple simple_conditions are provided, evaluates each one
- Combines results using the logic_operator (AND/OR)
- For AND: returns True only if all conditions are True
- For OR: returns True if any condition is True
- Supports both dict and dataclass configuration formats

**Use Cases:**

- Check if a field equals a specific value
- Verify numeric comparisons (>, <, >=, <=)
- Test string patterns (contains, starts_with, ends_with)
- Combine multiple conditions with AND/OR logic

---

#### `evaluate_multi_branch()`

Evaluate multi-branch conditions to determine which branch to take.

```python
def evaluate_multi_branch(
    self,
    state: WorkflowState,
    branches: list,
) -> str:
    """Evaluate multi-branch conditions."""
```

**Parameters:**

- `state` (WorkflowState) - The current workflow state
- `branches` (list) - List of branch configurations, each with a condition and handle_id

**Returns:**

- `str` - Branch handle ID (without 'branch-' prefix) or "0" for default branch

**Raises:**

- `ValueError` - If branch configuration is invalid

**Example:**

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

evaluator = ConditionEvaluator()

state = WorkflowState(
    node_outputs={
        "classifier": {
            "fields": {"category": "urgent"}
        }
    }
)

branches = [
    {
        "handle_id": "branch-1",
        "label": "Urgent",
        "condition": {
            "input_source": "specific",
            "source_node_id": "classifier",
            "field_path": "category",
            "operator": "==",
            "value": "urgent"
        }
    },
    {
        "handle_id": "branch-2",
        "label": "Normal",
        "condition": {
            "input_source": "specific",
            "source_node_id": "classifier",
            "field_path": "category",
            "operator": "==",
            "value": "normal"
        }
    }
]

# Evaluates to "1" (matches first branch)
result = evaluator.evaluate_multi_branch(state, branches)
print(f"Selected branch: {result}")  # "1"
```

**Behaviour:**

- Iterates through branches in order
- Evaluates each branch's condition
- Returns the handle_id of the first matching branch (with 'branch-' prefix removed)
- Returns "0" if no branches match (default branch)
- Short-circuits evaluation once a match is found

**Use Cases:**

- Route to different workflows based on data classification
- Select handling path based on priority or category
- Implement switch/case-like logic in workflows
- Dynamic routing with multiple possible paths

---

#### `evaluate_expression()`

Evaluate a Python expression-based condition safely using AST validation.

```python
def evaluate_expression(
    self,
    state: WorkflowState,
    condition_config: Any,
) -> bool:
    """Evaluate an expression-based condition."""
```

**Parameters:**

- `state` (WorkflowState) - The current workflow state
- `condition_config` (Any) - Configuration containing the expression string

**Returns:**

- `bool` - True if expression evaluates to a truthy value, False otherwise

**Raises:**

- `ValueError` - If expression contains disallowed operations
- `SyntaxError` - If expression has invalid Python syntax

**Example:**

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

evaluator = ConditionEvaluator()

state = WorkflowState(
    node_outputs={
        "counter": {
            "fields": {"count": 42, "max": 100}
        }
    }
)

# Complex expression with multiple conditions
condition_config = {
    "expression": "node_outputs['counter']['fields']['count'] > 40 and node_outputs['counter']['fields']['count'] < node_outputs['counter']['fields']['max']"
}

result = evaluator.evaluate_expression(state, condition_config)
print(f"Expression result: {result}")  # True
```

**Behaviour:**

- Builds a safe evaluation context with state data
- Parses expression into AST (Abstract Syntax Tree)
- Validates that only whitelisted operations are used
- Evaluates expression and converts result to boolean
- Logs warnings if expression evaluation fails

**Use Cases:**

- Complex conditional logic not supported by simple operators
- Mathematical calculations in conditions
- Boolean algebra with multiple variables
- Nested data structure access with conditions

---

#### `evaluate_llm()`

Evaluate a condition using LLM reasoning to make intelligent routing decisions.

```python
def evaluate_llm(
    self,
    state: WorkflowState,
    condition_config: Any,
    graph: Any,
) -> str:
    """Evaluate an LLM-based condition."""
```

**Parameters:**

- `state` (WorkflowState) - The current workflow state
- `condition_config` (Any) - Configuration containing the LLM prompt and settings
- `graph` (Any) - Graph definition containing default LLM configuration

**Returns:**

- `str` - Routing decision as string (e.g., "true", "false", or branch label)

**Raises:**

- `ValueError` - If LLM evaluator was not initialised with graph_manager
- `Exception` - If LLM invocation fails

**Example:**

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState
from backend.services.graph import GraphManager

# Initialise with graph_manager for LLM access
graph_manager = GraphManager()
evaluator = ConditionEvaluator(graph_manager)

state = WorkflowState(
    messages=[
        {"role": "user", "content": "I'm very frustrated with your service!"}
    ],
    original_message="I'm very frustrated with your service!"
)

condition_config = {
    "condition_type": "llm",
    "llm_prompt": "Analyse the user's message: '{last_message}'. Is the user expressing frustration or anger? Answer with 'true' or 'false'.",
    "llm_config": {
        "provider": "openai",
        "model": "gpt-4"
    }
}

graph = type('Graph', (), {'llm_config': condition_config["llm_config"]})()

# LLM will analyse sentiment and return "true" or "false"
result = evaluator.evaluate_llm(state, condition_config, graph)
print(f"LLM decision: {result}")  # "true"
```

**Behaviour:**

- Formats the LLM prompt with context from workflow state
- Invokes the LLM using the configured model
- Parses the LLM response to extract routing decision
- For multi-branch mode, looks for branch labels in response
- For binary mode, looks for "true"/"false" or "yes"/"no" in response
- Falls back to "false" if response is ambiguous

**Use Cases:**

- Sentiment analysis for routing to appropriate handlers
- Content classification using natural language understanding
- Intent detection for dynamic workflow paths
- Quality assessment of generated content
- Intelligent decision-making based on context

---

**Class Attributes:**

- `value_extractor: ValueExtractor` - Extracts values from workflow state
- `single_evaluator: SingleConditionEvaluator` - Evaluates individual conditions
- `branch_evaluator: BranchConditionEvaluator` - Evaluates multi-branch routing
- `expression_evaluator: ExpressionConditionEvaluator` - Evaluates expression conditions
- `llm_evaluator: Optional[LLMConditionEvaluator]` - Evaluates LLM conditions (None if no graph_manager)

---

### `ConditionFunctionFactory`

Factory for creating LangGraph-compatible condition functions for workflow routing.

**Purpose:** Creates callable functions that evaluate conditions and return routing decisions compatible with
LangGraph's conditional edge system.

**Responsibilities:**

- Create condition functions that wrap ConditionEvaluator logic
- Handle result caching to avoid re-evaluation
- Parse and route based on condition configuration
- Store evaluation results in workflow state for later retrieval
- Support all condition types (binary, multi-branch, expression, LLM)

**Initialisation:**

```python
def __init__(
    self,
    condition_evaluator: ConditionEvaluator,
) -> None:
    """
    Initialise the factory.

    Args:
        condition_evaluator: The condition evaluator to use for evaluation
    """
```

**Key Methods:**

#### `create_condition_function()`

Create a condition function for use as a LangGraph conditional edge.

```python
def create_condition_function(
    self,
    node: Any,
    graph: Any,
) -> Callable[[WorkflowState], str]:
    """Create a condition function for conditional routing."""
```

**Parameters:**

- `node` (Any) - The condition node containing condition_config
- `graph` (Any) - The complete graph definition

**Returns:**

- `Callable[[WorkflowState], str]` - Function that takes WorkflowState and returns routing decision

**Raises:**

- `ValueError` - If condition configuration is invalid

**Example:**

```python
from backend.services.conditions import ConditionEvaluator, ConditionFunctionFactory
from backend.services.workflow.state import WorkflowState

# Setup
evaluator = ConditionEvaluator()
factory = ConditionFunctionFactory(evaluator)

# Create node with condition config
node = type('Node', (), {
    'uniq_id': 'condition_1',
    'name': 'Check Status',
    'condition_config': {
        'branch_mode': 'binary',
        'condition_type': 'simple',
        'input_source': 'specific',
        'source_node_id': 'processor',
        'field_path': 'status',
        'simple_conditions': [{
            'operator': '==',
            'value': 'success',
            'value_type': 'string'
        }],
        'logic_operator': 'AND'
    }
})()

graph = type('Graph', (), {'llm_config': None})()

# Create condition function
condition_func = factory.create_condition_function(node, graph)

# Use in workflow
state = WorkflowState(
    node_outputs={
        'processor': {'fields': {'status': 'success'}}
    }
)

# Function returns routing decision
next_node = condition_func(state)  # "true"
print(f"Route to: {next_node}")
```

**Behaviour:**

- Creates a closure that captures node and graph references
- Checks for pre-computed results in state to avoid re-evaluation
- Parses condition configuration to determine evaluation strategy
- Delegates to appropriate evaluator method based on condition type
- Stores evaluation result in state with key `__condition_result_{node_id}`
- Returns string routing decision compatible with LangGraph

**Use Cases:**

- Create conditional edges in LangGraph workflows
- Implement workflow branching logic
- Enable dynamic routing based on data or LLM decisions
- Support complex multi-branch routing scenarios

---

**Class Attributes:**

- `evaluator: ConditionEvaluator` - The condition evaluator instance used for evaluation

---

### `ValueExtractor`

Extracts values from workflow state based on various input source configurations.

**Purpose:** Provides a unified interface for extracting values from different locations in workflow state, supporting
multiple input sources and nested field access.

**Responsibilities:**

- Extract values from different input sources (previous, specific, start, static)
- Navigate nested data structures using field paths
- Handle both dict and dataclass configuration formats
- Parse JSON when needed for structured data access
- Provide fallback values when extraction fails

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise the value extractor."""
```

**Key Methods:**

#### `extract()`

Extract a value from workflow state based on condition configuration.

```python
def extract(
    self,
    state: WorkflowState,
    condition_config: Any,
) -> Any:
    """Extract value from state based on condition configuration."""
```

**Parameters:**

- `state` (WorkflowState) - The workflow state to extract from
- `condition_config` (Any) - Configuration specifying extraction rules

**Returns:**

- `Any` - The extracted value, or empty string if extraction fails

**Example:**

```python
from backend.services.conditions import ValueExtractor
from backend.services.workflow.state import WorkflowState

extractor = ValueExtractor()

# State with nested data
state = WorkflowState(
    node_outputs={
        'api_call': {
            'fields': {
                'response': {
                    'status': 200,
                    'data': {
                        'users': [
                            {'name': 'Alice', 'age': 30},
                            {'name': 'Bob', 'age': 25}
                        ]
                    }
                }
            }
        }
    }
)

# Extract nested field using dot notation
config = {
    'input_source': 'specific',
    'source_node_id': 'api_call',
    'field_path': 'response.data.users.0.name'
}

value = extractor.extract(state, config)
print(f"Extracted: {value}")  # "Alice"
```

**Behaviour:**

- Parses configuration to determine input source and extraction rules
- Routes to appropriate extraction method based on input_source
- For nested fields, uses dot notation to navigate data structures
- Tries multiple locations (fields, structured_output, raw JSON)
- Returns empty string if value cannot be extracted

**Use Cases:**

- Extract specific fields from node outputs for comparison
- Get last message content for condition evaluation
- Access nested data structures with complex paths
- Retrieve static values from configuration
- Extract original workflow input for routing decisions

---

**Static Methods:**

#### `_extract_field_value()`

Extract a value from nested data using dot notation field path.

```python
@staticmethod
def _extract_field_value(
    data: Any,
    field_path: str,
) -> Any:
    """Extract a value from nested data using dot notation."""
```

**Parameters:**

- `data` (Any) - The data structure to extract from (dict, list, or object)
- `field_path` (str) - Dot-separated path to the field (e.g., "user.address.city")

**Returns:**

- `Any` - The extracted value, or None if path is invalid

**Example:**

```python
from backend.services.conditions import ValueExtractor

data = {
    'user': {
        'profile': {
            'addresses': [
                {'city': 'London', 'country': 'UK'},
                {'city': 'Paris', 'country': 'France'}
            ]
        }
    }
}

# Extract nested field
city = ValueExtractor._extract_field_value(data, 'user.profile.addresses.0.city')
print(city)  # "London"

# Access list by index
country = ValueExtractor._extract_field_value(data, 'user.profile.addresses.1.country')
print(country)  # "France"
```

**Behaviour:**

- Splits field_path by dots to navigate nested structure
- Supports dictionary key access
- Supports list/tuple index access using numeric strings
- Supports object attribute access via getattr
- Returns None if any part of the path is invalid
- Handles mixed access patterns (dict.list.dict.attr)

**Use Cases:**

- Navigate complex JSON responses from APIs
- Access specific elements in arrays
- Extract nested configuration values
- Traverse mixed data structures

---

### `SingleConditionEvaluator`

Evaluates individual conditions using various comparison operators.

**Purpose:** Provides comprehensive operator support for evaluating single conditions against values, including numeric
comparisons, string operations, pattern matching, and list membership.

**Responsibilities:**

- Evaluate numeric comparisons (==, !=, >, <, >=, <=)
- Evaluate string comparisons and patterns (contains, starts_with, ends_with, matches)
- Check string emptiness (is_empty, is_not_empty)
- Test list membership (in, not_in)
- Auto-detect numeric vs string comparison based on value type
- Support regex pattern matching

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise the single condition evaluator."""
```

**Key Methods:**

#### `evaluate()`

Evaluate a single condition against a value.

```python
def evaluate(
    self,
    value: Any,
    condition: Any,
) -> bool:
    """Evaluate a single condition against a value."""
```

**Parameters:**

- `value` (Any) - The value to evaluate
- `condition` (Any) - Condition configuration with operator and compare value

**Returns:**

- `bool` - True if condition is met, False otherwise

**Example:**

```python
from backend.services.conditions import SingleConditionEvaluator

evaluator = SingleConditionEvaluator()

# Numeric comparison
condition = {
    'operator': '>=',
    'value': 18,
    'value_type': 'number'
}
result = evaluator.evaluate(21, condition)
print(result)  # True

# String pattern matching
condition = {
    'operator': 'contains',
    'value': 'error',
    'value_type': 'string'
}
result = evaluator.evaluate("An error occurred", condition)
print(result)  # True

# Regex matching
condition = {
    'operator': 'matches',
    'value': r'^[A-Z]{3}-\d{4}$',
    'value_type': 'string'
}
result = evaluator.evaluate("ABC-1234", condition)
print(result)  # True

# List membership
condition = {
    'operator': 'in',
    'value': ['pending', 'processing', 'completed'],
    'value_type': 'string'
}
result = evaluator.evaluate("processing", condition)
print(result)  # True
```

**Behaviour:**

- Determines evaluation strategy based on value_type (number, string, auto)
- For numeric: converts values to float and compares
- For string: converts to string and applies operator
- Auto mode: detects numeric values and uses appropriate comparison
- Case-insensitive string matching for contains, starts_with, ends_with
- Returns False if type conversion fails

**Use Cases:**

- Validate numeric thresholds (age >= 18, count > 0)
- Check string patterns (email format, ID format)
- Test content inclusion (error messages, keywords)
- Verify field presence (is_not_empty)
- Check enum membership (status in allowed_values)

---

**Supported Operators:**

**Numeric Operators:**

- `==` - Equals
- `!=` - Not equals
- `>` - Greater than
- `<` - Less than
- `>=` - Greater than or equal
- `<=` - Less than or equal

**String Operators:**

- `==` - Exact match
- `!=` - Not equal
- `contains` - Contains substring (case-insensitive)
- `not_contains` - Does not contain substring (case-insensitive)
- `starts_with` - Starts with prefix (case-insensitive)
- `ends_with` - Ends with suffix (case-insensitive)
- `is_empty` - String is empty or whitespace-only
- `is_not_empty` - String is not empty
- `matches` - Matches regex pattern

**List Operators:**

- `in` - Value is in list
- `not_in` - Value is not in list

---

### `BranchConditionEvaluator`

Evaluates conditions specifically for multi-branch routing scenarios.

**Purpose:** Coordinates value extraction and condition evaluation for multi-branch routing, delegating to
ValueExtractor and SingleConditionEvaluator.

**Responsibilities:**

- Extract values for branch conditions
- Evaluate branch conditions using single condition evaluator
- Support all input sources for branch-specific routing
- Handle both dict and dataclass branch configurations

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise the branch condition evaluator."""
```

**Key Methods:**

#### `evaluate()`

Evaluate a branch condition to determine if the branch should be taken.

```python
def evaluate(
    self,
    state: WorkflowState,
    branch_condition: Any,
) -> bool:
    """Evaluate a branch condition."""
```

**Parameters:**

- `state` (WorkflowState) - The current workflow state
- `branch_condition` (Any) - Branch condition configuration

**Returns:**

- `bool` - True if branch condition is met, False otherwise

**Example:**

```python
from backend.services.conditions import BranchConditionEvaluator
from backend.services.workflow.state import WorkflowState

evaluator = BranchConditionEvaluator()

state = WorkflowState(
    node_outputs={
        'classifier': {
            'fields': {'priority': 'high', 'score': 95}
        }
    }
)

# Branch condition for high priority items
branch_condition = {
    'input_source': 'specific',
    'source_node_id': 'classifier',
    'field_path': 'priority',
    'operator': '==',
    'value': 'high'
}

result = evaluator.evaluate(state, branch_condition)
print(f"Take this branch: {result}")  # True
```

**Behaviour:**

- Extracts value from state using branch condition's input source
- Delegates to SingleConditionEvaluator for actual comparison
- Supports all input sources (specific, previous, start, static)
- Returns boolean result for branch selection

**Use Cases:**

- Evaluate conditions for each branch in multi-way routing
- Support switch/case-like workflow logic
- Enable priority-based routing
- Classify and route based on data attributes

---

**Class Attributes:**

- `value_extractor: ValueExtractor` - Extracts values from workflow state
- `single_evaluator: SingleConditionEvaluator` - Evaluates conditions

---

### `ExpressionConditionEvaluator`

Safely evaluates Python expression-based conditions using AST validation.

**Purpose:** Provides safe evaluation of user-defined Python expressions by using AST (Abstract Syntax Tree) visitor
pattern to whitelist allowed operations and prevent code injection attacks.

**Responsibilities:**

- Parse Python expressions into AST
- Validate that only safe operations are used
- Evaluate expressions in a restricted context
- Prevent code injection and malicious operations
- Provide access to workflow state in expression context
- Handle evaluation errors gracefully

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise the expression condition evaluator."""
```

**Key Methods:**

#### `evaluate()`

Safely evaluate a Python expression condition using AST validation.

```python
def evaluate(
    self,
    state: WorkflowState,
    condition_config: Any,
) -> bool:
    """Evaluate a Python expression condition safely."""
```

**Parameters:**

- `state` (WorkflowState) - The workflow state providing evaluation context
- `condition_config` (Any) - Configuration containing the expression string

**Returns:**

- `bool` - True if expression evaluates to truthy value, False otherwise

**Example:**

```python
from backend.services.conditions import ExpressionConditionEvaluator
from backend.services.workflow.state import WorkflowState

evaluator = ExpressionConditionEvaluator()

state = WorkflowState(
    node_outputs={
        'validator': {
            'fields': {
                'score': 85,
                'threshold': 70,
                'status': 'active'
            }
        }
    },
    original_message="Process this request"
)

# Complex expression with multiple conditions
condition_config = {
    'expression': """
    node_outputs['validator']['fields']['score'] >= node_outputs['validator']['fields']['threshold']
    and node_outputs['validator']['fields']['status'] == 'active'
    """
}

result = evaluator.evaluate(state, condition_config)
print(f"Expression result: {result}")  # True

# Using safe built-in functions
condition_config = {
    'expression': "len(original_message) > 10 and 'request' in original_message.lower()"
}

result = evaluator.evaluate(state, condition_config)
print(f"Expression result: {result}")  # True
```

**Behaviour:**

- Builds evaluation context with access to messages, node_outputs, original_message
- Creates SafeExpressionEvaluator with whitelist of allowed operations
- Parses expression into AST
- Validates each node in AST against whitelist
- Evaluates expression if all operations are safe
- Returns False and logs warning if evaluation fails
- Prevents access to **dunder** attributes for security

**Use Cases:**

- Complex boolean logic not supported by simple operators
- Mathematical calculations in routing decisions
- Nested data structure access with conditions
- Combining multiple checks with and/or/not operators
- Using safe built-in functions (len, str, int, float, etc.)

---

**Whitelisted Operations:**

**Comparison Operators:**

- `==`, `!=`, `<`, `<=`, `>`, `>=` - Standard comparisons
- `in`, `not in` - Membership testing
- `is`, `is not` - Identity testing

**Boolean Operators:**

- `and` - Logical AND
- `or` - Logical OR
- `not` - Logical NOT

**Arithmetic Operators:**

- `+`, `-`, `*`, `/`, `//`, `%`, `**` - Standard arithmetic

**Safe Functions:**

- `len()` - Length of sequence
- `str()`, `int()`, `float()`, `bool()` - Type conversions
- `abs()` - Absolute value
- `min()`, `max()` - Min/max values
- `sum()` - Sum of sequence
- `round()` - Round numbers

**Data Structures:**

- List literals: `[1, 2, 3]`
- Tuple literals: `(1, 2, 3)`
- Dict literals: `{'key': 'value'}`
- Subscript access: `data['key']`, `list[0]`
- Attribute access: `obj.attr` (except **dunder**)

**Control Flow:**

- Ternary expressions: `value if condition else other_value`

---

### `SafeExpressionEvaluator`

AST-based safe expression evaluator (used internally by ExpressionConditionEvaluator).

**Purpose:** Implements the AST NodeVisitor pattern to safely evaluate Python expressions by whitelisting allowed
operations and rejecting potentially dangerous operations.

**Responsibilities:**

- Visit AST nodes and evaluate whitelisted operations
- Reject disallowed operations with clear error messages
- Prevent code injection attacks
- Block access to dangerous attributes and functions
- Provide controlled access to evaluation context

**Initialisation:**

```python
def __init__(
    self,
    context: dict,
) -> None:
    """
    Initialise the safe evaluator.

    Args:
        context: Variable context for evaluation (available variables)
    """
```

**Key Methods:**

#### `evaluate()`

Safely evaluate an expression string.

```python
def evaluate(
    self,
    expression: str,
) -> Any:
    """Safely evaluate an expression."""
```

**Parameters:**

- `expression` (str) - The Python expression to evaluate

**Returns:**

- `Any` - The evaluation result

**Raises:**

- `ValueError` - If expression contains disallowed operations
- `SyntaxError` - If expression has invalid Python syntax
- `NameError` - If undefined variables are referenced

**Example:**

```python
from backend.services.conditions.evaluators.expression import SafeExpressionEvaluator

context = {
    'count': 42,
    'status': 'active',
    'data': {'value': 100}
}

evaluator = SafeExpressionEvaluator(context)

# Safe expression
result = evaluator.evaluate("count > 40 and status == 'active'")
print(result)  # True

# Safe function usage
result = evaluator.evaluate("len(status) + data['value']")
print(result)  # 106

# Unsafe expression (will raise ValueError)
try:
    result = evaluator.evaluate("__import__('os').system('ls')")
except ValueError as e:
    print(f"Rejected: {e}")  # "Operation 'Call' is not allowed..."
```

**Behaviour:**

- Parses expression into AST
- Walks AST tree visiting each node
- Calls appropriate visit method for each node type
- Whitelisted nodes are evaluated normally
- Non-whitelisted nodes raise ValueError
- Returns final evaluation result

**Use Cases:**

- Internal use by ExpressionConditionEvaluator
- Safe evaluation of user-provided expressions
- Controlled expression evaluation in restricted environments

---

### `LLMConditionEvaluator`

Uses Language Model reasoning to make intelligent routing decisions.

**Purpose:** Leverages LLM capabilities to make context-aware routing decisions that would be difficult or impossible to
express with simple conditions or expressions.

**Responsibilities:**

- Format prompts with workflow context
- Invoke LLM with configured model
- Parse LLM responses to extract routing decisions
- Support both binary and multi-branch routing
- Handle LLM errors gracefully
- Use graph_manager to access LLM instances

**Initialisation:**

```python
def __init__(
    self,
    graph_manager,
) -> None:
    """
    Initialise the LLM condition evaluator.

    Args:
        graph_manager: GraphManager instance for getting LLM instances
    """
```

**Key Methods:**

#### `evaluate()`

Evaluate a condition using LLM reasoning.

```python
def evaluate(
    self,
    state: WorkflowState,
    condition_config: Any,
    graph: Any,
) -> str:
    """Evaluate a condition using an LLM."""
```

**Parameters:**

- `state` (WorkflowState) - The current workflow state
- `condition_config` (Any) - Configuration with LLM prompt and settings
- `graph` (Any) - The graph containing default LLM config

**Returns:**

- `str` - Routing decision ("true"/"false" for binary, or branch index for multi-branch)

**Raises:**

- `Exception` - If LLM invocation fails (caught and logged, returns "false")

**Example:**

```python
from backend.services.conditions import LLMConditionEvaluator
from backend.services.workflow.state import WorkflowState
from backend.services.graph import GraphManager

graph_manager = GraphManager()
evaluator = LLMConditionEvaluator(graph_manager)

# Sentiment analysis example
state = WorkflowState(
    messages=[
        type('Message', (), {'content': 'This product is absolutely terrible! I want a refund immediately!'})()
    ],
    original_message="This product is absolutely terrible! I want a refund immediately!"
)

condition_config = {
    'llm_prompt': """
    Analyse the sentiment of this customer message: '{last_message}'

    Determine if the customer is:
    1. Satisfied (positive sentiment)
    2. Neutral (no strong sentiment)
    3. Dissatisfied (negative sentiment)

    Return ONLY the number (1, 2, or 3) corresponding to the sentiment.
    """,
    'llm_config': {
        'provider': 'openai',
        'model': 'gpt-4'
    },
    'branch_labels': ['satisfied', 'neutral', 'dissatisfied']
}

graph = type('Graph', (), {'llm_config': condition_config['llm_config']})()

result = evaluator.evaluate(state, condition_config, graph)
print(f"Route to branch: {result}")  # "2" (dissatisfied)
```

**Behaviour:**

- Formats LLM prompt with placeholders: {last_message}, {original_message}, {node_outputs}
- Invokes LLM using graph_manager.get_llm()
- Extracts text from LLM response (handles both content attribute and string)
- For multi-branch: searches for branch labels in response and returns index
- For binary: searches for "true"/"yes" or "false"/"no" in response
- Falls back to "false" on error or ambiguous response
- Logs errors but doesn't raise exceptions

**Use Cases:**

- Sentiment analysis for customer support routing
- Content classification based on semantic understanding
- Intent detection from natural language
- Quality assessment of generated content
- Context-aware decision making beyond rule-based logic
- Language detection and routing
- Topic categorisation
- Urgency or priority assessment

---

**Class Attributes:**

- `graph_manager: GraphManager` - Manager for accessing LLM instances

---

## Configuration

### Configuration Classes

The conditions service doesn't define explicit configuration classes. Instead, it accepts configuration as dictionaries
or dataclasses with the following structures:

**Binary Condition Configuration:**

```python
{
    "branch_mode": "binary",  # "binary" or "multi"
    "condition_type": "simple",  # "simple", "expression", or "llm"
    "input_source": "specific",  # "previous", "specific", "start", or "static"
    "source_node_id": "node_id",  # Required if input_source is "specific"
    "field_path": "field.nested.path",  # Optional dot notation path
    "simple_conditions": [
        {
            "operator": "==",  # Comparison operator
            "value": "expected_value",  # Value to compare against
            "value_type": "string"  # "string", "number", or "auto"
        }
    ],
    "logic_operator": "AND"  # "AND" or "OR" for multiple conditions
}
```

**Multi-Branch Condition Configuration:**

```python
{
    "branch_mode": "multi",
    "branches": [
        {
            "handle_id": "branch-1",
            "label": "High Priority",
            "condition": {
                "input_source": "specific",
                "source_node_id": "classifier",
                "field_path": "priority",
                "operator": "==",
                "value": "high"
            }
        },
        {
            "handle_id": "branch-2",
            "label": "Low Priority",
            "condition": {
                "input_source": "specific",
                "source_node_id": "classifier",
                "field_path": "priority",
                "operator": "==",
                "value": "low"
            }
        }
    ]
}
```

**Expression Condition Configuration:**

```python
{
    "condition_type": "expression",
    "expression": "node_outputs['validator']['score'] >= 70 and len(messages) > 0"
}
```

**LLM Condition Configuration:**

```python
{
    "condition_type": "llm",
    "llm_prompt": "Analyse this: '{last_message}'. Is it urgent? Answer yes or no.",
    "llm_config": {
        "provider": "openai",
        "model": "gpt-4",
        "temperature": 0.0
    },
    "branch_labels": []  # Optional: for multi-branch LLM routing
}
```

### Environment Variables

None - this service does not use environment variables.

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.conditions import ConditionEvaluator

# For simple, expression-based conditions (no LLM)
evaluator = ConditionEvaluator()
```

**Advanced Initialisation:**

```python
from backend.services.conditions import ConditionEvaluator, ConditionFunctionFactory
from backend.services.graph import GraphManager

# For LLM-based conditions
graph_manager = GraphManager()
evaluator = ConditionEvaluator(graph_manager)

# Create factory for generating condition functions
factory = ConditionFunctionFactory(evaluator)
```

**Dependency Injection:**

```python
# In ConditionNodeExecutor
class ConditionNodeExecutor(BaseNodeExecutor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Inject graph_manager from kwargs
        self.condition_evaluator = ConditionEvaluator(kwargs.get("graph_manager"))
```

## Error Handling

### Exception Hierarchy

The conditions service uses standard Python exceptions:

```
Exception
├── ValueError
│   ├── Invalid operators in expressions
│   ├── Disallowed AST operations
│   ├── Malformed condition configuration
│   └── LLM evaluator not initialised
├── SyntaxError
│   └── Invalid Python expression syntax
├── NameError
│   └── Undefined variables in expressions
├── TypeError
│   └── Type mismatches during evaluation
└── AttributeError
    └── Invalid attribute access
```

### Exception Details

#### `ValueError`

Raised when condition configuration is invalid or expressions contain disallowed operations.

**When raised:**

- Expression contains non-whitelisted AST operations (e.g., import, exec, eval)
- LLM evaluator is used without graph_manager initialisation
- Function calls to non-whitelisted functions in expressions
- Subscript or attribute access fails

**Example:**

```python
from backend.services.conditions import ExpressionConditionEvaluator

evaluator = ExpressionConditionEvaluator()

try:
    result = evaluator.evaluate(state, {
        'expression': '__import__("os").system("ls")'  # Dangerous!
    })
except ValueError as e:
    print(f"Security violation: {e}")
    # "Operation 'Call' is not allowed for security reasons"
```

#### `SyntaxError`

Raised when a Python expression has invalid syntax.

**When raised:**

- Expression string is not valid Python
- Unmatched parentheses or brackets
- Invalid operator usage

**Example:**

```python
from backend.services.conditions import ExpressionConditionEvaluator

evaluator = ExpressionConditionEvaluator()

try:
    result = evaluator.evaluate(state, {
        'expression': 'count > 10 and and status == "active"'  # Invalid syntax
    })
except SyntaxError as e:
    print(f"Syntax error: {e}")
```

#### `NameError`

Raised when an expression references undefined variables.

**When raised:**

- Variable name in expression doesn't exist in context
- Typo in variable name

**Example:**

```python
from backend.services.conditions import ExpressionConditionEvaluator

evaluator = ExpressionConditionEvaluator()

try:
    result = evaluator.evaluate(state, {
        'expression': 'undefined_variable > 10'  # Variable doesn't exist
    })
except NameError as e:
    print(f"Undefined variable: {e}")
    # "Name 'undefined_variable' is not defined"
```

### Error Handling Patterns

**Recommended Pattern:**

```python
from backend.services.conditions import (
    ConditionEvaluator,
    ExpressionConditionEvaluator,
)
from backend.services.workflow.state import WorkflowState

evaluator = ConditionEvaluator()

try:
    # Evaluate condition
    result = evaluator.evaluate_binary_condition(state, condition_config)

    # Use result for routing
    if result:
        next_node = "success_path"
    else:
        next_node = "failure_path"

except ValueError as e:
    # Handle configuration errors
    logger.error(f"Invalid condition configuration: {e}")
    next_node = "error_handler"

except (SyntaxError, NameError) as e:
    # Handle expression errors
    logger.error(f"Expression evaluation failed: {e}")
    next_node = "default_path"

except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error in condition evaluation: {e}")
    next_node = "default_path"
```

**Expression Evaluation with Fallback:**

```python
from backend.services.conditions import ExpressionConditionEvaluator

evaluator = ExpressionConditionEvaluator()

def safe_evaluate_expression(state, expression):
    """Safely evaluate expression with fallback to False."""
    try:
        config = {'expression': expression}
        return evaluator.evaluate(state, config)
    except (ValueError, SyntaxError, NameError, TypeError) as e:
        logger.warning(f"Expression evaluation failed: {e}, defaulting to False")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in expression evaluation: {e}")
        return False

# Use with confidence
result = safe_evaluate_expression(state, user_expression)
```

**LLM Evaluation with Retry:**

```python
from backend.services.conditions import LLMConditionEvaluator

def evaluate_with_retry(evaluator, state, config, graph, max_retries=3):
    """Evaluate LLM condition with retry logic."""
    for attempt in range(max_retries):
        try:
            result = evaluator.evaluate(state, config, graph)
            return result
        except Exception as e:
            logger.warning(f"LLM evaluation attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("All LLM evaluation attempts failed, using default")
                return "false"
    return "false"
```

## Integration Patterns

### Integration with Node Executors

The primary integration point is through the ConditionNodeExecutor which uses ConditionEvaluator to process condition
nodes:

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.nodes.executors import BaseNodeExecutor

class ConditionNodeExecutor(BaseNodeExecutor):
    """Executor for CONDITION nodes."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialise with graph_manager for LLM support
        self.condition_evaluator = ConditionEvaluator(kwargs.get("graph_manager"))

    async def execute(self, node, state, graph, execution_id, user_id=None):
        """Execute condition node and determine routing."""
        # Evaluate based on condition type
        if node.condition_config.branch_mode == "multi":
            result = self.condition_evaluator.evaluate_multi_branch(
                state,
                node.condition_config.branches
            )
        elif node.condition_config.condition_type == "expression":
            result = self.condition_evaluator.evaluate_expression(
                state,
                node.condition_config
            )
        elif node.condition_config.condition_type == "llm":
            result = self.condition_evaluator.evaluate_llm(
                state,
                node.condition_config,
                graph
            )
        else:
            result = self.condition_evaluator.evaluate_binary_condition(
                state,
                node.condition_config
            )

        # Store result for condition function
        state[f"__condition_result_{node.uniq_id}"] = result

        return {"condition_result": result}
```

### Integration with Execution Engine

The ExecutionEngine uses ConditionFunctionFactory to create LangGraph conditional edges:

```python
from backend.services.conditions import ConditionEvaluator, ConditionFunctionFactory
from backend.services.execution.engine import ExecutionEngine

class ExecutionEngine:
    """Main execution coordinator."""

    def __init__(self, graph_manager):
        self.graph_manager = graph_manager

        # Initialise condition services
        self.condition_evaluator = ConditionEvaluator(graph_manager)
        self.condition_factory = ConditionFunctionFactory(self.condition_evaluator)

    def build_graph(self, workflow_def):
        """Build LangGraph from workflow definition."""
        from langgraph.graph import StateGraph

        graph_builder = StateGraph(WorkflowState)

        # Add nodes...
        for node in workflow_def.nodes:
            if node.type == "CONDITION":
                # Create condition function for this node
                condition_func = self.condition_factory.create_condition_function(
                    node,
                    workflow_def
                )

                # Add conditional edge
                graph_builder.add_conditional_edges(
                    source=previous_node,
                    path=condition_func,
                    path_map={
                        "true": true_branch_node,
                        "false": false_branch_node,
                    }
                )

        return graph_builder.compile()
```

### Integration with Workflow State

The conditions service reads from and writes to WorkflowState:

```python
from backend.services.workflow.state import WorkflowState

# Reading from state
state = WorkflowState(
    messages=[...],
    node_outputs={
        "node_1": {
            "raw": "output text",
            "fields": {"key": "value"},
            "structured_output": {...}
        }
    },
    original_message="User input"
)

# Conditions extract values from state
from backend.services.conditions import ValueExtractor

extractor = ValueExtractor()
value = extractor.extract(state, {
    'input_source': 'specific',
    'source_node_id': 'node_1',
    'field_path': 'key'
})

# Conditions write results to state
state[f"__condition_result_{node_id}"] = "true"

# Condition function reads cached result
cached_result = state.get(f"__condition_result_{node_id}")
```

### Dependency Flow

```
API Layer (routes.py)
    ↓
ExecutionEngine
    ↓
ConditionFunctionFactory ← creates → Callable[[WorkflowState], str]
    ↓                                       ↓
ConditionEvaluator                   LangGraph Conditional Edge
    ↓
┌───────────┬───────────────┬────────────────┐
↓           ↓               ↓                ↓
Value     Single        Expression         LLM
Extractor Evaluator     Evaluator       Evaluator
                                           ↓
                                     GraphManager (for LLM access)
```

**Services that depend on conditions:**

- `backend.services.nodes.executors.condition` - ConditionNodeExecutor
- `backend.services.execution.engine` - ExecutionEngine

**Services that conditions depends on:**

- `backend.services.workflow.state` - WorkflowState definition
- `backend.services.execution.logging` - Logging utilities
- `backend.services.graph` - GraphManager (optional, for LLM)

### Common Integration Patterns

#### Pattern 1: Binary Routing

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

evaluator = ConditionEvaluator()

def route_by_status(state: WorkflowState) -> str:
    """Route based on status field."""
    condition_config = {
        'input_source': 'specific',
        'source_node_id': 'processor',
        'field_path': 'status',
        'simple_conditions': [{
            'operator': '==',
            'value': 'success',
            'value_type': 'string'
        }],
        'logic_operator': 'AND'
    }

    result = evaluator.evaluate_binary_condition(state, condition_config)
    return "success_handler" if result else "error_handler"
```

#### Pattern 2: Multi-Branch Classification

```python
from backend.services.conditions import ConditionEvaluator

evaluator = ConditionEvaluator()

def classify_priority(state: WorkflowState) -> str:
    """Classify and route by priority level."""
    branches = [
        {
            'handle_id': 'branch-critical',
            'condition': {
                'input_source': 'specific',
                'source_node_id': 'analyser',
                'field_path': 'priority_score',
                'operator': '>=',
                'value': 90,
                'value_type': 'number'
            }
        },
        {
            'handle_id': 'branch-high',
            'condition': {
                'input_source': 'specific',
                'source_node_id': 'analyser',
                'field_path': 'priority_score',
                'operator': '>=',
                'value': 70,
                'value_type': 'number'
            }
        },
        {
            'handle_id': 'branch-normal',
            'condition': {
                'input_source': 'specific',
                'source_node_id': 'analyser',
                'field_path': 'priority_score',
                'operator': '>=',
                'value': 30,
                'value_type': 'number'
            }
        }
    ]

    branch_id = evaluator.evaluate_multi_branch(state, branches)

    # Map to handler nodes
    priority_map = {
        'critical': 'critical_handler',
        'high': 'high_priority_handler',
        'normal': 'normal_handler',
        '0': 'low_priority_handler'  # default
    }

    return priority_map.get(branch_id.replace('branch-', ''), 'low_priority_handler')
```

#### Pattern 3: Expression-Based Complex Logic

```python
from backend.services.conditions import ExpressionConditionEvaluator

evaluator = ExpressionConditionEvaluator()

def complex_routing(state: WorkflowState) -> str:
    """Route using complex expression logic."""
    condition_config = {
        'expression': """
        (node_outputs['validator']['fields']['score'] >= 80
         and len(messages) > 2)
        or
        (node_outputs['validator']['fields']['override'] == True
         and node_outputs['validator']['fields']['status'] == 'approved')
        """
    }

    result = evaluator.evaluate(state, condition_config)
    return "proceed" if result else "review_required"
```

#### Pattern 4: LLM-Based Intelligent Routing

```python
from backend.services.conditions import LLMConditionEvaluator
from backend.services.graph import GraphManager

graph_manager = GraphManager()
evaluator = LLMConditionEvaluator(graph_manager)

def sentiment_routing(state: WorkflowState, graph) -> str:
    """Route based on LLM sentiment analysis."""
    condition_config = {
        'llm_prompt': """
        Analyse the sentiment of this customer message: '{last_message}'

        Classify as:
        - positive: Customer is happy or satisfied
        - neutral: No strong emotion
        - negative: Customer is unhappy or frustrated

        Return ONLY one word: positive, neutral, or negative.
        """,
        'llm_config': graph.llm_config,
        'branch_labels': ['positive', 'neutral', 'negative']
    }

    result = evaluator.evaluate(state, condition_config, graph)

    # Map to handler nodes
    sentiment_map = {
        '0': 'positive_response_handler',
        '1': 'standard_response_handler',
        '2': 'escalation_handler'
    }

    return sentiment_map.get(result, 'standard_response_handler')
```

## Usage Examples

### Example 1: Basic Binary Condition

Complete end-to-end example of evaluating a simple binary condition:

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

# Step 1: Initialise evaluator
evaluator = ConditionEvaluator()

# Step 2: Create workflow state with data
state = WorkflowState(
    messages=[],
    node_outputs={
        "data_processor": {
            "raw": "Processing completed successfully",
            "fields": {
                "status": "success",
                "records_processed": 150,
                "errors": 0
            }
        }
    },
    original_message="Process the data file"
)

# Step 3: Define condition configuration
condition_config = {
    "input_source": "specific",
    "source_node_id": "data_processor",
    "field_path": "status",
    "simple_conditions": [
        {
            "operator": "==",
            "value": "success",
            "value_type": "string"
        }
    ],
    "logic_operator": "AND"
}

# Step 4: Evaluate condition
result = evaluator.evaluate_binary_condition(state, condition_config)

# Step 5: Use result for routing decision
if result:
    print("Routing to success handler")
    next_node = "success_notification"
else:
    print("Routing to error handler")
    next_node = "error_recovery"
```

### Example 2: Multi-Branch Routing

Complete example showing multi-branch classification and routing:

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

# Step 1: Initialise evaluator
evaluator = ConditionEvaluator()

# Step 2: Create state with classification data
state = WorkflowState(
    node_outputs={
        "content_classifier": {
            "fields": {
                "category": "technical_support",
                "confidence": 0.95,
                "language": "en"
            }
        }
    }
)

# Step 3: Define branches with conditions
branches = [
    {
        "handle_id": "branch-sales",
        "label": "Sales Inquiry",
        "condition": {
            "input_source": "specific",
            "source_node_id": "content_classifier",
            "field_path": "category",
            "operator": "==",
            "value": "sales"
        }
    },
    {
        "handle_id": "branch-support",
        "label": "Technical Support",
        "condition": {
            "input_source": "specific",
            "source_node_id": "content_classifier",
            "field_path": "category",
            "operator": "==",
            "value": "technical_support"
        }
    },
    {
        "handle_id": "branch-billing",
        "label": "Billing Question",
        "condition": {
            "input_source": "specific",
            "source_node_id": "content_classifier",
            "field_path": "category",
            "operator": "==",
            "value": "billing"
        }
    }
]

# Step 4: Evaluate multi-branch condition
branch_result = evaluator.evaluate_multi_branch(state, branches)

# Step 5: Map to handler nodes
branch_handlers = {
    "sales": "sales_team_handler",
    "support": "technical_support_handler",
    "billing": "billing_department_handler",
    "0": "general_inquiry_handler"  # default
}

# Get handler based on result
handler_node = branch_handlers.get(branch_result, "general_inquiry_handler")
print(f"Routing to: {handler_node}")
```

### Example 3: Complex Expression Evaluation

Show advanced expression-based routing with complex logic:

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

# Step 1: Initialise evaluator
evaluator = ConditionEvaluator()

# Step 2: Create state with complex data
state = WorkflowState(
    messages=[
        type('Message', (), {'role': 'user', 'content': 'Process my order'})(),
        type('Message', (), {'role': 'assistant', 'content': 'Processing...'})(),
        type('Message', (), {'role': 'system', 'content': 'Validation complete'})()
    ],
    node_outputs={
        "order_validator": {
            "fields": {
                "total_amount": 1250.00,
                "item_count": 5,
                "customer_tier": "premium",
                "requires_approval": False,
                "risk_score": 15
            }
        },
        "inventory_check": {
            "fields": {
                "all_items_available": True,
                "estimated_ship_date": "2025-10-27"
            }
        }
    },
    original_message="Process my order for 5 items"
)

# Step 3: Define complex expression condition
condition_config = {
    "expression": """
    (node_outputs['order_validator']['fields']['total_amount'] < 2000.0
     and node_outputs['order_validator']['fields']['customer_tier'] == 'premium'
     and node_outputs['order_validator']['fields']['requires_approval'] == False)
    or
    (node_outputs['order_validator']['fields']['risk_score'] < 20
     and node_outputs['inventory_check']['fields']['all_items_available'] == True
     and len(messages) >= 2)
    """
}

# Step 4: Evaluate expression
result = evaluator.evaluate_expression(state, condition_config)

# Step 5: Route based on result
if result:
    print("Order approved - proceeding to fulfilment")
    next_step = "auto_fulfil_order"
else:
    print("Order requires manual review")
    next_step = "manual_review_queue"

# Additional example: Using safe functions in expressions
numeric_condition = {
    "expression": """
    max(
        node_outputs['order_validator']['fields']['item_count'],
        len(messages)
    ) >= 5
    and abs(node_outputs['order_validator']['fields']['risk_score']) < 50
    """
}

numeric_result = evaluator.evaluate_expression(state, numeric_condition)
print(f"Numeric condition result: {numeric_result}")
```

### Example 4: LLM-Based Intelligent Routing

Complete workflow showing LLM-based decision making:

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState
from backend.services.graph import GraphManager

async def intelligent_routing_workflow():
    """Example showing LLM-based routing for customer service."""

    # Step 1: Initialise with graph_manager for LLM access
    graph_manager = GraphManager()
    evaluator = ConditionEvaluator(graph_manager)

    # Step 2: Create state with customer message
    state = WorkflowState(
        messages=[
            type('Message', (), {
                'role': 'user',
                'content': 'I ordered a laptop 3 weeks ago and it still hasn\'t arrived. This is completely unacceptable! I need it for work tomorrow. Can you expedite shipping or should I just cancel and order from your competitor?'
            })()
        ],
        node_outputs={
            "customer_lookup": {
                "fields": {
                    "customer_id": "CUST-12345",
                    "lifetime_value": 15000,
                    "account_age_days": 730,
                    "previous_issues": 1
                }
            }
        },
        original_message="I ordered a laptop 3 weeks ago and it still hasn't arrived..."
    )

    # Step 3: Define LLM routing configuration
    condition_config = {
        "condition_type": "llm",
        "llm_prompt": """
        Analyse this customer service interaction and determine the appropriate routing.

        Customer Message: '{last_message}'

        Customer Profile:
        - Lifetime Value: ${node_outputs[customer_lookup][fields][lifetime_value]}
        - Account Age: {node_outputs[customer_lookup][fields][account_age_days]} days
        - Previous Issues: {node_outputs[customer_lookup][fields][previous_issues]}

        Route to ONE of these options:
        1. immediate_escalation - High-value customer, urgent issue, showing frustration
        2. priority_support - Moderate urgency, needs quick resolution
        3. standard_support - Standard inquiry, normal processing
        4. automated_response - Simple question that can be handled automatically

        Respond with ONLY the routing option name.
        """,
        "llm_config": {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.0  # Low temperature for consistent routing
        },
        "branch_labels": [
            "immediate_escalation",
            "priority_support",
            "standard_support",
            "automated_response"
        ]
    }

    # Create graph with LLM config
    graph = type('Graph', (), {'llm_config': condition_config["llm_config"]})()

    # Step 4: Evaluate using LLM
    routing_decision = evaluator.evaluate_llm(state, condition_config, graph)

    # Step 5: Map to actual handler functions
    routing_map = {
        "0": {  # immediate_escalation
            "handler": "senior_support_specialist",
            "priority": "critical",
            "sla_hours": 1
        },
        "1": {  # priority_support
            "handler": "priority_queue",
            "priority": "high",
            "sla_hours": 4
        },
        "2": {  # standard_support
            "handler": "standard_queue",
            "priority": "normal",
            "sla_hours": 24
        },
        "3": {  # automated_response
            "handler": "chatbot",
            "priority": "low",
            "sla_hours": 48
        }
    }

    # Step 6: Execute routing
    handler_config = routing_map.get(routing_decision, routing_map["2"])

    print(f"LLM Routing Decision: {routing_decision}")
    print(f"Handler: {handler_config['handler']}")
    print(f"Priority: {handler_config['priority']}")
    print(f"SLA: {handler_config['sla_hours']} hours")

    return handler_config

# Run the workflow
# result = await intelligent_routing_workflow()
```

### Example 5: Creating Condition Functions for LangGraph

Show how to use ConditionFunctionFactory to create LangGraph-compatible functions:

```python
from backend.services.conditions import ConditionEvaluator, ConditionFunctionFactory
from backend.services.workflow.state import WorkflowState
from langgraph.graph import StateGraph

# Step 1: Initialise services
evaluator = ConditionEvaluator()
factory = ConditionFunctionFactory(evaluator)

# Step 2: Define condition nodes
quality_check_node = type('Node', (), {
    'uniq_id': 'quality_checker',
    'name': 'Quality Gate',
    'condition_config': {
        'branch_mode': 'binary',
        'condition_type': 'simple',
        'input_source': 'specific',
        'source_node_id': 'quality_analyser',
        'field_path': 'quality_score',
        'simple_conditions': [{
            'operator': '>=',
            'value': 85,
            'value_type': 'number'
        }],
        'logic_operator': 'AND'
    }
})()

content_router_node = type('Node', (), {
    'uniq_id': 'content_router',
    'name': 'Content Type Router',
    'condition_config': {
        'branch_mode': 'multi',
        'branches': [
            {
                'handle_id': 'branch-text',
                'label': 'Text Content',
                'condition': {
                    'input_source': 'specific',
                    'source_node_id': 'content_analyser',
                    'field_path': 'content_type',
                    'operator': '==',
                    'value': 'text'
                }
            },
            {
                'handle_id': 'branch-image',
                'label': 'Image Content',
                'condition': {
                    'input_source': 'specific',
                    'source_node_id': 'content_analyser',
                    'field_path': 'content_type',
                    'operator': '==',
                    'value': 'image'
                }
            },
            {
                'handle_id': 'branch-video',
                'label': 'Video Content',
                'condition': {
                    'input_source': 'specific',
                    'source_node_id': 'content_analyser',
                    'field_path': 'content_type',
                    'operator': '==',
                    'value': 'video'
                }
            }
        ]
    }
})()

graph_def = type('Graph', (), {'llm_config': None})()

# Step 3: Create condition functions
quality_condition = factory.create_condition_function(quality_check_node, graph_def)
content_route_condition = factory.create_condition_function(content_router_node, graph_def)

# Step 4: Build LangGraph with conditional edges
graph_builder = StateGraph(WorkflowState)

# Add nodes (simplified)
graph_builder.add_node("quality_analyser", lambda s: s)
graph_builder.add_node("high_quality_processor", lambda s: s)
graph_builder.add_node("needs_improvement", lambda s: s)
graph_builder.add_node("content_analyser", lambda s: s)
graph_builder.add_node("text_processor", lambda s: s)
graph_builder.add_node("image_processor", lambda s: s)
graph_builder.add_node("video_processor", lambda s: s)
graph_builder.add_node("default_processor", lambda s: s)

# Add conditional edges using created functions
graph_builder.add_conditional_edges(
    source="quality_analyser",
    path=quality_condition,
    path_map={
        "true": "high_quality_processor",
        "false": "needs_improvement"
    }
)

graph_builder.add_conditional_edges(
    source="content_analyser",
    path=content_route_condition,
    path_map={
        "text": "text_processor",
        "image": "image_processor",
        "video": "video_processor",
        "0": "default_processor"  # default branch
    }
)

# Step 5: Compile and test
graph_builder.set_entry_point("quality_analyser")
compiled_graph = graph_builder.compile()

# Test the graph
test_state = WorkflowState(
    node_outputs={
        "quality_analyser": {
            "fields": {"quality_score": 92}
        },
        "content_analyser": {
            "fields": {"content_type": "image"}
        }
    }
)

# Quality condition will return "true" (score 92 >= 85)
quality_result = quality_condition(test_state)
print(f"Quality check result: {quality_result}")  # "true"

# Content router will return "image"
content_result = content_route_condition(test_state)
print(f"Content routing result: {content_result}")  # "image"
```

### Example 6: Compound Conditions with AND/OR Logic

Show how to combine multiple conditions with logic operators:

```python
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

evaluator = ConditionEvaluator()

# Create state with multiple data points
state = WorkflowState(
    node_outputs={
        "user_validator": {
            "fields": {
                "age": 25,
                "account_verified": True,
                "country": "AU",
                "subscription_tier": "premium"
            }
        }
    }
)

# Example 1: AND logic - all conditions must be true
and_condition = {
    "input_source": "specific",
    "source_node_id": "user_validator",
    "field_path": "",  # Will check multiple fields
    "simple_conditions": [
        {
            "input_source": "specific",
            "source_node_id": "user_validator",
            "field_path": "age",
            "operator": ">=",
            "value": 18,
            "value_type": "number"
        },
        {
            "input_source": "specific",
            "source_node_id": "user_validator",
            "field_path": "account_verified",
            "operator": "==",
            "value": True,
            "value_type": "auto"
        },
        {
            "input_source": "specific",
            "source_node_id": "user_validator",
            "field_path": "subscription_tier",
            "operator": "in",
            "value": ["premium", "enterprise"],
            "value_type": "string"
        }
    ],
    "logic_operator": "AND"
}

and_result = evaluator.evaluate_binary_condition(state, and_condition)
print(f"AND condition (all must match): {and_result}")  # True

# Example 2: OR logic - any condition can be true
or_condition = {
    "input_source": "specific",
    "source_node_id": "user_validator",
    "field_path": "",
    "simple_conditions": [
        {
            "input_source": "specific",
            "source_node_id": "user_validator",
            "field_path": "subscription_tier",
            "operator": "==",
            "value": "enterprise",
            "value_type": "string"
        },
        {
            "input_source": "specific",
            "source_node_id": "user_validator",
            "field_path": "country",
            "operator": "in",
            "value": ["AU", "NZ", "UK"],
            "value_type": "string"
        },
        {
            "input_source": "specific",
            "source_node_id": "user_validator",
            "field_path": "age",
            "operator": ">",
            "value": 65,
            "value_type": "number"
        }
    ],
    "logic_operator": "OR"
}

or_result = evaluator.evaluate_binary_condition(state, or_condition)
print(f"OR condition (any can match): {or_result}")  # True (country matches)
```

## Performance Considerations

### Performance Characteristics

**ValueExtractor:**

- O(1) for direct field access
- O(n) for nested field path navigation where n is path depth
- O(1) for cached message access
- JSON parsing: O(m) where m is JSON string length

**SingleConditionEvaluator:**

- O(1) for all numeric comparisons
- O(n) for string contains/pattern matching where n is string length
- O(m) for regex matching where m is pattern complexity
- O(k) for list membership where k is list size

**ExpressionConditionEvaluator:**

- O(n) for AST parsing where n is expression length
- O(m) for AST evaluation where m is number of operations
- Typically very fast (<1ms) for simple expressions
- Complex nested expressions may take 5-10ms

**LLMConditionEvaluator:**

- O(1) for prompt formatting
- O(API latency) for LLM invocation (typically 500ms-5s)
- Network-bound, not CPU-bound
- Dominated by LLM API call time

**ConditionEvaluator:**

- Binary: O(k * c) where k is number of simple_conditions, c is condition complexity
- Multi-branch: O(n * c) where n is number of branches, c is condition complexity
- Expression: O(AST size)
- LLM: O(API latency)

### Optimisation Tips

#### Tip 1: Cache LLM Results

**Problem:**

```python
# Re-evaluates LLM condition every time (expensive!)
for iteration in range(5):
    result = evaluator.evaluate_llm(state, config, graph)
```

**Solution:**

```python
# Store result in state for reuse
def get_cached_llm_result(evaluator, state, config, graph, cache_key):
    """Use state caching to avoid repeated LLM calls."""
    cached = state.get(f"__llm_cache_{cache_key}")
    if cached is not None:
        return cached

    result = evaluator.evaluate_llm(state, config, graph)
    state[f"__llm_cache_{cache_key}"] = result
    return result

# Use cached version
for iteration in range(5):
    result = get_cached_llm_result(evaluator, state, config, graph, "sentiment_check")
```

#### Tip 2: Order Branches by Likelihood

**Problem:**

```python
# Rare conditions checked first
branches = [
    {"condition": rare_edge_case_1},  # 1% match rate
    {"condition": rare_edge_case_2},  # 2% match rate
    {"condition": common_case},       # 80% match rate
    {"condition": another_common},    # 15% match rate
]
```

**Solution:**

```python
# Order by likelihood - most common first
branches = [
    {"condition": common_case},       # 80% match rate - checked first
    {"condition": another_common},    # 15% match rate - checked second
    {"condition": rare_edge_case_2},  # 2% match rate
    {"condition": rare_edge_case_1},  # 1% match rate
]

# Multi-branch short-circuits on first match
result = evaluator.evaluate_multi_branch(state, branches)
```

#### Tip 3: Use Simple Conditions Over Expressions When Possible

**Problem:**

```python
# Expression evaluation requires AST parsing
condition_config = {
    "expression": "node_outputs['node1']['fields']['status'] == 'success'"
}
result = evaluator.evaluate_expression(state, condition_config)
```

**Solution:**

```python
# Simple condition is faster (no AST parsing)
condition_config = {
    "input_source": "specific",
    "source_node_id": "node1",
    "field_path": "status",
    "simple_conditions": [{
        "operator": "==",
        "value": "success",
        "value_type": "string"
    }],
    "logic_operator": "AND"
}
result = evaluator.evaluate_binary_condition(state, condition_config)
```

#### Tip 4: Minimise Field Path Depth

**Problem:**

```python
# Deep nesting requires multiple dictionary lookups
config = {
    "input_source": "specific",
    "source_node_id": "processor",
    "field_path": "data.results.items.0.details.metadata.status"
}
value = extractor.extract(state, config)
```

**Solution:**

```python
# Flatten data structure when possible
# Store flattened data in node output
state.node_outputs["processor"]["fields"] = {
    "status": "success",  # Direct access
    "item_count": 42
}

config = {
    "input_source": "specific",
    "source_node_id": "processor",
    "field_path": "status"  # Single level
}
value = extractor.extract(state, config)
```

### Async/Await Support

The conditions service is currently **synchronous**. LLM evaluations use synchronous LLM.invoke():

```python
# Current: Synchronous
result = evaluator.evaluate_llm(state, condition_config, graph)
```

For async workflows, wrap in async functions:

```python
from backend.services.conditions import ConditionEvaluator

async def async_evaluate_llm(evaluator, state, config, graph):
    """Async wrapper for LLM evaluation."""
    # Run synchronous evaluation in executor
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        evaluator.evaluate_llm,
        state,
        config,
        graph
    )
    return result

# Usage
evaluator = ConditionEvaluator(graph_manager)
result = await async_evaluate_llm(evaluator, state, config, graph)
```

### Batch Operations

The service doesn't currently support batch evaluation, but you can implement it:

```python
from backend.services.conditions import ConditionEvaluator

def evaluate_batch(evaluator, states, condition_config):
    """Evaluate same condition across multiple states."""
    results = []
    for state in states:
        result = evaluator.evaluate_binary_condition(state, condition_config)
        results.append(result)
    return results

# Usage
states = [state1, state2, state3, state4]
results = evaluate_batch(evaluator, states, condition_config)
```

For parallel processing:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def evaluate_batch_parallel(evaluator, states, condition_config, max_workers=5):
    """Evaluate conditions in parallel."""
    loop = asyncio.get_event_loop()

    def evaluate_one(state):
        return evaluator.evaluate_binary_condition(state, condition_config)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            loop.run_in_executor(executor, evaluate_one, state)
            for state in states
        ]
        results = await asyncio.gather(*futures)

    return results

# Usage
results = await evaluate_batch_parallel(evaluator, states, condition_config)
```

## Testing Patterns

### Unit Testing

```python
import pytest
from backend.services.conditions import (
    ConditionEvaluator,
    SingleConditionEvaluator,
    ValueExtractor,
)
from backend.services.workflow.state import WorkflowState


@pytest.fixture
def evaluator():
    """Condition evaluator fixture."""
    return ConditionEvaluator()


@pytest.fixture
def sample_state():
    """Sample workflow state fixture."""
    return WorkflowState(
        node_outputs={
            "test_node": {
                "fields": {
                    "status": "success",
                    "count": 42
                }
            }
        }
    )


def test_binary_condition_equals(evaluator, sample_state):
    """Test simple equality condition."""
    condition_config = {
        "input_source": "specific",
        "source_node_id": "test_node",
        "field_path": "status",
        "simple_conditions": [{
            "operator": "==",
            "value": "success",
            "value_type": "string"
        }],
        "logic_operator": "AND"
    }

    result = evaluator.evaluate_binary_condition(sample_state, condition_config)
    assert result is True


def test_binary_condition_numeric_comparison(evaluator, sample_state):
    """Test numeric comparison condition."""
    condition_config = {
        "input_source": "specific",
        "source_node_id": "test_node",
        "field_path": "count",
        "simple_conditions": [{
            "operator": ">",
            "value": 40,
            "value_type": "number"
        }],
        "logic_operator": "AND"
    }

    result = evaluator.evaluate_binary_condition(sample_state, condition_config)
    assert result is True


def test_single_evaluator_operators():
    """Test various operators in single evaluator."""
    evaluator = SingleConditionEvaluator()

    # Test contains
    assert evaluator.evaluate("hello world", {"operator": "contains", "value": "world"}) is True

    # Test starts_with
    assert evaluator.evaluate("hello world", {"operator": "starts_with", "value": "hello"}) is True

    # Test numeric comparison
    assert evaluator.evaluate(42, {"operator": ">=", "value": 40, "value_type": "number"}) is True

    # Test in list
    assert evaluator.evaluate("active", {"operator": "in", "value": ["active", "pending"]}) is True


def test_value_extractor_nested_path():
    """Test nested field path extraction."""
    extractor = ValueExtractor()

    data = {
        "user": {
            "profile": {
                "name": "Alice",
                "age": 30
            }
        }
    }

    result = ValueExtractor._extract_field_value(data, "user.profile.name")
    assert result == "Alice"

    result = ValueExtractor._extract_field_value(data, "user.profile.age")
    assert result == 30
```

### Mocking Dependencies

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.conditions import ConditionEvaluator, LLMConditionEvaluator


@pytest.fixture
def mock_graph_manager():
    """Mock GraphManager for LLM testing."""
    mock_manager = Mock()

    # Mock LLM response
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "true"
    mock_llm.invoke.return_value = mock_response

    mock_manager.get_llm.return_value = mock_llm

    return mock_manager


def test_llm_evaluator_with_mock(mock_graph_manager):
    """Test LLM evaluator with mocked graph manager."""
    evaluator = LLMConditionEvaluator(mock_graph_manager)

    state = {
        "messages": [Mock(content="Test message")],
        "original_message": "Test",
        "node_outputs": {}
    }

    condition_config = {
        "llm_prompt": "Test prompt: {last_message}",
        "llm_config": {"model": "test"},
        "branch_labels": []
    }

    graph = Mock(llm_config={"model": "test"})

    result = evaluator.evaluate(state, condition_config, graph)

    # Verify LLM was called
    mock_graph_manager.get_llm.assert_called_once()
    assert result == "true"


@patch('backend.services.conditions.evaluators.expression.SafeExpressionEvaluator')
def test_expression_evaluator_with_mock(mock_safe_eval):
    """Test expression evaluator with mocked AST evaluator."""
    from backend.services.conditions import ExpressionConditionEvaluator

    # Setup mock
    mock_instance = mock_safe_eval.return_value
    mock_instance.evaluate.return_value = True

    evaluator = ExpressionConditionEvaluator()
    state = {"messages": [], "node_outputs": {}, "original_message": ""}
    condition_config = {"expression": "1 + 1 == 2"}

    result = evaluator.evaluate(state, condition_config)

    assert result is True
    mock_instance.evaluate.assert_called_once_with("1 + 1 == 2")
```

### Integration Testing

```python
import pytest
from backend.services.conditions import ConditionEvaluator, ConditionFunctionFactory
from backend.services.workflow.state import WorkflowState


@pytest.mark.integration
def test_end_to_end_binary_routing():
    """Integration test for complete binary routing flow."""
    # Setup
    evaluator = ConditionEvaluator()
    factory = ConditionFunctionFactory(evaluator)

    # Create node
    node = type('Node', (), {
        'uniq_id': 'test_condition',
        'name': 'Test Condition',
        'condition_config': {
            'branch_mode': 'binary',
            'condition_type': 'simple',
            'input_source': 'specific',
            'source_node_id': 'processor',
            'field_path': 'status',
            'simple_conditions': [{
                'operator': '==',
                'value': 'success',
                'value_type': 'string'
            }],
            'logic_operator': 'AND'
        }
    })()

    graph = type('Graph', (), {'llm_config': None})()

    # Create condition function
    condition_func = factory.create_condition_function(node, graph)

    # Test success case
    success_state = WorkflowState(
        node_outputs={'processor': {'fields': {'status': 'success'}}}
    )
    result = condition_func(success_state)
    assert result == "true"

    # Test failure case
    failure_state = WorkflowState(
        node_outputs={'processor': {'fields': {'status': 'error'}}}
    )
    result = condition_func(failure_state)
    assert result == "false"


@pytest.mark.integration
def test_end_to_end_multi_branch():
    """Integration test for multi-branch routing."""
    evaluator = ConditionEvaluator()

    state = WorkflowState(
        node_outputs={
            'classifier': {'fields': {'category': 'urgent'}}
        }
    )

    branches = [
        {
            'handle_id': 'branch-urgent',
            'condition': {
                'input_source': 'specific',
                'source_node_id': 'classifier',
                'field_path': 'category',
                'operator': '==',
                'value': 'urgent'
            }
        },
        {
            'handle_id': 'branch-normal',
            'condition': {
                'input_source': 'specific',
                'source_node_id': 'classifier',
                'field_path': 'category',
                'operator': '==',
                'value': 'normal'
            }
        }
    ]

    result = evaluator.evaluate_multi_branch(state, branches)
    assert result == "urgent"  # Matches first branch
```

## Best Practices

### Do's

✅ **Use simple conditions when possible**

```python
# Prefer simple conditions for better performance
condition_config = {
    "input_source": "specific",
    "source_node_id": "validator",
    "field_path": "status",
    "simple_conditions": [{
        "operator": "==",
        "value": "approved",
        "value_type": "string"
    }],
    "logic_operator": "AND"
}
```

✅ **Validate condition configurations before use**

```python
def validate_condition_config(config):
    """Validate condition configuration before evaluation."""
    required_fields = ["input_source"]

    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")

    if config.get("input_source") == "specific" and not config.get("source_node_id"):
        raise ValueError("source_node_id required for specific input source")

    return True

# Use validation
try:
    validate_condition_config(condition_config)
    result = evaluator.evaluate_binary_condition(state, condition_config)
except ValueError as e:
    logger.error(f"Invalid configuration: {e}")
```

✅ **Order multi-branch conditions by likelihood**

```python
# Put most common cases first for better performance
branches = [
    {"handle_id": "branch-common", "condition": common_case},      # 70% of cases
    {"handle_id": "branch-occasional", "condition": occasional},    # 25% of cases
    {"handle_id": "branch-rare", "condition": rare_edge_case}      # 5% of cases
]
```

✅ **Use type hints for better IDE support**

```python
from typing import Dict, Any
from backend.services.conditions import ConditionEvaluator
from backend.services.workflow.state import WorkflowState

def evaluate_quality_gate(
    evaluator: ConditionEvaluator,
    state: WorkflowState,
    threshold: int
) -> bool:
    """Evaluate quality gate with type hints."""
    condition_config: Dict[str, Any] = {
        "input_source": "specific",
        "source_node_id": "quality_check",
        "field_path": "score",
        "simple_conditions": [{
            "operator": ">=",
            "value": threshold,
            "value_type": "number"
        }],
        "logic_operator": "AND"
    }

    return evaluator.evaluate_binary_condition(state, condition_config)
```

✅ **Cache LLM results to avoid redundant API calls**

```python
def get_or_evaluate_llm(evaluator, state, config, graph, cache_key):
    """Use caching for expensive LLM evaluations."""
    cached_result = state.get(f"__llm_result_{cache_key}")
    if cached_result is not None:
        logger.info(f"Using cached LLM result for {cache_key}")
        return cached_result

    result = evaluator.evaluate_llm(state, config, graph)
    state[f"__llm_result_{cache_key}"] = result
    return result
```

✅ **Use expression evaluator for complex logic**

```python
# When you need complex boolean algebra, use expressions
condition_config = {
    "expression": """
    (node_outputs['validator']['score'] >= 80 and
     node_outputs['validator']['status'] == 'verified')
    or
    (node_outputs['validator']['override'] == True and
     node_outputs['approver']['approved'] == True)
    """
}
result = evaluator.evaluate_expression(state, condition_config)
```

### Don'ts

❌ **Don't use expressions for simple comparisons**

```python
# Bad: Unnecessary complexity and slower
condition_config = {
    "expression": "node_outputs['node1']['fields']['status'] == 'success'"
}

# Good: Use simple condition instead
condition_config = {
    "input_source": "specific",
    "source_node_id": "node1",
    "field_path": "status",
    "simple_conditions": [{"operator": "==", "value": "success"}],
    "logic_operator": "AND"
}
```

❌ **Don't forget to initialise with graph_manager for LLM conditions**

```python
# Bad: Will fail when evaluating LLM conditions
evaluator = ConditionEvaluator()  # No graph_manager
result = evaluator.evaluate_llm(state, config, graph)  # ValueError!

# Good: Initialise with graph_manager
from backend.services.graph import GraphManager

graph_manager = GraphManager()
evaluator = ConditionEvaluator(graph_manager)
result = evaluator.evaluate_llm(state, config, graph)  # Works!
```

❌ **Don't use dangerous operations in expressions**

```python
# Bad: Trying to use disallowed operations
condition_config = {
    "expression": "__import__('os').system('ls')"  # Security violation!
}
# Raises: ValueError: Operation not allowed for security reasons

# Good: Use only whitelisted operations
condition_config = {
    "expression": "len(messages) > 0 and node_outputs['node1']['count'] >= 10"
}
```

❌ **Don't modify state inside condition functions**

```python
# Bad: Side effects in condition evaluation
def bad_condition_function(state):
    state["new_field"] = "modified"  # Don't do this!
    return "true"

# Good: Conditions should be pure functions
def good_condition_function(state):
    # Read-only access to state
    value = state.get("node_outputs", {}).get("node1", {}).get("fields", {}).get("status")
    return "true" if value == "success" else "false"
```

❌ **Don't ignore error handling**

```python
# Bad: No error handling
result = evaluator.evaluate_llm(state, config, graph)

# Good: Handle potential errors
try:
    result = evaluator.evaluate_llm(state, config, graph)
except ValueError as e:
    logger.error(f"LLM evaluation failed: {e}")
    result = "false"  # Fallback
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    result = "false"
```

❌ **Don't use deep nesting unnecessarily**

```python
# Bad: Deeply nested field paths are slower
config = {
    "field_path": "level1.level2.level3.level4.level5.value"
}

# Good: Flatten data structure when possible
# Store flattened output in node
node_output["fields"] = {
    "extracted_value": data["level1"]["level2"]["level3"]["level4"]["level5"]["value"]
}

config = {
    "field_path": "extracted_value"  # Direct access
}
```

## Related Documentation

### Related Services

- [execution](./execution.md) - Workflow execution engine that uses conditions for routing
- [graph](./graph.md) - Graph building and management, provides GraphManager for LLM access
- [workflow](./workflow.md) - Workflow state management and definitions
- [nodes](./nodes.md) - Node executors including ConditionNodeExecutor

### Related API Modules

- [graph API](../agents-guide/api/graph.md) - Graph execution API that triggers condition evaluation
- [workflow API](../agents-guide/api/workflow.md) - Workflow management API

### Architecture Documentation

- [Workflow Execution Architecture](../architecture/workflow_execution.md) - Overview of how conditions fit into
  execution flow
- [LangGraph Integration](../architecture/langgraph_integration.md) - How condition functions integrate with LangGraph

## Summary

The conditions service module provides a robust, flexible, and secure framework for evaluating routing conditions in
AgenticStudio workflows. It serves as the decision-making engine that determines how workflow execution branches based on
data, expressions, or intelligent LLM reasoning.

The module's architecture follows well-established design patterns including Strategy (for different evaluator types),
Factory (for creating condition functions), Visitor (for safe expression evaluation), and Orchestrator (for coordinating
evaluation). This design makes it extensible, testable, and maintainable while providing strong security guarantees
through AST-based expression validation.

By supporting multiple condition types—simple comparisons, complex expressions, multi-branch routing, and LLM-based
decisions—the service enables everything from straightforward if/else logic to sophisticated AI-powered routing based on
semantic understanding. The integration with LangGraph through ConditionFunctionFactory makes it seamless to use these
conditions as conditional edges in workflow graphs.

**Key Features:**

- Multiple evaluation strategies (simple, expression, multi-branch, LLM)
- Safe expression evaluation using AST visitor pattern to prevent code injection
- Comprehensive operator support (numeric, string, pattern, list membership)
- Flexible value extraction from multiple input sources with nested field path support
- LLM-based intelligent routing using natural language reasoning
- Compound logic with AND/OR operators
- Result caching to avoid re-evaluation
- Support for both dict and dataclass configuration formats

**Primary Use Cases:**

- Binary routing (true/false) based on field values
- Multi-way branching for classification and categorisation
- Complex conditional logic with boolean algebra
- Sentiment analysis and content classification using LLMs
- Dynamic workflow routing based on data patterns
- Quality gates and validation checks
- Priority-based routing and escalation logic

**When to Use This Service:**

- Building workflows with conditional branching
- Implementing data-driven routing logic
- Creating intelligent workflows that adapt based on content
- Evaluating complex conditions that combine multiple data points
- Using LLM reasoning for routing decisions
- Implementing approval workflows with multiple criteria
- Creating switch/case-like routing behaviour
