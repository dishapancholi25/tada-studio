# Memory Service

## Overview

The memory service provides comprehensive memory management capabilities for agents in the AgenticStudio system. It handles
conversation history tracking, memory storage, retrieval, formatting, and lifecycle management. The service enables
agents to maintain context across interactions while providing flexible memory retention policies and pruning
strategies.

**Location:** `backend/services/memory/`

**Primary Responsibilities:**

- Store and retrieve agent conversation memories
- Manage agent memory profiles with configurable retention policies
- Format memories into context strings for LLM prompts
- Track agent interaction statistics
- Prune old or inactive memories based on retention policies
- Support both thread-scoped and global memory strategies

**Key Use Cases:**

- Maintaining conversation context for chatbot agents
- Storing important facts and summaries for long-term memory
- Managing memory lifecycle across multiple executions
- Formatting conversation history for agent prompts
- Tracking agent usage patterns and interaction statistics

## Architecture

### Module Structure

```
backend/services/memory/
├── __init__.py           # Public API exports and package documentation
├── manager.py            # High-level memory management interface
├── repository.py         # Database CRUD operations
├── formatter.py          # Memory formatting for LLM context
├── statistics.py         # Agent interaction tracking
├── pruning.py           # Memory lifecycle management
├── exceptions.py        # Custom exception definitions
└── schemas.py           # Pydantic data models
```

**File Purposes:**

- **manager.py**: Main service interface that coordinates between repository, formatter, statistics, and pruning
  modules. Provides high-level methods for all memory operations.
- **repository.py**: Handles all database interactions using SQLAlchemy. Provides async methods for CRUD operations on
  memories and agent profiles.
- **formatter.py**: Utilities for formatting memory data into context strings suitable for LLM prompts. Handles JSON
  parsing and conversation history structuring.
- **statistics.py**: Tracks and manages agent interaction statistics including conversation counts and message counts.
- **pruning.py**: Manages memory lifecycle through retention policies, pruning old memories, and clearing agent
  memories.
- **exceptions.py**: Domain-specific exception classes for better error handling and debugging.
- **schemas.py**: Pydantic models for type-safe data validation and serialisation within the service layer.

### Design Patterns

**Singleton Pattern:**

- The `MemoryManager` uses a singleton pattern via `get_memory_manager()` to ensure a single instance across the
  application
- Provides `reset_memory_manager()` for testing and reinitialisation

**Repository Pattern:**

- `MemoryRepository` abstracts database operations from business logic
- Static methods provide a clean interface without instance state

**Dependency Injection:**

- The manager injects repository instance into statistics and pruning components
- Enables easier testing and mocking of dependencies

**Separation of Concerns:**

- Each module has a single, well-defined responsibility
- Manager coordinates between specialised modules
- Clear boundaries between storage, formatting, and business logic

**Component Relationships:**

```
MemoryManager (Coordinator)
    ├── MemoryRepository (Data Access)
    ├── MemoryFormatter (Presentation)
    ├── MemoryStatistics (Analytics)
    │   └── uses MemoryRepository
    └── MemoryPruning (Lifecycle)
        └── uses MemoryRepository
```

### Dependencies

**Internal Dependencies:**

- `backend.models.memory.ConversationMemory` - Database model for memory entries
- `backend.models.memory.AgentMemoryProfile` - Database model for agent profiles
- `backend.services.database.get_db` - Database session management
- `backend.services.config.get_logger` - Logging configuration

**External Dependencies:**

- `sqlalchemy` - Database ORM for queries and transactions
- `pydantic` - Data validation and serialisation
- `datetime` - Timestamp handling with timezone support

**Database Dependencies:**

- `conversation_memories` table - Stores all memory entries
- `agent_memory_profiles` table - Stores agent configuration and statistics

**Environment Variables:**
None directly used by this service (database configuration is handled by the database service)

## Public API

### Exported Classes

- `MemoryManager` - Main interface for memory management operations
- `MemoryRepository` - Database repository for memory operations (advanced usage)
- `MemoryFormatter` - Utilities for formatting memory data (advanced usage)
- `MemoryStatistics` - Statistics tracking for agent memories (advanced usage)
- `MemoryPruning` - Memory lifecycle management (advanced usage)

### Exported Functions

- `get_memory_manager()` - Get singleton MemoryManager instance
- `reset_memory_manager()` - Reset singleton instance (testing only)

### Constants and Configuration

No exported constants. Configuration is stored in database models:

- Default memory window size: 10 messages
- Default summarisation threshold: 20 messages
- Default retention days: 30 days
- Default importance score: 0.5

### Exceptions

```
Exception
└── MemoryError (base exception)
    ├── MemoryNotFoundError
    ├── AgentProfileNotFoundError
    ├── InvalidMemoryTypeError
    ├── MemoryStorageError
    ├── MemoryRetrievalError
    ├── MemoryDeletionError
    └── InvalidImportanceScoreError
```

### Schemas

- `MemoryCreate` - Input schema for creating memories
- `MemoryData` - Output schema for memory data
- `AgentProfileData` - Output schema for agent profiles
- `ConversationTurn` - Schema for conversation turn pairs
- `ConversationHistoryEntry` - Schema for formatted history
- `MemoryQuery` - Schema for querying memories
- `MemoryStatistics` - Schema for statistics data

## Core Classes

### `MemoryManager`

Main interface for memory management operations, coordinating between repository, formatting, statistics, and pruning
operations.

**Purpose:** Provides a high-level API for all memory operations, abstracting the complexity of coordinating multiple
specialised components.

**Responsibilities:**

- Create and store memory entries
- Retrieve memories with filtering and pagination
- Format memories for agent context
- Manage agent profiles and statistics
- Coordinate pruning and summarisation operations

**Initialisation:**

```python
def __init__(self) -> None:
    """Initialise memory manager with dependencies."""
```

The manager automatically initialises all required components. Use `get_memory_manager()` instead of direct
instantiation.

**Key Methods:**

#### `create_memory()`

```python
async def create_memory(
    self,
    agent_id: str,
    agent_name: str,
    memory_type: str,
    content: str,
    graph_execution_id: Optional[str] = None,
    node_execution_id: Optional[str] = None,
    importance_score: float = 0.5,
) -> ConversationMemory:
    """Create a new memory entry."""
```

**Parameters:**

- `agent_id` (str) - Unique agent identifier
- `agent_name` (str) - Human-readable agent name
- `memory_type` (str) - Type of memory: "conversation", "summary", "fact", or "instruction"
- `content` (str) - Memory content (can be plain text or JSON string)
- `graph_execution_id` (Optional[str]) - Associated graph execution ID for filtering
- `node_execution_id` (Optional[str]) - Associated node execution ID
- `importance_score` (float) - Memory importance from 0.0 to 1.0 (default: 0.5)

**Returns:**

- `ConversationMemory` - Created memory entry with database ID and metadata

**Raises:**

- `MemoryStorageError` - If memory creation fails

**Example:**

```python
from backend.services.memory import get_memory_manager

manager = get_memory_manager()

# Create a conversation memory
memory = await manager.create_memory(
    agent_id="agent-123",
    agent_name="Customer Support Bot",
    memory_type="conversation",
    content="User asked about pricing plans",
    graph_execution_id="exec-456",
    importance_score=0.7,
)

print(f"Created memory with ID: {memory.id}")
```

**Behaviour:**

- Validates memory type against allowed values
- Creates database entry with timestamp
- Initialises access tracking (count=0, last_accessed=None)
- Sets memory as active by default
- Logs creation for debugging

**Use Cases:**

- Store conversation turns during agent execution
- Save important facts extracted from conversations
- Record summaries of long conversations
- Store agent-specific instructions or preferences

#### `get_agent_memories()`

```python
async def get_agent_memories(
    self,
    agent_id: str,
    memory_types: Optional[list[str]] = None,
    limit: int = 10,
    only_active: bool = True,
    graph_execution_id: Optional[str] = None,
) -> list[dict]:
    """Get memories for a specific agent."""
```

**Parameters:**

- `agent_id` (str) - Agent identifier
- `memory_types` (Optional[list[str]]) - Filter by memory types (e.g., ["conversation", "fact"])
- `limit` (int) - Maximum number of memories to return (default: 10)
- `only_active` (bool) - Whether to only return active memories (default: True)
- `graph_execution_id` (Optional[str]) - Filter by execution ID

**Returns:**

