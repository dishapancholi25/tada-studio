# Workflow Service

## Overview

The workflow service module provides comprehensive workflow lifecycle management for LangGraph-based workflows in
AgenticStudio. It handles workflow publication (exposing workflows as HTTP endpoints), subworkflow checkpoint resumption,
and state management for workflow execution.

**Location:** `backend/services/workflow/`

**Primary Responsibilities:**

- Publishing workflows as authenticated HTTP endpoints
- Managing workflow access control, rate limiting, and CORS
- Resuming subworkflow executions from checkpoints
- Defining LangGraph state schemas with custom reducer functions
- Providing state constants for workflow control flow

**Key Use Cases:**

- Publishing internal workflows as public or authenticated APIs
- Resuming paused subworkflows to completion
- Managing structured state flow through LangGraph workflows
- Tracking workflow execution metadata and results

## Table of Contents

1. [Architecture](#architecture)
2. [Public API](#public-api)
3. [Publishing Submodule](#publishing-submodule)
4. [Resumption Submodule](#resumption-submodule)
5. [State Submodule](#state-submodule)
6. [Integration Patterns](#integration-patterns)
7. [Usage Examples](#usage-examples)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)
10. [Related Documentation](#related-documentation)

---

## Architecture

### Module Structure

```
backend/services/workflow/
├── __init__.py                     # Root package (minimal exports)
├── publishing/                      # Workflow publication services
│   ├── __init__.py                 # Exports: WorkflowPublishingService
│   ├── service.py                  # Core publishing service
│   ├── responses.py                # Response builders and URL formatting
│   ├── helpers.py                  # Graph loading and validation helpers
│   └── legacy.py                   # Legacy token compatibility
├── resumption/                      # Subworkflow checkpoint resumption
│   ├── __init__.py                 # Exports: SubworkflowResumeHandler
│   ├── handler.py                  # Main resumption handler
│   ├── checkpoint_loader.py        # Checkpoint and graph loading
│   ├── state_extractor.py          # Result extraction utilities
│   ├── subworkflow_executor.py     # Subworkflow execution logic
│   └── utils.py                    # Logging and utility functions
└── state/                           # LangGraph state management
    ├── __init__.py                 # Exports: State schemas, reducers, constants
    ├── schemas.py                  # TypedDict state definitions
    ├── reducers.py                 # Custom reducer functions
    └── constants.py                # Special node identifiers
```

### Design Patterns

**1. Service Layer Pattern**

- Publishing service provides static methods for database persistence
- Resumption handler encapsulates checkpoint resumption logic
- Separation of concerns between state definition and execution

**2. Helper Functions Pattern**

- Helper modules (`responses.py`, `helpers.py`, `utils.py`) provide focused utilities
- Separation of response formatting from business logic
- Reusable validation and loading functions

**3. TypedDict State Pattern**

- State schemas use TypedDict with Annotated types for LangGraph integration
- Custom reducer functions control state merge behaviour
- Immutable constants for special node identifiers

**4. Composition Pattern**

- Resumption handler composes checkpoint loader, state extractor, and executor
- Each component handles a specific aspect of resumption
- Clean separation enables testing and reuse

### Dependencies

**Internal Dependencies:**

- `backend.services.database` - Database session management
- `backend.services.graph` - Graph loading and management
- `backend.services.subgraph` - Subworkflow graph building
- `backend.services.config` - Configuration and logging
- `backend.services.checkpoint` - Checkpoint metadata management
- `backend.models` - Database models (PublishedWorkflow, Workflow, etc.)

**External Dependencies:**

- `langgraph` - State management and workflow execution
- `langchain_core` - Message types for conversation handling
- `sqlalchemy` - Database ORM queries
- `typing_extensions` - TypedDict support

**Database Dependencies:**

- `published_workflows` table - Published workflow configuration
- `workflows` table - Workflow definitions
- `workflow_memberships` table - Access control
- `workflow_access_logs` table - Access logging

**Environment Variables:**

- None directly (configuration handled by `backend.services.config`)

---

## Public API

### Publishing Submodule

**Exported Classes:**

- `WorkflowPublishingService` - Database service for workflow publishing

**Key Methods:**

- `publish_workflow()` - Publish or update workflow publication
- `unpublish_workflow()` - Unpublish a workflow
- `get_published_workflow_by_identifier()` - Get published workflow by ID or slug
- `list_published_workflows_for_user()` - List user-accessible published workflows
- `log_access()` - Log access to published workflow

**Helper Functions:**

- `build_endpoint_url()` - Build HTTP endpoint URL
- `load_graph()` - Load graph from memory or disk
- `validate_graph_for_publishing()` - Validate graph is ready for publishing

### Resumption Submodule

**Exported Classes:**

- `SubworkflowResumeHandler` - Handles subworkflow checkpoint resumption

**Key Methods:**

- `resume_subworkflow_checkpoint()` - Resume subworkflow from checkpoint
- `complete_parent_workflow()` - Complete parent workflow with subworkflow result

**Helper Classes:**

- `CheckpointLoader` - Load graphs and nodes from checkpoints
- `SubworkflowExecutor` - Build and execute subworkflows

### State Submodule

**Exported TypedDicts:**

- `WorkflowState` - Main LangGraph state schema
- `NodeOutput` - Node execution output structure
- `NodeResult` - Execution history entry
- `WorkflowMetadata` - Execution metadata tracking
- `MemoryContext` - Conversation memory context
- `OrchestrationContext` - Orchestrator delegation context

**Exported Reducer Functions:**

- `last_value_reducer()` - Keep last non-None value
- `merge_node_outputs()` - Merge node output dictionaries
- `merge_metadata()` - Merge metadata dictionaries
- `max_execution_order()` - Take maximum execution order
- `merge_results()` - Concatenate result lists

**Exported Constants:**

- `ENTRY_POINT` - `"__start__"` - LangGraph entry node
- `EXIT_POINT` - `"__end__"` - LangGraph exit node
- `INTERRUPT_POINT` - `"__interrupt__"` - Human-in-the-loop pause
- `ERROR_POINT` - `"__error__"` - Error handling identifier

---

## Publishing Submodule

The publishing submodule manages workflow publication, allowing workflows to be exposed as HTTP endpoints with
authentication, rate limiting, and access logging.

### WorkflowPublishingService

Service for managing published workflows with database persistence.

**Purpose:** Provides database operations for workflow publication lifecycle.

**Responsibilities:**

- Create or update workflow publication records
- Manage publication settings (auth, rate limits, CORS)
- Track access statistics and logging
- Query published workflows by identifier or slug

#### `publish_workflow()`

```python
@staticmethod
def publish_workflow(
    graph_name: str,
    user_identifier: str,
    custom_slug: Optional[str] = None,
    description: str = "",
    require_authentication: bool = True,
    rate_limit: Optional[Dict[str, int]] = None,
    allowed_origins: Optional[List[str]] = None,
    webhook_url: Optional[str] = None,
    input_schema: Optional[Dict[str, Any]] = None,
) -> PublishedWorkflow:
    """Publish a workflow or update existing publication settings."""
```

**Parameters:**

- `graph_name` (str) - Name of the workflow to publish
- `user_identifier` (str) - User publishing the workflow (email or user ID)
- `custom_slug` (Optional[str]) - Custom URL slug for the endpoint (default: None)
- `description` (str) - Description of the published workflow (default: "")
- `require_authentication` (bool) - Whether authentication is required (default: True)
- `rate_limit` (Optional[Dict[str, int]]) - Rate limiting config (e.g., `{"requests": 100, "window": 3600}`)
- `allowed_origins` (Optional[List[str]]) - CORS allowed origins (default: None)
- `webhook_url` (Optional[str]) - Webhook URL for completion callbacks (default: None)
- `input_schema` (Optional[Dict[str, Any]]) - JSON schema for input validation (default: None)

**Returns:**

- `PublishedWorkflow` - The created or updated database record

**Raises:**

- `ValueError` - If custom_slug conflicts with existing workflow or user doesn't own workflow

**Example:**

```python
from backend.services.workflow.publishing import WorkflowPublishingService

# Basic publication
published = WorkflowPublishingService.publish_workflow(
    graph_name="customer_support_agent",
    user_identifier="user@example.com",
    description="Customer support chatbot",
    require_authentication=True,
)

# Advanced publication with custom slug and rate limiting
published = WorkflowPublishingService.publish_workflow(
    graph_name="data_processor",
    user_identifier="admin@example.com",
    custom_slug="process-data",
    description="Data processing pipeline",
    require_authentication=True,
    rate_limit={"requests": 1000, "window": 3600},
    allowed_origins=["https://app.example.com"],
    webhook_url="https://api.example.com/webhooks/workflow-complete",
    input_schema={
        "type": "object",
        "properties": {
            "data": {"type": "array"},
            "options": {"type": "object"}
        },
        "required": ["data"]
    },
)
```

**Behaviour:**

- Resolves user ID from identifier (email or ID)
- Verifies user owns the workflow
- Updates existing publication if found, creates new one otherwise
- Validates custom slug uniqueness
- Persists configuration to database
- Does NOT auto-generate authentication tokens (use Personal Access Tokens instead)

**Use Cases:**

- Publishing workflows for external API consumers
- Creating authenticated endpoints for third-party integrations
- Setting up rate-limited public APIs
- Configuring CORS for browser-based clients

#### `unpublish_workflow()`

```python
@staticmethod
def unpublish_workflow(graph_name: str) -> bool:
    """Unpublish a workflow (mark as not published)."""
```

**Parameters:**

- `graph_name` (str) - Name of the workflow to unpublish

**Returns:**

- `bool` - True if workflow was unpublished, False if not found

**Example:**

```python
# Unpublish a workflow
success = WorkflowPublishingService.unpublish_workflow("customer_support_agent")
if success:
    print("Workflow unpublished successfully")
else:
    print("Workflow not found")
```

**Behaviour:**

- Marks workflow as unpublished in database
- Does NOT revoke Personal Access Tokens (users maintain control)
- Updates timestamp
- Endpoint will return 404 after unpublishing

#### `get_published_workflow_by_identifier()`

```python
@staticmethod
def get_published_workflow_by_identifier(identifier: str) -> Optional[PublishedWorkflow]:
    """Get published workflow by workflow_id or custom_slug."""
```

**Parameters:**

- `identifier` (str) - Either a workflow UUID or a custom slug

**Returns:**

- `Optional[PublishedWorkflow]` - Published workflow if found, None otherwise

**Example:**

```python
# Get by workflow UUID
workflow = WorkflowPublishingService.get_published_workflow_by_identifier(
    "550e8400-e29b-41d4-a716-446655440000"
)

# Get by custom slug
workflow = WorkflowPublishingService.get_published_workflow_by_identifier(
    "process-data"
)

if workflow:
    print(f"Found: {workflow.graph_name}")
    print(f"Endpoint: /api/http-execution/trigger/{workflow.custom_slug or workflow.workflow_id}")
```

**Behaviour:**

- Attempts to parse identifier as UUID first
- If UUID, queries by `workflow_id`
- If not UUID, queries by `custom_slug`
- Only returns published workflows (`is_published=True`)
- Detaches object from session to avoid session errors

#### `list_published_workflows_for_user()`

```python
@staticmethod
def list_published_workflows_for_user(user_identifier: str) -> List[PublishedWorkflow]:
    """Get list of published workflows accessible to a user."""
```

**Parameters:**

- `user_identifier` (str) - User ID or identifier

**Returns:**

- `List[PublishedWorkflow]` - List of accessible published workflows

**Example:**

```python
# List all workflows user can access
workflows = WorkflowPublishingService.list_published_workflows_for_user(
    "user@example.com"
)

for workflow in workflows:
    print(f"Name: {workflow.graph_name}")
    print(f"Published: {workflow.published_at}")
    print(f"Access count: {workflow.access_count}")
    print(f"Endpoint: {workflow.custom_slug or workflow.workflow_id}")
    print("---")
```

**Behaviour:**

- Resolves user ID from identifier
- Queries workflows user created OR has membership to
- Joins with `workflows` and `workflow_memberships` tables
- Eager loads workflow relationship
- Only returns published workflows

**Use Cases:**

- Displaying published workflows in user dashboard
- Listing API endpoints for documentation
- Access control verification

#### `log_access()`

```python
@staticmethod
def log_access(
    published_workflow: PublishedWorkflow,
    client_ip: Optional[str],
    user_agent: Optional[str],
    request_method: str,
    request_path: str,
    token_used: Optional[str],
    authentication_status: str,
    response_status: int,
    execution_id: Optional[str] = None,
    execution_status: Optional[str] = None,
    execution_duration_ms: Optional[int] = None,
    response_size_bytes: Optional[int] = None,
    error_message: Optional[str] = None,
    rate_limit_hit: bool = False,
    rate_limit_remaining: Optional[int] = None,
) -> None:
    """Log access to a published workflow."""
```

**Parameters:**

- `published_workflow` (PublishedWorkflow) - The published workflow being accessed
- `client_ip` (Optional[str]) - Client IP address
- `user_agent` (Optional[str]) - Client User-Agent header
- `request_method` (str) - HTTP method (GET, POST, etc.)
- `request_path` (str) - Request path
- `token_used` (Optional[str]) - Authentication token used (hashed or truncated)
- `authentication_status` (str) - Authentication result (e.g., "success", "failed", "none")
- `response_status` (int) - HTTP response status code
- `execution_id` (Optional[str]) - Workflow execution ID (default: None)
- `execution_status` (Optional[str]) - Execution status (default: None)
- `execution_duration_ms` (Optional[int]) - Execution duration in milliseconds (default: None)
- `response_size_bytes` (Optional[int]) - Response size in bytes (default: None)
- `error_message` (Optional[str]) - Error message if request failed (default: None)
- `rate_limit_hit` (bool) - Whether rate limit was exceeded (default: False)
- `rate_limit_remaining` (Optional[int]) - Remaining requests in rate limit window (default: None)

**Returns:**

- None

**Example:**

```python
from datetime import datetime

# Log successful access
WorkflowPublishingService.log_access(
    published_workflow=workflow,
    client_ip="192.168.1.100",
    user_agent="Mozilla/5.0...",
    request_method="POST",
    request_path="/api/http-execution/trigger/process-data",
    token_used="pat_abc123...",
    authentication_status="success",
    response_status=200,
    execution_id="exec-550e8400-e29b-41d4-a716-446655440000",
    execution_status="completed",
    execution_duration_ms=1234,
    response_size_bytes=5678,
    rate_limit_remaining=95,
)

# Log rate limit exceeded
WorkflowPublishingService.log_access(
    published_workflow=workflow,
    client_ip="192.168.1.100",
    user_agent="curl/7.68.0",
    request_method="POST",
    request_path="/api/http-execution/trigger/process-data",
    token_used="pat_abc123...",
    authentication_status="success",
    response_status=429,
    error_message="Rate limit exceeded",
    rate_limit_hit=True,
    rate_limit_remaining=0,
)
```

**Behaviour:**

- Updates workflow's `last_accessed` timestamp
- Increments workflow's `access_count`
- Creates detailed access log entry in database
- Commits changes immediately

**Use Cases:**

- Auditing API access
- Monitoring workflow usage
- Rate limit enforcement tracking
- Debugging authentication issues

### Helper Functions

#### `build_endpoint_url()`

```python
def build_endpoint_url(workflow_id: str, custom_slug: str = None) -> str:
    """Build the endpoint URL for a published workflow."""
```

**Parameters:**

- `workflow_id` (str) - The workflow UUID (used if no custom_slug)
- `custom_slug` (str) - Optional custom slug (takes precedence over workflow_id)

**Returns:**

- `str` - Full endpoint URL

**Example:**

```python
from backend.services.workflow.publishing.responses import build_endpoint_url

# With custom slug
url = build_endpoint_url(
    workflow_id="550e8400-e29b-41d4-a716-446655440000",
    custom_slug="process-data"
)
# Result: "http://localhost:8000/api/http-execution/trigger/process-data"

# Without custom slug
url = build_endpoint_url(
    workflow_id="550e8400-e29b-41d4-a716-446655440000"
)
# Result: "http://localhost:8000/api/http-execution/trigger/550e8400-e29b-41d4-a716-446655440000"
```

#### `load_graph()`

```python
def load_graph(graph_name: str):
    """Load a graph from memory or disk."""
```

**Parameters:**

- `graph_name` (str) - Name of the graph to load

**Returns:**

- `GraphData` - Loaded graph object

**Example:**

```python
from backend.services.workflow.publishing.helpers import load_graph

graph = load_graph("customer_support_agent")
print(f"Loaded graph: {graph.name}")
print(f"Nodes: {len(graph.nodes)}")
```

#### `validate_graph_for_publishing()`

```python
def validate_graph_for_publishing(graph):
    """Validate a graph is ready for publishing."""
```

**Parameters:**

- `graph` (GraphData) - Graph to validate

**Raises:**

- `HTTPException` - If graph is invalid (status 400)

**Example:**

```python
from backend.services.workflow.publishing.helpers import (
    load_graph,
    validate_graph_for_publishing
)

graph = load_graph("customer_support_agent")
validate_graph_for_publishing(graph)  # Raises HTTPException if invalid
```

---

## Resumption Submodule

The resumption submodule handles the complex process of resuming subworkflow executions from checkpoints. This is
critical for workflows that delegate to subworkflows and need to resume after interruptions.

### SubworkflowResumeHandler

Handles resumption of subworkflow checkpoints and parent workflow completion.

**Purpose:** Orchestrates the multi-step process of resuming subworkflow checkpoints and propagating results back to
parent workflows.

**Responsibilities:**

- Load parent graph and subworkflow node configurations
- Build and execute subworkflow applications from checkpoints
- Extract results from completed subworkflows
- Prepare parent workflow for continuation with subworkflow results

**Initialisation:**

```python
def __init__(self, execution_engine, graph_manager):
    """
    Initialise the handler.

    Args:
        execution_engine: The LangGraph execution engine
        graph_manager: The graph manager for accessing graphs
    """
```

**Example:**

```python
from backend.services.workflow.resumption import SubworkflowResumeHandler
from backend.services.execution.engine import get_executor
from backend.services.graph import get_graph_manager

executor = get_executor()
graph_manager = get_graph_manager()

handler = SubworkflowResumeHandler(
    execution_engine=executor,
    graph_manager=graph_manager
)
```

#### `resume_subworkflow_checkpoint()`

```python
async def resume_subworkflow_checkpoint(
    self,
    parent_thread_id: str,
    subworkflow_thread_id: str,
    subworkflow_name: str,
    checkpoint_id: str,
    new_input: Any,
    checkpoint_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Resume a subworkflow from a checkpoint and get its result."""
```

**Parameters:**

- `parent_thread_id` (str) - The parent workflow's thread ID
- `subworkflow_thread_id` (str) - The subworkflow's thread ID
- `checkpoint_id` (str) - The checkpoint ID to resume from
- `subworkflow_name` (str) - Name of the subworkflow
- `new_input` (Any) - The input to resume with
- `checkpoint_metadata` (Dict[str, Any]) - Metadata about the checkpoint

**Returns:**

- `Dict[str, Any]` - Subworkflow result containing:
  - `workflow_output` (str) - The final output from the subworkflow
  - `completed` (bool) - Whether execution completed successfully
  - `chunks_processed` (int) - Number of execution chunks processed
  - `error` (str) - Error message if resumption failed

**Example:**

```python
# Resume a subworkflow checkpoint
result = await handler.resume_subworkflow_checkpoint(
    parent_thread_id="thread_1729680000_ParentWorkflow",
    subworkflow_thread_id="thread_1729680123_DataProcessor",
    subworkflow_name="DataProcessor",
    checkpoint_id="1ef7b2c3-4d5e-6789-abcd-ef0123456789",
    new_input={"continue": True, "additional_data": "value"},
    checkpoint_metadata={
        "parent_tool_call": {
            "id": "call_abc123",
            "name": "DataProcessor",
            "args": {}
        }
    }
)

if result.get("completed"):
    print(f"Subworkflow completed: {result['workflow_output']}")
    print(f"Processed {result['chunks_processed']} chunks")
else:
    print(f"Subworkflow failed: {result.get('error')}")
```

**Behaviour:**

1. Loads parent graph from thread ID
2. Finds subworkflow node configuration in parent graph
3. Builds subworkflow application with checkpoint support
4. Executes subworkflow from checkpoint with new input
5. Streams execution chunks until completion or end
6. Extracts and formats final result
7. Returns result dictionary

**Use Cases:**

- Resuming interrupted subworkflow executions
- Providing additional input to paused subworkflows
- Completing delegation patterns in multi-agent workflows

#### `complete_parent_workflow()`

```python
@staticmethod
async def complete_parent_workflow(
    parent_thread_id: str,
    subworkflow_result: Dict[str, Any],
    checkpoint_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Complete the parent workflow with the subworkflow result."""
```

**Parameters:**

- `parent_thread_id` (str) - The parent workflow's thread ID
- `subworkflow_result` (Dict[str, Any]) - The result from the subworkflow
- `checkpoint_metadata` (Dict[str, Any]) - Metadata about the checkpoint

**Returns:**

- `Dict[str, Any]` - Parent workflow completion result containing:
  - `status` (str) - Completion status ("completed")
  - `subworkflow_result` (Dict[str, Any]) - The subworkflow result
  - `tool_call_id` (str) - Tool call ID that should receive the result
  - `error` (str) - Error message if completion failed

**Example:**

```python
# Complete parent workflow after subworkflow finishes
completion = await SubworkflowResumeHandler.complete_parent_workflow(
    parent_thread_id="thread_1729680000_ParentWorkflow",
    subworkflow_result={
        "workflow_output": "Processed 1000 records successfully",
        "completed": True,
        "chunks_processed": 15
    },
    checkpoint_metadata={
        "parent_tool_call": {
            "id": "call_abc123",
            "name": "DataProcessor",
            "args": {}
        }
    }
)

print(f"Status: {completion['status']}")
print(f"Tool call {completion['tool_call_id']} will receive result")
```

**Behaviour:**

- Extracts tool call ID from checkpoint metadata
- Formats result for parent workflow continuation
- Logs completion information
- Returns formatted completion result

**Use Cases:**

- Propagating subworkflow results to parent agents
- Completing tool call patterns in delegated execution
- Logging workflow completion for debugging

### Helper Classes

#### `CheckpointLoader`

Handles loading graph and node information from checkpoints.

**Key Methods:**

```python
def load_parent_graph(self, parent_thread_id: str) -> Optional[Any]:
    """Load the parent graph from a thread ID."""

def find_subworkflow_node(self, parent_graph: Any, subworkflow_name: str) -> Optional[Any]:
    """Find a subworkflow node in the parent graph."""
```

**Example:**

```python
from backend.services.workflow.resumption.checkpoint_loader import CheckpointLoader

loader = CheckpointLoader(graph_manager)

# Load parent graph
parent_graph = loader.load_parent_graph("thread_1729680000_ParentWorkflow")

# Find subworkflow node
subworkflow_node = loader.find_subworkflow_node(parent_graph, "DataProcessor")
```

#### `SubworkflowExecutor`

Handles building and executing subworkflows from checkpoints.

**Key Methods:**

```python
def build_subworkflow_app(
    self,
    subworkflow_node: Any,
    parent_graph_name: str,
    checkpointer: Any,
) -> Any:
    """Build a subworkflow application from a node."""

async def execute_subworkflow(
    self,
    subworkflow_app: Any,
    subworkflow_thread_id: str,
    checkpoint_id: str,
    new_input: Any,
) -> Tuple[Optional[Dict[str, Any]], int]:
    """Execute a subworkflow from a checkpoint."""
```

**Example:**

```python
from backend.services.workflow.resumption.subworkflow_executor import SubworkflowExecutor

executor = SubworkflowExecutor(graph_manager)

# Build subworkflow app
app = executor.build_subworkflow_app(
    subworkflow_node=node,
    parent_graph_name="ParentWorkflow",
    checkpointer=checkpointer
)

# Execute subworkflow
final_state, chunk_count = await executor.execute_subworkflow(
    subworkflow_app=app,
    subworkflow_thread_id="thread_1729680123_DataProcessor",
    checkpoint_id="1ef7b2c3-4d5e-6789-abcd-ef0123456789",
    new_input={"continue": True}
)
```

---

## State Submodule

The state submodule defines the structured state that flows through LangGraph workflows, including TypedDict schemas,
custom reducer functions, and special node constants.

### WorkflowState

Main state dictionary that flows through the LangGraph workflow.

**Purpose:** Define the complete state structure for LangGraph workflow execution with typed fields and custom merge
behaviour.

**Structure:**

```python
class WorkflowState(TypedDict):
    """Main state dictionary for LangGraph workflows."""

    # Core message handling
    messages: Annotated[Sequence[BaseMessage], add_messages]
    original_message: str

    # Node outputs and results
    node_outputs: Annotated[Dict[str, NodeOutput], merge_node_outputs]
    results: Annotated[List[NodeResult], merge_results]

    # Execution context
    current_node: Annotated[Optional[str], last_value_reducer]
    execution_id: str
    db_execution_id: Optional[int]
    graph_name: str
    execution_order: Annotated[int, max_execution_order]

    # Metadata and contexts
    metadata: Annotated[WorkflowMetadata, merge_metadata]
    memory_context: Optional[MemoryContext]
    orchestration_context: Optional[OrchestrationContext]
    subgraph_context: Optional[Dict[str, Any]]

    # Custom data
    custom_data: Optional[Dict[str, Any]]
    file_info: Optional[Dict[str, Any]]
```

**Field Descriptions:**

**Core Message Handling:**

- `messages` - LangChain message history (uses LangGraph's `add_messages` reducer)
- `original_message` - Original input message preserved throughout execution

**Node Tracking:**

- `node_outputs` - Maps node_id → NodeOutput (uses `merge_node_outputs` reducer)
- `results` - List of execution history entries (uses `merge_results` reducer)

**Execution Context:**

- `current_node` - Currently executing node ID (uses `last_value_reducer`)
- `execution_id` - Unique UUID for this workflow execution
- `db_execution_id` - Database ID for persistence
- `graph_name` - Name of the graph being executed
- `execution_order` - Sequential order counter (uses `max_execution_order` reducer)

**Metadata & Contexts:**

- `metadata` - Execution metadata (uses `merge_metadata` reducer)
- `memory_context` - Conversation memory (if enabled)
- `orchestration_context` - Orchestrator tracking (if applicable)
- `subgraph_context` - Subgraph delegation info (if applicable)

**Custom Data:**

- `custom_data` - Arbitrary data passed between nodes
- `file_info` - File information for FILE_READ nodes

**Example:**

```python
from backend.services.workflow.state import WorkflowState
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph

# Create initial state
initial_state: WorkflowState = {
    "messages": [HumanMessage(content="Process customer inquiry")],
    "original_message": "Process customer inquiry",
    "node_outputs": {},
    "results": [],
    "current_node": None,
    "execution_id": "exec-550e8400-e29b-41d4-a716-446655440000",
    "db_execution_id": 42,
    "graph_name": "customer_support",
    "metadata": {
        "execution_started": "2025-10-27T10:30:00Z",
        "initial_input": {"message": "Process customer inquiry"}
    },
    "memory_context": None,
    "orchestration_context": None,
    "custom_data": None,
    "execution_order": 0,
    "subgraph_context": None,
    "file_info": None,
}

# Create workflow with WorkflowState
workflow = StateGraph(WorkflowState)

# Define node that updates state
def process_inquiry(state: WorkflowState) -> dict:
    """Process customer inquiry."""
    return {
        "current_node": "process_inquiry",
        "node_outputs": {
            "process_inquiry": {
                "raw": "Inquiry processed",
                "fields": {"status": "completed"}
            }
        },
        "metadata": {
            "current_node_name": "Process Inquiry",
            "current_node_type": "AGENT"
        }
    }

workflow.add_node("process_inquiry", process_inquiry)
```

### NodeOutput

Output structure from a single node execution.

**Purpose:** Capture different output formats from node execution for downstream consumption.

**Structure:**

```python
class NodeOutput(TypedDict, total=False):
    """Output structure from a single node execution."""

    raw: str
    structured: Optional[Dict[str, Any]]
    fields: Dict[str, Any]
```

**Field Descriptions:**

- `raw` - Raw text output from the node (e.g., LLM response text)
- `structured` - Parsed structured/JSON output if node produces structured data
- `fields` - Extracted fields as dictionary for template variable replacement

**Example:**

```python
from backend.services.workflow.state import NodeOutput, WorkflowState

def my_agent_node(state: WorkflowState) -> dict:
    """Agent node that produces structured output."""

    # Create node output
    output: NodeOutput = {
        "raw": "Customer inquiry processed successfully. Ticket #12345 created.",
        "structured": {
            "status": "completed",
            "ticket_id": "12345",
            "priority": "medium",
            "assigned_to": "support_team"
        },
        "fields": {
            "ticket_id": "12345",
            "status": "completed"
        }
    }

    # Return state update
    return {
        "node_outputs": {
            "my_agent_node": output
        }
    }
```

**Use Cases:**

- LLM nodes: Store raw response text and extracted fields
- Structured output nodes: Store JSON output and field mappings
- Template nodes: Provide field values for downstream template rendering

### NodeResult

Result entry for tracking execution history.

**Purpose:** Store execution history information for debugging and audit trails.

**Structure:**

```python
class NodeResult(TypedDict, total=False):
    """Result entry for tracking execution history."""

    agent: Optional[str]
    response: str
    tools: List[str]
    tool_executions: List[Dict[str, Any]]
```

**Field Descriptions:**

- `agent` - Name of the agent (if this was an agent node)
- `response` - The text response/output from the node
- `tools` - List of tool names that were used during execution
- `tool_executions` - Detailed information about each tool execution

**Example:**

```python
from backend.services.workflow.state import NodeResult, WorkflowState

def research_agent(state: WorkflowState) -> dict:
    """Research agent that uses multiple tools."""

    # Simulate tool usage
    result: NodeResult = {
        "agent": "ResearchAgent",
        "response": "Found 5 relevant academic papers on the topic",
        "tools": ["web_search", "document_reader", "citation_extractor"],
        "tool_executions": [
            {
                "tool": "web_search",
                "status": "success",
                "query": "machine learning papers 2024",
                "results_count": 10
            },
            {
                "tool": "document_reader",
                "status": "success",
                "documents_read": 5
            },
            {
                "tool": "citation_extractor",
                "status": "success",
                "citations_found": 15
            }
        ]
    }

    # Add to results list
    return {
        "results": [result]
    }
```

### WorkflowMetadata

Metadata for workflow execution tracking and debugging.

**Purpose:** Track workflow execution progress, timing, and errors.

**Structure:**

```python
class WorkflowMetadata(TypedDict, total=False):
    """Metadata for workflow execution tracking."""

    execution_started: str
    execution_ended: Optional[str]
    current_node_name: Optional[str]
    current_node_type: Optional[str]
    initial_input: Dict[str, Any]
    error: Optional[str]
    token_counts: Optional[Dict[str, int]]
```

**Field Descriptions:**

- `execution_started` - ISO 8601 timestamp when execution began
- `execution_ended` - ISO 8601 timestamp when execution completed
- `current_node_name` - Display name of currently executing node
- `current_node_type` - Type of current node (AGENT, CONDITION, etc.)
- `initial_input` - Original input that started the workflow
- `error` - Error message if workflow encountered an error
- `token_counts` - Token usage statistics (prompt, completion, total)

**Example:**

```python
from backend.services.workflow.state import WorkflowMetadata, WorkflowState
from datetime import datetime, timezone

def update_metadata(state: WorkflowState) -> dict:
    """Update workflow metadata during execution."""

    metadata: WorkflowMetadata = {
        "current_node_name": "Data Processor",
        "current_node_type": "AGENT",
        "token_counts": {
            "prompt": 150,
            "completion": 200,
            "total": 350
        }
    }

    return {"metadata": metadata}

def complete_workflow(state: WorkflowState) -> dict:
    """Mark workflow as completed."""

    metadata: WorkflowMetadata = {
        "execution_ended": datetime.now(timezone.utc).isoformat(),
    }

    return {"metadata": metadata}
```

### Reducer Functions

Custom reducer functions control how state updates are merged during workflow execution, especially important for
parallel node execution.

#### `last_value_reducer()`

```python
def last_value_reducer(current: Optional[str], updates: Optional[str]) -> Optional[str]:
    """Reducer that keeps the last non-None value."""
```

**Parameters:**

- `current` (Optional[str]) - The current value in the state
- `updates` (Optional[str]) - The new value from the node update

**Returns:**

- `Optional[str]` - The update value if not None, otherwise the current value

**Example:**

```python
from typing import Annotated
from backend.services.workflow.state import last_value_reducer

# Used in WorkflowState for current_node field
current_node: Annotated[Optional[str], last_value_reducer]

# Behaviour demonstration
assert last_value_reducer("old", "new") == "new"
assert last_value_reducer("old", None) == "old"
assert last_value_reducer(None, "new") == "new"
```

**Use Cases:**

- `WorkflowState.current_node` - Track which node is currently executing
- Scalar fields that should keep most recent value

#### `merge_node_outputs()`

```python
def merge_node_outputs(
    current: Dict[str, NodeOutput],
    updates: Dict[str, NodeOutput]
) -> Dict[str, NodeOutput]:
    """Reducer that merges node output dictionaries."""
```

**Parameters:**

- `current` (Dict[str, NodeOutput]) - The current node_outputs dictionary
- `updates` (Dict[str, NodeOutput]) - New node outputs from the update

**Returns:**

- `Dict[str, NodeOutput]` - Merged dictionary with all node outputs

**Example:**

```python
from backend.services.workflow.state import merge_node_outputs, NodeOutput

current = {
    "node1": {"raw": "output1", "fields": {"key1": "value1"}}
}
updates = {
    "node2": {"raw": "output2", "fields": {"key2": "value2"}}
}

merged = merge_node_outputs(current, updates)
# Result: {"node1": {...}, "node2": {...}}
assert len(merged) == 2
assert "node1" in merged and "node2" in merged
```

**Behaviour:**

- If current is None, returns updates (or empty dict)
- If updates is None, returns current
- Otherwise, merges updates into copy of current (updates override)

**Use Cases:**

- `WorkflowState.node_outputs` - Accumulate outputs from all executed nodes
- Parallel nodes each adding their outputs

#### `merge_metadata()`

```python
def merge_metadata(
    current: Optional[WorkflowMetadata],
    updates: Optional[WorkflowMetadata]
) -> WorkflowMetadata:
    """Reducer that merges metadata from parallel nodes."""
```

**Parameters:**

- `current` (Optional[WorkflowMetadata]) - The current metadata dictionary
- `updates` (Optional[WorkflowMetadata]) - New metadata from the update

**Returns:**

- `WorkflowMetadata` - Merged metadata dictionary

**Example:**

```python
from backend.services.workflow.state import merge_metadata

current = {
    "execution_started": "2025-10-27T10:00:00Z",
    "current_node_name": "node1"
}
updates = {
    "current_node_name": "node2",
    "current_node_type": "AGENT"
}

merged = merge_metadata(current, updates)
# Result: {
#     "execution_started": "2025-10-27T10:00:00Z",
#     "current_node_name": "node2",
#     "current_node_type": "AGENT"
# }
```

**Behaviour:**

- Merges updates into current, keeping most recent non-None values
- Preserves fields not in the update

**Use Cases:**

- `WorkflowState.metadata` - Track execution metadata across parallel nodes

#### `max_execution_order()`

```python
def max_execution_order(current: int, updates: int) -> int:
    """Reducer that keeps the maximum execution order value."""
```

**Parameters:**

- `current` (int) - The current execution order
- `updates` (int) - New execution order from the update

**Returns:**

- `int` - Maximum of current and updates

**Example:**

```python
from backend.services.workflow.state import max_execution_order

assert max_execution_order(3, 5) == 5
assert max_execution_order(10, 7) == 10
assert max_execution_order(None, 5) == 5
```

**Use Cases:**

- `WorkflowState.execution_order` - Sequential execution order counter
- Ensuring counter always progresses forward

#### `merge_results()`

```python
def merge_results(
    current: List[NodeResult],
    updates: List[NodeResult]
) -> List[NodeResult]:
    """Reducer that merges result lists from parallel nodes."""
```

**Parameters:**

- `current` (List[NodeResult]) - The current results list
- `updates` (List[NodeResult]) - New results from the update

**Returns:**

- `List[NodeResult]` - Concatenated list of all results

**Example:**

```python
from backend.services.workflow.state import merge_results

current = [{"agent": "Agent1", "response": "Result1", "tools": [], "tool_executions": []}]
updates = [{"agent": "Agent2", "response": "Result2", "tools": [], "tool_executions": []}]

merged = merge_results(current, updates)
assert len(merged) == 2
# Order preserved: current items first, then updates
```

**Behaviour:**

- Concatenates lists (current + updates)
- Preserves execution order

**Use Cases:**

- `WorkflowState.results` - Accumulate execution history from all nodes
- Parallel nodes each adding their results

### Constants

Special node identifiers for LangGraph control flow.

#### `ENTRY_POINT`

```python
ENTRY_POINT = "__start__"
```

The entry point node identifier for LangGraph workflows. Represents the implicit START node.

**Example:**

```python
from backend.services.workflow.state import ENTRY_POINT
from langgraph.graph import StateGraph

workflow = StateGraph(WorkflowState)
# LangGraph internally uses ENTRY_POINT when setting entry point
workflow.set_entry_point("first_node")
```

#### `EXIT_POINT`

```python
EXIT_POINT = "__end__"
```

The exit point node identifier for LangGraph workflows. Represents the implicit END node.

**Example:**

```python
from backend.services.workflow.state import EXIT_POINT
from langgraph.graph import StateGraph, END

workflow = StateGraph(WorkflowState)
workflow.add_edge("last_node", END)  # END == EXIT_POINT == "__end__"
```

#### `INTERRUPT_POINT`

```python
INTERRUPT_POINT = "__interrupt__"
```

The interrupt point identifier for human-in-the-loop workflows. Pauses execution for external input.

**Example:**

```python
from backend.services.workflow.state import INTERRUPT_POINT

def human_approval_node(state: WorkflowState) -> dict:
    """Node that pauses for human approval."""
    return {"next": INTERRUPT_POINT}  # Pauses workflow
```

#### `ERROR_POINT`

```python
ERROR_POINT = "__error__"
```

The error point identifier for error handling. Custom constant for application error handling.

**Example:**

```python
from backend.services.workflow.state import ERROR_POINT

def conditional_edge(state: WorkflowState) -> str:
    """Route to error handler if error occurred."""
    if state["metadata"].get("error"):
        return ERROR_POINT
    return "next_node"
```

---

## Configuration

### Initialisation Patterns

#### Publishing Service Usage

```python
from backend.services.workflow.publishing import WorkflowPublishingService

# Publishing service uses static methods - no initialisation needed
published = WorkflowPublishingService.publish_workflow(
    graph_name="my_workflow",
    user_identifier="user@example.com"
)
```

#### Resumption Handler Initialisation

```python
from backend.services.workflow.resumption import SubworkflowResumeHandler
from backend.services.execution.engine import get_executor
from backend.services.graph import get_graph_manager

# Get required dependencies
executor = get_executor()
graph_manager = get_graph_manager()

# Initialise handler
resume_handler = SubworkflowResumeHandler(
    execution_engine=executor,
    graph_manager=graph_manager
)

# Resume subworkflow
result = await resume_handler.resume_subworkflow_checkpoint(
    parent_thread_id="thread_1729680000_Parent",
    subworkflow_thread_id="thread_1729680123_Sub",
    subworkflow_name="SubWorkflow",
    checkpoint_id="checkpoint-id",
    new_input={"continue": True},
    checkpoint_metadata={}
)
```

#### State Usage in LangGraph

```python
from backend.services.workflow.state import WorkflowState, NodeOutput
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

# Create workflow with WorkflowState schema
workflow = StateGraph(WorkflowState)

# Define node function
def my_node(state: WorkflowState) -> dict:
    """Node that processes state and returns updates."""

    # Create node output
    output: NodeOutput = {
        "raw": "Processing completed",
        "structured": {"status": "success"},
        "fields": {"result": "completed"}
    }

    # Return state update
    return {
        "current_node": "my_node",
        "node_outputs": {"my_node": output},
        "metadata": {
            "current_node_name": "My Node",
            "current_node_type": "PROCESSOR"
        }
    }

# Add node to workflow
workflow.add_node("my_node", my_node)
workflow.add_edge("my_node", END)
workflow.set_entry_point("my_node")

# Compile workflow
app = workflow.compile()

# Execute with initial state
initial_state: WorkflowState = {
    "messages": [HumanMessage(content="Start")],
    "original_message": "Start",
    "node_outputs": {},
    "results": [],
    "current_node": None,
    "execution_id": "exec-123",
    "db_execution_id": None,
    "graph_name": "test_workflow",
    "metadata": {"execution_started": "2025-10-27T10:00:00Z", "initial_input": {}},
    "memory_context": None,
    "orchestration_context": None,
    "custom_data": None,
    "execution_order": 0,
    "subgraph_context": None,
    "file_info": None,
}

result = await app.ainvoke(initial_state)
```

---

## Error Handling

### Exception Hierarchy

```
ValueError (built-in)
├── Publishing errors
│   ├── Workflow not found
│   ├── User permission denied
│   └── Custom slug conflict
│
Exception (built-in)
├── Resumption errors
│   ├── Graph loading failed
│   ├── Subworkflow node not found
│   └── Execution errors
│
HTTPException (FastAPI)
├── Publishing validation errors
│   ├── 404: Workflow not found
│   └── 400: Invalid workflow
```

### Publishing Service Errors

#### Workflow Not Found or Permission Denied

```python
from backend.services.workflow.publishing import WorkflowPublishingService

try:
    published = WorkflowPublishingService.publish_workflow(
        graph_name="non_existent_workflow",
        user_identifier="user@example.com"
    )
except ValueError as e:
    if "not found" in str(e):
        print(f"Workflow doesn't exist: {e}")
    elif "permission" in str(e):
        print(f"User doesn't own workflow: {e}")
```

#### Custom Slug Conflict

```python
try:
    published = WorkflowPublishingService.publish_workflow(
        graph_name="my_workflow",
        user_identifier="user@example.com",
        custom_slug="existing-slug"  # Already in use
    )
except ValueError as e:
    if "already in use" in str(e):
        print(f"Slug conflict: {e}")
        # Suggest alternative slug
        alternative = "my-workflow-v2"
```

### Resumption Handler Errors

#### Graph Loading Failed

```python
from backend.services.workflow.resumption import SubworkflowResumeHandler

result = await handler.resume_subworkflow_checkpoint(
    parent_thread_id="invalid_thread_id",
    subworkflow_thread_id="sub_thread",
    subworkflow_name="SubWorkflow",
    checkpoint_id="checkpoint-id",
    new_input={},
    checkpoint_metadata={}
)

if result.get("error"):
    error = result["error"]
    if "Could not load parent graph" in error:
        print(f"Graph loading failed: {error}")
    elif "Could not find subworkflow node" in error:
        print(f"Subworkflow node not found: {error}")
```

#### Execution Errors

```python
try:
    result = await handler.resume_subworkflow_checkpoint(
        parent_thread_id="thread_id",
        subworkflow_thread_id="sub_thread",
        subworkflow_name="SubWorkflow",
        checkpoint_id="checkpoint-id",
        new_input={"invalid": "input"},  # Invalid input causing execution error
        checkpoint_metadata={}
    )

    if not result.get("completed"):
        print(f"Execution failed: {result.get('error')}")

except Exception as e:
    print(f"Unexpected error during resumption: {e}")
```

### Error Handling Patterns

#### Publishing Workflow with Error Handling

```python
from backend.services.workflow.publishing import WorkflowPublishingService
from backend.services.workflow.publishing.helpers import (
    load_graph,
    validate_graph_for_publishing
)
from fastapi import HTTPException

async def publish_workflow_safely(graph_name: str, user_id: str):
    """Publish workflow with comprehensive error handling."""

    try:
        # Step 1: Load graph
        try:
            graph = load_graph(graph_name)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow '{graph_name}' not found"
            )

        # Step 2: Validate graph
        try:
            validate_graph_for_publishing(graph)
        except HTTPException as e:
            # Re-raise validation errors
            raise

        # Step 3: Publish
        try:
            published = WorkflowPublishingService.publish_workflow(
                graph_name=graph_name,
                user_identifier=user_id,
                require_authentication=True
            )
            return {
                "success": True,
                "workflow_id": published.workflow_id,
                "endpoint_url": f"/api/http-execution/trigger/{published.workflow_id}"
            }
        except ValueError as e:
            if "permission" in str(e).lower():
                raise HTTPException(status_code=403, detail=str(e))
            elif "already in use" in str(e).lower():
                raise HTTPException(status_code=409, detail=str(e))
            else:
                raise HTTPException(status_code=400, detail=str(e))

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error publishing workflow: {str(e)}"
        )
```

#### Resuming with Error Recovery

```python
async def resume_with_retry(
    handler: SubworkflowResumeHandler,
    parent_thread_id: str,
    subworkflow_thread_id: str,
    subworkflow_name: str,
    checkpoint_id: str,
    new_input: dict,
    checkpoint_metadata: dict,
    max_retries: int = 3
) -> dict:
    """Resume subworkflow with retry logic."""

    for attempt in range(max_retries):
        try:
            result = await handler.resume_subworkflow_checkpoint(
                parent_thread_id=parent_thread_id,
                subworkflow_thread_id=subworkflow_thread_id,
                subworkflow_name=subworkflow_name,
                checkpoint_id=checkpoint_id,
                new_input=new_input,
                checkpoint_metadata=checkpoint_metadata
            )

            if result.get("completed"):
                return result
            else:
                error = result.get("error", "Unknown error")
                if "Could not load" in error or "Could not find" in error:
                    # Non-retryable error
                    return result
                elif attempt < max_retries - 1:
                    # Retryable error - try again
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    # Max retries reached
                    return result

        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                return {
                    "error": str(e),
                    "completed": False
                }

    return {"error": "Max retries exceeded", "completed": False}
```

---

## Integration Patterns

### Integration with API Layer

The workflow service integrates with the FastAPI application layer for HTTP endpoint management.

#### Publishing API Integration

```python
# backend/api/workflow/publishing.py
from fastapi import APIRouter, Depends, HTTPException
from backend.services.workflow.publishing import WorkflowPublishingService
from backend.services.workflow.publishing.helpers import (
    load_and_validate_unpublished_graph,
    validate_graph_for_publishing
)
from backend.services.workflow.publishing.responses import build_endpoint_url

router = APIRouter(prefix="/api/publish", tags=["workflow-publishing"])

@router.post("/workflow/{graph_name}")
async def publish_workflow(
    graph_name: str,
    request: PublishWorkflowRequest,
    current_user: dict = Depends(get_current_user)
):
    """Publish a workflow as an HTTP endpoint."""

    # Step 1: Load and validate graph
    graph = load_and_validate_unpublished_graph(graph_name)
    validate_graph_for_publishing(graph)

    # Step 2: Publish in database
    published_workflow = WorkflowPublishingService.publish_workflow(
        graph_name=graph_name,
        user_identifier=current_user["email"],
        custom_slug=request.custom_slug,
        description=request.description,
        require_authentication=request.require_authentication,
        rate_limit=request.rate_limit,
        allowed_origins=request.allowed_origins
    )

    # Step 3: Build response
    endpoint_url = build_endpoint_url(
        workflow_id=published_workflow.workflow_id,
        custom_slug=published_workflow.custom_slug
    )

    return {
        "success": True,
        "graph_name": graph_name,
        "endpoint_url": endpoint_url,
        "workflow_id": published_workflow.workflow_id
    }
```

#### HTTP Execution Integration

```python
# backend/api/http_execution/routes.py
from fastapi import APIRouter, Request, HTTPException
from backend.services.workflow.publishing import WorkflowPublishingService

router = APIRouter(prefix="/api/http-execution")

@router.post("/trigger/{identifier}")
async def trigger_workflow(identifier: str, request: Request):
    """Trigger a published workflow execution."""

    # Step 1: Get published workflow
    published = WorkflowPublishingService.get_published_workflow_by_identifier(identifier)
    if not published:
        raise HTTPException(status_code=404, detail="Published workflow not found")

    # Step 2: Authenticate if required
    if published.require_authentication:
        # Authenticate using Personal Access Token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not authenticate_pat(token, published):
            raise HTTPException(status_code=401, detail="Invalid token")

    # Step 3: Check rate limits
    if published.rate_limit:
        if is_rate_limited(published, client_ip=request.client.host):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Step 4: Execute workflow
    executor = get_executor()
    result = await executor.execute_workflow(
        graph_name=published.graph_name,
        input_data=await request.json()
    )

    # Step 5: Log access
    WorkflowPublishingService.log_access(
        published_workflow=published,
        client_ip=request.client.host,
        user_agent=request.headers.get("User-Agent"),
        request_method="POST",
        request_path=str(request.url.path),
        token_used=token if published.require_authentication else None,
        authentication_status="success",
        response_status=200,
        execution_id=result.get("execution_id")
    )

    return result
```

### Integration with Execution Engine

The resumption handler integrates with the execution engine for checkpoint resumption.

#### Execution Engine Integration

```python
# backend/services/execution/engine.py
from backend.services.workflow.resumption import SubworkflowResumeHandler

class ExecutionEngine:
    """Main execution engine coordinator."""

    def __init__(self, graph_manager: GraphManager):
        self.graph_manager = graph_manager
        self.checkpointer = initialize_checkpointer()

        # Initialise resumption handler
        self.subworkflow_resume_handler = SubworkflowResumeHandler(
            execution_engine=self,
            graph_manager=graph_manager
        )

    async def resume_from_checkpoint(
        self,
        graph_name: str,
        thread_id: str,
        checkpoint_id: str,
        new_input: dict
    ):
        """Resume execution from a checkpoint."""

        # Check if this is a subworkflow checkpoint
        metadata = get_checkpoint_metadata(checkpoint_id)

        if metadata.get("is_subworkflow_checkpoint"):
            # Delegate to subworkflow resume handler
            return await self.subworkflow_resume_handler.resume_subworkflow_checkpoint(
                parent_thread_id=metadata["parent_thread_id"],
                subworkflow_thread_id=thread_id,
                subworkflow_name=metadata["subworkflow_name"],
                checkpoint_id=checkpoint_id,
                new_input=new_input,
                checkpoint_metadata=metadata
            )
        else:
            # Regular checkpoint resumption
            return await self.resume_regular_checkpoint(
                graph_name, thread_id, checkpoint_id, new_input
            )
```

### Integration with Graph Builder

The state schemas integrate with the graph builder for workflow compilation.

#### Graph Builder Integration

```python
# backend/services/graph/builder.py
from backend.services.workflow.state import WorkflowState, EXIT_POINT
from langgraph.graph import StateGraph, END

class GraphBuilder:
    """Builds LangGraph workflows from graph definitions."""

    def build_workflow(self, graph: GraphData):
        """Build a LangGraph workflow from graph definition."""

        # Create StateGraph with WorkflowState
        workflow = StateGraph(WorkflowState)

        # Add nodes
        for node in graph.nodes:
            node_function = self.create_node_function(node)
            workflow.add_node(node.id, node_function)

        # Add edges
        for edge in graph.edges:
            if edge.target == "END":
                workflow.add_edge(edge.source, END)  # END == EXIT_POINT
            else:
                workflow.add_edge(edge.source, edge.target)

        # Set entry point
        workflow.set_entry_point(graph.entry_node)

        # Compile with checkpointer
        return workflow.compile(checkpointer=self.checkpointer)

    def create_node_function(self, node):
        """Create a node function that updates WorkflowState."""

        def node_function(state: WorkflowState) -> dict:
            # Execute node logic
            result = execute_node(node, state)

            # Return state update
            return {
                "current_node": node.id,
                "node_outputs": {
                    node.id: {
                        "raw": result.raw_output,
                        "structured": result.structured_output,
                        "fields": result.fields
                    }
                },
                "metadata": {
                    "current_node_name": node.display_name,
                    "current_node_type": node.type.value
                }
            }

        return node_function
```

### Dependency Flow

```
User Request
    ↓
API Layer (backend/api/workflow/publishing.py)
    ↓
WorkflowPublishingService (backend/services/workflow/publishing/service.py)
    ↓
Database (PublishedWorkflow model)
    ↓
Response to User


HTTP Request to Published Endpoint
    ↓
API Layer (backend/api/http_execution/routes.py)
    ↓
WorkflowPublishingService.get_published_workflow_by_identifier()
    ↓
Authentication & Rate Limiting
    ↓
ExecutionEngine.execute_workflow()
    ↓
WorkflowPublishingService.log_access()
    ↓
Response to Client


Checkpoint Resumption Request
    ↓
ExecutionEngine.resume_from_checkpoint()
    ↓
SubworkflowResumeHandler.resume_subworkflow_checkpoint()
    ↓
CheckpointLoader.load_parent_graph()
    ↓
SubworkflowExecutor.build_subworkflow_app()
    ↓
SubworkflowExecutor.execute_subworkflow()
    ↓
SubworkflowResumeHandler.complete_parent_workflow()
    ↓
Response with Results
```

---

## Usage Examples

### Example 1: Basic Workflow Publishing

Complete example showing how to publish a workflow with authentication.

```python
from backend.services.workflow.publishing import WorkflowPublishingService
from backend.services.workflow.publishing.helpers import (
    load_graph,
    validate_graph_for_publishing
)
from backend.services.workflow.publishing.responses import build_endpoint_url

# Step 1: Load and validate the workflow
graph_name = "customer_support_agent"
graph = load_graph(graph_name)
validate_graph_for_publishing(graph)

# Step 2: Publish the workflow
published_workflow = WorkflowPublishingService.publish_workflow(
    graph_name=graph_name,
    user_identifier="admin@example.com",
    description="Customer support chatbot for handling inquiries",
    require_authentication=True
)

# Step 3: Get the endpoint URL
endpoint_url = build_endpoint_url(
    workflow_id=published_workflow.workflow_id,
    custom_slug=published_workflow.custom_slug
)

print(f"Workflow published successfully!")
print(f"Endpoint: {endpoint_url}")
print(f"Workflow ID: {published_workflow.workflow_id}")
print(f"Authentication required: {published_workflow.require_authentication}")
print(f"Create a Personal Access Token at Settings → API Tokens to authenticate")
```

### Example 2: Advanced Publishing with Rate Limiting

Complete example showing advanced publication with custom slug, rate limiting, and CORS.

```python
from backend.services.workflow.publishing import WorkflowPublishingService
from backend.services.workflow.publishing.helpers import (
    load_graph,
    validate_graph_for_publishing
)

# Define rate limit (100 requests per hour)
rate_limit = {
    "requests": 100,
    "window": 3600  # seconds
}

# Define allowed origins for CORS
allowed_origins = [
    "https://app.example.com",
    "https://dashboard.example.com"
]

# Define input schema for validation
input_schema = {
    "type": "object",
    "properties": {
        "message": {
            "type": "string",
            "description": "Customer inquiry message"
        },
        "customer_id": {
            "type": "string",
            "description": "Customer ID"
        },
        "priority": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "default": "medium"
        }
    },
    "required": ["message", "customer_id"]
}

# Publish with advanced configuration
published = WorkflowPublishingService.publish_workflow(
    graph_name="customer_support_agent",
    user_identifier="admin@example.com",
    custom_slug="customer-support",
    description="AI-powered customer support agent",
    require_authentication=True,
    rate_limit=rate_limit,
    allowed_origins=allowed_origins,
    webhook_url="https://api.example.com/webhooks/workflow-complete",
    input_schema=input_schema
)

print(f"Published with custom slug: {published.custom_slug}")
print(f"Endpoint: /api/http-execution/trigger/{published.custom_slug}")
print(f"Rate limit: {rate_limit['requests']} requests per hour")
print(f"CORS origins: {', '.join(allowed_origins)}")
```

### Example 3: Managing Published Workflows

Complete example showing how to list, update, and unpublish workflows.

```python
from backend.services.workflow.publishing import WorkflowPublishingService

# List all workflows for a user
user_id = "user@example.com"
workflows = WorkflowPublishingService.list_published_workflows_for_user(user_id)

print(f"Published workflows for {user_id}:")
for workflow in workflows:
    print(f"\n  Name: {workflow.graph_name}")
    print(f"  Published: {workflow.published_at}")
    print(f"  Access count: {workflow.access_count}")
    print(f"  Endpoint: /api/http-execution/trigger/{workflow.custom_slug or workflow.workflow_id}")
    print(f"  Auth required: {workflow.require_authentication}")

# Update a published workflow
graph_name = "customer_support_agent"
updated = WorkflowPublishingService.publish_workflow(
    graph_name=graph_name,
    user_identifier=user_id,
    custom_slug="support-v2",  # Changed slug
    description="Updated customer support agent",
    require_authentication=False,  # Changed to public
    rate_limit={"requests": 500, "window": 3600}  # Increased rate limit
)

print(f"\nWorkflow updated:")
print(f"  New slug: {updated.custom_slug}")
print(f"  Auth required: {updated.require_authentication}")

# Unpublish a workflow
success = WorkflowPublishingService.unpublish_workflow(graph_name)
if success:
    print(f"\nWorkflow '{graph_name}' unpublished successfully")
else:
    print(f"\nWorkflow '{graph_name}' not found")
```

### Example 4: Resuming Subworkflow Checkpoint

Complete example showing subworkflow checkpoint resumption.

```python
import asyncio
from backend.services.workflow.resumption import SubworkflowResumeHandler
from backend.services.execution.engine import get_executor
from backend.services.graph import get_graph_manager

async def resume_subworkflow_example():
    """Example of resuming a subworkflow checkpoint."""

    # Get dependencies
    executor = get_executor()
    graph_manager = get_graph_manager()

    # Initialise handler
    handler = SubworkflowResumeHandler(
        execution_engine=executor,
        graph_manager=graph_manager
    )

    # Define checkpoint information
    parent_thread_id = "thread_1729680000_ParentWorkflow"
    subworkflow_thread_id = "thread_1729680123_DataProcessor"
    subworkflow_name = "DataProcessor"
    checkpoint_id = "1ef7b2c3-4d5e-6789-abcd-ef0123456789"

    # Define new input for resumption
    new_input = {
        "continue": True,
        "additional_data": {
            "batch_size": 100,
            "filter": "active_only"
        }
    }

    # Checkpoint metadata
    checkpoint_metadata = {
        "parent_tool_call": {
            "id": "call_abc123",
            "name": "DataProcessor",
            "args": {}
        },
        "is_subworkflow_checkpoint": True,
        "parent_thread_id": parent_thread_id,
        "subworkflow_name": subworkflow_name
    }

    print("Resuming subworkflow checkpoint...")

    # Resume subworkflow
    result = await handler.resume_subworkflow_checkpoint(
        parent_thread_id=parent_thread_id,
        subworkflow_thread_id=subworkflow_thread_id,
        subworkflow_name=subworkflow_name,
        checkpoint_id=checkpoint_id,
        new_input=new_input,
        checkpoint_metadata=checkpoint_metadata
    )

    # Check result
    if result.get("completed"):
        print(f"\n✓ Subworkflow completed successfully!")
        print(f"  Output: {result['workflow_output']}")
        print(f"  Chunks processed: {result['chunks_processed']}")

        # Complete parent workflow
        completion = await SubworkflowResumeHandler.complete_parent_workflow(
            parent_thread_id=parent_thread_id,
            subworkflow_result=result,
            checkpoint_metadata=checkpoint_metadata
        )

        print(f"\n✓ Parent workflow completion prepared:")
        print(f"  Status: {completion['status']}")
        print(f"  Tool call ID: {completion['tool_call_id']}")
    else:
        print(f"\n✗ Subworkflow failed:")
        print(f"  Error: {result.get('error')}")

# Run the example
asyncio.run(resume_subworkflow_example())
```

### Example 5: Using WorkflowState in LangGraph

Complete example showing how to use WorkflowState with custom nodes.

```python
from backend.services.workflow.state import (
    WorkflowState,
    NodeOutput,
    NodeResult,
    EXIT_POINT
)
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END
from datetime import datetime, timezone

# Define custom node functions
def research_node(state: WorkflowState) -> dict:
    """Research node that uses tools to gather information."""

    # Simulate research
    research_result = "Found 5 relevant papers on quantum computing"

    # Create node output
    output: NodeOutput = {
        "raw": research_result,
        "structured": {
            "papers_found": 5,
            "topic": "quantum computing",
            "relevance_score": 0.92
        },
        "fields": {
            "papers_count": 5,
            "topic": "quantum computing"
        }
    }

    # Create result entry
    result: NodeResult = {
        "agent": "ResearchAgent",
        "response": research_result,
        "tools": ["web_search", "academic_db"],
        "tool_executions": [
            {"tool": "web_search", "status": "success", "results": 3},
            {"tool": "academic_db", "status": "success", "results": 2}
        ]
    }

    # Return state update
    return {
        "messages": [AIMessage(content=research_result)],
        "current_node": "research",
        "node_outputs": {"research": output},
        "results": [result],
        "metadata": {
            "current_node_name": "Research Agent",
            "current_node_type": "AGENT",
            "token_counts": {
                "prompt": 120,
                "completion": 80,
                "total": 200
            }
        },
        "execution_order": state["execution_order"] + 1
    }

def summary_node(state: WorkflowState) -> dict:
    """Summary node that aggregates research results."""

    # Get research output
    research_output = state["node_outputs"].get("research", {})
    papers_count = research_output.get("fields", {}).get("papers_count", 0)

    # Create summary
    summary = f"Research complete. Found {papers_count} papers. Summary: ..."

    output: NodeOutput = {
        "raw": summary,
        "fields": {"summary": summary}
    }

    return {
        "messages": [AIMessage(content=summary)],
        "current_node": "summary",
        "node_outputs": {"summary": output},
        "metadata": {
            "current_node_name": "Summary Agent",
            "current_node_type": "AGENT",
            "execution_ended": datetime.now(timezone.utc).isoformat()
        },
        "execution_order": state["execution_order"] + 1
    }

# Build workflow
workflow = StateGraph(WorkflowState)

# Add nodes
workflow.add_node("research", research_node)
workflow.add_node("summary", summary_node)

# Add edges
workflow.add_edge("research", "summary")
workflow.add_edge("summary", END)

# Set entry point
workflow.set_entry_point("research")

# Compile
app = workflow.compile()

# Execute
async def run_workflow():
    initial_state: WorkflowState = {
        "messages": [HumanMessage(content="Research quantum computing")],
        "original_message": "Research quantum computing",
        "node_outputs": {},
        "results": [],
        "current_node": None,
        "execution_id": "exec-550e8400-e29b-41d4-a716-446655440000",
        "db_execution_id": 42,
        "graph_name": "research_workflow",
        "metadata": {
            "execution_started": datetime.now(timezone.utc).isoformat(),
            "initial_input": {"message": "Research quantum computing"}
        },
        "memory_context": None,
        "orchestration_context": None,
        "custom_data": None,
        "execution_order": 0,
        "subgraph_context": None,
        "file_info": None,
    }

    result = await app.ainvoke(initial_state)

    print("Workflow completed!")
    print(f"Messages: {len(result['messages'])}")
    print(f"Node outputs: {list(result['node_outputs'].keys())}")
    print(f"Results: {len(result['results'])}")
    print(f"Final execution order: {result['execution_order']}")

import asyncio
asyncio.run(run_workflow())
```

### Example 6: Access Logging and Analytics

Complete example showing how to log and analyse workflow access.

```python
from backend.services.workflow.publishing import WorkflowPublishingService
from backend.models import WorkflowAccessLog
from backend.services.database import get_db
from datetime import datetime, timedelta

# Get published workflow
workflow = WorkflowPublishingService.get_published_workflow_by_identifier("process-data")

# Log an access
WorkflowPublishingService.log_access(
    published_workflow=workflow,
    client_ip="192.168.1.100",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    request_method="POST",
    request_path="/api/http-execution/trigger/process-data",
    token_used="pat_abc123def456",
    authentication_status="success",
    response_status=200,
    execution_id="exec-550e8400-e29b-41d4-a716-446655440000",
    execution_status="completed",
    execution_duration_ms=1234,
    response_size_bytes=5678,
    rate_limit_remaining=95
)

# Query access logs for analytics
with get_db() as db:
    # Get last 24 hours of access
    since = datetime.utcnow() - timedelta(days=1)
    recent_access = (
        db.query(WorkflowAccessLog)
        .filter(
            WorkflowAccessLog.published_workflow_id == workflow.id,
            WorkflowAccessLog.accessed_at >= since
        )
        .all()
    )

    print(f"Access analytics for {workflow.graph_name}:")
    print(f"  Total accesses (24h): {len(recent_access)}")

    # Count by status
    success_count = sum(1 for log in recent_access if log.authentication_status == "success")
    failed_count = sum(1 for log in recent_access if log.authentication_status == "failed")

    print(f"  Successful: {success_count}")
    print(f"  Failed auth: {failed_count}")

    # Calculate average execution time
    completed = [log for log in recent_access if log.execution_duration_ms]
    if completed:
        avg_duration = sum(log.execution_duration_ms for log in completed) / len(completed)
        print(f"  Avg execution time: {avg_duration:.0f}ms")

    # Rate limit hits
    rate_limit_hits = sum(1 for log in recent_access if log.rate_limit_hit)
    print(f"  Rate limit hits: {rate_limit_hits}")
```

---

## Performance Considerations

### Performance Characteristics

**Publishing Service:**

- Database queries: O(1) for lookups by ID/slug, O(n) for user workflow lists
- Memory usage: Minimal (stateless service)
- I/O: Database-bound (PostgreSQL queries)

**Resumption Handler:**

- Complexity: O(n) where n is number of execution chunks
- Memory usage: Moderate (streams execution chunks)
- I/O: Checkpoint I/O-bound, LangGraph execution CPU/I/O-bound

**State Schemas:**

- Reducer functions: O(1) for scalars, O(n) for dictionaries/lists
- Memory usage: State size grows with workflow complexity
- Serialisation: TypedDict enables efficient JSON serialisation

### Optimisation Tips

#### Tip 1: Batch Workflow Listing

**Problem:**

```python
# Inefficient: Query workflows one at a time
for user_id in user_ids:
    workflows = WorkflowPublishingService.list_published_workflows_for_user(user_id)
    process_workflows(workflows)
```

**Solution:**

```python
# Efficient: Query once with bulk user list
from backend.services.database import get_db
from sqlalchemy import or_

with get_db() as db:
    # Single query for all users
    accessible_workflow_ids = (
        select(Workflow.id)
        .select_from(Workflow)
        .outerjoin(WorkflowMembership)
        .where(
            or_(
                Workflow.created_by_user_id.in_(user_ids),
                WorkflowMembership.user_id.in_(user_ids)
            )
        )
    )

    published_workflows = (
        db.query(PublishedWorkflow)
        .filter(
            PublishedWorkflow.is_published,
            PublishedWorkflow.workflow_id.in_(accessible_workflow_ids)
        )
        .all()
    )
```

#### Tip 2: Cache Published Workflow Lookups

```python
from functools import lru_cache
from typing import Optional

@lru_cache(maxsize=256)
def get_cached_published_workflow(identifier: str) -> Optional[dict]:
    """Cached lookup for published workflows (use with caution)."""
    workflow = WorkflowPublishingService.get_published_workflow_by_identifier(identifier)
    if workflow:
        return {
            "workflow_id": workflow.workflow_id,
            "graph_name": workflow.graph_name,
            "require_authentication": workflow.require_authentication,
            "rate_limit": workflow.rate_limit,
            "custom_slug": workflow.custom_slug
        }
    return None

# Clear cache when publishing/unpublishing
def publish_workflow_with_cache_clear(*args, **kwargs):
    result = WorkflowPublishingService.publish_workflow(*args, **kwargs)
    get_cached_published_workflow.cache_clear()
    return result
```

**Note:** Be cautious with caching - ensure cache is invalidated when workflows are published/unpublished.

#### Tip 3: Stream Subworkflow Execution

Resumption handler already streams execution chunks efficiently. Monitor chunk processing:

```python
async def resume_with_monitoring(handler, *args, **kwargs):
    """Resume subworkflow with progress monitoring."""

    start_time = time.time()
    result = await handler.resume_subworkflow_checkpoint(*args, **kwargs)
    elapsed = time.time() - start_time

    chunks = result.get("chunks_processed", 0)
    if chunks > 0:
        avg_chunk_time = elapsed / chunks
        print(f"Processed {chunks} chunks in {elapsed:.2f}s")
        print(f"Average chunk time: {avg_chunk_time:.3f}s")

    return result
```

### Async Support

The resumption handler is fully async:

```python
# Correct: Use await
result = await handler.resume_subworkflow_checkpoint(...)

# Incorrect: Don't call without await
# result = handler.resume_subworkflow_checkpoint(...)  # Returns coroutine!
```

### State Reducer Performance

Reducers are called frequently during state updates. Keep them efficient:

```python
# Good: O(1) reducer
def last_value_reducer(current, updates):
    return updates if updates is not None else current

# Good: O(n) where n = number of keys
def merge_node_outputs(current, updates):
    if current is None:
        return updates or {}
    if updates is None:
        return current
    merged = dict(current)
    merged.update(updates)
    return merged

# Avoid: O(n²) nested loops in reducers
# def bad_reducer(current, updates):
#     result = {}
#     for key1 in current:
#         for key2 in updates:  # BAD: nested loop
#             ...
```

---

## Testing Patterns

### Unit Testing Publishing Service

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.services.workflow.publishing import WorkflowPublishingService

@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    return session

@pytest.fixture
def sample_workflow():
    """Sample workflow for testing."""
    workflow = Mock()
    workflow.id = "550e8400-e29b-41d4-a716-446655440000"
    workflow.name = "test_workflow"
    workflow.created_by_user_id = "user-123"
    return workflow

def test_publish_workflow_creates_new_publication(mock_db_session, sample_workflow):
    """Test publishing a workflow creates a new publication record."""

    with patch('backend.services.workflow.publishing.service.get_db') as mock_get_db:
        mock_get_db.return_value.__enter__.return_value = mock_db_session
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            sample_workflow,  # Workflow query
            None,  # Existing publication query (none found)
            None,  # Slug conflict query
        ]

        # Publish workflow
        with patch('backend.services.workflow.publishing.service.resolve_user_id', return_value="user-123"):
            published = WorkflowPublishingService.publish_workflow(
                graph_name="test_workflow",
                user_identifier="user@example.com",
                description="Test workflow",
                require_authentication=True
            )

        # Verify publication was added to session
        mock_db_session.add.assert_called_once()

        # Verify flush was called
        mock_db_session.flush.assert_called_once()

def test_publish_workflow_raises_on_slug_conflict():
    """Test that publishing raises ValueError on slug conflict."""

    with patch('backend.services.workflow.publishing.service.get_db') as mock_get_db:
        mock_db_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db_session

        # Setup mock responses
        existing_slug = Mock()
        existing_slug.graph_name = "other_workflow"
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            Mock(id="workflow-id", created_by_user_id="user-123"),  # Workflow
            None,  # Existing publication
            existing_slug,  # Slug conflict
        ]

        # Should raise ValueError
        with patch('backend.services.workflow.publishing.service.resolve_user_id', return_value="user-123"):
            with pytest.raises(ValueError, match="already in use"):
                WorkflowPublishingService.publish_workflow(
                    graph_name="test_workflow",
                    user_identifier="user@example.com",
                    custom_slug="existing-slug"
                )
```

### Unit Testing Resumption Handler

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.services.workflow.resumption import SubworkflowResumeHandler

@pytest.fixture
def mock_execution_engine():
    """Mock execution engine."""
    engine = Mock()
    engine.checkpointer = Mock()
    return engine

@pytest.fixture
def mock_graph_manager():
    """Mock graph manager."""
    manager = Mock()
    return manager

@pytest.fixture
def resume_handler(mock_execution_engine, mock_graph_manager):
    """Create resume handler with mocked dependencies."""
    return SubworkflowResumeHandler(
        execution_engine=mock_execution_engine,
        graph_manager=mock_graph_manager
    )

@pytest.mark.asyncio
async def test_resume_subworkflow_success(resume_handler):
    """Test successful subworkflow resumption."""

    # Mock checkpoint loader
    with patch.object(resume_handler.checkpoint_loader, 'load_parent_graph') as mock_load:
        mock_graph = Mock()
        mock_load.return_value = mock_graph

        with patch.object(resume_handler.checkpoint_loader, 'find_subworkflow_node') as mock_find:
            mock_node = Mock()
            mock_find.return_value = mock_node

            # Mock subworkflow executor
            with patch.object(resume_handler.subworkflow_executor, 'build_subworkflow_app') as mock_build:
                mock_app = Mock()
                mock_build.return_value = mock_app

                with patch.object(resume_handler.subworkflow_executor, 'execute_subworkflow') as mock_execute:
                    final_state = {"workflow_output": "Success"}
                    chunk_count = 5
                    mock_execute.return_value = (final_state, chunk_count)

                    # Resume
                    result = await resume_handler.resume_subworkflow_checkpoint(
                        parent_thread_id="parent_thread",
                        subworkflow_thread_id="sub_thread",
                        subworkflow_name="SubWorkflow",
                        checkpoint_id="checkpoint-id",
                        new_input={"continue": True},
                        checkpoint_metadata={}
                    )

                    # Assertions
                    assert result["completed"] is True
                    assert result["workflow_output"] == "Success"
                    assert result["chunks_processed"] == 5

@pytest.mark.asyncio
async def test_resume_subworkflow_graph_not_found(resume_handler):
    """Test resumption when parent graph not found."""

    with patch.object(resume_handler.checkpoint_loader, 'load_parent_graph') as mock_load:
        mock_load.return_value = None

        result = await resume_handler.resume_subworkflow_checkpoint(
            parent_thread_id="invalid_thread",
            subworkflow_thread_id="sub_thread",
            subworkflow_name="SubWorkflow",
            checkpoint_id="checkpoint-id",
            new_input={},
            checkpoint_metadata={}
        )

        assert "error" in result
        assert "Could not load parent graph" in result["error"]
```

### Integration Testing State Schemas

```python
import pytest
from backend.services.workflow.state import (
    WorkflowState,
    NodeOutput,
    merge_node_outputs,
    merge_results,
    last_value_reducer
)
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END

@pytest.mark.integration
def test_workflow_state_with_langgraph():
    """Integration test for WorkflowState with LangGraph."""

    # Create workflow
    workflow = StateGraph(WorkflowState)

    # Define test nodes
    def node1(state: WorkflowState) -> dict:
        output: NodeOutput = {
            "raw": "Node 1 output",
            "fields": {"key1": "value1"}
        }
        return {
            "current_node": "node1",
            "node_outputs": {"node1": output},
            "messages": [AIMessage(content="Node 1")]
        }

    def node2(state: WorkflowState) -> dict:
        output: NodeOutput = {
            "raw": "Node 2 output",
            "fields": {"key2": "value2"}
        }
        return {
            "current_node": "node2",
            "node_outputs": {"node2": output},
            "messages": [AIMessage(content="Node 2")]
        }

    # Build workflow
    workflow.add_node("node1", node1)
    workflow.add_node("node2", node2)
    workflow.add_edge("node1", "node2")
    workflow.add_edge("node2", END)
    workflow.set_entry_point("node1")

    # Compile
    app = workflow.compile()

    # Initial state
    initial_state: WorkflowState = {
        "messages": [HumanMessage(content="Start")],
        "original_message": "Start",
        "node_outputs": {},
        "results": [],
        "current_node": None,
        "execution_id": "test-exec-123",
        "db_execution_id": None,
        "graph_name": "test_graph",
        "metadata": {"execution_started": "2025-10-27T10:00:00Z", "initial_input": {}},
        "memory_context": None,
        "orchestration_context": None,
        "custom_data": None,
        "execution_order": 0,
        "subgraph_context": None,
        "file_info": None,
    }

    # Run workflow
    import asyncio
    result = asyncio.run(app.ainvoke(initial_state))

    # Assertions
    assert result["current_node"] == "node2"
    assert len(result["node_outputs"]) == 2
    assert "node1" in result["node_outputs"]
    assert "node2" in result["node_outputs"]
    assert len(result["messages"]) == 3  # Human + 2 AI messages

def test_merge_node_outputs_reducer():
    """Test node outputs reducer function."""

    current = {
        "node1": {"raw": "output1", "fields": {"a": 1}}
    }
    updates = {
        "node2": {"raw": "output2", "fields": {"b": 2}}
    }

    merged = merge_node_outputs(current, updates)

    assert len(merged) == 2
    assert "node1" in merged
    assert "node2" in merged
    assert merged["node1"]["fields"]["a"] == 1
    assert merged["node2"]["fields"]["b"] == 2

def test_last_value_reducer():
    """Test last value reducer function."""

    assert last_value_reducer("old", "new") == "new"
    assert last_value_reducer("old", None) == "old"
    assert last_value_reducer(None, "new") == "new"
    assert last_value_reducer(None, None) is None
```

---

## Best Practices

### Do's

✅ **Use Static Methods for Publishing Service**

```python
# Good: Use static methods directly
published = WorkflowPublishingService.publish_workflow(
    graph_name="my_workflow",
    user_identifier="user@example.com"
)

# Unnecessary: Don't instantiate
# service = WorkflowPublishingService()  # Not needed!
```

✅ **Validate Graphs Before Publishing**

```python
# Good: Validate before publishing
from backend.services.workflow.publishing.helpers import (
    load_graph,
    validate_graph_for_publishing
)

graph = load_graph("my_workflow")
validate_graph_for_publishing(graph)  # Raises if invalid
published = WorkflowPublishingService.publish_workflow(...)

# Bad: Publishing without validation
# published = WorkflowPublishingService.publish_workflow(...)  # May fail!
```

✅ **Use Type Hints with WorkflowState**

```python
# Good: Explicit type hints
from backend.services.workflow.state import WorkflowState, NodeOutput

def my_node(state: WorkflowState) -> dict:
    output: NodeOutput = {
        "raw": "Result",
        "fields": {"key": "value"}
    }
    return {"node_outputs": {"my_node": output}}

# Less clear: No type hints
# def my_node(state):
#     return {"node_outputs": {"my_node": {...}}}
```

✅ **Log Access for Published Workflows**

```python
# Good: Always log access
WorkflowPublishingService.log_access(
    published_workflow=workflow,
    client_ip=request.client.host,
    user_agent=request.headers.get("User-Agent"),
    request_method="POST",
    request_path=str(request.url.path),
    token_used=token,
    authentication_status="success",
    response_status=200,
    execution_id=execution_id
)

# Bad: Not logging access (loses audit trail)
```

✅ **Handle Resumption Errors Gracefully**

```python
# Good: Check result and handle errors
result = await handler.resume_subworkflow_checkpoint(...)
if result.get("completed"):
    process_success(result)
else:
    handle_error(result.get("error"))

# Bad: Assume success
# output = result["workflow_output"]  # May not exist if error!
```

✅ **Use Custom Reducers for Parallel Nodes**

```python
# Good: Use appropriate reducers for parallel execution
from typing import Annotated
from backend.services.workflow.state import merge_node_outputs

class MyState(TypedDict):
    outputs: Annotated[Dict[str, NodeOutput], merge_node_outputs]
    # Parallel nodes will merge correctly

# Bad: No reducer for concurrent updates
# class MyState(TypedDict):
#     outputs: Dict[str, NodeOutput]
#     # Parallel nodes may lose data!
```

### Don'ts

❌ **Don't Hard-Code Workflow IDs**

```python
# Bad: Hard-coding workflow IDs
workflow = WorkflowPublishingService.get_published_workflow_by_identifier(
    "550e8400-e29b-41d4-a716-446655440000"  # Hard-coded!
)

# Good: Use custom slugs or environment variables
import os
workflow = WorkflowPublishingService.get_published_workflow_by_identifier(
    os.environ.get("WORKFLOW_SLUG", "default-workflow")
)
```

❌ **Don't Mutate State Directly in Reducers**

```python
# Bad: Mutating input arguments
def bad_reducer(current: dict, updates: dict) -> dict:
    current.update(updates)  # Mutates current!
    return current

# Good: Create new dict
def good_reducer(current: dict, updates: dict) -> dict:
    merged = dict(current) if current else {}
    if updates:
        merged.update(updates)
    return merged
```

❌ **Don't Publish Invalid Workflows**

```python
# Bad: Skip validation
published = WorkflowPublishingService.publish_workflow(
    graph_name="untested_workflow",
    user_identifier="user@example.com"
)
# May publish broken workflow!

# Good: Validate first
graph = load_graph("untested_workflow")
validation = graph.validate()
if not validation["is_valid"]:
    raise ValueError(f"Invalid workflow: {validation['errors']}")
validate_graph_for_publishing(graph)
published = WorkflowPublishingService.publish_workflow(...)
```

❌ **Don't Block on Async Resumption**

```python
# Bad: Synchronous call to async function
# result = handler.resume_subworkflow_checkpoint(...)  # Returns coroutine!

# Good: Await the coroutine
result = await handler.resume_subworkflow_checkpoint(...)

# Or use asyncio.run if not in async context
import asyncio
result = asyncio.run(handler.resume_subworkflow_checkpoint(...))
```

❌ **Don't Store Sensitive Data in State**

```python
# Bad: Storing passwords in state
def bad_node(state: WorkflowState) -> dict:
    return {
        "custom_data": {
            "password": "secret123",  # Stored in checkpoint!
            "api_key": "sk-..."
        }
    }

# Good: Use environment variables or secure storage
import os
def good_node(state: WorkflowState) -> dict:
    api_key = os.environ.get("API_KEY")
    # Use but don't store
    result = api_call(api_key)
    return {
        "node_outputs": {
            "node": {"raw": result, "fields": {}}
        }
    }
```

❌ **Don't Ignore Rate Limits**

```python
# Bad: Not respecting rate limits
for i in range(1000):
    trigger_published_workflow(identifier)  # May hit rate limit!

# Good: Implement backoff and retry
import time
def trigger_with_rate_limit(identifier, max_retries=3):
    for attempt in range(max_retries):
        response = trigger_published_workflow(identifier)
        if response.status_code == 429:  # Rate limited
            retry_after = int(response.headers.get("Retry-After", 60))
            time.sleep(retry_after)
            continue
        return response
    raise Exception("Rate limit exceeded")
```

---

## Related Documentation

### Related Services

- [Execution Service](./execution.md) - Workflow execution engine and coordination
- [Graph Service](./graph.md) - Graph building and management
- [Subgraph Service](./subgraph.md) - Subworkflow delegation and execution
- [Checkpoint Service](./checkpoint.md) - Checkpoint management and metadata
- [Database Service](./database.md) - Database operations and migrations

### Related API Modules

- [Workflow Publishing API](../agents-guide/api/workflow.md) - HTTP endpoints for workflow publishing
- [HTTP Execution API](../agents-guide/api/http_execution.md) - Endpoints for triggering published workflows
- [Authentication API](../agents-guide/api/auth.md) - Personal Access Token management

### Architecture Documentation

- [LangGraph Integration](../architecture/langgraph.md) - How LangGraph is integrated
- [State Management](../architecture/state_management.md) - State flow architecture
- [Checkpoint System](../architecture/checkpoints.md) - Checkpoint and resumption design

### External Documentation

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) - LangGraph state management
- [LangGraph Reducers](https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers) - Custom reducer functions
- [TypedDict Documentation](https://docs.python.org/3/library/typing.html#typing.TypedDict) - Python TypedDict usage

---

## Summary

The workflow service module provides comprehensive workflow lifecycle management for AgenticStudio, spanning publication,
resumption, and state management. It serves as the bridge between workflow definitions and their execution, enabling
workflows to be exposed as HTTP APIs, resumed from checkpoints, and tracked through structured state schemas.

**Key Features:**

- **Workflow Publishing:** Expose workflows as authenticated HTTP endpoints with rate limiting, CORS, and access logging
- **Subworkflow Resumption:** Resume interrupted subworkflow executions from checkpoints with result propagation
- **State Management:** Structured TypedDict schemas with custom reducers for LangGraph integration
- **Access Control:** User-based workflow access with Personal Access Token authentication
- **Audit Trails:** Comprehensive access logging for monitoring and debugging

**Primary Use Cases:**

- Publishing internal AI workflows as public or authenticated APIs
- Creating multi-tenant workflow endpoints with user-specific access
- Resuming complex multi-agent workflows from checkpoints
- Tracking workflow execution with structured state and metadata
- Implementing human-in-the-loop patterns with checkpoint interrupts

**When to Use This Service:**

- **Publishing Submodule:** When you need to expose workflows as HTTP endpoints for external consumption
- **Resumption Submodule:** When implementing subworkflow delegation patterns with checkpoint support
- **State Submodule:** When building LangGraph workflows that need structured state management

The workflow service is a core component of AgenticStudio's workflow execution architecture, working closely with the
execution engine, graph builder, and checkpoint system to provide a complete workflow lifecycle solution.
