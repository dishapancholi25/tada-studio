# Agentic Studio - Repository Guidelines

## Project Overview

Agentic Studio is an AI workflow builder that combines LangGraph, FastAPI, and Next.js to create, visualize, and execute complex AI agent workflows.

**Key Capabilities:**

- Visual workflow graph editor with drag-and-drop nodes
- Multi-agent orchestration with delegation patterns
- Real-time execution streaming via WebSocket
- Document processing with vector search (RAG)
- Phoenix observability and evaluation tracing (OTel auto-instrumentation, span annotations, trace deep-links)
- LangSmith tracing integration (legacy/optional)
- Checkpoint-based pause/resume execution

---

## Architecture Overview

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | FastAPI + LangGraph | API server, workflow execution engine |
| **Frontend** | Next.js 15 + React 19 | Visual workflow editor, execution viewer |
| **Database** | PostgreSQL + pgvector | Workflows, executions, embeddings |
| **Real-time** | WebSocket | Streaming execution updates |
| **Observability** | Phoenix (OTel) + Custom Trace Viewer | LLM trace exploration, span annotations, evaluation deep-links; custom trace viewer for node-level execution |

**Python Version:** 3.11+
**Node Version:** 18+

---

## Directory Structure

```
/
├── backend/                      # FastAPI + LangGraph backend
│   ├── app.py                    # FastAPI application entry point
│   ├── config_service.py         # Configuration & logging setup
│   ├── api/                      # 25+ API route modules
│   │   ├── graph/                # Main workflow API (CRUD, execution)
│   │   ├── execution/            # Execution management
│   │   ├── auth/                 # Authentication
│   │   ├── documents/            # Document management
│   │   ├── datasources/          # Data source connections
│   │   ├── memory/               # Conversation memory
│   │   ├── websocket/            # WebSocket streaming
│   │   └── ...                   # 18+ more modules
│   ├── services/                 # 38+ business logic services
│   │   ├── graph/                # Graph building & management
│   │   ├── execution/            # Execution engine
│   │   ├── nodes/                # Node executors
│   │   ├── dependency_injection/ # DI container
│   │   ├── database/             # Database connections
│   │   ├── document/             # Document processing
│   │   ├── phoenix/              # Phoenix OTel instrumentation, evaluators, dataset sync
│   │   └── ...                   # More services
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── base.py               # Base mixins (UUID, timestamps)
│   │   ├── workflows/            # Workflow, GraphDefinition
│   │   ├── execution/            # GraphExecution, NodeExecution
│   │   └── documents/            # Document, DocumentChunk
│   ├── tools/                    # Built-in tool implementations
│   └── tests/                    # pytest test suite
├── frontend/                     # Next.js application
│   ├── src/
│   │   ├── app/                  # App Router pages
│   │   ├── components/           # React components
│   │   │   ├── nodes/            # Workflow node components
│   │   │   ├── panels/           # Configuration panels
│   │   │   ├── ui/               # Base UI components
│   │   │   └── ...
│   │   ├── contexts/             # React contexts (auth, graph, theme)
│   │   ├── hooks/                # Custom React hooks
│   │   └── services/             # API client services
│   ├── biome.json                # BiomeJS config
│   └── eslint.config.mjs         # ESLint config
├── docs/                         # Documentation
│   ├── architecture/             # Architecture decisions
│   └── for-agents/               # AI assistant guidance
├── workspace/                    # Local graph storage (gitignored)
└── pyproject.toml                # Python dependencies + Ruff config
```

---

## LangGraph Patterns

### Graph Building Pipeline

```
GraphData (JSON definition)
    ↓
GraphBuilder.build()
    ├── Analyze nodes (count types)
    ├── Create StateGraph(WorkflowState)
    ├── Find START/END nodes
    ├── Add nodes (filter subworkflow internals)
    ├── Set entry point
    └── Add edges via EdgeBuilder
    ↓
StateGraph (LangGraph object)
    ↓
compile(checkpointer=PostgresCheckpointer)
    ↓
Compiled App (executable)
```

**Key Files:**

- `backend/services/graph/builder.py` - Graph construction
- `backend/services/graph/edge_builder.py` - Edge/connection logic
- `backend/services/graph/compilation.py` - Compilation with tool binding

### Node Types

| Type | Purpose | Executor Location |
|------|---------|-------------------|
| `START` | Workflow entry point | Built-in |
| `END` | Workflow exit point | Built-in |
| `AGENT` | LLM reasoning node | `services/nodes/agent/` |
| `CONDITION` | Branching/routing | `services/conditions/` |
| `DATABASE_QUERY` | Query database | `tools/database_query/` |
| `HTTP_REQUEST` | HTTP API calls | `tools/http_request/` |
| `DOCUMENT_SEARCH` | Vector search (RAG) | `tools/document_search/` |
| `WEB_SEARCH` | Web search | `tools/web_search/` |
| `MCP_SERVER` | Model Context Protocol | `tools/mcp_server_tool.py` |
| `SUBWORKFLOW` | Nested workflow | `services/subgraph/` |
| `EMAIL_SEND` | Send emails | `tools/email_send/` |