- `list[dict]` - List of memory dictionaries with fields: id, agent_id, agent_name, memory_type, content,
  importance_score, access_count, is_active, created_at, graph_execution_id, node_execution_id, last_accessed

**Raises:**

- `MemoryRetrievalError` - If retrieval fails

**Example:**

```python
# Get recent conversation memories
memories = await manager.get_agent_memories(
    agent_id="agent-123",
    memory_types=["conversation"],
    limit=20,
)

for memory in memories:
    print(f"{memory['created_at']}: {memory['content']}")
```

**Behaviour:**

- Filters out expired memories automatically
- Orders by creation time (newest first)
- Updates access tracking for retrieved memories
- Converts database models to dictionaries

**Use Cases:**

- Load conversation history before agent execution
- Display memory contents in UI
- Retrieve facts for context injection
- Export memory data

#### `get_conversation_history()`

```python
async def get_conversation_history(
    self,
    agent_id: str,
    graph_execution_id: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Get conversation history for an agent."""
```

**Parameters:**

- `agent_id` (str) - Agent identifier
- `graph_execution_id` (Optional[str]) - Filter by execution ID
- `limit` (int) - Maximum number of history entries (default: 10)

**Returns:**

- `list[dict]` - Formatted conversation history with fields: timestamp, type, content, role

**Example:**

```python
# Get formatted conversation history
history = await manager.get_conversation_history(
    agent_id="agent-123",
    limit=10,
)

for entry in history:
    print(f"[{entry['timestamp']}] {entry['role']}: {entry['content']}")
```

**Behaviour:**

- Retrieves only "conversation" type memories
- Formats memories into structured history entries
- Parses JSON content if present
- Returns entries in chronological order

**Use Cases:**

- Display conversation history in chat UI
- Generate conversation transcripts
- Analyse conversation patterns

#### `store_conversation_turn()`

```python
async def store_conversation_turn(
    self,
    agent_id: str,
    agent_name: str,
    user_message: str,
    agent_response: str,
    graph_execution_id: Optional[str] = None,
    node_execution_id: Optional[str] = None,
) -> None:
    """Store a complete conversation turn (user message + agent response)."""
```

**Parameters:**

- `agent_id` (str) - Agent identifier
- `agent_name` (str) - Agent name
- `user_message` (str) - User's message
- `agent_response` (str) - Agent's response
- `graph_execution_id` (Optional[str]) - Graph execution ID
- `node_execution_id` (Optional[str]) - Node execution ID

**Returns:**

- None

**Example:**

```python
# Store a conversation turn
await manager.store_conversation_turn(
    agent_id="agent-123",
    agent_name="Customer Support Bot",
    user_message="What are your pricing plans?",
    agent_response="We offer three tiers: Basic, Pro, and Enterprise.",
    graph_execution_id="exec-456",
)
```

**Behaviour:**

- Creates two memory entries (user message and agent response)
- Formats content as JSON with role information
- Updates agent statistics (+2 messages)
- Sets default importance score (0.5) for both

**Use Cases:**

- Store complete Q&A pairs from chat interactions
- Maintain conversation context for future interactions
- Build training datasets from conversations

#### `get_or_create_agent_profile()`

```python
async def get_or_create_agent_profile(
    self,
    agent_id: str,
    agent_name: str,
    graph_id: str
) -> dict:
    """Get or create an agent memory profile."""
```

**Parameters:**

- `agent_id` (str) - Unique agent identifier
- `agent_name` (str) - Human-readable agent name
- `graph_id` (str) - Graph that this agent belongs to

**Returns:**

- `dict` - Profile configuration with fields: id, agent_id, agent_name, graph_id, memory_window_size,
  summarization_threshold, memory_retention_days, total_conversations, total_messages, last_interaction

**Example:**

```python
# Get or create agent profile
profile = await manager.get_or_create_agent_profile(
    agent_id="agent-123",
    agent_name="Customer Support Bot",
    graph_id="graph-789",
)

print(f"Memory window size: {profile['memory_window_size']}")
print(f"Total conversations: {profile['total_conversations']}")
```

**Behaviour:**

- Creates profile if it doesn't exist
- Uses default values for new profiles
- Returns existing profile if already created

**Use Cases:**

- Initialise memory settings for new agents
- Retrieve memory configuration for agent execution
- Track agent usage statistics

#### `format_memory_context()`

```python
async def format_memory_context(self, memories: list[dict]) -> str:
    """Format memories into a context string for the agent."""
```

**Parameters:**

- `memories` (list[dict]) - List of memory dictionaries

**Returns:**

- `str` - Formatted context string suitable for LLM prompts

**Example:**

```python
# Format memories for agent prompt
memories = await manager.get_agent_memories("agent-123", limit=10)
context = await manager.format_memory_context(memories)

prompt = f"""
You are a helpful assistant.

{context}

User: How can I help you today?
"""
```

**Behaviour:**

- Groups memories by type (summaries, facts, conversations)
- Formats each type differently
- Limits number of each type shown
- Returns empty string if no memories

**Use Cases:**

- Inject conversation history into agent prompts
- Provide context for agent decision-making
- Display formatted memory in UI

#### `prune_old_memories()`

```python
async def prune_old_memories(
    self,
    agent_id: str,
    retention_days: int = 30
) -> int:
    """Prune old memories for an agent."""
```

**Parameters:**

- `agent_id` (str) - Agent identifier
- `retention_days` (int) - Number of days to retain memories (default: 30)

**Returns:**

- `int` - Number of memories pruned

**Example:**

```python
# Prune memories older than 30 days
pruned_count = await manager.prune_old_memories(
    agent_id="agent-123",
    retention_days=30,
)

print(f"Pruned {pruned_count} old memories")
```

**Behaviour:**

- Soft-deletes memories (sets is_active=False)
- Only prunes conversation memories with importance < 0.5
- Keeps important memories regardless of age

**Use Cases:**

- Regular cleanup of old conversation data
- Enforce data retention policies
- Reduce database size

#### `clear_agent_memory()`

```python
async def clear_agent_memory(
    self,
    agent_id: str,
    graph_execution_id: Optional[str] = None
) -> int:
    """Clear all memories for an agent."""
```

**Parameters:**

- `agent_id` (str) - Agent identifier
- `graph_execution_id` (Optional[str]) - Optional execution ID filter

**Returns:**

- `int` - Number of memories cleared

**Example:**

```python
# Clear all memories for an agent
cleared_count = await manager.clear_agent_memory(agent_id="agent-123")

# Clear memories for specific execution
cleared_count = await manager.clear_agent_memory(
    agent_id="agent-123",
    graph_execution_id="exec-456",
)
```

**Behaviour:**

- Permanently deletes memories from database
- Can filter by execution ID for thread-scoped clearing
- Returns count of deleted entries

**Use Cases:**

- Reset agent memory for testing
- Clear thread-specific memories
- Implement "forget everything" feature

#### `summarize_conversation()`

```python
async def summarize_conversation(
    self,
    agent_id: str,
    agent_name: str,
    conversation_memory_ids: list[str],
    graph_execution_id: Optional[str] = None,
) -> Optional[str]:
    """Create a summary of a conversation."""
```

**Parameters:**

- `agent_id` (str) - Agent identifier
- `agent_name` (str) - Agent name
- `conversation_memory_ids` (list[str]) - IDs of memories to summarise
- `graph_execution_id` (Optional[str]) - Graph execution ID

**Returns:**

- `Optional[str]` - Summary text or None if no memories

**Example:**

```python
# Get recent memories
memories = await manager.get_agent_memories("agent-123", limit=20)
memory_ids = [m["id"] for m in memories]

# Create summary
summary = await manager.summarize_conversation(
    agent_id="agent-123",
    agent_name="Customer Support Bot",
    conversation_memory_ids=memory_ids,
)
```

**Behaviour:**

- Currently uses simple placeholder summarisation
- Creates a new "summary" type memory
- Lowers importance score of summarised memories to 0.3
- In production, would use LLM for actual summarisation

**Use Cases:**

- Condense long conversations into summaries
- Reduce memory usage while preserving context
- Generate conversation abstracts

**Class Attributes:**

- `repository: MemoryRepository` - Database operations handler
- `formatter: MemoryFormatter` - Memory formatting utilities
- `statistics: MemoryStatistics` - Statistics tracking
- `pruning: MemoryPruning` - Lifecycle management

### `MemoryRepository`

Repository for memory database operations providing async methods for CRUD operations.

**Purpose:** Abstract database operations from business logic, providing a clean interface for data access.

**Responsibilities:**

