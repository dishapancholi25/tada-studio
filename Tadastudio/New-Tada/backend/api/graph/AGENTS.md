# Graph API Module

## Overview

The Graph API module is the core API for workflow management in AgenticStudio. It provides comprehensive endpoints for
creating, managing, and executing AI workflows as directed acyclic graphs (DAGs).

**Location:** [backend/api/graph/](../../backend/api/graph/)

**Base Path:** `/api/graph`

**Primary Responsibilities:**

- Workflow CRUD operations (Create, Read, Update, Delete)
- Node management (agents, tools, conditions)
- Connection/edge management
- LLM configuration for agent nodes
- Workflow execution and monitoring
- File upload and processing
- Validation and export
- Template management

## Architecture

### Module Structure

```
backend/api/graph/
├── __init__.py           # Module exports (router, initialize_engine)
├── routes.py             # All API endpoints (444 lines)
├── models.py             # Pydantic request/response models (409 lines)
├── constants.py          # Constants and configuration
├── dependencies.py       # FastAPI dependencies
├── exceptions.py         # Custom exceptions
├── handlers/             # Request handlers (business logic delegation)
│   ├── graph_crud.py     # Graph CRUD operations
│   ├── node_crud.py      # Node CRUD operations
│   ├── connection_crud.py # Connection management
│   ├── execution.py      # Workflow execution
│   ├── llm_config.py     # LLM configuration
│   ├── file_upload.py    # File handling
│   ├── validation.py     # Validation and export
│   └── templates.py      # Template management
└── services/             # Service layer integration
    ├── execution_manager.py  # Execution coordination
    └── file_processor.py     # File processing
```

### Design Pattern

The Graph API follows a **handler-based architecture**:

```
HTTP Request
    ↓
Route Handler (routes.py)
    ↓
Business Logic Handler (handlers/*.py)
    ↓
Service Layer (services/*)
    ↓
Database / LangGraph / External APIs
```

**Benefits:**

- Thin route handlers focus on HTTP concerns
- Business logic isolated in handlers
- Services are reusable across APIs
- Easy to test handlers independently

## Authentication & Authorisation

### Authentication

All endpoints (except health checks) require authentication via **OAuth2-Proxy**.

**User Extraction:**

```python
from ..auth.dependencies import get_current_user

@router.get("/list")
async def list_graphs(current_user: Dict[str, Any] = Depends(get_current_user)):
    # current_user contains: id, email, name, etc.
    return await graph_crud.handle_list_graphs(current_user)
```

**Headers Injected by OAuth2-Proxy:**

- `X-Forwarded-User` - Username or email
- `X-Forwarded-Email` - User email
- `X-Forwarded-Preferred-Username` - Display name

### Authorisation

**User-Scoped Data:**
All graph operations are scoped to the authenticated user:

- Users can only see/modify their own workflows
- Shared workflows are accessible via explicit sharing
- GraphStorageService enforces user-scoping at database level

**Implementation:**

```python
# In graph_crud.py
async def handle_list_graphs(current_user: Dict[str, Any]):
    user_id = current_user["id"]
    # Only returns user's workflows + shared workflows
    workflows = storage_service.get_user_workflows(user_id)
    return {"success": True, "graphs": workflows}
```

## API Endpoints

### Health & Utilities (2 endpoints)

#### `GET /api/graph/health`

Health check with system metrics.

**Response:**

```json
{
  "success": true,
  "status": "healthy",
  "timestamp": "2025-10-20T10:30:00Z",
  "active_graphs": 15,
  "active_executions": 3,
  "total_executions": 247
}
```

**Usage:**

- Monitoring and load balancer health checks
- Quick system status overview

#### `GET /api/graph/types`

Get available node types for workflow building.

**Response:**

```json
{
  "success": true,
  "node_types": [
    {
      "value": "agent",
      "label": "Agent",
      "description": "AI agent with LLM and tools"
    },
    {
      "value": "tool",
      "label": "Tool",
      "description": "Standalone tool execution"
    },
    {
      "value": "condition",
      "label": "Condition",
      "description": "Conditional branching logic"
    }
    // ... more node types
  ]
}
```

**Node Types Available:**

- `START` - Entry point
- `END` - Exit point
- `AGENT` - AI agent with LLM
- `TOOL` - Tool execution
- `CONDITION` - Branching logic
- `HUMAN` - Human-in-the-loop
- `FILE_READ` - File processing
- `WEB_SEARCH` - Web search
- `DATABASE_QUERY` - Database queries
- `HTTP_REQUEST` - HTTP API calls
- `EMAIL_SEND` - Send emails
- `EMAIL_WAIT` - Wait for email
- `DOCUMENT_SEARCH` - Vector search
- `SUBWORKFLOW` - Nested workflows
- `MCP_SERVER` - Model Context Protocol integration

### Graph Management (10 endpoints)

#### `GET /api/graph/list`

List all workflows owned by or shared with the current user.

**Authentication:** Required

**Response:**

```json
{
  "success": true,
  "graphs": [
    {
      "id": "wf-abc-123",
      "name": "customer-support-workflow",
      "description": "Automated support triage",
      "created_at": "2025-10-15T10:00:00Z",
      "updated_at": "2025-10-20T14:30:00Z",
      "user_id": "user-123",
      "is_public": false,
      "version": 3
    }
  ]
}
```

**Key Fields:**

- `id` - Unique workflow identifier
- `name` - Human-readable workflow name
- `version` - Current version number
- `is_public` - Whether workflow is publicly shared

#### `POST /api/graph/create`

Create a new empty workflow.

**Authentication:** Required

**Request:**

```json
{
  "name": "customer-support-workflow",
  "description": "Automated support triage system"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Graph created successfully",
  "graph": {
    "id": "wf-abc-123",
    "name": "customer-support-workflow",
    "description": "Automated support triage system",
    "nodes": [],
    "edges": [],
    "created_at": "2025-10-20T10:30:00Z"
  }
}
```

