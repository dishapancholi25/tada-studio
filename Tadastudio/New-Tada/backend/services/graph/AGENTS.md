# Graph Service Documentation

## Overview

The graph service provides comprehensive workflow graph management functionality for AgenticStudio, serving as the core
service for building, storing, validating, and executing visual workflow graphs.

**Location:** `backend/services/graph/`

**Primary Responsibilities:**

- Graph creation, persistence, and lifecycle management
- Node and connection management for workflow graphs
- Orchestrator and delegation pattern implementation
- Graph validation and compilation
- Database storage and access control
- Tool binding and agent compilation

**Key Use Cases:**

- Creating and managing visual workflow graphs in the AgenticStudio UI
- Building agent-based workflows with tool connections
- Implementing orchestrator patterns with sub-agent delegation
- Persisting graphs to database with version control
- Compiling graphs for optimised execution
- Validating graph structure before execution

## Architecture

### Module Structure

```
backend/services/graph/
├── __init__.py              # Public API exports
├── manager.py               # GraphManager (main facade)
├── node_manager.py          # Node CRUD operations
├── connection_manager.py    # Connection management
├── graph_crud.py            # Graph persistence
├── orchestrator_manager.py  # Orchestrator/delegation logic
├── validation.py            # Graph validation
├── export.py                # Graph export (LangGraph format)
├── compilation.py           # Compile-time tool binding
├── builder.py               # StateGraph builder
├── edge_builder.py          # Edge construction
├── cache.py                 # Graph compilation cache
├── constants.py             # Module constants
├── exceptions.py            # Custom exceptions
├── storage/                 # Database persistence
│   ├── __init__.py
│   ├── service.py           # GraphStorageService
│   ├── graph_persistence.py # Core persistence logic
│   ├── workflow_manager.py  # Workflow management
│   ├── query_builder.py     # SQL query builder
│   ├── access_control.py    # User access control
│   ├── user_resolver.py     # User resolution utilities
│   └── exceptions.py        # Storage exceptions
├── agent_tools/             # Agent tool creation
│   ├── __init__.py
│   ├── factory.py           # AgentToolFactory
│   ├── serialization.py     # Tool serialization
│   └── creators/            # Tool creator implementations
│       ├── database_query.py
│       ├── document_search.py
│       ├── http_request.py
│       ├── web_search.py
│       ├── mcp_server.py
│       └── subworkflow.py
└── tools/                   # Tool resolution
    ├── __init__.py
    ├── factory.py           # Tool factory
    └── resolver.py          # Tool resolver
```

**Major Components:**