- Execute database queries and transactions
- Convert between database models and domain objects
- Handle database errors and exceptions
- Manage database sessions

**Key Methods:**

#### `create_memory()`

```python
@staticmethod
async def create_memory(memory_data: MemoryCreate) -> ConversationMemory:
    """Create a new memory entry in the database."""
```

**Parameters:**

- `memory_data` (MemoryCreate) - Validated memory creation data

**Returns:**

- `ConversationMemory` - Database model with generated ID

**Raises:**

- `MemoryStorageError` - If database operation fails

**Example:**

```python
from backend.services.memory import MemoryRepository
from backend.services.memory.schemas import MemoryCreate

memory_data = MemoryCreate(
    agent_id="agent-123",
    agent_name="Bot",
    memory_type="conversation",
    content="Hello world",
)

memory = await MemoryRepository.create_memory(memory_data)
```

#### `get_memories()`

```python
@staticmethod
async def get_memories(
    agent_id: str,
    memory_types: Optional[list[str]] = None,
    limit: int = 10,
    only_active: bool = True,
    graph_execution_id: Optional[str] = None,
) -> list[ConversationMemory]:
    """Retrieve memories for an agent."""
```

**Parameters:**

- Same as `MemoryManager.get_agent_memories()`

**Returns:**

- `list[ConversationMemory]` - Database model instances

**Raises:**

- `MemoryRetrievalError` - If query fails

#### `update_memory_access()`

```python
@staticmethod
async def update_memory_access(memory_ids: list[str]) -> None:
    """Update access count and timestamp for memories."""
```

**Parameters:**

- `memory_ids` (list[str]) - List of memory IDs to update

**Behaviour:**

- Increments access_count by 1
- Updates last_accessed timestamp

#### `get_or_create_agent_profile()`

```python
@staticmethod
async def get_or_create_agent_profile(
    agent_id: str,
    agent_name: str,
    graph_id: str
) -> AgentMemoryProfile:
    """Get or create an agent memory profile."""
```

#### `update_agent_statistics()`

```python
@staticmethod
async def update_agent_statistics(
    agent_id: str,
    increment_conversations: bool = False,
    increment_messages: int = 0,
) -> None:
    """Update agent interaction statistics."""
```

#### `update_importance_scores()`

```python
@staticmethod
async def update_importance_scores(
    memory_ids: list[str],
    new_score: float
) -> None:
    """Update importance scores for multiple memories."""
```

#### `deactivate_old_memories()`

```python
@staticmethod
async def deactivate_old_memories(
    agent_id: str,
    retention_days: int
) -> int:
    """Soft delete old memories based on retention policy."""
```

#### `delete_agent_memories()`

```python
@staticmethod
async def delete_agent_memories(
    agent_id: str,
    graph_execution_id: Optional[str] = None
) -> int:
    """Permanently delete memories for an agent."""
```

#### `get_memory_statistics()`

```python
@staticmethod
async def get_memory_statistics(agent_id: str) -> dict:
    """Get statistics about an agent's memories."""
```

**Returns:**

- `dict` - Statistics including total_memories, active_memories, memory_by_type, average_importance

### `MemoryFormatter`

Formatter for memory data providing utilities to format memories into context strings.

**Purpose:** Transform raw memory data into formats suitable for LLM prompts and user interfaces.

**Responsibilities:**

- Format memory collections into context strings
- Parse JSON memory content
- Structure conversation history
- Extract content from various formats

**Key Methods:**

#### `format_memory_context()`

```python
@staticmethod
def format_memory_context(memories: list[dict[str, Any]]) -> str:
    """Format memories into a context string for the agent."""
```

**Parameters:**

- `memories` (list[dict]) - List of memory dictionaries

**Returns:**

- `str` - Formatted context with sections for summaries, facts, and conversations

**Example:**

```python
from backend.services.memory import MemoryFormatter

memories = [
    {"memory_type": "fact", "content": "User prefers Python"},
    {"memory_type": "conversation", "content": '{"role": "user", "content": "Hello"}'},
]

context = MemoryFormatter.format_memory_context(memories)
print(context)
# Output:
# Remembered Facts:
# - User prefers Python
#
# Recent Conversation History:
# User: Hello
```

**Behaviour:**

- Groups memories by type
- Limits output (3 summaries, 5 facts, all conversations)
- Formats each type appropriately
- Returns chronological conversation history

#### `format_conversation_history()`

```python
@staticmethod
def format_conversation_history(
    memories: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Format conversation memories into structured history."""
```

**Parameters:**

- `memories` (list[dict]) - Conversation memory dictionaries

**Returns:**

- `list[dict]` - Structured history entries with timestamp, type, content, role

**Example:**

```python
memories = [
    {
        "content": '{"role": "user", "content": "Hi"}',
        "created_at": datetime.now(),
    }
]

history = MemoryFormatter.format_conversation_history(memories)
# Returns: [{"timestamp": "...", "type": "message", "content": "Hi", "role": "user"}]
```

#### `create_conversation_content()`

```python
@staticmethod
def create_conversation_content(
    message_type: str,
    content: str,
    role: str
) -> str:
    """Create properly formatted conversation content."""
```

**Parameters:**

- `message_type` (str) - Type of message (user_message, agent_response)
- `content` (str) - Message content
- `role` (str) - Role (user, assistant)

**Returns:**

- `str` - JSON-formatted content string

**Example:**

```python
content = MemoryFormatter.create_conversation_content(
    message_type="user_message",
    content="Hello",
    role="user",
)
# Returns: '{"type": "user_message", "content": "Hello", "role": "user"}'
```

#### `extract_content_from_memory()`

```python
@staticmethod
def extract_content_from_memory(memory_content: str) -> str:
    """Extract plain text content from memory."""
```

**Parameters:**

- `memory_content` (str) - Memory content (JSON or plain text)

**Returns:**

- `str` - Plain text content

**Example:**

```python
json_content = '{"content": "Hello", "role": "user"}'
text = MemoryFormatter.extract_content_from_memory(json_content)
# Returns: "Hello"

plain_text = "Plain message"
text = MemoryFormatter.extract_content_from_memory(plain_text)
# Returns: "Plain message"
```

### `MemoryStatistics`

Manager for memory statistics providing methods to track agent interactions.

**Purpose:** Track and manage agent interaction metrics for analytics and monitoring.

**Responsibilities:**

- Track conversation counts
- Track message counts
- Aggregate memory statistics
- Update agent profiles with usage data

**Initialisation:**

```python
def __init__(self, repository: MemoryRepository):
    """Initialise statistics manager with repository."""
```

**Key Methods:**

#### `increment_conversation_count()`

```python
async def increment_conversation_count(self, agent_id: str) -> None:
    """Increment conversation count for an agent."""
```

#### `increment_message_count()`

```python
async def increment_message_count(
    self,
    agent_id: str,
    message_count: int = 1
) -> None:
    """Increment message count for an agent."""
```

#### `record_conversation_turn()`

```python
async def record_conversation_turn(
    self,
    agent_id: str,
    message_count: int = 2
) -> None:
    """Record a complete conversation turn."""
```

#### `get_agent_statistics()`

```python
async def get_agent_statistics(self, agent_id: str) -> dict:
    """Get comprehensive statistics for an agent."""
```

**Returns:**

- `dict` - Statistics with total_memories, active_memories, memory_by_type, average_importance

**Example:**

```python
from backend.services.memory import get_memory_manager

manager = get_memory_manager()
stats = await manager.statistics.get_agent_statistics("agent-123")

print(f"Total memories: {stats['total_memories']}")
print(f"Active memories: {stats['active_memories']}")
print(f"Average importance: {stats['average_importance']}")
```

### `MemoryPruning`

Manager for memory pruning and cleanup operations.

**Purpose:** Manage memory lifecycle through retention policies and cleanup operations.

**Responsibilities:**

- Prune old memories based on age
- Clear agent memories selectively
- Enforce retention policies
- Manage memory limits (planned)

**Initialisation:**

```python
def __init__(self, repository: MemoryRepository):
    """Initialise pruning manager with repository."""
```

**Key Methods:**

#### `prune_old_memories()`

```python
async def prune_old_memories(
    self,
    agent_id: str,
    retention_days: int = 30
) -> int:
    """Prune old memories based on retention policy."""
```

**Behaviour:**

- Soft-deletes conversation memories older than retention_days
- Only affects memories with importance_score < 0.5
- Preserves important memories regardless of age

#### `clear_agent_memories()`

