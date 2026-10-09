# Trace Service Documentation

## Overview

The trace service module provides comprehensive execution visualization and analysis capabilities for AgenticStudio
workflows. It transforms flat execution data from the database into hierarchical tree structures, calculates detailed
statistics, tracks costs, and supports multiple export formats for execution traces.

**Location:** `backend/services/trace/`

**Primary Responsibilities:**

- Transform flat execution data into hierarchical trace trees
- Calculate token usage and cost metrics across executions
- Generate execution statistics and performance analytics
- Export traces in multiple formats (JSON, YAML, OpenTelemetry)
- Map node types for visualization
- Extract and structure execution metadata

**Key Use Cases:**

- Visualising workflow execution flow in the frontend trace viewer
- Analysing LLM costs and token usage
- Debugging complex agent orchestrations
- Exporting traces for external analysis tools
- Performance monitoring and optimisation

---

## Architecture

### Module Structure

```
backend/services/trace/
├── __init__.py                  # Public API exports
├── tree_builder.py              # Hierarchical tree construction
├── statistics.py                # Statistics aggregation
├── export_service.py            # Multi-format export
├── cost_calculator.py           # Token cost calculation
├── node_mapper.py               # Node type mapping
└── metadata_service.py          # Metadata capture and enrichment
```

**File Purposes:**

- **tree_builder.py** - Core service that builds hierarchical trace trees from flat node execution lists
- **statistics.py** - Aggregates metrics across nodes (tokens, costs, durations, status counts)
- **export_service.py** - Converts trace trees to JSON, YAML, or OpenTelemetry formats
- **cost_calculator.py** - Calculates LLM costs based on token usage and model pricing
- **node_mapper.py** - Maps internal node types to trace viewer types and extracts LLM calls
- **metadata_service.py** - Captures rich metadata for LLM calls, tools, orchestration, memory, and environment

### Design Patterns

**Factory Pattern (Class Methods)**
The module extensively uses class methods as factory functions, allowing services to be used without instantiation:

```python
# No instantiation needed
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
stats = StatisticsService.calculate_execution_stats(nodes)
```

**Builder Pattern**
`TraceTreeBuilder` implements the builder pattern to construct complex hierarchical structures in stages:

1. Build node map (flat lookup)
2. Build hierarchy (parent-child relationships)
3. Sort tree (execution order)
4. Calculate metadata (aggregations)

**Strategy Pattern**
`ExportService` uses different export strategies based on format:

- JSON export (pass-through)
- YAML export (serialisation)
- OpenTelemetry export (transformation)

**Data Enrichment Pipeline**
`TraceMetadataService` enriches raw execution data with contextual metadata through a pipeline:

1. Capture LLM metadata
2. Capture message structure
3. Capture tool metadata
4. Capture environment metadata

### Dependencies

**Internal Dependencies:**

- `backend.services.config` - Logging configuration
- `backend.services.database` - Database access (indirect via API)
- `backend.services.execution.history` - Execution data retrieval (indirect via API)
- `backend.models.execution.NodeExecution` - Database model (indirect via API)

**External Dependencies:**

- `yaml` - YAML export functionality
- `langchain_core.messages` - Message type handling
- Python standard library (`dataclasses`, `datetime`, `typing`)

**Database Dependencies:**

- Reads from `node_executions` table (via API layer)
- Reads from `graph_executions` table (via API layer)

**Environment Variables:**

- `ENABLE_POSTGRES_CHECKPOINTING` - Feature flag captured in environment metadata
- `ENABLE_NATIVE_TOOL_NODES` - Feature flag captured in environment metadata
- `ENABLE_PERFORMANCE_LOGGING` - Feature flag captured in environment metadata
- `ENVIRONMENT` - Deployment environment (development/staging/production)
- `AZURE_REGION` - Azure region for deployment tracking
- `DEPLOYMENT_ID` - Deployment identifier

---

## Public API

### Exported Classes

- `TraceTreeBuilder` - Builds hierarchical trace trees from flat execution data
- `StatisticsService` - Calculates aggregated statistics for executions
- `ExportService` - Exports trace data in multiple formats
- `CostCalculator` - Calculates LLM costs from token usage
- `NodeMapper` - Maps node types and extracts LLM calls from agents
- `TraceMetadataService` - Captures and enriches execution metadata

### Exported Functions

All functionality is provided through class methods on the exported classes. There are no standalone function exports.

### Constants and Configuration

**Cost Configuration (in `CostCalculator`):**

- `TOKEN_COSTS` - Dictionary mapping model names to per-1M-token pricing (AUD)

**Node Type Mapping (in `NodeMapper`):**

- `NODE_TYPE_MAPPING` - Dictionary mapping internal node types to trace viewer types

### Exceptions

This module does not define custom exceptions. Errors are logged and propagated as standard Python exceptions that are
caught and handled by the API layer.

---

## Core Classes

### `TraceTreeBuilder`

Transforms flat execution data from the database into a hierarchical tree structure suitable for visualization in the
trace viewer.

**Purpose:** Convert linear node execution records into a parent-child tree that reflects the actual execution flow,
including agent delegation, tool calls, and subagent hierarchies.

**Responsibilities:**

- Build lookup maps for efficient node access
- Construct parent-child relationships based on `parent_agent_id`
- Extract LLM calls from agent nodes as separate child nodes
- Sort nodes by execution order and start time
- Calculate aggregate metadata (total tokens, cost, node counts)
- Handle edge cases (missing parents, duplicate node executions)

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise trace tree builder."""
```

**Instance Attributes:**

- `node_map: Dict[str, Dict[str, Any]]` - Maps database ID to trace node
- `node_id_to_db_ids: Dict[str, List[str]]` - Maps graph node_id to list of database IDs
- `root_nodes: List[Dict[str, Any]]` - List of root-level trace nodes

**Key Methods:**

#### `build_trace_tree()`

```python
@classmethod
def build_trace_tree(
    cls,
    execution_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Transform flat execution data into hierarchical trace tree.

    Args:
        execution_data: Execution dictionary with node_executions list

    Returns:
        Hierarchical trace tree with metadata
    """
```

**Parameters:**

- `execution_data` (Dict[str, Any]) - Dictionary containing:
  - `id`: Execution ID
  - `graph_name`: Name of the graph
  - `status`: Execution status
  - `start_time`: Execution start time
  - `end_time`: Execution end time
  - `duration_seconds`: Total duration
  - `node_executions`: List of node execution dictionaries
  - `input_data`: Execution input
  - `output_data`: Execution output
  - `error_message`: Error if execution failed

**Returns:**

- `Dict[str, Any]` - Trace tree structure containing:
  - `executionId`: Execution ID
  - `graphName`: Graph name
  - `status`: Execution status
  - `startTime`: Start timestamp
  - `endTime`: End timestamp
  - `duration`: Duration in seconds
  - `nodes`: List of root trace nodes (hierarchical)
  - `metadata`: Aggregated metadata

**Example:**

```python
from backend.services.trace import TraceTreeBuilder
from backend.services.execution.history import ExecutionHistoryService

# Fetch execution data from database
execution_data = ExecutionHistoryService.get_graph_execution_dict("exec-123")

# Build hierarchical trace tree
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

# Access tree structure
print(f"Execution: {trace_tree['graphName']}")
print(f"Total nodes: {trace_tree['metadata']['totalNodes']}")
print(f"Total cost: ${trace_tree['metadata']['totalCost']:.4f}")

# Navigate tree hierarchy
for root_node in trace_tree['nodes']:
    print(f"Root: {root_node['name']} ({root_node['type']})")
    for child in root_node['children']:
        print(f"  Child: {child['name']} ({child['type']})")
