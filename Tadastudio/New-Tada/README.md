# Agentic Studio

[![Ruff](https://github.com/synechron/agentic-studio/actions/workflows/ruff.yaml/badge.svg)](https://github.com/synechron/agentic-studio/actions/workflows/ruff.yaml)
[![PyTest](https://github.com/synechron/agentic-studio/actions/workflows/pytest.yaml/badge.svg)](https://github.com/synechron/agentic-studio/actions/workflows/pytest.yaml)

A drag-and-drop, no-code/low-code platform for creating and executing AI agent workflows using LangGraph and LangChain.

## Running the Project

Start with `python -m backend.app` and `frontend/npm run dev`

## Project Overview

This system enables non-programmers to create sophisticated AI workflows through a visual, drag-and-drop interface.
Users can combine AI agents, tools, and decision nodes to build complex automation workflows without writing code.

### Key Features (Planned)

- **Drag-and-drop workflow builder**
- **Pre-configured AI agents** (research, coding, general assistance)
- **Agent import from JSON** (supports approximation of A2A Agent Card format)
- **Tool integration** (web search, file processing, APIs)
- **Conditional branching** and decision nodes
- **Human-in-the-loop** capabilities
- **Memory management** (short-term and long-term)
- **Visual workflow execution** and monitoring

## Architecture Overview

### Backend Components

#### Core Data Models (`enhanced_nodedata.py`)

**Purpose**: Defines the data structures for workflow components

**Key Classes**:

- `NodeType` - Enumeration of available node types (AGENT, TOOL, CONDITION, etc.)
- `EnhancedNodeData` - Core node configuration with type-specific settings
- `ToolConfig` - Configuration for tool nodes (web search, file reader, etc.)
- `AgentConfig` - Configuration for AI agent nodes with LLM settings
- `ConditionConfig` - Configuration for decision/branching nodes
- `LLMConfig` - Language model configuration (Azure OpenAI, OpenAI, Anthropic)
- `GraphData` - Complete workflow representation

**Features**:

- Type-safe node configuration
- Validation and error checking
- Serialization to/from JSON
- Template system for common patterns

#### Graph Management (`graph_manager.py`)

**Purpose**: Creates, manages, and validates workflows

**Key Responsibilities**:

- Graph CRUD operations (create, read, update, delete)
- Node creation with templates (research agent, code assistant, etc.)
- Tool instantiation and management
- LLM configuration and validation
- Workflow validation and export
- File system persistence

**Features**:

- Pre-built agent templates
- Tool library (web search, arXiv, Wikipedia, file operations)
- LLM provider abstraction
- Automatic tool binding for agents
- Graph validation and error reporting

#### Execution Engine (`execution_engine.py`)

**Purpose**: Executes workflows using LangChain/LangGraph

**Key Features**:

- Workflow execution with state management
- Async and sync execution modes
- Execution history and logging
- Error handling and recovery
- Tool invocation and result processing

**Current Status**: Under development

#### Low-Level API (`graph_builder_api.py`)

**Purpose**: Comprehensive REST API for all system operations

**Endpoints**:

- `/api/graph/*` - Graph management
- `/api/graph/node/*` - Node operations
- `/api/graph/agent/*` - Agent chat and configuration
- `/api/graph/llm/*` - LLM provider management
- `/api/graph/execute` - Workflow execution
- `/api/graph/validate/*` - Workflow validation

**Features**:

- Full CRUD operations
- Real-time chat with agents
- Template management
- Execution monitoring
- Error handling and validation

#### Simplified API (`simplified_api.py`)

**Purpose**: Higher-level, user-friendly API for common operations

**Design Goals**:

- Simplified JSON schemas
- Common workflow patterns as single operations
- Beginner-friendly parameter names
- Automatic configuration for typical use cases

**Current Status**: Planned/Under development

## API Architecture and Testing Strategy

### API Layer Architecture

The system has a layered API architecture that builds from core functionality to user-facing endpoints:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Planned)                          │
│                 Drag-and-drop Interface                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   API Layer                                    │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │ simplified_workflow │  │    graph_builder_api.py        │  │
│  │     _api.py         │  │   (Production Endpoints)       │  │
│  │  (High-level API)   │  │                                 │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │           api_integration_bridge.py                        │  │
│  │              (Migration Layer)                             │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                 Backend Core                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │               graph_manager.py                              │  │
│  │           (Core Business Logic)                             │  │
│  │                                                             │  │
│  │  • Graph CRUD operations                                    │  │
│  │  • Node creation and management                             │  │
│  │  • Connection management                                    │  │
│  │  • LLM configuration                                        │  │
│  │  • Tool instantiation                                       │  │
│  │  • Agent chat execution                                     │  │
│  │  • File persistence                                         │  │
│  └─────────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │            enhanced_nodedata.py                             │  │
│  │              (Data Models)                                  │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### Core Components Relationship

**1. `enhanced_nodedata.py`** - Data Foundation

- Defines all data structures (`NodeType`, `GraphData`, `AgentConfig`, etc.)
- Provides validation and serialization
- Used by all other components

**2. `graph_manager.py`** - Business Logic Engine

- **Consumes**: Data models from `enhanced_nodedata.py`
- **Provides**: Core graph operations, agent creation, tool management
- **Used by**: All API layers for actual functionality
- **Key Methods**: `create_graph()`, `create_node()`, `add_connection()`, `execute_simple_chat()`

**3. `graph_builder_api.py`** - Production REST API

- **Consumes**: `graph_manager.py` methods via `shared.graph_manager`
- **Provides**: HTTP endpoints for external clients
- **Endpoints**: `/api/graph/*` for all graph operations
- **Usage**: Production frontend, external integrations

**4. `simplified_workflow_api.py`** - User-Friendly API

- **Consumes**: Same `graph_manager.py` core
- **Provides**: Higher-level, simplified operations
- **Purpose**: Easier integration for non-technical users
- **Status**: Under development

**5. `api_integration_bridge.py`** - Migration Helper

- **Purpose**: Bridge between simplified and complex APIs
- **Enables**: Gradual migration and A/B testing
- **Status**: Experimental

### Testing Strategy

The testing approach validates the system at two critical levels:

#### Backend Validation: `chat_test.py`

**Purpose**: Validates core functionality without HTTP layer

**What it tests**:

- Direct `graph_manager.py` function calls
- Agent creation and configuration
- Tool integration (DuckDuckGo, Wikipedia, ArXiv)
- LLM connectivity and chat functionality
- Graph creation with proper connections
- Complex workflow patterns (conditional, parallel)
- File persistence and loading

**Why it's important**:

- Tests the **business logic core** independent of API layer
- Faster execution (no HTTP overhead)
- Easier debugging of core functionality issues
- Validates that the foundation works before testing APIs

**Example workflows tested**:

- Connected linear workflows (Start -> Agent -> End)
- Conditional branching (Start -> Agent -> Condition -> [Math|General] -> End)
- Parallel processing (Start -> Splitter -> [Worker1, Worker2, Worker3] -> Aggregator -> End)

#### API Validation: `test_api_integration.py`

**Purpose**: Validates HTTP endpoints work correctly

**What it tests**:

- REST API endpoint responses (`/api/graph/*`)
- HTTP request/response handling
- API error handling (404s, validation errors)
- Data serialization through HTTP layer
- End-to-end workflow via API calls
- Multi-step API operations (create graph -> add nodes -> connect -> execute)

**Why it's important**:

- Ensures **API layer correctly calls** `graph_manager.py`
- Tests HTTP-specific concerns (serialization, error codes)
- Validates external client integration points
- Catches API-specific bugs (routing, parameter handling)

**Key difference from `chat_test.py`**:

- Uses HTTP requests instead of direct function calls
- Tests the **integration layer** rather than core logic
- Validates real-world usage patterns

## Testing

### Running Tests

#### Backend Core Tests: `chat_test.py`

Tests the core business logic without HTTP layer:

```bash
# Run all backend tests directly
python tests/chat_test.py

# Or with pytest (more detailed output)
pytest tests/chat_test.py -v -s

# Run specific test functions
pytest tests/chat_test.py::test_direct_langchain_agent -v -s
pytest tests/chat_test.py::test_conditional_workflow -v -s
```

**Requirements**:

- [x] Environment variables (`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`)
- [ ] No API server needed
- [ ] No HTTP requests

**Output**:

- Creates connected workflow JSON files in `workspace/default/`
- Tests agent chat with real LLMs
- Validates complex workflow patterns

#### API Integration Tests: `test_api_integration.py`

Tests the HTTP endpoints and API layer:

```bash
# 1. FIRST: Start the API server
python app.py
# Server should be running on http://localhost:8000

# 2. THEN: In another terminal, run API tests
python tests/test_api_integration.py

# Or with pytest
pytest tests/test_api_integration.py -v -s

# Run without slow tests
pytest tests/test_api_integration.py -v -s -m "not slow"
```

**Requirements**:

- [x] Environment variables for LLM tests
- [x] **API server running** on `localhost:8000`
- [x] Server accessible and responding

**Output**:

- Tests all REST endpoints (`/api/graph/*`)
- Validates HTTP request/response cycle
- Creates test graphs via API calls
- Tests error handling (404s, validation errors)

### Test Output and Debugging

Both test suites generate:

**Console Output**:

```bash
Testing Agent Tool Calling...
   Agent tools: ['web_search', 'calculator']
   Calculator tool working!
   Response: The result of 15 * 23 + 47 is 392...
   Web search tool working!
```

**Generated Files** (in `workspace/default/`):

- `connected_test_graph.json` - Linear workflow
- `conditional_workflow.json` - Branching workflow
- `parallel_workflow.json` - Parallel processing
- `test_graph_*.json` - API test artifacts

**Failure Diagnosis**:

- `chat_test.py` failures -> Core business logic issues
- `test_api_integration.py` failures -> API layer or HTTP issues

### Test Prerequisites

**Environment Setup**:

```bash
# Required for LLM functionality
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Required for credential encryption (API keys, passwords)
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
CREDENTIAL_ENCRYPTION_KEY=your_fernet_key_here

# Optional: For key rotation (when changing encryption keys)
# Set the current version number (defaults to 1)
CREDENTIAL_ENCRYPTION_KEY_VERSION=2
# Keep old keys for decryption of existing data
CREDENTIAL_ENCRYPTION_KEY_V1=old_key_here
CREDENTIAL_ENCRYPTION_KEY_V2=new_key_here  # Should match CREDENTIAL_ENCRYPTION_KEY

# Optional: Additional providers
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# RBAC Configuration
# Default role assigned to new users on first login
# Options: PENDING (requires admin approval), USER (standard access), ADMIN (full access)
# Default: USER (backward compatible)
DEFAULT_USER_ROLE=USER

# Admin user configuration (users with these emails will be automatically assigned ADMIN role)
ADMIN_USERS=admin1@example.com,admin2@example.com

# Admin group from OAuth token (users in this group will be assigned ADMIN role)
ADMIN_GROUP=admins
```

## Role-Based Authorization

The system supports three user roles:

- **PENDING**: User awaiting admin approval. Cannot access the system until approved.
- **USER**: Standard authenticated user with access to the system.
- **ADMIN**: Administrator with full system access, including user management.

### Admin User Approval Workflow

1. When `DEFAULT_USER_ROLE=PENDING`, new users are created with PENDING status
2. Admins can view all users in the Settings → Admin → Users tab
3. Click on the role badge (PENDING/USER/ADMIN) to cycle through roles
4. Users with PENDING status see a blocking panel until approved
5. The role badge cycles through: PENDING → USER → ADMIN → PENDING

### Admin Configuration

Admins can be configured in three ways:

1. **ADMIN_USERS**: Comma-separated list of admin emails (environment variable)
2. **ADMIN_GROUP**: OAuth group name for admin users (environment variable)
3. **Database role**: Manually assigned via the admin UI

Users configured via `ADMIN_USERS` or `ADMIN_GROUP` are protected and cannot have their admin status removed through the UI.

**Dependencies**:

```bash
uv sync
# Key packages: langchain, langgraph, fastapi, pytest
```

### Test Categories

#### Test Features

- Automatic environment validation
- Test graph creation and cleanup
- Agent chat testing with real LLMs
- Workflow execution testing
- Visual graph output for debugging
- Comprehensive error scenario testing

```bash
# Run all tests with verbose output
pytest -vs

# Run specific test categories
pytest -m "backend" -vs        # Backend only (no API server needed)
pytest -m "api" -vs           # API tests (requires server running)
pytest -m "not slow" -vs      # Skip slow tests

# Run with coverage
pytest --cov=backend -vs
```

### Test Output

Tests generate:

- **Success/Fail status** for each component
- **Print statements** showing test progress
- **Graph visualizations** in the `workspace/` folder
- **Coverage reports** (when using `--cov`)

This testing strategy ensures both the **core functionality** (`chat_test.py`) and **API integration** (
`test_api_integration.py`) work correctly, providing confidence in the entire system stack.