```python
async def clear_agent_memories(
    self,
    agent_id: str,
    graph_execution_id: Optional[str] = None
) -> int:
    """Clear all memories for an agent."""
```

**Behaviour:**

- Permanently deletes memories from database
- Can filter by execution ID

#### `cleanup_expired_memories()`

```python
async def cleanup_expired_memories(self) -> int:
    """Clean up expired memories across all agents."""
```

**Note:** Currently a placeholder. Expired memories are filtered during retrieval.

#### `enforce_memory_limits()`

```python
async def enforce_memory_limits(
    self,
    agent_id: str,
    max_memories: int = 1000
) -> int:
    """Enforce memory limits for an agent."""
```

**Note:** Currently a placeholder for future implementation.

## Functions

### `get_memory_manager()`

Get the singleton memory manager instance.

**Signature:**

```python
def get_memory_manager() -> MemoryManager:
    """Get the singleton memory manager instance."""
```

**Returns:**

- `MemoryManager` - Singleton instance

**Example:**

```python
from backend.services.memory import get_memory_manager

# Get manager instance
manager = get_memory_manager()

# Use manager
memory = await manager.create_memory(
    agent_id="agent-123",
    agent_name="Bot",
    memory_type="conversation",
    content="Hello",
)
```

**Use Cases:**

- Access memory service from anywhere in the application
- Ensure consistent instance across modules
- Simplify dependency management

### `reset_memory_manager()`

Reset the singleton memory manager instance.

**Signature:**

```python
def reset_memory_manager() -> None:
    """Reset the singleton memory manager instance."""
```

**Returns:**

- None

**Example:**

```python
from backend.services.memory import reset_memory_manager

# Reset for testing
reset_memory_manager()

# Next call to get_memory_manager() will create new instance
```

**Use Cases:**

- Reset state between tests
- Reinitialise after configuration changes
- Clean up in test teardown

## Configuration

### Configuration Classes

The service uses database models for configuration stored in `AgentMemoryProfile`:

```python
class AgentMemoryProfile:
    """Agent memory profile configuration."""

    agent_id: str
    agent_name: str
    graph_id: str
    memory_window_size: int = 10
    summarization_threshold: int = 20
    memory_retention_days: int = 30
    total_conversations: int = 0
    total_messages: int = 0
    last_interaction: Optional[datetime] = None
    personality_traits: Optional[dict] = None
    knowledge_base: Optional[dict] = None
    interaction_patterns: Optional[dict] = None
```

**Fields:**

- `memory_window_size` - Number of conversation turns to keep in context (default: 10)
- `summarization_threshold` - Number of messages before summarisation (default: 20)
- `memory_retention_days` - Days to retain old memories (default: 30)
- `total_conversations` - Counter for total conversation sessions
- `total_messages` - Counter for total messages processed
- `last_interaction` - Timestamp of last interaction
- `personality_traits` - Optional JSON data for agent personality (future use)
- `knowledge_base` - Optional JSON data for agent knowledge (future use)
- `interaction_patterns` - Optional JSON data for analytics (future use)

### Memory Types

Valid memory types:

- `conversation` - User messages and agent responses
- `summary` - Condensed summaries of conversations
- `fact` - Important facts extracted from conversations
- `instruction` - Agent-specific instructions or preferences

### Importance Scores

Memory importance scores range from 0.0 to 1.0:

- `0.0-0.3` - Low importance (candidates for early pruning)
- `0.4-0.6` - Medium importance (default: 0.5)
- `0.7-0.9` - High importance (preserved longer)
- `1.0` - Critical importance (never pruned)

### Environment Variables

None directly used. Database configuration is handled by the database service.

### Initialisation Patterns

**Basic Initialisation:**

```python
from backend.services.memory import get_memory_manager

manager = get_memory_manager()
```

**Usage in API Routes:**

```python
from fastapi import Depends
from backend.services.memory import get_memory_manager

async def my_route(
    manager: MemoryManager = Depends(get_memory_manager)
):
    memories = await manager.get_agent_memories("agent-123")
    return memories
```

**Usage in Agent Execution:**

```python
from backend.services.memory import get_memory_manager

class AgentExecutor:
    def __init__(self):
        self.memory_manager = get_memory_manager()

    async def execute_with_memory(self, agent_id: str, message: str):
        # Load memory context
        memories = await self.memory_manager.get_agent_memories(agent_id)
        context = await self.memory_manager.format_memory_context(memories)

        # Execute agent with context
        response = await self.execute_agent(message, context)

        # Store conversation
        await self.memory_manager.store_conversation_turn(
            agent_id=agent_id,
            agent_name="Agent",
            user_message=message,
            agent_response=response,
        )

        return response
```

## Error Handling

### Exception Hierarchy

```
Exception
└── MemoryError (base exception for all memory errors)
    ├── MemoryNotFoundError (specific memory entry not found)
    ├── AgentProfileNotFoundError (agent profile not found)
    ├── InvalidMemoryTypeError (invalid memory type specified)
    ├── MemoryStorageError (storage/creation failed)
    ├── MemoryRetrievalError (retrieval/query failed)
    ├── MemoryDeletionError (deletion/pruning failed)
    └── InvalidImportanceScoreError (invalid importance score)
```

### Exception Details

#### `MemoryError`

Base exception for all memory-related errors.

**Inherits from:** `Exception`

**When raised:**

- Never raised directly, only subclasses are raised

**Example:**

```python
from backend.services.memory import MemoryError

try:
    await manager.create_memory(...)
except MemoryError as e:
    # Catches all memory-related errors
    logger.error(f"Memory operation failed: {e}")
```

#### `MemoryNotFoundError`

Raised when a requested memory entry cannot be found.

**Inherits from:** `MemoryError`

**When raised:**

- Attempting to access a memory with non-existent ID
- Querying for a deleted memory

**Example:**

```python
from backend.services.memory import MemoryNotFoundError

try:
    memory = await repository.get_memory_by_id("invalid-id")
except MemoryNotFoundError as e:
    print(f"Memory not found: {e.memory_id}")
```

#### `AgentProfileNotFoundError`

Raised when an agent profile cannot be found.

**Inherits from:** `MemoryError`

**When raised:**

- Attempting to update profile for non-existent agent
- Querying profile that hasn't been created

**Example:**

```python
from backend.services.memory import AgentProfileNotFoundError

try:
    profile = await repository.get_agent_profile("invalid-agent")
except AgentProfileNotFoundError as e:
    print(f"Agent profile not found: {e.agent_id}")
```

#### `InvalidMemoryTypeError`

Raised when an invalid memory type is specified.

**Inherits from:** `MemoryError`

**When raised:**

- Providing memory type not in ["conversation", "summary", "fact", "instruction"]

**Example:**

```python
from backend.services.memory import InvalidMemoryTypeError

try:
    memory = await manager.create_memory(
        agent_id="agent-123",
        agent_name="Bot",
        memory_type="invalid_type",  # Will raise error
        content="Test",
    )
except InvalidMemoryTypeError as e:
    print(f"Invalid type: {e.memory_type}")
    print(f"Valid types: {e.valid_types}")
```

#### `MemoryStorageError`

Raised when memory cannot be stored in the database.

**Inherits from:** `MemoryError`

**When raised:**

- Database connection failure during creation
- Validation failure in database model
- Transaction rollback during storage

**Example:**

```python
from backend.services.memory import MemoryStorageError

try:
    memory = await manager.create_memory(...)
except MemoryStorageError as e:
    logger.error(f"Failed to store memory: {e}")
    # Retry or return error to user
```

#### `MemoryRetrievalError`

Raised when memory retrieval fails.

**Inherits from:** `MemoryError`

**When raised:**

- Database connection failure during query
- Query timeout
- Invalid query parameters

#### `MemoryDeletionError`

Raised when memory deletion fails.

**Inherits from:** `MemoryError`

**When raised:**

- Database connection failure during deletion
- Transaction failure during pruning
- Insufficient permissions (if applicable)

#### `InvalidImportanceScoreError`

Raised when an invalid importance score is provided.

**Inherits from:** `MemoryError`

**When raised:**

- Importance score < 0.0 or > 1.0

**Example:**

```python
from backend.services.memory import InvalidImportanceScoreError

try:
    memory = await manager.create_memory(
        agent_id="agent-123",
        agent_name="Bot",
        memory_type="conversation",
        content="Test",
        importance_score=1.5,  # Invalid!
    )
except InvalidImportanceScoreError as e:
    print(f"Invalid score: {e.score}")
```

