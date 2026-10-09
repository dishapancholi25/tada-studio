# Common Service Module

## Overview

The common service module provides shared utility functions that are used across graph and subgraph execution in the
AgenticStudio backend. It maintains a clean dependency hierarchy by centralising common functionality that would otherwise
create circular dependencies between execution services.

**Location:** [backend/services/common/](../../backend/services/common/)

**Primary Responsibilities:**

- Tool name normalisation and type mapping for node execution
- Response content extraction from various message types
- WebSocket notification helpers for real-time execution updates
- Shared utilities to prevent code duplication across execution contexts

**Key Use Cases:**

- Mapping synthetic tool names to canonical names and node types
- Extracting text responses from AIMessage, dict, or string responses
- Sending standardised WebSocket notifications during node execution
- Maintaining consistency across main graph and subgraph execution flows

## Architecture

### Module Structure

```
backend/services/common/
├── __init__.py                  # Empty package marker
├── tracking/                    # Reserved for future tracking functionality
│   └── __init__.py
└── utils/                       # Core utility functions
    ├── __init__.py              # Exports all public functions
    ├── response_extractor.py   # Response content extraction logic
    ├── tool_type_mapper.py     # Tool name to node type mapping
    └── websocket_notifier.py   # WebSocket notification helpers
```

**File Descriptions:**