```

**Behaviour:**

- Creates a new builder instance internally
- Processes all nodes in three passes:
    1. **Build node map** - Create trace nodes and lookup structures
    2. **Build hierarchy** - Connect nodes via parent-child relationships
    3. **Sort tree** - Order nodes by execution sequence
- Extracts LLM calls from agent nodes as separate child nodes
- Handles duplicate node executions (same node_id executed multiple times)
- Warns about missing parent references
- Calculates aggregate metadata using `CostCalculator`

**Use Cases:**

- Loading trace data for the frontend trace viewer
- Generating execution visualizations
- Analyzing workflow structure
- Debugging agent delegation flows

---

### `StatisticsService`

Calculates comprehensive aggregated statistics across all nodes in an execution.

**Purpose:** Provide detailed metrics about token usage, costs, performance, and execution status for analysis and
monitoring.

**Responsibilities:**

- Count nodes by status (completed, failed, running)
- Sum token usage across all nodes
- Calculate total costs using `CostCalculator`
- Compute average durations
- Group tokens and costs by node type and model
- Calculate performance metrics (tokens per second, time to first token)

**Key Methods:**

#### `calculate_execution_stats()`

```python
@classmethod
def calculate_execution_stats(
    cls,
    nodes: List[Any],
) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics for an execution.

    Args:
        nodes: List of NodeExecution objects or dictionaries

    Returns:
        Dictionary containing aggregated statistics
    """
```

**Parameters:**

- `nodes` (List[Any]) - List of node execution objects (SQLAlchemy models or dictionaries)

**Returns:**

- `Dict[str, Any]` - Statistics dictionary containing:
  - `totalNodes`: Total number of nodes
  - `completedNodes`: Number of completed nodes
  - `failedNodes`: Number of failed nodes
  - `runningNodes`: Number of running nodes
  - `totalTokens`: Sum of all tokens
  - `totalCost`: Total cost in AUD
  - `averageDuration`: Average node duration in seconds
  - `tokensByType`: Token counts grouped by node type
  - `costByType`: Costs grouped by node type
  - `costByModel`: Costs grouped by LLM model
  - `performanceMetrics`: Performance statistics

**Example:**

```python
from backend.services.trace import StatisticsService
from backend.services.database import get_db
from backend.models import NodeExecution

# Fetch all nodes for an execution
with get_db() as db:
    nodes = db.query(NodeExecution).filter(
        NodeExecution.graph_execution_id == "exec-123"
    ).all()

# Calculate statistics
stats = StatisticsService.calculate_execution_stats(nodes)

# Display statistics
print(f"Total nodes: {stats['totalNodes']}")
print(f"Completed: {stats['completedNodes']}")
print(f"Failed: {stats['failedNodes']}")
print(f"Total tokens: {stats['totalTokens']:,}")
print(f"Total cost: ${stats['totalCost']:.4f}")
print(f"Average duration: {stats['averageDuration']:.2f}s")

# Analyze by type
for node_type, token_count in stats['tokensByType'].items():
    cost = stats['costByType'].get(node_type, 0)
    print(f"{node_type}: {token_count:,} tokens, ${cost:.4f}")

# Analyze by model
for model, cost in stats['costByModel'].items():
    print(f"{model}: ${cost:.4f}")

# Performance metrics
perf = stats['performanceMetrics']
if perf['averageTokensPerSecond']:
    print(f"Avg tokens/sec: {perf['averageTokensPerSecond']:.2f}")
if perf['averageTimeToFirstToken']:
    print(f"Avg TTFT: {perf['averageTimeToFirstToken']:.2f}ms")
```

**Behaviour:**

- Accepts both SQLAlchemy model objects and dictionaries
- Returns empty statistics structure if no nodes provided
- Calculates costs using `CostCalculator` if not already present on nodes
- Only includes non-null values in performance metrics
- Groups data by node type and model for detailed breakdown

**Use Cases:**

- Dashboard metrics and monitoring
- Cost analysis and budgeting
- Performance optimization identification
- Execution summary reports
- Comparing execution efficiency

---

### `ExportService`

Exports trace tree data in various formats for integration with external tools.

**Purpose:** Convert internal trace tree format to industry-standard formats for analysis, visualization, and
integration with monitoring tools.

**Responsibilities:**

- Export as JSON (native format)
- Export as YAML for human readability
- Convert to OpenTelemetry format for distributed tracing tools

**Key Methods:**

#### `export_as_json()`

```python
@classmethod
def export_as_json(
    cls,
    trace_tree: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Export trace tree as JSON.

    Args:
        trace_tree: Trace tree dictionary

    Returns:
        Trace tree (pass-through for JSON)
    """
```

**Parameters:**

- `trace_tree` (Dict[str, Any]) - Trace tree from `TraceTreeBuilder.build_trace_tree()`

**Returns:**

- `Dict[str, Any]` - Same trace tree (pass-through)

**Example:**

```python
from backend.services.trace import TraceTreeBuilder, ExportService

# Build trace tree
execution_data = ExecutionHistoryService.get_graph_execution_dict("exec-123")
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

# Export as JSON (pass-through)
json_data = ExportService.export_as_json(trace_tree)

# Can be serialized with json.dumps()
import json
json_string = json.dumps(json_data, indent=2)
```

#### `export_as_yaml()`

```python
@classmethod
def export_as_yaml(
    cls,
    trace_tree: Dict[str, Any],
) -> str:
    """
    Export trace tree as YAML string.

    Args:
        trace_tree: Trace tree dictionary

    Returns:
        YAML string representation
    """
```

**Parameters:**

- `trace_tree` (Dict[str, Any]) - Trace tree from `TraceTreeBuilder.build_trace_tree()`

**Returns:**

- `str` - YAML-formatted string

**Example:**

```python
from backend.services.trace import TraceTreeBuilder, ExportService

# Build trace tree
execution_data = ExecutionHistoryService.get_graph_execution_dict("exec-123")
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

# Export as YAML
yaml_string = ExportService.export_as_yaml(trace_tree)

# Save to file
with open("trace_exec-123.yaml", "w") as f:
    f.write(yaml_string)

