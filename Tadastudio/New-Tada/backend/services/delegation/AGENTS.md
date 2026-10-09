# Delegation Service

## Overview

The delegation service provides multi-agent orchestration capabilities for AgenticStudio, enabling orchestrator agents to
delegate tasks to sub-agents and sub-workflows. This service creates LangChain tools that wrap agent and workflow nodes,
allowing for seamless task delegation with proper execution tracking, state management, and output storage.

**Location:** [backend/services/delegation/](../../backend/services/delegation/)

**Primary Responsibilities:**

- Creating delegation tools that wrap agent nodes as callable tools
- Detecting orchestrator patterns in workflow graphs
- Managing execution context and tracking for delegated tasks
- Handling both simple and subgraph-based delegation execution
- Providing handoff tools for agent-to-agent transfers (LangGraph pattern)
- Creating subworkflow execution tools
- Storing and retrieving outputs from delegated executions
- Building tool node mappings for sub-agent tool resolution

**Key Use Cases:**

- Multi-agent workflows where an orchestrator delegates to specialist agents
- Hierarchical agent architectures with task decomposition
- Agent handoff patterns for sequential task processing
- Sub-workflow execution from parent workflows
- Tool execution tracking across nested agent calls

## Architecture

### Module Structure

```
backend/services/delegation/
├── __init__.py                  # Public API exports
├── detection.py                 # Orchestrator pattern detection
├── models.py                    # Data models and TypedDicts
├── config.py                    # Configuration and constants
├── storage.py                   # Output storage utilities
├── factories/                   # Tool factory implementations
│   ├── __init__.py             # Factory exports
│   ├── base.py                 # BaseDelegationToolFactory (shared functionality)
│   ├── sync_factory.py         # AgentDelegationToolFactory (main factory)
│   ├── handoff.py              # Handoff tool creation
│   └── subworkflow.py          # Subworkflow tool creation
├── executors/                   # Execution strategy implementations
│   ├── __init__.py             # Executor exports
│   ├── simple_executor.py      # SimpleDelegationExecutor (no tracking)
│   └── subgraph_executor.py    # SubgraphDelegationExecutor (with tracking)
└── utils/                       # Utility functions
    ├── __init__.py             # Utility exports
    ├── tool_mapping.py         # Tool node mapping builders
    └── event_loop.py           # Async/sync execution helpers
```

### Design Patterns

#### Factory Pattern

The service uses the **Factory Pattern** to create delegation tools:

```
BaseDelegationToolFactory (Abstract base with shared functionality)
    │
    └── AgentDelegationToolFactory (Concrete factory for agent delegation)
```

**Benefits:**

- Encapsulates complex tool creation logic
- Provides consistent interface for creating different tool types
- Shares common functionality (context retrieval, tool mapping) via base class
- Extensible for future delegation patterns

#### Strategy Pattern

The service uses the **Strategy Pattern** for execution:

```
Delegation Request
    ↓
ExecutorSelector (in factory)
    ↓
SimpleDelegationExecutor OR SubgraphDelegationExecutor
    ↓
Delegation Result
```

**Execution Strategies:**

- **SimpleDelegationExecutor**: Used when no execution context is available; performs basic agent chat
- **SubgraphDelegationExecutor**: Used when execution context exists; uses LangGraph subgraphs for full tracking

#### Dependency Injection

Factories depend on `GraphManager` injected at construction:

```python
factory = AgentDelegationToolFactory(graph_manager)
```

This allows:

- Testing with mock graph managers
- Decoupling from graph implementation details
- Runtime graph manager selection

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                  API / Execution Layer                      │
│  (Uses delegation tools created by factory)                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         AgentDelegationToolFactory (Main Factory)           │
│  - Creates delegation tools for orchestrators               │
│  - Selects execution strategy                               │
│  - Manages execution context                                │
└───────┬─────────────────────────────┬───────────────────────┘
        │                             │
        ↓                             ↓
┌──────────────────┐         ┌──────────────────┐
│ Simple Executor  │         │ Subgraph Executor│
│ (No tracking)    │         │ (Full tracking)  │
└───────┬──────────┘         └────────┬─────────┘
        │                             │
        └──────────┬──────────────────┘
                   │
                   ↓
        ┌──────────────────────┐
        │   GraphManager       │
        │   (Agent execution)  │
        └──────────────────────┘
```

### Dependencies

#### Internal Dependencies

- `backend.services.execution` - Execution context management and executor access
- `backend.services.subgraph` - Subgraph builder for sub-agent execution
- `backend.services.config` - Logging utilities
- `backend.services.dependency_injection` - Graph manager retrieval
- `backend.models.workflow` - EnhancedNodeData, GraphData, NodeType, ConnectionType

#### External Dependencies

- `langchain_core.tools` - Tool class for wrapping delegation functions
- `langchain_core.messages` - AIMessage for response parsing
- `asyncio` - Async execution and event loop handling
- `concurrent.futures` - Thread pool for async execution in sync contexts

#### Database Dependencies

None directly. Output storage uses in-memory caching on GraphManager instance.

#### Environment Variables

None. Configuration is handled via:

- `backend.services.delegation.config` constants
- Execution context from parent workflows

## Public API

### Exported Classes

- `AgentDelegationToolFactory` - Main factory for creating delegation tools for orchestrator agents

### Exported Functions

- `detect_orchestrator_pattern()` - Detect if a node should be configured as an orchestrator based on connections
- `create_handoff_tool()` - Create handoff tools for agent-to-agent transfers following LangGraph pattern

### Constants and Configuration

From [config.py](../../backend/services/delegation/config.py):

- `DELEGATION_TIMEOUT_SECONDS` - Timeout for delegation execution (default: 300 seconds / 5 minutes)
- `DEFAULT_EXECUTION_ORDER` - Default execution order value (default: 0)
- `LOG_PREFIX_DELEGATION` - Log prefix for delegation operations
- `LOG_PREFIX_SUBAGENT_STORE` - Log prefix for sub-agent output storage
- `LOG_PREFIX_SUBWORKFLOW` - Log prefix for subworkflow operations
- `LOG_PREFIX_SUBWORKFLOW_STORE` - Log prefix for subworkflow output storage
- `LOG_PREFIX_HANDOFF` - Log prefix for handoff operations

### Exceptions

This module does not define custom exceptions. It raises:

- `ValueError` - When invalid node types are provided (e.g., non-AGENT node to delegation tool creator)
- Standard Python exceptions for execution failures

## Core Classes

### `AgentDelegationToolFactory`

Main factory for creating delegation tools that allow orchestrator agents to delegate tasks to sub-agents and
sub-workflows.

**Purpose:** Provides a high-level interface for creating delegation tools with proper execution tracking, context
management, and tool resolution.

**Responsibilities:**

- Creating delegation tools that wrap agent nodes
- Creating subworkflow execution tools
- Managing execution context (execution IDs, database IDs)
- Selecting appropriate execution strategy (simple vs. subgraph)
- Building tool node mappings for sub-agents
- Creating complete tool sets for orchestrator nodes

**Initialisation:**

```python
def __init__(
    self,
    graph_manager,
) -> None:
    """
    Args:
        graph_manager: GraphManager instance for executing agents
    """
```

**Example:**

```python
from backend.services.delegation import AgentDelegationToolFactory
from backend.services.graph import GraphManager

# Initialize factory with graph manager
graph_manager = GraphManager()
factory = AgentDelegationToolFactory(graph_manager)
```

**Class Hierarchy:**

```
BaseDelegationToolFactory
    └── AgentDelegationToolFactory
```

**Key Methods:**

#### `create_delegation_tool()`

Creates a delegation tool that wraps a single agent node as a callable LangChain tool.

```python
def create_delegation_tool(
    self,
    agent_node: EnhancedNodeData,
    orchestrator_id: str,
    description: Optional[str] = None,
    parent_execution_id: Optional[str] = None,
    parent_db_execution_id: Optional[str] = None,
) -> Tool:
    """Create a delegation tool that wraps an agent node."""
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - The agent node to wrap as a tool
- `orchestrator_id` (str) - Unique ID of the orchestrator agent node
- `description` (Optional[str]) - Custom description for the tool (default: generated from agent metadata)
- `parent_execution_id` (Optional[str]) - Parent execution ID for tracking (default: retrieved from context)
- `parent_db_execution_id` (Optional[str]) - Parent database execution ID (default: retrieved from context)

**Returns:**

- `Tool` - LangChain Tool instance that can be used by the orchestrator

**Raises:**

- `ValueError` - If agent_node is not an AGENT type

