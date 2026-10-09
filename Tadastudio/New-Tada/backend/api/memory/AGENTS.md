# Memory API Module

## Overview

The Memory API module provides comprehensive memory management capabilities for AI agents in AgenticStudio. It enables
agents to store, retrieve, and manage conversation history, learned facts, summaries, and instructions across workflow
executions. The module supports memory lifecycle management including pruning old entries and maintaining agent-specific
memory profiles.

**Location:** [backend/api/memory/](../../backend/api/memory/)

**Base Path:** `/api/memory`

**Primary Responsibilities:**

- Store and retrieve agent memories (conversations, facts, summaries, instructions)
- Manage conversation history for agent context
- Maintain agent memory profiles with configuration settings
- Prune and clean up old or inactive memories
- Track memory access patterns and importance scoring
- Support execution-scoped memory filtering

## Architecture

### Module Structure

```
backend/api/memory/
├── __init__.py          # Module exports (router)
├── routes.py            # All 6 API endpoints (309 lines)
├── models.py            # Pydantic request/response models (93 lines)
└── dependencies.py      # FastAPI dependency injection (34 lines)
```

**File Descriptions:**

- ****init**.py**: Exports the FastAPI router and module documentation
- **routes.py**: Contains all endpoint implementations with direct service calls
- **models.py**: Pydantic models for request validation and response serialisation
- **dependencies.py**: Provides `MemoryService` dependency for injection

### Design Pattern

The Memory API follows a **direct service integration pattern**:

```
HTTP Request
    ↓
Route Handler (routes.py)
    ↓
Memory Service (MemoryManager)
    ↓
Service Components (Repository, Formatter, Statistics, Pruning)
    ↓
Database / Storage
```

**Benefits:**

- Simple and direct architecture for focused API
- Minimal overhead between API and service layer
- Clear separation between API models and service schemas
- Easy to understand and maintain
- Efficient for the module's scope (6 endpoints)

**Difference from Graph Module:**
Unlike the larger Graph API module which uses a handler-based pattern, the Memory API directly calls service methods
from routes. This is appropriate given the module's focused scope and straightforward operations.

## Authentication & Authorisation

### Authentication

**None Required** - The Memory API currently does not enforce authentication at the API layer. This module is designed
for internal service-to-service communication and agent memory management.

**Important Considerations:**

- If deploying this API publicly, authentication should be added
- Consider adding user-scoped memory access in future versions
- Currently relies on agent_id for memory isolation
- No OAuth2-Proxy integration (unlike graph/execution modules)

### Authorisation

**Agent-Scoped Access:**
Memory entries are isolated by `agent_id`:

- Each agent can only access its own memories via agent_id parameter
- Memory profiles are specific to agent_id + graph_id combinations
- No cross-agent memory sharing mechanism
- Graph execution ID provides additional scoping within agent memories

**Implementation Pattern:**

```python
# Memories are filtered by agent_id
memories = await memory_service.get_agent_memories(
    agent_id="agent-123",  # Agent isolation
    graph_execution_id="exec-456",  # Optional execution scoping
    only_active=True
)
```

## API Endpoints

### Memory Management

#### `POST /api/memory/memories`

Create a new memory entry for an agent. Memories can be of type conversation, summary, fact, or instruction.

**Authentication:** None

**Request Body:**

```json
{
  "agent_id": "agent-code-reviewer-v2",
  "agent_name": "Code Reviewer Assistant",
  "memory_type": "conversation",
  "content": "User prefers snake_case naming convention for Python variables",
  "importance_score": 0.8,
  "graph_execution_id": "exec-7f3e9a2c-4b1d-4e5f-8c9a-1d2e3f4a5b6c",
  "node_execution_id": "node-exec-123"
}
```

**Request Fields:**

- `agent_id` (required) - Unique identifier for the agent
- `agent_name` (required) - Human-readable agent name
- `memory_type` (required) - One of: `conversation`, `summary`, `fact`, `instruction`
- `content` (required) - The memory content/text
- `importance_score` (optional) - Float between 0.0 and 1.0 (default: 0.5)
- `graph_execution_id` (optional) - Associate memory with specific workflow execution
- `node_execution_id` (optional) - Associate memory with specific node execution

**Response:**

```json
{
  "id": "65a3f2c1b4e8d9a7c6b5e4f3",
  "agent_id": "agent-code-reviewer-v2",
  "agent_name": "Code Reviewer Assistant",
  "memory_type": "conversation",
  "content": "User prefers snake_case naming convention for Python variables",
  "importance_score": 0.8,
  "access_count": 0,
  "is_active": true,
  "created_at": "2025-01-15T14:30:22.123456",
  "last_accessed": null
}
```

**Use Cases:**

- Storing user preferences during agent conversations
- Recording important facts learned during workflow execution
- Saving conversation summaries for context window management
- Preserving user instructions for future agent behaviour

**Behaviour:**

- Memory is created with `is_active=true` by default
- `access_count` starts at 0
- `created_at` timestamp is automatically set
- `last_accessed` is null until memory is retrieved
- Returns 400 if invalid memory_type or importance_score
- Returns 500 if database operation fails

**Validation:**

- `memory_type` must be one of: `conversation`, `summary`, `fact`, `instruction`
- `importance_score` must be between 0.0 and 1.0 (inclusive)
- `agent_id` and `content` cannot be empty strings
- MongoDB ObjectId format for returned `id`