- **manager.py**: Main facade coordinating all graph operations
- **node_manager.py**: Node creation, updates, deletion, and configuration
- **connection_manager.py**: Connection creation, removal, and relationship tracking
- **graph_crud.py**: Graph lifecycle (create, read, update, persist)
- **orchestrator_manager.py**: Orchestrator detection and delegation tools
- **validation.py**: Graph and node validation for execution readiness
- **compilation.py**: Compile-time tool binding and agent caching
- **storage/**: Database persistence layer with multi-tenant support
- **agent_tools/**: Factory for creating tool instances for agents

### Design Patterns

**Facade Pattern:**
The `GraphManager` class serves as a facade, providing a unified interface to all graph operations while delegating to
specialised service modules.

**Service Layer Pattern:**
The module is organised into focused service classes (NodeManager, ConnectionManager, ValidationService, etc.), each
responsible for a specific domain.

**Factory Pattern:**

- `AgentToolFactory`: Creates tool instances for agents
- `AgentDelegationToolFactory`: Creates delegation tools for orchestrators
- Tool creator classes for each node type

**Repository Pattern:**
`GraphStorageService` provides an abstraction over database operations for graph persistence.

**Dependency Injection:**
GraphManager is accessed via dependency injection (`get_graph_manager()`) to support testing and singleton behaviour.

**Component Relationships:**

```
┌─────────────────────────────────────────────────────┐
│              GraphManager (Facade)                   │
├─────────────────────────────────────────────────────┤
│  Coordinates all graph operations                   │
└────────────┬────────────────────────────────────────┘
             │
     ┌───────┴───────┐
     │               │
     ▼               ▼
┌──────────┐    ┌──────────────┐
│  Node    │    │  Connection  │
│ Manager  │    │   Manager    │
└──────────┘    └──────────────┘
     │               │
     │               │
     ▼               ▼
┌──────────────────────────────┐
│   GraphCRUDService           │
│   ├─ create_graph()          │
│   ├─ load_graph()            │
│   └─ save_graph()            │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  GraphStorageService         │
│  (Database Persistence)      │
└──────────────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   OrchestratorManager        │
│   ├─ detect patterns         │
│   ├─ create sub-agents       │
│   └─ delegation tools        │
└──────────────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   ValidationService          │
│   CompilationService         │
│   ExportService              │
└──────────────────────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.models.workflow`: Data models (GraphData, NodeData, Connection, etc.)
- `backend.services.config`: Logging utilities
- `backend.services.delegation`: Agent delegation tool factory
- `backend.services.execution.agent`: Agent execution services
- `backend.services.execution.async_agent`: Async agent executor
- `backend.services.llm_models`: LLM factory for agent creation
- `backend.services.model_deployment`: Model deployment management
- `backend.services.agent`: Agent compiler for compile-time binding
- `backend.services.tools`: Tool registry for compile-time features
- `backend.services.database`: Database session management
- `backend.services.workflow.state`: WorkflowState for LangGraph

**External Dependencies:**

- `langgraph`: StateGraph construction and compilation
- `sqlalchemy`: Database ORM for persistence
- `pydantic`: Data validation and serialization

**Database Dependencies:**

- `workflows` table: Stores workflow definitions
- `workflow_versions` table: Version history
- `users` table: User information for access control

**Environment Variables:**

- Database connection via SQLAlchemy settings (inherited from database service)
- No graph-specific environment variables

## Public API

### Exported Classes

- `GraphManager` - Main facade for all graph operations (primary entry point)
- `NodeManager` - Node creation and management service
- `ConnectionManager` - Connection management between nodes
- `GraphCRUDService` - Graph persistence and lifecycle management
- `OrchestratorManager` - Orchestrator and delegation management
- `ValidationService` - Graph and node validation
- `ExportService` - Graph export to various formats
- `CompilationService` - Compile-time tool binding and caching
- `GraphBuilder` - LangGraph StateGraph builder
- `EdgeBuilder` - Edge construction for StateGraph
- `GraphCache` - Compilation cache for graphs
- `GraphStorageService` - Database persistence service

### Exported Functions

- `resolve_user_id()` - Resolve user identifier for database operations
- `get_user_info()` - Retrieve user information from database

### Constants and Configuration

- `DEFAULT_NODE_STYLES` - Default styling for different node types (dict)
- `DEFAULT_AGENT_SYSTEM_PROMPT` - Default system prompt for agents (string)
- `LOG_PREFIX_NODE_MANAGER` - "[NODE-MANAGER]"
- `LOG_PREFIX_CONNECTION_MANAGER` - "[CONNECTION-MANAGER]"
- `LOG_PREFIX_GRAPH_CRUD` - "[GRAPH-CRUD]"
- `LOG_PREFIX_ORCHESTRATOR` - "[ORCHESTRATOR]"
- `LOG_PREFIX_VALIDATION` - "[VALIDATION]"
- `LOG_PREFIX_EXPORT` - "[EXPORT]"
- `LOG_PREFIX_COMPILATION` - "[COMPILATION]"
- `LOG_PREFIX_GRAPH_MANAGER` - "[GRAPH-MANAGER]"

### Exceptions

```
Exception
└── GraphOperationError (base exception for graph operations)
    ├── GraphNotFoundError
    ├── NodeNotFoundError
    ├── NodeValidationError
    ├── ConnectionValidationError
    ├── CircularDependencyError
    ├── GraphValidationError
    ├── CompilationError
    ├── ExportError
    ├── OrchestratorConfigurationError
    └── SubAgentCreationError
```

**Storage Exceptions:**

```
Exception
└── GraphStorageError (base storage exception)
    ├── WorkflowNotFoundError
    ├── AccessDeniedError
    ├── UserNotFoundError
    ├── GraphNotFoundError
    └── GraphVersionNotFoundError
```

## Core Classes

### `GraphManager`

Main facade for managing workflow graphs and their operations.

**Purpose:** Provides a unified, high-level interface for all graph-related operations, coordinating between specialised
service modules.

**Responsibilities:**

- Graph CRUD operations (create, read, update, delete)
- Node operations (create, update, delete, add to graph)
- Connection management (add, remove connections)
- Orchestrator and delegation management
- Graph validation and compilation
- Tool management for agents
- Agent execution (sync and async)

**Initialisation:**

```python
def __init__(
    self,
    workspace_dir: str = "./workspace",
    lazy_compile: bool = True,
) -> None:
    """
    Args:
        workspace_dir: Directory for workspace files (default: "./workspace")
        lazy_compile: Whether to use lazy compilation (default: True)
    """
```

**Key Methods:**

#### `create_graph()`

```python
def create_graph(
    self,
    name: str,
    description: str = "",
    username: str = "default",
    default_llm_config: Optional[str] = None,
) -> GraphData:
    """Create a new graph with default START node."""
```

**Parameters:**

- `name` (str) - Graph name
- `description` (str) - Graph description (default: "")
- `username` (str) - User creating the graph (default: "default")
- `default_llm_config` (Optional[str]) - Deprecated, ignored

**Returns:**

- `GraphData` - The created graph object

**Example:**

```python
from backend.services.graph import GraphManager

manager = GraphManager()
graph = manager.create_graph(
    "customer-support-workflow",
    "Automated customer support system"
)
print(f"Created graph: {graph.name} with ID: {graph.workflow_id}")
```

**Behaviour:**

- Creates a new GraphData instance with metadata
- Adds a default START node at position (100, 100)
- Saves the graph to database storage
- Adds to active_graphs cache

**Use Cases:**

- Creating new workflows from the UI
- Programmatically building workflow templates
- Initialising test graphs

#### `load_graph()`

```python
def load_graph(
    self,
    graph_name: str,
    username: str = "default",
) -> Optional[GraphData]:
    """Load a graph from database storage."""
```

**Parameters:**

- `graph_name` (str) - Name of the graph to load
- `username` (str) - User identifier for access control

**Returns:**

- `GraphData` - Loaded graph object, or None if not found

**Example:**

```python
graph = manager.load_graph("customer-support-workflow", username="user@example.com")
if graph:
    print(f"Loaded graph with {len(graph.nodes)} nodes")
else:
    print("Graph not found")
```

**Behaviour:**

- Fetches graph from database using GraphStorageService
- Runs orchestrator auto-detection on loaded graph
- Adds graph to active_graphs cache
- Updates metadata (last_loaded_by, last_loaded_at)

**Use Cases:**

- Opening a workflow in the editor
- Loading graphs for execution
- Retrieving graphs for analysis

#### `create_node()`

```python
def create_node(
    self,
    node_type: NodeType,
    name: str,
    position: Position = None,
    tool_template: Optional[str] = None,
    agent_template: Optional[str] = None,
    condition_prompt: Optional[str] = None,
    llm_config_override: Optional[str] = None,
    **kwargs,
) -> EnhancedNodeData:
    """Create a new node with specified type and configuration."""
```

**Parameters:**

- `node_type` (NodeType) - Type of node (AGENT, TOOL, CONDITION, etc.)
- `name` (str) - Node name
- `position` (Position) - Node position in graph canvas
- `condition_prompt` (Optional[str]) - Prompt for CONDITION nodes
- `**kwargs` - Additional node properties

**Returns:**

- `EnhancedNodeData` - The created node

**Example:**

```python
from backend.models.workflow import NodeType, Position

# Create an agent node
agent_node = manager.create_node(
    NodeType.AGENT,
    "Customer Support Agent",
    position=Position(300, 200),
    description="Handles customer inquiries"
)

# Create a condition node
condition_node = manager.create_node(
    NodeType.CONDITION,
    "Is Urgent?",
    position=Position(500, 200),
    condition_prompt="Determine if this is an urgent request"
)
```

**Behaviour:**

- Generates unique node ID (UUID)
- Applies default styling for node type
- Configures type-specific settings (AgentConfig, ConditionConfig, etc.)
- For AGENT nodes, assigns default LLM deployment if available
- Sets creation and update timestamps

**Use Cases:**

- Adding nodes to workflow canvas
- Building workflows programmatically
- Creating test fixtures

#### `add_connection()`

```python
def add_connection(
    self,
    graph_name: str,
    source_id: str,
    target_id: str,
    source_handle: Optional[str] = None,
    target_handle: Optional[str] = None,
    connection_type: ConnectionType = ConnectionType.WORKFLOW,
    label: str = "",
    true_condition: bool = False,
) -> bool:
    """Add a connection between two nodes."""
```

**Parameters:**

- `graph_name` (str) - Name of the graph
- `source_id` (str) - ID of source node
- `target_id` (str) - ID of target node
- `connection_type` (ConnectionType) - Type of connection (WORKFLOW, TOOL, DELEGATION)
- `true_condition` (bool) - For CONDITION nodes, whether this is the true branch

**Returns:**

- `bool` - True if connection added successfully

**Raises:**

- `NodeNotFoundError` - If source or target node doesn't exist
- `ConnectionValidationError` - If connection is invalid

**Example:**

```python
from backend.models.workflow import ConnectionType

# Add workflow connection
success = manager.add_connection(
    "customer-support-workflow",
    "start-node-id",
    "agent-node-id",
    connection_type=ConnectionType.WORKFLOW
)

# Add tool connection
success = manager.add_connection(
    "customer-support-workflow",
    "agent-node-id",
    "database-tool-id",
    connection_type=ConnectionType.TOOL
)

# Add delegation connection
success = manager.add_connection(
    "customer-support-workflow",
    "orchestrator-id",
    "sub-agent-id",
    connection_type=ConnectionType.DELEGATION
)
```

**Behaviour:**

- Validates connection compatibility (e.g., TOOL connections must be from AGENT to tool-compatible nodes)
- Updates node relationship lists (nexts, inputs)
- For TOOL connections, adds tool to agent's tools list
- For DELEGATION connections, marks source as orchestrator, target as sub-agent
- Automatically saves graph after connection

**Use Cases:**

- Connecting nodes in the visual editor
- Building workflow execution paths
- Establishing agent-tool relationships

#### `validate_graph()`

```python
def validate_graph(
    self,
    graph_name: str,
) -> Dict[str, Any]:
    """Validate a graph for execution readiness."""
```

**Parameters:**

- `graph_name` (str) - Name of the graph to validate

**Returns:**

- `Dict[str, Any]` - Validation result with keys:
  - `valid` (bool) - Whether graph is valid
  - `errors` (List[str]) - Validation errors
  - `warnings` (List[str]) - Validation warnings

**Example:**

```python
result = manager.validate_graph("customer-support-workflow")

if result["valid"]:
    print("Graph is ready for execution")
else:
    print("Validation errors:")
    for error in result["errors"]:
        print(f"  - {error}")

    print("Warnings:")
    for warning in result["warnings"]:
        print(f"  - {warning}")
```

**Behaviour:**

- Checks for required nodes (START node)
- Validates agent node configurations (LLM config, tools)
- Detects orphaned nodes (nodes with no connections)
- Validates LLM configuration parameters

**Use Cases:**

- Pre-execution validation
- UI validation feedback
- Automated testing

#### `compile_graph()`

```python
async def compile_graph(
    self,
    graph: GraphData,
) -> Dict[str, Any]:
    """Compile a graph with compile-time tool binding."""
```

**Parameters:**

- `graph` (GraphData) - Graph to compile

**Returns:**

- `Dict[str, Any]` - Dictionary mapping agent_id → CompiledAgent

**Raises:**

- `CompilationError` - If compilation fails

**Example:**

```python
import asyncio

async def compile_workflow():
    graph = manager.load_graph("customer-support-workflow")
    compiled_agents = await manager.compile_graph(graph)

    for agent_id, compiled_agent in compiled_agents.items():
        print(f"Compiled {compiled_agent.agent_name} with {len(compiled_agent.tools)} tools")

asyncio.run(compile_workflow())
```

**Behaviour:**

- Pre-compiles all agent nodes with their tool bindings
- Caches compiled agents for reuse
- Updates compilation status (compiling → compiled/partial/failed)
- Returns empty dict if compile-time features disabled

**Use Cases:**

- Optimising graph execution performance
- Pre-validating tool bindings
- Production deployment preparation

#### `get_tools()`

```python
def get_tools(
    self,
    tool_list: Optional[List[str]] = None,
    agent_config=None,
    graph_name: str = None,
    agent_node_id: str = None,
) -> List[Any]:
    """Get tools for an agent."""
```

**Parameters:**

- `tool_list` (Optional[List[str]]) - List of tool names
- `agent_config` - Agent configuration
- `graph_name` (str) - Graph name for context
- `agent_node_id` (str) - Agent node ID for tool resolution

**Returns:**

- `List[Any]` - List of tool instances

**Example:**

```python
# Get tools for an agent node
tools = manager.get_tools(
    graph_name="customer-support-workflow",
    agent_node_id="agent-123",
    agent_config=agent_node.agent_config
)

for tool in tools:
    print(f"Tool: {tool.name}")
```

**Behaviour:**

- Resolves tool definitions from node connections
- Creates tool instances using AgentToolFactory
- Includes delegation tools for orchestrator agents
- Handles compile-time and runtime tool resolution

**Use Cases:**

- Preparing tools for agent execution
- UI display of agent capabilities
- Tool validation

#### `execute_agent_async()`

```python
async def execute_agent_async(
    self,
    agent_node: EnhancedNodeData,
    user_message: str,
    format_output: bool = True,
    db_execution_id: Optional[str] = None,
    tool_execution_tracker: Optional[list] = None,
    return_token_counts: bool = False,
    graph_name: Optional[str] = None,
) -> Any:
    """Execute agent asynchronously."""
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - Agent node to execute
- `user_message` (str) - User input message
- `format_output` (bool) - Whether to format response
- `db_execution_id` (Optional[str]) - Database execution ID for tracking
- `tool_execution_tracker` (Optional[list]) - List to track tool executions
- `return_token_counts` (bool) - Whether to return token usage

**Returns:**

- `Any` - Agent response (formatted or raw)

**Example:**

```python
async def run_agent():
    graph = manager.load_graph("customer-support-workflow")
    agent_node = graph.get_node_by_id("support-agent-id")

    response = await manager.execute_agent_async(
        agent_node,
        "I need help with my order",
        graph_name=graph.name
    )

    print(f"Agent response: {response}")

asyncio.run(run_agent())
```

**Behaviour:**

- Creates execution context with configuration
- Resolves tools for the agent
- Executes agent using async executor
- Optionally returns token counts for billing

**Use Cases:**

- Agent node execution in workflows
- Testing agent behaviour
- Interactive agent chat

**Class Attributes:**

- `workspace_dir: Path` - Workspace directory path
- `model_service: ModelDeploymentService` - Model deployment service
- `node_manager: NodeManager` - Node management service
- `connection_manager: ConnectionManager` - Connection management service
- `graph_crud: GraphCRUDService` - Graph CRUD service
- `validation_service: ValidationService` - Validation service
- `compilation_service: CompilationService` - Compilation service
- `orchestrator_manager: OrchestratorManager` - Orchestrator management
- `tool_factory: AgentToolFactory` - Tool factory
- `llm_factory: LLMFactory` - LLM factory
- `async_executor` - Async agent executor
- `sync_executor` - Sync agent executor

**Properties:**

- `active_graphs: Dict[str, GraphData]` - In-memory cache of loaded graphs (read-only)
- `compiled_agents: Dict[str, Any]` - Cache of compiled agents (read-only)
- `compilation_status: Dict[str, str]` - Compilation status by graph (read-only)

---

### `NodeManager`

Service for managing workflow nodes.

**Purpose:** Handles all node-related operations including creation, updates, deletion, and type-specific configuration.

**Responsibilities:**

- Create nodes with type-specific configuration
- Update node properties and configurations
- Delete nodes and clean up relationships
- Apply default styling
- Configure LLM deployments for agents

**Initialisation:**

```python
def __init__(
    self,
    model_service: Any = None,
) -> None:
    """
    Args:
        model_service: Model deployment service for LLM defaults
    """
```

**Key Methods:**

#### `create_node()`

```python
def create_node(
    self,
    node_type: NodeType,
    name: str,
    position: Position = None,
    tool_template: Optional[str] = None,
    agent_template: Optional[str] = None,
    condition_prompt: Optional[str] = None,
    llm_config_override: Optional[str] = None,
    **kwargs,
) -> EnhancedNodeData:
    """Create a new node with specified type and configuration."""
```

**Example:**

```python
from backend.services.graph import NodeManager
from backend.models.workflow import NodeType, Position

node_mgr = NodeManager(model_service)
agent_node = node_mgr.create_node(
    NodeType.AGENT,
    "Support Agent",
    position=Position(200, 100),
    description="Handles customer support queries"
)
```

#### `update_node()`

```python
def update_node(
    self,
    graph: Any,
    node_id: str,
    updates: Dict[str, Any],
) -> bool:
    """Update a node in the specified graph."""
```

**Example:**

```python
success = node_mgr.update_node(
    graph,
    "agent-123",
    {
        "name": "Updated Agent Name",
        "agent_config": {
            "system_prompt": "You are a helpful assistant",
            "tools": ["web_search", "calculator"]
        }
    }
)
```

#### `delete_node()`

```python
def delete_node(
    self,
    graph: Any,
    node_id: str,
) -> bool:
    """Delete a node and all its connections."""
```

**Example:**

```python
success = node_mgr.delete_node(graph, "agent-123")
```

**Behaviour:**

- Removes all connections involving the node
- Cleans up references in other nodes (nexts, inputs)
- Removes tools from agents that used deleted tool nodes
- Updates graph timestamp

---

### `ConnectionManager`

Service for managing connections between nodes.

**Purpose:** Handles connection creation, removal, validation, and relationship maintenance.

**Responsibilities:**

- Add connections between nodes
- Remove connections
- Validate connection compatibility
- Update node relationships (nexts, inputs, tool lists)
- Configure delegation relationships

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialize connection manager."""
```

**Key Methods:**

#### `add_connection()`

```python
def add_connection(
    self,
    graph: Any,
    source_id: str,
    target_id: str,
    source_handle: Optional[str] = None,
    target_handle: Optional[str] = None,
    connection_type: ConnectionType = ConnectionType.WORKFLOW,
    label: str = "",
    true_condition: bool = False,
) -> bool:
    """Add a connection between two nodes in the graph."""
```

**Example:**

```python
from backend.services.graph import ConnectionManager
from backend.models.workflow import ConnectionType

conn_mgr = ConnectionManager()

# Add workflow connection
conn_mgr.add_connection(
    graph,
    "agent-1",
    "agent-2",
    connection_type=ConnectionType.WORKFLOW
)

# Add tool connection
conn_mgr.add_connection(
    graph,
    "agent-1",
    "database-query-tool",
    connection_type=ConnectionType.TOOL
)

# Add delegation connection
conn_mgr.add_connection(
    graph,
    "orchestrator-agent",
    "specialist-agent",
    connection_type=ConnectionType.DELEGATION
)
```

**Behaviour:**

- Validates nodes exist
- Validates connection type compatibility
- Updates node relationship lists
- For TOOL connections: adds tool to agent's tools list
- For DELEGATION connections: marks source as orchestrator, target as sub-agent

#### `remove_connection()`

```python
def remove_connection(
    self,
    graph: Any,
    source_id: str,
    target_id: str,
) -> bool:
    """Remove a connection between two nodes."""
```

**Example:**

```python
success = conn_mgr.remove_connection(graph, "agent-1", "tool-1")
```

**Behaviour:**

- Removes connection from graph.connections
- Cleans up node relationships
- For DELEGATION: unmarks orchestrator if no more delegated agents
- For TOOL: removes tool from agent's tools list

---

### `GraphCRUDService`

Service for graph CRUD operations.

**Purpose:** Manages graph lifecycle including creation, retrieval, persistence, and deletion.

**Responsibilities:**

- Create new graphs
- Load graphs from database
- Save graphs to database
- List user's graphs
- Maintain in-memory graph cache

**Initialisation:**

```python
def __init__(
    self,
    workspace_dir: str = "./workspace",
) -> None:
    """
    Args:
        workspace_dir: Directory for workspace files
    """
```

**Key Methods:**

#### `create_graph()`

```python
def create_graph(
    self,
    name: str,
    description: str = "",
    username: str = "default",
    default_llm_config: Optional[str] = None,
    node_manager: Optional[Any] = None,
) -> GraphData:
    """Create a new graph with default START node."""
```

**Example:**

```python
from backend.services.graph import GraphCRUDService

graph_crud = GraphCRUDService()
graph = graph_crud.create_graph(
    "order-processing",
    "Automated order processing workflow",
    username="user@example.com",
    node_manager=node_manager
)
```

#### `save_graph()`

```python
def save_graph(
    self,
    graph: GraphData,
    username: str = "default",
) -> bool:
    """Save a graph to database storage."""
```

**Example:**

```python
success = graph_crud.save_graph(graph, username="user@example.com")
if success:
    print("Graph saved successfully")
```

#### `load_graph()`

```python
def load_graph(
    self,
    graph_name: str,
    username: str = "default",
    orchestrator_manager: Optional[Any] = None,
) -> Optional[GraphData]:
    """Load a graph from database storage."""
```

**Example:**

```python
graph = graph_crud.load_graph(
    "order-processing",
    username="user@example.com",
    orchestrator_manager=orch_manager
)
```

#### `list_graphs()`

```python
def list_graphs(
    self,
    username: str = "default",
) -> List[Dict[str, Any]]:
    """List all graphs for a user from database storage."""
```

**Example:**

```python
graphs = graph_crud.list_graphs(username="user@example.com")
for graph_info in graphs:
    print(f"{graph_info['name']}: {graph_info['node_count']} nodes")
```

**Class Attributes:**

- `workspace_dir: Path` - Workspace directory
- `active_graphs: Dict[str, GraphData]` - In-memory cache of loaded graphs

---

### `OrchestratorManager`

Service for managing orchestrator agents and delegation.

**Purpose:** Handles orchestrator detection, configuration, sub-agent creation, and delegation tool management.

**Responsibilities:**

- Detect orchestrator patterns in graphs
- Configure orchestrator relationships
- Create sub-agents
- Generate delegation tools

**Initialisation:**

```python
def __init__(
    self,
    delegation_factory: Any,
    node_manager: Any = None,
    connection_manager: Any = None,
) -> None:
    """
    Args:
        delegation_factory: Factory for creating delegation tools
        node_manager: Optional node manager for creating sub-agents
        connection_manager: Optional connection manager
    """
```

**Key Methods:**

#### `detect_and_configure_orchestrators()`

```python
def detect_and_configure_orchestrators(
    self,
    graph: GraphData,
) -> int:
    """Detect and configure orchestrator agents in a graph."""
```

**Example:**

```python
from backend.services.graph import OrchestratorManager

orch_mgr = OrchestratorManager(delegation_factory, node_mgr, conn_mgr)
count = orch_mgr.detect_and_configure_orchestrators(graph)
print(f"Configured {count} orchestrators")
```

**Behaviour:**

- Analyses graph connections to identify orchestrator patterns
- Marks agents as orchestrators if they have DELEGATION connections
- Configures include_delegation_tools flag

#### `create_sub_agent()`

```python
def create_sub_agent(
    self,
    graph_name: str,
    active_graphs: Dict[str, GraphData],
    parent_agent_id: str,
    name: Optional[str] = None,
    position: Optional[Position] = None,
    delegation_description: str = "",
    agent_template: Optional[str] = None,
) -> Optional[EnhancedNodeData]:
    """Create a sub-agent for an orchestrator."""
```

**Example:**

```python
sub_agent = orch_mgr.create_sub_agent(
    "customer-support",
    active_graphs,
    "orchestrator-123",
    name="Billing Specialist",
    delegation_description="Handles billing and payment queries"
)
```

**Behaviour:**

- Creates new agent node
- Positions it relative to parent orchestrator
- Marks as sub-agent with parent_agent_id
- Adds DELEGATION connection to parent
- Saves updated graph

#### `get_delegation_tools()`

```python
def get_delegation_tools(
    self,
    graph: GraphData,
    orchestrator_node: EnhancedNodeData,
) -> List[Any]:
    """Get delegation tools for an orchestrator agent."""
```

**Example:**

```python
delegation_tools = orch_mgr.get_delegation_tools(graph, orchestrator_node)
for tool in delegation_tools:
    print(f"Delegation tool: {tool.name}")
```

**Behaviour:**

- Finds all agents connected via DELEGATION connections
- Creates delegation tools using delegation factory
- Returns list of callable tool instances

---

### `ValidationService`

Service for validating graphs, nodes, and configurations.

**Purpose:** Ensures graphs are valid and ready for execution.

**Responsibilities:**

- Validate graph structure
- Validate node configurations
- Validate LLM configurations
- Detect orphaned nodes
- Check execution readiness

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialize validation service."""
```

**Key Methods:**

#### `validate_graph()`

```python
def validate_graph(
    self,
    graph: GraphData,
) -> Dict[str, Any]:
    """Validate a graph for execution readiness."""
```

**Example:**

```python
from backend.services.graph import ValidationService

validator = ValidationService()
result = validator.validate_graph(graph)

if not result["valid"]:
    print("Validation errors:")
    for error in result["errors"]:
        print(f"  ❌ {error}")

if result["warnings"]:
    print("Warnings:")
    for warning in result["warnings"]:
        print(f"  ⚠️  {warning}")
```

**Returns:**

```python
{
    "valid": True/False,
    "errors": ["Error 1", "Error 2"],
    "warnings": ["Warning 1"]
}
```

#### `validate_agent_llm_config()`

```python
def validate_agent_llm_config(
    self,
    agent_config: AgentConfig,
) -> Tuple[bool, List[str]]:
    """Validate LLM configuration for an agent."""
```

**Example:**

```python
is_valid, errors = validator.validate_agent_llm_config(agent_config)

if not is_valid:
    for error in errors:
        print(f"Config error: {error}")
```

**Behaviour:**

- Checks for required fields (provider, model, API key)
- Validates parameter ranges (temperature, timeout)
- Checks provider-specific requirements (Azure endpoint, etc.)

---

### `CompilationService`

Service for compiling graphs with compile-time tool binding.

**Purpose:** Pre-compiles agents with their tool bindings for improved execution performance.

**Responsibilities:**

- Compile agents with tools
- Cache compiled agents
- Track compilation status
- Manage tool registry

**Initialisation:**

```python
def __init__(
    self,
    use_compile_time_tools: bool = True,
    lazy_compile: bool = True,
) -> None:
    """
    Args:
        use_compile_time_tools: Whether to enable compile-time tools
        lazy_compile: Whether to use lazy compilation
    """
```

**Key Methods:**

#### `compile_graph()`

```python
async def compile_graph(
    self,
    graph: GraphData,
) -> Dict[str, Any]:
    """Compile all agents in a graph with their tools."""
```

**Example:**

```python
from backend.services.graph import CompilationService
import asyncio

compiler = CompilationService()

async def compile():
    compiled_agents = await compiler.compile_graph(graph)
    for agent_id, compiled in compiled_agents.items():
        print(f"Compiled {compiled.agent_name} with {len(compiled.tools)} tools")

asyncio.run(compile())
```

**Returns:**

- `Dict[str, CompiledAgent]` - Map of agent_id to compiled agent

**Raises:**

- `CompilationError` - If compilation fails

#### `get_compiled_agent()`

```python
def get_compiled_agent(
    self,
    agent_id: str,
) -> Optional[Any]:
    """Get a compiled agent by ID."""
```

**Example:**

```python
compiled = compiler.get_compiled_agent("agent-123")
if compiled:
    print(f"Using cached compiled agent with {len(compiled.tools)} tools")
```

**Class Attributes:**

- `use_compile_time_tools: bool` - Whether compile-time tools are enabled
- `lazy_compile: bool` - Whether to use lazy compilation
- `compiled_agents: Dict[str, Any]` - Cache of compiled agents
- `compilation_status: Dict[str, str]` - Status by graph name
- `tool_registry: Optional[Any]` - Tool registry instance
- `agent_compiler: Optional[Any]` - Agent compiler instance

---

### `GraphStorageService`

Database persistence service for graphs.

**Purpose:** Provides database storage and retrieval for workflow graphs with multi-tenant support.

**Responsibilities:**

- Save graphs to database
- Load graphs from database
- List user's graphs
- Manage versions
- Access control

**Key Methods:**

#### `save_graph()`

```python
@staticmethod
def save_graph(
    graph: GraphData,
    workspace_id: str,
    created_by: str,
) -> Optional[str]:
    """Save a graph to database."""
```

**Example:**

```python
from backend.services.graph import GraphStorageService

workflow_id = GraphStorageService.save_graph(
    graph,
    workspace_id="user@example.com",
    created_by="user@example.com"
)

if workflow_id:
    print(f"Saved with workflow ID: {workflow_id}")
```

#### `load_graph()`

```python
@staticmethod
def load_graph(
    graph_name: str,
    workspace_id: str,
) -> Optional[GraphData]:
    """Load a graph from database by name."""
```

**Example:**

```python
graph = GraphStorageService.load_graph(
    "order-processing",
    workspace_id="user@example.com"
)
```

#### `list_graphs()`

```python
@staticmethod
def list_graphs(
    workspace_id: str,
) -> List[Dict[str, Any]]:
    """List all graphs for a workspace."""
```

**Example:**

```python
graphs = GraphStorageService.list_graphs(workspace_id="user@example.com")
for g in graphs:
    print(f"{g['name']} (v{g['version']})")
```

---

### `GraphBuilder`

Builds LangGraph StateGraph from workflow definitions.

**Purpose:** Converts AgenticStudio workflow graphs to executable LangGraph StateGraphs.

**Responsibilities:**

- Analyse node types
- Create StateGraph
- Add nodes and edges
- Configure entry points
- Handle tool nodes

**Key Methods:**

#### `build()`

```python
def build(
    self,
    graph: GraphData,
    execution_id: str,
    db_execution_id: Optional[int],
) -> StateGraph:
    """Build a LangGraph StateGraph from workflow definition."""
```

**Example:**

```python
from backend.services.graph import GraphBuilder

builder = GraphBuilder(
    node_function_creator,
    tool_node_creator,
    should_use_native_tools_fn,
    condition_function_factory
)

state_graph = builder.build(graph, execution_id="exec-123", db_execution_id=456)
compiled = state_graph.compile()
```

**Returns:**

- `StateGraph` - LangGraph StateGraph ready for compilation

---

### `GraphCache`

Cache for compiled LangGraph StateGraphs.

**Purpose:** Stores compiled graphs to avoid redundant compilation.

**Responsibilities:**

- Cache compiled graphs by key
- Retrieve cached graphs
- Invalidate cache entries
- Track cache size

**Key Methods:**

#### `get()`

```python
def get(
    self,
    graph: GraphData,
) -> Optional[StateGraph]:
    """Retrieve a cached compiled graph if it exists."""
```

**Example:**

```python
from backend.services.graph import GraphCache

cache = GraphCache()

# Try to get from cache
compiled = cache.get(graph)

if compiled:
    print("Using cached compilation")
else:
    # Compile and cache
    compiled = state_graph.compile()
    cache.put(graph, compiled)
```

#### `put()`

```python
def put(
    self,
    graph: GraphData,
    compiled_graph: StateGraph,
) -> None:
    """Store a compiled graph in the cache."""
```

#### `invalidate()`

```python
def invalidate(
    self,
    graph: GraphData,
) -> bool:
    """Invalidate (remove) a specific graph from the cache."""
```

**Example:**

```python
# Invalidate cache when graph changes
cache.invalidate(graph)
```

## Functions

### `resolve_user_id()`

Resolve user identifier for database operations.

**Signature:**

```python
def resolve_user_id(
    user_identifier: Optional[str] = None,
) -> int:
    """Resolve user identifier to database user ID.

    Args:
        user_identifier: Email or username

    Returns:
        Database user ID

    Raises:
        UserNotFoundError: If user not found
    """
```

**Example:**

```python
from backend.services.graph import resolve_user_id

user_id = resolve_user_id("user@example.com")
```

**Use Cases:**

- Converting email to database ID for storage operations
- Access control checks

## Configuration

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.graph import GraphManager

# Create graph manager with defaults
manager = GraphManager()

# Create a new graph
graph = manager.create_graph("my-workflow", "A sample workflow")
```

**Advanced Initialisation:**

```python
from backend.services.graph import GraphManager

# Custom workspace directory and lazy compilation
manager = GraphManager(
    workspace_dir="/custom/workspace",
    lazy_compile=False  # Compile immediately on load
)
```

**Dependency Injection:**

```python
from backend.services.dependency_injection import get_graph_manager

# Get singleton instance (recommended in production)
manager = get_graph_manager()

# Use in API endpoints
graph = manager.load_graph("workflow-name", username=current_user["email"])
```

### Environment Variables

The graph service does not use environment-specific variables directly. It inherits database configuration from the
database service via SQLAlchemy.

### Module Constants

**Node Styling:**

```python
from backend.services.graph import DEFAULT_NODE_STYLES
from backend.models.workflow import NodeType

# Get default styling for a node type
agent_style = DEFAULT_NODE_STYLES[NodeType.AGENT]
print(f"Agent color: {agent_style.color}")  # "#9C27B0" (purple)
```

**Default Prompts:**

```python
from backend.services.graph import DEFAULT_AGENT_SYSTEM_PROMPT

print(DEFAULT_AGENT_SYSTEM_PROMPT)
# "You are a helpful AI assistant. Please respond to the user's message thoughtfully and accurately."
```

## Error Handling

### Exception Hierarchy

```
Exception
└── GraphOperationError
    ├── GraphNotFoundError
    ├── NodeNotFoundError
    ├── NodeValidationError
    ├── ConnectionValidationError
    ├── CircularDependencyError
    ├── GraphValidationError
    ├── CompilationError
    ├── ExportError
    ├── OrchestratorConfigurationError
    └── SubAgentCreationError
```

**Storage Exceptions:**

```
Exception
└── GraphStorageError
    ├── WorkflowNotFoundError
    ├── AccessDeniedError
    ├── UserNotFoundError
    ├── GraphNotFoundError
    └── GraphVersionNotFoundError
```

### Exception Details

#### `GraphNotFoundError`

Raised when a requested graph cannot be found.

**Inherits from:** `GraphOperationError`

**When raised:**

- Graph name doesn't exist in database
- User doesn't have access to the graph
- Graph was deleted

**Example:**

```python
from backend.services.graph import GraphManager, GraphNotFoundError

try:
    graph = manager.load_graph("non-existent-graph")
except GraphNotFoundError as e:
    print(f"Graph not found: {e}")
```

#### `NodeNotFoundError`

Raised when a requested node cannot be found.

**Inherits from:** `GraphOperationError`

**When raised:**

- Node ID doesn't exist in graph
- Node was deleted

**Example:**

```python
from backend.services.graph import NodeNotFoundError

try:
    manager.update_node("my-graph", "invalid-node-id", {"name": "New Name"})
except NodeNotFoundError as e:
    print(f"Node not found: {e}")
```

#### `ConnectionValidationError`

Raised when connection validation fails.

**Inherits from:** `GraphOperationError`

**When raised:**

- TOOL connection from non-AGENT node
- DELEGATION connection to non-AGENT node
- Invalid connection type

**Example:**

```python
from backend.services.graph import ConnectionValidationError
from backend.models.workflow import ConnectionType

try:
    # This will fail - TOOL connections must originate from AGENT nodes
    manager.add_connection(
        "my-graph",
        "condition-node",
        "tool-node",
        connection_type=ConnectionType.TOOL
    )
except ConnectionValidationError as e:
    print(f"Invalid connection: {e}")
```

#### `CompilationError`

Raised when graph compilation fails.

**Inherits from:** `GraphOperationError`

**When raised:**

- Agent compilation fails due to invalid tool configuration
- Missing required dependencies
- Tool registry unavailable

**Example:**

```python
from backend.services.graph import CompilationError
import asyncio

async def compile_graph():
    try:
        compiled = await manager.compile_graph(graph)
    except CompilationError as e:
        print(f"Compilation failed: {e}")
        for error in e.errors:
            print(f"  - {error}")

asyncio.run(compile_graph())
```

### Error Handling Patterns

**Recommended Pattern:**

```python
from backend.services.graph import (
    GraphManager,
    GraphNotFoundError,
    NodeNotFoundError,
    ConnectionValidationError,
    GraphValidationError,
    GraphOperationError
)

try:
    # Load graph
    graph = manager.load_graph("my-workflow", username="user@example.com")

    # Validate before execution
    validation_result = manager.validate_graph("my-workflow")
    if not validation_result["valid"]:
        # Handle validation errors
        for error in validation_result["errors"]:
            logger.error(f"Validation error: {error}")
        raise GraphValidationError("my-workflow", validation_result["errors"])

    # Perform operations
    manager.add_connection("my-workflow", "node-1", "node-2")
    manager.save_graph(graph, username="user@example.com")

except GraphNotFoundError as e:
    # Graph doesn't exist or user doesn't have access
    logger.error(f"Graph not found: {e}")
    return {"error": "Graph not found", "graph_name": e.graph_name}

except NodeNotFoundError as e:
    # Node doesn't exist
    logger.error(f"Node not found: {e}")
    return {"error": "Node not found", "node_id": e.node_id}

except ConnectionValidationError as e:
    # Invalid connection
    logger.error(f"Invalid connection: {e}")
    return {"error": str(e)}

except GraphValidationError as e:
    # Graph validation failed
    logger.error(f"Validation failed: {e}")
    return {"error": "Validation failed", "errors": e.errors}

except GraphOperationError as e:
    # Catch-all for graph operation errors
    logger.error(f"Graph operation failed: {e}")
    return {"error": str(e)}
```

**Storage Error Handling:**

```python
from backend.services.graph import (
    GraphStorageService,
    GraphStorageError,
    AccessDeniedError,
    WorkflowNotFoundError
)

try:
    graphs = GraphStorageService.list_graphs(workspace_id="user@example.com")
except AccessDeniedError as e:
    logger.error(f"Access denied: {e}")
    return {"error": "Access denied"}
except GraphStorageError as e:
    logger.error(f"Storage error: {e}")
    return {"error": "Database error"}
```

## Integration Patterns

### Integration with API Layer

The graph service is primarily accessed through FastAPI endpoints in `backend/api/graph/`. Integration uses dependency
injection to access the singleton GraphManager instance.

**Example from backend/api/graph/routes.py:**

```python
from fastapi import APIRouter, Depends
from backend.services.dependency_injection import get_graph_manager
from backend.api.graph.dependencies import get_user_identifier, get_graph_or_404
from backend.auth import get_current_user

router = APIRouter()

@router.post("/graphs")
async def create_graph(
    request: CreateGraphRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new workflow graph."""
    user_id = get_user_identifier(current_user)
    manager = get_graph_manager()

    graph = manager.create_graph(
        name=request.name,
        description=request.description,
        username=user_id
    )

    return {
        "workflow_id": graph.workflow_id,
        "name": graph.name,
        "description": graph.description
    }

@router.get("/graphs/{graph_name}")
async def get_graph(
    graph_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve a workflow graph."""
    user_id = get_user_identifier(current_user)
    graph = get_graph_or_404(graph_name, user_id)

    return graph.dict()

@router.put("/graphs/{graph_name}/nodes/{node_id}")
async def update_node(
    graph_name: str,
    node_id: str,
    updates: dict,
    current_user: dict = Depends(get_current_user)
):
    """Update a node in the graph."""
    user_id = get_user_identifier(current_user)
    graph = get_graph_or_404(graph_name, user_id)

    manager = get_graph_manager()
    success = manager.update_node(graph_name, node_id, updates)

    if success:
        manager.save_graph(graph, username=user_id)

    return {"success": success}
```

### Integration with Execution Layer

The graph service provides graphs to the execution layer for workflow execution.

**Example from backend/services/execution/:**

```python
from backend.services.dependency_injection import get_graph_manager

async def execute_workflow(workflow_name: str, user_input: str, username: str):
    """Execute a workflow graph."""
    manager = get_graph_manager()

    # Load the graph
    graph = manager.load_graph(workflow_name, username=username)

    if not graph:
        raise ValueError(f"Graph '{workflow_name}' not found")

    # Validate the graph
    validation_result = manager.validate_graph(workflow_name)
    if not validation_result["valid"]:
        raise ValueError(f"Graph validation failed: {validation_result['errors']}")

    # Compile agents (if enabled)
    compiled_agents = await manager.compile_graph(graph)

    # Execute using execution engine
    from backend.services.dependency_injection import get_execution_engine

    engine = get_execution_engine()
    result = await engine.execute(
        graph,
        user_input,
        execution_id="exec-123",
        username=username
    )

    return result
```

### Integration with Other Services

**With Model Deployment Service:**

```python
from backend.services.graph import GraphManager
from backend.services.model_deployment import ModelDeploymentService

# GraphManager automatically uses ModelDeploymentService
# to assign default LLM deployments to new agent nodes

manager = GraphManager()

# When creating agent nodes, default LLM deployment is assigned
agent_node = manager.create_node(
    NodeType.AGENT,
    "Support Agent"
)

# The agent_node.agent_config.llm_config will have the default deployment
print(agent_node.agent_config.llm_config.model_deployment_id)
```

**With Agent Service:**

```python
from backend.services.graph import GraphManager

manager = GraphManager()

# Compilation service integrates with agent service
compiled_agents = await manager.compile_graph(graph)

# Uses backend.services.agent.get_agent_compiler()
# and backend.services.tools.get_tool_registry()
```

**With Delegation Service:**

```python
from backend.services.graph import GraphManager

manager = GraphManager()

# Get delegation tools for orchestrator
delegation_tools = manager.get_delegation_tools(graph, orchestrator_node)

# Internally uses backend.services.delegation.AgentDelegationToolFactory
```

### Dependency Flow

```
API Layer (FastAPI)
    │
    ├─→ get_graph_manager() (Dependency Injection)
    │
    ▼
GraphManager (Facade)
    │
    ├─→ NodeManager
    ├─→ ConnectionManager
    ├─→ GraphCRUDService
    │       │
    │       └─→ GraphStorageService (Database)
    │
    ├─→ OrchestratorManager
    │       │
    │       └─→ AgentDelegationToolFactory
    │
    ├─→ ValidationService
    ├─→ CompilationService
    │       │
    │       ├─→ get_agent_compiler()
    │       └─→ get_tool_registry()
    │
    ├─→ AgentToolFactory
    │       │
    │       └─→ Tool Creators
    │
    ├─→ LLMFactory
    └─→ ModelDeploymentService
```

### Common Integration Patterns

#### Pattern 1: Create and Configure Graph

```python
from backend.services.dependency_injection import get_graph_manager
from backend.models.workflow import NodeType, Position, ConnectionType

async def create_support_workflow(username: str):
    """Create a customer support workflow."""
    manager = get_graph_manager()

    # Create graph
    graph = manager.create_graph(
        "customer-support",
        "Automated customer support workflow",
        username=username
    )

    # Create nodes
    agent_node = manager.create_node(
        NodeType.AGENT,
        "Support Agent",
        position=Position(300, 200),
        description="Handles customer inquiries"
    )

    database_tool = manager.create_node(
        NodeType.DATABASE_QUERY,
        "Order Lookup",
        position=Position(300, 400)
    )

    # Add nodes to graph
    manager.add_node_to_graph(graph.name, agent_node)
    manager.add_node_to_graph(graph.name, database_tool)

    # Connect START to agent
    start_node = graph.nodes[0]  # START node created by default
    manager.add_connection(
        graph.name,
        start_node.uniq_id,
        agent_node.uniq_id,
        connection_type=ConnectionType.WORKFLOW
    )

    # Connect tool to agent
    manager.add_connection(
        graph.name,
        agent_node.uniq_id,
        database_tool.uniq_id,
        connection_type=ConnectionType.TOOL
    )

    # Validate
    result = manager.validate_graph(graph.name)
    if not result["valid"]:
        raise ValueError(f"Validation failed: {result['errors']}")

    # Save
    manager.save_graph(graph, username=username)

    return graph
```

#### Pattern 2: Load and Execute Graph

```python
from backend.services.dependency_injection import get_graph_manager

async def execute_graph_workflow(graph_name: str, user_input: str, username: str):
    """Load and execute a graph."""
    manager = get_graph_manager()

    # Load graph
    graph = manager.load_graph(graph_name, username=username)

    if not graph:
        raise ValueError(f"Graph '{graph_name}' not found")

    # Find the first agent node
    agent_node = next(
        (node for node in graph.nodes if node.type == NodeType.AGENT),
        None
    )

    if not agent_node:
        raise ValueError("No agent node found in graph")

    # Execute agent
    response = await manager.execute_agent_async(
        agent_node,
        user_input,
        graph_name=graph_name
    )

    return response
```

#### Pattern 3: Orchestrator with Sub-Agents

```python
from backend.services.dependency_injection import get_graph_manager
from backend.models.workflow import NodeType, Position, ConnectionType

async def create_orchestrator_workflow(username: str):
    """Create workflow with orchestrator pattern."""
    manager = get_graph_manager()

    # Create graph
    graph = manager.create_graph(
        "multi-agent-support",
        "Multi-agent customer support",
        username=username
    )

    # Create orchestrator
    orchestrator = manager.create_node(
        NodeType.AGENT,
        "Support Orchestrator",
        position=Position(300, 200),
        description="Routes customer queries to specialist agents"
    )
    manager.add_node_to_graph(graph.name, orchestrator)

    # Create specialist agents
    billing_agent = manager.create_sub_agent(
        graph.name,
        orchestrator.uniq_id,
        name="Billing Specialist",
        delegation_description="Handles billing and payment questions"
    )

    technical_agent = manager.create_sub_agent(
        graph.name,
        orchestrator.uniq_id,
        name="Technical Specialist",
        delegation_description="Handles technical support questions"
    )

    # Connect START to orchestrator
    start_node = graph.nodes[0]
    manager.add_connection(
        graph.name,
        start_node.uniq_id,
        orchestrator.uniq_id,
        connection_type=ConnectionType.WORKFLOW
    )

    # Detect and configure orchestrators
    count = manager.detect_and_configure_orchestrators(graph)
    print(f"Configured {count} orchestrators")

    # Save
    manager.save_graph(graph, username=username)

    return graph
```

## Usage Examples

### Example 1: Basic Graph Creation

```python
from backend.services.graph import GraphManager
from backend.models.workflow import NodeType, Position, ConnectionType

# Initialize manager
manager = GraphManager()

# Create a new graph
graph = manager.create_graph(
    "simple-chat",
    "Simple chatbot workflow"
)

print(f"Created graph: {graph.name}")
print(f"Workflow ID: {graph.workflow_id}")

# Create an agent node
agent_node = manager.create_node(
    NodeType.AGENT,
    "Chatbot Agent",
    position=Position(300, 200),
    description="A helpful chatbot"
)

# Add node to graph
manager.add_node_to_graph(graph.name, agent_node)

# Connect START node to agent
start_node = graph.nodes[0]  # START node created by default
manager.add_connection(
    graph.name,
    start_node.uniq_id,
    agent_node.uniq_id,
    connection_type=ConnectionType.WORKFLOW
)

# Create END node
end_node = manager.create_node(
    NodeType.END,
    "End",
    position=Position(300, 400)
)
manager.add_node_to_graph(graph.name, end_node)

# Connect agent to END
manager.add_connection(
    graph.name,
    agent_node.uniq_id,
    end_node.uniq_id,
    connection_type=ConnectionType.WORKFLOW
)

# Save the graph
success = manager.save_graph(graph)
print(f"Graph saved: {success}")
```

### Example 2: Agent with Tools

```python
from backend.services.graph import GraphManager
from backend.models.workflow import NodeType, Position, ConnectionType

manager = GraphManager()

# Create graph
graph = manager.create_graph(
    "research-assistant",
    "AI research assistant with web search"
)

# Create agent
agent_node = manager.create_node(
    NodeType.AGENT,
    "Research Agent",
    position=Position(300, 200),
    description="Conducts research using web search"
)
manager.add_node_to_graph(graph.name, agent_node)

# Create web search tool
web_search_tool = manager.create_node(
    NodeType.WEB_SEARCH,
    "Web Search",
    position=Position(300, 400)
)
manager.add_node_to_graph(graph.name, web_search_tool)

# Connect START to agent
start_node = graph.nodes[0]
manager.add_connection(
    graph.name,
    start_node.uniq_id,
    agent_node.uniq_id,
    connection_type=ConnectionType.WORKFLOW
)

# Connect web search tool to agent
manager.add_connection(
    graph.name,
    agent_node.uniq_id,
    web_search_tool.uniq_id,
    connection_type=ConnectionType.TOOL
)

# Validate graph
result = manager.validate_graph(graph.name)
if result["valid"]:
    print("Graph is valid!")
else:
    print("Validation errors:")
    for error in result["errors"]:
        print(f"  - {error}")

# Save graph
manager.save_graph(graph)
```

### Example 3: Multi-Agent Orchestrator Workflow

```python
from backend.services.graph import GraphManager
from backend.models.workflow import NodeType, Position, ConnectionType
import asyncio

async def create_multi_agent_workflow():
    """Create a complex multi-agent workflow with orchestrator."""
    manager = GraphManager()

    # Create graph
    graph = manager.create_graph(
        "customer-service",
        "Multi-agent customer service system"
    )

    # Create orchestrator agent
    orchestrator = manager.create_node(
        NodeType.AGENT,
        "Service Orchestrator",
        position=Position(300, 200),
        description="Routes customer requests to appropriate specialist"
    )
    manager.add_node_to_graph(graph.name, orchestrator)

    # Create specialist sub-agents
    billing_specialist = manager.create_sub_agent(
        graph.name,
        orchestrator.uniq_id,
        name="Billing Specialist",
        delegation_description="Expert in billing, payments, and invoices"
    )

    tech_specialist = manager.create_sub_agent(
        graph.name,
        orchestrator.uniq_id,
        name="Technical Specialist",
        delegation_description="Expert in technical issues and troubleshooting"
    )

    sales_specialist = manager.create_sub_agent(
        graph.name,
        orchestrator.uniq_id,
        name="Sales Specialist",
        delegation_description="Expert in product information and sales"
    )

    # Connect START to orchestrator
    start_node = graph.nodes[0]
    manager.add_connection(
        graph.name,
        start_node.uniq_id,
        orchestrator.uniq_id,
        connection_type=ConnectionType.WORKFLOW
    )

    # Add database query tool to billing specialist
    database_tool = manager.create_node(
        NodeType.DATABASE_QUERY,
        "Customer Database",
        position=Position(500, 400)
    )
    manager.add_node_to_graph(graph.name, database_tool)

    manager.add_connection(
        graph.name,
        billing_specialist.uniq_id,
        database_tool.uniq_id,
        connection_type=ConnectionType.TOOL
    )

    # Detect and configure orchestrators
    orch_count = manager.detect_and_configure_orchestrators(graph)
    print(f"Configured {orch_count} orchestrators")

    # Validate
    result = manager.validate_graph(graph.name)
    assert result["valid"], f"Validation failed: {result['errors']}"

    # Compile the graph
    compiled_agents = await manager.compile_graph(graph)
    print(f"Compiled {len(compiled_agents)} agents")

    # Save
    manager.save_graph(graph)

    print(f"Created workflow with {len(graph.nodes)} nodes")
    return graph

# Run the example
asyncio.run(create_multi_agent_workflow())
```

### Example 4: Testing with Graph Service

```python
import pytest
from backend.services.graph import GraphManager, NodeNotFoundError
from backend.models.workflow import NodeType, Position

def test_create_and_retrieve_graph():
    """Test basic graph creation and retrieval."""
    manager = GraphManager()

    # Create graph
    graph = manager.create_graph("test-graph", "Test workflow")

    assert graph.name == "test-graph"
    assert graph.description == "Test workflow"
    assert len(graph.nodes) == 1  # START node

    # Retrieve graph
    retrieved = manager.get_graph("test-graph")
    assert retrieved is not None
    assert retrieved.name == "test-graph"

def test_node_operations():
    """Test node creation, update, and deletion."""
    manager = GraphManager()
    graph = manager.create_graph("test-nodes", "Test node operations")

    # Create node
    agent_node = manager.create_node(
        NodeType.AGENT,
        "Test Agent",
        position=Position(100, 100)
    )

    assert agent_node.name == "Test Agent"
    assert agent_node.type == NodeType.AGENT

    # Add to graph
    success = manager.add_node_to_graph(graph.name, agent_node)
    assert success
    assert len(graph.nodes) == 2  # START + agent

    # Update node
    success = manager.update_node(
        graph.name,
        agent_node.uniq_id,
        {"name": "Updated Agent"}
    )
    assert success

    updated_node = graph.get_node_by_id(agent_node.uniq_id)
    assert updated_node.name == "Updated Agent"

    # Delete node
    success = manager.delete_node(graph.name, agent_node.uniq_id)
    assert success
    assert len(graph.nodes) == 1  # Only START remains

def test_connection_validation():
    """Test connection validation."""
    manager = GraphManager()
    graph = manager.create_graph("test-connections", "Test connections")

    # Create nodes
    agent = manager.create_node(NodeType.AGENT, "Agent")
    tool = manager.create_node(NodeType.TOOL, "Tool")

    manager.add_node_to_graph(graph.name, agent)
    manager.add_node_to_graph(graph.name, tool)

    # Valid connection: AGENT → TOOL
    from backend.models.workflow import ConnectionType
    success = manager.add_connection(
        graph.name,
        agent.uniq_id,
        tool.uniq_id,
        connection_type=ConnectionType.TOOL
    )
    assert success

    # Invalid connection should raise error
    condition = manager.create_node(NodeType.CONDITION, "Condition")
    manager.add_node_to_graph(graph.name, condition)

    from backend.services.graph import ConnectionValidationError
    with pytest.raises(ConnectionValidationError):
        # TOOL connections must originate from AGENT
        manager.add_connection(
            graph.name,
            condition.uniq_id,
            tool.uniq_id,
            connection_type=ConnectionType.TOOL
        )

def test_graph_validation():
    """Test graph validation."""
    manager = GraphManager()
    graph = manager.create_graph("test-validation", "Test validation")

    # Initially valid (has START node)
    result = manager.validate_graph(graph.name)
    assert result["valid"]

    # Add agent without LLM config
    agent = manager.create_node(NodeType.AGENT, "Invalid Agent")
    agent.agent_config = None  # Remove config
    manager.add_node_to_graph(graph.name, agent)

    result = manager.validate_graph(graph.name)
    # Should have validation errors
    assert not result["valid"]
    assert len(result["errors"]) > 0

@pytest.mark.asyncio
async def test_graph_compilation():
    """Test graph compilation."""
    manager = GraphManager()
    graph = manager.create_graph("test-compile", "Test compilation")

    # Create agent with proper config
    agent = manager.create_node(NodeType.AGENT, "Test Agent")
    manager.add_node_to_graph(graph.name, agent)

    # Compile graph
    try:
        compiled = await manager.compile_graph(graph)
        # Should return dict (may be empty if compilation not available)
        assert isinstance(compiled, dict)
    except Exception as e:
        # Compilation may fail if dependencies not available
        pytest.skip(f"Compilation not available: {e}")
```

## Performance Considerations

### Performance Characteristics

**Graph Operations:**

- `create_graph()`: O(1) - Creates graph object and START node
- `load_graph()`: O(n) - Database query + deserialisation of n nodes
- `save_graph()`: O(n) - Serialisation of n nodes + database write
- `list_graphs()`: O(m) - Database query for m graphs with pagination support
- `get_graph()`: O(1) - Dictionary lookup in active_graphs cache

**Node Operations:**

- `create_node()`: O(1) - Node creation and configuration
- `add_node_to_graph()`: O(1) - Append to list
- `update_node()`: O(n) - Linear search through nodes by ID
- `delete_node()`: O(n + c) - Node lookup + connection cleanup (c connections)

**Connection Operations:**

- `add_connection()`: O(n) - Node lookup + relationship updates
- `remove_connection()`: O(c) - Connection list filtering (c connections)

**Validation:**

- `validate_graph()`: O(n + c) - Iterates all nodes and connections
- `validate_agent_llm_config()`: O(1) - Configuration validation

**Compilation:**

- `compile_graph()`: O(a × t) - For a agents with t tools each
- `get_compiled_agent()`: O(1) - Dictionary lookup

**Memory Usage:**

- Each graph in `active_graphs` cache: ~10-100 KB depending on node count
- Compiled agents cache: ~50-500 KB per compiled agent with tools
- StateGraph compilation: ~100-1000 KB per compiled graph

**I/O Characteristics:**

- Database operations: I/O-bound (graph persistence, loading)
- Compilation: CPU-bound (agent compilation, tool binding)
- Validation: CPU-bound (graph traversal, configuration checks)
- Execution: Mixed (LLM API calls are I/O-bound, logic is CPU-bound)

### Optimisation Tips

#### Tip 1: Use Active Graph Cache

**Problem:**

```python
# Inefficient: Loads from database every time
for i in range(10):
    graph = manager.load_graph("my-workflow")
    # Do something with graph
```

**Solution:**

```python
# Efficient: Load once, use cached version
graph = manager.load_graph("my-workflow")  # Loads from DB

for i in range(10):
    # Subsequent calls use cached version
    cached_graph = manager.get_graph("my-workflow")  # O(1) lookup
    # Do something with cached_graph
```

#### Tip 2: Batch Node Operations

**Problem:**

```python
# Inefficient: Save after each node addition
for node_config in node_configs:
    node = manager.create_node(**node_config)
    manager.add_node_to_graph(graph.name, node)
    manager.save_graph(graph)  # Expensive database write each time
```

**Solution:**

```python
# Efficient: Batch operations and save once
for node_config in node_configs:
    node = manager.create_node(**node_config)
    manager.add_node_to_graph(graph.name, node)

# Save once at the end
manager.save_graph(graph)  # Single database write
```

#### Tip 3: Use Compilation for Repeated Executions

**Problem:**

```python
# Inefficient: Tools resolved at runtime for each execution
async def run_workflow_multiple_times():
    for i in range(100):
        # Tools resolved on each execution
        result = await execute_workflow(graph, user_input)
```

**Solution:**

```python
# Efficient: Pre-compile agents with tool bindings
async def run_workflow_multiple_times():
    # Compile once
    compiled_agents = await manager.compile_graph(graph)

    for i in range(100):
        # Uses pre-compiled agents with cached tool bindings
        result = await execute_workflow(graph, user_input)
```

#### Tip 4: Validate Before Heavy Operations

**Problem:**

```python
# Inefficient: Attempt compilation of invalid graph
compiled = await manager.compile_graph(invalid_graph)  # Fails after expensive work
```

**Solution:**

```python
# Efficient: Validate first (cheap), then compile
result = manager.validate_graph(graph.name)

if result["valid"]:
    # Only compile if valid
    compiled = await manager.compile_graph(graph)
else:
    print(f"Validation errors: {result['errors']}")
```

#### Tip 5: Use Lazy Compilation

**Problem:**

```python
# Inefficient: Compiles all graphs immediately on startup
manager = GraphManager(lazy_compile=False)  # Compiles all graphs

# Slow startup time
```

**Solution:**

```python
# Efficient: Compile on-demand when needed
manager = GraphManager(lazy_compile=True)  # Default

# Graphs compiled only when needed
result = await execute_workflow(graph, user_input)  # Compiles on first use
```

### Async/Await Support

The graph service provides async methods for long-running operations:

**Async Operations:**

```python
import asyncio
from backend.services.graph import GraphManager

async def async_workflow_operations():
    """Example of async operations."""
    manager = GraphManager()

    # Async graph compilation
    graph = manager.load_graph("my-workflow")
    compiled_agents = await manager.compile_graph(graph)

    # Async agent execution
    agent_node = graph.get_node_by_id("agent-123")
    response = await manager.execute_agent_async(
        agent_node,
        "User input message"
    )

    return response

# Run async operations
result = asyncio.run(async_workflow_operations())
```

**Concurrent Operations:**

```python
import asyncio
from backend.services.graph import GraphManager

async def compile_multiple_graphs():
    """Compile multiple graphs concurrently."""
    manager = GraphManager()

    graphs = [
        manager.load_graph("graph-1"),
        manager.load_graph("graph-2"),
        manager.load_graph("graph-3"),
    ]

    # Compile all graphs concurrently
    compilation_tasks = [
        manager.compile_graph(graph)
        for graph in graphs
    ]

    results = await asyncio.gather(*compilation_tasks)

    for i, compiled in enumerate(results):
        print(f"Graph {i+1}: {len(compiled)} agents compiled")

asyncio.run(compile_multiple_graphs())
```

### Connection Pooling

The graph service uses SQLAlchemy's connection pooling for database operations through the GraphStorageService.

**Connection Pool Configuration:**
Managed by the database service layer, not directly configured in graph service.

### Batch Operations

**Batch Node Creation:**

```python
def create_nodes_batch(manager, graph_name, node_configs):
    """Create multiple nodes efficiently."""
    nodes = []

    # Create all nodes first
    for config in node_configs:
        node = manager.create_node(
            config["type"],
            config["name"],
            position=Position(**config["position"])
        )
        nodes.append(node)

    # Add all nodes to graph
    for node in nodes:
        manager.add_node_to_graph(graph_name, node)

    # Single save operation
    graph = manager.get_graph(graph_name)
    manager.save_graph(graph)

    return nodes
```

**Batch Connection Creation:**

```python
def create_connections_batch(manager, graph_name, connection_configs):
    """Create multiple connections efficiently."""
    for conn in connection_configs:
        manager.add_connection(
            graph_name,
            conn["source_id"],
            conn["target_id"],
            connection_type=conn["type"]
        )

    # Auto-saved by add_connection, but could be optimised
    # by modifying ConnectionManager to batch saves
```

## Testing Patterns

### Unit Testing

**Basic Service Testing:**

```python
import pytest
from backend.services.graph import GraphManager, NodeManager
from backend.models.workflow import NodeType, Position

class TestNodeManager:
    """Test NodeManager service."""

    @pytest.fixture
    def node_manager(self):
        """Create NodeManager instance."""
        return NodeManager(model_service=None)

    def test_create_agent_node(self, node_manager):
        """Test creating an agent node."""
        node = node_manager.create_node(
            NodeType.AGENT,
            "Test Agent",
            position=Position(100, 100)
        )

        assert node.name == "Test Agent"
        assert node.type == NodeType.AGENT
        assert node.agent_config is not None
        assert node.position.x == 100
        assert node.position.y == 100

    def test_create_tool_node(self, node_manager):
        """Test creating a tool node."""
        node = node_manager.create_node(
            NodeType.TOOL,
            "Test Tool"
        )

        assert node.name == "Test Tool"
        assert node.type == NodeType.TOOL
        assert node.tool_config is not None

    def test_node_has_default_style(self, node_manager):
        """Test nodes receive default styling."""
        node = node_manager.create_node(NodeType.AGENT, "Agent")

        assert node.style is not None
        assert node.style.color == "#9C27B0"  # Purple for agents
```

**Testing with Fixtures:**

```python
import pytest
from backend.services.graph import GraphManager
from backend.models.workflow import NodeType, Position, ConnectionType

@pytest.fixture
def graph_manager():
    """Create GraphManager instance for testing."""
    return GraphManager(workspace_dir="./test_workspace")

@pytest.fixture
def sample_graph(graph_manager):
    """Create a sample graph for testing."""
    graph = graph_manager.create_graph(
        "test-graph",
        "Test workflow"
    )

    # Add an agent node
    agent = graph_manager.create_node(
        NodeType.AGENT,
        "Test Agent",
        position=Position(300, 200)
    )
    graph_manager.add_node_to_graph(graph.name, agent)

    return graph

def test_graph_has_start_node(sample_graph):
    """Test that created graphs have START node."""
    start_nodes = [n for n in sample_graph.nodes if n.type == NodeType.START]
    assert len(start_nodes) == 1

def test_add_connection_to_graph(graph_manager, sample_graph):
    """Test adding connections between nodes."""
    # Get START and agent nodes
    start_node = sample_graph.nodes[0]
    agent_node = sample_graph.nodes[1]

    # Add connection
    success = graph_manager.add_connection(
        sample_graph.name,
        start_node.uniq_id,
        agent_node.uniq_id,
        connection_type=ConnectionType.WORKFLOW
    )

    assert success
    assert len(sample_graph.connections) == 1
```

### Mocking Dependencies

**Mocking Model Service:**

```python
import pytest
from unittest.mock import Mock, MagicMock
from backend.services.graph import NodeManager
from backend.models.workflow import NodeType

def test_agent_node_with_default_deployment():
    """Test agent node creation with mocked model service."""
    # Mock model service
    mock_model_service = Mock()
    mock_model_service.get_default_deployment.return_value = {
        "id": "deployment-123",
        "provider": "openai",
        "model_name": "gpt-4",
        "name": "GPT-4 Default",
        "display_name": "GPT-4"
    }

    # Create node manager with mock
    node_manager = NodeManager(model_service=mock_model_service)

    # Create agent node
    node = node_manager.create_node(NodeType.AGENT, "Test Agent")

    # Verify default deployment was assigned
    assert node.agent_config.llm_config is not None
    assert node.agent_config.llm_config.provider == "openai"
    assert node.agent_config.llm_config.model_name == "gpt-4"

    # Verify mock was called
    mock_model_service.get_default_deployment.assert_called_once_with(
        model_type="llm"
    )
```

**Mocking Database Operations:**

```python
import pytest
from unittest.mock import patch, MagicMock
from backend.services.graph import GraphStorageService

@patch('backend.services.graph.storage.service.get_db_session')
def test_save_graph_with_mocked_db(mock_get_db):
    """Test graph save with mocked database."""
    # Mock database session
    mock_session = MagicMock()
    mock_get_db.return_value.__enter__.return_value = mock_session

    # Create test graph
    from backend.models.workflow import GraphData
    graph = GraphData(
        name="test-graph",
        description="Test"
    )

    # Save graph
    workflow_id = GraphStorageService.save_graph(
        graph,
        workspace_id="user@test.com",
        created_by="user@test.com"
    )

    # Verify database operations
    assert mock_session.add.called or mock_session.merge.called
    assert mock_session.commit.called
```

### Integration Testing

**Testing Full Workflow:**

```python
import pytest
import asyncio
from backend.services.graph import GraphManager
from backend.models.workflow import NodeType, Position, ConnectionType

@pytest.mark.integration
class TestGraphWorkflowIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_create_and_execute_workflow(self):
        """Test creating and executing a complete workflow."""
        manager = GraphManager()

        # Create workflow
        graph = manager.create_graph(
            "integration-test-workflow",
            "Integration test"
        )

        # Create agent
        agent = manager.create_node(
            NodeType.AGENT,
            "Test Agent",
            position=Position(300, 200)
        )
        manager.add_node_to_graph(graph.name, agent)

        # Connect START to agent
        start_node = graph.nodes[0]
        manager.add_connection(
            graph.name,
            start_node.uniq_id,
            agent.uniq_id,
            connection_type=ConnectionType.WORKFLOW
        )

        # Validate
        result = manager.validate_graph(graph.name)
        assert result["valid"], f"Validation failed: {result['errors']}"

        # Compile (if available)
        try:
            compiled = await manager.compile_graph(graph)
            print(f"Compiled {len(compiled)} agents")
        except Exception as e:
            pytest.skip(f"Compilation not available: {e}")

        # Save
        success = manager.save_graph(graph)
        assert success

        # Reload
        reloaded = manager.load_graph(graph.name)
        assert reloaded is not None
        assert reloaded.name == graph.name
        assert len(reloaded.nodes) == len(graph.nodes)
```

**Testing Database Persistence:**

```python
import pytest
from backend.services.graph import GraphManager, GraphStorageService

@pytest.mark.integration
@pytest.mark.database
class TestGraphPersistence:
    """Integration tests for database persistence."""

    def test_save_and_load_graph(self):
        """Test saving and loading graphs from database."""
        manager = GraphManager()

        # Create and save graph
        graph = manager.create_graph(
            "persistence-test",
            "Test persistence",
            username="test@example.com"
        )

        original_workflow_id = graph.workflow_id
        original_node_count = len(graph.nodes)

        # Clear active graphs to force load from DB
        manager.active_graphs.clear()

        # Load from database
        loaded = manager.load_graph(
            "persistence-test",
            username="test@example.com"
        )

        assert loaded is not None
        assert loaded.workflow_id == original_workflow_id
        assert len(loaded.nodes) == original_node_count

    def test_list_user_graphs(self):
        """Test listing graphs for a user."""
        # Create multiple graphs
        manager = GraphManager()

        graph1 = manager.create_graph("test-1", username="user@test.com")
        graph2 = manager.create_graph("test-2", username="user@test.com")

        # List graphs
        graphs = manager.list_graphs(username="user@test.com")

        # Should include both graphs
        graph_names = [g["name"] for g in graphs]
        assert "test-1" in graph_names
        assert "test-2" in graph_names
```

## Best Practices

### Do's

✅ **Use dependency injection to access GraphManager**

```python
from backend.services.dependency_injection import get_graph_manager

# Good: Use singleton instance
manager = get_graph_manager()

# Avoid: Creating multiple instances
# manager = GraphManager()  # Don't do this in production code
```

✅ **Validate graphs before execution**

```python
# Good: Validate first
result = manager.validate_graph("my-workflow")
if not result["valid"]:
    raise ValueError(f"Invalid graph: {result['errors']}")

# Then execute
await execute_workflow(graph, user_input)
```

✅ **Use batch operations for multiple changes**

```python
# Good: Batch operations, save once
for node_config in nodes:
    node = manager.create_node(**node_config)
    manager.add_node_to_graph(graph.name, node)

manager.save_graph(graph)  # Single save

# Avoid: Save after each operation
# for node_config in nodes:
#     node = manager.create_node(**node_config)
#     manager.add_node_to_graph(graph.name, node)
#     manager.save_graph(graph)  # Inefficient
```

✅ **Handle exceptions appropriately**

```python
# Good: Specific exception handling
from backend.services.graph import GraphNotFoundError, NodeNotFoundError

try:
    graph = manager.load_graph("my-workflow")
except GraphNotFoundError as e:
    logger.error(f"Graph not found: {e.graph_name}")
    return {"error": "Graph not found"}
```

✅ **Use type hints and proper models**

```python
# Good: Use proper types
from backend.models.workflow import NodeType, Position, ConnectionType

node = manager.create_node(
    NodeType.AGENT,  # Use enum
    "Agent Name",
    position=Position(100, 200)  # Use Position model
)
```

✅ **Pre-compile graphs for production**

```python
# Good: Pre-compile frequently used graphs
async def prepare_production_graphs():
    """Pre-compile graphs for production use."""
    manager = get_graph_manager()

    production_graphs = [
        "customer-support",
        "order-processing",
        "technical-support"
    ]

    for graph_name in production_graphs:
        graph = manager.load_graph(graph_name)
        if graph:
            await manager.compile_graph(graph)
            logger.info(f"Pre-compiled {graph_name}")
```

### Don'ts

❌ **Don't create nodes without adding them to graphs**

```python
# Bad: Created but never added
node = manager.create_node(NodeType.AGENT, "Orphan Agent")
# Node exists but isn't in any graph

# Good: Add to graph
node = manager.create_node(NodeType.AGENT, "Agent")
manager.add_node_to_graph(graph.name, node)
```

❌ **Don't skip validation**

```python
# Bad: Execute without validation
await execute_workflow(graph, user_input)  # Might fail at runtime

# Good: Validate first
result = manager.validate_graph(graph.name)
if result["valid"]:
    await execute_workflow(graph, user_input)
else:
    handle_validation_errors(result["errors"])
```

❌ **Don't ignore connection types**

```python
# Bad: Wrong connection type
manager.add_connection(
    graph.name,
    "agent-id",
    "tool-id",
    connection_type=ConnectionType.WORKFLOW  # Wrong!
)

# Good: Use correct connection type
manager.add_connection(
    graph.name,
    "agent-id",
    "tool-id",
    connection_type=ConnectionType.TOOL  # Correct
)
```

❌ **Don't modify graphs without saving**

```python
# Bad: Changes lost when process restarts
manager.add_node_to_graph(graph.name, node)
manager.add_connection(graph.name, source, target)
# No save! Changes lost

# Good: Save after modifications
manager.add_node_to_graph(graph.name, node)
manager.add_connection(graph.name, source, target)
manager.save_graph(graph)  # Persist changes
```

❌ **Don't create circular dependencies**

```python
# Bad: Creates infinite loop
manager.add_connection(graph.name, "node-a", "node-b")
manager.add_connection(graph.name, "node-b", "node-c")
manager.add_connection(graph.name, "node-c", "node-a")  # Circular!

# Good: Use validation to detect circles
result = manager.validate_graph(graph.name)
# Validation will catch circular dependencies
```

❌ **Don't access internal attributes directly**

```python
# Bad: Direct access to internal state
manager.graph_crud.active_graphs["my-graph"] = modified_graph

# Good: Use public API
manager.save_graph(modified_graph)
```

## Related Documentation

### Related Services

- [Execution Service](execution.md) - Workflow execution engine that uses graphs
- [Agent Service](agent.md) - Agent compilation and tool binding
- [LLM Models Service](llm_models.md) - LLM provider management for agent nodes
- [Model Deployment Service](model_deployment.md) - LLM deployment configuration
- [Delegation Service](delegation.md) - Agent delegation tool factory
- [Database Service](database.md) - Database session management
- [Workflow Service](workflow.md) - Workflow state and execution coordination

### Related API Modules

- [Graph API](../../../backend/api/graph/graph.md) - HTTP endpoints for graph operations
- [Workflow API](../../../backend/api/workflow/workflow.md) - Workflow execution endpoints
- [HTTP Execution API](../../../backend/api/http_execution/http_execution.md) - HTTP-triggered workflow execution

### Architecture Documentation

- [Service Layer Architecture](../architecture/service_layer.md) - Overall service architecture
- [Database Schema](../architecture/database_schema.md) - Database structure for graphs
- [Multi-Tenant Architecture](../architecture/multi_tenant.md) - Multi-tenancy implementation

### External Documentation

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) - LangGraph StateGraph reference
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation with Pydantic
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/) - Database ORM reference

## Summary

The graph service is the core workflow management system in AgenticStudio, providing comprehensive functionality for
creating, storing, validating, and executing visual workflow graphs. It serves as the foundation for the visual workflow
builder and execution engine.

The service is architected as a facade pattern with specialised service modules for different concerns: node management,
connection management, CRUD operations, orchestration, validation, compilation, and persistence. This modular design
enables clean separation of concerns while providing a unified API through the GraphManager facade.

The service integrates deeply with other AgenticStudio services including the execution engine (for running workflows), the
agent service (for compiling agents with tools), the LLM models service (for configuring agent LLMs), and the database
service (for multi-tenant persistence).

**Key Features:**

- Visual workflow graph creation and management
- Multi-node type support (agents, tools, conditions, subworkflows)
- Orchestrator pattern with sub-agent delegation
- Compile-time tool binding for performance
- Database persistence with version control
- Multi-tenant support with access control
- Graph validation and execution readiness checks
- LangGraph integration for execution

**Primary Use Cases:**

- Building visual agent workflows in the UI
- Creating multi-agent orchestrator systems
- Persisting and versioning workflow definitions
- Validating graph structure before execution
- Compiling workflows for optimised execution
- Managing workflow access across tenants

**When to Use This Service:**

- Building or modifying workflow graphs programmatically
- Creating workflow templates or presets
- Implementing custom workflow logic
- Testing workflow configurations
- Integrating with the visual workflow editor
- Executing agent-based workflows
- Managing workflow persistence and versioning
