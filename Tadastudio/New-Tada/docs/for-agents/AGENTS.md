# Documentation for Agents

## Summaries of Implemented Features

- Summaries of implemented features should be added to `docs/for-agents/implementation-summaries`

## API Documentation

- API documentation should be generated using the prompt in `CREATING_API_DOCUMENTATION.md`
- API documentation should be added to the directory for the respective api in `backend/api`

## Service Documentation

- Service documentation should be generated using the prompt in `CREATING_SERVICE_DOCUMENTATION.md`
- Service documentation should be added to the directory for the respective service in `backend/services`

## Release and Deployment

- Full instructions for releasing and deploying new versions are in `docs/for-agents/RELEASE_AND_DEPLOYMENT.md`
- Covers: kubectl contexts, namespaces, deployments, image tags, rolling restarts, image updates, and rollbacks

## Project Structure & Module Organization

### Phoenix Observability

`backend/services/phoenix/` contains the Phoenix OTel integration:

- `config.py` — configuration, runtime DB settings, URL helpers
- `instrumentation.py` — OTel bootstrap, `GatedSpanProcessor`, `ProjectRoutingSpanProcessor` registration
- `tracing.py` — per-workflow context manager, root span capture
- `annotations.py` — post-execution span annotations
- `project_routing.py` — ContextVar-based concurrency-safe project routing
- `evaluators.py` — supplementary faithfulness/tool-selection/LLM judge evaluators
- `dataset_sync.py` — experiment mirroring

`backend/services/evaluation/phoenix_adapter.py` handles span correlation and annotation.
Phoenix documentation lives in `docs/for-agents/PHOENIX.md`,
`docs/architecture/06-phoenix-integration.md`, and `docs/operations/phoenix-runbook.md`.
Docker Compose includes a `phoenix` service for local observability on port 6006.

### Langfuse Observability

`backend/services/langfuse/` contains the Langfuse SDK integration:

- `config.py` — `LangfuseConfig` dataclass, `get_langfuse_config()`, `get_langfuse_env_config()`, runtime DB settings fallback
- `instrumentation.py` — `initialize_langfuse_instrumentation()` (idempotent, non-fatal), native Langfuse SDK client setup, OpenInference LangChain + OpenAI auto-instrumentation, `shutdown_langfuse()`, `reset_openinference_instrumentation()`
- `tracing.py` — `build_langfuse_trace_ref()` for deep-link generation using `client.get_trace_url()`

Key design points:

- **Non-fatal** — all Langfuse operations are wrapped in try/except; missing packages or bad config are logged and swallowed
- **Runtime toggle** — settings read from `system_settings` DB table first, falling back to env vars; can be enabled/disabled via Settings UI without restart
- **Coexists with Phoenix** — both observability backends can run simultaneously; both receive spans from the same OpenInference instrumentors
- **Native SDK** — uses the Langfuse Python SDK (`langfuse` package) which configures OTel export automatically
- Called from `backend/app.py` lifespan after Phoenix initialization
- `backend/config_api.py` exposes Langfuse config to the frontend settings UI
- `backend/services/execution/workflow_executor.py` captures trace IDs for deep-linking

### Azure OpenAI PTU Provider

`backend/services/llm_models/providers/azure_openai_ptu.py` implements the gateway-fronted Azure OpenAI provider:

- `NonStreamingAzureChatOpenAI` — AzureChatOpenAI variant that degrades `astream` to non-streaming (gateway limitation)
- `AzureOpenAIPTUProvider` — extends `AzureOpenAIProvider` with OAuth2 token management, custom headers, and TLS config
- Process-wide token cache with thread-safe refresh (keyed by `(token_url, client_id)`)
- Registered as `azure_openai_ptu` in the LLM factory provider registry

Configuration is per model-deployment (stored in DB, configured via Settings → LLM Providers).

### Real-Time Collaboration

`backend/api/collaboration/` provides WebSocket-based real-time collaborative editing:

- `routes.py` — WebSocket endpoint `/api/collab/{room_name}`, connection management, auth gating
- Uses `pycrdt-websocket` for Yjs CRDT synchronization
- `frontend/src/hooks/useCollaboration.ts` — React hook managing Yjs + y-websocket

`backend/api/notifications/` provides access request notifications:

- `routes.py` — WebSocket endpoint `/api/notifications/ws`, REST endpoints for access request management
- `manager.py` — in-memory notification delivery

See `backend/api/collaboration/README.md` for architecture details.

### LLM-Safe File Content References

`backend/services/file_content_references.py` provides a runtime reference system for large file content:

