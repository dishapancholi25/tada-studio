# Execution Service

## Overview

The execution service is AgenticStudio's core workflow orchestration system, responsible for executing LangGraph-based
workflows with support for checkpointing, pause/resume, async agent execution, and comprehensive state tracking. This
service acts as the central coordinator for all workflow executions, managing the complete lifecycle from initialisation
through streaming execution to finalisation.

**Location:** `backend/services/execution/`

**Primary Responsibilities:**

- Orchestrate LangGraph workflow execution with streaming and checkpoint support
- Manage async agent execution with tool calling, memory, and structured outputs
- Handle workflow pause/resume and checkpoint management
- Track execution state and history with database persistence
- Coordinate between nodes, conditions, and subgraph executions
- Provide real-time WebSocket notifications for execution events

**Key Use Cases:**

- Execute multi-step AI workflows with complex branching logic
- Pause workflows at checkpoints for human-in-the-loop interactions
- Resume workflows from saved checkpoints with new input
- Execute async agents with tool calling and memory management
- Track execution history and state for debugging and monitoring

## Architecture

### Module Structure

```
backend/services/execution/
├── __init__.py                      # Public API exports
├── engine.py                        # ExecutionEngine coordinator
├── workflow_executor.py             # WorkflowExecutor lifecycle management
├── resume_handler.py                # ResumeHandler checkpoint resumption
├── exceptions.py                    # Exception hierarchy
├── types.py                         # TypedDict definitions
├── logging.py                       # Structured logging utilities
├── checkpointer.py                  # PostgreSQL checkpointer initialisation
├── checkpoint_adapter.py            # Async checkpointer adapter
│
├── async_agent/                     # Async agent execution
│   ├── __init__.py                  # Async agent public API
│   ├── executor.py                  # AsyncAgentExecutor main class
│   ├── llm_builder.py               # LLM building and configuration
│   ├── memory_handler.py            # Memory management
│   ├── message_builder.py           # Message construction
│   ├── tool_executor.py             # Tool execution
│   ├── token_handler.py             # Token counting
│   ├── structured_output_handler.py # Structured output handling
│   ├── http_metadata_handler.py     # HTTP metadata extraction
│   ├── models.py                    # Data models
│   ├── exceptions.py                # Async agent exceptions
│   └── utils.py                     # Helper utilities
│
├── context/                         # Execution context management
│   ├── __init__.py                  # Context public API
│   ├── manager.py                   # ExecutionContext class
│   ├── store.py                     # Context variable storage
│   ├── utils.py                     # Context utility functions
│   ├── exceptions.py                # Context exceptions
│   └── testing.py                   # Testing utilities
│
├── checkpoint/                      # Checkpoint execution
│   ├── __init__.py                  # Checkpoint public API
│   ├── base.py                      # Base checkpoint executor
│   ├── manual.py                    # Manual checkpoint executor
│   ├── email.py                     # Email checkpoint executor
│   └── tracker.py                   # Checkpoint iteration tracker
│
├── state/                           # State tracking
│   ├── __init__.py                  # State tracking public API
│   ├── tracker.py                   # StateExecutionTracker
│   ├── models.py                    # State type definitions
│   ├── validators.py                # State validators
│   └── exceptions.py                # State tracking exceptions
│
├── paused/                          # Paused execution management
│   ├── __init__.py                  # Paused execution public API
│   ├── service.py                   # PausedExecutionService
│   ├── queries.py                   # Database queries
│   ├── models.py                    # Paused execution models
│   └── checkpoint_handler.py        # Checkpoint handler
│
├── history/                         # Execution history
│   ├── __init__.py                  # History public API
│   ├── service.py                   # ExecutionHistoryService
│   ├── graph_execution.py           # Graph execution tracking
│   ├── node_execution.py            # Node execution tracking
│   ├── queries.py                   # Database queries
│   ├── serialization.py             # Data serialisation
│   └── formatters/                  # Output formatters
│       ├── graph_formatter.py
│       └── node_formatter.py
│
├── nodes/                           # Node function factory
│   ├── __init__.py
│   └── factory.py                   # NodeFunctionFactory
│
└── agent/                           # Legacy agent execution (deprecated)
    └── ...                          # (Use async_agent instead)
```

### Design Patterns

#### 1. **Coordinator Pattern (ExecutionEngine)**

The `ExecutionEngine` acts as a slim coordinator that delegates to specialised service modules rather than containing
complex logic itself. This pattern ensures separation of concerns and makes the system highly testable and maintainable.

#### 2. **Factory Pattern (NodeFunctionFactory)**

Node functions are created dynamically using the factory pattern, allowing different node types to have different
execution strategies while maintaining a consistent interface.

#### 3. **Strategy Pattern (Checkpoint Executors)**

Different checkpoint types (manual, email) implement the same `CheckpointExecutor` interface, allowing the system to
handle various checkpoint strategies uniformly.

#### 4. **Context Manager Pattern (ExecutionContext)**

Execution context uses Python context managers (both sync and async) to ensure proper setup and teardown of execution
state, preventing resource leaks.

#### 5. **Dependency Injection**

Services receive their dependencies through constructor injection, making the system modular and testable:

```python
class ExecutionEngine:
    def __init__(self, graph_manager: GraphManager):
        self.graph_manager = graph_manager
        self.checkpointer = initialize_checkpointer()
        self.subgraph_builder = SubgraphBuilder(graph_manager)
        # ... more dependencies injected
```

#### 6. **Event Streaming**

Workflow execution uses LangGraph's streaming API to provide real-time updates via WebSocket notifications, enabling
progressive UI updates.

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                      ExecutionEngine                        │
│                   (Main Coordinator)                        │
└───────────────┬──────────────────────────┬──────────────────┘
                │                          │
    ┌───────────▼──────────┐    ┌─────────▼────────────┐
    │  WorkflowExecutor    │    │   ResumeHandler      │
    │  (Lifecycle Mgmt)    │    │  (Checkpoint Resume) │
    └───────────┬──────────┘    └──────────────────────┘
                │
    ┌───────────▼────────────────────────────────────────┐
    │              GraphBuilder                          │
    │         (Build LangGraph StateGraph)               │
    └───────────┬────────────────────────────────────────┘
                │
    ┌───────────▼──────────┬──────────────┬──────────────┐
    │                      │              │              │
┌───▼────────┐  ┌─────────▼──────┐  ┌────▼──────┐  ┌───▼──────┐
│AsyncAgent  │  │ Checkpoint     │  │  State    │  │ History  │
│Executor    │  │ Executors      │  │ Tracker   │  │ Service  │
└────────────┘  └────────────────┘  └───────────┘  └──────────┘
```

**Data Flow:**

1. API Layer → ExecutionEngine.execute_graph()
2. ExecutionEngine → WorkflowExecutor.execute()
3. WorkflowExecutor → GraphBuilder.build() → LangGraph StateGraph
4. StateGraph → Node Functions → Node Executors
5. Node Executors → AsyncAgentExecutor (for agent nodes)
6. State Updates → StateExecutionTracker
7. Events → ExecutionHistoryService (database)
8. Events → WebSocket Notifier (real-time updates)

### Dependencies

#### Internal Dependencies

**Core Services:**

- `backend.services.graph` - Graph management and building
- `backend.services.conditions` - Condition evaluation
- `backend.services.io` - Input/output processing
- `backend.services.nodes` - Node executors
- `backend.services.subgraph` - Subgraph execution
- `backend.services.checkpoint` - Checkpoint metadata
- `backend.services.workflow` - Workflow state and resumption
- `backend.services.websocket` - WebSocket notifications
- `backend.services.llm_models` - LLM factory
- `backend.services.model_deployment` - Model service

**Database:**

- `backend.models` - Database ORM models
- SQLAlchemy for database operations
- PostgreSQL for checkpoint persistence

#### External Dependencies

**LangGraph/LangChain:**

- `langgraph` - StateGraph, checkpointing, streaming
- `langchain_core` - Messages, tools, runnables
- `langchain_postgres` - PostgreSQL checkpointer

**Utilities:**

- `contextvars` - Thread-safe context management
- `asyncio` - Async execution
- `typing` - Type hints

#### Environment Variables

- `POSTGRES_CONNECTION_STRING` - Database connection (optional, auto-built if not provided)
- `POSTGRES_HOST` - Database host (default: "localhost")
- `POSTGRES_PORT` - Database port (default: 5432)
- `POSTGRES_USER` - Database user (default: "postgres")
- `POSTGRES_PASSWORD` - Database password (default: "postgres")
- `POSTGRES_DB` - Database name (default: "langgraph_db")

## Public API

### Exported Classes

**Engine:**

- `ExecutionEngine` - Main execution coordinator and orchestrator
- `WorkflowExecutor` - Workflow lifecycle management
- `ResumeHandler` - Checkpoint resumption handling

**Async Agent Execution:**

- `AsyncAgentExecutor` - Async agent execution orchestrator
- `AsyncExecutionConfig` - Configuration for async execution
- `AsyncExecutionResult` - Result from async execution
- `TokenCounts` - Token usage statistics
- `ToolExecutionRecord` - Tool execution tracking record

**Context Management:**

- `ExecutionContext` - Execution context manager with context manager support

**State Tracking:**

- `StateExecutionTracker` - State-based execution tracking

**Paused Execution:**

- `PausedExecutionService` - Service for managing paused executions

**Checkpointing:**

- `AsyncCheckpointerAdapter` - Adapter for async checkpointing

**Logging:**

- `ExecutionLogger` - Structured execution logging
- `timing_decorator` - Function timing decorator

### Exported Functions

**Engine Functions:**

- `initialize_executor(graph_manager)` - Initialise global execution engine
- `get_executor()` - Get the global execution engine instance

**Checkpointer Functions:**

- `initialize_checkpointer()` - Initialise PostgreSQL checkpointer
- `build_postgres_connection_string()` - Build connection string from env vars

**Async Agent Functions:**

- `create_async_agent_executor()` - Factory for creating AsyncAgentExecutor

**Context Functions:**

- `get_current_execution_id()` - Get current execution ID from context
- `get_current_db_execution_id()` - Get database execution ID from context
- `set_execution_context()` - Set execution context
- `clear_execution_context()` - Clear execution context

### Constants and Configuration

**Execution Configuration (TypedDict):**

```python
class ExecutionConfig(TypedDict, total=False):
    execution_id: str
    user_id: Optional[str]
    workflow_id: Optional[str]
    graph_definition_id: Optional[str]
    thread_id: Optional[str]
    checkpoint_id: Optional[str]
    enable_checkpointing: bool
    checkpoint_interval: int
    max_retries: int
    timeout_seconds: int
    enable_websocket: bool
    metadata: Dict[str, Any]