# YAML is human-readable
print(yaml_string)
```

#### `export_as_opentelemetry()`

```python
@classmethod
def export_as_opentelemetry(
    cls,
    trace_tree: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert trace tree to OpenTelemetry format.

    Args:
        trace_tree: Trace tree dictionary

    Returns:
        OpenTelemetry format dictionary
    """
```

**Parameters:**

- `trace_tree` (Dict[str, Any]) - Trace tree from `TraceTreeBuilder.build_trace_tree()`

**Returns:**

- `Dict[str, Any]` - OpenTelemetry format with structure:
  - `data`: List of traces
    - `traceID`: Execution ID
    - `spans`: List of span objects
    - `processes`: Service definitions

**Example:**

```python
from backend.services.trace import TraceTreeBuilder, ExportService

# Build trace tree
execution_data = ExecutionHistoryService.get_graph_execution_dict("exec-123")
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

# Export as OpenTelemetry format
otel_data = ExportService.export_as_opentelemetry(trace_tree)

# Send to OpenTelemetry collector or Jaeger
import requests
requests.post(
    "http://jaeger-collector:14268/api/traces",
    json=otel_data
)

# Or save for later import
import json
with open("trace_otel.json", "w") as f:
    json.dump(otel_data, f, indent=2)
```

**Behaviour:**

- JSON export is a pass-through (no transformation)
- YAML export uses `yaml.dump()` with readable formatting
- OpenTelemetry export:
  - Creates spans for each node in the tree
  - Preserves parent-child relationships via `parentSpanId`
  - Includes tags for node type, status, tokens, cost, LLM metadata
  - Recursively processes all children
  - Uses execution ID as trace ID

**Use Cases:**

- JSON: API responses, frontend consumption
- YAML: Human-readable reports, documentation, archival
- OpenTelemetry: Integration with Jaeger, Zipkin, Datadog, New Relic

---

### `CostCalculator`

Calculates LLM operation costs based on token usage and model-specific pricing.

**Purpose:** Provide accurate cost estimates for LLM operations across different models and providers to enable budget
tracking and cost optimization.

**Responsibilities:**

- Maintain pricing tables for different LLM models
- Calculate per-node costs from input/output tokens
- Calculate total costs across multiple nodes
- Support model-specific pricing (GPT-4, Claude, etc.)
- Handle both dictionary and SQLAlchemy model inputs

**Configuration:**

```python
TOKEN_COSTS = {
    "gpt-4o": {"input": 3.85446, "output": 15.4179},  # AUD per 1M tokens
    "gpt-4o-latest": {"input": 3.85446, "output": 15.4179},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "gpt-4": {"input": 30.0, "output": 60.0},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "claude-3-opus": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}
```

**Key Methods:**

#### `calculate_node_cost()`

```python
@classmethod
def calculate_node_cost(
    cls,
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    model: Optional[str] = None,
) -> Optional[float]:
    """
    Calculate cost for a single node based on token usage.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model name for model-specific pricing (defaults to gpt-4o)

    Returns:
        Total cost in currency of pricing table, or None if no tokens
    """
```

**Parameters:**

- `input_tokens` (Optional[int]) - Number of prompt/input tokens
- `output_tokens` (Optional[int]) - Number of completion/output tokens
- `model` (Optional[str]) - Model name (e.g., "gpt-4o", "claude-3-sonnet")

**Returns:**

- `Optional[float]` - Total cost in AUD, or None if no tokens

**Example:**

```python
from backend.services.trace import CostCalculator

# Calculate cost for a GPT-4o call
cost = CostCalculator.calculate_node_cost(
    input_tokens=1000,
    output_tokens=500,
    model="gpt-4o"
)
print(f"Cost: ${cost:.4f} AUD")  # Cost: $0.0116 AUD

# Calculate with default model (gpt-4o)
cost = CostCalculator.calculate_node_cost(
    input_tokens=2000,
    output_tokens=1000
)
print(f"Cost: ${cost:.4f} AUD")

# Different models have different costs
gpt4_cost = CostCalculator.calculate_node_cost(1000, 500, "gpt-4")
claude_cost = CostCalculator.calculate_node_cost(1000, 500, "claude-3-sonnet")
print(f"GPT-4: ${gpt4_cost:.4f}, Claude Sonnet: ${claude_cost:.4f}")

# Returns None if no tokens
cost = CostCalculator.calculate_node_cost(0, 0, "gpt-4o")
print(cost)  # None
```

#### `calculate_total_cost()`

```python
@classmethod
def calculate_total_cost(
    cls,
    nodes: list,
) -> float:
    """
    Calculate total cost across multiple nodes.

    Args:
        nodes: List of node dictionaries with token and cost information

    Returns:
        Total cost across all nodes
    """
```

**Parameters:**

- `nodes` (list) - List of node dictionaries or SQLAlchemy models with:
  - `total_cost`: Pre-calculated cost (if available)
  - `input_tokens`, `output_tokens`: Token counts (if cost not available)
  - `llm_metadata.model`: Model name for pricing

**Returns:**

- `float` - Total cost across all nodes in AUD

**Example:**

```python
from backend.services.trace import CostCalculator
from backend.services.database import get_db
from backend.models import NodeExecution

# Calculate total cost for an execution
with get_db() as db:
    nodes = db.query(NodeExecution).filter(
        NodeExecution.graph_execution_id == "exec-123"
    ).all()

    total_cost = CostCalculator.calculate_total_cost(nodes)
    print(f"Total execution cost: ${total_cost:.4f} AUD")

# Works with dictionary list too
nodes_dict = [
    {"input_tokens": 1000, "output_tokens": 500, "llm_metadata": {"model": "gpt-4o"}},
    {"input_tokens": 2000, "output_tokens": 1000, "llm_metadata": {"model": "gpt-4o"}},
    {"total_cost": 0.05}  # Pre-calculated cost
]
total = CostCalculator.calculate_total_cost(nodes_dict)
print(f"Total: ${total:.4f}")
```

#### `enrich_node_with_cost()`

```python
@classmethod
def enrich_node_with_cost(
    cls,
    node: Dict,
) -> Dict:
    """
    Add calculated cost to node if not present.

    Args:
        node: Node dictionary

    Returns:
        Node dictionary with cost metadata added
    """
```

**Parameters:**

- `node` (Dict) - Node dictionary

**Returns:**

- `Dict` - Same node dictionary with `metadata.cost` added if calculated

**Example:**

```python
from backend.services.trace import CostCalculator

node = {
    "id": "node-123",
    "input_tokens": 1000,
    "output_tokens": 500,
    "llm_metadata": {"model": "gpt-4o"}
}

# Enrich with cost
enriched_node = CostCalculator.enrich_node_with_cost(node)

# Cost is added to metadata
print(enriched_node["metadata"]["cost"])  # 0.01162...
```

**Behaviour:**

- Defaults to "gpt-4o" pricing if model not specified
- Case-insensitive model name matching
- Returns None if both tokens are 0 or None
- Uses existing `total_cost` field if available
- Falls back to token-based calculation if cost not present

**Use Cases:**

- Real-time cost tracking during execution
- Budget monitoring and alerts
- Cost breakdown by model or node type
- ROI analysis for different models
- Optimizing model selection based on cost

---

### `NodeMapper`

Maps internal node types to trace viewer types and extracts detailed LLM call information from agent nodes.

**Purpose:** Transform database node representations into visualization-friendly formats and extract granular LLM
interactions for detailed trace analysis.

**Responsibilities:**

- Map internal node types (e.g., "AGENT", "TOOL") to viewer types (e.g., "agent", "tool")
- Extract individual LLM calls from agent message structures
- Build trace node dictionaries with all required fields
- Structure metadata for visualization
- Handle special node types (SUBWORKFLOW, HTTP_REQUEST, etc.)

**Configuration:**

```python
NODE_TYPE_MAPPING = {
    "AGENT": "agent",
    "TOOL": "tool",
    "CONDITION": "condition",
    "HUMAN": "human",
    "ORCHESTRATOR": "orchestrator",
    "SUBGRAPH": "subgraph",
    "CHECKPOINT": "checkpoint",
    "START": "start",
    "END": "end",
    # Specific tool types
    "DOCUMENT_SEARCH": "tool",
    "DATABASE_QUERY": "tool",
    "HTTP_REQUEST": "tool",
    "WEB_SEARCH": "tool",
    "EMAIL_SEND": "tool",
    "FILE_READ": "tool",
    "MCP_SERVER": "tool",
    "SUBWORKFLOW": "subgraph",
    "LLM": "llm",
}
```

**Key Methods:**

#### `map_node_type()`

```python
@classmethod
def map_node_type(
    cls,
    node_type: str,
) -> str:
    """
    Map internal node types to trace viewer types.

    Args:
        node_type: Internal node type string

    Returns:
        Mapped node type for trace viewer
    """
```

**Parameters:**

- `node_type` (str) - Internal node type (e.g., "AGENT", "DATABASE_QUERY")

**Returns:**

- `str` - Viewer type (e.g., "agent", "tool", "unknown")

**Example:**

```python
from backend.services.trace import NodeMapper

# Map common types
viewer_type = NodeMapper.map_node_type("AGENT")
print(viewer_type)  # "agent"

viewer_type = NodeMapper.map_node_type("DATABASE_QUERY")
print(viewer_type)  # "tool"

viewer_type = NodeMapper.map_node_type("SUBWORKFLOW")
print(viewer_type)  # "subgraph"

# Unknown types return "unknown"
viewer_type = NodeMapper.map_node_type("CUSTOM_TYPE")
print(viewer_type)  # "unknown"
```

#### `extract_llm_calls_from_agent()`

```python
@classmethod
def extract_llm_calls_from_agent(
    cls,
    node: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Extract LLM calls as separate nodes from agent execution.

    Args:
        node: Agent node dictionary containing message structure and LLM metadata

    Returns:
        List of LLM call node dictionaries
    """
```

**Parameters:**

- `node` (Dict[str, Any]) - Agent node with:
  - `message_structure.messages`: List of conversation messages
  - `llm_metadata`: LLM configuration and performance data
  - `id`: Node ID for generating child IDs
  - `status`, `start_time`, `end_time`: Execution info

**Returns:**

- `List[Dict[str, Any]]` - List of LLM call nodes (one per assistant message)

**Example:**

```python
from backend.services.trace import NodeMapper

agent_node = {
    "id": "node-123",
    "node_type": "AGENT",
    "status": "completed",
    "start_time": "2025-10-27T10:00:00Z",
    "end_time": "2025-10-27T10:00:05Z",
    "duration_seconds": 5.0,
    "input_tokens": 1000,
    "output_tokens": 500,
    "total_tokens": 1500,
    "total_cost": 0.0116,
    "llm_metadata": {
        "model": "gpt-4o",
        "provider": "azure",
        "temperature": 0.7
    },
    "message_structure": {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language..."}
        ]
    }
}

# Extract LLM calls
llm_calls = NodeMapper.extract_llm_calls_from_agent(agent_node)

# One LLM call per assistant message
for llm_call in llm_calls:
    print(f"LLM Call: {llm_call['name']}")
    print(f"Model: {llm_call['metadata']['model']}")
    print(f"Tokens: {llm_call['metadata']['tokens']['total']}")
    print(f"Input messages: {len(llm_call['input']['messages'])}")
    print(f"Output: {llm_call['output'][:50]}...")