**Errors:**

- `400 Bad Request` - Invalid memory type or importance score
- `500 Internal Server Error` - Database storage failure

---

#### `GET /api/memory/agents/{agent_id}/memories`

Retrieve memories for a specific agent with optional filtering by type, execution, and active status.

**Authentication:** None

**Path Parameters:**

- `agent_id` - The unique identifier of the agent

**Query Parameters:**

- `memory_types` (optional) - Comma-separated list of memory types to filter (e.g., "conversation,fact")
- `limit` (optional) - Maximum number of memories to return (default: 10, min: 1, max: 100)
- `only_active` (optional) - Return only active memories (default: true)
- `graph_execution_id` (optional) - Filter memories by specific execution ID

**Response:**

```json
[
  {
    "id": "65a3f2c1b4e8d9a7c6b5e4f3",
    "agent_id": "agent-code-reviewer-v2",
    "agent_name": "Code Reviewer Assistant",
    "memory_type": "fact",
    "content": "User prefers snake_case naming convention for Python variables",
    "importance_score": 0.8,
    "access_count": 3,
    "is_active": true,
    "created_at": "2025-01-15T14:30:22.123456",
    "last_accessed": "2025-01-15T15:42:10.654321"
  },
  {
    "id": "65a3f2c1b4e8d9a7c6b5e4f4",
    "agent_id": "agent-code-reviewer-v2",
    "agent_name": "Code Reviewer Assistant",
    "memory_type": "instruction",
    "content": "Always check for type hints in Python code reviews",
    "importance_score": 0.9,
    "access_count": 5,
    "is_active": true,
    "created_at": "2025-01-15T14:28:15.987654",
    "last_accessed": "2025-01-15T15:42:10.654321"
  }
]
```

**Use Cases:**

- Retrieving agent context before starting a conversation
- Loading relevant memories for specific workflow execution
- Filtering by memory type to get only facts or instructions
- Implementing memory-based agent personalisation
- Building conversation context for LLM prompts

**Behaviour:**

- Memories are returned ordered by importance_score and recency
- Automatically updates `access_count` and `last_accessed` for retrieved memories
- Empty array returned if no memories match filters
- `memory_types` parameter supports multiple types via comma separation
- `limit` parameter controls pagination

**Validation:**

- `limit` must be between 1 and 100
- `memory_types` values must be valid memory types
- `only_active` must be boolean (true/false)

**Example Requests:**

```bash
# Get all active memories for agent
GET /api/memory/agents/agent-123/memories

# Get only conversation and fact memories
GET /api/memory/agents/agent-123/memories?memory_types=conversation,fact

# Get up to 50 memories including inactive ones
GET /api/memory/agents/agent-123/memories?limit=50&only_active=false

# Get memories for specific execution
GET /api/memory/agents/agent-123/memories?graph_execution_id=exec-456
```

**Errors:**

- `400 Bad Request` - Invalid memory_types or limit parameter
- `500 Internal Server Error` - Database retrieval failure

---

#### `DELETE /api/memory/agents/{agent_id}/memories`

Clear all memories for a specific agent, with optional filtering by execution ID.

**Authentication:** None

**Path Parameters:**

- `agent_id` - The unique identifier of the agent

**Query Parameters:**

- `graph_execution_id` (optional) - Only clear memories associated with this execution ID

**Response:**

```json
{
  "message": "Successfully cleared 24 memories for agent agent-code-reviewer-v2",
  "count": 24
}
```

**Use Cases:**

- Resetting agent memory between sessions
- Clearing memories after workflow completion
- Removing execution-specific memories while preserving others
- Implementing "forget" functionality for agents
- Cleaning up test data during development

**Behaviour:**

- Permanently deletes memory records from database
- If `graph_execution_id` is provided, only memories with that execution ID are deleted
- If `graph_execution_id` is omitted, ALL memories for the agent are deleted
- Returns count of deleted memories
- Safe to call even if no memories exist (returns count: 0)

**Validation:**

- `agent_id` must be non-empty string
- `graph_execution_id` format is not validated (any string accepted)

**Example Requests:**

```bash
# Clear ALL memories for agent
DELETE /api/memory/agents/agent-123/memories

# Clear only memories from specific execution
DELETE /api/memory/agents/agent-123/memories?graph_execution_id=exec-456
```

**Errors:**

- `400 Bad Request` - Memory deletion validation error
- `500 Internal Server Error` - Database deletion failure

**Warning:**
This operation is **irreversible**. All deleted memories cannot be recovered. Use with caution in production
environments.

---

### Conversation History

#### `GET /api/memory/agents/{agent_id}/conversation-history`

Retrieve formatted conversation history for an agent, optimised for LLM context injection.

**Authentication:** None

**Path Parameters:**

- `agent_id` - The unique identifier of the agent

**Query Parameters:**

- `graph_execution_id` (optional) - Filter history by specific execution ID
- `limit` (optional) - Maximum number of history entries to return (default: 10, min: 1, max: 100)

**Response:**