```

**Execution Status (Enum):**

```python
class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    WAITING_FOR_CHECKPOINT = "waiting_for_checkpoint"
```

### Exceptions

```
Exception
└── ExecutionError (base exception for all execution errors)
    ├── NodeExecutionError (node execution failures)
    ├── CheckpointError (checkpoint operation failures)
    │   └── CheckpointResumeError (checkpoint resume failures)
    ├── GraphBuildError (graph building failures)
    ├── ConditionEvaluationError (condition evaluation failures)
    ├── ValidationError (validation failures)
    └── TimeoutError (execution timeouts)

AsyncAgentExecutionError (async agent execution failures)
├── LLMBuildError (LLM building failures)
├── MemoryOperationError (memory operation failures)
├── MessageBuildError (message building failures)
├── StructuredOutputError (structured output failures)
├── TokenCountError (token counting failures)
└── ToolExecutionError (tool execution failures)

ExecutionContextError (context management failures)
├── ContextNotSetError (context not set when required)
├── ContextAlreadySetError (attempted to set already-active context)
└── ContextValidationError (context data validation failed)

StateTrackingError (state tracking failures)
├── InvalidExecutionOrderError (invalid execution order)
├── MissingStateKeyError (required state key missing)
├── InvalidStateStructureError (invalid state structure)
└── StateUpdateError (state update failed)
```

## Core Classes

### `ExecutionEngine`

The main execution coordinator that orchestrates all workflow execution services. This slim engine delegates to
specialised service modules rather than containing complex logic itself.

**Purpose:** Serve as the central orchestrator and dependency provider for all execution services.

**Responsibilities:**

- Initialise and coordinate all service components
- Provide public API surface for workflow execution
- Manage active execution state and history
- Build LangGraph StateGraphs from workflow definitions
- Register node executors for different node types

**Initialisation:**

```python
def __init__(
    self,
    graph_manager: GraphManager,
) -> None:
    """
    Initialise execution engine.

    Args:
        graph_manager: Graph manager for workflow definitions
    """