**Validation:**

- Name must be unique per user
- Name cannot be empty
- Description is optional

#### `POST /api/graph/import-raw`

Import a complete workflow from JSON definition.

**Authentication:** Required

**Request:**

```json
{
  "name": "imported-workflow",
  "description": "Imported from external source",
  "workflow_json": {
    "nodes": [
      {
        "id": "node-1",
        "type": "agent",
        "data": { /* node configuration */ }
      }
    ],
    "edges": [
      {
        "id": "edge-1",
        "source": "node-1",
        "target": "node-2"
      }
    ]
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Workflow imported successfully",
  "graph": { /* complete graph definition */ }
}
```

**Use Cases:**

- Import workflows from templates
- Restore from backup
- Clone workflows between environments
- Programmatic workflow creation

#### `GET /api/graph/{graph_name}`

Get complete workflow definition by name.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Workflow name (URL-encoded)

**Response:**

```json
{
  "success": true,
  "graph": {
    "id": "wf-abc-123",
    "name": "customer-support-workflow",
    "description": "...",
    "nodes": [
      {
        "id": "node-1",
        "type": "agent",
        "position": { "x": 100, "y": 100 },
        "data": {
          "name": "Triage Agent",
          "llm_config": { /* LLM settings */ },
          "tools": ["search", "database"],
          "prompt_template": "..."
        }
      }
    ],
    "edges": [
      {
        "id": "edge-1",
        "source": "node-1",
        "target": "node-2",
        "sourceHandle": null,
        "targetHandle": null
      }
    ]
  }
}
```

#### `GET /api/graph/by-id/{workflow_id}`

Get workflow by database ID (alternative to name-based lookup).

**Authentication:** Required

**Path Parameters:**

- `workflow_id` - Workflow UUID

**Response:** Same as `GET /api/graph/{graph_name}`

**When to Use:**

- When you have the workflow ID from database
- Avoiding name conflicts
- Direct database lookups

#### `DELETE /api/graph/{graph_name}`

Delete a workflow permanently.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Workflow name

**Query Parameters:**

- `username` (optional) - Legacy parameter

**Response:**

```json
{
  "success": true,
  "message": "Graph 'customer-support-workflow' deleted successfully"
}
```

**Behaviour:**

- Deletes from database (workflows table)
- Removes graph versions
- Cancels active executions
- Cannot be undone

**Authorisation:**

- Only workflow owner can delete
- Shared users cannot delete

#### `POST /api/graph/save/{graph_name}`

Save workflow to disk (for backup/export).

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Workflow name

**Response:**

```json
{
  "success": true,
  "message": "Graph saved to disk",
  "file_path": "/workspace/default/customer-support-workflow.json"
}
```

**Note:** This is a legacy endpoint. Workflows are automatically persisted to PostgreSQL.

#### `POST /api/graph/reload/{graph_name}`

Force reload workflow from disk, bypassing cache.

**Path Parameters:**

- `graph_name` - Workflow name

**Query Parameters:**

- `username` - Username (default: "default")

**Response:**

```json
{
  "success": true,
  "message": "Graph reloaded successfully",
  "graph": { /* reloaded graph definition */ }
}
```

**Use Cases:**

- Development and testing
- Refresh after external modifications
- Cache invalidation

#### `POST /api/graph/batch-update`

Apply multiple changes to a workflow atomically.

**Authentication:** Required

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "changes": [
    {
      "type": "add_node",
      "data": {
        "node_id": "node-3",
        "node_type": "tool",
        "name": "Search Tool"
      }
    },
    {
      "type": "add_connection",
      "data": {
        "source_id": "node-1",
        "target_id": "node-3"
      }
    },
    {
      "type": "update_node",
      "data": {
        "node_id": "node-2",
        "updates": {
          "name": "Updated Name"
        }
      }
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "message": "Batch update completed successfully",
  "changes_applied": 3,
  "graph": { /* updated graph definition */ }
}
```

**Change Types:**

- `add_node` - Create new node
- `update_node` - Modify existing node
- `delete_node` - Remove node
- `add_connection` - Create edge
- `delete_connection` - Remove edge
- `update_metadata` - Modify graph metadata

**Atomicity:**

- All changes applied in single transaction
- If any change fails, all are rolled back
- Ensures graph consistency

#### `GET /api/graph/state/{graph_name}`

Get current graph state for real-time UI updates.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Workflow name

**Response:**

```json
{
  "success": true,
  "graph_name": "customer-support-workflow",
  "state": {
    "nodes": [/* all nodes */],
    "edges": [/* all edges */],
    "metadata": {
      "last_modified": "2025-10-20T14:30:00Z",
      "version": 3,
      "node_count": 12,
      "edge_count": 15
    }
  }
}
```

**Use Cases:**

- Real-time collaboration
- UI synchronisation
- Change detection
- Optimistic UI updates

### Node Management (7 endpoints)

#### `POST /api/graph/node/create`

Create a new node in a workflow.

**Authentication:** Required

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "node_type": "agent",
  "name": "Triage Agent",
  "position": { "x": 250, "y": 150 },
  "agent_template": "research-agent",
  "llm_type": "azure_openai",
  "model_name": "gpt-4",
  "description": "Initial triage and classification"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Node created successfully",
  "node": {
    "id": "node-abc-123",
    "type": "agent",
    "position": { "x": 250, "y": 150 },
    "data": {
      "name": "Triage Agent",
      "llm_config": {
        "type": "azure_openai",
        "model_name": "gpt-4"
      }
    }
  },
  "graph": { /* updated graph */ }
}
```

**Node-Specific Configuration:**

**AGENT Nodes:**

- `agent_template` - Pre-configured agent type
- `llm_type` - LLM provider
- `model_name` - Model to use
- `agent_config` - Tools, prompt template, memory settings

**TOOL Nodes:**

- `tool_template` - Tool type (web_search, calculator, etc.)

**CONDITION Nodes:**

- `condition_config` - Branching logic configuration

**DATABASE_QUERY Nodes:**

- `database_query_config` - Query configuration, datasource

**WEB_SEARCH Nodes:**

- `web_search_config` - Provider, API keys

**DOCUMENT_SEARCH Nodes:**

- `document_search_config` - Collection, filters, top_k

**Position:**

- `x`, `y` coordinates for visual layout
- Used by ReactFlow frontend

#### `POST /api/graph/node/create-sub-agent`

Create a sub-agent connected to an orchestrator agent.

**Authentication:** Required

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "parent_agent_id": "node-orchestrator",
  "name": "Technical Support Agent",
  "position": { "x": 400, "y": 200 },
  "delegation_description": "Handle technical issues requiring code analysis",
  "agent_template": "code-assistant"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Sub-agent created and connected",
  "node": { /* new sub-agent node */ },
  "delegation_connection": {
    "source": "node-orchestrator",
    "target": "node-abc-456",
    "type": "delegation"
  },
  "graph": { /* updated graph */ }
}
```

**Automatic Behaviour:**

- Creates sub-agent node
- Creates delegation connection
- Adds handoff tool to orchestrator
- Configures delegation routing

**Use Cases:**

- Multi-agent workflows
- Specialised sub-agents
- Task delegation patterns
- Hierarchical agent architectures

#### `PUT /api/graph/node/update`

Update an existing node's properties.

**Authentication:** Required

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "node_id": "node-abc-123",
  "updates": {
    "name": "Updated Triage Agent",
    "description": "Enhanced with sentiment analysis",
    "agent_config": {
      "tools": ["search", "database", "sentiment"],
      "prompt_template": "New prompt template..."
    }
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Node updated successfully",
  "node": { /* updated node */ },
  "graph": { /* updated graph */ }
}
```