```json
{
  "agent_id": "agent-customer-support-v1",
  "history": [
    {
      "timestamp": "2025-01-15T14:30:22.123456",
      "type": "conversation",
      "role": "user",
      "content": "How do I reset my password?"
    },
    {
      "timestamp": "2025-01-15T14:30:25.654321",
      "type": "conversation",
      "role": "agent",
      "content": "I can help you reset your password. Please click the 'Forgot Password' link on the login page."
    },
    {
      "timestamp": "2025-01-15T14:30:45.789012",
      "type": "conversation",
      "role": "user",
      "content": "I didn't receive the reset email."
    },
    {
      "timestamp": "2025-01-15T14:30:50.234567",
      "type": "conversation",
      "role": "agent",
      "content": "Let me check your email settings. Can you confirm your email address?"
    }
  ]
}
```

**Use Cases:**

- Loading conversation context for multi-turn dialogues
- Displaying chat history in UI applications
- Providing context for agent decision making
- Analysing conversation patterns
- Building conversation summaries

**Behaviour:**

- Returns conversation memories in chronological order
- Each entry includes timestamp, type, role, and content
- Role is typically "user" or "agent"
- Limited to conversation-type memories only
- Automatically filters by agent_id

**Validation:**

- `limit` must be between 1 and 100
- Returns empty history array if no conversations exist

**Example Requests:**

```bash
# Get last 10 conversation entries
GET /api/memory/agents/agent-123/conversation-history

# Get last 50 entries for specific execution
GET /api/memory/agents/agent-123/conversation-history?limit=50&graph_execution_id=exec-456
```

**Errors:**

- `400 Bad Request` - Invalid limit parameter
- `500 Internal Server Error` - Database retrieval failure

---

### Agent Profile Management

#### `GET /api/memory/agents/{agent_id}/profile`

Get or create an agent's memory profile with configuration settings and interaction statistics.

**Authentication:** None

**Path Parameters:**

- `agent_id` - The unique identifier of the agent

**Query Parameters:**

- `agent_name` (required) - Human-readable name for the agent
- `graph_id` (required) - The workflow/graph identifier this agent belongs to

**Response:**

```json
{
  "id": "65a3f2c1b4e8d9a7c6b5e4f5",
  "agent_id": "agent-customer-support-v1",
  "agent_name": "Customer Support Assistant",
  "graph_id": "graph-customer-service-workflow",
  "memory_window_size": 50,
  "summarization_threshold": 100,
  "memory_retention_days": 30,
  "total_conversations": 127,
  "total_messages": 543,
  "last_interaction": "2025-01-15T15:42:10.654321"
}
```

**Response Fields:**

- `id` - Unique profile identifier
- `agent_id` - Agent identifier
- `agent_name` - Agent display name
- `graph_id` - Associated workflow ID
- `memory_window_size` - Number of recent memories to keep in active context
- `summarization_threshold` - Number of messages before triggering summarisation
- `memory_retention_days` - Days to retain memories before pruning eligibility
- `total_conversations` - Count of conversation sessions
- `total_messages` - Total message count across all conversations
- `last_interaction` - Timestamp of most recent agent interaction

**Use Cases:**

- Initialising agent memory configuration
- Retrieving agent interaction statistics
- Configuring memory window size for context management
- Tracking agent usage patterns
- Setting up new agents in workflows

**Behaviour:**

- Creates profile if it doesn't exist (idempotent operation)
- Updates `last_interaction` timestamp on each call
- Default values applied for new profiles:
  - `memory_window_size`: 50
  - `summarization_threshold`: 100
  - `memory_retention_days`: 30
  - `total_conversations`: 0
  - `total_messages`: 0
- Profile is unique per (agent_id, graph_id) combination

**Validation:**

- `agent_id`, `agent_name`, and `graph_id` must be non-empty strings
- Parameters passed as query parameters, not request body

**Example Requests:**

```bash
# Get or create profile for agent
GET /api/memory/agents/agent-123/profile?agent_name=Support%20Bot&graph_id=graph-456
```

**Errors:**

- `400 Bad Request` - Missing required query parameters
- `500 Internal Server Error` - Database operation failure

---

### Memory Maintenance

#### `POST /api/memory/agents/{agent_id}/prune-memories`

Prune old or inactive memories for an agent based on retention policy.

**Authentication:** None

**Path Parameters:**

- `agent_id` - The unique identifier of the agent

**Query Parameters:**

- `retention_days` (optional) - Number of days to retain memories (default: 30, min: 1)

**Response:**

```json
{
  "message": "Successfully pruned 18 old memories for agent agent-code-reviewer-v2",
  "count": 18
}
```

**Use Cases:**

- Implementing memory retention policies
- Cleaning up old memories to reduce storage
- Maintaining memory database performance
- Scheduled maintenance tasks
- Removing outdated agent knowledge

**Behaviour:**

- Marks memories as inactive (soft delete) rather than deleting
- Prunes memories older than `retention_days` from creation date
- Only affects memories for the specified agent_id
- Does not prune high-importance memories (importance_score > 0.9)
- Returns count of memories marked inactive

**Validation:**

- `retention_days` must be at least 1
- Safe to run multiple times (idempotent)

**Example Requests:**

```bash
# Prune memories older than 30 days (default)
POST /api/memory/agents/agent-123/prune-memories

# Prune memories older than 7 days
POST /api/memory/agents/agent-123/prune-memories?retention_days=7

# Long-term retention (90 days)
POST /api/memory/agents/agent-123/prune-memories?retention_days=90
```

**Errors:**

- `400 Bad Request` - Invalid retention_days parameter
- `500 Internal Server Error` - Database update failure

**Performance Considerations:**

- Pruning operation may take time for agents with many memories
- Consider running as background task for large datasets
- Index on created_at field recommended for performance