```

**Key Methods:**

#### `execute_graph()`

Execute a complete workflow graph with full lifecycle management.

```python
async def execute_graph(
    self,
    graph: GraphData,
    initial_input: Dict[str, Any],
    execution_id: str,
    user_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    graph_definition_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a workflow graph."""
```

**Parameters:**

- `graph` (GraphData) - The workflow graph definition
- `initial_input` (Dict[str, Any]) - Initial input data for the workflow
- `execution_id` (str) - Unique execution identifier (used as thread_id)
- `user_id` (Optional[str]) - User executing the graph
- `workflow_id` (Optional[str]) - Workflow UUID
- `graph_definition_id` (Optional[str]) - Graph definition UUID (for versioning)

**Returns:**

- `Dict[str, Any]` - Execution result with status, outputs, and metadata

**Raises:**

- `ExecutionError` - If execution fails
- `GraphBuildError` - If graph building fails
- `NodeExecutionError` - If a node execution fails

**Example:**

```python
from backend.services.execution import get_executor
from backend.services.graph import GraphManager

# Get the initialised executor
executor = get_executor()

# Execute a workflow
result = await executor.execute_graph(
    graph=workflow_graph,
    initial_input={"message": "Process this data"},
    execution_id="exec-123",
    user_id="user-456",
    workflow_id="workflow-789",
    graph_definition_id="def-abc",
)

# Check result
if result["status"] == "completed":
    print(f"Final output: {result['final_output']}")
elif result["status"] == "paused":
    print(f"Paused at checkpoint: {result['checkpoint_id']}")
```

**Behaviour:**

- Creates database execution record for tracking
- Registers execution in active_executions dict
- Sets execution context for sub-agent tracking
- Processes START node execution
- Builds and compiles LangGraph StateGraph with checkpointing
- Streams execution events in real-time
- Handles pause/resume at checkpoints
- Processes END node execution
- Sends WebSocket notifications for all events
- Updates database with final results

**Use Cases:**

- Execute user-initiated workflows via API
- Run scheduled workflows
- Execute workflows as part of subgraph operations

#### `resume_from_checkpoint()`

Resume workflow execution from a saved checkpoint with optional new input.

```python
async def resume_from_checkpoint(
    self,
    graph_name: str,
    thread_id: str,
    checkpoint_id: str,
    new_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resume execution from a checkpoint."""
```

**Parameters:**

- `graph_name` (str) - Name of the graph to resume
- `thread_id` (str) - Thread ID for the execution (same as original execution_id)
- `checkpoint_id` (str) - ID of the checkpoint to resume from
- `new_input` (Optional[Dict[str, Any]]) - New input to provide when resuming (e.g., user response)

**Returns:**

- `Dict[str, Any]` - Execution result (may pause again at another checkpoint)

**Raises:**

- `CheckpointResumeError` - If resume fails
- `ValueError` - If graph or checkpoint not found

**Example:**

```python
# Resume from a paused checkpoint with user input
result = await executor.resume_from_checkpoint(
    graph_name="customer-workflow",
    thread_id="exec-123",
    checkpoint_id="ckpt-456",
    new_input={"approval": "approved", "comments": "Looks good"},
)

if result["status"] == "completed":
    print("Workflow completed after resume")
elif result["status"] == "paused":
    print("Workflow paused again at another checkpoint")
```

**Behaviour:**

- Loads graph definition and checkpoint metadata
- Handles subworkflow checkpoint delegation if needed
- Creates new database execution record for resume
- Builds LangGraph app with checkpoint resumption
- Sends resume_started WebSocket notification
- Executes from checkpoint with streaming
- Handles potential re-pause at another checkpoint
- Finalises execution if completed

**Use Cases:**

- Resume manual checkpoints after human approval
- Resume email checkpoints after email response received
- Continue paused workflows with additional input

#### `get_execution_status()`

Get the current status of an active execution.

```python
def get_execution_status(
    self,
    execution_id: str,
) -> Optional[Dict[str, Any]]:
    """Get the current status of an execution."""
```

**Parameters:**

- `execution_id` (str) - Execution identifier

**Returns:**

- `Optional[Dict[str, Any]]` - Execution status dict or None if not found

**Example:**

```python
status = executor.get_execution_status("exec-123")
if status:
    print(f"Status: {status['status']}")
    print(f"Current node: {status['current_node_name']}")
    print(f"Started: {status['start_time']}")
```

#### `get_checkpoints()`

List all checkpoints for a given thread_id.

```python
def get_checkpoints(
    self,
    thread_id: str,
) -> List[Dict[str, Any]]:
    """List checkpoints for a given thread_id."""
```

**Parameters:**

- `thread_id` (str) - Thread identifier

**Returns:**

- `List[Dict[str, Any]]` - List of checkpoint dictionaries

**Example:**

```python
checkpoints = executor.get_checkpoints("exec-123")
for ckpt in checkpoints:
    print(f"Checkpoint: {ckpt['checkpoint_id']} at {ckpt['timestamp']}")
```

**Class Attributes:**

- `graph_manager: GraphManager` - Graph manager instance
- `active_executions: Dict[str, Dict[str, Any]]` - Dict of active execution states
- `execution_history: List[Dict[str, Any]]` - List of completed executions
- `checkpointer: PostgresSaver` - LangGraph PostgreSQL checkpointer
- `workflow_executor: WorkflowExecutor` - Workflow lifecycle executor
- `resume_handler: ResumeHandler` - Checkpoint resumption handler
- `graph_builder: GraphBuilder` - LangGraph StateGraph builder

**Properties:**
None (all attributes are public)

---

### `WorkflowExecutor`

Handles the complete workflow execution lifecycle, from initialisation through streaming execution to finalisation.

**Purpose:** Orchestrate all phases of workflow execution with proper separation of concerns.

**Responsibilities:**

- Initialise execution context and database tracking
- Process START and END node execution
- Build and compile LangGraph StateGraph
- Stream execution events with real-time updates
- Handle pause/resume at checkpoints
- Finalise execution with database updates and notifications

**Initialisation:**

```python
def __init__(
    self,
    engine: ExecutionEngine,
) -> None:
    """
    Initialise the WorkflowExecutor.

    Args:
        engine: The main execution engine instance
    """
```

**Key Methods:**

#### `execute()`

Execute a complete workflow graph through all lifecycle phases.

```python
async def execute(
    self,
    graph: GraphData,
    initial_input: Dict[str, Any],
    execution_id: str,
    user_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    graph_definition_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a complete workflow graph."""
```

**Parameters:**

- `graph` (GraphData) - The workflow graph definition
- `initial_input` (Dict[str, Any]) - Initial input data
- `execution_id` (str) - Unique execution identifier (thread_id)
- `user_id` (Optional[str]) - User executing the graph
- `workflow_id` (Optional[str]) - Workflow UUID
- `graph_definition_id` (Optional[str]) - Graph definition UUID

**Returns:**

- `Dict[str, Any]` - Execution result with status, outputs, and metadata

**Raises:**

- `ExecutionError` - If execution fails
- `asyncio.CancelledError` - If execution is cancelled

**Example:**

```python
# WorkflowExecutor is typically used internally by ExecutionEngine
executor = WorkflowExecutor(engine)
result = await executor.execute(
    graph=graph,
    initial_input={"message": "Hello"},
    execution_id="exec-123",
    user_id="user-456",
)
```

**Behaviour:**

- **Phase 1:** Initialise execution context and database record
- **Phase 2:** Process START node execution and tracking
- **Phase 3:** Build and compile LangGraph StateGraph
- **Phase 4:** Execute workflow with streaming
- **Phase 5:** Handle pause if workflow pauses at checkpoint
- **Phase 6:** Finalise execution with END node processing
- Always clears execution context in finally block

**Use Cases:**

- Internal execution orchestration by ExecutionEngine
- Testing workflow execution lifecycle

---

### `AsyncAgentExecutor`

Main orchestrator for asynchronous agent execution with LLM calling, tool execution, memory management, and token
counting.

**Purpose:** Coordinate all aspects of async agent execution by delegating to specialised handlers.

**Responsibilities:**

- Build LLM instances with proper configuration
- Manage conversation memory (load and store)
- Construct messages with system prompts and memory
- Execute tool calls and track usage
- Handle structured output parsing
- Count and report token usage
- Extract HTTP metadata from responses

**Initialisation:**

```python
def __init__(
    self,
    llm_factory: LLMFactory,
    model_service: ModelDeploymentService,
    get_tools_callback: Optional[callable] = None,
) -> None:
    """
    Initialise the async agent executor.

    Args:
        llm_factory: Factory for creating LLM instances
        model_service: Service for model deployment management
        get_tools_callback: Optional callback to get tools for an agent
            Signature: (tool_list, agent_config, agent_node_id) -> List[Tool]
    """
```

**Key Methods:**

#### `execute_agent()`

Execute an agent asynchronously with full orchestration of all execution steps.

```python
async def execute_agent(
    self,
    agent_node: EnhancedNodeData,
    user_message: str,
    config: Optional[AsyncExecutionConfig] = None,
    graph_name: Optional[str] = None,
) -> ExecutionResult:
    """Execute an agent asynchronously."""
```

**Parameters:**

- `agent_node` (EnhancedNodeData) - The agent node to execute
- `user_message` (str) - The user's message
- `config` (Optional[AsyncExecutionConfig]) - Execution configuration
- `graph_name` (Optional[str]) - Graph name for tool discovery

**Returns:**

- `ExecutionResult` - Result with response, token counts, and metadata

**Raises:**

- `AsyncAgentExecutionError` - If execution fails
- `LLMBuildError` - If LLM building fails

**Example:**

```python
from backend.services.execution.async_agent import (
    create_async_agent_executor,
    AsyncExecutionConfig,
)

# Create executor
executor = create_async_agent_executor(
    llm_factory=llm_factory,
    model_service=model_service,
    get_tools_callback=graph_manager.get_tools,
)

# Execute agent
config = AsyncExecutionConfig(
    db_execution_id=123,
    return_token_counts=True,
    enable_memory=True,
    memory_window_size=10,
)

result = await executor.execute_agent(
    agent_node=agent_node,
    user_message="Search for recent news about AI",
    config=config,
    graph_name="my-workflow",
)

# Access results
print(f"Response: {result.response}")
print(f"Tokens used: {result.token_counts.total_tokens}")
print(f"Tools called: {len(result.tool_executions)}")
```

**Behaviour:**

- Step 1: Validate and prepare agent configuration
- Step 2: Build LLM with proper settings (temperature, max_tokens, etc.)
- Step 3: Initialise token counting for the model
- Step 4: Load memory context if enabled
- Step 5: Get tools if not using structured output
- Step 6: Build messages with system prompt, memory, and user message
- Step 7: Count input tokens
- Step 8: Execute LLM (with tools or structured output)
- Step 9: Extract token metadata from response
- Step 10: Store memory if enabled
- Step 11: Build and return execution result

**Use Cases:**

- Execute agent nodes in workflows
- Run standalone agent queries
- Execute agents with tool calling
- Execute agents with structured output (JSON, Pydantic models)

---

### `ResumeHandler`

Handles resuming workflow execution from checkpoints, including subworkflow checkpoints and email checkpoint handling.

**Purpose:** Manage all aspects of checkpoint resumption with proper state restoration.

**Responsibilities:**

- Load graph and checkpoint metadata
- Handle subworkflow checkpoint delegation
- Resume execution with new input
- Process pause/interrupt events during resume
- Finalise execution after resume

**Initialisation:**

```python
def __init__(
    self,
    engine: ExecutionEngine,
) -> None:
    """
    Initialise the ResumeHandler.

    Args:
        engine: The main execution engine instance
    """
```

**Key Methods:**

#### `resume()`

Resume execution from a checkpoint with comprehensive state restoration.

```python
async def resume(
    self,
    graph_name: str,
    thread_id: str,
    checkpoint_id: str,
    new_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resume execution from a checkpoint."""
```

**Parameters:**

- `graph_name` (str) - Name of the graph to resume
- `thread_id` (str) - Thread ID for the execution
- `checkpoint_id` (str) - ID of the checkpoint to resume from
- `new_input` (Optional[Dict[str, Any]]) - New input to provide when resuming

**Returns:**

- `Dict[str, Any]` - Execution result with status, outputs, etc.

**Raises:**

- `ValueError` - If graph not found
- `CheckpointResumeError` - If resume fails

**Example:**

```python
# Resume from manual checkpoint
result = await resume_handler.resume(
    graph_name="approval-workflow",
    thread_id="exec-123",
    checkpoint_id="ckpt-456",
    new_input={"approved": True, "notes": "Approved by manager"},
)

# Resume from email checkpoint
result = await resume_handler.resume(
    graph_name="email-workflow",
    thread_id="exec-789",
    checkpoint_id="ckpt-abc",
    new_input={"email_response": "Yes, proceed with the order"},
)
```

**Behaviour:**

- Phase 1: Load and validate graph exists
- Phase 2: Check for subworkflow checkpoint and delegate if needed
- Phase 3: Initialise execution context for resume
- Phase 4: Build and compile graph with checkpointer
- Phase 5: Notify resume started via WebSocket
- Phase 6: Execute from checkpoint using LangGraph Command
- Phase 7: Handle pause if workflow pauses again
- Phase 8: Finalise execution if completed

**Use Cases:**

- Resume manual checkpoints after user approval/rejection
- Resume email checkpoints after email response received
- Resume subworkflow checkpoints
- Continue paused workflows with additional context

---

### `PausedExecutionService`

Service for managing paused workflow executions, providing business logic for querying, inspecting, and managing
workflows paused at checkpoints.

**Purpose:** Provide high-level operations for working with paused executions.

**Responsibilities:**

- Query paused executions by graph or globally
- Retrieve execution state and checkpoint information
- Provide pagination for large result sets
- Extract checkpoint details and context

**Initialisation:**

```python
def __init__(
    self,
    execution_engine: ExecutionEngine,
) -> None:
    """
    Initialise the paused execution service.

    Args:
        execution_engine: The execution engine instance
    """
```

**Key Methods:**

#### `get_paused_executions_by_graph()`

Get all paused executions for a specific graph with pagination.

```python
def get_paused_executions_by_graph(
    self,
    db: Session,
    graph_name: str,
    skip: int = 0,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get all paused executions for a specific graph."""
```

**Parameters:**

- `db` (Session) - Database session
- `graph_name` (str) - Name of the graph/workflow
- `skip` (int) - Number of records to skip (for pagination)
- `limit` (int) - Maximum number of records to return

**Returns:**

- `Dict[str, Any]` - Dictionary with paused execution summaries and pagination info

**Raises:**

- `Exception` - If database query fails

**Example:**

```python
from backend.services.execution import PausedExecutionService
from backend.services.database import get_db_session

service = PausedExecutionService(executor)
db = get_db_session()

# Get first page of paused executions
result = service.get_paused_executions_by_graph(
    db=db,
    graph_name="customer-approval",
    skip=0,
    limit=20,
)

for exec_summary in result["executions"]:
    print(f"Execution {exec_summary['id']} paused at {exec_summary['paused_at']}")
    print(f"  Checkpoint: {exec_summary['checkpoint_node_name']}")
    print(f"  Prompt: {exec_summary['checkpoint_prompt']}")

# Check pagination
if result["pagination"]["has_more"]:
    next_skip = result["pagination"]["next_skip"]
    # Fetch next page...
```

**Use Cases:**

- Display paused executions in admin dashboard
- List pending approvals for a workflow
- Monitor checkpoint usage and patterns

#### `get_all_paused_executions()`

Get all paused executions across all graphs.

```python
def get_all_paused_executions(
    self,
    db: Session,
) -> Dict[str, Any]:
    """Get all paused executions across all graphs."""
```

**Example:**

```python
result = service.get_all_paused_executions(db)

print(f"Total paused: {result['total_paused']}")
for graph_name, executions in result["by_graph"].items():
    print(f"{graph_name}: {len(executions)} paused")
```

---

### `StateExecutionTracker`

State-based execution tracking for LangGraph workflows, providing utilities for managing execution order and state
metadata.

**Purpose:** Provide state management utilities for tracking execution progress.

**Responsibilities:**

- Get and increment execution order from state
- Validate state structure
- Extract metadata safely
- Provide backward compatibility functions

**Usage:**

```python
from backend.services.execution.state import StateExecutionTracker

# Get execution order
order = StateExecutionTracker.get_execution_order(state)

# Increment execution order
state_update = StateExecutionTracker.increment_execution_order(state)

# Validate state structure
StateExecutionTracker.validate_state(state)
```

**Key Methods:**

#### `get_execution_order()`

Get the current execution order from state.

```python
@staticmethod
def get_execution_order(state: Dict[str, Any]) -> int:
    """Get execution order from state."""
```

#### `increment_execution_order()`

Increment execution order and return state update.

```python
@staticmethod
def increment_execution_order(state: Dict[str, Any]) -> Dict[str, Any]:
    """Increment execution order in state."""
```

**Example:**

```python
# In a node function
def my_node_function(state: WorkflowState):
    # Get current order
    current_order = StateExecutionTracker.get_execution_order(state)

    # Do work...

    # Return state update with incremented order
    return StateExecutionTracker.increment_execution_order(state)
```

---

### `ExecutionContext`

Dataclass for managing execution context with context manager support (both sync and async).

**Purpose:** Provide thread-safe execution context management across async boundaries.

**Responsibilities:**

- Store execution ID and database execution ID
- Manage execution data dictionary
- Support context manager protocol (with/async with)
- Ensure proper cleanup on exit

**Initialisation:**

```python
def __init__(
    self,
    execution_id: str,
    db_execution_id: Optional[int],
    execution_data: Dict[str, Any],
) -> None:
    """
    Initialise execution context.

    Args:
        execution_id: Unique execution identifier (thread_id)
        db_execution_id: Database execution record ID
        execution_data: Additional execution data
    """
```

**Example:**

```python
from backend.services.execution.context import ExecutionContext

# Use as context manager
async with ExecutionContext("exec-123", 456, {}) as ctx:
    # Context is active here
    await process_workflow()
# Context automatically cleared

# Manual management
from backend.services.execution.context import (
    set_execution_context,
    get_current_execution_id,
    clear_execution_context,
)

set_execution_context("exec-123", 456, {})
exec_id = get_current_execution_id()  # Returns "exec-123"
clear_execution_context()
```

**Use Cases:**

- Track execution context for sub-agent execution
- Maintain context across async boundaries
- Ensure proper cleanup of execution state

---

### `ExecutionLogger`

Structured logger for execution tracking with context management and consistent formatting.

**Purpose:** Provide structured logging with automatic context propagation.

**Responsibilities:**

- Log execution lifecycle events (start, end)
- Log node execution events (start, end)
- Log errors with context
- Log checkpoint creation
- Support context managers for automatic timing

**Initialisation:**

```python
def __init__(
    self,
    execution_id: str,
    user_id: Optional[str] = None,
) -> None:
    """
    Initialise execution logger.

    Args:
        execution_id: Unique execution identifier
        user_id: Optional user identifier
    """
```

**Example:**

```python
from backend.services.execution.logging import ExecutionLogger

logger = ExecutionLogger("exec-123", user_id="user-456")

# Log execution lifecycle
logger.log_execution_start("my-workflow", {"input": "data"})

# Log node execution
logger.log_node_start("node-1", "Agent Node", "AGENT")
# ... node execution ...
logger.log_node_end("node-1", {"output": "result"}, duration_seconds=1.5)

# Log completion
logger.log_execution_end("success", {"final": "output"}, duration_seconds=10.2)

# Use context manager
with logger.execution_context("my-workflow", {"input": "data"}):
    # Execute workflow - automatically logged
    pass
```

**Key Methods:**

#### `log_execution_start()`

```python
def log_execution_start(
    self,
    graph_name: str,
    initial_input: Dict[str, Any],
    workflow_id: Optional[str] = None,
) -> None:
```

#### `log_execution_end()`

```python
def log_execution_end(
    self,
    status: str,
    output: Any,
    duration_seconds: float,
    nodes_executed: int = 0,
) -> None:
```

#### `log_node_start()` / `log_node_end()`

```python
def log_node_start(
    self,
    node_id: str,
    node_name: str,
    node_type: str,
    input_data: Optional[Dict[str, Any]] = None,
) -> None:

def log_node_end(
    self,
    node_id: str,
    output: Dict[str, Any],
    duration_seconds: float,
) -> None:
```

#### `log_error()`

```python
def log_error(
    self,
    error: Exception,
    node_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> None:
```

---

## Functions

### `initialize_executor()`

Initialise the global execution engine instance.

**Signature:**

```python
def initialize_executor(
    graph_manager: GraphManager,
) -> ExecutionEngine:
    """Initialise the global execution engine."""
```

**Parameters:**

- `graph_manager` (GraphManager) - Graph manager for workflow definitions

**Returns:**

- `ExecutionEngine` - The initialised engine instance

**Example:**

```python
from backend.services.execution import initialize_executor
from backend.services.graph import GraphManager

graph_manager = GraphManager()
executor = initialize_executor(graph_manager)
```

**Use Cases:**

- Application startup initialisation
- Test setup

---

### `get_executor()`

Get the global execution engine instance.

**Signature:**

```python
def get_executor() -> ExecutionEngine:
    """Get the global execution engine."""
```

**Returns:**

- `ExecutionEngine` - The global engine instance

**Raises:**

- `RuntimeError` - If executor not initialised

**Example:**

```python
from backend.services.execution import get_executor

# Get executor (must be initialised first)
executor = get_executor()

# Execute workflow
result = await executor.execute_graph(
    graph=graph,
    initial_input={"message": "Hello"},
    execution_id="exec-123",
)
```

**Use Cases:**

- Access executor in API handlers
- Access executor in background tasks

---

### `initialize_checkpointer()`

Initialise PostgreSQL checkpointer for LangGraph persistence.

**Signature:**

```python
def initialize_checkpointer() -> PostgresSaver:
    """Initialise PostgreSQL checkpointer."""
```

**Returns:**

- `PostgresSaver` - Configured checkpointer instance

**Example:**

```python
from backend.services.execution import initialize_checkpointer

checkpointer = initialize_checkpointer()
```

**Behaviour:**

- Builds connection string from environment variables
- Creates PostgresSaver instance
- Sets up database schema if needed

**Use Cases:**

- Internal use by ExecutionEngine
- Testing checkpoint functionality

---

### `create_async_agent_executor()`

Factory function to create AsyncAgentExecutor with proper dependency injection.

**Signature:**

```python
def create_async_agent_executor(
    llm_factory: LLMFactory,
    model_service: ModelDeploymentService,
    get_tools_callback: Optional[callable] = None,
) -> AsyncAgentExecutor:
    """Factory function to create AsyncAgentExecutor."""
```

**Parameters:**

- `llm_factory` (LLMFactory) - Factory for creating LLM instances
- `model_service` (ModelDeploymentService) - Service for model deployment
- `get_tools_callback` (Optional[callable]) - Callback to get tools for an agent
  - Signature: `(tool_list, agent_config, agent_node_id) -> List[Tool]`

**Returns:**

- `AsyncAgentExecutor` - Configured executor instance

**Example:**

```python
from backend.services.execution.async_agent import create_async_agent_executor
from backend.services.llm_models import LLMFactory
from backend.services.model_deployment import ModelDeploymentService

# Create executor
executor = create_async_agent_executor(
    llm_factory=LLMFactory(),
    model_service=ModelDeploymentService(),
    get_tools_callback=lambda tools, config, node_id: tools,
)

# Use executor
result = await executor.execute_agent(
    agent_node=node,
    user_message="Hello",
)
```

**Use Cases:**

- Create async agent executors in node executors
- Testing async agent execution

---

### Context Management Functions

#### `set_execution_context()`

Set the execution context for the current async task.

**Signature:**

```python
def set_execution_context(
    execution_id: str,
    db_execution_id: Optional[int],
    execution_data: Dict[str, Any],
) -> None:
    """Set the execution context."""
```

**Parameters:**

- `execution_id` (str) - Unique execution identifier
- `db_execution_id` (Optional[int]) - Database execution ID
- `execution_data` (Dict[str, Any]) - Additional execution data

**Example:**

```python
from backend.services.execution.context import set_execution_context

set_execution_context("exec-123", 456, {"graph_name": "my-workflow"})
```

---

#### `get_current_execution_id()`

Get the current execution ID from context.

**Signature:**

```python
def get_current_execution_id() -> Optional[str]:
    """Get the current execution ID."""
```

**Returns:**

- `Optional[str]` - Execution ID or None if not set

**Example:**

```python
from backend.services.execution.context import get_current_execution_id

exec_id = get_current_execution_id()
if exec_id:
    print(f"Current execution: {exec_id}")
```

---

#### `clear_execution_context()`

Clear the execution context.

**Signature:**

```python
def clear_execution_context() -> None:
    """Clear the execution context."""
```

**Example:**

```python
from backend.services.execution.context import clear_execution_context

# Clean up context
clear_execution_context()
```

---

## Configuration

### Execution Configuration Models

#### `ExecutionConfig` (TypedDict)

Configuration for workflow execution.

```python
class ExecutionConfig(TypedDict, total=False):
    execution_id: str
    user_id: Optional[str]
    workflow_id: Optional[str]
    graph_definition_id: Optional[str]
    thread_id: Optional[str]
    checkpoint_id: Optional[str]
    enable_checkpointing: bool
    checkpoint_interval: int
    max_retries: int
    timeout_seconds: int
    enable_websocket: bool
    metadata: Dict[str, Any]
```

**Fields:**

- `execution_id` - Unique identifier for this execution
- `user_id` - User executing the workflow
- `workflow_id` - Workflow UUID
- `graph_definition_id` - Graph definition UUID (for versioning)
- `thread_id` - Thread ID for checkpointing (usually same as execution_id)
- `checkpoint_id` - Optional checkpoint to resume from
- `enable_checkpointing` - Whether to enable checkpointing (default: True)
- `checkpoint_interval` - How often to checkpoint in nodes (default: 1)
- `max_retries` - Maximum retry attempts for failed nodes (default: 0)
- `timeout_seconds` - Overall execution timeout (default: 300)
- `enable_websocket` - Whether to send WebSocket notifications (default: True)
- `metadata` - Additional metadata to track

#### `AsyncExecutionConfig` (Dataclass)

Configuration for async agent execution.

```python
@dataclass
class AsyncExecutionConfig:
    db_execution_id: Optional[int] = None
    return_token_counts: bool = False
    enable_memory: bool = False
    memory_window_size: int = 10
    tool_execution_tracker: Optional[List[ToolExecutionRecord]] = None
```

**Fields:**

- `db_execution_id` - Database execution ID for tracking (default: None)
- `return_token_counts` - Whether to return token usage stats (default: False)
- `enable_memory` - Whether to use conversation memory (default: False)
- `memory_window_size` - Number of messages to include from memory (default: 10)
- `tool_execution_tracker` - List to track tool executions (default: None)

### Environment Variables

#### Database Configuration

- `POSTGRES_CONNECTION_STRING` - Full PostgreSQL connection string (optional)
  - If not provided, built from individual components below
  - Example: `postgresql://user:pass@localhost:5432/dbname`

- `POSTGRES_HOST` - Database host (default: `"localhost"`)
- `POSTGRES_PORT` - Database port (default: `5432`)
- `POSTGRES_USER` - Database user (default: `"postgres"`)
- `POSTGRES_PASSWORD` - Database password (default: `"postgres"`)
- `POSTGRES_DB` - Database name (default: `"langgraph_db"`)

### Initialisation Patterns

#### Basic Initialisation

```python
from backend.services.execution import initialize_executor, get_executor
from backend.services.graph import GraphManager

# Initialise during application startup
graph_manager = GraphManager()
executor = initialize_executor(graph_manager)

# Later, access the executor
executor = get_executor()
```

#### Advanced Initialisation with Custom Configuration

```python
from backend.services.execution import ExecutionEngine
from backend.services.graph import GraphManager
import os

# Set custom database configuration
os.environ["POSTGRES_HOST"] = "db.example.com"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_USER"] = "workflow_user"
os.environ["POSTGRES_PASSWORD"] = "secure_password"
os.environ["POSTGRES_DB"] = "workflows"

# Initialise
graph_manager = GraphManager()
executor = ExecutionEngine(graph_manager)
```

#### Dependency Injection

The execution engine uses constructor-based dependency injection:

```python
# In FastAPI application startup
from fastapi import FastAPI
from backend.services.execution import initialize_executor
from backend.services.graph import GraphManager

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Initialise services on startup."""
    graph_manager = GraphManager()
    executor = initialize_executor(graph_manager)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    # Cleanup if needed
    pass
```

## Error Handling

### Exception Hierarchy

```
Exception
└── ExecutionError (base for all execution errors)
    ├── NodeExecutionError (node execution failures)
    │   └── (node_id, node_name, node_type attributes)
    │
    ├── CheckpointError (checkpoint operations)
    │   ├── checkpoint_id attribute
    │   ├── thread_id attribute
    │   ├── operation attribute (save, load, delete)
    │   └── CheckpointResumeError (resume-specific failures)
    │
    ├── GraphBuildError (graph building)
    │   ├── graph_name attribute
    │   ├── node_id attribute
    │   └── phase attribute (nodes, edges, conditions, compilation)
    │
    ├── ConditionEvaluationError (condition evaluation)
    │   ├── condition_type attribute
    │   ├── node_id attribute
    │   └── condition_config attribute
    │
    ├── ValidationError (validation failures)
    │   ├── validation_type attribute
    │   └── failed_checks attribute
    │
    └── TimeoutError (execution timeouts)
        ├── timeout_seconds attribute
        └── elapsed_seconds attribute

AsyncAgentExecutionError (async agent execution)
├── agent_name attribute
├── LLMBuildError (LLM building failures)
├── MemoryOperationError (memory failures)
├── MessageBuildError (message construction failures)
├── StructuredOutputError (structured output parsing failures)
├── TokenCountError (token counting failures)
└── ToolExecutionError (tool execution failures)

ExecutionContextError (context management)
├── ContextNotSetError (context not set when required)
├── ContextAlreadySetError (attempted to set already-active context)
└── ContextValidationError (context validation failed)

StateTrackingError (state tracking)
├── InvalidExecutionOrderError (invalid execution order)
├── MissingStateKeyError (required state key missing)
├── InvalidStateStructureError (invalid state structure)
└── StateUpdateError (state update failed)
```

### Exception Details

#### `ExecutionError`

Base exception for all execution-related errors.

**When raised:**

- Base class for more specific execution errors
- Rarely raised directly

**Attributes:**

- `message: str` - Human-readable error message
- `execution_id: Optional[str]` - Execution identifier where error occurred
- `context: Dict[str, Any]` - Additional context about the error
- `original_error: Optional[Exception]` - The original exception if wrapping

**Example:**

```python
from backend.services.execution import ExecutionError

try:
    result = await executor.execute_graph(...)
except ExecutionError as e:
    logger.error(f"Execution failed: {e}")
    logger.error(f"Execution ID: {e.execution_id}")
    logger.error(f"Context: {e.context}")
    if e.original_error:
        logger.error(f"Original error: {e.original_error}")
```

#### `NodeExecutionError`

Exception raised when a node execution fails.

**Inherits from:** `ExecutionError`

**When raised:**

- Node execution throws an exception
- Node configuration is invalid
- Node dependencies fail

**Attributes:**

- `node_id: str` - ID of the node that failed
- `node_name: str` - Name of the node that failed
- `node_type: str` - Type of the node (AGENT, HTTP_REQUEST, etc.)

**Example:**

```python
from backend.services.execution import NodeExecutionError

try:
    result = await executor.execute_graph(...)
except NodeExecutionError as e:
    logger.error(f"Node execution failed: {e.node_name} ({e.node_type})")
    logger.error(f"Node ID: {e.node_id}")

    # Handle specific node types differently
    if e.node_type == "AGENT":
        # Handle agent failure
        notify_admin(f"Agent node {e.node_name} failed")
    elif e.node_type == "HTTP_REQUEST":
        # Handle HTTP failure
        retry_http_request(e.node_id)
```

#### `CheckpointError` / `CheckpointResumeError`

Exceptions raised when checkpoint operations fail.

**Inherits from:** `ExecutionError`

**When raised:**

- Checkpoint save fails
- Checkpoint load fails
- Checkpoint not found
- Resume from checkpoint fails (CheckpointResumeError)

**Attributes:**

- `checkpoint_id: Optional[str]` - ID of the checkpoint
- `thread_id: Optional[str]` - Thread ID for checkpointing
- `operation: Optional[str]` - The operation that failed (save, load, delete, resume)

**Example:**

```python
from backend.services.execution import CheckpointResumeError

try:
    result = await executor.resume_from_checkpoint(
        graph_name="workflow",
        thread_id="exec-123",
        checkpoint_id="ckpt-456",
        new_input={"response": "approved"},
    )
except CheckpointResumeError as e:
    logger.error(f"Resume failed: {e}")
    logger.error(f"Checkpoint: {e.checkpoint_id}")
    logger.error(f"Thread: {e.thread_id}")

    # Notify user
    return {"error": "Failed to resume workflow", "details": str(e)}
```

#### `AsyncAgentExecutionError`

Exception raised when async agent execution fails.

**When raised:**

- Agent configuration is invalid
- LLM execution fails
- Tool execution fails
- Memory operations fail

**Attributes:**

- `agent_name: str` - Name of the agent that failed

**Example:**

```python
from backend.services.execution.async_agent import (
    AsyncAgentExecutionError,
    LLMBuildError,
    ToolExecutionError,
)

try:
    result = await executor.execute_agent(agent_node, user_message)
except LLMBuildError as e:
    logger.error(f"LLM build failed: {e}")
    # Return fallback response
    return {"response": "LLM unavailable, please try again"}
except ToolExecutionError as e:
    logger.error(f"Tool execution failed: {e}")
    # Continue without tool result
    pass
except AsyncAgentExecutionError as e:
    logger.error(f"Agent execution failed: {e.agent_name}")
    raise
```

### Error Handling Patterns

#### Recommended Error Handling Pattern

```python
from backend.services.execution import (
    get_executor,
    ExecutionError,
    NodeExecutionError,
    CheckpointError,
    TimeoutError,
    ValidationError,
)
from backend.services.config import get_logger

logger = get_logger(__name__)

async def execute_workflow(
    graph_name: str,
    input_data: Dict[str, Any],
    execution_id: str,
) -> Dict[str, Any]:
    """Execute workflow with comprehensive error handling."""

    executor = get_executor()

    try:
        # Load graph
        graph = executor.graph_manager.get_graph(graph_name)
        if not graph:
            return {
                "status": "failed",
                "error": "Graph not found",
                "error_type": "validation",
            }

        # Execute workflow
        result = await executor.execute_graph(
            graph=graph,
            initial_input=input_data,
            execution_id=execution_id,
        )

        return result

    except ValidationError as e:
        # Handle validation errors
        logger.error(f"Validation error: {e}")
        return {
            "status": "failed",
            "error": "Invalid configuration",
            "error_type": "validation",
            "details": str(e),
        }

    except TimeoutError as e:
        # Handle timeout errors
        logger.error(f"Execution timeout: {e}")
        return {
            "status": "failed",
            "error": "Execution timeout",
            "error_type": "timeout",
            "timeout_seconds": e.timeout_seconds,
            "elapsed_seconds": e.elapsed_seconds,
        }

    except NodeExecutionError as e:
        # Handle node execution errors
        logger.error(f"Node execution failed: {e}")
        return {
            "status": "failed",
            "error": f"Node {e.node_name} failed",
            "error_type": "node_execution",
            "node_id": e.node_id,
            "node_type": e.node_type,
            "details": str(e),
        }

    except CheckpointError as e:
        # Handle checkpoint errors
        logger.error(f"Checkpoint error: {e}")
        return {
            "status": "failed",
            "error": "Checkpoint operation failed",
            "error_type": "checkpoint",
            "operation": e.operation,
            "details": str(e),
        }

    except ExecutionError as e:
        # Handle general execution errors
        logger.error(f"Execution error: {e}")
        return {
            "status": "failed",
            "error": "Execution failed",
            "error_type": "execution",
            "details": str(e),
        }

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": "Unexpected error",
            "error_type": "unexpected",
            "details": str(e),
        }
```

#### Async Agent Error Handling

```python
from backend.services.execution.async_agent import (
    create_async_agent_executor,
    AsyncAgentExecutionError,
    LLMBuildError,
    MemoryOperationError,
    ToolExecutionError,
)

async def execute_agent_with_fallback(
    agent_node,
    user_message: str,
) -> Dict[str, Any]:
    """Execute agent with fallback handling."""

    executor = create_async_agent_executor(
        llm_factory=llm_factory,
        model_service=model_service,
    )

    try:
        result = await executor.execute_agent(
            agent_node=agent_node,
            user_message=user_message,
        )
        return {"success": True, "response": result.response}

    except LLMBuildError as e:
        # LLM unavailable, use fallback
        logger.error(f"LLM build failed: {e}")
        return {
            "success": False,
            "error": "LLM unavailable",
            "fallback_response": "I'm temporarily unavailable. Please try again.",
        }

    except MemoryOperationError as e:
        # Memory failed, continue without memory
        logger.warning(f"Memory operation failed: {e}")
        # Retry without memory
        config = AsyncExecutionConfig(enable_memory=False)
        result = await executor.execute_agent(
            agent_node=agent_node,
            user_message=user_message,
            config=config,
        )
        return {"success": True, "response": result.response, "memory_disabled": True}

    except ToolExecutionError as e:
        # Tool failed, return partial result
        logger.error(f"Tool execution failed: {e}")
        return {
            "success": False,
            "error": "Tool execution failed",
            "details": str(e),
        }

    except AsyncAgentExecutionError as e:
        # General agent error
        logger.error(f"Agent execution failed: {e}")
        return {
            "success": False,
            "error": "Agent execution failed",
            "details": str(e),
        }
```

## Integration Patterns

### Integration with API Layer

The execution service is typically accessed from FastAPI route handlers:

```python
# backend/api/execution/routes.py
from fastapi import APIRouter, Depends, HTTPException
from backend.services.execution import get_executor, ExecutionError
from backend.api.execution.models import ExecuteWorkflowRequest, ExecuteWorkflowResponse

router = APIRouter()

@router.post("/execute")
async def execute_workflow(
    request: ExecuteWorkflowRequest,
) -> ExecuteWorkflowResponse:
    """Execute a workflow via API."""

    try:
        executor = get_executor()

        # Load graph
        graph = executor.graph_manager.get_graph(request.graph_name)
        if not graph:
            raise HTTPException(status_code=404, detail="Graph not found")

        # Execute
        result = await executor.execute_graph(
            graph=graph,
            initial_input=request.input_data,
            execution_id=request.execution_id,
            user_id=request.user_id,
            workflow_id=request.workflow_id,
        )

        return ExecuteWorkflowResponse(**result)

    except ExecutionError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/resume")
async def resume_execution(
    graph_name: str,
    thread_id: str,
    checkpoint_id: str,
    new_input: Dict[str, Any],
) -> ExecuteWorkflowResponse:
    """Resume a paused workflow."""

    executor = get_executor()

    result = await executor.resume_from_checkpoint(
        graph_name=graph_name,
        thread_id=thread_id,
        checkpoint_id=checkpoint_id,
        new_input=new_input,
    )

    return ExecuteWorkflowResponse(**result)
```

### Integration with Other Services

#### Graph Service Integration

```python
from backend.services.execution import get_executor
from backend.services.graph import GraphManager

# Execution engine uses graph manager
executor = get_executor()
graph = executor.graph_manager.get_graph("my-workflow")

# Graph builder builds LangGraph StateGraph
state_graph = executor.graph_builder.build(graph, execution_id, db_execution_id)
```

#### WebSocket Integration

```python
from backend.services.execution import get_executor
from backend.services.websocket import notifier as ws_notifier

# Execution engine sends WebSocket notifications
await ws_notifier.on_execution_started(execution_id, data)
await ws_notifier.on_node_start(execution_id, node_id, node_name, node_type)
await ws_notifier.on_node_complete(execution_id, node_id, node_name, output)
await ws_notifier.on_execution_complete(execution_id, result)
await ws_notifier.on_execution_paused(execution_id, checkpoint_info)
```

#### Database Integration

```python
from backend.services.execution.history import ExecutionHistoryService
from backend.services.database import get_db_session

# Create execution record
db_execution = ExecutionHistoryService.create_graph_execution(
    graph_id=graph.name,
    graph_name=graph.name,
    graph_definition=asdict(graph),
    input_data=initial_input,
    user_id=user_id,
    thread_id=execution_id,
    workflow_id=workflow_id,
)

# Create node execution
node_exec = ExecutionHistoryService.create_node_execution(
    graph_execution_id=db_execution["id"],
    node_id=node.uniq_id,
    node_name=node.name,
    node_type=node.type.value,
    execution_order=execution_order,
    input_data=input_data,
)

# Update execution status
ExecutionHistoryService.update_graph_execution(
    execution_id=db_execution["id"],
    status="completed",
    output_data=result,
)
```

### Dependency Flow

```
API Layer (FastAPI routes)
    ↓
ExecutionEngine (get_executor())
    ↓
WorkflowExecutor / ResumeHandler
    ↓
GraphBuilder → StateGraph
    ↓
Node Functions
    ↓
Node Executors (AgentNodeExecutor, HttpNodeExecutor, etc.)
    ↓
AsyncAgentExecutor (for agent nodes)
    ↓
LLM Services, Tool Services, Memory Services
```

**Services that depend on execution:**

- API layer (`backend.api.execution`)
- Background task runners
- Workflow testing utilities

**Services that execution depends on:**

- Graph service (graph management)
- LLM services (model execution)
- Tool services (tool calling)
- Memory services (conversation memory)
- Database services (persistence)
- WebSocket services (notifications)

### Common Integration Patterns

#### Pattern 1: API Endpoint with Execution

```python
from fastapi import APIRouter, BackgroundTasks
from backend.services.execution import get_executor

router = APIRouter()

@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow_api(
    workflow_id: str,
    input_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
):
    """Execute workflow via API with background processing."""

    executor = get_executor()
    execution_id = generate_execution_id()

    # Execute in background
    background_tasks.add_task(
        execute_workflow_background,
        executor,
        workflow_id,
        input_data,
        execution_id,
    )

    return {
        "execution_id": execution_id,
        "status": "started",
        "message": "Workflow execution started",
    }

async def execute_workflow_background(
    executor,
    workflow_id: str,
    input_data: Dict[str, Any],
    execution_id: str,
):
    """Background task for workflow execution."""

    graph = executor.graph_manager.get_graph_by_id(workflow_id)

    result = await executor.execute_graph(
        graph=graph,
        initial_input=input_data,
        execution_id=execution_id,
    )

    # Send notification on completion
    await notify_completion(execution_id, result)
```

#### Pattern 2: Workflow with Checkpoints

```python
async def workflow_with_approval():
    """Execute workflow that pauses for approval."""

    executor = get_executor()

    # First execution - will pause at checkpoint
    result = await executor.execute_graph(
        graph=approval_workflow_graph,
        initial_input={"request": "Purchase order for $10,000"},
        execution_id="exec-123",
    )

    if result["status"] == "paused":
        # Workflow paused at approval checkpoint
        checkpoint_id = result["checkpoint_id"]
        thread_id = result["thread_id"]

        # Wait for approval (in real app, this would be via API callback)
        approval_response = await wait_for_approval(checkpoint_id)

        # Resume with approval response
        final_result = await executor.resume_from_checkpoint(
            graph_name=approval_workflow_graph.name,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            new_input=approval_response,
        )

        return final_result

    return result
```

#### Pattern 3: Agent Execution in Workflow

```python
# In a node executor
from backend.services.execution.async_agent import create_async_agent_executor

class AgentNodeExecutor:
    async def execute(self, node, state, graph, execution_id):
        """Execute agent node."""

        # Create async agent executor
        agent_executor = create_async_agent_executor(
            llm_factory=self.llm_factory,
            model_service=self.model_service,
            get_tools_callback=self.graph_manager.get_tools,
        )

        # Execute agent
        config = AsyncExecutionConfig(
            enable_memory=node.agent_config.use_memory,
            return_token_counts=True,
        )

        result = await agent_executor.execute_agent(
            agent_node=node,
            user_message=state["original_message"],
            config=config,
            graph_name=graph.name,
        )

        # Return state update
        return {
            "node_outputs": {
                node.uniq_id: {
                    "raw": result.response,
                    "token_counts": result.token_counts,
                }
            }
        }
```

## Usage Examples

### Example 1: Basic Workflow Execution

Complete end-to-end example of executing a simple workflow:

```python
from backend.services.execution import get_executor
from backend.services.graph import GraphManager
from backend.models.workflow import GraphData, NodeData, EdgeData, NodeType

async def execute_simple_workflow():
    """Execute a simple workflow with agent and HTTP nodes."""

    # Get executor
    executor = get_executor()

    # Define workflow graph
    graph = GraphData(
        name="simple-workflow",
        nodes=[
            NodeData(
                uniq_id="start-1",
                name="Start",
                type=NodeType.START,
            ),
            NodeData(
                uniq_id="agent-1",
                name="Research Agent",
                type=NodeType.AGENT,
                agent_config={
                    "model": "gpt-4",
                    "system_prompt": "You are a research assistant.",
                    "temperature": 0.7,
                },
            ),
            NodeData(
                uniq_id="http-1",
                name="Send Results",
                type=NodeType.HTTP_REQUEST_ACTION,
                http_config={
                    "url": "https://api.example.com/results",
                    "method": "POST",
                },
            ),
            NodeData(
                uniq_id="end-1",
                name="End",
                type=NodeType.END,
            ),
        ],
        edges=[
            EdgeData(source="start-1", target="agent-1"),
            EdgeData(source="agent-1", target="http-1"),
            EdgeData(source="http-1", target="end-1"),
        ],
    )

    # Execute workflow
    result = await executor.execute_graph(
        graph=graph,
        initial_input={
            "message": "Research the latest AI developments",
            "user_message": "Research the latest AI developments",
        },
        execution_id="exec-simple-001",
        user_id="user-123",
    )

    # Check result
    if result["status"] == "completed":
        print("Workflow completed successfully!")
        print(f"Final output: {result['final_output']}")
        print(f"Node outputs: {result['node_outputs']}")
    else:
        print(f"Workflow failed: {result.get('error')}")

    return result
```

### Example 2: Workflow with Checkpoint and Resume

Complete example showing workflow pause and resume:

```python
from backend.services.execution import get_executor
from backend.models.workflow import NodeType

async def workflow_with_checkpoint_example():
    """Execute workflow with manual checkpoint and resume."""

    executor = get_executor()

    # Define workflow with checkpoint
    graph = GraphData(
        name="approval-workflow",
        nodes=[
            NodeData(uniq_id="start-1", name="Start", type=NodeType.START),
            NodeData(
                uniq_id="agent-1",
                name="Analyse Request",
                type=NodeType.AGENT,
                agent_config={
                    "model": "gpt-4",
                    "system_prompt": "Analyse the purchase request.",
                },
            ),
            NodeData(
                uniq_id="checkpoint-1",
                name="Approval Required",
                type=NodeType.CHECKPOINT,
                checkpoint_config={
                    "type": "manual",
                    "prompt": "Please review and approve the purchase request",
                },
            ),
            NodeData(
                uniq_id="agent-2",
                name="Process Approval",
                type=NodeType.AGENT,
                agent_config={
                    "model": "gpt-4",
                    "system_prompt": "Process the approval decision.",
                },
            ),
            NodeData(uniq_id="end-1", name="End", type=NodeType.END),
        ],
        edges=[
            EdgeData(source="start-1", target="agent-1"),
            EdgeData(source="agent-1", target="checkpoint-1"),
            EdgeData(source="checkpoint-1", target="agent-2"),
            EdgeData(source="agent-2", target="end-1"),
        ],
    )

    # Step 1: Execute workflow (will pause at checkpoint)
    print("Step 1: Starting workflow execution...")
    result = await executor.execute_graph(
        graph=graph,
        initial_input={
            "message": "Purchase request for 10 laptops at $15,000",
        },
        execution_id="exec-approval-001",
        user_id="user-123",
    )

    # Check if paused
    if result["status"] == "paused":
        print(f"Workflow paused at checkpoint: {result['paused_node_name']}")
        print(f"Prompt: {result['prompt']}")
        print(f"Checkpoint ID: {result['checkpoint_id']}")

        # Step 2: Simulate approval process
        # In real app, this would wait for user action via API
        import asyncio
        await asyncio.sleep(2)  # Simulate waiting

        # Step 3: Resume with approval decision
        print("\nStep 3: Resuming with approval...")
        approval_input = {
            "approval_decision": "approved",
            "approval_notes": "Purchase approved by manager",
            "approved_by": "manager-456",
        }

        final_result = await executor.resume_from_checkpoint(
            graph_name=graph.name,
            thread_id=result["thread_id"],
            checkpoint_id=result["checkpoint_id"],
            new_input=approval_input,
        )

        if final_result["status"] == "completed":
            print("Workflow completed after approval!")
            print(f"Final output: {final_result['final_output']}")
            return final_result

    return result
```

### Example 3: Async Agent Execution with Tools

Complete example showing async agent execution with tool calling:

```python
from backend.services.execution.async_agent import (
    create_async_agent_executor,
    AsyncExecutionConfig,
)
from backend.services.llm_models import LLMFactory
from backend.services.model_deployment import ModelDeploymentService
from backend.models.workflow import EnhancedNodeData, AgentConfig

async def async_agent_with_tools_example():
    """Execute async agent with tool calling."""

    # Create async agent executor
    executor = create_async_agent_executor(
        llm_factory=LLMFactory(),
        model_service=ModelDeploymentService(),
        get_tools_callback=lambda tools, config, node_id: tools,
    )

    # Define agent node with tools
    agent_node = EnhancedNodeData(
        uniq_id="agent-search",
        name="Search Agent",
        type=NodeType.AGENT,
        agent_config=AgentConfig(
            model="gpt-4",
            system_prompt="You are a helpful research assistant with access to web search.",
            temperature=0.7,
            max_tokens=2000,
            tools=["web_search", "calculator"],
        ),
    )

    # Configure execution
    config = AsyncExecutionConfig(
        db_execution_id=None,
        return_token_counts=True,
        enable_memory=False,
        tool_execution_tracker=[],  # Will track tool calls
    )

    # Execute agent
    print("Executing agent with tools...")
    result = await executor.execute_agent(
        agent_node=agent_node,
        user_message="What are the latest developments in quantum computing? Calculate 2^10.",
        config=config,
        graph_name="research-workflow",
    )

    # Display results
    print(f"\nAgent Response:\n{result.response}\n")

    if result.token_counts:
        print(f"Token Usage:")
        print(f"  Input tokens: {result.token_counts.input_tokens}")
        print(f"  Output tokens: {result.token_counts.output_tokens}")
        print(f"  Total tokens: {result.token_counts.total_tokens}")
        print(f"  Model: {result.token_counts.model}\n")

    if result.tool_executions:
        print(f"Tool Executions ({len(result.tool_executions)}):")
        for tool_exec in result.tool_executions:
            print(f"  - {tool_exec.tool_name}")
            print(f"    Input: {tool_exec.tool_input}")
            print(f"    Output: {tool_exec.tool_output[:100]}...")

    return result
```

### Example 4: Complete Workflow with Error Handling

Show a realistic, complete workflow with proper error handling:

```python
from backend.services.execution import (
    get_executor,
    ExecutionError,
    NodeExecutionError,
    TimeoutError,
)
from backend.services.database import get_db_session
from backend.services.config import get_logger

logger = get_logger(__name__)

async def complete_workflow_with_error_handling(
    graph_name: str,
    input_data: Dict[str, Any],
    user_id: str,
) -> Dict[str, Any]:
    """
    Complete workflow execution example with comprehensive error handling.

    This example shows:
    - Loading graph from database
    - Executing with proper error handling
    - Handling different failure scenarios
    - Logging and monitoring
    - Cleanup on errors
    """

    executor = get_executor()
    execution_id = f"exec-{datetime.now().timestamp()}"

    logger.info(f"Starting workflow execution: {execution_id}")

    try:
        # Step 1: Load and validate graph
        logger.info(f"Loading graph: {graph_name}")
        graph = executor.graph_manager.get_graph(graph_name)

        if not graph:
            logger.error(f"Graph not found: {graph_name}")
            return {
                "status": "failed",
                "error": "Graph not found",
                "error_type": "validation",
            }

        # Step 2: Validate input data
        required_fields = ["message"]
        missing_fields = [f for f in required_fields if f not in input_data]

        if missing_fields:
            logger.error(f"Missing required fields: {missing_fields}")
            return {
                "status": "failed",
                "error": f"Missing required fields: {', '.join(missing_fields)}",
                "error_type": "validation",
            }

        # Step 3: Execute workflow
        logger.info(f"Executing graph: {graph_name}")
        result = await executor.execute_graph(
            graph=graph,
            initial_input=input_data,
            execution_id=execution_id,
            user_id=user_id,
        )

        # Step 4: Handle different result statuses
        if result["status"] == "completed":
            logger.info(f"Workflow completed successfully: {execution_id}")

            # Store final output in database
            db = get_db_session()
            store_workflow_output(db, execution_id, result["final_output"])

            return {
                "success": True,
                "execution_id": execution_id,
                "status": "completed",
                "output": result["final_output"],
            }

        elif result["status"] == "paused":
            logger.info(f"Workflow paused at checkpoint: {execution_id}")

            return {
                "success": True,
                "execution_id": execution_id,
                "status": "paused",
                "checkpoint_id": result["checkpoint_id"],
                "thread_id": result["thread_id"],
                "prompt": result.get("prompt"),
                "message": "Workflow paused for user input",
            }

        else:
            logger.warning(f"Workflow returned unexpected status: {result['status']}")
            return {
                "success": False,
                "execution_id": execution_id,
                "status": result["status"],
                "error": result.get("error", "Unknown error"),
            }

    except TimeoutError as e:
        logger.error(f"Workflow execution timeout: {execution_id}", exc_info=True)

        return {
            "success": False,
            "execution_id": execution_id,
            "status": "failed",
            "error": "Workflow execution timed out",
            "error_type": "timeout",
            "timeout_seconds": e.timeout_seconds,
        }

    except NodeExecutionError as e:
        logger.error(
            f"Node execution failed: {e.node_name} ({e.node_type})",
            exc_info=True,
        )

        # Send alert for critical nodes
        if e.node_type == "AGENT":
            await send_alert(
                f"Agent node failed in workflow {graph_name}",
                {"node_name": e.node_name, "error": str(e)},
            )

        return {
            "success": False,
            "execution_id": execution_id,
            "status": "failed",
            "error": f"Node {e.node_name} failed",
            "error_type": "node_execution",
            "node_id": e.node_id,
            "node_name": e.node_name,
            "node_type": e.node_type,
            "details": str(e),
        }

    except ExecutionError as e:
        logger.error(f"Workflow execution error: {execution_id}", exc_info=True)

        return {
            "success": False,
            "execution_id": execution_id,
            "status": "failed",
            "error": "Workflow execution failed",
            "error_type": "execution",
            "details": str(e),
        }

    except Exception as e:
        logger.error(f"Unexpected error in workflow: {execution_id}", exc_info=True)

        # Send alert for unexpected errors
        await send_alert(
            f"Unexpected error in workflow {graph_name}",
            {"execution_id": execution_id, "error": str(e)},
        )

        return {
            "success": False,
            "execution_id": execution_id,
            "status": "failed",
            "error": "Unexpected error occurred",
            "error_type": "unexpected",
            "details": str(e),
        }

    finally:
        # Cleanup
        logger.info(f"Cleaning up execution: {execution_id}")
        # Cleanup code here if needed

async def send_alert(message: str, context: Dict[str, Any]):
    """Send alert to monitoring system."""
    # Implementation would send to monitoring/alerting system
    pass

def store_workflow_output(db, execution_id: str, output: Any):
    """Store workflow output in database."""
    # Implementation would store in database
    pass
```

### Example 5: Testing Workflow Execution

Show how to test workflow execution:

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
from backend.services.execution import ExecutionEngine
from backend.services.graph import GraphManager

@pytest.mark.asyncio
async def test_workflow_execution():
    """Test basic workflow execution."""

    # Setup
    graph_manager = Mock(spec=GraphManager)
    graph_manager.get_graph = Mock(return_value=create_test_graph())

    executor = ExecutionEngine(graph_manager)

    # Execute
    result = await executor.execute_graph(
        graph=create_test_graph(),
        initial_input={"message": "Test input"},
        execution_id="test-exec-1",
        user_id="test-user",
    )

    # Assert
    assert result["status"] == "completed"
    assert "final_output" in result
    assert "node_outputs" in result

@pytest.mark.asyncio
async def test_workflow_pause_resume():
    """Test workflow pause and resume."""

    executor = ExecutionEngine(graph_manager)

    # First execution - should pause
    result = await executor.execute_graph(
        graph=create_checkpoint_graph(),
        initial_input={"message": "Test"},
        execution_id="test-exec-2",
    )

    assert result["status"] == "paused"
    assert "checkpoint_id" in result

    # Resume execution
    final_result = await executor.resume_from_checkpoint(
        graph_name=create_checkpoint_graph().name,
        thread_id=result["thread_id"],
        checkpoint_id=result["checkpoint_id"],
        new_input={"approval": "approved"},
    )

    assert final_result["status"] == "completed"

@pytest.mark.asyncio
async def test_async_agent_execution():
    """Test async agent execution."""

    from backend.services.execution.async_agent import create_async_agent_executor

    # Mock dependencies
    llm_factory = Mock()
    model_service = Mock()

    executor = create_async_agent_executor(
        llm_factory=llm_factory,
        model_service=model_service,
    )

    # Execute
    agent_node = create_test_agent_node()
    result = await executor.execute_agent(
        agent_node=agent_node,
        user_message="Test message",
    )

    # Assert
    assert result.response is not None
    assert isinstance(result.metadata, dict)

def create_test_graph():
    """Create a test graph."""
    # Implementation
    pass

def create_checkpoint_graph():
    """Create a graph with checkpoint."""
    # Implementation
    pass

def create_test_agent_node():
    """Create a test agent node."""
    # Implementation
    pass
```

## Performance Considerations

### Performance Characteristics

**Execution Engine:**

- **Graph building:** O(n + e) where n=nodes, e=edges
- **State updates:** O(1) dictionary operations
- **Checkpoint operations:** O(1) database writes (indexed by thread_id)

**Async Agent Execution:**

- **LLM calls:** Network I/O bound (depends on model provider)
- **Tool execution:** Varies by tool (HTTP requests, database queries, etc.)
- **Memory operations:** O(n) where n=window size (typically 10-20 messages)
- **Token counting:** O(m) where m=message length

**State Tracking:**

- **Execution order tracking:** O(1) state lookups
- **State validation:** O(1) structure checks

**Database Operations:**

- **Execution record creation:** O(1) single INSERT
- **Node execution tracking:** O(1) per node INSERT/UPDATE
- **Checkpoint list:** O(log n) with index on thread_id

### Optimisation Tips

#### Tip 1: Use Checkpoint Batching

**Problem:**

```python
# Creates checkpoint on every node
for node in nodes:
    execute_node(node)  # Checkpoint after each
```

**Solution:**

```python
# Configure checkpoint interval
config = ExecutionConfig(
    checkpoint_interval=5,  # Checkpoint every 5 nodes instead
)
```

#### Tip 2: Minimise State Size

**Problem:**

```python
# Storing large data in state
state_update = {
    "node_outputs": {
        node_id: {
            "raw": huge_response_data,  # 10MB of data
            "all_intermediate_results": [...],  # Unnecessary data
        }
    }
}
```

**Solution:**

```python
# Store only necessary data, save large data separately
state_update = {
    "node_outputs": {
        node_id: {
            "raw": response_summary,  # Just summary
            "data_ref": "s3://bucket/exec-123/node-1.json",  # Reference
        }
    }
}
```

#### Tip 3: Use Memory Window Size

**Problem:**

```python
# Loading entire conversation history
config = AsyncExecutionConfig(
    enable_memory=True,
    memory_window_size=1000,  # Loads 1000 messages!
)
```

**Solution:**

```python
# Use reasonable window size
config = AsyncExecutionConfig(
    enable_memory=True,
    memory_window_size=10,  # Just recent context
)
```

#### Tip 4: Parallel Node Execution

When using custom workflows, design graphs to allow parallel execution:

**Sequential (Slow):**

```
START → Node A → Node B → Node C → END
```

**Parallel (Fast):**

```
       ┌→ Node A →┐
START →├→ Node B →├→ END
       └→ Node C →┘
```

### Async/Await Support

The execution service is fully async-native:

```python
from backend.services.execution import get_executor

# All main methods are async
executor = get_executor()

# Execute workflow (async)
result = await executor.execute_graph(...)

# Resume from checkpoint (async)
result = await executor.resume_from_checkpoint(...)

# Async agent execution
from backend.services.execution.async_agent import create_async_agent_executor

agent_executor = create_async_agent_executor(...)
result = await agent_executor.execute_agent(...)
```

**Concurrent Execution:**

```python
import asyncio

# Execute multiple workflows concurrently
results = await asyncio.gather(
    executor.execute_graph(graph1, input1, "exec-1"),
    executor.execute_graph(graph2, input2, "exec-2"),
    executor.execute_graph(graph3, input3, "exec-3"),
)
```

### Connection Pooling

**Database Connection Pooling:**
The PostgreSQL checkpointer uses connection pooling automatically:

```python
from langchain_postgres import PostgresSaver
from psycopg_pool import ConnectionPool

# Checkpointer uses connection pool internally
checkpointer = PostgresSaver(
    sync_connection=connection_string,
    # Pool configuration handled by LangChain
)
```

**HTTP Connection Pooling:**
For HTTP requests in nodes, use session pooling:

```python
import aiohttp

# Create session with connection pooling
async with aiohttp.ClientSession() as session:
    # Reuse connections
    async with session.get(url) as response:
        data = await response.json()
```

### Batch Operations

**Batch Execution History Updates:**

```python
# Instead of individual updates
for node in nodes:
    ExecutionHistoryService.create_node_execution(...)

# Consider batching if available
ExecutionHistoryService.create_node_executions_batch([...])
```

## Best Practices

### Do's

✅ **Use execution context for sub-agent tracking**

```python
from backend.services.execution.context import ExecutionContext

async with ExecutionContext(execution_id, db_execution_id, {}):
    # Context automatically available to sub-agents
    await execute_workflow()
```

✅ **Always use try/finally to clear context**

```python
from backend.services.execution.context import (
    set_execution_context,
    clear_execution_context,
)

try:
    set_execution_context(execution_id, db_execution_id, {})
    await execute_workflow()
finally:
    clear_execution_context()  # Always cleanup
```

✅ **Handle paused status explicitly**

```python
result = await executor.execute_graph(...)

if result["status"] == "paused":
    # Save checkpoint info for later resume
    save_checkpoint_info(
        checkpoint_id=result["checkpoint_id"],
        thread_id=result["thread_id"],
    )
elif result["status"] == "completed":
    # Process completion
    process_result(result["final_output"])
```

✅ **Use structured error handling**

```python
from backend.services.execution import (
    NodeExecutionError,
    CheckpointError,
    ExecutionError,
)

try:
    result = await executor.execute_graph(...)
except NodeExecutionError as e:
    # Handle specific node failure
    logger.error(f"Node {e.node_name} failed: {e}")
except CheckpointError as e:
    # Handle checkpoint failure
    logger.error(f"Checkpoint failed: {e}")
except ExecutionError as e:
    # Handle general execution error
    logger.error(f"Execution failed: {e}")
```

✅ **Configure async agent execution appropriately**

```python
from backend.services.execution.async_agent import AsyncExecutionConfig

config = AsyncExecutionConfig(
    return_token_counts=True,  # Track token usage
    enable_memory=True,  # Use conversation memory
    memory_window_size=10,  # Reasonable window
)

result = await executor.execute_agent(agent_node, message, config)
```

✅ **Use execution logger for structured logging**

```python
from backend.services.execution.logging import ExecutionLogger

logger = ExecutionLogger(execution_id, user_id)

with logger.execution_context(graph_name, initial_input):
    # Automatically logs start/end with timing
    await execute_workflow()
```

### Don'ts

❌ **Don't forget to clear execution context**

```python
# BAD: Context never cleared
set_execution_context(execution_id, db_execution_id, {})
await execute_workflow()
# Context still set! Memory leak!

# GOOD: Always clear
try:
    set_execution_context(execution_id, db_execution_id, {})
    await execute_workflow()
finally:
    clear_execution_context()
```

❌ **Don't assume execution always completes**

```python
# BAD: Assumes completed
result = await executor.execute_graph(...)
output = result["final_output"]  # May not exist if paused!

# GOOD: Check status
result = await executor.execute_graph(...)
if result["status"] == "completed":
    output = result["final_output"]
elif result["status"] == "paused":
    handle_pause(result)
```

❌ **Don't store sensitive data in state**

```python
# BAD: Storing secrets in state
state_update = {
    "api_keys": {"openai": "sk-..."},  # Stored in checkpoint!
}

# GOOD: Use secure storage
state_update = {
    "api_key_ref": "secret-manager://openai-key",  # Reference
}
```

❌ **Don't catch all exceptions without logging**

```python
# BAD: Swallows errors
try:
    result = await executor.execute_graph(...)
except Exception:
    pass  # Lost all error information!

# GOOD: Log and handle appropriately
try:
    result = await executor.execute_graph(...)
except Exception as e:
    logger.error(f"Execution failed: {e}", exc_info=True)
    raise  # Re-raise or handle appropriately
```

❌ **Don't use large memory window sizes**

```python
# BAD: Loads too much history
config = AsyncExecutionConfig(
    enable_memory=True,
    memory_window_size=1000,  # Way too large!
)

# GOOD: Use reasonable window
config = AsyncExecutionConfig(
    enable_memory=True,
    memory_window_size=10,  # Recent context only
)
```

❌ **Don't ignore checkpoint failures**

```python
# BAD: Assumes resume always works
result = await executor.resume_from_checkpoint(...)
# Didn't check if resume succeeded

# GOOD: Handle resume failures
try:
    result = await executor.resume_from_checkpoint(...)
    if result["status"] == "failed":
        handle_resume_failure(result)
except CheckpointResumeError as e:
    logger.error(f"Resume failed: {e}")
    notify_user("Failed to resume workflow")
```

## Related Documentation

### Related Services

- [Graph Service](./graph.md) - Graph management and building
- [Agent Service](./agent.md) - Agent compilation and configuration
- [Memory Service](./memory.md) - Conversation memory management
- [Checkpoint Service](./checkpoint.md) - Checkpoint metadata management
- [Workflow Service](./workflow.md) - Workflow state and publishing
- [Database Service](./database.md) - Database operations

### Related API Modules

- [Execution API](../agents-guide/api/execution.md) - HTTP endpoints for execution
- [Checkpoint API](../agents-guide/api/checkpoints.md) - Checkpoint management endpoints
- [Graph API](../agents-guide/api/graph.md) - Graph management endpoints

### Architecture Documentation

- [System Architecture](../architecture/system.md) - Overall system design
- [LangGraph Integration](../architecture/langgraph.md) - LangGraph usage patterns
- [State Management](../architecture/state.md) - State management patterns

### External Documentation

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) - LangGraph framework
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction) - LangChain library