### Error Handling Patterns

```python
from backend.services.memory import (
    get_memory_manager,
    MemoryError,
    MemoryStorageError,
    MemoryRetrievalError,
    InvalidMemoryTypeError,
)

async def safe_memory_operation():
    """Example of comprehensive error handling."""
    manager = get_memory_manager()

    try:
        # Create memory
        memory = await manager.create_memory(
            agent_id="agent-123",
            agent_name="Bot",
            memory_type="conversation",
            content="Hello world",
        )

        # Retrieve memories
        memories = await manager.get_agent_memories(
            agent_id="agent-123",
            limit=10,
        )

        return {"success": True, "memories": memories}

    except InvalidMemoryTypeError as e:
        # Handle validation errors
        logger.error(f"Invalid memory type: {e}")
        return {"success": False, "error": "invalid_type"}

    except MemoryStorageError as e:
        # Handle storage failures (may be transient)
        logger.error(f"Storage failed: {e}")
        # Could retry here
        return {"success": False, "error": "storage_failed"}

    except MemoryRetrievalError as e:
        # Handle retrieval failures
        logger.error(f"Retrieval failed: {e}")
        return {"success": False, "error": "retrieval_failed"}

    except MemoryError as e:
        # Catch-all for other memory errors
        logger.error(f"Memory operation failed: {e}")
        return {"success": False, "error": "memory_error"}

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise
```

## Integration Patterns

### Integration with API Layer

The memory service integrates with FastAPI routes through dependency injection:

```python
# From backend/api/memory/routes.py
from fastapi import APIRouter, Depends, HTTPException
from backend.services.memory import get_memory_manager, MemoryManager

router = APIRouter(prefix="/api/memory", tags=["memory"])

@router.post("/memories")
async def create_memory(
    request: MemoryCreateRequest,
    manager: MemoryManager = Depends(get_memory_manager),
):
    """Create a new memory entry via API."""
    try:
        memory = await manager.create_memory(
            agent_id=request.agent_id,
            agent_name=request.agent_name,
            memory_type=request.memory_type,
            content=request.content,
            importance_score=request.importance_score,
        )
        return MemoryResponse.from_orm(memory)
    except MemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/agents/{agent_id}/memories")
async def get_memories(
    agent_id: str,
    manager: MemoryManager = Depends(get_memory_manager),
    limit: int = 10,
):
    """Retrieve memories for an agent via API."""
    memories = await manager.get_agent_memories(
        agent_id=agent_id,
        limit=limit,
    )
    return memories
```

### Integration with Execution Service

The memory service integrates with agent execution through a memory handler:

```python
# From backend/services/execution/agent/memory_handler.py
from backend.services.memory import get_memory_manager
from backend.models.workflow import EnhancedNodeData

class MemoryHandler:
    """Handles memory operations for agent execution."""

    @staticmethod
    async def load_memory_context(
        agent_node: EnhancedNodeData,
        db_execution_id: Optional[str] = None,
    ) -> str:
        """Load memory context for an agent before execution."""
        if not agent_node.agent_config.memory_enabled:
            return ""

        manager = get_memory_manager()

        # Get agent profile
        profile = await manager.get_or_create_agent_profile(
            agent_id=agent_node.uniq_id,
            agent_name=agent_node.name,
            graph_id="subagent_execution",
        )

        # Get recent memories
        memories = await manager.get_agent_memories(
            agent_id=agent_node.uniq_id,
            limit=profile["memory_window_size"] * 2,
            graph_execution_id=db_execution_id,
        )

        # Format for agent prompt
        return await manager.format_memory_context(memories)

    @staticmethod
    async def store_memory(
        agent_node: EnhancedNodeData,
        user_message: str,
        agent_response: str,
        db_execution_id: Optional[str] = None,
    ) -> None:
        """Store conversation after agent execution."""
        if not agent_node.agent_config.memory_enabled:
            return

        manager = get_memory_manager()

        await manager.store_conversation_turn(
            agent_id=agent_node.uniq_id,
            agent_name=agent_node.name,
            user_message=user_message,
            agent_response=agent_response,
            graph_execution_id=db_execution_id,
        )
```

### Integration with Other Services

**Database Service:**

```python
from backend.services.database import get_db
from backend.models import ConversationMemory

# Repository uses database service for sessions
with get_db() as db:
    memory = db.query(ConversationMemory).filter(...).first()
```

**Config Service:**

```python
from backend.services.config import get_logger

logger = get_logger("memory_manager")
logger.info("Memory operation completed")
```

### Dependency Flow

```
API Layer (FastAPI routes)
    ↓
Memory Service (MemoryManager)
    ↓
Repository Layer (MemoryRepository)
    ↓
Database Service (SQLAlchemy sessions)
    ↓
Database Models (ConversationMemory, AgentMemoryProfile)
```

**What services this module depends on:**

- `backend.services.database` - Database session management
- `backend.services.config` - Logging configuration
- `backend.models.memory` - Database models

**What services depend on this module:**

- `backend.api.memory` - REST API endpoints
- `backend.services.execution.agent.memory_handler` - Agent execution
- `backend.services.execution.async_agent.memory_handler` - Async agent execution
- `backend.services.nodes.executors.agent` - Node executor for agents

### Common Integration Patterns

#### Pattern 1: Memory-Enabled Agent Execution

```python
from backend.services.memory import get_memory_manager
from backend.services.llm import execute_llm_call

async def execute_agent_with_memory(
    agent_id: str,
    agent_name: str,
    user_message: str,
    execution_id: str,
) -> str:
    """Execute agent with memory context."""
    manager = get_memory_manager()

    # Step 1: Load memory context
    memories = await manager.get_agent_memories(
        agent_id=agent_id,
        graph_execution_id=execution_id,
        limit=10,
    )
    memory_context = await manager.format_memory_context(memories)

    # Step 2: Build prompt with context
    prompt = f"""
    You are {agent_name}.

    {memory_context}

    User: {user_message}
    Assistant:
    """

    # Step 3: Execute LLM call
    response = await execute_llm_call(prompt)

    # Step 4: Store conversation
    await manager.store_conversation_turn(
        agent_id=agent_id,
        agent_name=agent_name,
        user_message=user_message,
        agent_response=response,
        graph_execution_id=execution_id,
    )

    return response
```

#### Pattern 2: Memory Maintenance Background Task

```python
from backend.services.memory import get_memory_manager
import asyncio

async def maintain_agent_memories():
    """Background task for memory maintenance."""
    manager = get_memory_manager()

    # Get all active agents (from agent service)
    active_agents = await get_active_agents()

    for agent in active_agents:
        # Get agent profile for retention settings
        profile = await manager.get_or_create_agent_profile(
            agent_id=agent.id,
            agent_name=agent.name,
            graph_id=agent.graph_id,
        )

        # Prune old memories
        pruned = await manager.prune_old_memories(
            agent_id=agent.id,
            retention_days=profile["memory_retention_days"],
        )

        if pruned > 0:
            logger.info(f"Pruned {pruned} memories for agent {agent.name}")

        # Check if summarisation needed
        stats = await manager.statistics.get_agent_statistics(agent.id)
        if stats["active_memories"] > profile["summarization_threshold"]:
            # Trigger summarisation
            await summarize_agent_memories(agent.id, manager)
```

#### Pattern 3: Multi-Agent Memory Sharing

```python
async def share_fact_between_agents(
    fact: str,
    source_agent_id: str,
    target_agent_ids: list[str],
    execution_id: str,
) -> None:
    """Share a fact from one agent to multiple agents."""
    manager = get_memory_manager()

    # Store fact for each target agent
    for agent_id in target_agent_ids:
        await manager.create_memory(
            agent_id=agent_id,
            agent_name=f"Agent-{agent_id}",
            memory_type="fact",
            content=f"Learned from {source_agent_id}: {fact}",
            graph_execution_id=execution_id,
            importance_score=0.8,  # High importance for shared facts
        )
```

## Usage Examples

### Example 1: Basic Usage

Complete end-to-end example of basic memory operations:

```python
from backend.services.memory import get_memory_manager

async def basic_memory_example():
    """Basic memory operations example."""

    # Step 1: Get manager instance
    manager = get_memory_manager()

    # Step 2: Create agent profile
    profile = await manager.get_or_create_agent_profile(
        agent_id="support-bot-1",
        agent_name="Customer Support Bot",
        graph_id="customer-service-graph",
    )
    print(f"Agent profile created: {profile['agent_id']}")

    # Step 3: Store a conversation turn
    await manager.store_conversation_turn(
        agent_id="support-bot-1",
        agent_name="Customer Support Bot",
        user_message="What are your business hours?",
        agent_response="We are open Monday-Friday, 9 AM to 5 PM EST.",
        graph_execution_id="exec-001",
    )
    print("Conversation stored")

    # Step 4: Retrieve memories
    memories = await manager.get_agent_memories(
        agent_id="support-bot-1",
        limit=10,
    )
    print(f"Retrieved {len(memories)} memories")

    # Step 5: Format for context
    context = await manager.format_memory_context(memories)
    print(f"Memory context:\n{context}")

# Run example
import asyncio
asyncio.run(basic_memory_example())
```

### Example 2: Advanced Usage with Memory Strategies

Complete example showing memory strategies and filtering:

```python
from backend.services.memory import get_memory_manager
from typing import Literal

async def advanced_memory_example(
    agent_id: str,
    strategy: Literal["global", "thread_scoped"],
    execution_id: str,
):
    """Advanced memory usage with strategies."""
    manager = get_memory_manager()

    # Create agent profile with custom settings
    profile = await manager.get_or_create_agent_profile(
        agent_id=agent_id,
        agent_name="Advanced Bot",
        graph_id="advanced-graph",
    )

    # Store fact (global memory - no execution filter)
    await manager.create_memory(
        agent_id=agent_id,
        agent_name="Advanced Bot",
        memory_type="fact",
        content="User prefers detailed technical explanations",
        importance_score=0.9,
    )

    # Store conversation (thread-scoped memory)
    await manager.store_conversation_turn(
        agent_id=agent_id,
        agent_name="Advanced Bot",
        user_message="Explain quantum computing",
        agent_response="Quantum computing uses quantum bits...",
        graph_execution_id=execution_id,
    )

    # Retrieve memories based on strategy
    if strategy == "thread_scoped":
        # Only get memories from current execution
        memories = await manager.get_agent_memories(
            agent_id=agent_id,
            graph_execution_id=execution_id,
            limit=20,
        )
    else:
        # Get all memories (global strategy)
        memories = await manager.get_agent_memories(
            agent_id=agent_id,
            limit=20,
        )

    # Separate by type
    facts = [m for m in memories if m["memory_type"] == "fact"]
    conversations = [m for m in memories if m["memory_type"] == "conversation"]

    print(f"Strategy: {strategy}")
    print(f"Facts: {len(facts)}")
    print(f"Conversations: {len(conversations)}")

    return await manager.format_memory_context(memories)
```

### Example 3: Complete Workflow with Maintenance

Show a realistic, complete workflow with memory maintenance:

```python
from backend.services.memory import (
    get_memory_manager,
    MemoryError,
    MemoryStorageError,
)
from datetime import datetime

async def complete_memory_workflow():
    """Complete workflow showing typical usage in application."""
    manager = get_memory_manager()

    agent_id = "chatbot-001"
    agent_name = "Customer Service Bot"
    execution_id = f"exec-{datetime.now().timestamp()}"

    try:
        # Step 1: Initialise agent memory
        profile = await manager.get_or_create_agent_profile(
            agent_id=agent_id,
            agent_name=agent_name,
            graph_id="customer-service",
        )
        print(f"Initialised agent: {profile['agent_name']}")

        # Step 2: Load existing context
        existing_memories = await manager.get_agent_memories(
            agent_id=agent_id,
            memory_types=["fact", "summary", "conversation"],
            limit=profile["memory_window_size"] * 2,
        )
        context = await manager.format_memory_context(existing_memories)
        print(f"Loaded context: {len(context)} characters")

        # Step 3: Simulate conversation
        conversations = [
            ("What's your return policy?", "Our return policy allows returns within 30 days."),
            ("What about refunds?", "Refunds are processed within 5-7 business days."),
            ("Do you ship internationally?", "Yes, we ship to over 100 countries worldwide."),
        ]

        for user_msg, bot_response in conversations:
            # Store each turn
            await manager.store_conversation_turn(
                agent_id=agent_id,
                agent_name=agent_name,
                user_message=user_msg,
                agent_response=bot_response,
                graph_execution_id=execution_id,
            )
            print(f"Stored: {user_msg[:30]}...")

        # Step 4: Extract and store a fact
        await manager.create_memory(
            agent_id=agent_id,
            agent_name=agent_name,
            memory_type="fact",
            content="Customer interested in international shipping and return policies",
            importance_score=0.8,
            graph_execution_id=execution_id,
        )
        print("Stored extracted fact")

        # Step 5: Check statistics
        stats = await manager.statistics.get_agent_statistics(agent_id)
        print(f"Statistics: {stats['active_memories']} active memories")
        print(f"Memory types: {stats['memory_by_type']}")

        # Step 6: Maintenance - check if summarisation needed
        if stats["active_memories"] > profile["summarization_threshold"]:
            # Get conversation memories for summarisation
            conv_memories = await manager.get_agent_memories(
                agent_id=agent_id,
                memory_types=["conversation"],
                limit=100,
            )
            memory_ids = [m["id"] for m in conv_memories[:20]]

            # Create summary
            summary = await manager.summarize_conversation(
                agent_id=agent_id,
                agent_name=agent_name,
                conversation_memory_ids=memory_ids,
                graph_execution_id=execution_id,
            )
            print(f"Created summary: {summary[:100]}...")

        # Step 7: Prune old memories
        pruned_count = await manager.prune_old_memories(
            agent_id=agent_id,
            retention_days=profile["memory_retention_days"],
        )
        print(f"Pruned {pruned_count} old memories")

        # Step 8: Get final conversation history for display
        history = await manager.get_conversation_history(
            agent_id=agent_id,
            graph_execution_id=execution_id,
            limit=10,
        )

        return {
            "success": True,
            "agent_id": agent_id,
            "memories_active": stats["active_memories"],
            "memories_pruned": pruned_count,
            "conversation_history": history,
        }

    except MemoryStorageError as e:
        print(f"Storage error: {e}")
        return {"success": False, "error": "storage_failed"}

    except MemoryError as e:
        print(f"Memory error: {e}")
        return {"success": False, "error": str(e)}
```

### Example 4: Testing Usage

Show how to use this service in tests:

```python
import pytest
from backend.services.memory import (
    get_memory_manager,
    reset_memory_manager,
    MemoryStorageError,
)

@pytest.fixture
def memory_manager():
    """Memory manager fixture."""
    reset_memory_manager()  # Ensure clean state
    manager = get_memory_manager()
    yield manager
    reset_memory_manager()  # Cleanup

@pytest.mark.asyncio
async def test_create_and_retrieve_memory(memory_manager):
    """Test basic memory creation and retrieval."""
    # Create memory
    memory = await memory_manager.create_memory(
        agent_id="test-agent",
        agent_name="Test Agent",
        memory_type="conversation",
        content="Test message",
    )

    assert memory.id is not None
    assert memory.agent_id == "test-agent"
    assert memory.content == "Test message"

    # Retrieve memories
    memories = await memory_manager.get_agent_memories(
        agent_id="test-agent",
        limit=10,
    )

    assert len(memories) == 1
    assert memories[0]["content"] == "Test message"

@pytest.mark.asyncio
async def test_memory_filtering(memory_manager):
    """Test memory filtering by type."""
    # Create different types
    await memory_manager.create_memory(
        agent_id="test-agent",
        agent_name="Test Agent",
        memory_type="conversation",
        content="Conversation",
    )

    await memory_manager.create_memory(
        agent_id="test-agent",
        agent_name="Test Agent",
        memory_type="fact",
        content="Important fact",
    )

    # Filter by type
    facts = await memory_manager.get_agent_memories(
        agent_id="test-agent",
        memory_types=["fact"],
        limit=10,
    )

    assert len(facts) == 1
    assert facts[0]["memory_type"] == "fact"

@pytest.mark.asyncio
async def test_conversation_turn_storage(memory_manager):
    """Test storing conversation turns."""
    await memory_manager.store_conversation_turn(
        agent_id="test-agent",
        agent_name="Test Agent",
        user_message="Hello",
        agent_response="Hi there!",
    )

    memories = await memory_manager.get_agent_memories(
        agent_id="test-agent",
        limit=10,
    )

    # Should create 2 memories (user + agent)
    assert len(memories) == 2

@pytest.mark.asyncio
async def test_memory_pruning(memory_manager):
    """Test memory pruning."""
    # Create some memories
    for i in range(5):
        await memory_manager.create_memory(
            agent_id="test-agent",
            agent_name="Test Agent",
            memory_type="conversation",
            content=f"Message {i}",
            importance_score=0.3,  # Low importance
        )

    # Prune with 0 day retention (prune all old ones)
    pruned = await memory_manager.prune_old_memories(
        agent_id="test-agent",
        retention_days=0,
    )

    # Note: Actual behaviour depends on timestamps
    assert pruned >= 0

@pytest.mark.asyncio
async def test_error_handling(memory_manager):
    """Test error handling."""
    with pytest.raises(Exception):  # Pydantic validation error
        await memory_manager.create_memory(
            agent_id="test-agent",
            agent_name="Test Agent",
            memory_type="invalid_type",  # Invalid type
            content="Test",
        )
```