---

## Error Handling

### Error Response Format

All error responses follow a consistent FastAPI HTTP exception format:

```json
{
  "detail": "Invalid memory type 'unknown'. Valid types: conversation, summary, fact, instruction"
}
```

### Common Error Codes

#### 400 Bad Request

Returned when request validation fails or business logic constraints are violated.

**Scenarios:**

- Invalid `memory_type` (not in: conversation, summary, fact, instruction)
- Invalid `importance_score` (not between 0.0 and 1.0)
- Invalid `limit` parameter (not between 1 and 100)
- Invalid `retention_days` (less than 1)
- Missing required fields in request body
- Invalid `memory_types` filter values

**Example:**

```json
{
  "detail": "Invalid importance score 1.5. Must be between 0.0 and 1.0"
}
```

#### 500 Internal Server Error

Returned when internal service operations fail.

**Scenarios:**

- Database connection failures
- Memory storage errors
- Memory retrieval errors
- Memory deletion errors
- Unexpected service exceptions

**Example:**

```json
{
  "detail": "Failed to store memory: Database connection timeout"
}
```

### Memory Service Exceptions

The Memory API catches and translates the following exceptions from `backend.services.memory`:

| Exception                     | HTTP Status | Description                                  |
|-------------------------------|-------------|----------------------------------------------|
| `MemoryError`                 | 400         | Base exception for memory-related errors     |
| `MemoryNotFoundError`         | 400         | Requested memory entry not found             |
| `AgentProfileNotFoundError`   | 400         | Agent profile not found (rare, auto-created) |
| `InvalidMemoryTypeError`      | 400         | Invalid memory type provided                 |
| `InvalidImportanceScoreError` | 400         | Importance score out of range                |
| `MemoryStorageError`          | 500         | Failed to store memory in database           |
| `MemoryRetrievalError`        | 500         | Failed to retrieve memories                  |
| `MemoryDeletionError`         | 500         | Failed to delete memories                    |

### Error Handling Example

**Python Client with Error Handling:**

```python
import httpx
from typing import Dict, Any

async def create_agent_memory(
    agent_id: str,
    content: str,
    memory_type: str = "conversation"
) -> Dict[str, Any]:
    """Create a memory with proper error handling."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/api/memory/memories",
                json={
                    "agent_id": agent_id,
                    "agent_name": "My Agent",
                    "memory_type": memory_type,
                    "content": content,
                    "importance_score": 0.7
                }
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            print(f"Validation error: {e.response.json()['detail']}")
        elif e.response.status_code == 500:
            print(f"Server error: {e.response.json()['detail']}")
        raise

    except httpx.RequestError as e:
        print(f"Network error: {e}")
        raise

# Usage
try:
    memory = await create_agent_memory(
        agent_id="agent-123",
        content="User prefers dark mode",
        memory_type="preference"  # Invalid type!
    )
except Exception as e:
    print(f"Failed to create memory: {e}")
    # Output: Validation error: Invalid memory type 'preference'.
    #         Valid types: conversation, summary, fact, instruction
```

**JavaScript Client with Error Handling:**

```javascript
async function createMemory(agentId, content, memoryType = 'conversation') {
  try {
    const response = await fetch('http://localhost:8000/api/memory/memories', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: agentId,
        agent_name: 'My Agent',
        memory_type: memoryType,
        content: content,
        importance_score: 0.7
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`API Error (${response.status}): ${error.detail}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to create memory:', error.message);
    throw error;
  }
}

// Usage
try {
  const memory = await createMemory('agent-123', 'User prefers dark mode');
  console.log('Memory created:', memory.id);
} catch (error) {
  // Handle error
}
```

---

## Integration with Services Layer

### Dependency Flow

The Memory API integrates with the services layer through a simple, direct pattern:

```
API Route (routes.py)
    ↓
Dependency Injection (dependencies.py)
    ↓
MemoryManager (backend.services.memory)
    ↓
┌─────────────┬──────────────┬──────────────┬──────────────┐
│   Repository│   Formatter  │  Statistics  │   Pruning    │
└─────────────┴──────────────┴──────────────┴──────────────┘
         ↓            ↓              ↓              ↓
    Database      LLM Context   Tracking       Lifecycle
```

### Dependency Injection

The Memory API uses FastAPI's dependency injection system via the `MemoryService` type alias:

**dependencies.py:**

```python
from typing import Annotated
from fastapi import Depends
from backend.services.memory import MemoryManager, get_memory_manager

def get_memory_service() -> MemoryManager:
    """Get memory manager instance."""
    return get_memory_manager()

# Type alias for cleaner endpoint signatures
MemoryService = Annotated[MemoryManager, Depends(get_memory_service)]
```

**Usage in Routes:**

```python
from .dependencies import MemoryService

@router.post("/memories")
async def create_memory(
    memory: MemoryCreateRequest,
    memory_service: MemoryService,  # Injected automatically
):
    created_memory = await memory_service.create_memory(
        agent_id=memory.agent_id,
        memory_type=memory.memory_type,
        content=memory.content
    )
    return created_memory