### WorkflowState Schema

Located in `backend/services/workflow/state/schemas.py`:

```python
class WorkflowState(TypedDict):
    # Messages with LangGraph's add_messages reducer
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Node execution tracking
    node_outputs: Annotated[Dict[str, NodeOutput], merge_node_outputs]
    results: Annotated[List[NodeResult], merge_results]

    # Execution context
    current_node: Annotated[Optional[str], last_value_reducer]
    execution_id: str
    execution_order: Annotated[int, max_execution_order]

    # Metadata
    metadata: Annotated[WorkflowMetadata, merge_metadata]
    memory_context: Optional[MemoryContext]
    orchestration_context: Optional[OrchestrationContext]
```

### Execution Lifecycle (6 Phases)

Implemented in `backend/services/execution/workflow_executor.py`:

1. **Initialize Context** - Create DB execution record, setup `active_executions` tracking
2. **Process START Node** - Handle initial input, create history record
3. **Build & Compile Graph** - Construct StateGraph, compile with checkpointer
4. **Execute Streaming** - Main execution loop via `astream()`, emit WebSocket events
5. **Handle Control** - Process pause/stop requests, handle interrupts
6. **Finalize Execution** - Process END node, mark complete, cleanup

### Node Executor Registry

Strategy pattern for node execution in `backend/services/nodes/`:

```python
# Registration (in ExecutionEngine.__init__)
NodeExecutorRegistry.register(
    NodeType.AGENT,
    factory=lambda: AgentNodeExecutor(dependencies)
)

# Execution
executor = NodeExecutorRegistry.get_executor(node.type)
result = await executor.execute(node, state, graph, execution_id)
```

**Executor Interface:**

```python
async def execute(
    node: EnhancedNodeData,
    state: WorkflowState,
    graph: GraphData,
    execution_id: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]
```

---

## API Patterns

### Route Organization

Each API module follows this structure:

```
backend/api/graph/
├── routes.py           # Thin HTTP handlers (@router decorators)
├── models.py           # Pydantic request/response models
├── exceptions.py       # HTTP exception classes
├── dependencies.py     # FastAPI Depends functions
└── handlers/           # Business logic functions
    ├── graph_crud.py   # Create, read, update, delete graphs
    ├── node_crud.py    # Node operations
    ├── execution.py    # Graph execution
    ├── connection_crud.py
    └── ...
```

### Handler Pattern

Routes are thin HTTP handlers that delegate to handler functions:

```python
# routes.py - HTTP concerns only
@router.get("/list")
async def list_graphs(current_user: Dict = Depends(get_current_user)):
    return await graph_crud.handle_list_graphs(current_user)

# handlers/graph_crud.py - Business logic
async def handle_list_graphs(current_user: Dict) -> Dict[str, Any]:
    user_id = get_user_identifier(current_user)
    graphs = get_graph_manager().list_graphs(user_id)
    return {"success": True, "graphs": graphs}
```

### Dependency Injection

Centralized in `backend/services/dependency_injection/`:

```python
from backend.services.dependency_injection import (
    get_graph_manager,
    get_execution_engine,
    get_execution_history_service,
)

# Direct access
graph_mgr = get_graph_manager()

# FastAPI injection
@router.get("/example")
async def example(engine: ExecutionEngine = Depends(get_execution_engine)):
    pass
```

### Service Layer

| Service | Purpose | Location |
|---------|---------|----------|
| `GraphManager` | Graph lifecycle (CRUD) | `services/graph/manager.py` |
| `ExecutionEngine` | Execution coordination | `services/execution/engine.py` |
| `WorkflowExecutor` | 6-phase execution | `services/execution/workflow_executor.py` |
| `NodeExecutorRegistry` | Node executor lookup | `services/nodes/registry.py` |
| `GraphStorageService` | Database persistence | `services/graph/storage.py` |
| `ExecutionHistoryService` | Execution tracking | `services/execution/history.py` |

### Error Handling

Exception hierarchy in `backend/api/*/exceptions.py`:

```python
class GraphAPIException(HTTPException):  # Base
    pass

class GraphNotFoundError(GraphAPIException):      # 404
class GraphAlreadyExistsError(GraphAPIException): # 400
class UnauthorizedError(GraphAPIException):       # 401
class ForbiddenError(GraphAPIException):          # 403
class ExecutionError(GraphAPIException):          # 500
```

**Standard Response Format:**

```python
# Success
{"success": True, "message": "...", "data": {...}}

# Error (via HTTPException)
{"detail": "Error message"}
```

---

## Code Quality Tools