## Summary

The Execution Service is the core orchestration system for AgenticStudio, providing comprehensive workflow execution
capabilities with LangGraph integration. It handles the complete lifecycle of workflow execution from initialisation
through streaming execution to finalisation, with robust support for checkpointing, pause/resume, and async agent
execution.

The service is architected with a slim coordinator pattern where the `ExecutionEngine` delegates to specialised service
modules (`WorkflowExecutor`, `ResumeHandler`, `AsyncAgentExecutor`, etc.) rather than containing complex logic itself.
This design ensures high testability, maintainability, and clear separation of concerns.

Key architectural features include dependency injection for modularity, context managers for proper resource cleanup,
event streaming for real-time updates, and comprehensive error handling with a well-structured exception hierarchy. The
service integrates seamlessly with PostgreSQL for checkpoint persistence, WebSocket notifications for real-time updates,
and the LangGraph framework for stateful workflow execution.

**Key Features:**

- Complete workflow lifecycle management with LangGraph StateGraph execution
- Checkpoint-based pause/resume for human-in-the-loop workflows
- Async agent execution with tool calling, memory, and structured outputs
- Real-time WebSocket notifications for execution events
- Database persistence for execution history and checkpoints
- Thread-safe execution context management across async boundaries
- Comprehensive error handling with structured exceptions
- State tracking and validation utilities
- Structured logging with automatic context propagation

**Primary Use Cases:**

- Execute multi-step AI workflows with complex branching and conditions
- Pause workflows for human approval or input via checkpoints
- Resume paused workflows from saved state with new input
- Execute agents with tool calling and conversation memory
- Track execution history and state for monitoring and debugging
- Integrate workflow execution into API endpoints and background tasks

**When to Use This Service:**

- Building AI workflow applications that need orchestration
- Implementing approval workflows with human-in-the-loop
- Creating conversational agents with memory and tools
- Executing long-running workflows with checkpoint persistence
- Providing real-time workflow status updates to users
- Building testable, maintainable workflow systems