**Updateable Fields:**

- `name` - Node name
- `description` - Description
- `position` - Visual position
- Type-specific configuration (agent_config, tool_config, etc.)
- `prompt_template` - Custom prompts

**Immutable Fields:**

- `id` - Node ID
- `type` - Node type (cannot change AGENT to TOOL)

#### `DELETE /api/graph/node/{graph_name}/{node_id}`

Delete a node from workflow.

**Path Parameters:**

- `graph_name` - Workflow name
- `node_id` - Node ID to delete

**Response:**

```json
{
  "success": true,
  "message": "Node deleted successfully"
}
```

**Cascade Behaviour:**

- Removes all incoming edges
- Removes all outgoing edges
- For orchestrators: removes sub-agent delegations
- Graph validation runs after deletion

**Restrictions:**

- Cannot delete START node
- Cannot delete END node (if it's the only one)

#### `GET /api/graph/node/{graph_name}/{node_id}`

Get detailed information about a specific node.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Workflow name
- `node_id` - Node ID

**Response:**

```json
{
  "success": true,
  "node": {
    "id": "node-abc-123",
    "type": "agent",
    "position": { "x": 250, "y": 150 },
    "data": {
      "name": "Triage Agent",
      "description": "...",
      "llm_config": { /* full LLM configuration */ },
      "agent_config": {
        "tools": ["search", "database"],
        "prompt_template": "...",
        "memory_enabled": true
      },
      "connected_nodes": {
        "incoming": ["node-start"],
        "outgoing": ["node-condition-1"]
      }
    }
  }
}
```

**Use Cases:**

- Node inspector UI
- Configuration editing
- Debugging workflows
- Dependency analysis

#### `PUT /api/graph/node/configure`

Configure node-specific settings.

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "node_id": "node-search",
  "config": {
    "provider": "tavily",
    "max_results": 10,
    "include_domains": ["docs.python.org"],
    "search_depth": "advanced"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "Node configured successfully",
  "node": { /* updated node with new config */ }
}
```

**Configuration Types by Node:**

**WEB_SEARCH:**

- `provider` - tavily, exa, brave
- `max_results` - Results to return
- `search_depth` - basic, advanced

**DATABASE_QUERY:**

- `datasource_id` - Connected datasource
- `query_template` - SQL template
- `parameters` - Query parameters

**FILE_READ:**

- `extraction_mode` - auto, text, ocr
- `output_format` - markdown, json, text
- `ocr_library` - easyocr, pytesseract

#### `GET /api/graph/graph/{graph_name}/agents`

Get all agent nodes in a workflow with their configurations.

**Path Parameters:**

- `graph_name` - Workflow name

**Response:**

```json
{
  "success": true,
  "agents": [
    {
      "id": "node-agent-1",
      "name": "Triage Agent",
      "llm_config": {
        "type": "azure_openai",
        "model_name": "gpt-4",
        "temperature": 0.7
      },
      "tools": ["search", "database"],
      "agent_type": "research"
    },
    {
      "id": "node-agent-2",
      "name": "Response Agent",
      "llm_config": { /* config */ },
      "tools": ["email_send"],
      "agent_type": "general"
    }
  ]
}
```

**Use Cases:**

- Agent management dashboard
- LLM cost estimation
- Batch LLM configuration updates
- Workflow analysis

### Connection Management (2 endpoints)

#### `POST /api/graph/connection/create`

Create a connection (edge) between two nodes.

**Authentication:** Required

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "source_id": "node-agent-1",
  "target_id": "node-condition-1",
  "source_handle": null,
  "target_handle": null,
  "label": "Process Result",
  "connection_type": "workflow"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Connection created successfully"
}
```

**Connection Types:**

**workflow** (default):

- Standard execution flow
- Sequential node execution
- State propagation

**tool**:

- Tool attachment to agent
- Makes tool available to agent
- Not part of execution flow

**delegation**:

- Orchestrator to sub-agent
- Enables agent delegation
- Special routing logic

**Handles (for Condition Nodes):**

- `source_handle` - Branch identifier (e.g., "branch-0", "branch-1")
- Used for conditional routing
- Multiple outgoing edges with different handles

**Validation:**

- Prevents cycles (DAG enforcement)
- Checks node compatibility
- Validates handle configuration
- Ensures single START node

#### `DELETE /api/graph/connection/delete`

Delete a connection between nodes.

**Authentication:** Required

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "source_id": "node-agent-1",
  "target_id": "node-condition-1"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Connection deleted successfully"
}
```

**Behaviour:**

- Removes edge from graph
- Preserves nodes
- Updates graph validation state
- May create disconnected nodes (valid)

### LLM Configuration (5 endpoints)

#### `GET /api/graph/llm/providers`

Get list of available LLM providers.

**Response:**

```json
{
  "success": true,
  "providers": [
    {
      "id": "azure_openai",
      "name": "Azure OpenAI",
      "description": "Microsoft Azure hosted OpenAI models",
      "requires_deployment": true,
      "supports_streaming": true
    },
    {
      "id": "openai",
      "name": "OpenAI",
      "description": "Direct OpenAI API",
      "requires_deployment": false,
      "supports_streaming": true
    },
    {
      "id": "anthropic",
      "name": "Anthropic Claude",
      "description": "Claude models via Anthropic API",
      "requires_deployment": false,
      "supports_streaming": true
    }
  ]
}
```

#### `GET /api/graph/llm/models/{provider}`

Get available models for a specific provider.

**Path Parameters:**

- `provider` - Provider ID (azure_openai, openai, anthropic)

**Response:**

```json
{
  "success": true,
  "provider": "azure_openai",
  "models": [
    {
      "id": "gpt-4",
      "name": "GPT-4",
      "description": "Most capable model",
      "context_window": 8192,
      "supports_functions": true,
      "supports_vision": false
    },
    {
      "id": "gpt-4-turbo",
      "name": "GPT-4 Turbo",
      "description": "Faster GPT-4 variant",
      "context_window": 128000,
      "supports_functions": true,
      "supports_vision": true
    }
  ]
}
```

#### `POST /api/graph/llm/test`

Test LLM connection and configuration.

**Request:**

```json
{
  "llm_config": {
    "type": "azure_openai",
    "model_name": "gpt-4",
    "azure_endpoint": "https://my-resource.openai.azure.com/",
    "api_key": "sk-...",
    "deployment_name": "gpt4-deployment",
    "api_version": "2024-02-15-preview"
  },
  "test_message": "Hello, respond to confirm connection works."
}
```

**Response (Success):**

```json
{
  "success": true,
  "test_result": {
    "status": "success",
    "response": "Hello! The connection is working correctly.",
    "latency_ms": 1247,
    "model_used": "gpt-4",
    "tokens_used": {
      "prompt": 12,
      "completion": 9,
      "total": 21
    }
  }
}
```

**Response (Failure):**

```json
{
  "success": false,
  "error": "Authentication failed",
  "message": "Invalid API key or deployment name"
}
```

**Use Cases:**

- Validate API keys before saving
- Test model availability
- Check deployment configuration
- Diagnose connection issues

#### `PUT /api/graph/node/llm/configure`

Configure LLM settings for an agent node.

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "node_id": "node-agent-1",
  "llm_config": {
    "type": "azure_openai",
    "model_name": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "streaming": true,
    "azure_endpoint": "https://my-resource.openai.azure.com/",
    "deployment_name": "gpt4-deployment",
    "api_version": "2024-02-15-preview"
  }
}
```