```

### Services Used

The Memory API relies on the following service components from `backend.services.memory`:

#### MemoryManager

**Purpose:** Main service interface coordinating all memory operations

**Key Methods:**

- `create_memory()` - Store new memory entry
- `get_agent_memories()` - Retrieve filtered memories
- `get_conversation_history()` - Get formatted conversation history
- `get_or_create_agent_profile()` - Manage agent profiles
- `prune_old_memories()` - Clean up old memories
- `clear_agent_memory()` - Delete agent memories
- `format_memory_context()` - Format memories for LLM context

**Location:** [backend/services/memory/manager.py](../../services/memory/manager.py)

#### MemoryRepository

**Purpose:** Database CRUD operations for memory storage

**Responsibilities:**

- Low-level database queries (MongoDB)
- Memory creation, retrieval, update, deletion
- Access tracking updates
- Agent profile management

**Location:** [backend/services/memory/repository.py](../../services/memory/repository.py)

#### MemoryFormatter

**Purpose:** Format memories for LLM context injection

**Responsibilities:**

- Convert memory entries to LLM-friendly format
- Organise memories by type and importance
- Generate context strings for prompts
- Handle conversation history formatting

**Location:** [backend/services/memory/formatter.py](../../services/memory/formatter.py)

#### MemoryStatistics

**Purpose:** Track agent interaction statistics

**Responsibilities:**

- Count conversations and messages
- Calculate memory usage metrics
- Track access patterns
- Update agent profile statistics

**Location:** [backend/services/memory/statistics.py](../../services/memory/statistics.py)

#### MemoryPruning

**Purpose:** Manage memory lifecycle and retention

**Responsibilities:**

- Identify old/inactive memories
- Apply retention policies
- Mark memories as inactive
- Preserve high-importance memories

**Location:** [backend/services/memory/pruning.py](../../services/memory/pruning.py)

### Example Integration

**Complete Flow Example:**

```python
# 1. User makes HTTP request
POST /api/memory/memories
{
  "agent_id": "agent-123",
  "agent_name": "Assistant",
  "memory_type": "fact",
  "content": "User's timezone is UTC+10"
}

# 2. Route handler in routes.py
@router.post("/memories", response_model=MemoryResponse)
async def create_memory(
    memory: MemoryCreateRequest,
    memory_service: MemoryService,  # ← Injected by FastAPI
):
    # 3. Call MemoryManager service
    created_memory = await memory_service.create_memory(
        agent_id=memory.agent_id,
        agent_name=memory.agent_name,
        memory_type=memory.memory_type,
        content=memory.content,
        importance_score=memory.importance_score,
    )

    # 4. MemoryManager coordinates with Repository
    # manager.py internally calls:
    # - MemoryRepository.create_memory()
    # - MemoryStatistics.update_agent_stats()

    # 5. Repository stores in MongoDB
    # - Inserts ConversationMemory document
    # - Returns created memory object

    # 6. Transform to API response model
    return MemoryResponse(
        id=str(created_memory.id),
        agent_id=created_memory.agent_id,
        # ... other fields
    )

# 7. FastAPI serialises response to JSON
```

### Model Transformation

The API uses different models at each layer for proper separation of concerns:

**API Layer (models.py):**

```python
class MemoryCreateRequest(BaseModel):
    """API request model for creating memory."""
    agent_id: str
    memory_type: str
    content: str
    importance_score: float = 0.5
```

**Service Layer (backend.services.memory.schemas):**

```python
class MemoryCreate(BaseModel):
    """Service schema for memory creation."""
    agent_id: str
    memory_type: str
    content: str
    importance_score: float = 0.5

    @field_validator("memory_type")
    def validate_memory_type(cls, v: str) -> str:
        # Validation logic
        pass
```

**Database Model (backend.models):**

```python
class ConversationMemory(Document):
    """MongoDB document for memory storage."""
    agent_id: str
    memory_type: str
    content: str
    importance_score: float
    access_count: int
    is_active: bool
    created_at: datetime
    # ... other fields
```

This layered approach ensures:

- API concerns (HTTP, JSON) stay in API layer
- Business logic (validation, transformation) in service layer
- Database concerns (queries, indexes) in repository layer

---

## Usage Examples

### Complete Memory Management Workflow

This example demonstrates a complete agent memory lifecycle from creation through retrieval and pruning.

**Python Example:**

```python
import httpx
from typing import List, Dict, Any
from datetime import datetime

