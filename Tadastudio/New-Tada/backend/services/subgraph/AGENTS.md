# Subgraph Service Module

## Overview

The Subgraph service provides native LangGraph subgraph support for sub-agent and sub-workflow execution in AgenticStudio.
It eliminates the need for creating new event loops and context variable workarounds by implementing proper async
delegation patterns using LangGraph's native subgraph capabilities.

**Location:** [backend/services/subgraph/](../../backend/services/subgraph/)

**Primary Responsibilities:**

- Creating and caching compiled LangGraph subgraphs for sub-agents and sub-workflows
- Managing state passing between parent graphs and subgraphs
- Executing sub-agents with proper async patterns and database tracking
- Executing sub-workflows with node traversal and output collection
- Tracking tool executions performed by sub-agents
- Sending WebSocket notifications for execution progress
- Managing execution context and graph resolution

**Key Use Cases:**

- Agent orchestration: One agent delegating tasks to other agents
- Workflow composition: Agents invoking nested workflows
- Parallel agent execution: Multiple sub-agents executing concurrently
- Tool execution tracking: Monitoring tools used by delegated agents

## Architecture

### Module Structure

```
backend/services/subgraph/
├── __init__.py                      # Public API exports
├── models.py                        # State TypedDicts and data models
├── builder.py                       # SubgraphBuilder for creating graphs
├── executor.py                      # SubgraphExecutor for running graphs
├── cache.py                         # SubgraphCache for compiled graphs
├── agent/                           # Agent subgraph components
│   ├── __init__.py                  # Exports create_agent_subgraph
│   ├── factory.py                   # Agent subgraph factory function
│   ├── execution_handler.py         # Agent execution coordination
│   ├── database_tracker.py          # Database record management
│   └── tool_tracker.py              # Tool execution tracking
└── workflow/                        # Workflow subgraph components
    ├── __init__.py                  # Exports create_workflow_subgraph
    ├── factory.py                   # Workflow subgraph factory function
    ├── execution_handler.py         # Workflow execution coordination
    ├── database_tracker.py          # Database record management
    └── node_executor.py             # Individual node execution
```

**File Responsibilities:**

- **models.py** - Defines TypedDict state models for subgraph execution (SubAgentState, SubWorkflowState) and supporting
  data structures (ToolExecution, ToolNodeMapping, TokenCounts)
- **builder.py** - SubgraphBuilder class that creates and caches compiled subgraphs for both agents and workflows
- **executor.py** - SubgraphExecutor class that handles state preparation and subgraph invocation
- **cache.py** - SubgraphCache class that stores compiled graphs by node ID and version
- **agent/factory.py** - Factory function to create agent subgraphs with proper state management
- **agent/execution_handler.py** - Core agent execution logic with database tracking and WebSocket notifications
- **agent/database_tracker.py** - Database record creation and updates for sub-agent execution
- **agent/tool_tracker.py** - Tool execution tracking with database records and notifications
- **workflow/factory.py** - Factory function to create workflow subgraphs
- **workflow/execution_handler.py** - Workflow traversal and node execution coordination
- **workflow/database_tracker.py** - Database record management for sub-workflows
- **workflow/node_executor.py** - Execution logic for individual workflow nodes (AGENT, END)

### Design Patterns

#### Factory Pattern

The module uses the **Factory Pattern** extensively to create different types of subgraphs:

```
SubgraphBuilder (Façade)
    ↓
create_agent_subgraph() (Factory)
    ↓
StateGraph with agent execution node
    ↓
Compiled graph ready for execution
```

```
SubgraphBuilder (Façade)
    ↓
create_workflow_subgraph() (Factory)
    ↓
StateGraph with workflow execution node
    ↓
Compiled graph ready for execution
```

**Benefits:**

- Encapsulates complex graph construction logic
- Provides consistent interface for creating subgraphs
- Allows easy addition of new subgraph types

#### Builder Pattern

**SubgraphBuilder** acts as a builder that coordinates:

- Graph creation via factories
- Caching of compiled graphs
- Cache management and lookup

#### Executor Pattern

**SubgraphExecutor** separates graph execution from graph construction:

- Prepares initial state from parent state
- Invokes compiled subgraphs asynchronously
- Extracts results for parent state updates

#### Cache Pattern

**SubgraphCache** implements caching with:

- Key generation based on node ID and version
- Prefix support for different subgraph types (agent_, workflow_)
- Cache invalidation methods

#### Handler Pattern

Execution handlers coordinate multiple concerns:

- Database tracking
- WebSocket notifications
- Tool execution monitoring
- Error handling
- State management

**Separation of Concerns:**

```
execution_handler.py     → High-level coordination
database_tracker.py      → Database operations
tool_tracker.py          → Tool tracking (agents only)
node_executor.py         → Node execution (workflows only)
```

### Dependencies

#### Internal Dependencies

**Model Dependencies:**

- `backend.models.workflow` - EnhancedNodeData, NodeType, AgentConfig
- Provides workflow and node data structures

**Service Dependencies:**

- `backend.services.config` - get_logger() for logging
- `backend.services.execution.history` - ExecutionHistoryService for database tracking
- `backend.services.execution.context` - get_current_execution_id() for context resolution
- `backend.services.common.utils.websocket_notifier` - WebSocket notification functions
- `backend.services.common.utils.tool_type_mapper` - Tool type mapping and extraction
- `backend.services.common.utils.response_extractor` - Response content extraction

**Integration Points:**

```
Subgraph Service
    ↓
Uses graph_manager (from caller)
    ↓
graph_manager.execute_agent_async()
graph_manager.get_node()
graph_manager.get_graph()
```

#### External Dependencies

**LangGraph (langgraph):**

- `langgraph.graph.StateGraph` - Graph construction
- `langgraph.graph.END` - Graph termination constant
- `langgraph.checkpoint.base.BaseCheckpointSaver` - State persistence
- `langgraph.graph.message.add_messages` - Message state reducer

**LangChain (langchain_core):**

- `langchain_core.messages.BaseMessage` - Message base class
- `langchain_core.messages.HumanMessage` - User messages
- `langchain_core.messages.AIMessage` - Agent responses

**Python Standard Library:**

- `datetime` - Timestamp management
- `typing` - Type annotations
- `asyncio` - Async event loop utilities (tool_tracker.py)

#### Database Dependencies

The module relies on the **ExecutionHistoryService** for:

- Creating node execution records
- Starting node execution (timestamp marking)
- Completing node execution (status, output, token counts)
- Retrieving node execution data

**Database Schema Assumptions:**

- Node executions have: id, node_id, node_name, node_type, status, input_data, output_data, execution_order
- Token tracking: input_tokens, output_tokens, total_tokens
- Timing: start_time, end_time, duration_seconds
- Hierarchy: is_sub_agent, parent_agent_id

#### Configuration

**No Environment Variables:** This module does not directly consume environment variables.

**Logging Configuration:**

- Uses `backend.services.config.get_logger()` to obtain loggers
- Logger names: `subgraph.builder`, `subgraph.executor`, `subgraph.cache`, `subgraph.agent.*`, `subgraph.workflow.*`

## Public API

### Exported Classes

The following classes are exported in `__all__`:

- `SubgraphBuilder` - Creates and caches subgraphs for agents and workflows
- `SubgraphExecutor` - Executes subgraphs with proper state management
- `SubAgentState` - TypedDict for sub-agent execution state
- `SubWorkflowState` - TypedDict for sub-workflow execution state
- `ToolExecution` - TypedDict for tool execution tracking
- `ToolNodeMapping` - TypedDict for tool-to-node mapping
- `TokenCounts` - TypedDict for LLM token usage

### Exported Functions

- `create_subagent_graph()` - Convenience function for backward compatibility; creates a compiled subgraph for an agent
  node

### Constants and Configuration

**No exported constants.** The module uses internal constants from LangGraph (e.g., `END`).

### Exceptions

**No custom exceptions defined.** The module relies on standard Python exceptions and LangGraph exceptions. Errors are
logged and returned in state dictionaries.

## Core Classes

### `SubgraphBuilder`

The SubgraphBuilder class coordinates the creation of LangGraph subgraphs for sub-agent and sub-workflow execution,
providing caching to avoid redundant compilation.

**Purpose:**

- Provides a unified interface for creating both agent and workflow subgraphs
- Manages a cache of compiled graphs to improve performance
- Coordinates with factory functions to build subgraphs

**Responsibilities:**

- Create agent subgraphs with proper execution logic
- Create workflow subgraphs with node traversal
- Cache compiled subgraphs by node ID and version
- Provide cache management utilities

**Initialisation:**

```python
def __init__(
    self,
    graph_manager: Any,
) -> None:
    """
    Initialise the subgraph builder.

    Args:
        graph_manager: The GraphManager instance for agent execution
    """
```

**Key Methods:**

#### `create_subagent_graph()`

```python
def create_subagent_graph(
    self,
    agent_node: EnhancedNodeData,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> StateGraph:
    """
    Create a subgraph for a delegated agent.

    This subgraph will:
    1. Execute the agent with proper async patterns
    2. Track execution in the database
    3. Update execution order
    4. Track tool executions
    5. Send WebSocket notifications
    6. Return results to parent graph
    """
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - The agent node to create a subgraph for
- `checkpointer` (Optional[BaseCheckpointSaver]) - Optional checkpointer for state persistence (default: None)

**Returns:**

- `StateGraph` - Compiled StateGraph ready for execution

**Example:**

```python
from backend.services.subgraph import SubgraphBuilder
from backend.models.workflow import EnhancedNodeData

# Assume we have a graph_manager and an agent_node
graph_manager = get_graph_manager()
agent_node = graph_manager.get_node("my-graph", "agent-node-id")

# Create subgraph builder
builder = SubgraphBuilder(graph_manager)