**Response:**

```json
{
  "success": true,
  "message": "LLM configuration updated",
  "node": { /* updated node with new LLM config */ }
}
```

**LLM Parameters:**

**Common:**

- `temperature` - Randomness (0-2)
- `max_tokens` - Max response length
- `top_p` - Nucleus sampling
- `frequency_penalty` - Reduce repetition
- `presence_penalty` - Encourage diversity
- `streaming` - Enable token streaming

**Azure OpenAI Specific:**

- `azure_endpoint` - Resource endpoint
- `deployment_name` - Model deployment
- `api_version` - API version

**OpenAI Specific:**

- `organization_id` - Optional org ID

**Anthropic Specific:**

- `anthropic_version` - API version

#### `GET /api/graph/node/{graph_name}/{node_id}/llm`

Get LLM configuration for an agent node.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Workflow name
- `node_id` - Agent node ID

**Response:**

```json
{
  "success": true,
  "llm_config": {
    "type": "azure_openai",
    "model_name": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000,
    /* ... other settings ... */
  }
}
```

### Execution (8 endpoints)

#### `POST /api/graph/execute`

Execute a workflow with given inputs.

**Authentication:** Required

**Request:**

```json
{
  "graph_name": "customer-support-workflow",
  "initial_input": {
    "user_query": "My account is locked",
    "user_id": "12345",
    "priority": "high"
  },
  "username": "default",
  "async_execution": true,
  "file_info": null
}
```

**Response (Async):**

```json
{
  "success": true,
  "message": "Execution started",
  "execution_id": "exec-abc-123",
  "async": true,
  "status_endpoint": "/api/graph/execution/exec-abc-123/status"
}
```

**Response (Sync):**

```json
{
  "success": true,
  "message": "Execution completed",
  "execution_id": "exec-abc-123",
  "async": false,
  "execution_result": {
    "status": "completed",
    "final_output": {
      "resolution": "Account unlocked",
      "actions_taken": ["password_reset", "notification_sent"]
    },
    "duration_seconds": 12.4,
    "tokens_used": 1247,
    "nodes_executed": ["start", "agent-1", "condition-1", "agent-2", "end"]
  }
}
```

**Execution Modes:**

**Synchronous (`async_execution: false`):**