- **Purpose:** FILE_READ nodes expose a compact token (`{{file_content_ref:<hex>}}`) to LLM-facing prompts instead of injecting the entire raw file payload (which would blow context windows or confuse the model).
- `register_file_content_reference(content, execution_id, node_id, metadata)` → returns compact token string
- `resolve_file_content_references(value)` → recursively resolves tokens inside strings, lists, and dicts back to original content
- `get_file_content_reference_metadata(value)` → retrieve metadata for a token
- `clear_file_content_references(execution_id)` → cleanup after execution
- References are stored in-memory with a 2-hour TTL (`REFERENCE_TTL_SECONDS = 7200`)
- Maximum 256 references stored at once (`MAX_REFERENCES = 256`)
- Token format: `{{file_content_ref:<32-char hex>}}`
- Pattern: `REFERENCE_TOKEN_PATTERN = r"\{\{file_content_ref:([a-f0-9]{32})\}\}"`

**Integration points:**
- `backend/services/nodes/executors/file.py` — registers references when `llm_safe_mode` is enabled on FILE_READ config
- `backend/services/delegation/factories/sync_factory.py` — resolves references before passing content to tools
- `backend/tools/http_request/handlers.py` — resolves references in HTTP request bodies
- `frontend/src/components/nodes/FileReadNode.tsx` — UI shows LLM-safe mode toggle
- `frontend/src/components/panels/properties/sections/ExtractionSection.tsx` — configuration panel

### Document Storage Enhancements

**Page Boundary Tracking** (`backend/services/document_storage/chunking/page_tracker.py`):

- Assigns a **dominant page** to each chunk based on which page contributes the most text
- Adds `page_range` metadata (e.g., `"pages 3-4"`) for chunks spanning multiple pages
- Embeds page boundary markers (`[Page N]`) directly within chunk text to improve citation accuracy for agents using the document search tool
- Chunk metadata includes: `page` (dominant), `page_start`, `page_end`, `page_range`

**Azure Blob Storage References** (`backend/services/document_storage/service.py`):

- Documents uploaded to Azure Blob Storage get a `blob_url` stored in metadata
- Document search results include `file_url` for direct download links
- `_resolve_document_file_url()` in `backend/api/http_execution/utils/output.py` resolves download URLs in execution output with priority: explicit `file_url` > `/api/documents/{id}/download` > `source_location`
- Dependency: `azure-storage-blob` package (`backend/pyproject.toml`)
- `backend/api/documents/router.py` includes download endpoint and blob URL generation

**HTTP Execution Output Metadata** (`backend/api/http_execution/utils/output.py`):

- Execution output from document search results now includes structured reference metadata
- Parses JSON document results with `content`, `metadata`, `file_url`, `page`, `page_range`
- Returns enriched output for external consumers (CI/CD, webhooks) with citation sources

### File Read Node

`backend/services/nodes/executors/file.py` — `FileNodeExecutor` handles FILE_READ nodes:

- **Input formats:** file path, base64-encoded content, or raw text content
- **OCR processing:** Uses GPT-4o vision API for PDFs, images (PNG/JPG), DOCX, XLSX, PPTX
- **Direct text extraction:** For TXT, MD, CSV, JSON, XML, HTML files
- **LLM-safe mode:** When enabled (`file_read_config.llm_safe = True`), registers file content as a compact reference token instead of injecting raw content into the LLM prompt
- **Config model:** `backend/models/workflow/configs/file.py` — includes `llm_safe` boolean field
- **Frontend:** `frontend/src/components/nodes/FileReadNode.tsx`, `FileReadPropertiesPanel.tsx`
- **Connection type:** FILE_READ is a valid tool target in `connection_manager.py` (`VALID_TOOL_TARGET_TYPES`)
- **Execution panel:** File upload supported directly from the execution input section (`ExecutionFileUpload.tsx`)
- **Multiple file upload:** Supports uploading and processing multiple files in a single execution

### Chat Features

`frontend/src/app/chat/` and `backend/api/chat/` provide the conversational chat interface:

- **Chat sessions** — persistent conversations tied to published workflows
- **PDF attachments** — `frontend/src/components/chat/ChatPdfAttachment.tsx` renders uploaded PDF previews inline
- **Suggestion chips** — `frontend/src/components/chat/SuggestionChips.tsx` shows AI-generated follow-up suggestions parsed from `<<<SUGGESTIONS>>>` blocks in responses
- **Canvas Chat Panel** — `frontend/src/components/panels/execution/CanvasChatPanel.tsx` provides in-canvas chat during workflow execution
- **Streaming responses** — `frontend/src/components/chat/StreamingAssistantMessage.tsx` renders token-by-token LLM responses
- **Document ingestion from chat** — `backend/api/chat/handlers/message.py` processes chat-uploaded files, extracts content, and forwards to the workflow as structured input

### UI/UX (Mashreq/TADA Design System)

Major UI overhaul applied across the application (PR 138 + related commits):