**Example:**

```python
from backend.models.workflow import EnhancedNodeData, NodeType

# Create agent node (typically loaded from graph)
specialist_agent = EnhancedNodeData(
    uniq_id="agent_123",
    name="Data Analyst",
    type=NodeType.AGENT,
    description="Analyzes data and generates insights",
    is_sub_agent=True,
    delegation_description="Delegate data analysis tasks to this specialist",
)

# Create delegation tool
tool = factory.create_delegation_tool(
    agent_node=specialist_agent,
    orchestrator_id="orchestrator_456",
)

# Tool can now be used by orchestrator
result = tool.invoke("Analyze sales data for Q4 trends")
print(result)
# Output: "Data Analyst completed the task with the following result:\n\n[Analysis results...]"
```

**Behaviour:**

- Generates tool name from agent name (e.g., "delegate_to_data_analyst")
- Uses agent's `delegation_description` if available, otherwise generates from `description`
- Retrieves execution context from ExecutionContext or context variables
- Automatically selects execution strategy:
  - If execution IDs available and subgraph builder exists: uses SubgraphDelegationExecutor
  - Otherwise: uses SimpleDelegationExecutor
- Logs delegation start, execution details, and completion
- Formats result as agent response message

**Use Cases:**

- Creating individual delegation tools for specific sub-agents
- Custom tool creation with specific descriptions
- Fine-grained control over delegation tool configuration

#### `create_delegation_tools_for_orchestrator()`

Creates a complete set of delegation tools for all agents and subworkflows connected to an orchestrator node.

```python
def create_delegation_tools_for_orchestrator(
    self,
    orchestrator_node: EnhancedNodeData,
    connected_agents: List[EnhancedNodeData],
) -> List[Tool]:
    """Create delegation tools for all agents connected to an orchestrator."""
```

**Parameters:**

- `orchestrator_node` (EnhancedNodeData) - The orchestrator agent node
- `connected_agents` (List[EnhancedNodeData]) - List of agent and subworkflow nodes connected to the orchestrator

**Returns:**

- `List[Tool]` - List of delegation tools (one per connected agent/subworkflow)

**Raises:**

- `ValueError` - If orchestrator_node is not an AGENT type

**Example:**

```python
from backend.models.workflow import NodeType

# Orchestrator and connected agents (typically from graph)
orchestrator = EnhancedNodeData(
    uniq_id="orch_001",
    name="Task Orchestrator",
    type=NodeType.AGENT,
)

connected_agents = [
    EnhancedNodeData(
        uniq_id="agent_data",
        name="Data Analyst",
        type=NodeType.AGENT,
        delegation_description="Analyze data and generate insights",
    ),
    EnhancedNodeData(
        uniq_id="agent_report",
        name="Report Writer",
        type=NodeType.AGENT,
        delegation_description="Write professional reports",
    ),
    EnhancedNodeData(
        uniq_id="workflow_viz",
        name="Visualisation Workflow",
        type=NodeType.SUBWORKFLOW,
    ),
]

# Create all delegation tools
tools = factory.create_delegation_tools_for_orchestrator(
    orchestrator_node=orchestrator,
    connected_agents=connected_agents,
)

print(f"Created {len(tools)} delegation tools")
# Output: "Created 3 delegation tools"

# Tools can be provided to orchestrator agent
for tool in tools:
    print(f"- {tool.name}: {tool.description}")
# Output:
# - delegate_to_data_analyst: Analyze data and generate insights
# - delegate_to_report_writer: Write professional reports
# - execute_visualisation_workflow_workflow: Execute Visualisation Workflow...
```

**Behaviour:**