| File                                                                                     | Purpose                                                                  |
|------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| [utils/**init**.py](../../backend/services/common/utils/__init__.py)                     | Exports public API for all utility functions                             |
| [utils/response_extractor.py](../../backend/services/common/utils/response_extractor.py) | Extracts text content from various response types (AIMessage, dict, str) |
| [utils/tool_type_mapper.py](../../backend/services/common/utils/tool_type_mapper.py)     | Maps tool names to NodeType values, handles synthetic names              |
| [utils/websocket_notifier.py](../../backend/services/common/utils/websocket_notifier.py) | Sends WebSocket notifications for node lifecycle events                  |
| [tracking/**init**.py](../../backend/services/common/tracking/__init__.py)               | Reserved for future tracking features                                    |

### Design Patterns

**Utility Module Pattern:**
The common service follows a pure utility module pattern with stateless functions. There are no classes, instances, or
global state — only pure functions that can be imported and called directly.

**Separation of Concerns:**

- **Tool Mapping:** Handles tool name normalisation and type detection
- **Response Extraction:** Handles response content extraction with fallback logic
- **WebSocket Notifications:** Handles real-time client updates

**Dependency Inversion:**
This module is designed to be a leaf node in the dependency graph. It depends on:

- `backend.services.config` (logging)
- `backend.services.websocket` (notifications)
- `langchain_core.messages` (AIMessage type)

But it does NOT depend on execution or graph services, preventing circular dependencies.

**Component Relationships:**

```
┌─────────────────────────────────────────────────────────┐
│             Execution Services Layer                    │
│  (execution/, subgraph/, checkpoint/)                   │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ imports utilities
                  ▼
┌─────────────────────────────────────────────────────────┐
│             Common Service Module                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Tool Mapper  │  │  Response    │  │  WebSocket   │  │
│  │              │  │  Extractor   │  │  Notifier    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ depends on
                  ▼
┌─────────────────────────────────────────────────────────┐
│        Foundation Services                              │
│  (config, websocket, langchain_core)                    │
└─────────────────────────────────────────────────────────┘
```

### Dependencies

**Internal Dependencies:**

- `backend.services.config` - Logging infrastructure
- `backend.services.websocket` - WebSocket notification system

**External Dependencies:**

- `langchain_core.messages` - AIMessage type for response handling
- Python standard library: `typing`, `datetime`

**No Database Dependencies:**
This module does not interact with the database directly. Database operations are handled by calling services.

**No Environment Variables:**
This module does not use environment variables directly. Configuration is handled by dependency services.

## Public API

### Exported Functions

All functions are exported from `backend.services.common.utils`:

**Tool Type Mapping:**

- `extract_base_tool_name(synthetic_tool_name: str) -> str` - Extract canonical tool name from synthetic names
- `get_tool_node_type(tool_name: str) -> str` - Map tool name to NodeType string
- `TOOL_TYPE_PATTERNS` - Dictionary mapping node types to tool name patterns

**Response Extraction:**

- `extract_response_content(response: Any, agent_name: str, tool_execution_tracker: List[dict]) -> str` - Extract text
  content from various response types

**WebSocket Notifications:**

- `send_node_start_notification(...)` - Send notification when node starts executing
- `send_node_complete_notification(...)` - Send notification when node completes successfully
- `send_node_error_notification(...)` - Send notification when node encounters error

### Constants and Configuration

#### `TOOL_TYPE_PATTERNS`

Dictionary mapping NodeType values to tool name patterns for recognition.

```python
TOOL_TYPE_PATTERNS = {
    "DATABASE_QUERY": ["query_database", "database", "query_db"],
    "WEB_SEARCH": ["search_web", "web_search"],
    "DOCUMENT_SEARCH": ["search_documents", "document_search"],
    "HTTP_REQUEST": ["http_request", "api_call"],
    "MCP_SERVER": ["mcp"],
}
```

**Purpose:** Used by `get_tool_node_type()` to determine the appropriate NodeType for a given tool name.

### Exceptions

This module does not define custom exceptions. It uses standard Python exceptions:

- `ValueError` - Raised by `extract_response_content()` if response cannot be extracted
- Standard exceptions are logged and handled gracefully in notification functions

## Functions

### Tool Type Mapping

#### `extract_base_tool_name()`

Extract the canonical base tool name from a synthetic tool name with UUID suffix.

**Signature:**

```python
def extract_base_tool_name(
    synthetic_tool_name: str,
) -> str:
    """
    Extract the base tool name from a synthetic tool name.

    Synthetic tool names often have UUID suffixes (e.g., "query_db_d252e908").
    This function removes the suffix and maps to the canonical tool name.
    """
```

**Parameters:**

- `synthetic_tool_name` (str) - The synthetic tool name, possibly with UUID suffix

**Returns:**

- `str` - The canonical base tool name without synthetic suffixes

**Examples:**

```python
from backend.services.common.utils import extract_base_tool_name

# Remove UUID suffix and normalise
base_name = extract_base_tool_name("query_db_d252e908")
# Returns: "query_database"

# Handle web search tools
base_name = extract_base_tool_name("web_search_abc12345")
# Returns: "web_search"

# No suffix - returns as-is
base_name = extract_base_tool_name("simple_tool")
# Returns: "simple_tool"
```

**Behaviour:**

- Checks if the last underscore-separated part is an 8-character hex string (UUID suffix)
- Maps common patterns to canonical names (query_db → query_database)
- Returns the original name if no synthetic pattern is detected
- Does not raise exceptions; handles all string inputs gracefully

**Use Cases:**

- Normalising tool names before database storage
- Matching tool executions to their definitions
- Cleaning up tool names for display in UI
- Mapping tool calls to their corresponding node types

---

#### `get_tool_node_type()`

Map a tool name to its corresponding NodeType string for database and UI display.

**Signature:**

```python
def get_tool_node_type(
    tool_name: str,
) -> str:
    """
    Map a tool name to its corresponding NodeType.

    This function checks tool name patterns to determine the appropriate
    node type for database recording and visualisation.
    """
```

**Parameters:**

- `tool_name` (str) - The tool name (base or synthetic)

**Returns:**

- `str` - The NodeType as a string (e.g., "DATABASE_QUERY", "WEB_SEARCH", "TOOL")

**Examples:**

```python
from backend.services.common.utils import get_tool_node_type

# Database query tools
node_type = get_tool_node_type("query_database")
# Returns: "DATABASE_QUERY"

# Web search with synthetic suffix
node_type = get_tool_node_type("web_search_abc12345")
# Returns: "WEB_SEARCH"

# Custom tool without pattern match
node_type = get_tool_node_type("custom_business_logic_tool")
# Returns: "TOOL"
```

**Behaviour:**

- Converts tool name to lowercase for pattern matching
- Checks against patterns in `TOOL_TYPE_PATTERNS`
- Returns specific node type if pattern matches
- Returns generic "TOOL" as fallback for unknown tools
- Logs debug messages for pattern matching results

**Use Cases:**

- Determining node type when creating database execution records
- Categorising tool executions for analytics
- Displaying appropriate icons in the UI
- Filtering execution history by tool type

### Response Extraction

#### `extract_response_content()`

Extract text content from various response types with fallback logic.

**Signature:**

```python
def extract_response_content(
    response: Any,
    agent_name: str,
    tool_execution_tracker: List[dict],
) -> str:
    """
    Extract text content from a response object.

    Handles different response types (AIMessage, objects with content attribute,
    strings) and provides fallback logic if the response is empty.
    """
```

**Parameters:**

- `response` (Any) - The response object from agent execution (AIMessage, dict, str, etc.)
- `agent_name` (str) - Name of the agent (used for logging)
- `tool_execution_tracker` (List[dict]) - List of tool executions (used for fallback if response is empty)

**Returns:**

- `str` - The extracted response content as a string

**Raises:**

- Logs errors but does not raise exceptions; always returns a string

**Examples:**

```python
from backend.services.common.utils import extract_response_content
from langchain_core.messages import AIMessage

# Extract from AIMessage
response = AIMessage(content="Analysis complete. Found 3 issues.")
tool_tracker = []
content = extract_response_content(response, "AnalysisAgent", tool_tracker)
# Returns: "Analysis complete. Found 3 issues."

# Handle empty response with tool results fallback
empty_response = AIMessage(content="")
tool_tracker = [
    {"result": "Database query returned 10 rows"},
    {"result": "Validation passed"}
]
content = extract_response_content(empty_response, "DataAgent", tool_tracker)
# Returns: "Based on my research: Database query returned 10 rows Validation passed"

# Handle string response
simple_response = "Task completed successfully"
content = extract_response_content(simple_response, "SimpleAgent", [])
# Returns: "Task completed successfully"
```

**Behaviour:**

- **AIMessage handling:** Extracts `.content` and checks for unprocessed tool calls
- **Generic object handling:** Checks for `.content` attribute
- **String handling:** Converts to string if no content attribute
- **Empty response handling:** Falls back to tool execution results
- **Final fallback:** Returns default error message if all else fails
- **Logging:** Logs detailed information about response type and extraction process

**Use Cases:**

- Extracting final agent responses for database storage
- Handling various LangChain message types uniformly
- Providing user-facing error messages when agents fail
- Constructing responses from tool results when agent doesn't provide text

### WebSocket Notifications

#### `send_node_start_notification()`

Send a WebSocket notification when a node starts execution.

**Signature:**

```python
async def send_node_start_notification(
    execution_id: str,
    node_id: str,
    node_name: str,
    node_type: str,
    is_sub_agent: bool = False,
    parent_agent_id: Optional[str] = None,
    database_node_id: Optional[int] = None,
) -> bool:
    """Send a WebSocket notification when a node starts execution."""
```

**Parameters:**

- `execution_id` (str) - The parent execution ID
- `node_id` (str) - The node's unique ID
- `node_name` (str) - The node's display name
- `node_type` (str) - The node type (e.g., "AGENT", "TOOL", "DATABASE_QUERY")
- `is_sub_agent` (bool) - Whether this is a sub-agent (default: False)
- `parent_agent_id` (Optional[str]) - The parent agent's ID if this is a sub-agent (default: None)
- `database_node_id` (Optional[int]) - The database node execution ID if available (default: None)

**Returns:**

- `bool` - True if notification was sent successfully, False otherwise

**Examples:**

```python
from backend.services.common.utils import send_node_start_notification

# Send notification for main agent starting
success = await send_node_start_notification(
    execution_id="exec_abc123",
    node_id="agent_node_1",
    node_name="Data Analysis Agent",
    node_type="AGENT",
)

# Send notification for sub-agent starting
success = await send_node_start_notification(
    execution_id="exec_abc123",
    node_id="sub_agent_2",
    node_name="Validation Agent",
    node_type="AGENT",
    is_sub_agent=True,
    parent_agent_id="agent_node_1",
    database_node_id=42,
)

# Send notification for tool starting
success = await send_node_start_notification(
    execution_id="exec_abc123",
    node_id="tool_1",
    node_name="Database Query",
    node_type="DATABASE_QUERY",
)
```

**Behaviour:**

- Validates that `execution_id` and `ws_notifier` are available
- Calls `ws_notifier.on_node_start()` with all parameters
- Logs success or failure with appropriate log level
- Returns False without raising if notification cannot be sent
- Handles exceptions gracefully to prevent execution interruption

**Use Cases:**

- Updating UI when agent execution starts
- Tracking execution progress in real-time
- Monitoring sub-agent delegation chains
- Debugging execution flow issues

---

#### `send_node_complete_notification()`

Send a WebSocket notification when a node completes execution successfully.

**Signature:**

```python
async def send_node_complete_notification(
    execution_id: str,
    node_id: str,
    node_name: str,
    output: Dict[str, Any],
    node_type: str,
    duration_seconds: Optional[float] = None,
    input_data: Optional[Dict[str, Any]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    is_sub_agent: bool = False,
    parent_agent_id: Optional[str] = None,
    database_node_id: Optional[int] = None,
) -> bool:
    """Send a WebSocket notification when a node completes execution."""
```

**Parameters:**

- `execution_id` (str) - The parent execution ID
- `node_id` (str) - The node's unique ID
- `node_name` (str) - The node's display name
- `output` (Dict[str, Any]) - The node's output data
- `node_type` (str) - The node type (e.g., "AGENT", "TOOL")
- `duration_seconds` (Optional[float]) - Execution duration in seconds (default: None)
- `input_data` (Optional[Dict[str, Any]]) - Input data passed to the node (default: None)
- `start_time` (Optional[str]) - ISO format start time (default: None)
- `end_time` (Optional[str]) - ISO format end time (default: None)
- `input_tokens` (Optional[int]) - Number of input tokens used (default: None)
- `output_tokens` (Optional[int]) - Number of output tokens generated (default: None)
- `total_tokens` (Optional[int]) - Total tokens used (default: None)
- `is_sub_agent` (bool) - Whether this is a sub-agent (default: False)
- `parent_agent_id` (Optional[str]) - The parent agent's ID if applicable (default: None)
- `database_node_id` (Optional[int]) - The database node execution ID if available (default: None)

**Returns:**

- `bool` - True if notification was sent successfully, False otherwise

**Examples:**

```python
from backend.services.common.utils import send_node_complete_notification
from datetime import datetime, timezone

# Send completion notification with full details
success = await send_node_complete_notification(
    execution_id="exec_abc123",
    node_id="agent_node_1",
    node_name="Data Analysis Agent",
    output={"response": "Analysis complete", "findings": ["issue1", "issue2"]},
    node_type="AGENT",
    duration_seconds=2.5,
    input_data={"task": "Analyse data quality"},
    start_time="2025-10-26T10:00:00Z",
    end_time="2025-10-26T10:00:02.5Z",
    input_tokens=150,
    output_tokens=300,
    total_tokens=450,
)

# Minimal completion notification
success = await send_node_complete_notification(
    execution_id="exec_abc123",
    node_id="tool_1",
    node_name="Database Query",
    output={"rows": 10, "data": [...]},
    node_type="DATABASE_QUERY",
)
```

**Behaviour:**

- Validates that `execution_id` and `ws_notifier` are available
- Calls `ws_notifier.on_node_complete()` with all parameters
- Logs success or failure with node name
- Returns False without raising if notification cannot be sent
- Handles exceptions gracefully

**Use Cases:**

- Displaying execution results in real-time UI
- Tracking token usage for cost monitoring
- Recording execution duration for performance analysis
- Showing sub-agent outputs in delegation chains

---

#### `send_node_error_notification()`

Send a WebSocket notification when a node encounters an error during execution.

**Signature:**

```python
async def send_node_error_notification(
    execution_id: str,
    node_id: str,
    node_name: str,
    error: str,
) -> bool:
    """Send a WebSocket notification when a node encounters an error."""
```

**Parameters:**

- `execution_id` (str) - The parent execution ID
- `node_id` (str) - The node's unique ID
- `node_name` (str) - The node's display name
- `error` (str) - The error message

**Returns:**

- `bool` - True if notification was sent successfully, False otherwise

**Examples:**

```python
from backend.services.common.utils import send_node_error_notification

# Send error notification
success = await send_node_error_notification(
    execution_id="exec_abc123",
    node_id="agent_node_1",
    node_name="Data Analysis Agent",
    error="Database connection timeout after 30 seconds",
)

# In exception handler
try:
    result = await execute_agent(agent_node, state)
except Exception as e:
    await send_node_error_notification(
        execution_id=state["parent_execution_id"],
        node_id=agent_node.uniq_id,
        node_name=agent_node.name,
        error=str(e),
    )
    raise
```

**Behaviour:**

- Validates that `execution_id` and `ws_notifier` are available
- Calls `ws_notifier.on_node_error()` with error details
- Logs error notification success or failure
- Returns False without raising if notification cannot be sent
- Handles exceptions in notification sending gracefully

**Use Cases:**

- Alerting users to execution failures in real-time
- Displaying error messages in the UI
- Debugging failed executions
- Triggering error recovery workflows

## Configuration

### No Configuration Required

This module does not require any configuration. It is a pure utility module that depends on:

- **Logging:** Provided by `backend.services.config.get_logger()`
- **WebSocket:** Provided by `backend.services.websocket.notifier`

### Initialisation Patterns

**Basic Usage:**

```python
from backend.services.common.utils import (
    extract_base_tool_name,
    get_tool_node_type,
    extract_response_content,
    send_node_start_notification,
    send_node_complete_notification,
    send_node_error_notification,
)

# Functions are ready to use immediately
tool_type = get_tool_node_type("query_database")
```

**No Dependency Injection:**
This module uses functions, not classes, so there's no dependency injection pattern. Dependencies (logger, websocket
notifier) are imported directly by the module.

## Error Handling

### Exception Handling Pattern

This module follows a **resilient error handling pattern**:

- WebSocket notification functions catch and log exceptions but never raise
- Response extraction handles all response types gracefully with fallbacks
- Tool mapping functions handle unexpected input safely

### Error Handling in Calling Code

**Recommended Pattern:**

```python
from backend.services.common.utils import (
    extract_response_content,
    send_node_start_notification,
    send_node_error_notification,
)

try:
    # Send start notification (non-critical)
    await send_node_start_notification(
        execution_id=exec_id,
        node_id=node.uniq_id,
        node_name=node.name,
        node_type="AGENT",
    )

    # Execute agent (critical)
    response = await execute_agent(node, state)

    # Extract response (critical, but has fallbacks)
    content = extract_response_content(
        response=response,
        agent_name=node.name,
        tool_execution_tracker=tool_tracker,
    )

except Exception as e:
    # Send error notification (non-critical)
    await send_node_error_notification(
        execution_id=exec_id,
        node_id=node.uniq_id,
        node_name=node.name,
        error=str(e),
    )
    # Re-raise critical errors
    raise
```

**Key Principles:**

- Notification failures should never interrupt execution
- Response extraction should always return a string (even if it's an error message)
- Tool mapping should always return a valid node type (default to "TOOL")

## Integration Patterns

### Integration with Subgraph Execution

The common service module is heavily used in subgraph execution for agents and workflows.

**Agent Execution Handler:**

```python
# From backend/services/subgraph/agent/execution_handler.py
from backend.services.common.utils import (
    extract_response_content,
    send_node_start_notification,
    send_node_complete_notification,
    send_node_error_notification,
)

async def execute_agent_in_subgraph(
    state: SubAgentState,
    agent_node: EnhancedNodeData,
    graph_manager: Any,
) -> Dict[str, Any]:
    """Execute an agent within a subgraph."""

    # Send start notification
    await send_node_start_notification(
        execution_id=state["parent_execution_id"],
        node_id=agent_node.uniq_id,
        node_name=agent_node.name,
        node_type="AGENT",
        is_sub_agent=True,
        parent_agent_id=state["parent_node_id"],
    )

    try:
        # Execute agent
        result = await execute_agent(agent_node, state, graph_manager)

        # Extract response
        response_content = extract_response_content(
            response=result,
            agent_name=agent_node.name,
            tool_execution_tracker=tool_tracker,
        )

        # Send completion notification
        await send_node_complete_notification(
            execution_id=state["parent_execution_id"],
            node_id=agent_node.uniq_id,
            node_name=agent_node.name,
            output={"response": response_content},
            node_type="AGENT",
            duration_seconds=duration,
        )

    except Exception as e:
        # Send error notification
        await send_node_error_notification(
            execution_id=state["parent_execution_id"],
            node_id=agent_node.uniq_id,
            node_name=agent_node.name,
            error=str(e),
        )
        raise
```

### Integration with Tool Tracking

**Tool Type Mapping:**

```python
# From backend/services/subgraph/agent/tool_tracker.py
from backend.services.common.utils import (
    extract_base_tool_name,
    get_tool_node_type,
)

async def track_tool_executions(
    tool_calls: List[ToolCall],
    parent_db_execution_id: int,
) -> List[dict]:
    """Track tool executions in database."""

    tracked_executions = []

    for tool_call in tool_calls:
        # Extract base tool name
        base_tool_name = extract_base_tool_name(tool_call.name)

        # Determine correct node type
        node_type = get_tool_node_type(base_tool_name)

        # Create database record
        tool_exec = await create_tool_execution_record(
            tool_name=base_tool_name,
            node_type=node_type,
            parent_execution_id=parent_db_execution_id,
        )

        tracked_executions.append(tool_exec)

    return tracked_executions
```

### Integration with Main Execution

**Workflow Execution:**

```python
# From backend/services/execution/workflow_executor.py
from backend.services.common.utils import send_node_start_notification

async def execute_workflow_node(
    node: EnhancedNodeData,
    execution_id: str,
) -> Dict[str, Any]:
    """Execute a workflow node."""

    # Notify UI of node start
    await send_node_start_notification(
        execution_id=execution_id,
        node_id=node.uniq_id,
        node_name=node.name,
        node_type=node.type.value,
    )

    # Execute node logic
    result = await execute_node(node)

    return result
```

### Dependency Flow

```
┌────────────────────────────────────────┐
│     API Layer (FastAPI Routes)        │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  Execution Services                    │
│  - workflow_executor.py                │
│  - resume_handler.py                   │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  Subgraph Services                     │
│  - agent/execution_handler.py          │
│  - workflow/execution_handler.py       │
│  - agent/tool_tracker.py               │
└────────────────┬───────────────────────┘
                 │
                 │ Uses common utilities
                 ▼
┌────────────────────────────────────────┐
│  Common Service Module                 │
│  - Tool mapping                        │
│  - Response extraction                 │
│  - WebSocket notifications             │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  Foundation Services                   │
│  - config (logging)                    │
│  - websocket (notifier)                │
└────────────────────────────────────────┘
```

**Services that depend on common:**

- `backend.services.execution` - Main workflow execution
- `backend.services.subgraph` - Sub-agent and subgraph execution
- `backend.services.execution.checkpoint` - Checkpoint handlers

**Services that common depends on:**

- `backend.services.config` - Logging
- `backend.services.websocket` - Real-time notifications

## Usage Examples

### Example 1: Tool Name Normalisation

```python
from backend.services.common.utils import (
    extract_base_tool_name,
    get_tool_node_type,
)

# Handle synthetic tool names from agent execution
synthetic_tool_name = "query_db_d252e908"

# Step 1: Extract base name
base_name = extract_base_tool_name(synthetic_tool_name)
# Result: "query_database"

# Step 2: Determine node type
node_type = get_tool_node_type(base_name)
# Result: "DATABASE_QUERY"

# Use for database storage
tool_execution_record = {
    "tool_name": base_name,
    "node_type": node_type,
    "raw_tool_name": synthetic_tool_name,
}
```

### Example 2: Response Extraction with Fallback

```python
from backend.services.common.utils import extract_response_content
from langchain_core.messages import AIMessage

# Scenario: Agent returns empty content but has tool results
response = AIMessage(content="", tool_calls=[...])

tool_execution_tracker = [
    {
        "tool": "query_database",
        "result": "Found 15 matching records",
    },
    {
        "tool": "web_search",
        "result": "Latest information: Product launched Q3 2025",
    },
]

# Extract with fallback to tool results
content = extract_response_content(
    response=response,
    agent_name="ResearchAgent",
    tool_execution_tracker=tool_execution_tracker,
)

# Result: "Based on my research: Found 15 matching records Latest information: Product launched Q3 2025"
print(content)
```

### Example 3: Complete Node Execution Flow

```python
from datetime import datetime, timezone
from backend.services.common.utils import (
    send_node_start_notification,
    send_node_complete_notification,
    send_node_error_notification,
    extract_response_content,
)

async def execute_agent_node_with_tracking(
    node_id: str,
    node_name: str,
    execution_id: str,
    agent_executor: Any,
) -> Dict[str, Any]:
    """Execute an agent node with full tracking and notifications."""

    start_time = datetime.now(timezone.utc)
    tool_tracker = []

    # Step 1: Send start notification
    await send_node_start_notification(
        execution_id=execution_id,
        node_id=node_id,
        node_name=node_name,
        node_type="AGENT",
    )

    try:
        # Step 2: Execute agent
        response = await agent_executor.ainvoke({
            "input": "Analyse the data",
        })

        # Step 3: Extract response content
        content = extract_response_content(
            response=response,
            agent_name=node_name,
            tool_execution_tracker=tool_tracker,
        )

        # Step 4: Calculate duration
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        # Step 5: Send completion notification
        await send_node_complete_notification(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            output={"response": content},
            node_type="AGENT",
            duration_seconds=duration,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
        )

        return {"success": True, "response": content}

    except Exception as e:
        # Step 6: Send error notification
        await send_node_error_notification(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            error=str(e),
        )

        return {"success": False, "error": str(e)}
```

### Example 4: Batch Tool Processing

```python
from backend.services.common.utils import (
    extract_base_tool_name,
    get_tool_node_type,
)
from typing import List, Dict

def process_tool_calls_batch(
    tool_calls: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Process multiple tool calls and normalise their names and types."""

    processed_tools = []

    for tool_call in tool_calls:
        synthetic_name = tool_call["name"]

        # Normalise tool name
        base_name = extract_base_tool_name(synthetic_name)

        # Determine node type
        node_type = get_tool_node_type(base_name)

        processed_tools.append({
            "synthetic_name": synthetic_name,
            "canonical_name": base_name,
            "node_type": node_type,
            "args": tool_call.get("args", {}),
        })

    return processed_tools

# Example usage
tool_calls = [
    {"name": "query_db_abc123", "args": {"query": "SELECT * FROM users"}},
    {"name": "web_search_def456", "args": {"query": "latest news"}},
    {"name": "custom_tool", "args": {"param": "value"}},
]

processed = process_tool_calls_batch(tool_calls)
# Result:
# [
#   {"synthetic_name": "query_db_abc123", "canonical_name": "query_database", "node_type": "DATABASE_QUERY", ...},
#   {"synthetic_name": "web_search_def456", "canonical_name": "web_search", "node_type": "WEB_SEARCH", ...},
#   {"synthetic_name": "custom_tool", "canonical_name": "custom_tool", "node_type": "TOOL", ...},
# ]
```

## Performance Considerations

### Performance Characteristics

**Tool Mapping Functions:**

- `extract_base_tool_name()` - O(1) complexity, simple string operations
- `get_tool_node_type()` - O(n) where n is number of patterns, but n is small (typically 5-10 patterns)
- Both functions are CPU-bound with minimal memory usage

**Response Extraction:**

- `extract_response_content()` - O(1) for type checking, O(m) for tool result iteration where m is number of tool
  executions
- Memory usage: proportional to response content size
- CPU-bound for string operations

**WebSocket Notifications:**

- Network I/O bound
- Async operations don't block execution
- Failure to send notifications doesn't impact execution performance

### Optimisation Tips

#### Tip 1: Avoid Redundant Tool Name Extraction

**Problem:**

```python
# Inefficient: Extracting base name multiple times
for tool_call in tool_calls:
    if extract_base_tool_name(tool_call.name) == "query_database":
        node_type = get_tool_node_type(extract_base_tool_name(tool_call.name))
```

**Solution:**

```python
# Efficient: Extract once, reuse
for tool_call in tool_calls:
    base_name = extract_base_tool_name(tool_call.name)
    if base_name == "query_database":
        node_type = get_tool_node_type(base_name)
```

#### Tip 2: Batch WebSocket Notifications When Possible

**Context:**
WebSocket notifications are async and non-blocking, but you should still avoid sending excessive notifications in tight
loops.

```python
# If you need to notify about multiple nodes, consider batching
# (Note: Current implementation sends individual notifications,
#  but future versions may support batching)

# Current pattern (acceptable)
for node in completed_nodes:
    await send_node_complete_notification(
        execution_id=exec_id,
        node_id=node.id,
        node_name=node.name,
        output=node.output,
        node_type=node.type,
    )
```

### Async/Await Support

All WebSocket notification functions are async:

```python
from backend.services.common.utils import send_node_start_notification

async def my_execution_function():
    # Async context required
    success = await send_node_start_notification(
        execution_id="exec_123",
        node_id="node_1",
        node_name="Agent",
        node_type="AGENT",
    )
```

**Synchronous code cannot use these functions directly.** If you need to send notifications from sync code, you must use
`asyncio.create_task()` or similar.

### No Connection Pooling

This module does not manage connections. The `backend.services.websocket` module handles WebSocket connection
management.

### No Caching

These utility functions do not use caching because:

- Tool name extraction is already O(1) and extremely fast
- Response extraction is called once per execution
- WebSocket notifications must be sent in real-time

## Testing Patterns

### Unit Testing

**Test Tool Mapping:**

```python
import pytest
from backend.services.common.utils import (
    extract_base_tool_name,
    get_tool_node_type,
)

def test_extract_base_tool_name_with_uuid_suffix():
    """Test extraction of base tool name from synthetic name."""
    result = extract_base_tool_name("query_db_d252e908")
    assert result == "query_database"

def test_extract_base_tool_name_without_suffix():
    """Test handling of non-synthetic tool names."""
    result = extract_base_tool_name("custom_tool")
    assert result == "custom_tool"

def test_get_tool_node_type_database():
    """Test mapping of database tools."""
    result = get_tool_node_type("query_database")
    assert result == "DATABASE_QUERY"

def test_get_tool_node_type_unknown():
    """Test fallback for unknown tool types."""
    result = get_tool_node_type("unknown_tool_xyz")
    assert result == "TOOL"
```

**Test Response Extraction:**

```python
from backend.services.common.utils import extract_response_content
from langchain_core.messages import AIMessage

def test_extract_response_from_ai_message():
    """Test extraction from AIMessage."""
    response = AIMessage(content="Test response")
    result = extract_response_content(response, "TestAgent", [])
    assert result == "Test response"

def test_extract_response_empty_with_tool_fallback():
    """Test fallback to tool results when response is empty."""
    response = AIMessage(content="")
    tool_tracker = [{"result": "Tool output"}]
    result = extract_response_content(response, "TestAgent", tool_tracker)
    assert "Tool output" in result

def test_extract_response_final_fallback():
    """Test final fallback when all else fails."""
    response = AIMessage(content="")
    result = extract_response_content(response, "TestAgent", [])
    assert "unable to complete" in result.lower()
```

### Mocking WebSocket Notifications

```python
import pytest
from unittest.mock import AsyncMock, patch
from backend.services.common.utils import send_node_start_notification

@pytest.mark.asyncio
@patch('backend.services.common.utils.websocket_notifier.ws_notifier')
async def test_send_node_start_notification_success(mock_notifier):
    """Test successful notification sending."""
    mock_notifier.on_node_start = AsyncMock()

    result = await send_node_start_notification(
        execution_id="exec_123",
        node_id="node_1",
        node_name="Test Node",
        node_type="AGENT",
    )

    assert result is True
    mock_notifier.on_node_start.assert_called_once()

@pytest.mark.asyncio
@patch('backend.services.common.utils.websocket_notifier.ws_notifier')
async def test_send_node_start_notification_failure(mock_notifier):
    """Test notification sending with WebSocket failure."""
    mock_notifier.on_node_start = AsyncMock(side_effect=Exception("Connection error"))

    # Should not raise, should return False
    result = await send_node_start_notification(
        execution_id="exec_123",
        node_id="node_1",
        node_name="Test Node",
        node_type="AGENT",
    )

    assert result is False
```

### Integration Testing

```python
import pytest
from backend.services.common.utils import (
    extract_base_tool_name,
    get_tool_node_type,
    extract_response_content,
)

@pytest.mark.integration
def test_tool_processing_pipeline():
    """Integration test for complete tool processing."""
    # Simulate tool call from agent
    synthetic_tool_name = "query_db_abc12345"

    # Step 1: Extract base name
    base_name = extract_base_tool_name(synthetic_tool_name)

    # Step 2: Get node type
    node_type = get_tool_node_type(base_name)

    # Verify complete pipeline
    assert base_name == "query_database"
    assert node_type == "DATABASE_QUERY"
```

## Best Practices

### Do's

✅ **Use tool mapping for all synthetic tool names**

```python
from backend.services.common.utils import extract_base_tool_name, get_tool_node_type

# Always normalise tool names before storage
for tool_call in agent_response.tool_calls:
    canonical_name = extract_base_tool_name(tool_call.name)
    node_type = get_tool_node_type(canonical_name)

    await store_tool_execution(
        name=canonical_name,
        type=node_type,
    )
```

✅ **Always provide tool_execution_tracker for response extraction**

```python
from backend.services.common.utils import extract_response_content

# Track tools during execution
tool_tracker = []

# Execute agent (tracker populated by reference)
response = await agent.ainvoke(input, tool_tracker=tool_tracker)

# Extract with fallback support
content = extract_response_content(
    response=response,
    agent_name="MyAgent",
    tool_execution_tracker=tool_tracker,  # Enables fallback
)
```

✅ **Send notifications at all key execution points**

```python
from backend.services.common.utils import (
    send_node_start_notification,
    send_node_complete_notification,
    send_node_error_notification,
)

# Always notify: start, complete, error
await send_node_start_notification(...)

try:
    result = await execute_node(...)
    await send_node_complete_notification(...)
except Exception as e:
    await send_node_error_notification(...)
    raise
```

### Don'ts

❌ **Don't assume tool names are canonical**

```python
# BAD: Assuming tool name is already normalised
if tool_call.name == "query_database":  # May actually be "query_db_abc123"
    ...

# GOOD: Always normalise first
base_name = extract_base_tool_name(tool_call.name)
if base_name == "query_database":
    ...
```

❌ **Don't ignore WebSocket notification failures in logs**

```python
# BAD: Not checking notification result
await send_node_start_notification(...)

# GOOD: Log if notifications are consistently failing
success = await send_node_start_notification(...)
if not success:
    logger.warning("WebSocket notifications may be down")
```

❌ **Don't modify TOOL_TYPE_PATTERNS directly**

```python
# BAD: Modifying shared constant
from backend.services.common.utils import TOOL_TYPE_PATTERNS
TOOL_TYPE_PATTERNS["NEW_TYPE"] = ["pattern"]  # Affects global state!

# GOOD: Extend in your own module if needed
CUSTOM_PATTERNS = {
    **TOOL_TYPE_PATTERNS,
    "NEW_TYPE": ["pattern"],
}
```

## Related Documentation

### Related Services

- [Config Service](./config.md) - Logging infrastructure used by common utilities
- [WebSocket Service](./websocket.md) - Real-time notification delivery
- [Execution Service](./execution.md) - Main consumer of common utilities
- [Subgraph Service](./subgraph.md) - Heavy user of tool mapping and notifications

### Related API Modules

- [Graph API](../agents-guide/api/graph.md) - Workflow execution that uses common utilities
- [WebSocket API](../agents-guide/api/websocket.md) - WebSocket connection management

### External Documentation

- [LangChain Messages](https://python.langchain.com/docs/modules/model_io/chat/message_types) - AIMessage and response
  types
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) - WebSocket concepts

## Summary

The common service module provides essential utility functions for graph and subgraph execution in AgenticStudio. It acts as
a shared foundation that prevents code duplication and maintains consistency across execution contexts.

The module focuses on three core areas: **tool name normalisation and type mapping** (handling synthetic tool names with
UUID suffixes), **response content extraction** (with robust fallback logic for various message types), and **WebSocket
notifications** (for real-time execution updates).

By centralising these utilities, the common service maintains a clean dependency hierarchy where higher-level execution
services can use these utilities without creating circular dependencies. All functions are designed to be resilient,
handling errors gracefully and providing sensible fallbacks.

**Key Features:**

- Tool name normalisation (synthetic to canonical)
- NodeType detection from tool name patterns
- Response extraction with multiple fallback strategies
- Async WebSocket notifications for node lifecycle events
- Stateless, pure function design
- Resilient error handling

**Primary Use Cases:**

- Normalising tool names before database storage
- Determining node types for execution tracking
- Extracting agent responses from various message formats
- Sending real-time execution updates to connected clients
- Maintaining consistency across main and sub-agent execution

**When to Use This Service:**

- When executing agents or tools and need to track them in the database
- When extracting final responses from LangChain agent executors
- When sending real-time updates to the frontend UI during execution
- When normalising tool names for display or analytics