```

#### `create_trace_node()`

```python
@classmethod
def create_trace_node(
    cls,
    node: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Transform a database node into a trace tree node.

    Args:
        node: Node dictionary from database

    Returns:
        Trace tree node dictionary
    """
```

**Parameters:**

- `node` (Dict[str, Any]) - Database node with all fields

**Returns:**

- `Dict[str, Any]` - Trace node with structure:
  - `id`: Database ID
  - `nodeId`: Graph node ID
  - `name`: Node name
  - `type`: Mapped viewer type
  - `status`: Execution status
  - `startTime`, `endTime`, `duration`: Timing
  - `executionOrder`: Sequence number
  - `children`: Empty list (populated by tree builder)
  - `metadata`: Structured metadata
  - `input`, `output`, `error`: Data fields
  - `messages`: Message structure if agent

**Example:**

```python
from backend.services.trace import NodeMapper

db_node = {
    "id": "db-uuid-123",
    "node_id": "agent_1",
    "node_name": "Data Analyst",
    "node_type": "AGENT",
    "status": "completed",
    "start_time": "2025-10-27T10:00:00Z",
    "end_time": "2025-10-27T10:00:05Z",
    "duration_seconds": 5.0,
    "execution_order": 1,
    "input_data": {"query": "Analyze sales"},
    "output_data": {"analysis": "Sales are up 10%"},
    "input_tokens": 1000,
    "output_tokens": 500,
    "total_tokens": 1500,
    "total_cost": 0.0116,
    "llm_metadata": {"model": "gpt-4o"},
    "is_sub_agent": False
}

# Create trace node
trace_node = NodeMapper.create_trace_node(db_node)

# Access trace node fields
print(f"ID: {trace_node['id']}")
print(f"Name: {trace_node['name']}")
print(f"Type: {trace_node['type']}")  # "agent"
print(f"Tokens: {trace_node['metadata']['tokens']['total']}")
print(f"Cost: ${trace_node['metadata']['cost']:.4f}")
print(f"Original type: {trace_node['metadata']['nodeType']}")
```

**Behaviour:**

- Maps node type using `map_node_type()`
- Calculates cost using `CostCalculator` if not present
- Extracts messages from message_structure
- Preserves original node_type in metadata
- Includes all metadata objects (llm, tool, orchestration, memory, environment)
- Returns nodes ready for tree building

**Use Cases:**

- Converting database records to visualization format
- Extracting detailed LLM interaction data
- Building hierarchical trace trees
- Displaying granular execution details

---

### `TraceMetadataService`

Captures rich metadata about execution context, LLM calls, tool invocations, orchestration, memory operations, and
environment for detailed trace analysis.

**Purpose:** Enrich execution traces with comprehensive contextual information beyond basic timing and I/O, enabling
deep analysis of performance, costs, and behaviour.

**Responsibilities:**

- Capture LLM call metadata (model, temperature, costs, performance)
- Structure conversation messages with token estimates
- Track tool invocation details
- Record orchestration and delegation patterns
- Monitor memory and context management
- Capture environment and feature flags

**Data Classes:**

```python
@dataclass
class LLMMetadata:
    """LLM call metadata with configuration, costs, and performance."""
    model: str
    provider: str
    deployment_name: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]
    # ... (see full definition in metadata_service.py)

@dataclass
class MessageStructure:
    """Conversation message structure with token counts."""
    messages: List[Dict[str, Any]]
    message_count: int
    system_prompt_tokens: Optional[int]
    conversation_history_tokens: Optional[int]

@dataclass
class ToolMetadata:
    """Tool invocation metadata with timing and results."""
    tool_name: str
    arguments: Dict[str, Any]
    execution_time_ms: float
    return_value: Any

@dataclass
class OrchestrationMetadata:
    """Orchestration and delegation metadata."""
    delegated_to: Optional[List[str]]
    subagents_created: int
    subagents_completed: int
    subagents_failed: int

@dataclass
class MemoryMetadata:
    """Memory operations and context management."""
    memory_retrievals: Optional[List[Dict[str, Any]]]
    context_window_size: Optional[int]
    context_pruning_applied: bool

@dataclass
class EnvironmentMetadata:
    """Runtime environment information."""
    python_version: Optional[str]
    langchain_version: Optional[str]
    cpu_cores: Optional[int]
    feature_flags: Optional[Dict[str, bool]]
    environment: str
```

**Key Methods:**

#### `capture_llm_metadata()`

```python
@staticmethod
def capture_llm_metadata(
    model: str,
    provider: str,
    config: Dict[str, Any],
    response: Optional[Any] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """Capture LLM call metadata."""
```

**Example:**

```python
from backend.services.trace import TraceMetadataService
import time

start = time.time()
# ... make LLM call ...
end = time.time()

llm_metadata = TraceMetadataService.capture_llm_metadata(
    model="gpt-4o",
    provider="azure",
    config={
        "temperature": 0.7,
        "max_tokens": 2000,
        "deployment_name": "gpt-4o-deployment"
    },
    response=llm_response,
    start_time=start,
    end_time=end,
    input_tokens=1000,
    output_tokens=500
)

print(f"Model: {llm_metadata['model']}")
print(f"Cost: ${llm_metadata['total_cost']:.4f}")
print(f"Latency: {llm_metadata['total_latency_ms']:.2f}ms")
print(f"Tokens/sec: {llm_metadata['tokens_per_second']:.2f}")
```

#### `capture_message_structure()`

```python
@staticmethod
def capture_message_structure(
    messages: List[BaseMessage],
    prompt_template_id: Optional[str] = None,
    prompt_variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Capture message structure and token counts."""
```

**Example:**

```python
from backend.services.trace import TraceMetadataService
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage(content="You are a helpful assistant"),
    HumanMessage(content="What is Python?"),
    AIMessage(content="Python is a programming language...")
]

message_structure = TraceMetadataService.capture_message_structure(
    messages=messages,
    prompt_template_id="assistant-v1",
    prompt_variables={"domain": "programming"}
)

print(f"Message count: {message_structure['message_count']}")
print(f"System prompt tokens: {message_structure['system_prompt_tokens']}")
print(f"Conversation tokens: {message_structure['conversation_history_tokens']}")
```

#### `capture_tool_metadata()`

```python
@staticmethod
def capture_tool_metadata(
    tool_name: str,
    arguments: Dict[str, Any],
    result: Any,
    start_time: float,
    end_time: float,
    error: Optional[Exception] = None,
) -> Dict[str, Any]:
    """Capture tool invocation metadata."""
```

**Example:**

```python
from backend.services.trace import TraceMetadataService
import time

start = time.time()
try:
    result = database_query_tool(query="SELECT * FROM users")
    error = None
except Exception as e:
    result = None
    error = e
end = time.time()

tool_metadata = TraceMetadataService.capture_tool_metadata(
    tool_name="database_query",
    arguments={"query": "SELECT * FROM users"},
    result=result,
    start_time=start,
    end_time=end,
    error=error
)

print(f"Tool: {tool_metadata['tool_name']}")
print(f"Execution time: {tool_metadata['execution_time_ms']:.2f}ms")
if tool_metadata['error_details']:
    print(f"Error: {tool_metadata['error_details']['error_message']}")
```

#### `capture_environment_metadata()`

```python
@staticmethod
def capture_environment_metadata() -> Dict[str, Any]:
    """Capture environment and runtime metadata."""
```

**Example:**

```python
from backend.services.trace import TraceMetadataService

env_metadata = TraceMetadataService.capture_environment_metadata()