- Blocks until completion
- Returns final result in response
- Suitable for: Short workflows, testing, simple scripts
- Timeout: Depends on server configuration

**Asynchronous (`async_execution: true`):**

- Returns immediately with execution ID
- Poll status endpoint for progress
- Suitable for: Long-running workflows, production use
- No timeout

**Initial Input:**

- Available to all nodes via state
- Accessed using `{{user_query}}` templates
- Can include any JSON-serialisable data

**File Info:**

- For workflows with FILE_READ nodes
- Includes file path and metadata
- Automatically populated when using file upload endpoints

#### `GET /api/graph/execution/{execution_id}/status`

Get current status of an execution.

**Path Parameters:**

- `execution_id` - Execution ID from execute response

**Response:**

```json
{
  "success": true,
  "execution_status": {
    "execution_id": "exec-abc-123",
    "status": "running",
    "progress": {
      "current_node": "node-agent-2",
      "nodes_completed": 5,
      "total_nodes": 8,
      "percent_complete": 62
    },
    "started_at": "2025-10-20T10:30:00Z",
    "elapsed_seconds": 8.3,
    "node_executions": [
      {
        "node_id": "start",
        "status": "completed",
        "duration_ms": 5
      },
      {
        "node_id": "node-agent-1",
        "status": "completed",
        "duration_ms": 3421,
        "output": "Classified as technical issue"
      },
      {
        "node_id": "node-agent-2",
        "status": "running",
        "started_at": "2025-10-20T10:30:08Z"
      }
    ]
  }
}
```

**Status Values:**

- `running` - In progress
- `completed` - Finished successfully
- `failed` - Error occurred
- `cancelled` - User cancelled
- `paused` - Waiting (e.g., for email)

**Polling Pattern:**

```javascript
// Poll every 2 seconds until complete
async function waitForExecution(executionId) {
  while (true) {
    const response = await fetch(`/api/graph/execution/${executionId}/status`);
    const data = await response.json();

    if (data.execution_status.status !== 'running') {
      return data;
    }

    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}
```

#### `GET /api/graph/execution/{execution_id}/history`

Get detailed execution history with all node outputs.

**Path Parameters:**

- `execution_id` - Execution ID

**Response:**

```json
{
  "success": true,
  "execution_id": "exec-abc-123",
  "execution_history": {
    "status": "completed",
    "started_at": "2025-10-20T10:30:00Z",
    "completed_at": "2025-10-20T10:30:12Z",
    "duration_seconds": 12.4,
    "initial_input": {
      "user_query": "My account is locked"
    },
    "final_output": {
      "resolution": "Account unlocked"
    },
    "node_history": [
      {
        "node_id": "node-agent-1",
        "node_name": "Triage Agent",
        "node_type": "agent",
        "status": "completed",
        "started_at": "2025-10-20T10:30:00.123Z",
        "completed_at": "2025-10-20T10:30:03.544Z",
        "duration_ms": 3421,
        "input": {
          "user_query": "My account is locked"
        },
        "output": {
          "classification": "technical",
          "priority": "high",
          "agent_response": "This is a technical account issue..."
        },
        "tool_calls": [
          {
            "tool": "database_query",
            "input": { "user_id": "12345" },
            "output": { "account_status": "locked" },
            "duration_ms": 234
          }
        ],
        "tokens_used": 487,
        "model_used": "gpt-4"
      }
    ],
    "total_tokens": 1247,
    "total_cost_usd": 0.0342
  }
}
```

**Use Cases:**

- Debugging failed executions
- Analysing workflow performance
- Audit trails
- Cost tracking
- Token usage monitoring

#### `GET /api/graph/executions`

List recent executions.

**Query Parameters:**

- `limit` - Max executions to return (default: 50)

**Response:**

```json
{
  "success": true,
  "active_executions": [
    {
      "execution_id": "exec-abc-123",
      "graph_name": "customer-support-workflow",
      "status": "running",
      "started_at": "2025-10-20T10:30:00Z",
      "elapsed_seconds": 8.3
    }
  ],
  "recent_executions": [
    {
      "execution_id": "exec-abc-122",
      "graph_name": "customer-support-workflow",
      "status": "completed",
      "started_at": "2025-10-20T10:25:00Z",
      "completed_at": "2025-10-20T10:25:15Z",
      "duration_seconds": 15.2
    }
  ]
}
```

#### `GET /api/graph/execution/{execution_id}/agent/{agent_id}/tools`

Get all tool executions for a specific agent.

**Path Parameters:**

- `execution_id` - Execution ID
- `agent_id` - Agent node ID

**Response:**

```json
{
  "success": true,
  "agent_id": "node-agent-1",
  "execution_id": "exec-abc-123",
  "total_tool_executions": 5,
  "grouped_executions": {
    "database_query": [
      {
        "tool_name": "database_query",
        "timestamp": "2025-10-20T10:30:01.234Z",
        "duration_ms": 234,
        "input": { "user_id": "12345" },
        "output": { "account_status": "locked" },
        "status": "success"
      },
      {
        "tool_name": "database_query",
        "timestamp": "2025-10-20T10:30:02.456Z",
        "duration_ms": 187,
        "input": { "query": "SELECT * FROM logs..." },
        "output": { "rows": [...] },
        "status": "success"
      }
    ],
    "web_search": [
      {
        "tool_name": "web_search",
        "timestamp": "2025-10-20T10:30:03.123Z",
        "duration_ms": 1543,
        "input": { "query": "account unlock procedures" },
        "output": { "results": [...] },
        "status": "success"
      }
    ]
  },
  "tool_executions": [/* flat list of all tool calls */]
}
```

**Use Cases:**

- Agent behaviour analysis
- Tool usage patterns
- Performance profiling
- Debugging tool issues

#### `POST /api/graph/execution/{execution_id}/cancel`

Cancel a running execution.

**Path Parameters:**

- `execution_id` - Execution ID

**Response:**