# Create compiled subgraph for the agent
subgraph = builder.create_subagent_graph(agent_node)

# The subgraph is now ready to execute
```

**Behaviour:**

- Checks cache first using node ID and version
- If cached, returns the compiled graph immediately
- If not cached, calls `create_agent_subgraph()` factory
- Stores the compiled graph in cache with "agent_" prefix
- Logs cache hits/misses for debugging

**Use Cases:**

- Agent orchestration where one agent delegates to another
- Creating reusable agent subgraphs for multiple executions
- Optimising performance by caching compiled graphs

#### `create_subworkflow_graph()`

```python
def create_subworkflow_graph(
    self,
    subworkflow_node: EnhancedNodeData,
    graph_name: Optional[str] = None,
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> StateGraph:
    """
    Create a subgraph for a sub-workflow execution.

    This subgraph will:
    1. Start from the SUBWORKFLOW node (acts as START)
    2. Execute all connected workflow nodes
    3. Collect output from END node
    4. Track execution in the database
    5. Send WebSocket notifications
    6. Return results to parent agent
    """
```

**Parameters:**

- `subworkflow_node` (EnhancedNodeData) - The SUBWORKFLOW node that starts the workflow
- `graph_name` (Optional[str]) - Name of the parent graph for context (default: None)
- `checkpointer` (Optional[BaseCheckpointSaver]) - Optional checkpointer for state persistence (default: None)

**Returns:**

- `StateGraph` - Compiled StateGraph ready for execution

**Example:**

```python
from backend.services.subgraph import SubgraphBuilder

# Create subgraph builder
builder = SubgraphBuilder(graph_manager)

# Get a subworkflow node
subworkflow_node = graph_manager.get_node("my-graph", "subworkflow-id")

# Create compiled subgraph for the workflow
subgraph = builder.create_subworkflow_graph(
    subworkflow_node,
    graph_name="my-graph"
)
```

**Behaviour:**

- Checks cache with "workflow_" prefix
- Creates workflow subgraph via factory if not cached
- Caches the compiled workflow graph
- Logs creation and caching events

**Use Cases:**

- Agents invoking nested workflows
- Reusable workflow components
- Workflow composition patterns

#### `clear_cache()`

```python
def clear_cache(self) -> None:
    """Clear the subgraph cache."""
```

**Example:**

```python
builder = SubgraphBuilder(graph_manager)

# After updating workflow definitions
builder.clear_cache()
```

**Behaviour:**

- Removes all cached subgraphs
- Logs the cache clear event
- Next subgraph creation will recompile from scratch

**Use Cases:**

- Workflow definition updates
- Memory management
- Testing and development

#### `get_cached_subgraph()`

```python
def get_cached_subgraph(
    self,
    agent_node: EnhancedNodeData,
) -> Optional[StateGraph]:
    """
    Get a cached subgraph if it exists.

    Returns the cached StateGraph, or None if not found.
    """
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - The agent node to look up

**Returns:**

- `Optional[StateGraph]` - The cached graph or None

**Example:**

```python
# Check if subgraph is already cached
cached = builder.get_cached_subgraph(agent_node)
if cached:
    print("Using cached subgraph")
else:
    print("Will need to compile new subgraph")
```

**Behaviour:**

- Looks up cache with "agent_" prefix
- Returns None without side effects if not cached
- Does not create or compile new graphs

**Use Cases:**

- Pre-flight cache checks
- Monitoring cache effectiveness
- Conditional graph creation logic

**Class Attributes:**

- `graph_manager: Any` - The GraphManager instance for agent/workflow execution
- `_cache: SubgraphCache` - Internal cache instance for storing compiled graphs

---

### `SubgraphExecutor`

The SubgraphExecutor class handles the execution of subgraphs with proper async patterns, managing state passing between
parent graphs and subgraphs.

**Purpose:**

- Prepare initial subgraph state from parent state
- Execute subgraphs asynchronously
- Extract and format results for parent state updates

**Responsibilities:**

- State transformation between parent and subgraph formats
- Async subgraph invocation
- Error handling and result extraction
- Execution order management

**Initialisation:**

```python
def __init__(
    self,
    subgraph_builder: SubgraphBuilder,
) -> None:
    """
    Initialise the executor.

    Args:
        subgraph_builder: The SubgraphBuilder instance
    """
```

**Key Methods:**

#### `execute_subagent()`

```python
async def execute_subagent(
    self,
    agent_node: EnhancedNodeData,
    task: str,
    parent_state: Dict[str, Any],
    checkpointer: Optional[BaseCheckpointSaver] = None,
) -> Dict[str, Any]:
    """
    Execute a sub-agent as a subgraph.

    Returns updated state containing:
    - execution_order: Updated execution order
    - subagent_response: The agent's response
    - subagent_error: Error message if execution failed
    - tool_executions: List of tool executions performed
    """
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - The agent to execute
- `task` (str) - The task description
- `parent_state` (Dict[str, Any]) - The parent graph's state
- `checkpointer` (Optional[BaseCheckpointSaver]) - Optional checkpointer (default: None)

**Returns:**

- `Dict[str, Any]` - Updated state dictionary with execution results

**Raises:**

- Does not raise exceptions; errors are returned in the state dictionary under "subagent_error" key

**Example:**

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

# Setup
builder = SubgraphBuilder(graph_manager)
executor = SubgraphExecutor(builder)

# Parent state
parent_state = {
    "execution_id": "exec-123",
    "db_execution_id": "db-456",
    "current_node": "orchestrator-node",
    "execution_order": 5,
    "graph_name": "my-workflow",
    "tool_node_mapping": {"search_web": "search-node-id"},
    "metadata": {"current_node_name": "Orchestrator"}
}

# Execute sub-agent
result = await executor.execute_subagent(
    agent_node=agent_node,
    task="Analyse the customer feedback and provide insights",
    parent_state=parent_state
)

# Check results
if result.get("subagent_error"):
    print(f"Error: {result['subagent_error']}")
else:
    print(f"Response: {result['subagent_response']}")
    print(f"Tools used: {len(result['tool_executions'])}")
    print(f"New execution order: {result['execution_order']}")
```

**Behaviour:**

- Creates SubAgentState from parent state
- Retrieves or creates subgraph via builder
- Invokes subgraph with `ainvoke()` for async execution
- Extracts relevant fields from result state
- Returns compact state update for parent
- Logs execution progress and errors

**Use Cases:**

- Agent delegation within workflows
- Orchestrator patterns where one agent coordinates others
- Async agent execution with proper context

---

### `SubgraphCache`

Cache for compiled LangGraph subgraphs, storing graphs keyed by node ID and version to reduce compilation overhead.

**Purpose:**

- Store compiled subgraphs to avoid redundant compilation
- Provide fast lookup by node identity
- Support cache invalidation

**Responsibilities:**

- Generate cache keys from node identity
- Store and retrieve compiled StateGraphs
- Track cache size and contents
- Clear cache when needed

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise an empty subgraph cache."""
```

**Key Methods:**

#### `get_cache_key()`

```python
def get_cache_key(
    self,
    node: EnhancedNodeData,
    prefix: str = "",
) -> str:
    """
    Generate a cache key for a node.

    Returns a unique cache key string.
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - The node to generate a key for
- `prefix` (str) - Optional prefix for the cache key (e.g., "agent_", "workflow_") (default: "")

**Returns:**

- `str` - A unique cache key in format: "{prefix}{node_id}_{version}"

**Example:**

```python
cache = SubgraphCache()

# Generate cache keys
key1 = cache.get_cache_key(agent_node, prefix="agent_")
# Returns: "agent_abc-123_v1"

key2 = cache.get_cache_key(workflow_node, prefix="workflow_")
# Returns: "workflow_def-456_v2"
```

#### `get()`

```python
def get(
    self,
    node: EnhancedNodeData,
    prefix: str = "",
) -> Optional[StateGraph]:
    """
    Retrieve a cached subgraph if it exists.

    Returns the cached StateGraph, or None if not found.
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - The node to look up
- `prefix` (str) - Optional prefix for the cache key (default: "")

**Returns:**

- `Optional[StateGraph]` - The cached StateGraph, or None if not found

**Example:**

```python
cache = SubgraphCache()

# Attempt retrieval
subgraph = cache.get(agent_node, prefix="agent_")
if subgraph:
    print("Cache hit!")
else:
    print("Cache miss - need to compile")
```

**Behaviour:**

- Generates cache key from node
- Looks up in internal dictionary
- Logs cache hit or miss
- Returns None without side effects if not found

#### `put()`

```python
def put(
    self,
    node: EnhancedNodeData,
    subgraph: StateGraph,
    prefix: str = "",
) -> None:
    """Store a compiled subgraph in the cache."""
```

**Parameters:**

- `node` (EnhancedNodeData) - The node the subgraph was created for
- `subgraph` (StateGraph) - The compiled StateGraph to cache
- `prefix` (str) - Optional prefix for the cache key (default: "")

**Example:**

```python
cache = SubgraphCache()

# Compile and cache
compiled_graph = workflow.compile()
cache.put(agent_node, compiled_graph, prefix="agent_")
```

**Behaviour:**

- Generates cache key
- Stores subgraph in internal dictionary
- Logs caching event with key
- Overwrites existing entry if key exists

#### `clear()`

```python
def clear(self) -> None:
    """Clear all cached subgraphs."""
```

**Example:**

```python
cache = SubgraphCache()

# Clear all cached graphs
cache.clear()
```

**Behaviour:**

- Removes all entries from cache
- Logs number of entries cleared
- Frees memory used by cached graphs

#### `size()`

```python
def size(self) -> int:
    """
    Get the number of cached subgraphs.

    Returns the number of items in the cache.
    """
```

**Example:**

```python
cache = SubgraphCache()
print(f"Cache contains {cache.size()} subgraphs")
```

#### `has()`

```python
def has(
    self,
    node: EnhancedNodeData,
    prefix: str = "",
) -> bool:
    """
    Check if a subgraph is cached.

    Returns True if the subgraph is cached, False otherwise.
    """
```

**Example:**

```python
if cache.has(agent_node, prefix="agent_"):
    print("Subgraph is cached")
```

**Class Attributes:**

- `_cache: Dict[str, StateGraph]` - Internal dictionary storing cached subgraphs

---

## State Models

### `SubAgentState`

TypedDict defining the state structure for sub-agent execution within a subgraph.

**Purpose:** Pass execution context and results between parent graph and agent subgraph.

**Fields:**

```python
class SubAgentState(TypedDict):
    # Task information
    task_description: str                          # The task to be performed
    task_id: Optional[str]                         # Unique task identifier

    # Execution context
    parent_execution_id: str                       # Parent's execution ID
    parent_db_execution_id: Optional[str]          # Parent's database execution ID
    parent_node_id: str                            # Parent orchestrator's node ID
    parent_node_name: str                          # Parent orchestrator's name

    # Execution tracking
    execution_order: int                           # Current execution order counter
    start_time: Optional[str]                      # ISO format start time
    end_time: Optional[str]                        # ISO format end time

    # Agent information
    agent_node_id: str                             # Sub-agent's node ID
    agent_node_name: str                           # Sub-agent's display name
    agent_config: Optional[Dict[str, Any]]         # Agent configuration

    # Graph context for tool resolution
    graph_name: Optional[str]                      # Parent graph name
    tool_node_mapping: Optional[Dict[str, str]]    # Tool name to node ID mapping
    tool_execution_tracker: List[Dict[str, Any]]   # Internal tool execution list

    # Results
    response: Optional[str]                        # Text response from agent
    structured_output: Optional[Dict[str, Any]]    # Structured output data
    tool_executions: List[Dict[str, Any]]          # Tool executions performed
    error: Optional[str]                           # Error message if failed

    # Messages for conversation context
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Metadata
    metadata: Dict[str, Any]                       # Additional execution metadata
```

**Example:**

```python
from backend.services.subgraph import SubAgentState
from langchain_core.messages import HumanMessage

# Create initial state for sub-agent
initial_state: SubAgentState = {
    "task_description": "Analyse customer sentiment from reviews",
    "task_id": "task_001",
    "parent_execution_id": "exec-abc-123",
    "parent_db_execution_id": "db-456",
    "parent_node_id": "orchestrator-node-id",
    "parent_node_name": "Customer Insights Orchestrator",
    "execution_order": 3,
    "start_time": None,
    "end_time": None,
    "agent_node_id": "sentiment-agent-id",
    "agent_node_name": "Sentiment Analyser",
    "agent_config": {"temperature": 0.7},
    "graph_name": "customer-insights-workflow",
    "tool_node_mapping": {"search_reviews": "review-search-node"},
    "tool_execution_tracker": [],
    "response": None,
    "structured_output": None,
    "tool_executions": [],
    "error": None,
    "messages": [HumanMessage(content="Analyse customer sentiment")],
    "metadata": {}
}
```

---

### `SubWorkflowState`

TypedDict defining the state structure for sub-workflow execution within a subgraph.

**Purpose:** Pass execution context and results between parent agent and workflow subgraph.

**Fields:**

```python
class SubWorkflowState(TypedDict):
    # Task information
    task_description: str                          # Task description for workflow
    workflow_input: Dict[str, Any]                 # Additional parameters from agent

    # Execution context
    parent_execution_id: str                       # Parent's execution ID
    parent_db_execution_id: Optional[str]          # Parent's database execution ID
    parent_node_id: str                            # Parent orchestrator's node ID
    parent_node_name: str                          # Parent orchestrator's name

    # Execution tracking
    execution_order: int                           # Current execution order counter
    start_time: Optional[str]                      # ISO format start time
    end_time: Optional[str]                        # ISO format end time

    # Workflow information
    workflow_node_id: str                          # Workflow node's ID
    workflow_node_name: str                        # Workflow's display name
    workflow_config: Optional[Dict[str, Any]]      # Workflow configuration

    # Graph context
    graph_name: Optional[str]                      # Parent graph name

    # Results
    workflow_output: Optional[str]                 # Output from END node
    nodes_executed: List[str]                      # List of executed node names
    structured_output: Optional[Dict[str, Any]]    # Structured output data
    error: Optional[str]                           # Error message if failed
    response: Optional[str]                        # Response text (compatibility)

    # Messages for conversation context
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Metadata
    metadata: Dict[str, Any]                       # Additional execution metadata
```

**Example:**

```python
from backend.services.subgraph import SubWorkflowState
from langchain_core.messages import HumanMessage

# Create initial state for sub-workflow
initial_state: SubWorkflowState = {
    "task_description": "Process customer order",
    "workflow_input": {"order_id": "ORD-123", "customer_id": "CUST-456"},
    "parent_execution_id": "exec-xyz-789",
    "parent_db_execution_id": "db-321",
    "parent_node_id": "order-agent-id",
    "parent_node_name": "Order Processing Agent",
    "execution_order": 5,
    "start_time": None,
    "end_time": None,
    "workflow_node_id": "order-workflow-id",
    "workflow_node_name": "Order Fulfilment Workflow",
    "workflow_config": None,
    "graph_name": "order-management",
    "workflow_output": None,
    "nodes_executed": [],
    "structured_output": None,
    "error": None,
    "response": None,
    "messages": [HumanMessage(content="Process order ORD-123")],
    "metadata": {}
}
```

---

### `ToolExecution`

TypedDict for structured tool execution tracking with support for different tool types (HTTP, search, MCP).

**Purpose:** Capture tool execution details for database recording and notification.

**Fields:**

```python
class ToolExecution(TypedDict, total=False):
    tool: str                                      # Tool name
    input: Dict[str, Any]                          # Input data passed to tool
    output: Any                                    # Output/results from tool
    results: Any                                   # Alternative field for results
    response: Dict[str, Any]                       # Response data (HTTP tools)
    request: Dict[str, Any]                        # Request data (HTTP tools)
    query: str                                     # Query string (search tools)
    provider: str                                  # Provider name (search tools)
    formatted_results: str                         # Formatted search results
    action: str                                    # Action performed (MCP tools)
    target: str                                    # Target of action (MCP tools)
    server: str                                    # Server name (MCP tools)
    connection_type: str                           # Connection type (MCP tools)
    arguments: Dict[str, Any]                      # Arguments passed (MCP tools)
    formatted_output: str                          # Formatted output (MCP tools)
    kwargs: Dict[str, Any]                         # Keyword arguments
    args: Any                                      # Positional arguments
    duration: float                                # Execution duration in seconds
    timestamp: float                               # Execution timestamp
    error: str                                     # Error message if failed
```

**Example:**

```python
from backend.services.subgraph import ToolExecution

# HTTP tool execution
http_tool_exec: ToolExecution = {
    "tool": "http_request_post",
    "request": {
        "url": "https://api.example.com/data",
        "method": "POST",
        "body": {"query": "customer data"}
    },
    "response": {
        "status_code": 200,
        "data": {"results": [...]}
    },
    "duration": 0.5,
    "timestamp": 1698765432.0
}

# Web search tool execution
search_tool_exec: ToolExecution = {
    "tool": "search_web_tavily",
    "query": "latest AI developments",
    "provider": "tavily",
    "formatted_results": "1. Article about...\n2. Research on...",
    "duration": 1.2,
    "timestamp": 1698765433.0
}
```

---

### `ToolNodeMapping`

TypedDict mapping a tool to its node representation in the workflow graph.

**Purpose:** Enable proper tool execution tracking with correct node IDs and types.

**Fields:**

```python
class ToolNodeMapping(TypedDict, total=False):
    node_id: str           # Unique ID of the tool node
    node_name: str         # Display name of the tool node
    node_type: str         # Type of the tool node (NodeType enum value)
```

**Example:**

```python
from backend.services.subgraph import ToolNodeMapping

# Tool node mapping
mapping: ToolNodeMapping = {
    "node_id": "search-node-abc-123",
    "node_name": "Web Search",
    "node_type": "WEB_SEARCH"
}

# Tool mapping dictionary
tool_node_mapping = {
    "search_web_tavily": {
        "node_id": "search-node-123",
        "node_name": "Web Search (Tavily)",
        "node_type": "WEB_SEARCH"
    },
    "http_request": {
        "node_id": "http-node-456",
        "node_name": "API Call",
        "node_type": "HTTP_REQUEST"
    }
}
```

---

### `TokenCounts`

TypedDict for LLM token usage information.

**Purpose:** Track token consumption for cost analysis and rate limiting.

**Fields:**

```python
class TokenCounts(TypedDict, total=False):
    input_tokens: int      # Number of input tokens used
    output_tokens: int     # Number of output tokens generated
    total_tokens: int      # Total tokens used (input + output)
```

**Example:**

```python
from backend.services.subgraph import TokenCounts

# Token usage from LLM execution
token_counts: TokenCounts = {
    "input_tokens": 150,
    "output_tokens": 85,
    "total_tokens": 235
}
```

---

## Functions

### `create_subagent_graph()`

Convenience function that creates a subgraph for a delegated agent. Provided for backward compatibility.

**Signature:**

```python
def create_subagent_graph(
    agent_node: EnhancedNodeData,
    graph_manager: Any,
) -> StateGraph:
    """
    Create a subgraph for a delegated agent.

    This is a convenience function that creates a SubgraphBuilder
    and returns a compiled subgraph.
    """
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - The agent node to create a subgraph for
- `graph_manager` (Any) - The GraphManager instance

**Returns:**

- `StateGraph` - Compiled StateGraph ready for execution

**Example:**

```python
from backend.services.subgraph import create_subagent_graph

# Simple usage without explicit builder
subgraph = create_subagent_graph(agent_node, graph_manager)

# Equivalent to:
# builder = SubgraphBuilder(graph_manager)
# subgraph = builder.create_subagent_graph(agent_node)
```

**Use Cases:**

- Quick subgraph creation without managing builder instances
- Legacy code compatibility
- Simple use cases without caching needs

---

## Configuration

### Initialisation Patterns

#### Basic Initialisation

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

# Assume you have a graph_manager instance
# graph_manager = get_graph_manager()

# Create builder
builder = SubgraphBuilder(graph_manager)

# Create executor
executor = SubgraphExecutor(builder)

# Now ready to create and execute subgraphs
```

#### Using the Convenience Function

```python
from backend.services.subgraph import create_subagent_graph

# Direct creation without managing builder
subgraph = create_subagent_graph(agent_node, graph_manager)
result = await subgraph.ainvoke(initial_state)
```

#### Complete Setup with Caching

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

# Create shared builder instance (reuse across multiple executions)
builder = SubgraphBuilder(graph_manager)

# Create executor
executor = SubgraphExecutor(builder)

# Execute multiple sub-agents (cache will be used)
result1 = await executor.execute_subagent(agent1, task1, parent_state)
result2 = await executor.execute_subagent(agent2, task2, parent_state)
result3 = await executor.execute_subagent(agent1, task3, parent_state)  # Cache hit!

# Clear cache when workflow definitions change
builder.clear_cache()
```

#### With Checkpointer for State Persistence

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Create checkpointer
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

# Create subgraph with checkpointer
subgraph = builder.create_subagent_graph(
    agent_node,
    checkpointer=checkpointer
)

# State will be persisted and can be resumed
```

---

## Error Handling

### Exception Hierarchy

The subgraph module does not define custom exceptions. It relies on:

- Standard Python exceptions (TypeError, ValueError, AttributeError, etc.)
- LangGraph exceptions
- Exceptions from dependent services (ExecutionHistoryService, WebSocket notifier, etc.)

**Error Handling Strategy:**

- Catch exceptions at execution handler level
- Log errors with full stack traces
- Return errors in state dictionaries rather than raising
- Mark database records as failed
- Send error notifications via WebSocket

### Error Handling Patterns

#### Agent Execution Error Handling

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

builder = SubgraphBuilder(graph_manager)
executor = SubgraphExecutor(builder)

try:
    result = await executor.execute_subagent(
        agent_node=agent_node,
        task="Analyse data",
        parent_state=parent_state
    )

    # Check for execution errors
    if result.get("subagent_error"):
        logger.error(f"Sub-agent failed: {result['subagent_error']}")
        # Handle error appropriately
        return {"error": result["subagent_error"]}

    # Process successful result
    response = result["subagent_response"]
    return {"success": True, "response": response}

except Exception as e:
    # Unexpected error outside subgraph execution
    logger.error(f"Unexpected error: {e}", exc_info=True)
    return {"error": str(e)}
```

#### Internal Error Handling in Execution Handler

The execution handlers (agent/execution_handler.py, workflow/execution_handler.py) follow this pattern:

```python
async def execute_agent_in_subgraph(state, agent_node, graph_manager):
    """Execute agent with comprehensive error handling."""

    start_time = datetime.now(timezone.utc)
    execution_order = state["execution_order"]

    # Create database record
    node_exec_id = await create_agent_execution_record(...)

    # Send start notification
    await send_node_start_notification(...)

    try:
        # Execute the agent
        result = await graph_manager.execute_agent_async(...)

        # Process result
        response_content, token_counts, tool_executions = process_result(result)

        # Complete database record
        await complete_agent_execution_record(...)

        # Send completion notification
        await send_node_complete_notification(...)

        # Return success state
        return {
            "response": response_content,
            "tool_executions": tool_executions,
            "execution_order": updated_order,
            "error": None
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)

        # Mark as failed in database
        await fail_agent_execution_record(node_exec_id, agent_node, str(e))

        # Send error notification
        await send_node_error_notification(...)

        # Return error state (not raising)
        return {
            "error": str(e),
            "execution_order": execution_order,
            "end_time": datetime.now(timezone.utc).isoformat()
        }
```

#### Database Operation Error Handling

```python
from backend.services.subgraph.agent.database_tracker import (
    create_agent_execution_record,
    complete_agent_execution_record
)

# Database operations handle their own errors
node_exec_id = await create_agent_execution_record(
    agent_node=agent_node,
    parent_db_execution_id=parent_db_execution_id,
    parent_node_id=parent_node_id,
    execution_order=execution_order,
    task_description=task
)

# node_exec_id will be None if database operation failed
if not node_exec_id:
    logger.warning("Failed to create database record, continuing without tracking")
    # Execution continues even if DB tracking fails
```

#### Tool Tracking Error Handling

```python
from backend.services.subgraph.agent.tool_tracker import track_tool_executions

# Tool tracking handles individual tool errors
updated_order = await track_tool_executions(
    tool_execution_tracker=tool_executions,
    agent_node=agent_node,
    parent_db_execution_id=parent_db_execution_id,
    parent_execution_id=parent_execution_id,
    execution_order=execution_order,
    tool_node_mapping=tool_node_mapping,
    graph_name=graph_name,
    graph_manager=graph_manager
)

# Individual tool tracking failures are logged but don't stop execution
# Updated execution order is always returned
```

---

## Integration Patterns

### Integration with API Layer

The subgraph service is primarily used internally by the graph execution system rather than directly by API endpoints.
However, here's how it integrates:

```python
# In backend/api/graph/routes.py or execution handler

from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor
from backend.graph_manager import get_graph_manager

@router.post("/execute")
async def execute_workflow(
    graph_name: str,
    input_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """Execute a workflow that may contain sub-agents."""

    # Get graph manager
    graph_manager = get_graph_manager()

    # Create subgraph builder (typically done once per server lifecycle)
    builder = SubgraphBuilder(graph_manager)

    # The graph execution will automatically use subgraphs for agent delegation
    # This happens transparently within the graph manager

    result = await graph_manager.execute_graph(
        graph_name=graph_name,
        initial_input=input_data,
        user_id=current_user["id"]
    )

    return {"success": True, "result": result}
```

### Integration with Graph Manager

The primary integration is with the GraphManager, which uses the subgraph service for agent delegation:

```python
# In backend/graph_manager.py or backend/async_graph_manager.py

from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

class AsyncGraphManager:
    """Graph manager that supports sub-agent delegation."""

    def __init__(self):
        self.subgraph_builder = SubgraphBuilder(self)
        self.subgraph_executor = SubgraphExecutor(self.subgraph_builder)

    async def execute_agent_node(
        self,
        agent_node: EnhancedNodeData,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an agent node, which may be a sub-agent."""

        # Check if this is a delegated agent (orchestrator calling sub-agent)
        if state.get("is_delegated_task"):
            # Use subgraph executor for sub-agent
            result = await self.subgraph_executor.execute_subagent(
                agent_node=agent_node,
                task=state.get("task_description"),
                parent_state=state
            )

            # Merge result back into parent state
            state["execution_order"] = result["execution_order"]
            if result.get("subagent_error"):
                state["error"] = result["subagent_error"]
            else:
                state["response"] = result["subagent_response"]
                state["tool_executions"].extend(result["tool_executions"])

            return state
        else:
            # Regular agent execution
            return await self.execute_agent_async(agent_node, state)
```

### Integration with Execution Service

The subgraph service integrates with the execution history service for database tracking:

```python
from backend.services.execution.history import ExecutionHistoryService
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

# Subgraph execution automatically creates execution records
builder = SubgraphBuilder(graph_manager)
executor = SubgraphExecutor(builder)

# Execute sub-agent (creates database records automatically)
result = await executor.execute_subagent(
    agent_node=agent_node,
    task="Analyse sentiment",
    parent_state={
        "execution_id": "exec-123",
        "db_execution_id": "db-456",  # Parent execution record
        "current_node": "orchestrator",
        "execution_order": 5,
        "graph_name": "customer-insights"
    }
)

# Database records are created:
# 1. Sub-agent node execution (is_sub_agent=True, parent_agent_id=orchestrator)
# 2. Tool node executions (parent_agent_id=sub-agent-id)
# All linked to the parent db_execution_id

# Retrieve execution history
execution_data = ExecutionHistoryService.get_node_execution_by_id(
    result.get("node_execution_id")
)
```

### Integration with WebSocket Notifications

```python
# The subgraph service automatically sends WebSocket notifications
# No additional code needed in your application

from backend.services.subgraph import SubgraphExecutor

executor = SubgraphExecutor(builder)

# Execute sub-agent
# WebSocket notifications are sent automatically:
# 1. node_start when sub-agent begins
# 2. node_complete/node_error when sub-agent finishes
# 3. tool notifications for each tool execution

result = await executor.execute_subagent(
    agent_node=agent_node,
    task="Process request",
    parent_state=parent_state
)

# Frontend receives notifications in real-time:
# {
#   "type": "node_start",
#   "execution_id": "exec-123",
#   "node_id": "sub-agent-id",
#   "node_name": "Data Processor",
#   "is_sub_agent": true,
#   "parent_agent_id": "orchestrator-id"
# }
#
# {
#   "type": "node_complete",
#   "execution_id": "exec-123",
#   "node_id": "sub-agent-id",
#   "output": {"response": "Processed 150 records"},
#   "duration_seconds": 2.5,
#   "token_counts": {...}
# }
```

### Dependency Flow

```
Frontend (WebSocket client)
    ↓
API Layer (routes.py)
    ↓
Graph Manager (async_graph_manager.py)
    ↓
Subgraph Service (SubgraphBuilder, SubgraphExecutor)
    ↓ ↓ ↓
    ├─→ Agent Execution (execute_agent_async)
    ├─→ Database Service (ExecutionHistoryService)
    └─→ WebSocket Notifier (send notifications)
```

**Data flow:**

1. API receives workflow execution request
2. Graph Manager starts workflow execution
3. When encountering agent delegation, Graph Manager uses SubgraphExecutor
4. SubgraphExecutor prepares state and invokes subgraph
5. Subgraph execution handler tracks progress in database
6. WebSocket notifications keep frontend updated
7. Results flow back up through SubgraphExecutor to parent state

### Common Integration Patterns

#### Pattern 1: Simple Agent Delegation

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

# Setup (typically once at application startup)
builder = SubgraphBuilder(graph_manager)
executor = SubgraphExecutor(builder)

# In workflow execution
async def orchestrator_agent_logic(state):
    """Orchestrator delegates to specialists."""

    # Identify need for delegation
    if "analyse sentiment" in state["task"].lower():
        # Delegate to sentiment analysis agent
        sentiment_agent = graph_manager.get_node(
            "customer-insights",
            "sentiment-agent-id"
        )

        result = await executor.execute_subagent(
            agent_node=sentiment_agent,
            task="Analyse sentiment in customer feedback",
            parent_state=state
        )

        # Use sub-agent's response
        sentiment_analysis = result.get("subagent_response")
        return {"sentiment": sentiment_analysis}

    # Handle other delegation scenarios
    # ...
```

#### Pattern 2: Parallel Sub-Agent Execution

```python
import asyncio
from backend.services.subgraph import SubgraphExecutor

async def parallel_delegation(state, executor):
    """Execute multiple sub-agents in parallel."""

    # Get agent nodes
    data_agent = graph_manager.get_node("workflow", "data-agent")
    analysis_agent = graph_manager.get_node("workflow", "analysis-agent")
    summary_agent = graph_manager.get_node("workflow", "summary-agent")

    # Execute in parallel
    results = await asyncio.gather(
        executor.execute_subagent(data_agent, "Fetch data", state),
        executor.execute_subagent(analysis_agent, "Analyse trends", state),
        executor.execute_subagent(summary_agent, "Create summary", state),
        return_exceptions=True
    )

    # Process results
    data_result, analysis_result, summary_result = results

    # Combine responses
    combined_response = {
        "data": data_result.get("subagent_response"),
        "analysis": analysis_result.get("subagent_response"),
        "summary": summary_result.get("subagent_response")
    }

    return combined_response
```

#### Pattern 3: Sub-Workflow Execution from Agent

```python
from backend.services.subgraph import SubgraphBuilder

async def agent_invokes_workflow(agent_state):
    """Agent invokes a sub-workflow for structured processing."""

    # Get subworkflow node
    subworkflow_node = graph_manager.get_node(
        "parent-graph",
        "data-processing-workflow"
    )

    # Create workflow subgraph
    builder = SubgraphBuilder(graph_manager)
    workflow_subgraph = builder.create_subworkflow_graph(
        subworkflow_node,
        graph_name="parent-graph"
    )

    # Prepare workflow state
    workflow_state = {
        "task_description": "Process customer data",
        "workflow_input": {"customer_id": "CUST-123"},
        "parent_execution_id": agent_state["execution_id"],
        "parent_db_execution_id": agent_state["db_execution_id"],
        "parent_node_id": agent_state["agent_node_id"],
        "parent_node_name": agent_state["agent_node_name"],
        "execution_order": agent_state["execution_order"],
        "workflow_node_id": subworkflow_node.uniq_id,
        "workflow_node_name": subworkflow_node.name,
        "workflow_config": None,
        "graph_name": "parent-graph",
        "workflow_output": None,
        "nodes_executed": [],
        "structured_output": None,
        "error": None,
        "response": None,
        "messages": [],
        "metadata": {}
    }

    # Execute workflow
    result = await workflow_subgraph.ainvoke(workflow_state)

    # Use workflow output
    return {
        "workflow_output": result["workflow_output"],
        "nodes_executed": result["nodes_executed"]
    }
```

---

## Usage Examples

### Example 1: Basic Sub-Agent Execution

Complete end-to-end example of executing a sub-agent:

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor
from backend.models.workflow import EnhancedNodeData
from backend.graph_manager import get_graph_manager

async def basic_subagent_example():
    """Execute a sub-agent for task delegation."""

    # Step 1: Get graph manager
    graph_manager = get_graph_manager()

    # Step 2: Create builder and executor
    builder = SubgraphBuilder(graph_manager)
    executor = SubgraphExecutor(builder)

    # Step 3: Get the sub-agent node
    agent_node = graph_manager.get_node(
        graph_name="customer-support",
        node_id="sentiment-analyser-agent"
    )

    # Step 4: Prepare parent state
    parent_state = {
        "execution_id": "exec-20251027-abc123",
        "db_execution_id": "456",
        "current_node": "orchestrator-node-id",
        "execution_order": 3,
        "graph_name": "customer-support",
        "tool_node_mapping": {
            "search_reviews": "review-search-node-id",
            "database_query": "db-query-node-id"
        },
        "metadata": {
            "current_node_name": "Support Orchestrator"
        }
    }

    # Step 5: Execute the sub-agent
    result = await executor.execute_subagent(
        agent_node=agent_node,
        task="Analyse sentiment from the customer feedback: 'The product is excellent but delivery was slow.'",
        parent_state=parent_state
    )

    # Step 6: Process the result
    if result.get("subagent_error"):
        print(f"❌ Sub-agent failed: {result['subagent_error']}")
        return {"error": result["subagent_error"]}

    print(f"✅ Sub-agent completed successfully")
    print(f"📝 Response: {result['subagent_response']}")
    print(f"🔧 Tools used: {len(result['tool_executions'])}")
    print(f"📊 New execution order: {result['execution_order']}")

    # Step 7: Use the response
    return {
        "sentiment": result["subagent_response"],
        "execution_order": result["execution_order"],
        "tools_used": [t["tool"] for t in result["tool_executions"]]
    }
```

### Example 2: Orchestrator Pattern with Multiple Sub-Agents

Complete example showing an orchestrator coordinating multiple specialist agents:

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor
import asyncio

async def orchestrator_pattern_example():
    """Orchestrator agent delegates to multiple specialist agents."""

    # Setup
    graph_manager = get_graph_manager()
    builder = SubgraphBuilder(graph_manager)
    executor = SubgraphExecutor(builder)

    # Parent state from orchestrator agent
    parent_state = {
        "execution_id": "exec-orchestrator-001",
        "db_execution_id": "789",
        "current_node": "orchestrator-agent",
        "execution_order": 1,
        "graph_name": "customer-insights-workflow",
        "tool_node_mapping": {},
        "metadata": {"current_node_name": "Insights Orchestrator"}
    }

    # Get specialist agent nodes
    sentiment_agent = graph_manager.get_node(
        "customer-insights-workflow",
        "sentiment-agent-id"
    )

    trend_agent = graph_manager.get_node(
        "customer-insights-workflow",
        "trend-agent-id"
    )

    recommendation_agent = graph_manager.get_node(
        "customer-insights-workflow",
        "recommendation-agent-id"
    )

    # Execute agents in sequence (each depends on previous)

    # Step 1: Sentiment analysis
    print("Step 1: Analysing sentiment...")
    sentiment_result = await executor.execute_subagent(
        agent_node=sentiment_agent,
        task="Analyse overall customer sentiment from the last 100 reviews",
        parent_state=parent_state
    )

    if sentiment_result.get("subagent_error"):
        return {"error": f"Sentiment analysis failed: {sentiment_result['subagent_error']}"}

    sentiment_analysis = sentiment_result["subagent_response"]
    parent_state["execution_order"] = sentiment_result["execution_order"]

    # Step 2: Trend analysis
    print("Step 2: Analysing trends...")
    trend_result = await executor.execute_subagent(
        agent_node=trend_agent,
        task=f"Given this sentiment analysis: {sentiment_analysis}, identify key trends and patterns",
        parent_state=parent_state
    )

    if trend_result.get("subagent_error"):
        return {"error": f"Trend analysis failed: {trend_result['subagent_error']}"}

    trend_analysis = trend_result["subagent_response"]
    parent_state["execution_order"] = trend_result["execution_order"]

    # Step 3: Generate recommendations
    print("Step 3: Generating recommendations...")
    recommendation_result = await executor.execute_subagent(
        agent_node=recommendation_agent,
        task=f"Based on sentiment: {sentiment_analysis} and trends: {trend_analysis}, provide actionable recommendations",
        parent_state=parent_state
    )

    if recommendation_result.get("subagent_error"):
        return {"error": f"Recommendation generation failed: {recommendation_result['subagent_error']}"}

    recommendations = recommendation_result["subagent_response"]

    # Combine all insights
    return {
        "sentiment": sentiment_analysis,
        "trends": trend_analysis,
        "recommendations": recommendations,
        "final_execution_order": recommendation_result["execution_order"],
        "total_tools_used": (
            len(sentiment_result["tool_executions"]) +
            len(trend_result["tool_executions"]) +
            len(recommendation_result["tool_executions"])
        )
    }
```

### Example 3: Parallel Sub-Agent Execution

Execute multiple independent sub-agents in parallel:

```python
import asyncio
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

async def parallel_subagent_example():
    """Execute multiple sub-agents in parallel for faster processing."""

    # Setup
    graph_manager = get_graph_manager()
    builder = SubgraphBuilder(graph_manager)
    executor = SubgraphExecutor(builder)

    # Parent state
    parent_state = {
        "execution_id": "exec-parallel-001",
        "db_execution_id": "999",
        "current_node": "parallel-orchestrator",
        "execution_order": 5,
        "graph_name": "multi-source-analysis",
        "tool_node_mapping": {},
        "metadata": {"current_node_name": "Parallel Orchestrator"}
    }

    # Get agent nodes
    social_media_agent = graph_manager.get_node("multi-source-analysis", "social-agent")
    news_agent = graph_manager.get_node("multi-source-analysis", "news-agent")
    review_agent = graph_manager.get_node("multi-source-analysis", "review-agent")

    # Execute all agents in parallel
    print("🚀 Starting parallel execution of 3 agents...")

    results = await asyncio.gather(
        executor.execute_subagent(
            agent_node=social_media_agent,
            task="Analyse social media sentiment about Product X",
            parent_state=parent_state
        ),
        executor.execute_subagent(
            agent_node=news_agent,
            task="Find recent news articles about Product X",
            parent_state=parent_state
        ),
        executor.execute_subagent(
            agent_node=review_agent,
            task="Summarise customer reviews for Product X",
            parent_state=parent_state
        ),
        return_exceptions=True  # Don't fail all if one fails
    )

    # Process results
    social_result, news_result, review_result = results

    # Check for errors
    errors = []
    if isinstance(social_result, Exception) or social_result.get("subagent_error"):
        errors.append(f"Social media analysis: {social_result.get('subagent_error', str(social_result))}")

    if isinstance(news_result, Exception) or news_result.get("subagent_error"):
        errors.append(f"News analysis: {news_result.get('subagent_error', str(news_result))}")

    if isinstance(review_result, Exception) or review_result.get("subagent_error"):
        errors.append(f"Review analysis: {review_result.get('subagent_error', str(review_result))}")

    # Combine successful results
    combined_insights = {
        "social_media": social_result.get("subagent_response") if not isinstance(social_result, Exception) else None,
        "news": news_result.get("subagent_response") if not isinstance(news_result, Exception) else None,
        "reviews": review_result.get("subagent_response") if not isinstance(review_result, Exception) else None,
        "errors": errors if errors else None,
        "execution_orders": [
            r.get("execution_order") for r in results
            if not isinstance(r, Exception) and r.get("execution_order")
        ]
    }

    print(f"✅ Parallel execution completed")
    print(f"📊 Successful: {3 - len(errors)}/3")

    return combined_insights
```

### Example 4: Sub-Workflow Execution

Execute a nested workflow from an agent:

```python
from backend.services.subgraph import SubgraphBuilder
from langchain_core.messages import HumanMessage

async def subworkflow_example():
    """Agent invokes a sub-workflow for structured multi-step processing."""

    # Setup
    graph_manager = get_graph_manager()
    builder = SubgraphBuilder(graph_manager)

    # Get the subworkflow node
    subworkflow_node = graph_manager.get_node(
        "order-processing",
        "payment-workflow-id"
    )

    # Parent state from calling agent
    parent_state = {
        "execution_id": "exec-order-123",
        "db_execution_id": "321",
        "current_node": "order-agent-id",
        "execution_order": 7
    }

    # Create subworkflow graph
    workflow_subgraph = builder.create_subworkflow_graph(
        subworkflow_node,
        graph_name="order-processing"
    )

    # Prepare subworkflow state
    workflow_state = {
        "task_description": "Process payment for order ORD-12345",
        "workflow_input": {
            "order_id": "ORD-12345",
            "amount": 99.99,
            "payment_method": "credit_card"
        },
        "parent_execution_id": parent_state["execution_id"],
        "parent_db_execution_id": parent_state["db_execution_id"],
        "parent_node_id": parent_state["current_node"],
        "parent_node_name": "Order Processing Agent",
        "execution_order": parent_state["execution_order"],
        "start_time": None,
        "end_time": None,
        "workflow_node_id": subworkflow_node.uniq_id,
        "workflow_node_name": "Payment Processing Workflow",
        "workflow_config": None,
        "graph_name": "order-processing",
        "workflow_output": None,
        "nodes_executed": [],
        "structured_output": None,
        "error": None,
        "response": None,
        "messages": [HumanMessage(content="Process payment for ORD-12345")],
        "metadata": {}
    }

    # Execute the subworkflow
    print("💳 Starting payment workflow...")
    result = await workflow_subgraph.ainvoke(workflow_state)

    # Check result
    if result.get("error"):
        print(f"❌ Payment workflow failed: {result['error']}")
        return {"payment_status": "failed", "error": result["error"]}

    print(f"✅ Payment workflow completed")
    print(f"📝 Output: {result['workflow_output']}")
    print(f"🔄 Nodes executed: {', '.join(result['nodes_executed'])}")

    return {
        "payment_status": "success",
        "workflow_output": result["workflow_output"],
        "nodes_executed": result["nodes_executed"],
        "execution_order": result["execution_order"]
    }
```

### Example 5: Caching and Performance Optimisation

Demonstrate cache usage for performance:

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor
import time

async def caching_example():
    """Demonstrate subgraph caching for performance optimisation."""

    # Setup
    graph_manager = get_graph_manager()
    builder = SubgraphBuilder(graph_manager)
    executor = SubgraphExecutor(builder)

    # Get agent node
    agent_node = graph_manager.get_node("workflows", "data-processor")

    # Check if cached
    print(f"Cache size before: {builder._cache.size()}")
    is_cached = builder._cache.has(agent_node, prefix="agent_")
    print(f"Agent subgraph cached: {is_cached}")

    # First execution - will compile and cache
    print("\n🔨 First execution (will compile)...")
    start = time.time()

    parent_state = {
        "execution_id": "exec-cache-001",
        "db_execution_id": "111",
        "current_node": "orchestrator",
        "execution_order": 1,
        "graph_name": "workflows",
        "tool_node_mapping": {},
        "metadata": {"current_node_name": "Orchestrator"}
    }

    result1 = await executor.execute_subagent(
        agent_node=agent_node,
        task="Process dataset 1",
        parent_state=parent_state
    )

    first_duration = time.time() - start
    print(f"⏱️  First execution took: {first_duration:.3f}s")
    print(f"📦 Cache size after: {builder._cache.size()}")

    # Second execution - will use cached subgraph
    print("\n⚡ Second execution (will use cache)...")
    start = time.time()

    parent_state["execution_order"] = result1["execution_order"]

    result2 = await executor.execute_subagent(
        agent_node=agent_node,
        task="Process dataset 2",
        parent_state=parent_state
    )

    second_duration = time.time() - start
    print(f"⏱️  Second execution took: {second_duration:.3f}s")

    # Calculate improvement
    improvement = ((first_duration - second_duration) / first_duration) * 100
    print(f"\n📈 Performance improvement: {improvement:.1f}% faster")

    # Clear cache
    print("\n🧹 Clearing cache...")
    builder.clear_cache()
    print(f"📦 Cache size after clear: {builder._cache.size()}")

    return {
        "first_execution_time": first_duration,
        "second_execution_time": second_duration,
        "improvement_percentage": improvement
    }
```

---

## Performance Considerations

### Performance Characteristics

**Subgraph Creation (Builder):**

- **First creation:** O(n) where n is the complexity of the subgraph (number of nodes and edges)
- **Cached retrieval:** O(1) dictionary lookup
- **Memory:** Each cached subgraph consumes memory proportional to its compiled graph size

**Subgraph Execution (Executor):**

- **State preparation:** O(1) - simple dictionary creation
- **Execution:** O(m) where m is the execution time of the agent or workflow
- **Result extraction:** O(1) - extracting specific fields from result state

**Caching:**

- **Lookup:** O(1) - dictionary-based cache
- **Storage:** O(k) where k is the number of unique subgraphs
- **Memory overhead:** Minimal - only stores compiled graphs, not execution state

**I/O Characteristics:**

- **Network-bound:** WebSocket notifications (non-blocking)
- **Database I/O:** Creating and updating execution records (async)
- **CPU-bound:** LLM inference within sub-agents (delegated to LLM service)

### Optimisation Tips

#### Tip 1: Reuse Builder and Executor Instances

**Problem:**

```python
# Inefficient - creates new builder/executor for each execution
async def execute_many_subagents(agents, tasks, state):
    results = []
    for agent, task in zip(agents, tasks):
        builder = SubgraphBuilder(graph_manager)  # ❌ New builder each time
        executor = SubgraphExecutor(builder)      # ❌ New executor each time
        result = await executor.execute_subagent(agent, task, state)
        results.append(result)
    return results
```

**Solution:**

```python
# Efficient - reuse builder and executor (cache is shared)
async def execute_many_subagents(agents, tasks, state):
    builder = SubgraphBuilder(graph_manager)      # ✅ Create once
    executor = SubgraphExecutor(builder)          # ✅ Create once

    results = []
    for agent, task in zip(agents, tasks):
        result = await executor.execute_subagent(agent, task, state)
        results.append(result)

    return results
```

**Benefit:** Cache is shared across all executions, reducing compilation overhead.

#### Tip 2: Use Parallel Execution for Independent Sub-Agents

**Problem:**

```python
# Sequential execution - slow
result1 = await executor.execute_subagent(agent1, task1, state)
result2 = await executor.execute_subagent(agent2, task2, state)
result3 = await executor.execute_subagent(agent3, task3, state)
# Total time = time1 + time2 + time3
```

**Solution:**

```python
# Parallel execution - fast
import asyncio

results = await asyncio.gather(
    executor.execute_subagent(agent1, task1, state),
    executor.execute_subagent(agent2, task2, state),
    executor.execute_subagent(agent3, task3, state)
)
# Total time ≈ max(time1, time2, time3)
```

**Benefit:** Reduces total execution time when sub-agents are independent.

#### Tip 3: Clear Cache Only When Necessary

**Problem:**

```python
# Clearing cache too frequently
for agent in agents:
    builder.clear_cache()  # ❌ Unnecessary - forces recompilation
    result = await executor.execute_subagent(agent, task, state)
```

**Solution:**

```python
# Clear cache only when workflow definitions change
# Most executions use cached subgraphs
for agent in agents:
    result = await executor.execute_subagent(agent, task, state)

# Clear cache only after workflow update
if workflow_definitions_changed:
    builder.clear_cache()  # ✅ Only when needed
```

**Benefit:** Maximises cache hit rate, avoiding redundant compilation.

#### Tip 4: Minimise State Size

**Problem:**

```python
# Large parent state with unnecessary data
parent_state = {
    "execution_id": "exec-123",
    "db_execution_id": "456",
    "current_node": "orchestrator",
    "execution_order": 5,
    "graph_name": "workflow",
    "tool_node_mapping": {},
    "metadata": {"current_node_name": "Orchestrator"},
    "large_dataset": [...],  # ❌ Unnecessary large data
    "historical_data": {...},  # ❌ Not needed by subgraph
    "cached_results": [...]  # ❌ Not used
}
```

**Solution:**

```python
# Lean parent state with only required fields
parent_state = {
    "execution_id": "exec-123",
    "db_execution_id": "456",
    "current_node": "orchestrator",
    "execution_order": 5,
    "graph_name": "workflow",
    "tool_node_mapping": {},
    "metadata": {"current_node_name": "Orchestrator"}
}
# Store large data elsewhere and pass only references
```

**Benefit:** Reduces memory usage and state copying overhead.

### Async/Await Support

The subgraph service is fully async-native:

**Async Execution:**

```python
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor

# All execution methods are async
async def async_example():
    builder = SubgraphBuilder(graph_manager)
    executor = SubgraphExecutor(builder)

    # Async execution
    result = await executor.execute_subagent(
        agent_node=agent,
        task="Process data",
        parent_state=state
    )

    return result

# Async subgraph invocation
async def direct_subgraph_invocation():
    builder = SubgraphBuilder(graph_manager)
    subgraph = builder.create_subagent_graph(agent_node)

    # Use ainvoke for async execution
    result = await subgraph.ainvoke(initial_state)

    return result
```

**Concurrent Execution:**

```python
import asyncio

async def concurrent_subagents():
    """Execute multiple sub-agents concurrently."""

    executor = SubgraphExecutor(builder)

    # All execute concurrently
    tasks = [
        executor.execute_subagent(agent1, task1, state),
        executor.execute_subagent(agent2, task2, state),
        executor.execute_subagent(agent3, task3, state)
    ]

    results = await asyncio.gather(*tasks)
    return results
```

**Benefits of Async:**

- Non-blocking I/O for database and WebSocket operations
- Efficient concurrent execution
- No threading overhead
- Natural integration with FastAPI and LangGraph

### Connection Pooling

The subgraph service does not directly manage connections. Connection pooling is handled by:

**Database Connections:**

- Managed by ExecutionHistoryService
- Uses SQLAlchemy connection pooling
- Configured at application level

**WebSocket Connections:**

- Managed by WebSocket notifier service
- Connection maintained by WebSocket server
- Subgraph service only sends messages

**No explicit configuration needed** in subgraph service code.

### Batch Operations

The subgraph service supports batch operations through parallel execution:

**Batch Sub-Agent Execution:**

```python
import asyncio

async def batch_execute_subagents(agent_tasks, executor, state):
    """
    Execute multiple sub-agents in batch.

    Args:
        agent_tasks: List of (agent_node, task) tuples
        executor: SubgraphExecutor instance
        state: Parent state

    Returns:
        List of results
    """

    # Create tasks
    tasks = [
        executor.execute_subagent(
            agent_node=agent,
            task=task,
            parent_state=state
        )
        for agent, task in agent_tasks
    ]

    # Execute all in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter successes and failures
    successes = [r for r in results if not isinstance(r, Exception) and not r.get("subagent_error")]
    failures = [r for r in results if isinstance(r, Exception) or r.get("subagent_error")]

    return {
        "successes": successes,
        "failures": failures,
        "total": len(results),
        "success_rate": len(successes) / len(results) if results else 0
    }
```

**Benefits:**

- Process multiple sub-agents concurrently
- Automatic error isolation (return_exceptions=True)
- Improved throughput

---

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor
from backend.models.workflow import EnhancedNodeData, NodeType

@pytest.fixture
def mock_graph_manager():
    """Mock GraphManager for testing."""
    manager = Mock()
    manager.execute_agent_async = AsyncMock(return_value="Agent response")
    manager.get_node = Mock(return_value=Mock(
        uniq_id="agent-123",
        name="Test Agent",
        type=NodeType.AGENT
    ))
    return manager

@pytest.fixture
def agent_node():
    """Sample agent node for testing."""
    node = Mock(spec=EnhancedNodeData)
    node.uniq_id = "agent-123"
    node.name = "Test Agent"
    node.type = NodeType.AGENT
    node.agent_config = Mock(temperature=0.7)
    return node

@pytest.fixture
def builder(mock_graph_manager):
    """SubgraphBuilder fixture."""
    return SubgraphBuilder(mock_graph_manager)

@pytest.fixture
def executor(builder):
    """SubgraphExecutor fixture."""
    return SubgraphExecutor(builder)

def test_builder_creation(mock_graph_manager):
    """Test SubgraphBuilder initialisation."""
    builder = SubgraphBuilder(mock_graph_manager)
    assert builder.graph_manager == mock_graph_manager
    assert builder._cache is not None
    assert builder._cache.size() == 0

def test_create_subagent_graph(builder, agent_node):
    """Test agent subgraph creation."""
    subgraph = builder.create_subagent_graph(agent_node)

    assert subgraph is not None
    # Verify cache was populated
    assert builder._cache.has(agent_node, prefix="agent_")

def test_create_subagent_graph_uses_cache(builder, agent_node):
    """Test that subsequent calls use cache."""
    # First call - creates and caches
    subgraph1 = builder.create_subagent_graph(agent_node)

    # Second call - should use cache
    subgraph2 = builder.create_subagent_graph(agent_node)

    # Should return same instance
    assert subgraph1 is subgraph2

def test_clear_cache(builder, agent_node):
    """Test cache clearing."""
    # Create subgraph (populates cache)
    builder.create_subagent_graph(agent_node)
    assert builder._cache.size() == 1

    # Clear cache
    builder.clear_cache()
    assert builder._cache.size() == 0

@pytest.mark.asyncio
async def test_execute_subagent_success(executor, agent_node):
    """Test successful sub-agent execution."""
    parent_state = {
        "execution_id": "exec-123",
        "db_execution_id": "456",
        "current_node": "orchestrator",
        "execution_order": 5,
        "graph_name": "test-workflow",
        "tool_node_mapping": {},
        "metadata": {"current_node_name": "Orchestrator"}
    }

    result = await executor.execute_subagent(
        agent_node=agent_node,
        task="Test task",
        parent_state=parent_state
    )

    # Verify result structure
    assert "execution_order" in result
    assert "subagent_response" in result or "subagent_error" in result
    assert result["execution_order"] >= parent_state["execution_order"]
```

### Mocking Dependencies

```python
import pytest
from unittest.mock import patch, AsyncMock, Mock

@pytest.mark.asyncio
@patch('backend.services.subgraph.agent.execution_handler.ExecutionHistoryService')
@patch('backend.services.subgraph.agent.execution_handler.send_node_start_notification')
@patch('backend.services.subgraph.agent.execution_handler.send_node_complete_notification')
async def test_agent_execution_with_mocked_services(
    mock_send_complete,
    mock_send_start,
    mock_history_service,
    executor,
    agent_node
):
    """Test agent execution with mocked external services."""

    # Setup mocks
    mock_history_service.create_node_execution.return_value = {"id": 123}
    mock_history_service.start_node_execution.return_value = None
    mock_history_service.complete_node_execution.return_value = None
    mock_send_start.return_value = None
    mock_send_complete.return_value = None

    # Mock agent execution
    executor.subgraph_builder.graph_manager.execute_agent_async = AsyncMock(
        return_value=("Test response", {"input_tokens": 10, "output_tokens": 20})
    )

    # Execute
    parent_state = {
        "execution_id": "exec-test",
        "db_execution_id": "db-test",
        "current_node": "orch",
        "execution_order": 1,
        "graph_name": "test",
        "tool_node_mapping": {},
        "metadata": {"current_node_name": "Test"}
    }

    result = await executor.execute_subagent(
        agent_node=agent_node,
        task="Test task",
        parent_state=parent_state
    )

    # Verify mocks were called
    mock_send_start.assert_called_once()
    mock_send_complete.assert_called_once()
    mock_history_service.create_node_execution.assert_called_once()

    # Verify result
    assert result.get("subagent_response") is not None

@pytest.mark.asyncio
@patch('backend.services.subgraph.agent.execution_handler.ExecutionHistoryService')
async def test_agent_execution_error_handling(mock_history_service, executor, agent_node):
    """Test error handling in agent execution."""

    # Setup mocks
    mock_history_service.create_node_execution.return_value = {"id": 123}

    # Mock agent execution to raise error
    executor.subgraph_builder.graph_manager.execute_agent_async = AsyncMock(
        side_effect=Exception("Test error")
    )

    # Execute
    parent_state = {
        "execution_id": "exec-test",
        "db_execution_id": "db-test",
        "current_node": "orch",
        "execution_order": 1,
        "graph_name": "test",
        "tool_node_mapping": {},
        "metadata": {"current_node_name": "Test"}
    }

    result = await executor.execute_subagent(
        agent_node=agent_node,
        task="Test task",
        parent_state=parent_state
    )

    # Verify error is in result
    assert "subagent_error" in result
    assert "Test error" in result["subagent_error"]
```

### Integration Testing

```python
import pytest
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor
from backend.graph_manager import AsyncGraphManager
from backend.models.workflow import EnhancedNodeData, NodeType

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_subagent_execution_integration():
    """Integration test with real GraphManager and database."""

    # Use real graph manager (configured for test environment)
    graph_manager = AsyncGraphManager()

    # Create real builder and executor
    builder = SubgraphBuilder(graph_manager)
    executor = SubgraphExecutor(builder)

    # Use a test agent node from database
    agent_node = graph_manager.get_node("test-workflow", "test-agent-id")

    # Real parent state
    parent_state = {
        "execution_id": "integration-test-exec",
        "db_execution_id": None,  # No DB tracking in test
        "current_node": "test-orchestrator",
        "execution_order": 1,
        "graph_name": "test-workflow",
        "tool_node_mapping": {},
        "metadata": {"current_node_name": "Test Orchestrator"}
    }

    # Execute with real services
    result = await executor.execute_subagent(
        agent_node=agent_node,
        task="This is an integration test task",
        parent_state=parent_state
    )

    # Verify result
    assert "subagent_response" in result or "subagent_error" in result
    assert result["execution_order"] > parent_state["execution_order"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_subworkflow_execution_integration():
    """Integration test for sub-workflow execution."""

    graph_manager = AsyncGraphManager()
    builder = SubgraphBuilder(graph_manager)

    # Get real subworkflow node
    subworkflow_node = graph_manager.get_node(
        "test-workflow",
        "test-subworkflow-id"
    )

    # Create workflow subgraph
    workflow_subgraph = builder.create_subworkflow_graph(
        subworkflow_node,
        graph_name="test-workflow"
    )

    # Prepare state
    from langchain_core.messages import HumanMessage

    workflow_state = {
        "task_description": "Test workflow execution",
        "workflow_input": {},
        "parent_execution_id": "test-exec",
        "parent_db_execution_id": None,
        "parent_node_id": "test-parent",
        "parent_node_name": "Test Parent",
        "execution_order": 1,
        "start_time": None,
        "end_time": None,
        "workflow_node_id": subworkflow_node.uniq_id,
        "workflow_node_name": subworkflow_node.name,
        "workflow_config": None,
        "graph_name": "test-workflow",
        "workflow_output": None,
        "nodes_executed": [],
        "structured_output": None,
        "error": None,
        "response": None,
        "messages": [HumanMessage(content="Test")],
        "metadata": {}
    }

    # Execute workflow
    result = await workflow_subgraph.ainvoke(workflow_state)

    # Verify result
    assert "workflow_output" in result or "error" in result
    assert "nodes_executed" in result
```

---

## Best Practices

### Do's

✅ **Reuse builder and executor instances across executions**

```python
# Create once at application/request level
builder = SubgraphBuilder(graph_manager)
executor = SubgraphExecutor(builder)

# Reuse for multiple executions
for agent, task in agent_tasks:
    result = await executor.execute_subagent(agent, task, state)
```

**Reason:** Shares cache across executions, improving performance.

✅ **Use parallel execution for independent sub-agents**

```python
import asyncio

# Execute independent sub-agents in parallel
results = await asyncio.gather(
    executor.execute_subagent(agent1, task1, state),
    executor.execute_subagent(agent2, task2, state),
    executor.execute_subagent(agent3, task3, state)
)
```

**Reason:** Reduces total execution time significantly.

✅ **Always check for errors in results**

```python
result = await executor.execute_subagent(agent, task, state)

if result.get("subagent_error"):
    # Handle error appropriately
    logger.error(f"Sub-agent failed: {result['subagent_error']}")
    return handle_error(result["subagent_error"])

# Process successful result
response = result["subagent_response"]
```

**Reason:** Subgraph errors are returned in state, not raised as exceptions.

✅ **Pass lean parent state with only required fields**

```python
# Include only necessary fields
parent_state = {
    "execution_id": execution_id,
    "db_execution_id": db_id,
    "current_node": node_id,
    "execution_order": order,
    "graph_name": graph_name,
    "tool_node_mapping": tool_mapping,
    "metadata": {"current_node_name": node_name}
}
```

**Reason:** Reduces memory usage and state copying overhead.

✅ **Clear cache when workflow definitions change**

```python
# After updating workflow definition
workflow_updated = update_workflow_definition(graph_name, new_definition)

if workflow_updated:
    builder.clear_cache()  # Force recompilation with new definition
```

**Reason:** Ensures subgraphs use latest workflow configurations.

✅ **Use proper logging levels**

```python
from backend.services.config import get_logger

logger = get_logger("my_module.subgraph")

logger.debug("Cache hit for agent subgraph")  # Detailed info
logger.info("Executing sub-agent: CustomerAnalyser")  # Normal flow
logger.warning("No tool node mapping provided")  # Potential issues
logger.error("Agent execution failed", exc_info=True)  # Errors with stack trace
```

**Reason:** Proper logging aids debugging and monitoring.

### Don'ts

❌ **Don't create new builder/executor instances for each execution**

```python
# Inefficient - creates new builder each time
async def execute_agent(agent, task, state):
    builder = SubgraphBuilder(graph_manager)  # ❌ Bad
    executor = SubgraphExecutor(builder)      # ❌ Bad
    return await executor.execute_subagent(agent, task, state)
```

**Reason:** Loses caching benefits, forces recompilation every time.

❌ **Don't execute dependent sub-agents in parallel**

```python
# Wrong - agent2 depends on agent1's result
results = await asyncio.gather(
    executor.execute_subagent(agent1, task1, state),
    executor.execute_subagent(agent2, f"Use result from {agent1}", state)  # ❌ Wrong
)
```

**Reason:** Agent2 task references agent1's result which isn't available yet.

**Correct approach:**

```python
# Execute sequentially when there are dependencies
result1 = await executor.execute_subagent(agent1, task1, state)
task2 = f"Use this data: {result1['subagent_response']}"
result2 = await executor.execute_subagent(agent2, task2, state)
```

❌ **Don't ignore error handling**

```python
# Dangerous - assumes success
result = await executor.execute_subagent(agent, task, state)
response = result["subagent_response"]  # ❌ May not exist if error occurred
```

**Reason:** Will raise KeyError if execution failed.

❌ **Don't pass large datasets in parent state**

```python
# Inefficient - large data in state
parent_state = {
    # ... required fields ...
    "large_dataset": [... 10MB of data ...],  # ❌ Bad
    "all_historical_records": {...}  # ❌ Bad
}
```

**Reason:** Increases memory usage and state copying overhead.

**Better approach:**

```python
# Pass only references
parent_state = {
    # ... required fields ...
    "dataset_id": "dataset-123",  # ✅ Good - reference only
}
# Sub-agent fetches data by ID when needed
```

❌ **Don't clear cache unnecessarily**

```python
# Wasteful - clears cache after every execution
result = await executor.execute_subagent(agent, task, state)
builder.clear_cache()  # ❌ Wasteful
```

**Reason:** Forces recompilation on next execution, negating caching benefits.

❌ **Don't modify subgraph state after creation**

```python
# Dangerous - modifying state directly
subgraph = builder.create_subagent_graph(agent_node)
subgraph.nodes["execute_agent"] = modified_node  # ❌ Don't do this
```

**Reason:** Breaks caching assumptions and may cause unexpected behaviour.

---

## Related Documentation

### Related Services

- [Execution Service](./execution.md) - Workflow execution coordination and history tracking
- [Agent Service](./agent.md) - Agent compilation and configuration
- [Graph Service](../agents-guide/api/graph.md) - Workflow graph management API
- [Database Service](./database.md) - Database operations and migrations
- [WebSocket Service](./websocket.md) - Real-time WebSocket notifications

### Related API Modules

- [Graph API](../agents-guide/api/graph.md) - Workflow management endpoints
- [Execution API](../agents-guide/api/execution.md) - Workflow execution endpoints

### Architecture Documentation

- [Async Execution Architecture](../architecture/async_execution.md) - Overview of async execution patterns
- [LangGraph Integration](../architecture/langgraph.md) - LangGraph usage and patterns

### External Documentation

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) - LangGraph framework docs
- [LangChain Documentation](https://python.langchain.com/) - LangChain library docs

---

## Summary

The **Subgraph service** is a critical component of AgenticStudio's agent orchestration system, enabling proper async
delegation of tasks to sub-agents and sub-workflows using LangGraph's native subgraph capabilities.

**Key Features:**

- **Native LangGraph integration** - Uses LangGraph subgraphs instead of workarounds
- **Proper async patterns** - No new event loops or context variable hacks
- **Comprehensive tracking** - Database records and WebSocket notifications for all executions
- **Performance optimisation** - Caching of compiled subgraphs
- **Tool execution tracking** - Full visibility into tools used by sub-agents
- **Flexible state management** - Clean state passing between parent and subgraphs

**Primary Use Cases:**

- **Agent orchestration** - One agent delegates tasks to specialist agents
- **Workflow composition** - Agents invoking nested workflows
- **Parallel execution** - Multiple sub-agents executing concurrently
- **Complex workflows** - Multi-level agent hierarchies with proper tracking

**When to Use This Service:**

- Building orchestrator agents that coordinate multiple specialist agents
- Creating reusable agent components invoked from workflows
- Implementing parallel agent execution for improved performance
- Requiring detailed execution tracking for sub-agents and their tools
- Composing workflows with nested workflow components

**Architecture Highlights:**

- **Factory Pattern** for creating different subgraph types
- **Builder Pattern** for coordinating graph creation and caching
- **Executor Pattern** for separating execution from construction
- **Handler Pattern** for coordinating multiple execution concerns
- **Proper separation of concerns** between execution logic, database tracking, and notifications

The subgraph service represents a clean, maintainable solution to agent delegation in LangGraph-based systems, avoiding
common pitfalls while providing comprehensive tracking and observability.