### Python - Ruff

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "C4", "UP"]
```

**Commands:**

```bash
ruff check backend/              # Lint check
ruff check backend/ --fix        # Auto-fix issues
ruff format backend/             # Format code
```

### Frontend - BiomeJS + ESLint

**BiomeJS** (`frontend/biome.json`):

- Tab indentation, width 2
- Recommended lint rules
- Covers: `.ts`, `.tsx`, `.js`, `.jsx`, `.json`

**ESLint** (`frontend/eslint.config.mjs`):

- Extends: `next/core-web-vitals`, `next/typescript`
- Warnings: `no-explicit-any`, `no-unused-vars`, `exhaustive-deps`

**Commands:**

```bash
cd frontend
npm run lint                  # ESLint check
npm run lint:fix              # Auto-fix
npm run type-check            # TypeScript validation
npx biome check .             # Biome check
npx biome check . --write     # Biome auto-fix
```

---

## Testing

### Backend

**Framework:** pytest with pytest-asyncio

```bash
pytest backend/tests/                    # Run all tests
pytest backend/tests/ -v                 # Verbose output
pytest backend/tests/ --cov=backend      # With coverage
pytest backend/tests/api/                # Specific module
```

**Test Location:** `backend/tests/` organized by module

### Frontend

**Framework:** Jest with React Testing Library

```bash
cd frontend
npm test                     # Run tests
npm test -- --coverage       # With coverage
```

**Test Pattern:** `*.test.ts`, `*.test.tsx`

---

## Build & Development Commands

### Backend

```bash
# Development (with auto-reload)
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
cd frontend
npm run dev                  # Dev server on :3000 (Turbopack)
npm run build                # Production build
npm run start                # Start production server
npm run type-check           # Verify TypeScript types
```

### Docker

```bash
docker-compose up                    # Run full stack
docker-compose up --build            # Rebuild and run
docker-compose up -d                 # Detached mode
docker-compose logs -f backend       # View backend logs
```

---

## Coding Conventions

### Python

- **Indentation:** 4 spaces
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes
- **Type hints:** Required on public functions
- **Async:** Use `async/await` for I/O operations
- **Models:** Pydantic for API contracts, SQLAlchemy for database
- **Imports:** Group by stdlib, third-party, local (enforced by Ruff isort)

### TypeScript/React

- **Indentation:** Tabs (BiomeJS)
- **Components:** `PascalCase` (e.g., `NodePanel.tsx`)
- **Hooks:** `camelCase` with `use` prefix (e.g., `useGraphHistory`)
- **Props:** Export interfaces separately
- **Styling:** Tailwind CSS classes (no inline styles)
- **State:** React Context API + custom hooks

### Patterns to Follow

- Keep routes thin, business logic in handlers/services
- Use dependency injection for shared resources
- Prefer async/await over callbacks
- Handle errors explicitly with typed exceptions
- Write tests for new features

### Required Checks Before Completing Frontend Changes

When making any frontend changes, always run these checks before considering the work complete:

```bash
cd frontend
npm run type-check            # TypeScript validation (must pass)
npm run lint                  # ESLint check (must pass)
npm test                      # Jest tests (must pass)
```

All three must pass. Fix any failures before finalizing changes.

---

## Security Guidelines

- **Secrets:** Load via environment variables (`.env` file)
- **Configuration:** Access through `backend/config_service.py`
- **Never commit:** `.env` files, API keys, credentials
- **Workspace exports:** Scrub before sharing (may contain credentials)
- **Database:** Use parameterized queries (SQLAlchemy handles this)
- **Input validation:** Validate at API boundaries (Pydantic models)
- **Authentication:** OAuth2-Proxy with JWT tokens

---

## Key Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Architecture Overview | `docs/architecture/00-overview.md` | System design |
| Design Principles | `docs/architecture/03-design-principles.md` | Patterns & practices |
| Agent Guidance | `docs/for-agents/AGENTS.md` | AI assistant guide |
| Graph Service | `backend/services/graph/AGENTS.md` | Graph building (88KB) |
| Execution Service | `backend/services/execution/AGENTS.md` | Execution engine |
| DI Container | `backend/services/dependency_injection/AGENTS.md` | Dependency injection |
| Streaming | `docs/for-agents/STREAMING.md` | WebSocket streaming |
| Subgraphs | `docs/for-agents/SUBGRAPHS.md` | Nested workflows |
| Phoenix ADR | `docs/architecture/phoenix-integration.md` | Architecture decision, dual-feed diagram |
| Phoenix Agent Guide | `docs/for-agents/PHOENIX.md` | File map, pitfalls, debugging |
| Phoenix Runbook | `docs/operations/phoenix-runbook.md` | Local setup, troubleshooting, deployment |

---

## Quick Reference

### Common Tasks

| Task | Command |
|------|---------|
| Start backend | `uvicorn backend.app:app --reload` |
| Start frontend | `cd frontend && npm run dev` |
| Run backend tests | `pytest backend/tests/ -v` |
| **Run frontend tests** | `cd frontend && npm test` |
| Lint Python | `ruff check backend/ --fix` |
| Lint frontend | `cd frontend && npm run lint:fix` |
| Type check frontend | `cd frontend && npm run type-check` |
| Format Python | `ruff format backend/` |

### Key Entry Points

| Purpose | File |
|---------|------|
| FastAPI app | `backend/app.py` |
| Graph API routes | `backend/api/graph/routes.py` |
| Execution engine | `backend/services/execution/engine.py` |
| Graph builder | `backend/services/graph/builder.py` |
| Workflow state | `backend/services/workflow/state/schemas.py` |
| Frontend pages | `frontend/src/app/` |
| Graph components | `frontend/src/components/core/` |