```json
{
  "success": true,
  "message": "Execution cancelled successfully",
  "execution_id": "exec-abc-123"
}
```

**Behaviour:**

- Stops execution gracefully
- Current node completes
- No further nodes executed
- Status set to "cancelled"
- Checkpoint saved

**Limitations:**

- Cannot cancel completed executions
- LLM calls in progress will complete
- External API calls may not be cancellable

#### `POST /api/graph/agent/{graph_name}/{agent_id}/chat`

Chat with a specific agent node directly (for testing).

**Path Parameters:**

- `graph_name` - Workflow name
- `agent_id` - Agent node ID

**Request:**

```json
{
  "message": "Hello, can you help me understand this code?"
}
```

**Response:**

```json
{
  "success": true,
  "response": {
    "content": "Of course! I'd be happy to help you understand the code. Please share the code you'd like me to explain.",
    "agent_name": "Code Assistant Agent",
    "model_used": "gpt-4",
    "tokens_used": {
      "prompt": 24,
      "completion": 32,
      "total": 56
    },
    "duration_ms": 1234
  }
}
```

**Use Cases:**

- Test agent configurations
- Validate LLM connections
- Preview agent behaviour
- Debugging prompts and tools

**Note:** This runs the agent in isolation, without workflow context.

### File Operations (5 endpoints)

#### `POST /api/graph/upload-file`

Upload a file for processing.

**Request:** Multipart form data

- `file` - File to upload

**Response:**

```json
{
  "success": true,
  "file_info": {
    "file_id": "file-abc-123",
    "filename": "document.pdf",
    "file_path": "/workspace/uploads/file-abc-123-document.pdf",
    "size_bytes": 245678,
    "mime_type": "application/pdf",
    "uploaded_at": "2025-10-20T10:30:00Z"
  }
}
```

**Supported File Types:**

- PDF (.pdf)
- Microsoft Word (.docx)
- Excel (.xlsx)
- Text files (.txt, .md)
- Images (.jpg, .png) - with OCR

**File Storage:**

- Stored in `/workspace/uploads/`
- Filename: `{file_id}-{original_name}`
- Temporary storage (cleaned up after processing)

#### `GET /api/graph/file-metadata/{file_path:path}`

Get metadata about an uploaded file.

**Path Parameters:**

- `file_path` - File path (URL-encoded)

**Response:**

```json
{
  "success": true,
  "metadata": {
    "filename": "document.pdf",
    "size_bytes": 245678,
    "mime_type": "application/pdf",
    "created_at": "2025-10-20T10:30:00Z",
    "modified_at": "2025-10-20T10:30:00Z",
    "exists": true,
    "readable": true
  }
}
```

#### `POST /api/graph/process-file`

Process a file using document service.

**Request:** Form data

- `file_path` - Path to file
- `extraction_mode` - auto, text, ocr (default: auto)
- `output_format` - markdown, json, text (default: markdown)
- `ocr_library` - easyocr, pytesseract (default: easyocr)
- `language` - Language code (default: en)

**Response:**

```json
{
  "success": true,
  "content": "# Document Title\n\nDocument content in markdown...",
  "metadata": {
    "pages": 5,
    "word_count": 1234,
    "extraction_method": "text",
    "processing_time_ms": 432
  },
  "extraction_method": "text"
}
```

**Extraction Modes:**

- `auto` - Detect best method
- `text` - Direct text extraction
- `ocr` - Force OCR (for images/scanned PDFs)

**Output Formats:**

- `markdown` - Structured markdown with headings
- `json` - Structured elements array
- `text` - Plain text

#### `POST /api/graph/execute-with-file`

Execute a workflow with a file as input.

**Request:** Multipart form data

- `graph_name` - Workflow name
- `username` - Username (default: "default")
- `async_execution` - true/false (default: true)
- `message` - Optional message for workflow
- `file` - File to process (optional)

**Response:**

```json
{
  "success": true,
  "message": "Execution started",
  "execution_id": "exec-abc-123",
  "file_processed": true,
  "file_info": {
    "filename": "document.pdf",
    "file_path": "/workspace/uploads/file-abc-123-document.pdf"
  },
  "status_endpoint": "/api/graph/execution/exec-abc-123/status"
}
```

**Behaviour:**

1. Upload file (if provided)
2. Process file through document service
3. Add file content to initial state
4. Execute workflow
5. Clean up temporary file

**Workflow Access:**

- File content available as `{{file_content}}`
- File metadata available as `{{file_metadata}}`
- Original filename as `{{filename}}`

### Validation & Export (5 endpoints)

#### `GET /api/graph/validate/{graph_name}`

Validate workflow for completeness and correctness.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Workflow name

**Response:**

```json
{
  "success": true,
  "validation": {
    "is_valid": true,
    "errors": [],
    "warnings": [
      {
        "type": "unused_node",
        "node_id": "node-tool-3",
        "message": "Node is not connected to any workflow path"
      }
    ],
    "checks": {
      "has_start_node": true,
      "has_end_node": true,
      "all_nodes_connected": true,
      "no_cycles": true,
      "valid_llm_configs": true,
      "all_tools_configured": true
    },
    "statistics": {
      "node_count": 12,
      "edge_count": 15,
      "agent_count": 4,
      "tool_count": 3,
      "condition_count": 2
    }
  }
}
```

**Validation Checks:**

- Has START node
- Has at least one END node
- No cycles (DAG requirement)
- All nodes reachable from START
- All LLM configs valid
- All required configurations present
- Condition branches properly configured

**Error Types:**

- `missing_start` - No START node
- `missing_end` - No END node
- `cycle_detected` - Graph has cycle
- `disconnected_node` - Unreachable node
- `invalid_config` - Missing/invalid configuration
- `invalid_llm` - LLM configuration error

#### `GET /api/graph/export/{graph_name}`

Export workflow in specified format.