print(f"Python version: {env_metadata['python_version']}")
print(f"LangChain version: {env_metadata['langchain_version']}")
print(f"CPU cores: {env_metadata['cpu_cores']}")
print(f"Environment: {env_metadata['environment']}")
print(f"Feature flags: {env_metadata['feature_flags']}")
```

#### `enrich_node_execution()`

```python
@staticmethod
def enrich_node_execution(
    node_execution_data: Dict[str, Any],
    llm_response: Optional[Any] = None,
    messages: Optional[List[BaseMessage]] = None,
    tool_result: Optional[Any] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Enrich node execution data with all available metadata."""
```

**Example:**

```python
from backend.services.trace import TraceMetadataService
from langchain_core.messages import HumanMessage, AIMessage

node_data = {
    "node_type": "AGENT",
    "node_name": "Assistant",
    "input_tokens": 1000,
    "output_tokens": 500
}

messages = [
    HumanMessage(content="Hello"),
    AIMessage(content="Hi there!")
]

enriched = TraceMetadataService.enrich_node_execution(
    node_execution_data=node_data,
    llm_response=llm_response,
    messages=messages,
    config={"model": "gpt-4o", "provider": "azure"}
)

# Enriched with LLM metadata
print(enriched['llm_metadata']['model'])
# Enriched with message structure
print(enriched['message_structure']['message_count'])
# Always includes environment
print(enriched['environment_metadata']['environment'])
```

**Use Cases:**

- Enriching node executions during workflow runs
- Debugging LLM behaviour and costs
- Analyzing tool performance
- Monitoring context window usage
- Tracking feature flag impact
- Environment-specific troubleshooting

---

## Configuration

### Model Pricing Configuration

LLM costs are configured in `CostCalculator.TOKEN_COSTS`:

```python
TOKEN_COSTS = {
    "gpt-4o": {"input": 3.85446, "output": 15.4179},  # AUD per 1M tokens
    "gpt-4o-mini": {"input": 0.15, "output": 0.6},
    "gpt-4-turbo": {"input": 10.0, "output": 30.0},
    "claude-3-sonnet": {"input": 3.0, "output": 15.0},
    # ... more models
}
```

**To add a new model:**

1. Add entry to `TOKEN_COSTS` dictionary
2. Use pricing per 1M tokens
3. Specify both input and output rates

### Node Type Mapping Configuration

Node type mappings are configured in `NodeMapper.NODE_TYPE_MAPPING`:

```python
NODE_TYPE_MAPPING = {
    "AGENT": "agent",
    "TOOL": "tool",
    # ... more mappings
}
```

**To add a new node type:**

1. Add entry to `NODE_TYPE_MAPPING`
2. Map to existing viewer type or "unknown"
3. Update frontend if new viewer type needed

### Environment Variables

The trace service reads these environment variables:

- `ENVIRONMENT` - Deployment environment (default: "development")
- `AZURE_REGION` - Azure region for deployment tracking
- `DEPLOYMENT_ID` - Deployment identifier
- `ENABLE_POSTGRES_CHECKPOINTING` - Feature flag (default: "true")
- `ENABLE_NATIVE_TOOL_NODES` - Feature flag (default: "true")
- `ENABLE_PERFORMANCE_LOGGING` - Feature flag (default: "true")

### Initialisation Patterns

**Basic Usage (Class Methods):**

```python
from backend.services.trace import TraceTreeBuilder, StatisticsService

# No initialisation needed - use class methods directly
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
stats = StatisticsService.calculate_execution_stats(nodes)
```

**In API Layer:**

```python
from fastapi import APIRouter
from backend.services.trace import TraceTreeBuilder, ExportService

router = APIRouter()

@router.get("/trace/{execution_id}")
async def get_trace(execution_id: str):
    execution_data = get_execution_data(execution_id)
    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
    return ExportService.export_as_json(trace_tree)
```

---

## Error Handling

### Exception Behaviour

The trace service does not define custom exceptions. Instead, it:

- Logs errors using the configured logger
- Propagates standard Python exceptions
- Lets the API layer catch and handle exceptions

**Common Exceptions:**

- `KeyError` - Missing required fields in node data
- `ValueError` - Invalid data format or values
- `TypeError` - Incorrect parameter types
- `ImportError` - Missing optional dependencies (e.g., yaml)

### Error Handling Patterns

**In API Layer:**

```python
from fastapi import APIRouter, HTTPException
from backend.services.trace import TraceTreeBuilder
from backend.services.config import get_logger

router = APIRouter()
logger = get_logger("trace_api")

@router.get("/trace/{execution_id}")
async def get_trace(execution_id: str):
    try:
        execution_data = get_execution_data(execution_id)

        if not execution_data:
            raise HTTPException(status_code=404, detail="Execution not found")

        trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
        return trace_tree

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building trace tree: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**In Service Layer:**

```python
from backend.services.trace import TraceTreeBuilder, StatisticsService
from backend.services.config import get_logger

logger = get_logger("my_service")

def process_execution(execution_id: str):
    try:
        execution_data = fetch_execution(execution_id)
        trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
        stats = StatisticsService.calculate_execution_stats(
            execution_data.get("node_executions", [])
        )
        return {"tree": trace_tree, "stats": stats}
    except KeyError as e:
        logger.error(f"Missing required field in execution data: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing execution: {e}")
        raise
```

**Defensive Coding:**

```python
# Handle missing data gracefully
execution_data = execution_data or {}
nodes = execution_data.get("node_executions", [])

if not nodes:
    logger.warning(f"No nodes found for execution {execution_id}")
    return {"nodes": [], "metadata": {}}

# Safe attribute access
node_type = node.get("node_type", "unknown")
tokens = node.get("total_tokens", 0)

# Handle None values
input_tokens = input_tokens or 0
output_tokens = output_tokens or 0
```

---

## Integration Patterns

### Integration with API Layer

The trace service is primarily consumed by the REST API in `backend/api/trace/routes.py`:

```python
from fastapi import APIRouter, HTTPException, Query
from backend.services.trace import (
    TraceTreeBuilder,
    StatisticsService,
    ExportService
)
from backend.services.execution.history import ExecutionHistoryService

router = APIRouter(prefix="/api/trace", tags=["trace"])

@router.get("/{execution_id}/tree")
async def get_trace_tree(execution_id: str):
    """Get hierarchical trace tree for visualization."""
    execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)

    if not execution_data:
        raise HTTPException(status_code=404, detail="Execution not found")

    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
    return trace_tree

@router.get("/{execution_id}/stats")
async def get_execution_stats(execution_id: str):
    """Get aggregated statistics."""
    with get_db() as db:
        nodes = db.query(NodeExecution).filter(
            NodeExecution.graph_execution_id == execution_id
        ).all()

        stats = StatisticsService.calculate_execution_stats(nodes)
        return stats

@router.get("/{execution_id}/export")
async def export_trace(
    execution_id: str,
    export_format: str = Query("json", enum=["json", "yaml", "opentelemetry"])
):
    """Export trace in various formats."""
    execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

    if export_format == "json":
        return ExportService.export_as_json(trace_tree)
    elif export_format == "yaml":
        return ExportService.export_as_yaml(trace_tree)
    elif export_format == "opentelemetry":
        return ExportService.export_as_opentelemetry(trace_tree)
```

### Integration with WebSocket Layer

Real-time trace streaming via `backend/api/trace/websocket.py`:

```python
from fastapi import WebSocket
from backend.services.trace import TraceTreeBuilder
from backend.services.execution.history import ExecutionHistoryService

@websocket_router.websocket("/{execution_id}/stream")
async def stream_trace_updates(websocket: WebSocket, execution_id: str):
    """Stream real-time trace updates."""
    await websocket.accept()

    while True:
        execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)

        if execution_data:
            trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
            await websocket.send_json({
                "type": "trace_update",
                "data": trace_tree
            })

        await asyncio.sleep(1)  # Update every second
```

### Integration with Other Services

**Execution History Service:**

```python
from backend.services.execution.history import ExecutionHistoryService
from backend.services.trace import TraceTreeBuilder

# Fetch execution with all node data
execution_data = ExecutionHistoryService.get_graph_execution_dict("exec-123")

# Build trace tree
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
```

**Database Service:**

```python
from backend.services.database import get_db
from backend.models import NodeExecution
from backend.services.trace import StatisticsService, CostCalculator

with get_db() as db:
    # Query nodes
    nodes = db.query(NodeExecution).filter(
        NodeExecution.graph_execution_id == execution_id
    ).all()

    # Calculate statistics
    stats = StatisticsService.calculate_execution_stats(nodes)

    # Calculate costs
    total_cost = CostCalculator.calculate_total_cost(nodes)
```

### Dependency Flow

```
Frontend Trace Viewer
        ↓
    API Layer (backend/api/trace/)
        ↓
    Trace Service (backend/services/trace/)
        ↓
    ┌─────────────┬─────────────────┐
    ↓             ↓                 ↓
Execution    Database         Config
History       Service         Service
Service
```

### Common Integration Patterns

#### Pattern 1: Fetch and Visualize Execution

```python
from backend.services.execution.history import ExecutionHistoryService
from backend.services.trace import TraceTreeBuilder, StatisticsService

def get_execution_visualization(execution_id: str):
    """Get complete execution visualization data."""

    # Fetch execution data
    execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)

    if not execution_data:
        return None

    # Build trace tree
    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

    # Calculate statistics
    nodes = execution_data.get("node_executions", [])
    stats = StatisticsService.calculate_execution_stats(nodes)

    return {
        "tree": trace_tree,
        "statistics": stats
    }
```

#### Pattern 2: Cost Analysis

```python
from backend.services.database import get_db
from backend.models import NodeExecution, GraphExecution
from backend.services.trace import CostCalculator, StatisticsService
from datetime import datetime, timedelta

def analyze_weekly_costs():
    """Analyze costs for the past week."""

    with get_db() as db:
        # Get executions from past week
        week_ago = datetime.utcnow() - timedelta(days=7)
        executions = db.query(GraphExecution).filter(
            GraphExecution.created_at >= week_ago
        ).all()

        total_cost = 0
        cost_by_model = {}

        for execution in executions:
            # Get nodes for this execution
            nodes = db.query(NodeExecution).filter(
                NodeExecution.graph_execution_id == execution.id
            ).all()

            # Calculate execution cost
            exec_cost = CostCalculator.calculate_total_cost(nodes)
            total_cost += exec_cost

            # Get cost breakdown
            stats = StatisticsService.calculate_execution_stats(nodes)
            for model, cost in stats['costByModel'].items():
                cost_by_model[model] = cost_by_model.get(model, 0) + cost

        return {
            "total_cost": total_cost,
            "cost_by_model": cost_by_model,
            "execution_count": len(executions)
        }
```

#### Pattern 3: Export for External Tools

```python
from backend.services.trace import TraceTreeBuilder, ExportService
from backend.services.execution.history import ExecutionHistoryService
import requests

def export_to_jaeger(execution_id: str, jaeger_url: str):
    """Export execution trace to Jaeger."""

    # Fetch and build trace tree
    execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

    # Export as OpenTelemetry format
    otel_data = ExportService.export_as_opentelemetry(trace_tree)

    # Send to Jaeger
    response = requests.post(
        f"{jaeger_url}/api/traces",
        json=otel_data
    )

    return response.status_code == 200
```

#### Pattern 4: Real-time Monitoring

```python
from backend.services.trace import StatisticsService, CostCalculator
from backend.services.database import get_db
from backend.models import NodeExecution

class ExecutionMonitor:
    """Monitor execution costs and performance in real-time."""

    def __init__(self, execution_id: str, cost_threshold: float = 1.0):
        self.execution_id = execution_id
        self.cost_threshold = cost_threshold
        self.total_cost = 0

    def check_node_completion(self, node_id: str):
        """Check costs when a node completes."""
        with get_db() as db:
            node = db.query(NodeExecution).filter(
                NodeExecution.id == node_id
            ).first()

            if node:
                # Calculate node cost
                cost = CostCalculator.calculate_node_cost(
                    node.input_tokens,
                    node.output_tokens,
                    node.llm_metadata.get("model") if node.llm_metadata else None
                )

                if cost:
                    self.total_cost += cost

                    # Alert if threshold exceeded
                    if self.total_cost > self.cost_threshold:
                        self.alert_cost_exceeded()

    def alert_cost_exceeded(self):
        """Alert when cost threshold is exceeded."""
        print(f"WARNING: Execution {self.execution_id} cost ${self.total_cost:.4f} "
              f"exceeded threshold ${self.cost_threshold:.4f}")
```

---

## Usage Examples

### Example 1: Basic Trace Tree Building

Complete end-to-end example of building a trace tree:

```python
from backend.services.trace import TraceTreeBuilder
from backend.services.execution.history import ExecutionHistoryService

# Step 1: Fetch execution data from database
execution_id = "exec-550e8400-e29b-41d4-a716-446655440000"
execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)

# Step 2: Build hierarchical trace tree
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

# Step 3: Access tree structure
print(f"Execution: {trace_tree['graphName']}")
print(f"Status: {trace_tree['status']}")
print(f"Duration: {trace_tree['duration']:.2f}s")
print(f"Total nodes: {trace_tree['metadata']['totalNodes']}")
print(f"Total tokens: {trace_tree['metadata']['totalTokens']:,}")
print(f"Total cost: ${trace_tree['metadata']['totalCost']:.4f} AUD")

# Step 4: Navigate hierarchy
def print_tree(nodes, indent=0):
    for node in nodes:
        print("  " * indent + f"- {node['name']} ({node['type']}) [{node['status']}]")
        if node.get('metadata', {}).get('tokens'):
            tokens = node['metadata']['tokens']
            print("  " * indent + f"  Tokens: {tokens['total']:,}")
        if node['children']:
            print_tree(node['children'], indent + 1)

print("\nExecution Tree:")
print_tree(trace_tree['nodes'])
```

### Example 2: Cost Analysis and Statistics

Complete example showing cost analysis:

```python
from backend.services.trace import StatisticsService, CostCalculator
from backend.services.database import get_db
from backend.models import NodeExecution

# Step 1: Fetch all nodes for an execution
execution_id = "exec-550e8400-e29b-41d4-a716-446655440000"

with get_db() as db:
    nodes = db.query(NodeExecution).filter(
        NodeExecution.graph_execution_id == execution_id
    ).all()

# Step 2: Calculate comprehensive statistics
stats = StatisticsService.calculate_execution_stats(nodes)

# Step 3: Display overview statistics
print("=== Execution Statistics ===")
print(f"Total Nodes: {stats['totalNodes']}")
print(f"Completed: {stats['completedNodes']}")
print(f"Failed: {stats['failedNodes']}")
print(f"Running: {stats['runningNodes']}")
print()

# Step 4: Display token usage
print("=== Token Usage ===")
print(f"Total Tokens: {stats['totalTokens']:,}")
print(f"Average Duration: {stats['averageDuration']:.2f}s")
print()

# Step 5: Display cost breakdown by type
print("=== Cost by Node Type ===")
for node_type, cost in sorted(stats['costByType'].items(), key=lambda x: x[1], reverse=True):
    tokens = stats['tokensByType'].get(node_type, 0)
    print(f"{node_type:15s}: ${cost:8.4f} ({tokens:,} tokens)")
print()

# Step 6: Display cost breakdown by model
print("=== Cost by Model ===")
for model, cost in sorted(stats['costByModel'].items(), key=lambda x: x[1], reverse=True):
    print(f"{model:20s}: ${cost:8.4f}")
print()

# Step 7: Display performance metrics
print("=== Performance Metrics ===")
perf = stats['performanceMetrics']
if perf['averageTokensPerSecond']:
    print(f"Avg Tokens/Second: {perf['averageTokensPerSecond']:.2f}")
if perf['averageTimeToFirstToken']:
    print(f"Avg Time to First Token: {perf['averageTimeToFirstToken']:.2f}ms")
print()

# Step 8: Calculate total cost separately
total_cost = CostCalculator.calculate_total_cost(nodes)
print(f"Total Cost: ${total_cost:.4f} AUD")
```

### Example 3: Export Workflow

Show all export formats:

```python
from backend.services.trace import TraceTreeBuilder, ExportService
from backend.services.execution.history import ExecutionHistoryService
import json

execution_id = "exec-550e8400-e29b-41d4-a716-446655440000"

# Step 1: Build trace tree
execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

# Step 2: Export as JSON (for API/frontend)
json_export = ExportService.export_as_json(trace_tree)
with open(f"trace_{execution_id}.json", "w") as f:
    json.dump(json_export, f, indent=2)
print(f"Exported JSON to trace_{execution_id}.json")

# Step 3: Export as YAML (human-readable)
yaml_export = ExportService.export_as_yaml(trace_tree)
with open(f"trace_{execution_id}.yaml", "w") as f:
    f.write(yaml_export)
print(f"Exported YAML to trace_{execution_id}.yaml")

# Step 4: Export as OpenTelemetry (for monitoring tools)
otel_export = ExportService.export_as_opentelemetry(trace_tree)
with open(f"trace_{execution_id}_otel.json", "w") as f:
    json.dump(otel_export, f, indent=2)
print(f"Exported OpenTelemetry to trace_{execution_id}_otel.json")

# Step 5: Send to Jaeger (optional)
import requests
try:
    response = requests.post(
        "http://localhost:14268/api/traces",
        json=otel_export,
        timeout=5
    )
    if response.status_code == 200:
        print("Successfully sent trace to Jaeger")
except requests.exceptions.RequestException as e:
    print(f"Could not send to Jaeger: {e}")
```

### Example 4: Metadata Enrichment During Execution

Show how to enrich node executions with metadata:

```python
from backend.services.trace import TraceMetadataService
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import time

# Simulate an agent execution
def execute_agent_with_trace(query: str):
    """Execute agent and capture rich trace metadata."""

    # Step 1: Prepare messages
    messages = [
        SystemMessage(content="You are a helpful data analyst assistant"),
        HumanMessage(content=query)
    ]

    # Step 2: Record start time
    start_time = time.time()

    # Step 3: Make LLM call (simulated)
    # In real code, this would call the actual LLM
    llm_response = {
        "content": "Here's the analysis...",
        "model": "gpt-4o",
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 300,
            "total_tokens": 450
        }
    }

    # Add AI response to messages
    messages.append(AIMessage(content=llm_response["content"]))

    # Step 4: Record end time
    end_time = time.time()

    # Step 5: Create base node execution data
    node_data = {
        "node_type": "AGENT",
        "node_name": "Data Analyst Agent",
        "status": "completed",
        "input_tokens": llm_response["usage"]["prompt_tokens"],
        "output_tokens": llm_response["usage"]["completion_tokens"],
        "total_tokens": llm_response["usage"]["total_tokens"],
        "input_data": {"query": query},
        "output_data": {"response": llm_response["content"]}
    }

    # Step 6: Enrich with metadata
    enriched_data = TraceMetadataService.enrich_node_execution(
        node_execution_data=node_data,
        llm_response=llm_response,
        messages=messages,
        config={
            "model": "gpt-4o",
            "provider": "azure",
            "temperature": 0.7,
            "max_tokens": 2000,
            "deployment_name": "gpt-4o-australia-east"
        }
    )

    # Step 7: Display enriched metadata
    print("=== Enriched Node Execution ===")
    print(f"Node: {enriched_data['node_name']}")
    print(f"Status: {enriched_data['status']}")

    if 'llm_metadata' in enriched_data:
        llm_meta = enriched_data['llm_metadata']
        print(f"\nLLM Metadata:")
        print(f"  Model: {llm_meta['model']}")
        print(f"  Provider: {llm_meta['provider']}")
        print(f"  Temperature: {llm_meta['temperature']}")
        print(f"  Total Cost: ${llm_meta['total_cost']:.4f}")

    if 'message_structure' in enriched_data:
        msg_struct = enriched_data['message_structure']
        print(f"\nMessage Structure:")
        print(f"  Message Count: {msg_struct['message_count']}")
        print(f"  System Prompt Tokens: {msg_struct['system_prompt_tokens']}")
        print(f"  Conversation Tokens: {msg_struct['conversation_history_tokens']}")

    if 'environment_metadata' in enriched_data:
        env_meta = enriched_data['environment_metadata']
        print(f"\nEnvironment:")
        print(f"  Environment: {env_meta['environment']}")
        print(f"  CPU Cores: {env_meta['cpu_cores']}")
        print(f"  Feature Flags: {env_meta['feature_flags']}")

    return enriched_data

# Execute with trace
result = execute_agent_with_trace("Analyze Q4 sales data")
```

### Example 5: Testing Usage

Show how to test trace services:

```python
import pytest
from backend.services.trace import (
    TraceTreeBuilder,
    StatisticsService,
    CostCalculator,
    NodeMapper
)

def test_cost_calculator():
    """Test cost calculation."""
    # Test GPT-4o cost
    cost = CostCalculator.calculate_node_cost(
        input_tokens=1000,
        output_tokens=500,
        model="gpt-4o"
    )
    assert cost is not None
    assert cost > 0
    print(f"GPT-4o cost for 1000/500 tokens: ${cost:.4f}")

    # Test with no tokens
    cost = CostCalculator.calculate_node_cost(0, 0, "gpt-4o")
    assert cost is None

def test_node_mapper():
    """Test node type mapping."""
    # Test known types
    assert NodeMapper.map_node_type("AGENT") == "agent"
    assert NodeMapper.map_node_type("TOOL") == "tool"
    assert NodeMapper.map_node_type("DATABASE_QUERY") == "tool"
    assert NodeMapper.map_node_type("SUBWORKFLOW") == "subgraph"

    # Test unknown type
    assert NodeMapper.map_node_type("UNKNOWN_TYPE") == "unknown"

def test_statistics_empty():
    """Test statistics with empty node list."""
    stats = StatisticsService.calculate_execution_stats([])

    assert stats['totalNodes'] == 0
    assert stats['totalTokens'] == 0
    assert stats['totalCost'] == 0
    assert stats['averageDuration'] == 0

def test_statistics_with_nodes():
    """Test statistics with sample nodes."""
    nodes = [
        {
            "status": "completed",
            "total_tokens": 1000,
            "input_tokens": 700,
            "output_tokens": 300,
            "duration_seconds": 5.0,
            "node_type": "AGENT",
            "llm_metadata": {"model": "gpt-4o"}
        },
        {
            "status": "completed",
            "total_tokens": 500,
            "input_tokens": 300,
            "output_tokens": 200,
            "duration_seconds": 3.0,
            "node_type": "AGENT",
            "llm_metadata": {"model": "gpt-4o"}
        }
    ]

    stats = StatisticsService.calculate_execution_stats(nodes)

    assert stats['totalNodes'] == 2
    assert stats['completedNodes'] == 2
    assert stats['totalTokens'] == 1500
    assert stats['averageDuration'] == 4.0
    assert "AGENT" in stats['tokensByType']
    assert stats['tokensByType']['AGENT'] == 1500

def test_trace_tree_builder():
    """Test trace tree building."""
    execution_data = {
        "id": "exec-123",
        "graph_name": "Test Graph",
        "status": "completed",
        "start_time": "2025-10-27T10:00:00Z",
        "end_time": "2025-10-27T10:00:10Z",
        "duration_seconds": 10.0,
        "node_executions": [
            {
                "id": "node-1",
                "node_id": "start",
                "node_name": "Start",
                "node_type": "START",
                "status": "completed",
                "execution_order": 0,
                "start_time": "2025-10-27T10:00:00Z",
                "end_time": "2025-10-27T10:00:01Z",
                "duration_seconds": 1.0
            },
            {
                "id": "node-2",
                "node_id": "agent_1",
                "node_name": "Agent",
                "node_type": "AGENT",
                "status": "completed",
                "execution_order": 1,
                "parent_agent_id": None,
                "start_time": "2025-10-27T10:00:01Z",
                "end_time": "2025-10-27T10:00:09Z",
                "duration_seconds": 8.0,
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_tokens": 1500
            }
        ]
    }

    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

    assert trace_tree['executionId'] == "exec-123"
    assert trace_tree['graphName'] == "Test Graph"
    assert trace_tree['status'] == "completed"
    assert len(trace_tree['nodes']) == 2  # Two root nodes
    assert trace_tree['metadata']['totalNodes'] == 2
    assert trace_tree['metadata']['totalTokens'] == 1500

if __name__ == "__main__":
    # Run tests
    test_cost_calculator()
    print("✓ Cost calculator tests passed")

    test_node_mapper()
    print("✓ Node mapper tests passed")

    test_statistics_empty()
    print("✓ Empty statistics tests passed")

    test_statistics_with_nodes()
    print("✓ Statistics with nodes tests passed")

    test_trace_tree_builder()
    print("✓ Trace tree builder tests passed")

    print("\nAll tests passed!")
```

---

## Performance Considerations

### Performance Characteristics

**Time Complexity:**

- `TraceTreeBuilder.build_trace_tree()`: O(n) where n is number of nodes
  - Build node map: O(n)
  - Build hierarchy: O(n)
  - Sort tree: O(n log n)
  - Calculate metadata: O(n)
- `StatisticsService.calculate_execution_stats()`: O(n) for n nodes
- `CostCalculator.calculate_total_cost()`: O(n) for n nodes
- `ExportService.export_as_opentelemetry()`: O(n) for recursive span creation

**Space Complexity:**

- `TraceTreeBuilder`: O(n) for node maps and tree structure
- `StatisticsService`: O(k) where k is number of unique node types/models
- Export formats: O(n) for full tree serialisation

**I/O Characteristics:**

- Trace service is CPU-bound (no I/O operations)
- I/O happens in calling layers (database queries, API responses)
- YAML export involves serialisation overhead

### Optimisation Tips

#### Tip 1: Batch Processing

**Problem:**

```python
# Inefficient: Building trees one at a time
for execution_id in execution_ids:
    execution_data = fetch_execution(execution_id)
    trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
    process_tree(trace_tree)
```

**Solution:**

```python
# Efficient: Fetch all executions first, then process
executions = fetch_executions_batch(execution_ids)

trace_trees = []
for execution_data in executions:
    tree = TraceTreeBuilder.build_trace_tree(execution_data)
    trace_trees.append(tree)

# Process all trees together
process_trees_batch(trace_trees)
```

#### Tip 2: Selective Metadata Capture

**Problem:**

```python
# Capturing all metadata for every node (expensive)
for node in nodes:
    enriched = TraceMetadataService.enrich_node_execution(
        node,
        llm_response=response,
        messages=messages,
        config=config
    )
```

**Solution:**

```python
# Only enrich agent nodes that need metadata
for node in nodes:
    if node['node_type'] == 'AGENT' and needs_detailed_trace:
        enriched = TraceMetadataService.enrich_node_execution(
            node,
            llm_response=response,
            messages=messages,
            config=config
        )
    else:
        enriched = node  # Skip enrichment for simple nodes
```

#### Tip 3: Lazy Export

**Problem:**

```python
# Building all export formats eagerly
json_export = ExportService.export_as_json(trace_tree)
yaml_export = ExportService.export_as_yaml(trace_tree)
otel_export = ExportService.export_as_opentelemetry(trace_tree)
```

**Solution:**

```python
# Only export in requested format
def export_trace(trace_tree, format: str):
    if format == "json":
        return ExportService.export_as_json(trace_tree)
    elif format == "yaml":
        return ExportService.export_as_yaml(trace_tree)
    elif format == "opentelemetry":
        return ExportService.export_as_opentelemetry(trace_tree)
```

#### Tip 4: Caching Expensive Calculations

**Problem:**

```python
# Recalculating statistics multiple times
stats1 = StatisticsService.calculate_execution_stats(nodes)
# ... later ...
stats2 = StatisticsService.calculate_execution_stats(nodes)  # Redundant
```

**Solution:**

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_cached_stats(execution_id: str):
    """Cached statistics calculation."""
    nodes = fetch_nodes(execution_id)
    return StatisticsService.calculate_execution_stats(nodes)

# Use cached version
stats = get_cached_stats(execution_id)
```

### Async/Await Support

The trace service does not currently provide async methods, but can be used in async contexts:

```python
from backend.services.trace import TraceTreeBuilder
import asyncio

async def build_trace_async(execution_id: str):
    """Async wrapper for trace building."""

    # Fetch data asynchronously
    execution_data = await fetch_execution_async(execution_id)

    # Build tree synchronously (CPU-bound)
    # Run in executor to avoid blocking event loop
    loop = asyncio.get_event_loop()
    trace_tree = await loop.run_in_executor(
        None,
        TraceTreeBuilder.build_trace_tree,
        execution_data
    )

    return trace_tree

# Usage in async context
trace_tree = await build_trace_async("exec-123")
```

### Batch Operations

For processing multiple executions efficiently:

```python
from backend.services.trace import TraceTreeBuilder, StatisticsService
from concurrent.futures import ThreadPoolExecutor
import asyncio

async def process_executions_batch(execution_ids: list[str]):
    """Process multiple executions in parallel."""

    # Fetch all executions concurrently
    executions = await fetch_executions_concurrent(execution_ids)

    # Build trees in parallel using thread pool
    with ThreadPoolExecutor(max_workers=4) as executor:
        loop = asyncio.get_event_loop()

        trace_trees = await asyncio.gather(*[
            loop.run_in_executor(
                executor,
                TraceTreeBuilder.build_trace_tree,
                execution_data
            )
            for execution_data in executions
        ])

    return trace_trees
```

---

## Best Practices

### Do's

✅ **Use class methods directly without instantiation**

```python
# Good: Direct class method usage
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
stats = StatisticsService.calculate_execution_stats(nodes)

# Avoid: Unnecessary instantiation
# builder = TraceTreeBuilder()  # Not needed
```

✅ **Check for null/empty data before processing**

```python
# Good: Defensive checks
execution_data = fetch_execution(execution_id)
if not execution_data:
    return {"error": "Execution not found"}

nodes = execution_data.get("node_executions", [])
if not nodes:
    return {"nodes": [], "metadata": {}}

trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
```

✅ **Use appropriate export format for use case**

```python
# Good: Choose format based on consumer
# For frontend/API: JSON
json_data = ExportService.export_as_json(trace_tree)

# For human review: YAML
yaml_report = ExportService.export_as_yaml(trace_tree)

# For monitoring tools: OpenTelemetry
otel_data = ExportService.export_as_opentelemetry(trace_tree)
send_to_jaeger(otel_data)
```

✅ **Handle both dict and SQLAlchemy model inputs**

```python
# Good: Services handle both input types
from backend.models import NodeExecution

# Works with SQLAlchemy models
nodes_orm = db.query(NodeExecution).all()
stats1 = StatisticsService.calculate_execution_stats(nodes_orm)

# Works with dictionaries
nodes_dict = [{"status": "completed", "total_tokens": 100}]
stats2 = StatisticsService.calculate_execution_stats(nodes_dict)
```

✅ **Log important events and warnings**

```python
# Good: Informative logging
from backend.services.config import get_logger

logger = get_logger("my_service")

logger.info(f"Building trace tree for execution {execution_id}")
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)

if trace_tree['metadata']['failedNodes'] > 0:
    logger.warning(f"Execution has {trace_tree['metadata']['failedNodes']} failed nodes")
```

✅ **Aggregate statistics at appropriate levels**

```python
# Good: Calculate statistics once, reuse results
stats = StatisticsService.calculate_execution_stats(nodes)

total_cost = stats['totalCost']
total_tokens = stats['totalTokens']
cost_by_model = stats['costByModel']

# Display multiple metrics from single calculation
print(f"Cost: ${total_cost:.4f}")
print(f"Tokens: {total_tokens:,}")
for model, cost in cost_by_model.items():
    print(f"  {model}: ${cost:.4f}")
```

### Don'ts

❌ **Don't instantiate service classes unnecessarily**

```python
# Bad: Creating instance when class methods are available
builder = TraceTreeBuilder()
trace_tree = builder.build_trace_tree(execution_data)

# Good: Use class method directly
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
```

❌ **Don't recalculate costs when already available**

```python
# Bad: Recalculating when node has total_cost
cost = CostCalculator.calculate_node_cost(
    node.input_tokens,
    node.output_tokens,
    model
)

# Good: Use existing cost if available
cost = node.total_cost or CostCalculator.calculate_node_cost(
    node.input_tokens,
    node.output_tokens,
    model
)

# Better: Services handle this automatically
total_cost = CostCalculator.calculate_total_cost(nodes)
```

❌ **Don't ignore missing parent warnings**

```python
# Bad: Ignoring structural issues
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
# Warning: Missing parent node_id XYZ logged but not handled

# Good: Investigate and fix data issues
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
if "Missing parent" in captured_logs:
    investigate_parent_tracking_issue()
```

❌ **Don't mix pricing currencies without conversion**

```python
# Bad: Adding USD and AUD costs
TOKEN_COSTS = {
    "gpt-4o": {"input": 3.85446, "output": 15.4179},  # AUD
    "claude-3": {"input": 3.0, "output": 15.0},  # USD - Wrong!
}

# Good: Use consistent currency
TOKEN_COSTS = {
    "gpt-4o": {"input": 3.85446, "output": 15.4179},  # AUD
    "claude-3": {"input": 4.5, "output": 22.5},  # AUD (converted)
}
```

❌ **Don't export large traces without pagination**

```python
# Bad: Exporting massive trace trees all at once
huge_trace_tree = TraceTreeBuilder.build_trace_tree(massive_execution)
yaml_export = ExportService.export_as_yaml(huge_trace_tree)  # OOM risk

# Good: Check size and paginate if needed
trace_tree = TraceTreeBuilder.build_trace_tree(execution_data)
node_count = trace_tree['metadata']['totalNodes']

if node_count > 1000:
    logger.warning(f"Large trace with {node_count} nodes")
    # Consider pagination or sampling
else:
    yaml_export = ExportService.export_as_yaml(trace_tree)
```

❌ **Don't assume all nodes have LLM data**

```python
# Bad: Assuming all nodes have token data
for node in nodes:
    tokens = node['total_tokens']  # KeyError if tool node!
    cost = node['llm_metadata']['model']  # KeyError!

# Good: Check node type and data availability
for node in nodes:
    if node.get('node_type') == 'AGENT' and node.get('total_tokens'):
        tokens = node['total_tokens']
        if node.get('llm_metadata'):
            model = node['llm_metadata'].get('model')
```

---

## Related Documentation

### Related Services

- [Execution Service](execution.md) - Workflow execution and node tracking
- [Database Service](database.md) - Database operations and models
- [Config Service](config.md) - Logging and configuration

### Related API Modules

- [Trace API](../../../backend/api/trace/trace.md) - REST endpoints for trace visualization
- [Graph API](../../../backend/api/graph/graph.md) - Graph execution endpoints
- [WebSocket API](../../../backend/api/websocket/websocket.md) - Real-time execution updates

### Related Models

- `NodeExecution` - Database model for node executions
- `GraphExecution` - Database model for workflow executions

### External Documentation

- [OpenTelemetry](https://opentelemetry.io/) - Distributed tracing standard
- [Jaeger](https://www.jaegertracing.io/) - Distributed tracing platform
- [LangChain](https://python.langchain.com/) - LLM framework integration

---

## Summary

The trace service module is a comprehensive execution analysis toolkit that transforms flat execution data into rich,
hierarchical visualizations. It provides the foundation for understanding workflow behaviour, analyzing costs,
monitoring performance, and debugging complex agent interactions in AgenticStudio.

**Key Features:**

- Hierarchical tree building from flat execution records
- Comprehensive statistics and cost analysis
- Multiple export formats (JSON, YAML, OpenTelemetry)
- Rich metadata capture for LLM, tool, and orchestration operations
- Model-specific cost calculation
- Real-time trace streaming support

**Primary Use Cases:**

- Visualizing workflow execution flow in the frontend trace viewer
- Analyzing LLM costs and optimizing model selection
- Debugging complex agent orchestrations and delegation patterns
- Exporting traces to external monitoring and analysis tools
- Performance monitoring and optimization
- Budget tracking and cost forecasting

**When to Use This Service:**

- When you need to display execution traces in the UI
- When analyzing execution costs and token usage
- When debugging workflow or agent behaviour
- When integrating with external tracing tools
- When generating execution reports or analytics
- When optimizing performance based on execution metrics

The trace service is designed to be stateless and efficient, using class methods for easy integration and supporting
both dictionary and ORM inputs for flexibility. It forms a critical part of the AgenticStudio observability stack, providing
insights into every aspect of workflow execution.