class MemoryClient:
    """Client for AgenticStudio Memory API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def create_memory(
        self,
        agent_id: str,
        agent_name: str,
        memory_type: str,
        content: str,
        importance_score: float = 0.5,
        graph_execution_id: str = None
    ) -> Dict[str, Any]:
        """Create a new memory entry."""
        response = await self.client.post(
            f"{self.base_url}/api/memory/memories",
            json={
                "agent_id": agent_id,
                "agent_name": agent_name,
                "memory_type": memory_type,
                "content": content,
                "importance_score": importance_score,
                "graph_execution_id": graph_execution_id
            }
        )
        response.raise_for_status()
        return response.json()

    async def get_memories(
        self,
        agent_id: str,
        memory_types: List[str] = None,
        limit: int = 10,
        graph_execution_id: str = None
    ) -> List[Dict[str, Any]]:
        """Retrieve agent memories."""
        params = {"limit": limit}
        if memory_types:
            params["memory_types"] = ",".join(memory_types)
        if graph_execution_id:
            params["graph_execution_id"] = graph_execution_id

        response = await self.client.get(
            f"{self.base_url}/api/memory/agents/{agent_id}/memories",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_conversation_history(
        self,
        agent_id: str,
        limit: int = 10,
        graph_execution_id: str = None
    ) -> Dict[str, Any]:
        """Get conversation history."""
        params = {"limit": limit}
        if graph_execution_id:
            params["graph_execution_id"] = graph_execution_id

        response = await self.client.get(
            f"{self.base_url}/api/memory/agents/{agent_id}/conversation-history",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_agent_profile(
        self,
        agent_id: str,
        agent_name: str,
        graph_id: str
    ) -> Dict[str, Any]:
        """Get or create agent profile."""
        response = await self.client.get(
            f"{self.base_url}/api/memory/agents/{agent_id}/profile",
            params={"agent_name": agent_name, "graph_id": graph_id}
        )
        response.raise_for_status()
        return response.json()

    async def prune_memories(
        self,
        agent_id: str,
        retention_days: int = 30
    ) -> Dict[str, Any]:
        """Prune old memories."""
        response = await self.client.post(
            f"{self.base_url}/api/memory/agents/{agent_id}/prune-memories",
            params={"retention_days": retention_days}
        )
        response.raise_for_status()
        return response.json()

    async def clear_memories(
        self,
        agent_id: str,
        graph_execution_id: str = None
    ) -> Dict[str, Any]:
        """Clear agent memories."""
        params = {}
        if graph_execution_id:
            params["graph_execution_id"] = graph_execution_id

        response = await self.client.delete(
            f"{self.base_url}/api/memory/agents/{agent_id}/memories",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def example_workflow():
    """Demonstrate complete memory management workflow."""
    client = MemoryClient()

    try:
        agent_id = "agent-customer-support-v1"
        agent_name = "Customer Support Assistant"
        graph_id = "graph-support-workflow"
        execution_id = "exec-2025-01-15-001"

        # 1. Get or create agent profile
        print("📋 Creating agent profile...")
        profile = await client.get_agent_profile(
            agent_id=agent_id,
            agent_name=agent_name,
            graph_id=graph_id
        )
        print(f"✓ Profile created: {profile['id']}")
        print(f"  Memory window: {profile['memory_window_size']}")
        print(f"  Retention: {profile['memory_retention_days']} days\n")

        # 2. Create various types of memories
        print("💾 Creating memories...")

        # Fact memory
        fact = await client.create_memory(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type="fact",
            content="Customer's account was created on 2024-03-15",
            importance_score=0.7,
            graph_execution_id=execution_id
        )
        print(f"✓ Fact stored: {fact['id']}")

        # Instruction memory
        instruction = await client.create_memory(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type="instruction",
            content="Always verify customer identity before account changes",
            importance_score=0.9,
            graph_execution_id=execution_id
        )
        print(f"✓ Instruction stored: {instruction['id']}")

        # Conversation memories
        conversation_1 = await client.create_memory(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type="conversation",
            content="User: How do I update my billing address?",
            importance_score=0.5,
            graph_execution_id=execution_id
        )

        conversation_2 = await client.create_memory(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type="conversation",
            content="Agent: You can update your billing address in Account Settings > Billing",
            importance_score=0.5,
            graph_execution_id=execution_id
        )
        print(f"✓ Conversation turns stored\n")

        # 3. Retrieve all memories
        print("📖 Retrieving all memories...")
        all_memories = await client.get_memories(
            agent_id=agent_id,
            limit=50,
            graph_execution_id=execution_id
        )
        print(f"✓ Retrieved {len(all_memories)} memories")
        for mem in all_memories:
            print(f"  - [{mem['memory_type']}] {mem['content'][:50]}...")
        print()

        # 4. Get only facts and instructions
        print("🔍 Retrieving facts and instructions...")
        important_memories = await client.get_memories(
            agent_id=agent_id,
            memory_types=["fact", "instruction"],
            limit=20
        )
        print(f"✓ Retrieved {len(important_memories)} important memories\n")

        # 5. Get conversation history
        print("💬 Retrieving conversation history...")
        history = await client.get_conversation_history(
            agent_id=agent_id,
            limit=20,
            graph_execution_id=execution_id
        )
        print(f"✓ Retrieved {len(history['history'])} conversation entries")
        for entry in history['history'][:2]:
            print(f"  - {entry.get('role', 'N/A')}: {entry['content'][:50]}...")
        print()

        # 6. Prune old memories (in production, this would be scheduled)
        print("🧹 Pruning old memories...")
        prune_result = await client.prune_memories(
            agent_id=agent_id,
            retention_days=30
        )
        print(f"✓ {prune_result['message']}\n")

        # 7. Clear execution-specific memories
        print("🗑️  Clearing execution-specific memories...")
        clear_result = await client.clear_memories(
            agent_id=agent_id,
            graph_execution_id=execution_id
        )
        print(f"✓ {clear_result['message']}\n")

        print("✅ Workflow completed successfully!")

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(f"   {e.response.json()}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()


# Run the workflow
if __name__ == "__main__":
    import asyncio
    asyncio.run(example_workflow())
```

**JavaScript/TypeScript Example:**

```typescript
interface Memory {
  id: string;
  agent_id: string;
  agent_name: string;
  memory_type: 'conversation' | 'summary' | 'fact' | 'instruction';
  content: string;
  importance_score: number;
  access_count: number;
  is_active: boolean;
  created_at: string;
  last_accessed: string | null;
}

interface AgentProfile {
  id: string;
  agent_id: string;
  agent_name: string;
  graph_id: string;
  memory_window_size: number;
  summarization_threshold: number;
  memory_retention_days: number;
  total_conversations: number;
  total_messages: number;
  last_interaction: string | null;
}

class MemoryAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async createMemory(params: {
    agent_id: string;
    agent_name: string;
    memory_type: 'conversation' | 'summary' | 'fact' | 'instruction';
    content: string;
    importance_score?: number;
    graph_execution_id?: string;
  }): Promise<Memory> {
    const response = await fetch(`${this.baseUrl}/api/memory/memories`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...params,
        importance_score: params.importance_score ?? 0.5,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to create memory: ${error.detail}`);
    }

    return response.json();
  }

  async getMemories(
    agentId: string,
    options?: {
      memory_types?: string[];
      limit?: number;
      graph_execution_id?: string;
    }
  ): Promise<Memory[]> {
    const params = new URLSearchParams();
    if (options?.memory_types) {
      params.set('memory_types', options.memory_types.join(','));
    }
    if (options?.limit) {
      params.set('limit', options.limit.toString());
    }
    if (options?.graph_execution_id) {
      params.set('graph_execution_id', options.graph_execution_id);
    }

    const response = await fetch(
      `${this.baseUrl}/api/memory/agents/${agentId}/memories?${params}`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to get memories: ${error.detail}`);
    }

    return response.json();
  }

  async getProfile(
    agentId: string,
    agentName: string,
    graphId: string
  ): Promise<AgentProfile> {
    const params = new URLSearchParams({
      agent_name: agentName,
      graph_id: graphId,
    });

    const response = await fetch(
      `${this.baseUrl}/api/memory/agents/${agentId}/profile?${params}`
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Failed to get profile: ${error.detail}`);
    }

    return response.json();
  }
}

// Usage example
async function agentConversationExample() {
  const client = new MemoryAPIClient();
  const agentId = 'agent-chatbot-v1';

  try {
    // Create agent profile
    const profile = await client.getProfile(
      agentId,
      'Chatbot Assistant',
      'graph-chat-workflow'
    );
    console.log(`Agent profile: ${profile.id}`);

    // Store user message
    await client.createMemory({
      agent_id: agentId,
      agent_name: 'Chatbot Assistant',
      memory_type: 'conversation',
      content: 'User: What are your business hours?',
      importance_score: 0.5,
    });

    // Store agent response
    await client.createMemory({
      agent_id: agentId,
      agent_name: 'Chatbot Assistant',
      memory_type: 'conversation',
      content: 'Agent: We are open Monday-Friday, 9 AM to 5 PM EST.',
      importance_score: 0.5,
    });

    // Store learned fact
    await client.createMemory({
      agent_id: agentId,
      agent_name: 'Chatbot Assistant',
      memory_type: 'fact',
      content: 'User prefers communication via email',
      importance_score: 0.8,
    });

    // Retrieve context for next response
    const memories = await client.getMemories(agentId, {
      limit: 20,
      memory_types: ['conversation', 'fact'],
    });

    console.log(`Retrieved ${memories.length} memories for context`);

    // Use memories to build LLM context
    const context = memories
      .map(m => `[${m.memory_type}] ${m.content}`)
      .join('\n');

    console.log('Context for LLM:\n', context);

  } catch (error) {
    console.error('Error:', error);
  }
}
```

---

## Performance Considerations

### Endpoint Performance

Memory API endpoints are categorised by typical response time:

#### Fast Endpoints (< 100ms)

- `POST /api/memory/memories` - Single database insert
- `GET /api/memory/agents/{agent_id}/profile` - Single document retrieval

#### Medium Endpoints (100-500ms)

- `GET /api/memory/agents/{agent_id}/memories` - Filtered query, limited results
- `GET /api/memory/agents/{agent_id}/conversation-history` - Conversation filtering
- `DELETE /api/memory/agents/{agent_id}/memories` - Delete operation with execution filter

#### Potentially Slow Endpoints (> 500ms)

- `POST /api/memory/agents/{agent_id}/prune-memories` - Bulk update operation on old memories
- `DELETE /api/memory/agents/{agent_id}/memories` - Without execution filter (deletes all agent memories)

### Optimisation Tips

#### 1. Limit Result Sets

**Bad:**

```python
# Retrieves all memories (could be thousands)
memories = await client.get_memories(agent_id="agent-123", limit=100)
```

**Good:**

```python
# Only retrieve what you need
memories = await client.get_memories(
    agent_id="agent-123",
    limit=10,  # Small limit for recent context
    memory_types=["fact", "instruction"],  # Filter by type
    graph_execution_id=current_execution_id  # Scope to execution
)
```

#### 2. Filter by Memory Type

**Bad:**

```python
# Retrieve all memories and filter in application
all_memories = await client.get_memories(agent_id, limit=50)
facts = [m for m in all_memories if m['memory_type'] == 'fact']
```

**Good:**

```python
# Filter at database level
facts = await client.get_memories(
    agent_id=agent_id,
    memory_types=["fact"],
    limit=20
)
```

#### 3. Use Execution Scoping

**Bad:**

```python
# Gets all agent memories across all executions
memories = await client.get_memories(agent_id="agent-123", limit=50)
```

**Good:**

```python
# Scope to current execution for relevant context
memories = await client.get_memories(
    agent_id="agent-123",
    graph_execution_id=current_execution_id,  # Much smaller result set
    limit=20
)
```

#### 4. Batch Memory Creation

**Bad:**

```python
# Multiple sequential API calls
for message in conversation:
    await client.create_memory(
        agent_id=agent_id,
        memory_type="conversation",
        content=message
    )
```

**Good:**

```python
# Use asyncio.gather for parallel creation
import asyncio

tasks = [
    client.create_memory(
        agent_id=agent_id,
        memory_type="conversation",
        content=message
    )
    for message in conversation
]
await asyncio.gather(*tasks)
```

#### 5. Prune Regularly but Not Frequently

**Bad:**

```python
# Prune after every conversation
await client.prune_memories(agent_id, retention_days=30)
```

**Good:**

```python
# Schedule pruning as a background task (daily/weekly)
# Use a job scheduler like Celery or cron
@scheduled_task(interval="daily")
async def prune_agent_memories():
    for agent_id in active_agents:
        await client.prune_memories(agent_id, retention_days=30)
```

### Database Indexing Recommendations

For optimal performance, ensure the following indexes exist on the `conversation_memories` collection:

```javascript
// MongoDB indexes
db.conversation_memories.createIndex({ "agent_id": 1, "is_active": 1 })
db.conversation_memories.createIndex({ "agent_id": 1, "graph_execution_id": 1 })
db.conversation_memories.createIndex({ "agent_id": 1, "memory_type": 1, "is_active": 1 })
db.conversation_memories.createIndex({ "created_at": 1 })  // For pruning
db.conversation_memories.createIndex({ "importance_score": -1 })  // For retrieval ordering
```

### Caching Strategies

While the Memory API doesn't implement caching internally, consider these patterns:

**Client-Side Caching:**

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedMemoryClient(MemoryClient):
    """Memory client with local caching."""

    def __init__(self, *args, cache_ttl_seconds=60, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)

    async def get_memories(self, agent_id: str, **kwargs):
        """Get memories with caching."""
        cache_key = f"{agent_id}:{kwargs}"

        # Check cache
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return cached_data

        # Fetch from API
        memories = await super().get_memories(agent_id, **kwargs)

        # Update cache
        self.cache[cache_key] = (memories, datetime.now())

        return memories
```

**Note:** Be cautious with caching as memory state changes frequently during agent conversations.

---

## Related Documentation

### API Modules

- [Graph API](../../../backend/api/graph/graph.md) - Workflow management and execution
- [Execution API](../../../backend/api/execution/execution.md) - Workflow execution orchestration
- [Execution History API](../../../backend/api/execution_history/execution_history.md) - Execution logs and results

### Architecture Documentation

- [Services Architecture](../architecture/services.md) - Service layer design patterns
- [Database Design](../architecture/database.md) - MongoDB collections and schemas
- [Agent System](../architecture/agents.md) - Agent design and memory integration

### Service Layer Documentation

- [Memory Service](../../services/memory.md) - Memory service implementation details
- [Repository Pattern](../services/repository.md) - Data access patterns

### Related Concepts

- **Workflow Execution Context:** Memories are scoped to `graph_execution_id` for execution-specific context
- **Agent Profiles:** Configuration and statistics for agent memory behaviour
- **Memory Types:** Understanding conversation, summary, fact, and instruction types
- **Importance Scoring:** How importance affects memory retrieval and pruning

---

## Summary

The Memory API module provides a comprehensive, simple-to-use interface for agent memory management in AgenticStudio. It
enables AI agents to maintain context across conversations, learn from interactions, and apply retention policies for
long-term memory health.

### Key Features

- **Flexible Memory Storage:** Support for four memory types (conversation, summary, fact, instruction) with importance
  scoring
- **Conversation History Tracking:** Structured conversation history for multi-turn dialogues
- **Agent Profiles:** Per-agent configuration for memory window size, summarisation, and retention policies
- **Memory Lifecycle Management:** Automated pruning and manual clearing capabilities
- **Execution Scoping:** Filter memories by workflow execution for relevant context
- **Access Tracking:** Automatic tracking of memory access patterns and frequency
- **Simple Integration:** Direct service integration pattern with minimal overhead
- **Type-Safe Operations:** Pydantic models ensure data validation throughout the stack

### Primary Use Cases

1. **Conversational Agents:** Maintain dialogue history and context across multiple turns
2. **Learning Systems:** Store facts and insights learned during agent interactions
3. **Personalisation:** Remember user preferences and customisation settings
4. **Instruction Following:** Preserve user instructions for consistent agent behaviour
5. **Context Management:** Provide relevant historical context for agent decision-making
6. **Memory Optimisation:** Automatically prune old memories to maintain performance
7. **Multi-Execution Workflows:** Scope memories to specific workflow executions
8. **Agent Analytics:** Track memory usage patterns and interaction statistics

### Architecture Highlights

- **Direct Service Pattern:** Routes call services directly without intermediate handlers
- **Clean Separation:** API models, service schemas, and database models are distinct layers
- **Dependency Injection:** FastAPI's DI system for testable, maintainable code
- **Error Handling:** Custom exceptions with HTTP status code mapping
- **Performance Optimised:** Support for filtering, limiting, and execution scoping
- **No Authentication:** Public API suitable for internal service communication

The Memory API is a foundational component for building context-aware, personalised AI agents in the AgenticStudio platform.
Its simple design and powerful features make it easy to integrate memory capabilities into any workflow.