**Authentication:** Required

**Path Parameters:**

- `graph_name` - Workflow name

**Query Parameters:**

- `export_format` - Export format (default: "langgraph")

**Response:**

```json
{
  "success": true,
  "format": "langgraph",
  "data": {
    "graph_definition": { /* LangGraph-compatible JSON */ },
    "metadata": {
      "name": "customer-support-workflow",
      "version": 3,
      "exported_at": "2025-10-20T10:30:00Z"
    }
  }
}
```

**Export Formats:**

- `langgraph` - LangGraph StateGraph definition
- `json` - Complete workflow JSON
- `mermaid` - Mermaid diagram syntax (future)

**Use Cases:**

- Backup workflows
- Import to other systems
- Version control
- Documentation generation

#### `POST /api/graph/structured-outputs/validate`

Validate a structured output schema.

**Request:**

```json
{
  "schema_name": "UserProfile",
  "fields": [
    {
      "name": "name",
      "type": "string",
      "required": true,
      "description": "User's full name"
    },
    {
      "name": "age",
      "type": "integer",
      "required": false,
      "description": "User's age"
    },
    {
      "name": "email",
      "type": "string",
      "required": true,
      "description": "User's email address"
    }
  ]
}
```

**Response:**

```json
{
  "success": true,
  "validation_result": {
    "is_valid": true,
    "errors": [],
    "warnings": []
  }
}
```

**Validation Rules:**

- Schema name is valid Python identifier
- All field names are valid identifiers
- Types are supported (string, integer, float, boolean, array, object)
- Required fields marked correctly
- No duplicate field names

#### `POST /api/graph/structured-outputs/preview`

Preview generated Pydantic model code for a schema.

**Request:** Same as validate

**Response:**

```json
{
  "success": true,
  "model_code": "from pydantic import BaseModel, Field\n\nclass UserProfile(BaseModel):\n    name: str = Field(..., description=\"User's full name\")\n    age: Optional[int] = Field(None, description=\"User's age\")\n    email: str = Field(..., description=\"User's email address\")",
  "tool_code": "def extract_user_profile(text: str) -> UserProfile:\n    \"\"\"Extract user profile from text.\"\"\"\n    # LLM extraction logic\n    pass",
  "errors": []
}
```

**Use Cases:**

- Preview generated code
- Validate schema before saving
- Learn Pydantic syntax
- Copy-paste for custom implementations

### Templates (2 endpoints)

#### `GET /api/graph/templates/tools`

Get available tool templates.

**Response:**

```json
{
  "success": true,
  "templates": {
    "web_search": {
      "name": "Web Search",
      "description": "Search the web using Tavily or Exa",
      "config": {
        "provider": "tavily",
        "max_results": 10
      }
    },
    "database_query": {
      "name": "Database Query",
      "description": "Execute SQL queries",
      "config": {
        "datasource_id": null,
        "query_template": "SELECT * FROM table"
      }
    },
    "calculator": {
      "name": "Calculator",
      "description": "Perform mathematical calculations",
      "config": {}
    }
  }
}
```

**Tool Categories:**

- **Search:** web_search, document_search
- **Data:** database_query, http_request
- **File:** file_read, file_write
- **Communication:** email_send
- **Utility:** calculator, code_interpreter

#### `GET /api/graph/templates/agents`

Get available agent templates with pre-configured settings.

**Response:**

```json
{
  "success": true,
  "templates": {
    "research-agent": {
      "name": "Research Agent",
      "description": "General-purpose research with web search",
      "tools": ["web_search", "calculator"],
      "prompt_template": "You are a helpful research assistant...",
      "llm_config": {
        "temperature": 0.7,
        "max_tokens": 2000
      }
    },
    "code-assistant": {
      "name": "Code Assistant",
      "description": "Help with code analysis and generation",
      "tools": ["code_interpreter"],
      "prompt_template": "You are an expert programmer...",
      "llm_config": {
        "temperature": 0.3,
        "max_tokens": 4000
      }
    }
  }
}
```

**Agent Categories:**

- **General:** general-assistant, research-agent
- **Technical:** code-assistant, data-analyst
- **Business:** customer-support, sales-agent
- **Creative:** content-writer, social-media-agent

## Error Handling

### Error Response Format

All errors follow this structure:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      /* Additional context */
    }
  }
}
```

### Common Error Codes

**Authentication Errors (401):**

- `UNAUTHORIZED` - No authentication provided
- `INVALID_TOKEN` - Invalid JWT token
- `TOKEN_EXPIRED` - Token has expired

**Authorisation Errors (403):**

- `FORBIDDEN` - User doesn't have access
- `NOT_OWNER` - User is not workflow owner

**Validation Errors (400):**

- `INVALID_REQUEST` - Request validation failed
- `INVALID_GRAPH_NAME` - Graph name invalid
- `INVALID_NODE_TYPE` - Unsupported node type
- `INVALID_CONNECTION` - Connection would create cycle

**Not Found Errors (404):**

- `GRAPH_NOT_FOUND` - Workflow doesn't exist
- `NODE_NOT_FOUND` - Node doesn't exist
- `EXECUTION_NOT_FOUND` - Execution doesn't exist

**Conflict Errors (409):**

- `DUPLICATE_GRAPH` - Graph name already exists
- `DUPLICATE_NODE` - Node ID already exists

**Server Errors (500):**

- `EXECUTION_FAILED` - Workflow execution failed
- `LLM_ERROR` - LLM provider error
- `DATABASE_ERROR` - Database operation failed

### Error Handling Example

```python
try:
    response = requests.post("/api/graph/create", json={
        "name": "my-workflow"
    })
    response.raise_for_status()
    data = response.json()
except requests.HTTPError as e:
    error_data = e.response.json()
    if error_data["error"]["code"] == "DUPLICATE_GRAPH":
        print("Graph already exists, using existing one")
        # Handle duplicate
    else:
        raise