## Performance Considerations

### Performance Characteristics

**Create Operations:**

- Complexity: O(1) - Single database insert
- I/O: Database write operation (I/O-bound)
- Memory: Minimal, single record

**Retrieve Operations:**

- Complexity: O(n) where n is limit parameter
- I/O: Database query with index lookup (I/O-bound)
- Memory: Linear with number of records retrieved

**Formatting Operations:**

- Complexity: O(n) where n is number of memories
- CPU: JSON parsing and string concatenation (CPU-bound)
- Memory: Linear with content size

**Pruning Operations:**

- Complexity: O(n) where n is old memories
- I/O: Database bulk update (I/O-bound)
- Memory: Minimal, operates in batches

**Database Indexes:**

- Index on `agent_id` for fast agent queries
- Index on `created_at` for ordering
- Index on `graph_execution_id` for filtering
- Composite index on `(agent_id, memory_type)` for filtered queries

### Optimisation Tips

#### Tip 1: Batch Memory Creation

**Problem:**

```python
# Inefficient: Multiple separate database transactions
for message in messages:
    await manager.create_memory(
        agent_id="agent-123",
        agent_name="Bot",
        memory_type="conversation",
        content=message,
    )
```

**Solution:**

```python
# Efficient: Use store_conversation_turn for pairs
await manager.store_conversation_turn(
    agent_id="agent-123",
    agent_name="Bot",
    user_message=user_msg,
    agent_response=bot_response,
)

# Or implement batch creation
async def batch_create_memories(memories: list[MemoryCreate]):
    """Custom batch creation method."""
    with get_db() as db:
        memory_objects = [
            ConversationMemory(**m.dict()) for m in memories
        ]
        db.bulk_save_objects(memory_objects)
        db.commit()
```

#### Tip 2: Limit Memory Retrieval

**Problem:**

```python
# Retrieves all memories - could be thousands
memories = await manager.get_agent_memories(
    agent_id="agent-123",
    limit=1000,  # Too many!
)
```

**Solution:**

```python
# Retrieve only what's needed for context
profile = await manager.get_or_create_agent_profile(
    agent_id="agent-123",
    agent_name="Bot",
    graph_id="graph-1",
)

# Use profile's memory window size
memories = await manager.get_agent_memories(
    agent_id="agent-123",
    limit=profile["memory_window_size"] * 2,  # e.g., 20
)
```

#### Tip 3: Cache Formatted Context

```python
from functools import lru_cache
from typing import Tuple

@lru_cache(maxsize=128)
def format_memory_context_cached(
    memory_tuple: Tuple[str, ...]
) -> str:
    """Cached memory formatting."""
    # Convert tuple back to memory list
    memories = [eval(m) for m in memory_tuple]
    formatter = MemoryFormatter()
    return formatter.format_memory_context(memories)

async def get_cached_context(agent_id: str) -> str:
    """Get memory context with caching."""
    manager = get_memory_manager()
    memories = await manager.get_agent_memories(agent_id, limit=10)

    # Convert to hashable tuple for caching
    memory_tuple = tuple(str(m) for m in memories)

    return format_memory_context_cached(memory_tuple)
```

### Async/Await Support

The memory service is fully async throughout:

```python
from backend.services.memory import get_memory_manager
import asyncio

async def async_memory_operations():
    """All operations are async."""
    manager = get_memory_manager()

    # All methods use async/await
    memory = await manager.create_memory(...)
    memories = await manager.get_agent_memories(...)
    context = await manager.format_memory_context(...)

    # Can run multiple operations concurrently
    results = await asyncio.gather(
        manager.get_agent_memories("agent-1", limit=10),
        manager.get_agent_memories("agent-2", limit=10),
        manager.get_agent_memories("agent-3", limit=10),
    )

    return results

# Sync wrapper for non-async contexts
def sync_get_memories(agent_id: str) -> list[dict]:
    """Synchronous wrapper."""
    return asyncio.run(
        get_memory_manager().get_agent_memories(agent_id)
    )
```

### Connection Pooling

Connection pooling is handled by the database service:

```python
# Database service manages connection pool
from backend.services.database import get_db

# Context manager handles connection lifecycle
with get_db() as db:
    # Connection from pool
    memories = db.query(ConversationMemory).all()
    # Connection returned to pool
```

### Batch Operations

**Batch Retrieval:**

```python
async def get_multiple_agent_memories(
    agent_ids: list[str]
) -> dict[str, list[dict]]:
    """Retrieve memories for multiple agents efficiently."""
    manager = get_memory_manager()

    # Use asyncio.gather for concurrent queries
    results = await asyncio.gather(
        *[manager.get_agent_memories(aid, limit=10) for aid in agent_ids]
    )

    return dict(zip(agent_ids, results))
```

**Batch Pruning:**

```python
async def prune_all_agents():
    """Prune memories for all agents."""
    # Get all agent IDs (from database)
    agent_ids = get_all_agent_ids()

    manager = get_memory_manager()

    # Prune concurrently with limit
    semaphore = asyncio.Semaphore(10)  # Limit concurrency

    async def prune_with_semaphore(agent_id: str):
        async with semaphore:
            return await manager.prune_old_memories(agent_id)

    results = await asyncio.gather(
        *[prune_with_semaphore(aid) for aid in agent_ids]
    )

    total_pruned = sum(results)
    print(f"Pruned {total_pruned} total memories")
```

## Testing Patterns

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock, Mock, patch
from backend.services.memory import MemoryManager
from backend.services.memory.repository import MemoryRepository

@pytest.fixture
def mock_repository():
    """Mock repository for testing."""
    repo = Mock(spec=MemoryRepository)
    repo.create_memory = AsyncMock()
    repo.get_memories = AsyncMock()
    repo.update_memory_access = AsyncMock()
    return repo

@pytest.fixture
def manager_with_mocks(mock_repository):
    """Manager with mocked dependencies."""
    manager = MemoryManager()
    manager.repository = mock_repository
    return manager

@pytest.mark.asyncio
async def test_create_memory_calls_repository(manager_with_mocks, mock_repository):
    """Test that create_memory calls repository correctly."""
    # Setup
    mock_memory = Mock()
    mock_memory.id = "mem-123"
    mock_repository.create_memory.return_value = mock_memory

    # Execute
    result = await manager_with_mocks.create_memory(
        agent_id="agent-123",
        agent_name="Bot",
        memory_type="conversation",
        content="Test",
    )

    # Verify
    assert mock_repository.create_memory.called
    assert result.id == "mem-123"

@pytest.mark.asyncio
async def test_get_memories_updates_access(manager_with_mocks, mock_repository):
    """Test that retrieving memories updates access tracking."""
    # Setup
    mock_memory = Mock()
    mock_memory.id = "mem-123"
    mock_repository.get_memories.return_value = [mock_memory]

    # Execute
    await manager_with_mocks.get_agent_memories("agent-123")

    # Verify access tracking called
    assert mock_repository.update_memory_access.called
    call_args = mock_repository.update_memory_access.call_args[1]
    assert "mem-123" in call_args["memory_ids"]
```

### Mocking Dependencies

```python
@patch('backend.services.memory.repository.get_db')
@pytest.mark.asyncio
async def test_with_mocked_database(mock_get_db):
    """Test with mocked database."""
    # Setup mock database session
    mock_db = Mock()
    mock_get_db.return_value.__enter__.return_value = mock_db

    # Setup mock query
    mock_query = Mock()
    mock_db.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []

    # Execute
    from backend.services.memory.repository import MemoryRepository
    memories = await MemoryRepository.get_memories("agent-123")

    # Verify
    assert memories == []
    assert mock_db.query.called