- Iterates through all connected nodes
- Creates delegation tools for AGENT type nodes
- Creates subworkflow execution tools for SUBWORKFLOW type nodes
- Logs errors for individual tool creation failures (doesn't stop processing)
- Returns all successfully created tools

**Use Cases:**

- Setting up orchestrator agents during graph compilation
- Automatic tool provisioning for multi-agent workflows
- Batch tool creation for complex orchestration scenarios

#### `create_subworkflow_tool()`

Creates a tool that executes a sub-workflow.

```python
def create_subworkflow_tool(
    self,
    subworkflow_node: EnhancedNodeData,
    orchestrator_id: str,
    description: Optional[str] = None,
    parent_execution_id: Optional[str] = None,
    parent_db_execution_id: Optional[str] = None,
) -> Tool:
    """Create a tool that executes a sub-workflow."""
```

**Parameters:**

- `subworkflow_node` (EnhancedNodeData) - The SUBWORKFLOW node to wrap as a tool
- `orchestrator_id` (str) - ID of the orchestrator agent
- `description` (Optional[str]) - Custom description for the tool
- `parent_execution_id` (Optional[str]) - Parent execution ID for tracking
- `parent_db_execution_id` (Optional[str]) - Parent database execution ID

**Returns:**

- `Tool` - Tool instance that can execute the sub-workflow

**Example:**

```python
subworkflow = EnhancedNodeData(
    uniq_id="subwf_001",
    name="Data Processing",
    type=NodeType.SUBWORKFLOW,
    subworkflow_config=SubworkflowConfig(
        workflow_name="data_processing",
        delegation_description="Process and clean data",
    ),
)

tool = factory.create_subworkflow_tool(
    subworkflow_node=subworkflow,
    orchestrator_id="orch_001",
)

result = tool.invoke(
    "Process customer data",
    customer_id="12345",
    include_history=True,
)
```

**Behaviour:**

- Delegates to `create_subworkflow_tool()` function from factories/subworkflow.py
- Passes graph_manager from factory instance
- Returns executable LangChain Tool

**Use Cases:**

- Creating tools for sub-workflow execution
- Enabling orchestrators to delegate to complete workflows
- Modular workflow composition

**Class Attributes:**

- `graph_manager` - GraphManager instance for executing agents
- `logger` - Logger instance for delegation operations

**Inherited from BaseDelegationToolFactory:**

- `_get_execution_context()` - Retrieve execution context from various sources
- `_build_tool_mapping()` - Build tool node mapping for sub-agents
- `_get_graph_name()` - Get current graph name from context
- `_get_tool_name_and_description()` - Generate tool name and description

### `BaseDelegationToolFactory`

Base factory class providing shared functionality for all delegation tool factories.

**Purpose:** Provides common functionality for execution context retrieval, tool mapping, and graph name resolution.

**Responsibilities:**

- Retrieving execution context from ExecutionContext or context variables
- Building tool node mappings for sub-agents
- Getting graph name from various sources
- Generating tool names and descriptions

**Initialisation:**

```python
def __init__(
    self,
    graph_manager,
) -> None:
    """
    Args:
        graph_manager: GraphManager instance for executing agents
    """
```

**Key Methods:**

#### `_get_execution_context()`

Retrieves execution context from ExecutionContext or context variables.

```python
def _get_execution_context(
    self,
    parent_execution_id: Optional[str] = None,
    parent_db_execution_id: Optional[str] = None,
) -> DelegationContext:
    """Get execution context from various sources."""
```

**Parameters:**

- `parent_execution_id` (Optional[str]) - Optional parent execution ID
- `parent_db_execution_id` (Optional[str]) - Optional parent database execution ID

**Returns:**

- `DelegationContext` - Dictionary containing execution context

**Behaviour:**

- First tries provided parameters
- Falls back to ExecutionContext.get_current()
- Finally falls back to context variables (get_current_execution_id(), get_current_db_execution_id())
- Returns context with execution_id, db_execution_id, execution_order, graph_name, tool_node_mapping

**Example:**

```python
context = factory._get_execution_context(
    parent_execution_id="exec_123",
    parent_db_execution_id="db_456",
)
# context = {
#     "execution_id": "exec_123",
#     "db_execution_id": "db_456",
#     "execution_order": 0,
#     "graph_name": None,
#     "tool_node_mapping": {},
# }
```

#### `_build_tool_mapping()`

Builds tool node mapping for a sub-agent, enabling tool resolution.

```python
def _build_tool_mapping(
    self,
    agent_node_id: str,
) -> Dict[str, Dict[str, str]]:
    """Build tool node mapping for a sub-agent."""
```

**Parameters:**

- `agent_node_id` (str) - The agent node ID to build mapping for

**Returns:**

- `Dict[str, Dict[str, str]]` - Tool node mapping dictionary

**Behaviour:**

- Gets graph name from context
- Retrieves graph from GraphManager
- Calls `build_tool_node_mapping()` utility function
- Returns mapping of tool names to node information
- Returns empty dict if graph not found or error occurs

**Example:**

```python
mapping = factory._build_tool_mapping("agent_123")
# mapping = {
#     "web_search_abc12345": {
#         "node_id": "node_abc123",
#         "node_name": "Web Search",
#         "node_type": NodeType.WEB_SEARCH
#     },
#     "web_search": {...},  # Alias
#     "document_search_def67890": {...},
# }
```

#### `_get_graph_name()`

Gets the current graph name from various sources.

```python
def _get_graph_name(self) -> Optional[str]:
    """Get the current graph name from various sources."""
```

**Returns:**

- `Optional[str]` - Graph name or None

**Behaviour:**

- First tries `graph_manager.current_graph_name` attribute
- Falls back to dependency injection (get_graph_manager())
- Returns None if not found

#### `_get_tool_name_and_description()`

Generates standardised tool name and description for an agent.

```python
def _get_tool_name_and_description(
    self,
    agent_node,
    custom_description: Optional[str] = None,
) -> tuple[str, str]:
    """Generate tool name and description for an agent."""
```

**Parameters:**

- `agent_node` - The agent node
- `custom_description` (Optional[str]) - Optional custom description

**Returns:**

- `tuple[str, str]` - Tuple of (tool_name, description)

**Behaviour:**

- Calls `generate_tool_name()` from config module
- Uses custom_description if provided, otherwise calls `generate_tool_description()`

**Class Attributes:**

- `graph_manager` - GraphManager instance
- `logger` - Logger instance

### `SimpleDelegationExecutor`

Executor for simple delegation without execution tracking or persistence.

**Purpose:** Provides basic agent execution for scenarios where no execution context is available or tracking is not
required.

**Responsibilities:**

- Executing agent chat without persistence
- Formatting responses
- Basic error handling

**Initialisation:**

```python
def __init__(
    self,
    graph_manager,
) -> None:
    """
    Args:
        graph_manager: GraphManager instance for executing agents
    """
```

**Key Methods:**

#### `execute()`

Executes delegation using simple chat execution.

```python
def execute(
    self,
    request: DelegationRequest,
) -> DelegationResult:
    """Execute delegation using simple chat execution."""
```

**Parameters:**

- `request` (DelegationRequest) - The delegation request

**Returns:**

- `DelegationResult` - Result with success status, response content, and metadata

**Example:**

```python
from backend.services.delegation.models import DelegationRequest, DelegationResult

request = DelegationRequest(
    agent_node=specialist_agent,
    task_description="Analyze Q4 sales data",
    orchestrator_id="orch_001",
)

executor = SimpleDelegationExecutor(graph_manager)
result = executor.execute(request)

if result.success:
    print(result.response)
else:
    print(f"Error: {result.error}")
```

**Behaviour:**

- Calls `graph_manager.execute_simple_chat()`
- Extracts content from AIMessage or converts to string
- Returns DelegationResult with execution_type="simple"
- Does not store outputs or track execution

**Use Cases:**

- Quick agent execution without tracking
- Testing and development
- Fallback when execution context unavailable

**Class Attributes:**

- `graph_manager` - GraphManager instance

### `SubgraphDelegationExecutor`

Executor for delegation using LangGraph subgraphs with full execution tracking and state management.

**Purpose:** Provides full-featured delegation execution with proper tracking, state management, tool resolution, and
output storage.

**Responsibilities:**

- Creating subgraph execution state
- Executing agents via LangGraph subgraphs
- Managing execution order
- Storing sub-agent outputs
- Handling async execution in sync contexts

**Initialisation:**

```python
def __init__(
    self,
    graph_manager,
) -> None:
    """
    Args:
        graph_manager: GraphManager instance for executing agents
    """
```

**Key Methods:**

#### `execute()`

Executes delegation using LangGraph subgraph approach.

```python
def execute(
    self,
    request: DelegationRequest,
) -> DelegationResult:
    """Execute delegation using subgraph approach."""
```

**Parameters:**

- `request` (DelegationRequest) - The delegation request with full context

**Returns:**

- `DelegationResult` - Result with success status, response, metadata, and structured output

**Example:**

```python
from backend.services.delegation.models import DelegationRequest, DelegationContext

context: DelegationContext = {
    "execution_id": "exec_789",
    "db_execution_id": "db_123",
    "execution_order": 1,
    "graph_name": "main_workflow",
    "tool_node_mapping": {...},
}

request = DelegationRequest(
    agent_node=specialist_agent,
    task_description="Generate monthly report",
    orchestrator_id="orch_001",
    context=context,
)

executor = SubgraphDelegationExecutor(graph_manager)
result = executor.execute(request)

if result.success:
    print(result.response)
    print(f"Execution order: {result.metadata['execution_order']}")
    print(f"Structured output: {result.metadata['structured_output']}")
```

**Behaviour:**

- Verifies subgraph builder availability
- Prepares SubAgentState with full execution context
- Creates subgraph via `executor.subgraph_builder.create_subagent_graph()`
- Executes subgraph using `run_async_in_sync()` for proper event loop handling
- Increments execution order
- Stores sub-agent output for later retrieval
- Returns DelegationResult with execution_type="subgraph"

**Use Cases:**

- Production delegation with full tracking
- Multi-level delegation hierarchies
- Tool execution tracking
- Structured output capture

**Class Attributes:**

- `graph_manager` - GraphManager instance

**Internal Methods:**

#### `_prepare_subagent_state()`

Prepares initial state for subgraph execution.

```python
def _prepare_subagent_state(
    self,
    request: DelegationRequest,
) -> Dict[str, Any]:
    """Prepare initial state for subgraph execution."""
```

**Returns:**

- `Dict[str, Any]` - SubAgentState dictionary with all required fields

**Behaviour:**

- Extracts context values from request
- Generates task_id using `generate_task_id()`
- Increments execution_order
- Includes tool_node_mapping for tool resolution
- Returns complete SubAgentState

#### `_store_subagent_output()`

Stores sub-agent output for later retrieval.

```python
def _store_subagent_output(
    self,
    request: DelegationRequest,
    result_state: Dict[str, Any],
) -> None:
    """Store subagent output for later retrieval."""
```

**Behaviour:**

- Stores output in `graph_manager._subagent_outputs[exec_id][agent_node_id]`
- Stores both raw response and structured output
- Logs storage operation

## Data Models

### `DelegationContext`

TypedDict containing context information for delegation execution.

```python
class DelegationContext(TypedDict, total=False):
    """Context information for delegation execution."""

    execution_id: Optional[str]
    db_execution_id: Optional[str]
    execution_order: int
    graph_name: Optional[str]
    tool_node_mapping: Dict[str, Dict[str, Any]]
```

**Fields:**

- `execution_id` - Parent execution ID for tracking
- `db_execution_id` - Database execution ID for persistence
- `execution_order` - Current execution order (incremented for sub-agents)
- `graph_name` - Name of the graph being executed
- `tool_node_mapping` - Mapping of tool names to node information

**Example:**

```python
context: DelegationContext = {
    "execution_id": "exec_abc123",
    "db_execution_id": "db_def456",
    "execution_order": 2,
    "graph_name": "customer_service_workflow",
    "tool_node_mapping": {
        "web_search": {"node_id": "ws_001", "node_name": "Web Search"},
    },
}
```

### `DelegationRequest`

Request object for delegating a task to an agent.

```python
class DelegationRequest:
    """Request for delegating a task to an agent."""

    def __init__(
        self,
        agent_node: EnhancedNodeData,
        task_description: str,
        orchestrator_id: str,
        context: Optional[DelegationContext] = None,
    ):
        """Initialize delegation request."""
```

**Attributes:**

- `agent_node` (EnhancedNodeData) - The agent node to delegate to
- `task_description` (str) - Description of the task
- `orchestrator_id` (str) - ID of the orchestrator agent
- `context` (Optional[DelegationContext]) - Execution context information

**Raises:**

- `ValueError` - If agent_node is not an AGENT type

**Example:**

```python
request = DelegationRequest(
    agent_node=data_analyst_node,
    task_description="Analyze customer churn patterns for Q4 2024",
    orchestrator_id="orchestrator_main",
    context=execution_context,
)
```

### `DelegationResult`

Result object from a delegation operation.

```python
class DelegationResult:
    """Result of a delegation operation."""

    def __init__(
        self,
        success: bool,
        response: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize delegation result."""
```

**Attributes:**

- `success` (bool) - Whether the delegation was successful
- `response` (Optional[str]) - Response from the delegated agent
- `error` (Optional[str]) - Error message if delegation failed
- `metadata` (Optional[Dict[str, Any]]) - Additional metadata about execution

**Methods:**

#### `format_for_agent()`

Formats the result for display to an agent.

```python
def format_for_agent(
    self,
    agent_name: str,
) -> str:
    """Format the result for display to an agent."""
```

**Example:**

```python
result = DelegationResult(
    success=True,
    response="Analysis complete. Churn rate is 15%...",
    metadata={
        "agent_name": "Data Analyst",
        "execution_order": 3,
    },
)

formatted = result.format_for_agent("Data Analyst")
# Output: "Data Analyst completed the task with the following result:\n\nAnalysis complete. Churn rate is 15%..."
```

### `SubworkflowRequest`

Request object for executing a subworkflow.

```python
class SubworkflowRequest:
    """Request for executing a subworkflow."""

    def __init__(
        self,
        subworkflow_node: EnhancedNodeData,
        task_description: str,
        orchestrator_id: str,
        workflow_input: Optional[Dict[str, Any]] = None,
        context: Optional[DelegationContext] = None,
    ):
        """Initialize subworkflow request."""
```

**Attributes:**

- `subworkflow_node` (EnhancedNodeData) - The subworkflow node to execute
- `task_description` (str) - Description of the task
- `orchestrator_id` (str) - ID of the orchestrator agent
- `workflow_input` (Optional[Dict[str, Any]]) - Additional input parameters
- `context` (Optional[DelegationContext]) - Execution context information

**Raises:**

- `ValueError` - If subworkflow_node is not a SUBWORKFLOW type

### `ToolNodeInfo`

TypedDict containing information about a tool node.

```python
class ToolNodeInfo(TypedDict):
    """Information about a tool node."""

    node_id: str
    node_name: str
    node_type: NodeType
```

**Fields:**

- `node_id` - Unique ID of the node
- `node_name` - Display name of the node
- `node_type` - Type of the node (NodeType enum value)

## Functions

### `detect_orchestrator_pattern()`

Detects if a node should be configured as an orchestrator based on its connections.

**Signature:**

```python
def detect_orchestrator_pattern(
    node: EnhancedNodeData,
    graph_nodes: List[EnhancedNodeData],
    connections: List[Any],
) -> bool:
    """Detect if a node should be configured as an orchestrator.

    An orchestrator is an agent node that delegates to 2 or more other agents
    via DELEGATION connections.
    """
```

**Parameters:**

- `node` (EnhancedNodeData) - The node to check
- `graph_nodes` (List[EnhancedNodeData]) - All nodes in the graph
- `connections` (List[Any]) - All connections in the graph

**Returns:**

- `bool` - True if the node appears to be an orchestrator (≥2 delegation connections to agents)

**Example:**

```python
from backend.services.delegation import detect_orchestrator_pattern
from backend.models.workflow import EnhancedNodeData, NodeType, ConnectionType

# Build graph structure
orchestrator_node = EnhancedNodeData(
    uniq_id="orch_001",
    name="Main Orchestrator",
    type=NodeType.AGENT,
)

specialist_1 = EnhancedNodeData(uniq_id="sp_001", type=NodeType.AGENT)
specialist_2 = EnhancedNodeData(uniq_id="sp_002", type=NodeType.AGENT)

all_nodes = [orchestrator_node, specialist_1, specialist_2]

# Connections from orchestrator to specialists
connections = [
    Connection(
        source_id="orch_001",
        target_id="sp_001",
        connection_type=ConnectionType.DELEGATION,
    ),
    Connection(
        source_id="orch_001",
        target_id="sp_002",
        connection_type=ConnectionType.DELEGATION,
    ),
]

# Detect orchestrator pattern
is_orchestrator = detect_orchestrator_pattern(
    node=orchestrator_node,
    graph_nodes=all_nodes,
    connections=connections,
)

print(is_orchestrator)  # Output: True
```

**Behaviour:**

- Returns False immediately if node is not AGENT type
- Counts outgoing DELEGATION connections to other AGENT nodes
- Also counts agent→agent connections without explicit connection_type (legacy support)
- Returns True if ≥2 delegation connections found
- Logs connection analysis details

**Use Cases:**

- Automatic orchestrator detection during graph compilation
- Determining which agents need delegation tools
- Graph validation and pattern analysis

### `create_handoff_tool()`

Creates a handoff tool following the LangGraph pattern for agent-to-agent transfers.

**Signature:**

```python
def create_handoff_tool(
    agent_name: str,
    agent_id: str,
    description: Optional[str] = None,
) -> Tool:
    """Create a handoff tool following LangGraph's pattern.

    This creates a tool that returns a Command object for proper
    agent handoff in LangGraph workflows.
    """
```

**Parameters:**

- `agent_name` (str) - Name of the agent to hand off to
- `agent_id` (str) - Unique ID of the agent node
- `description` (Optional[str]) - Optional tool description (default: "Transfer control to {agent_name} agent")

**Returns:**

- `Tool` - LangChain Tool that performs handoff

**Example:**

```python
from backend.services.delegation import create_handoff_tool

# Create handoff tool for customer support agent
handoff_tool = create_handoff_tool(
    agent_name="Customer Support",
    agent_id="agent_cs_001",
    description="Transfer conversation to customer support specialist",
)

# Use in LangGraph workflow
result = handoff_tool.invoke(
    task="Help customer with refund request",
    state={"customer_id": "12345"},
)

# Result is a command-like dict:
# {
#     "type": "handoff",
#     "goto": "agent_cs_001",
#     "agent_name": "Customer Support",
#     "task": "Help customer with refund request",
#     "state": {"customer_id": "12345"},
# }
```

**Behaviour:**

- Generates tool name: `transfer_to_{agent_name}` (lowercase, underscored)
- Returns dictionary with handoff metadata (not actual LangGraph Command object)
- Logs handoff operation

**Use Cases:**

- Sequential agent workflows with handoffs
- Multi-agent conversation systems
- LangGraph integration patterns

### `create_subworkflow_tool()`

Creates a tool that executes a sub-workflow.

**Signature:**

```python
def create_subworkflow_tool(
    subworkflow_node: EnhancedNodeData,
    orchestrator_id: str,
    graph_manager,
    description: Optional[str] = None,
    parent_execution_id: Optional[str] = None,
    parent_db_execution_id: Optional[str] = None,
) -> Tool:
    """Create a tool that executes a sub-workflow."""
```

**Parameters:**

- `subworkflow_node` (EnhancedNodeData) - The SUBWORKFLOW node to wrap as a tool
- `orchestrator_id` (str) - ID of the orchestrator agent
- `graph_manager` - GraphManager instance
- `description` (Optional[str]) - Optional custom description
- `parent_execution_id` (Optional[str]) - Parent execution ID for tracking
- `parent_db_execution_id` (Optional[str]) - Parent database execution ID

**Returns:**

- `Tool` - Tool instance that can execute the sub-workflow

**Raises:**

- `ValueError` - If subworkflow_node is not a SUBWORKFLOW type

**Example:**

```python
from backend.services.delegation.factories.subworkflow import create_subworkflow_tool

subworkflow_node = EnhancedNodeData(
    uniq_id="subwf_report",
    name="Monthly Report Generator",
    type=NodeType.SUBWORKFLOW,
    subworkflow_config=SubworkflowConfig(
        workflow_name="monthly_report_gen",
        delegation_description="Generate comprehensive monthly reports",
    ),
)

tool = create_subworkflow_tool(
    subworkflow_node=subworkflow_node,
    orchestrator_id="orch_main",
    graph_manager=graph_manager,
)

# Execute subworkflow with parameters
result = tool.invoke(
    "Generate October 2024 report",
    month="2024-10",
    include_charts=True,
)
```

**Behaviour:**

- Generates tool name: `execute_{workflow_name}_workflow`
- Uses SubgraphBuilder to create subworkflow graph
- Executes workflow with proper state management
- Stores workflow output for retrieval
- Handles async execution via `run_async_in_sync()`
- Returns formatted result from END node

**Use Cases:**

- Modular workflow composition
- Reusable workflow components
- Complex multi-stage workflows

## Utility Functions

### `build_tool_node_mapping()`

Builds a mapping of tool names to their corresponding node information, enabling sub-agents to resolve which node a tool
corresponds to.

**Signature:**

```python
def build_tool_node_mapping(
    graph: GraphData,
    agent_node_id: str,
) -> Dict[str, Dict[str, str]]:
    """Build tool node mapping for a sub-agent."""
```

**Parameters:**

- `graph` (GraphData) - The graph data containing nodes and connections
- `agent_node_id` (str) - The agent node ID to build mapping for

**Returns:**

- `Dict[str, Dict[str, str]]` - Dictionary mapping tool names to node information

**Example:**

```python
from backend.services.delegation.utils import build_tool_node_mapping

mapping = build_tool_node_mapping(
    graph=workflow_graph,
    agent_node_id="agent_researcher",
)

# mapping = {
#     "web_search_abc12345": {
#         "node_id": "node_ws_001",
#         "node_name": "Web Search",
#         "node_type": NodeType.WEB_SEARCH
#     },
#     "web_search": {...},  # Alias
#     "search_web": {...},  # Alias
#     "document_search_def67890": {...},
#     "document_search": {...},  # Alias
# }
```

**Behaviour:**

- Calls `graph.get_tool_nodes_for_agent(agent_node_id)`
- Maps each tool node with primary name and aliases
- Supports: WEB_SEARCH, DOCUMENT_SEARCH, DATABASE_QUERY, HTTP_REQUEST
- Returns empty dict if no tools found

**Tool Name Patterns:**

- Web Search: `web_search_{node_id[:8]}`, aliases: `web_search`, `search_web`
- Document Search: `document_search_{node_id[:8]}`, aliases: `document_search`, `search_documents`
- Database Query: `query_db_{node_id[:8]}`, aliases: `query_db`, `query_database`
- HTTP Request: `http_request_{node_id}` (full ID), alias: `http_request`

**Use Cases:**

- Enabling sub-agents to use tools from parent graph
- Tool resolution during execution
- Multi-level delegation with tool access

### `run_async_in_sync()`

Runs an async coroutine from synchronous code with automatic event loop handling.

**Signature:**

```python
def run_async_in_sync(
    coro: Awaitable[T],
    timeout: float = 300,
) -> T:
    """Run an async coroutine from synchronous code."""
```

**Parameters:**

- `coro` (Awaitable[T]) - The coroutine to run
- `timeout` (float) - Timeout in seconds (default: 300)

**Returns:**

- `T` - The result of the coroutine

**Raises:**

- `TimeoutError` - If execution exceeds timeout
- Any exception raised by the coroutine

**Example:**

```python
from backend.services.delegation.utils import run_async_in_sync

async def fetch_data():
    # Async operation
    return await some_async_call()

# Run from sync context
result = run_async_in_sync(fetch_data(), timeout=60)
```

**Behaviour:**

- Detects if event loop is already running
- If no loop: uses `asyncio.run()` directly
- If loop exists: runs in thread pool with new event loop
- Handles timeout with concurrent.futures

**Use Cases:**

- Calling async functions from sync delegation tools
- Event loop conflict resolution
- Subgraph execution from sync contexts

### `run_async_in_new_loop()`

Runs an async coroutine in a new event loop.

**Signature:**

```python
def run_async_in_new_loop(
    coro: Awaitable[T],
) -> T:
    """Run an async coroutine in a new event loop."""
```

**Parameters:**

- `coro` (Awaitable[T]) - The coroutine to run

**Returns:**

- `T` - The result of the coroutine

**Example:**

```python
from backend.services.delegation.utils import run_async_in_new_loop

result = run_async_in_new_loop(async_operation())
```

**Behaviour:**

- Creates new event loop
- Sets as current event loop
- Runs coroutine to completion
- Closes loop in finally block

**Use Cases:**

- Running async code in thread pools
- Isolating event loop execution
- Testing async code

## Configuration

### Configuration Functions

From [config.py](../../backend/services/delegation/config.py):

#### `generate_tool_name()`

Generates a standardised tool name for an agent.

```python
def generate_tool_name(
    agent_node: EnhancedNodeData,
    prefix: str = "delegate_to",
) -> str:
    """Generate a standardized tool name for an agent."""
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - The agent node
- `prefix` (str) - Prefix for the tool name (default: "delegate_to")

**Returns:**

- `str` - Standardised tool name (lowercase, underscored)

**Example:**

```python
from backend.services.delegation.config import generate_tool_name

agent = EnhancedNodeData(name="Data Analyst")
tool_name = generate_tool_name(agent)
# Output: "delegate_to_data_analyst"

custom_name = generate_tool_name(agent, prefix="call")
# Output: "call_data_analyst"
```

#### `generate_tool_description()`

Generates a description for a delegation tool.

```python
def generate_tool_description(
    agent_node: EnhancedNodeData,
) -> str:
    """Generate a description for a delegation tool."""
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - The agent node

**Returns:**

- `str` - Tool description

**Behaviour:**

- Uses `agent_node.delegation_description` if node is sub-agent
- Otherwise generates from `agent_node.description`

**Example:**

```python
from backend.services.delegation.config import generate_tool_description

agent = EnhancedNodeData(
    name="Report Writer",
    is_sub_agent=True,
    delegation_description="Creates professional business reports",
)

description = generate_tool_description(agent)
# Output: "Creates professional business reports"
```

#### `generate_task_id()`

Generates a task ID for delegation tracking.

```python
def generate_task_id(
    execution_id: str,
    agent_id: str,
) -> str:
    """Generate a task ID for delegation tracking."""
```

**Parameters:**

- `execution_id` (str) - Parent execution ID
- `agent_id` (str) - Agent node ID

**Returns:**

- `str` - Task ID string

**Example:**

```python
from backend.services.delegation.config import generate_task_id

task_id = generate_task_id("exec_123", "agent_456")
# Output: "task_exec_123_agent_456"
```

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.delegation import AgentDelegationToolFactory
from backend.services.graph import GraphManager

# Create graph manager
graph_manager = GraphManager()

# Create delegation factory
factory = AgentDelegationToolFactory(graph_manager)
```

**Usage in Graph Compilation:**

```python
from backend.services.delegation import (
    AgentDelegationToolFactory,
    detect_orchestrator_pattern,
)

# During graph compilation
def compile_agent_with_delegation(agent_node, graph_nodes, connections):
    # Detect if agent is orchestrator
    is_orchestrator = detect_orchestrator_pattern(
        agent_node,
        graph_nodes,
        connections,
    )

    if is_orchestrator:
        # Get connected agents
        connected_agents = get_connected_agents(agent_node, connections, graph_nodes)

        # Create delegation tools
        factory = AgentDelegationToolFactory(graph_manager)
        delegation_tools = factory.create_delegation_tools_for_orchestrator(
            orchestrator_node=agent_node,
            connected_agents=connected_agents,
        )

        # Add tools to agent
        agent_node.tools.extend(delegation_tools)
```

## Storage Functions

### `store_subagent_output()`

Stores sub-agent output for later retrieval.

```python
def store_subagent_output(
    graph_manager,
    execution_id: str,
    agent_node_id: str,
    agent_node_name: str,
    response: Optional[str],
    structured_output: Optional[Dict[str, Any]] = None,
) -> None:
    """Store subagent output for later retrieval."""
```

**Parameters:**

- `graph_manager` - GraphManager instance for storage
- `execution_id` (str) - Parent execution ID
- `agent_node_id` (str) - Agent node ID
- `agent_node_name` (str) - Agent node name
- `response` (Optional[str]) - Raw response text
- `structured_output` (Optional[Dict[str, Any]]) - Structured output dictionary

**Behaviour:**

- Initialises `graph_manager._subagent_outputs` if needed
- Stores under `graph_manager._subagent_outputs[execution_id][agent_node_id]`
- Stores both raw and structured outputs
- Logs storage operation

### `retrieve_subagent_output()`

Retrieves stored sub-agent output.

```python
def retrieve_subagent_output(
    graph_manager,
    execution_id: str,
    agent_node_id: str,
) -> Optional[Dict[str, Any]]:
    """Retrieve stored subagent output."""
```

**Returns:**

- `Optional[Dict[str, Any]]` - Output data dictionary with keys: `raw`, `structured`, `fields`

### `store_subworkflow_output()`

Stores subworkflow output for later retrieval.

```python
def store_subworkflow_output(
    graph_manager,
    execution_id: str,
    workflow_node_id: str,
    workflow_name: str,
    response: Optional[str],
    structured_output: Optional[Dict[str, Any]] = None,
    nodes_executed: Optional[list] = None,
) -> None:
    """Store subworkflow output for later retrieval."""
```

**Additional Field:**

- `nodes_executed` (Optional[list]) - List of nodes executed in the workflow

### `retrieve_subworkflow_output()`

Retrieves stored subworkflow output.

```python
def retrieve_subworkflow_output(
    graph_manager,
    execution_id: str,
    workflow_node_id: str,
) -> Optional[Dict[str, Any]]:
    """Retrieve stored subworkflow output."""
```

## Integration Patterns

### Integration with Graph Compilation

The delegation service is primarily used during graph compilation to provision orchestrator agents with delegation
tools.

```python
# In backend/services/graph/node_manager.py or similar
from backend.services.delegation import (
    AgentDelegationToolFactory,
    detect_orchestrator_pattern,
)

class NodeManager:
    def compile_agent_node(
        self,
        agent_node: EnhancedNodeData,
        graph_nodes: List[EnhancedNodeData],
        connections: List[Connection],
    ):
        # Detect if agent is orchestrator
        is_orchestrator = detect_orchestrator_pattern(
            node=agent_node,
            graph_nodes=graph_nodes,
            connections=connections,
        )

        if is_orchestrator:
            # Get agents connected via DELEGATION connections
            connected_agents = self._get_delegation_targets(
                agent_node,
                connections,
                graph_nodes,
            )

            # Create delegation factory
            factory = AgentDelegationToolFactory(self.graph_manager)

            # Create delegation tools
            delegation_tools = factory.create_delegation_tools_for_orchestrator(
                orchestrator_node=agent_node,
                connected_agents=connected_agents,
            )

            # Add to agent's tool list
            agent_node.compiled_tools = delegation_tools

            logger.info(
                f"Provisioned orchestrator {agent_node.name} "
                f"with {len(delegation_tools)} delegation tools"
            )
```

### Integration with Execution Service

The delegation service integrates with the execution service to execute sub-agents within the parent execution context.

```python
# Delegation flow during execution
from backend.services.execution import get_executor
from backend.services.delegation.executors import SubgraphDelegationExecutor

# In delegation tool function (created by factory)
def delegate_to_agent(task_description: str) -> str:
    # Get executor from execution service
    executor = get_executor()

    # Check for subgraph support
    if hasattr(executor, "subgraph_builder"):
        # Use subgraph executor for full tracking
        delegation_executor = SubgraphDelegationExecutor(graph_manager)
        result = delegation_executor.execute(request)
    else:
        # Fallback to simple execution
        delegation_executor = SimpleDelegationExecutor(graph_manager)
        result = delegation_executor.execute(request)

    return result.format_for_agent(agent_name)
```

### Integration with Subgraph Service

The delegation service uses the subgraph service to create isolated execution graphs for sub-agents.

```python
from backend.services.subgraph import SubgraphBuilder

class SubgraphDelegationExecutor:
    def execute(self, request: DelegationRequest) -> DelegationResult:
        # Get executor with subgraph support
        executor = get_executor()

        # Create subgraph for sub-agent
        subgraph = executor.subgraph_builder.create_subagent_graph(
            request.agent_node
        )

        # Prepare state with execution context
        initial_state = self._prepare_subagent_state(request)

        # Execute subgraph
        result_state = run_async_in_sync(subgraph.ainvoke(initial_state))

        return DelegationResult(
            success=True,
            response=result_state.get("response"),
            metadata={...},
        )
```

### Dependency Flow

```
API Layer (Execution Request)
    ↓
Execution Service (get_executor())
    ↓
Graph Manager (compile graph)
    ↓
Node Manager (compile agent nodes)
    ↓
Delegation Service (detect orchestrator, create tools)
    ↓
Graph Compilation Complete (agent has delegation tools)
    ↓
Execution Starts
    ↓
Orchestrator Agent (calls delegation tool)
    ↓
Delegation Tool Function (wrapped by factory)
    ↓
SubgraphDelegationExecutor or SimpleDelegationExecutor
    ↓
Subgraph Service (create_subagent_graph)
    ↓
Sub-agent Execution (in isolated subgraph)
    ↓
Output Storage (store_subagent_output)
    ↓
Return Result to Orchestrator
```

### Common Integration Patterns

#### Pattern 1: Orchestrator Detection and Tool Creation

```python
from backend.services.delegation import (
    AgentDelegationToolFactory,
    detect_orchestrator_pattern,
)

# Step 1: Detect orchestrator pattern
if detect_orchestrator_pattern(agent_node, graph_nodes, connections):
    # Step 2: Get connected agents
    connected_agents = [
        target for conn in connections
        if conn.source_id == agent_node.uniq_id
        and conn.connection_type == ConnectionType.DELEGATION
        for target in graph_nodes
        if target.uniq_id == conn.target_id
    ]

    # Step 3: Create factory and tools
    factory = AgentDelegationToolFactory(graph_manager)
    tools = factory.create_delegation_tools_for_orchestrator(
        orchestrator_node=agent_node,
        connected_agents=connected_agents,
    )

    # Step 4: Attach to agent
    agent_node.delegation_tools = tools
```

#### Pattern 2: Manual Delegation Tool Creation

```python
from backend.services.delegation import AgentDelegationToolFactory

# Create factory
factory = AgentDelegationToolFactory(graph_manager)

# Create individual delegation tool
specialist_tool = factory.create_delegation_tool(
    agent_node=specialist_agent,
    orchestrator_id="orch_main",
    description="Delegate complex data analysis tasks",
    parent_execution_id=current_execution_id,
)

# Use immediately
result = specialist_tool.invoke("Analyze Q4 revenue trends")
```

#### Pattern 3: Subworkflow Delegation

```python
from backend.services.delegation.factories.subworkflow import create_subworkflow_tool

# Create subworkflow tool
workflow_tool = create_subworkflow_tool(
    subworkflow_node=report_workflow_node,
    orchestrator_id="orch_main",
    graph_manager=graph_manager,
)

# Execute with parameters
result = workflow_tool.invoke(
    "Generate monthly report",
    month="2024-10",
    include_visualizations=True,
)
```

## Usage Examples

### Example 1: Basic Delegation Tool Creation

Complete end-to-end example of creating and using a delegation tool.

```python
from backend.services.delegation import AgentDelegationToolFactory
from backend.services.graph import GraphManager
from backend.models.workflow import EnhancedNodeData, NodeType

# Step 1: Set up graph manager
graph_manager = GraphManager()

# Step 2: Create agent nodes
orchestrator = EnhancedNodeData(
    uniq_id="orch_001",
    name="Research Orchestrator",
    type=NodeType.AGENT,
)

specialist = EnhancedNodeData(
    uniq_id="spec_data",
    name="Data Analyst",
    type=NodeType.AGENT,
    is_sub_agent=True,
    delegation_description="Analyze datasets and generate statistical insights",
)

# Step 3: Create delegation factory
factory = AgentDelegationToolFactory(graph_manager)

# Step 4: Create delegation tool
delegation_tool = factory.create_delegation_tool(
    agent_node=specialist,
    orchestrator_id=orchestrator.uniq_id,
)

# Step 5: Use the delegation tool
result = delegation_tool.invoke(
    "Analyze customer purchase patterns in the Q4 dataset"
)

# Step 6: Process result
print(f"Tool name: {delegation_tool.name}")
# Output: "Tool name: delegate_to_data_analyst"

print(f"Result: {result}")
# Output: "Data Analyst completed the task with the following result:\n\n[Analysis results...]"
```

### Example 2: Orchestrator Setup with Multiple Specialists

Complete example showing automatic orchestrator setup with multiple sub-agents.

```python
from backend.services.delegation import (
    AgentDelegationToolFactory,
    detect_orchestrator_pattern,
)
from backend.models.workflow import (
    EnhancedNodeData,
    NodeType,
    Connection,
    ConnectionType,
)

# Step 1: Define workflow structure
orchestrator = EnhancedNodeData(
    uniq_id="orch_customer_service",
    name="Customer Service Orchestrator",
    type=NodeType.AGENT,
    description="Routes customer requests to appropriate specialists",
)

support_agent = EnhancedNodeData(
    uniq_id="agent_support",
    name="Technical Support",
    type=NodeType.AGENT,
    is_sub_agent=True,
    delegation_description="Handle technical support questions and troubleshooting",
)

billing_agent = EnhancedNodeData(
    uniq_id="agent_billing",
    name="Billing Specialist",
    type=NodeType.AGENT,
    is_sub_agent=True,
    delegation_description="Handle billing inquiries and payment issues",
)

returns_agent = EnhancedNodeData(
    uniq_id="agent_returns",
    name="Returns Specialist",
    type=NodeType.AGENT,
    is_sub_agent=True,
    delegation_description="Process return and refund requests",
)

all_nodes = [orchestrator, support_agent, billing_agent, returns_agent]

# Step 2: Define connections
connections = [
    Connection(
        source_id=orchestrator.uniq_id,
        target_id=support_agent.uniq_id,
        connection_type=ConnectionType.DELEGATION,
    ),
    Connection(
        source_id=orchestrator.uniq_id,
        target_id=billing_agent.uniq_id,
        connection_type=ConnectionType.DELEGATION,
    ),
    Connection(
        source_id=orchestrator.uniq_id,
        target_id=returns_agent.uniq_id,
        connection_type=ConnectionType.DELEGATION,
    ),
]

# Step 3: Detect orchestrator pattern
is_orchestrator = detect_orchestrator_pattern(
    node=orchestrator,
    graph_nodes=all_nodes,
    connections=connections,
)

print(f"Is orchestrator: {is_orchestrator}")
# Output: "Is orchestrator: True"

# Step 4: Get connected agents
connected_specialists = [support_agent, billing_agent, returns_agent]

# Step 5: Create delegation tools
factory = AgentDelegationToolFactory(graph_manager)
delegation_tools = factory.create_delegation_tools_for_orchestrator(
    orchestrator_node=orchestrator,
    connected_agents=connected_specialists,
)

print(f"Created {len(delegation_tools)} delegation tools")
# Output: "Created 3 delegation tools"

# Step 6: Display tools
for tool in delegation_tools:
    print(f"- {tool.name}: {tool.description}")
# Output:
# - delegate_to_technical_support: Handle technical support questions and troubleshooting
# - delegate_to_billing_specialist: Handle billing inquiries and payment issues
# - delegate_to_returns_specialist: Process return and refund requests

# Step 7: Use orchestrator with delegation tools
# (In actual execution, these tools would be provided to the orchestrator agent)
result = delegation_tools[0].invoke(
    "Customer cannot connect to WiFi after router update"
)
print(result)
# Output: "Technical Support completed the task with the following result:\n\n[Support response...]"
```

### Example 3: Subworkflow Delegation

Complete workflow showing sub-workflow execution from an orchestrator.

```python
from backend.services.delegation import AgentDelegationToolFactory
from backend.models.workflow import (
    EnhancedNodeData,
    NodeType,
    SubworkflowConfig,
)

# Step 1: Create orchestrator
orchestrator = EnhancedNodeData(
    uniq_id="orch_report_gen",
    name="Report Generator Orchestrator",
    type=NodeType.AGENT,
)

# Step 2: Create subworkflow node
data_processing_workflow = EnhancedNodeData(
    uniq_id="subwf_data_proc",
    name="Data Processing Pipeline",
    type=NodeType.SUBWORKFLOW,
    description="Processes and cleanses raw data",
    subworkflow_config=SubworkflowConfig(
        workflow_name="data_processing_pipeline",
        delegation_description="Clean and process raw data files",
    ),
)

# Step 3: Create factory and subworkflow tool
factory = AgentDelegationToolFactory(graph_manager)
processing_tool = factory.create_subworkflow_tool(
    subworkflow_node=data_processing_workflow,
    orchestrator_id=orchestrator.uniq_id,
)

# Step 4: Execute subworkflow with parameters
result = processing_tool.invoke(
    "Process customer transaction data for monthly report",
    data_source="customer_transactions_oct_2024.csv",
    remove_duplicates=True,
    normalize_currency=True,
)

print(f"Workflow result: {result}")
# Output: "Data Processing Pipeline workflow completed with the following result:\n\n[Processed data summary...]"

# Step 5: Retrieve stored output
from backend.services.delegation.storage import retrieve_subworkflow_output

stored_output = retrieve_subworkflow_output(
    graph_manager=graph_manager,
    execution_id="exec_current",
    workflow_node_id=data_processing_workflow.uniq_id,
)

if stored_output:
    print(f"Raw output: {stored_output['raw']}")
    print(f"Structured output: {stored_output['structured']}")
    print(f"Nodes executed: {stored_output['workflow_nodes_executed']}")
```

### Example 4: Custom Execution Context

Example showing manual execution context management for delegation.

```python
from backend.services.delegation import AgentDelegationToolFactory
from backend.services.delegation.models import DelegationContext, DelegationRequest
from backend.services.delegation.executors import SubgraphDelegationExecutor

# Step 1: Build execution context manually
execution_context: DelegationContext = {
    "execution_id": "exec_parent_workflow_123",
    "db_execution_id": "db_exec_456",
    "execution_order": 2,
    "graph_name": "customer_onboarding_flow",
    "tool_node_mapping": {
        "web_search": {
            "node_id": "ws_node_001",
            "node_name": "Company Research",
            "node_type": NodeType.WEB_SEARCH,
        },
        "document_search": {
            "node_id": "ds_node_002",
            "node_name": "Policy Search",
            "node_type": NodeType.DOCUMENT_SEARCH,
        },
    },
}

# Step 2: Create delegation request
request = DelegationRequest(
    agent_node=compliance_specialist,
    task_description="Verify customer compliance with regulatory requirements",
    orchestrator_id="orch_onboarding",
    context=execution_context,
)

# Step 3: Execute with subgraph executor
executor = SubgraphDelegationExecutor(graph_manager)
result = executor.execute(request)

# Step 4: Process result
if result.success:
    print(f"Success! Response: {result.response}")
    print(f"Execution order: {result.metadata['execution_order']}")
    print(f"Structured output: {result.metadata.get('structured_output')}")
else:
    print(f"Error: {result.error}")
```

### Example 5: Testing Delegation Tools

Example showing how to test delegation tools in unit tests.

```python
import pytest
from unittest.mock import Mock, patch
from backend.services.delegation import AgentDelegationToolFactory
from backend.models.workflow import EnhancedNodeData, NodeType

@pytest.fixture
def mock_graph_manager():
    """Create mock graph manager for testing."""
    manager = Mock()
    manager.current_graph_name = "test_graph"
    manager.execute_simple_chat = Mock(return_value="Test response")
    return manager

@pytest.fixture
def test_agent():
    """Create test agent node."""
    return EnhancedNodeData(
        uniq_id="test_agent_001",
        name="Test Specialist",
        type=NodeType.AGENT,
        is_sub_agent=True,
        delegation_description="Test delegation",
    )

def test_delegation_tool_creation(mock_graph_manager, test_agent):
    """Test delegation tool creation."""
    factory = AgentDelegationToolFactory(mock_graph_manager)

    tool = factory.create_delegation_tool(
        agent_node=test_agent,
        orchestrator_id="orch_test",
    )

    assert tool.name == "delegate_to_test_specialist"
    assert "Test delegation" in tool.description

def test_delegation_tool_execution(mock_graph_manager, test_agent):
    """Test delegation tool execution."""
    factory = AgentDelegationToolFactory(mock_graph_manager)

    tool = factory.create_delegation_tool(
        agent_node=test_agent,
        orchestrator_id="orch_test",
    )

    # Execute tool
    result = tool.invoke("Test task")

    # Verify execution
    assert "Test Specialist completed the task" in result
    assert "Test response" in result
    mock_graph_manager.execute_simple_chat.assert_called_once()

def test_orchestrator_tool_creation(mock_graph_manager):
    """Test orchestrator tool creation."""
    orchestrator = EnhancedNodeData(
        uniq_id="orch_001",
        name="Test Orchestrator",
        type=NodeType.AGENT,
    )

    specialists = [
        EnhancedNodeData(
            uniq_id=f"spec_{i}",
            name=f"Specialist {i}",
            type=NodeType.AGENT,
            is_sub_agent=True,
        )
        for i in range(3)
    ]

    factory = AgentDelegationToolFactory(mock_graph_manager)
    tools = factory.create_delegation_tools_for_orchestrator(
        orchestrator_node=orchestrator,
        connected_agents=specialists,
    )

    assert len(tools) == 3
    assert all(tool.name.startswith("delegate_to_") for tool in tools)
```

## Performance Considerations

### Performance Characteristics

**Tool Creation:**

- Complexity: O(1) per tool
- Memory: Minimal (creates closure with references)
- I/O: None at creation time

**Tool Execution:**

- Complexity: Depends on sub-agent execution (typically O(n) where n = number of LLM calls)
- Memory: Proportional to execution state size
- I/O: I/O-bound (network calls to LLM providers)

**Tool Mapping:**

- Complexity: O(n) where n = number of tool nodes connected to agent
- Memory: O(n) for mapping storage
- I/O: None (in-memory operation)

**Orchestrator Detection:**

- Complexity: O(c) where c = number of connections
- Memory: Minimal (single-pass iteration)
- I/O: None

### Optimisation Tips

#### Tip 1: Reuse Factory Instances

**Problem:**

```python
# Creating new factory for each operation
for agent in agents:
    factory = AgentDelegationToolFactory(graph_manager)  # Wasteful
    tool = factory.create_delegation_tool(agent, orch_id)
```

**Solution:**

```python
# Create factory once, reuse
factory = AgentDelegationToolFactory(graph_manager)
for agent in agents:
    tool = factory.create_delegation_tool(agent, orch_id)
```

#### Tip 2: Batch Tool Creation

**Problem:**

```python
# Creating tools one at a time
tools = []
for agent in connected_agents:
    tool = factory.create_delegation_tool(agent, orch_id)
    tools.append(tool)
```

**Solution:**

```python
# Use batch method
tools = factory.create_delegation_tools_for_orchestrator(
    orchestrator_node=orchestrator,
    connected_agents=connected_agents,
)
```

#### Tip 3: Cache Tool Node Mappings

Tool node mappings are built fresh each time. For large graphs with many sub-agents, consider caching:

```python
# In factory or graph manager
_tool_mapping_cache = {}

def get_tool_mapping(agent_node_id):
    if agent_node_id not in _tool_mapping_cache:
        _tool_mapping_cache[agent_node_id] = build_tool_node_mapping(
            graph, agent_node_id
        )
    return _tool_mapping_cache[agent_node_id]
```

### Async/Await Support

The delegation service handles async execution automatically via utility functions:

```python
from backend.services.delegation.utils import run_async_in_sync

# Async subgraph execution
async def execute_subgraph_async(subgraph, initial_state):
    return await subgraph.ainvoke(initial_state)

# Called from sync context (delegation tool function)
result_state = run_async_in_sync(
    execute_subgraph_async(subgraph, initial_state),
    timeout=300,
)
```

**Benefits:**

- Automatically detects existing event loops
- Handles thread pool execution when needed
- Prevents "event loop already running" errors
- Supports timeout configuration

### Execution Timeout

Default timeout for delegation execution is 300 seconds (5 minutes), configurable via:

```python
from backend.services.delegation.config import DELEGATION_TIMEOUT_SECONDS

# Use in run_async_in_sync
result = run_async_in_sync(coro, timeout=DELEGATION_TIMEOUT_SECONDS)
```

For long-running delegations, increase timeout:

```python
# Custom timeout for complex workflows
result = run_async_in_sync(subworkflow_execution(), timeout=600)  # 10 minutes
```

## Best Practices

### Do's

✅ **Use orchestrator detection during graph compilation**

```python
from backend.services.delegation import detect_orchestrator_pattern

# In graph compilation phase
is_orchestrator = detect_orchestrator_pattern(
    node=agent_node,
    graph_nodes=all_nodes,
    connections=connections,
)

if is_orchestrator:
    # Automatically provision delegation tools
    tools = factory.create_delegation_tools_for_orchestrator(...)
```

✅ **Always provide execution context for tracking**

```python
# Good: Include execution context
tool = factory.create_delegation_tool(
    agent_node=specialist,
    orchestrator_id=orch_id,
    parent_execution_id=current_exec_id,
    parent_db_execution_id=current_db_exec_id,
)
```

✅ **Use batch methods for multiple tools**

```python
# Good: Batch creation
tools = factory.create_delegation_tools_for_orchestrator(
    orchestrator_node=orchestrator,
    connected_agents=specialists,
)

# Bad: Individual creation in loop
tools = []
for specialist in specialists:
    tool = factory.create_delegation_tool(specialist, orch_id)
    tools.append(tool)
```

✅ **Handle delegation errors gracefully**

```python
# Good: Handle errors from delegation
result = delegation_tool.invoke(task)

# Check for error indicators
if "Error" in result or "failed" in result.lower():
    # Handle delegation failure
    logger.error(f"Delegation failed: {result}")
    # Attempt recovery or alternative approach
```

✅ **Store and retrieve sub-agent outputs**

```python
from backend.services.delegation.storage import (
    store_subagent_output,
    retrieve_subagent_output,
)

# After delegation execution
store_subagent_output(
    graph_manager=graph_manager,
    execution_id=exec_id,
    agent_node_id=agent.uniq_id,
    agent_node_name=agent.name,
    response=result.response,
    structured_output=result.metadata.get("structured_output"),
)

# Later retrieval
output = retrieve_subagent_output(
    graph_manager=graph_manager,
    execution_id=exec_id,
    agent_node_id=agent.uniq_id,
)
```

### Don'ts

❌ **Don't create delegation tools for non-AGENT nodes**

```python
# Bad: Will raise ValueError
tool_node = EnhancedNodeData(type=NodeType.WEB_SEARCH, ...)
tool = factory.create_delegation_tool(tool_node, orch_id)  # ValueError!

# Good: Check node type first
if agent_node.type == NodeType.AGENT:
    tool = factory.create_delegation_tool(agent_node, orch_id)
```

❌ **Don't mix sync and async execution incorrectly**

```python
# Bad: Direct await in sync function
def sync_function():
    result = await subgraph.ainvoke(state)  # SyntaxError!

# Good: Use run_async_in_sync
from backend.services.delegation.utils import run_async_in_sync

def sync_function():
    result = run_async_in_sync(subgraph.ainvoke(state))
```

❌ **Don't ignore tool node mappings for sub-agents with tools**

```python
# Bad: Sub-agent won't be able to resolve tools
context = {
    "execution_id": exec_id,
    "db_execution_id": db_exec_id,
    "tool_node_mapping": {},  # Empty!
}

# Good: Build tool mapping
context = {
    "execution_id": exec_id,
    "db_execution_id": db_exec_id,
    "tool_node_mapping": factory._build_tool_mapping(agent_node.uniq_id),
}
```

❌ **Don't create circular delegation chains**

```python
# Bad: Agent A delegates to B, B delegates back to A
# This will cause infinite loops!

# Good: Design hierarchical delegation
# Orchestrator → Specialists (no back-delegation)
```

## Related Documentation

### Related Services

- [Execution Service](./execution.md) - Workflow and agent execution engine
- [Subgraph Service](./subgraph.md) - Subgraph builder for sub-agent and sub-workflow execution
- [Graph Service](./graph.md) - Graph building and management
- [Agent Service](./agent.md) - Agent compilation and configuration

### Related API Modules

- [Graph API](../agents-guide/api/graph.md) - Workflow management endpoints
- [Execution API](../agents-guide/api/execution.md) - Workflow execution endpoints

### Architecture Documentation

- [Multi-Agent Architecture](../architecture/multi_agent.md) - Multi-agent workflow patterns (if exists)
- [Execution Context](../architecture/execution_context.md) - Execution context management (if exists)

### External Documentation

- [LangChain Tools](https://python.langchain.com/docs/modules/tools/) - LangChain tool documentation
- [LangGraph](https://langchain-ai.github.io/langgraph/) - LangGraph documentation

## Summary

The delegation service is a core component of AgenticStudio's multi-agent orchestration capabilities, providing
sophisticated tools for hierarchical agent architectures and task decomposition. It enables orchestrator agents to
seamlessly delegate tasks to specialist sub-agents and sub-workflows while maintaining proper execution tracking,
context propagation, and state management.

The service achieves this through a factory-based architecture that creates LangChain tools wrapping agent and workflow
nodes. These tools handle execution strategy selection (simple vs. subgraph-based), context management, async/sync
bridging, and output storage. The detection utilities automatically identify orchestrator patterns in workflows,
enabling automatic tool provisioning during graph compilation.

Built on the factory and strategy patterns, the service provides extensibility for new delegation types while sharing
common functionality through the base factory class. Integration with the execution and subgraph services ensures proper
tracking and isolation of delegated tasks, while utility functions handle complex async execution scenarios.

**Key Features:**

- Automatic orchestrator detection based on graph structure
- Factory-based tool creation with execution strategy selection
- Full execution tracking via LangGraph subgraphs
- Tool node mapping for sub-agent tool resolution
- Subworkflow execution support
- Output storage and retrieval
- Async/sync execution bridging
- Handoff tools for LangGraph integration

**Primary Use Cases:**

- Multi-agent workflows with task delegation
- Hierarchical agent architectures (orchestrator → specialists)
- Modular workflow composition via sub-workflows
- Complex multi-stage data processing pipelines
- Agent handoff and sequential processing flows

**When to Use This Service:**

- Building workflows with multiple specialised agents
- Implementing orchestrator patterns for task routing
- Creating reusable sub-agent components
- Enabling agents to delegate specific tasks to specialists
- Tracking execution across nested agent calls