```

## Integration with Services Layer

### Dependency Flow

```
API Route (routes.py)
    ↓
Handler (handlers/*.py)
    ↓
Dependency Injection Container
    ↓
Services (services/*)
```

### Example Integration

**Route:**

```python
@router.post("/execute")
async def execute_graph(
    request: GraphExecutionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    return await execution.handle_execute_graph(request, current_user)
```

**Handler:**

```python
# In handlers/execution.py
async def handle_execute_graph(
    request: GraphExecutionRequest,
    current_user: Dict[str, Any]
):
    # Get services via DI
    graph_manager = get_graph_manager()
    execution_engine = get_execution_engine()

    # Load graph
    graph = graph_manager.get_graph(request.graph_name, current_user["id"])

    # Execute
    result = await execution_engine.execute(
        graph_data=graph,
        initial_input=request.initial_input,
        async_mode=request.async_execution
    )

    return {"success": True, "execution_id": result.execution_id}
```

**Services Used:**

- **GraphManager** - Graph CRUD, validation
- **ExecutionEngine** - Workflow execution
- **GraphStorageService** - Database persistence
- **DocumentService** - File processing
- **LLMConfig** - LLM provider management

## Usage Examples

### Complete Workflow Creation

```python
import requests

BASE_URL = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer {token}"}

# 1. Create workflow
response = requests.post(
    f"{BASE_URL}/api/graph/create",
    headers=HEADERS,
    json={
        "name": "customer-support",
        "description": "Automated customer support triage"
    }
)
workflow = response.json()["graph"]

# 2. Create START node (automatic)
# 3. Create agent node
response = requests.post(
    f"{BASE_URL}/api/graph/node/create",
    headers=HEADERS,
    json={
        "graph_name": "customer-support",
        "node_type": "agent",
        "name": "Triage Agent",
        "position": {"x": 250, "y": 150},
        "agent_template": "customer-support",
        "llm_type": "azure_openai",
        "model_name": "gpt-4"
    }
)
agent_node = response.json()["node"]

# 4. Create condition node
response = requests.post(
    f"{BASE_URL}/api/graph/node/create",
    headers=HEADERS,
    json={
        "graph_name": "customer-support",
        "node_type": "condition",
        "name": "Route by Priority",
        "position": {"x": 450, "y": 150}
    }
)
condition_node = response.json()["node"]

# 5. Create connections
# START -> Agent
requests.post(
    f"{BASE_URL}/api/graph/connection/create",
    headers=HEADERS,
    json={
        "graph_name": "customer-support",
        "source_id": "start",
        "target_id": agent_node["id"]
    }
)

# Agent -> Condition
requests.post(
    f"{BASE_URL}/api/graph/connection/create",
    headers=HEADERS,
    json={
        "graph_name": "customer-support",
        "source_id": agent_node["id"],
        "target_id": condition_node["id"]
    }
)

# 6. Execute workflow
response = requests.post(
    f"{BASE_URL}/api/graph/execute",
    headers=HEADERS,
    json={
        "graph_name": "customer-support",
        "initial_input": {
            "user_query": "My account is locked",
            "user_id": "12345"
        },
        "async_execution": True
    }
)
execution = response.json()
print(f"Execution started: {execution['execution_id']}")

# 7. Poll for status
import time
while True:
    response = requests.get(
        f"{BASE_URL}/api/graph/execution/{execution['execution_id']}/status",
        headers=HEADERS
    )
    status = response.json()["execution_status"]
    print(f"Status: {status['status']}")

    if status["status"] != "running":
        break

    time.sleep(2)
```

## Performance Considerations

### Endpoint Performance

**Fast Endpoints (< 100ms):**

- Health checks
- List operations (with pagination)
- Get node/graph by ID
- Validation

**Medium Endpoints (100ms - 1s):**

- Create/update operations
- File upload (small files)
- LLM connection tests
- Export operations

**Slow Endpoints (> 1s):**

- Synchronous execution
- Large file processing
- Complex graph operations

### Optimisation Tips

**1. Use Async Execution:**

```python
# Instead of blocking
response = execute_graph(async_execution=False)  # Slow

# Use async + polling
response = execute_graph(async_execution=True)  # Fast return
# Poll status endpoint
```

**2. Batch Operations:**

```python
# Instead of multiple requests
create_node(...)
create_node(...)
create_connection(...)

# Use batch update
batch_update(changes=[
    {"type": "add_node", ...},
    {"type": "add_node", ...},
    {"type": "add_connection", ...}
])
```

**3. Cache Graph Definitions:**

```python
# Client-side caching
graph_cache = {}

def get_graph(name):
    if name not in graph_cache:
        graph_cache[name] = fetch_graph(name)
    return graph_cache[name]
```

**4. Use WebSocket for Real-time:**
For real-time execution updates, use [WebSocket API](../websocket/websocket.md) instead of polling.

## Related Documentation

- [Architecture Overview](../../../docs/architecture/00-overview.md) - System architecture
- [Data Flow Patterns](../../../docs/architecture/02-data-flow.md) - How data flows
- [Execution API](../../../backend/api/execution/execution.md) - Execution-specific endpoints (when documented)
- [WebSocket API](../websocket/websocket.md) - Real-time updates (when documented)
- [Services Layer](../services/README.md) - Backend services (when documented)

## Summary

The Graph API provides comprehensive workflow management capabilities:

- **Complete CRUD** - Create, read, update, delete workflows
- **Visual Builder Support** - Node positions, drag-and-drop friendly
- **Multi-mode Execution** - Sync, async, streaming
- **Rich Configuration** - LLM settings, tools, conditions
- **Production Ready** - Authentication, validation, error handling
- **Developer Friendly** - Clear models, comprehensive responses

This is the primary API for building and managing AI workflows in AgenticStudio, designed to support both visual workflow
builders and programmatic workflow management.