@pytest.fixture
def mock_formatter():
    """Mock formatter for testing."""
    with patch('backend.services.memory.manager.MemoryFormatter') as mock:
        mock.format_memory_context = Mock(return_value="formatted context")
        yield mock

@pytest.mark.asyncio
async def test_format_memory_context(mock_formatter):
    """Test memory context formatting."""
    manager = MemoryManager()

    memories = [{"content": "test"}]
    context = await manager.format_memory_context(memories)

    assert context == "formatted context"
```

### Integration Testing

```python
import pytest
from backend.services.memory import get_memory_manager, reset_memory_manager
from backend.services.database import get_db

@pytest.fixture(scope="function")
def test_db():
    """Test database fixture."""
    # Setup test database
    # ... database setup code ...
    yield
    # Teardown
    # ... database cleanup code ...

@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_memory_workflow(test_db):
    """Integration test with real database."""
    reset_memory_manager()
    manager = get_memory_manager()

    # Create profile
    profile = await manager.get_or_create_agent_profile(
        agent_id="test-agent",
        agent_name="Test Agent",
        graph_id="test-graph",
    )
    assert profile["agent_id"] == "test-agent"

    # Store conversation
    await manager.store_conversation_turn(
        agent_id="test-agent",
        agent_name="Test Agent",
        user_message="Test user message",
        agent_response="Test agent response",
    )

    # Retrieve memories
    memories = await manager.get_agent_memories("test-agent")
    assert len(memories) == 2  # User + agent messages

    # Format context
    context = await manager.format_memory_context(memories)
    assert "Test user message" in context
    assert "Test agent response" in context

    # Cleanup
    cleared = await manager.clear_agent_memory("test-agent")
    assert cleared == 2

@pytest.mark.integration
@pytest.mark.asyncio
async def test_memory_pruning_integration(test_db):
    """Integration test for pruning."""
    reset_memory_manager()
    manager = get_memory_manager()

    # Create old memories with low importance
    # ... test pruning behaviour with real database ...
```

## Best Practices

### Do's

✅ **Use the singleton pattern for manager access:**

```python
from backend.services.memory import get_memory_manager

# Good: Use singleton
manager = get_memory_manager()

# Bad: Don't instantiate directly
manager = MemoryManager()  # Avoid this
```

✅ **Always set appropriate importance scores:**

```python
# Critical information - never prune
await manager.create_memory(
    agent_id="agent-123",
    agent_name="Bot",
    memory_type="fact",
    content="User's account ID: 12345",
    importance_score=1.0,  # Critical
)

# Regular conversation - can be pruned
await manager.create_memory(
    agent_id="agent-123",
    agent_name="Bot",
    memory_type="conversation",
    content="Small talk",
    importance_score=0.3,  # Low importance
)
```

✅ **Use execution IDs for thread-scoped memory:**

```python
# For thread-scoped conversations
await manager.store_conversation_turn(
    agent_id="agent-123",
    agent_name="Bot",
    user_message="Message in this thread",
    agent_response="Response",
    graph_execution_id=execution_id,  # Important for filtering
)

# Later, retrieve only this thread's memories
memories = await manager.get_agent_memories(
    agent_id="agent-123",
    graph_execution_id=execution_id,
)
```

✅ **Handle errors gracefully:**

```python
from backend.services.memory import MemoryError

try:
    await manager.create_memory(...)
except MemoryError as e:
    logger.error(f"Memory operation failed: {e}")
    # Provide fallback behaviour
    return default_response()
```

✅ **Use batch operations where possible:**

```python
# Good: Store complete conversation turn (2 memories in one call)
await manager.store_conversation_turn(
    agent_id="agent-123",
    agent_name="Bot",
    user_message="Question",
    agent_response="Answer",
)

# Less efficient: Store separately
await manager.create_memory(...)  # User message
await manager.create_memory(...)  # Agent response
```

✅ **Implement regular maintenance:**

```python
# Schedule periodic pruning
async def maintain_memories():
    """Background task for memory maintenance."""
    manager = get_memory_manager()

    for agent_id in active_agents:
        # Prune old memories
        await manager.prune_old_memories(agent_id, retention_days=30)

        # Check for summarisation needs
        stats = await manager.statistics.get_agent_statistics(agent_id)
        if stats["active_memories"] > 100:
            # Trigger summarisation
            await summarize_old_conversations(agent_id)
```

### Don'ts

❌ **Don't store sensitive data without encryption:**

```python
# Bad: Storing sensitive data directly
await manager.create_memory(
    agent_id="agent-123",
    agent_name="Bot",
    memory_type="fact",
    content="User's credit card: 1234-5678-9012-3456",  # Never do this!
)

# Good: Store reference or encrypted data
await manager.create_memory(
    agent_id="agent-123",
    agent_name="Bot",
    memory_type="fact",
    content="User has payment method on file",  # Reference only
)
```

❌ **Don't retrieve excessive memories:**

```python
# Bad: Retrieving too many memories
memories = await manager.get_agent_memories(
    agent_id="agent-123",
    limit=1000,  # Way too many for context!
)

# Good: Use reasonable limits
memories = await manager.get_agent_memories(
    agent_id="agent-123",
    limit=10,  # Reasonable for LLM context
)
```

❌ **Don't forget to filter by execution ID for thread-scoped agents:**

```python
# Bad: Getting all memories when agent is thread-scoped
memories = await manager.get_agent_memories(
    agent_id="thread-scoped-agent",
    # Missing graph_execution_id filter!
)

# Good: Filter by execution for thread-scoped
memories = await manager.get_agent_memories(
    agent_id="thread-scoped-agent",
    graph_execution_id=current_execution_id,
)
```

❌ **Don't ignore memory statistics:**

```python
# Bad: Creating memories indefinitely without monitoring
while True:
    await manager.create_memory(...)  # Could grow unbounded

# Good: Monitor and maintain
stats = await manager.statistics.get_agent_statistics(agent_id)
if stats["active_memories"] > 1000:
    await manager.prune_old_memories(agent_id)
```

❌ **Don't block async operations:**

```python
# Bad: Blocking async code
import asyncio
memory = asyncio.run(manager.create_memory(...))  # Don't run in async context

# Good: Use await
memory = await manager.create_memory(...)
```

## Related Documentation

### Related Services

- [Database Service](./database.md) - Database connection management and migrations
- [Execution Service](./execution.md) - Workflow and agent execution orchestration
- [Agent Service](./agent.md) - Agent compilation and configuration

### Related API Modules

- [Memory API](../agents-guide/api/memory.md) - REST API endpoints for memory management
- [Graph API](../agents-guide/api/graph.md) - Graph execution endpoints that use memory

### Architecture Documentation

- Database Models - `backend/models/memory/` for ConversationMemory and AgentMemoryProfile models
- Service Architecture - Overview of service layer patterns

### External Documentation

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/) - ORM used for database operations
- [Pydantic Documentation](https://docs.pydantic.dev/) - Data validation library

## Summary

The memory service is a comprehensive, modular system for managing agent memories in the AgenticStudio platform. It provides
type-safe, async operations for storing, retrieving, formatting, and maintaining conversation history and agent
knowledge. The service follows clean architecture principles with clear separation between repository (data access),
manager (business logic), formatter (presentation), statistics (analytics), and pruning (lifecycle) concerns.

The service integrates seamlessly with the execution layer to provide memory context for agent prompts and stores
conversation outcomes for future reference. It supports both global memory (shared across all executions) and
thread-scoped memory (isolated per execution), enabling flexible memory strategies based on agent requirements.

**Key Features:**

- Async/await support throughout for high performance
- Type-safe operations with Pydantic schemas
- Flexible memory types (conversation, summary, fact, instruction)
- Configurable retention policies and importance scoring
- Automatic memory pruning and lifecycle management
- Memory formatting optimised for LLM context injection
- Comprehensive statistics and usage tracking
- Thread-scoped and global memory strategies
- Integration with FastAPI for REST API access

**Primary Use Cases:**

- Maintaining conversation context for chatbot agents
- Storing and retrieving agent-specific knowledge
- Managing long-term memory with pruning and summarisation
- Tracking agent interaction patterns and usage statistics
- Providing memory context for LLM prompts
- Supporting multi-turn conversations with history

**When to Use This Service:**

- Building agents that need to remember past conversations
- Implementing chatbots with persistent context
- Creating agents with long-term knowledge retention
- Tracking agent usage and interaction patterns
- Building multi-agent systems with shared knowledge
- Implementing conversation summarisation and compression