- **Design system colors:** Primary orange `#FF5E00`, light theme throughout
- **Collapsible sidebar:** Hamburger icon, tooltips shown only when collapsed
- **Redesigned modals:** Create Workflow, Add Tool Node, Library dialogs
- **Keyboard shortcuts:** Cross-platform (Mac/Win/Linux) with `?` to open help dialog
  - `frontend/src/components/dialogs/KeyboardShortcutsDialog.tsx`
  - `frontend/src/hooks/useAccessibility.ts` — `useKeyboardShortcuts`, `useEscapeKey`, `useFocusTrap`
- **Responsive layouts:** Max-width 2xl, standardised padding, sticky table headers
- **Custom favicon:** `frontend/public/` updated with TADA Studio branding
- **ConfirmDialog component:** Replaced all `window.confirm()` calls with styled modal
- **Tooltip component:** Reusable portal-based tooltip (`frontend/src/components/ui/Tooltip.tsx`)
- **Notification improvements:** Line breaks, pause-on-hover (`frontend/src/components/ui/Notification.tsx`)

### CI/CD (Azure Pipelines)

- `azure-pipelines-backend.yml` — Backend Docker image build pipeline
- `azure-pipelines-frontend.yml` — Frontend Docker image build pipeline
- Triggered on pushes to `dev` branch
- Builds Docker images using existing Dockerfiles
- Runner: Azure DevOps hosted agents

### Backend Tools (`backend/tools/`)

Complete tool inventory with file locations:

| Tool | Location | Description |
|------|----------|-------------|
| **Database Query** | `backend/tools/database_query/` | Execute SQL queries against configured datasources |
| **Document Search** | `backend/tools/document_search/` | Semantic/hybrid search over document collections (RAG) |
| **Document Retrieve** | `backend/tools/document_retrieve/` | Retrieve full document content by ID |
| **Web Search** | `backend/tools/web_search/` | Search the web via Tavily API |
| **HTTP Request** | `backend/tools/http_request/` | Make HTTP API calls with dynamic parameters |
| **Email Send** | `backend/tools/email_send/` | Send emails via configured provider |
| **File Write** | `backend/tools/file_write/` | Write content to files |
| **File Read/Write Tools** | `backend/tools/file_tools.py` | `FileReadTool` and `FileWriteTool` — safe file system ops with path validation, extension filtering, and size limits |
| **Connected Node Tool** | `backend/tools/connected_node_tool.py` | `ConnectedNodeTool` — lets one node invoke another node as a tool (node composition) |
| **MCP Server Tool** | `backend/tools/mcp_server_tool.py` | Connect to Model Context Protocol servers (stdio) |
| **MCP Adapter** | `backend/tools/mcp_adapter_tool.py` | MCP via `langchain-mcp-adapters` with HTTP bridge fallback, execution tracking, bridge cache |
| **MCP HTTP Tools** | `backend/tools/mcp_http_tools.py` | Load tools from HTTP-based MCP servers |
| **MCP Native Tools** | `backend/tools/mcp_native_tools.py` | Load tools via native `langchain-mcp-adapters` SDK |
| **MCP Config Utils** | `backend/tools/mcp_config_utils.py` | Prepare MCP configs for execution (inject node metadata, resolve env vars) |
| **MCP Presets** | `backend/tools/mcp_presets.py` | Auth preset helpers for MCP server configurations |
| **SharePoint MCP** | `backend/tools/sharepoint_mcp/` | SharePoint MCP connector |
| **OneDrive MCP** | `backend/tools/onedrive_mcp/` | OneDrive MCP connector |
| **Fabric MCP** | `backend/tools/fabric_mcp/` | Fabric MCP connector |
| **Databricks DevOps MCP** | `backend/tools/databricks_devops_mcp/` | Databricks DevOps MCP connector |

### Backend Services (Additional)

Services not covered in Phoenix/Langfuse/PTU/Collaboration sections:

| Service | Location | Description |
|---------|----------|-------------|
| **Database Query Service** | `backend/services/database_query_service.py` | Simplified interface wrapping `DataSourceService` for the database query tool (row limits, timeouts) |
| **Managed Identity Service** | `backend/services/managed_identity_service.py` | Cloud managed-identity token generation (AWS/Azure) for MCP server auth without static credentials |
| **Mock Embeddings** | `backend/services/mock_embeddings.py` | Fallback embeddings implementation returning zero vectors when no embedding service is configured (dev/test) |
| **File Content References** | `backend/services/file_content_references.py` | LLM-safe compact tokens for large file content (see section above) |
| **MCP Client Manager** | `backend/mcp_client_manager.py` | Global singleton managing MCP client connections and lifecycle |

## Flow Driven Development

- Label-based issue triage that controls how Claude Code responds to issues
- Full instructions and label definitions are in `docs/for-agents/FLOW_DRIVEN_DEVELOPMENT.md`
- Labels: `green` (trivial, auto-merge), `blue` (non-trivial, PR for review), `red` (complex, plan only), `black` (very complex, analysis comments only)
