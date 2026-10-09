# Chat UI Feature - Design & Questions Document

## Context

This document captures the design decisions, open questions, and proposed architecture
for a new **Chat UI** feature. The goal is to allow users to interact with published
workflows through a conversational interface — send a message, trigger a full workflow
execution, and receive the result as a chat response. Real-time streaming shows execution
progress, and an optional side panel provides deeper execution details per message.

This is a **design-phase document** — no code changes yet. The intent is to enumerate
every design decision, propose approaches for each, and align on direction before
implementation begins.

---

## 1. Chat Model & Persistence

### Q1 - What is a "chat" and how is it persisted

**Why it matters:** Everything depends on whether a chat is a first-class DB entity or
a virtual grouping of executions.

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **A: New `ChatSession` + `ChatMessage` tables** | Dedicated models for sessions and messages | Clean relationships, supports metadata, easy to query | New migration, new tables, data duplication with execution input/output |
| **B: Virtual chats (shared ID on `GraphExecution`)** | Add `chat_session_id` to `GraphExecution`; a "chat" = all executions with that ID | Minimal schema changes, no duplication | Metadata needs to go somewhere; querying requires aggregation |
| **C: Thin `ChatSession` + FK on `GraphExecution`** | Session stores metadata; executions linked via FK; messages from I/O | Best of both — metadata on session, content on execution, no duplication | Messages without an execution can't exist |

**Suggested: C.** A thin `ChatSession` model gives chat-level metadata and organization,
while actual message content stays on `GraphExecution` where it already lives.

Proposed `ChatSession` model:

```
ChatSession:
  id              UUID PK
  user_id         String (FK)
  workflow_id     String (FK to workflows)
  title           String (auto-generated from first message, user-editable)
  last_message_at DateTime (for sorting)
  is_archived     Boolean (soft archive)
  created_at / updated_at (from TimestampMixin)
```

`GraphExecution` gets a new nullable column: `chat_session_id` (FK to `ChatSession`)
plus a new `trigger_type` value: `"chat"`.

### Q2 - Multiple chats per workflow

**Suggested: Yes, unlimited.** Standard pattern (ChatGPT, Claude). Users want separate
conversations for different topics. "New Chat" button creates a new `ChatSession`.

### Q3 - Chat naming/organization

| Approach | Description |
|----------|-------------|
| A: Auto-title from first message (truncated ~60 chars) | Simple, good default |
| B: LLM-generated title after first exchange | Better quality, adds latency and cost |
| C: Manual naming only | Low overhead, bad UX for many chats |

**Suggested: A with manual rename.** Use first ~60 characters of first user message.
Allow renaming via inline edit. LLM-generated titles can be a future enhancement.

### Q4 - Chat history, how far back, pagination

**Suggested:** Load the most recent 50 messages on page load, with "Load more" /
infinite scroll upward. API:
`GET /api/chat/sessions/{id}/messages?limit=50&before=<cursor>`. Since messages are
derived from `GraphExecution` records, this is a paginated query on
`graph_executions WHERE chat_session_id = X ORDER BY created_at DESC`.

---

## 2. Execution & Response

### Q5 - What constitutes the "response" to a chat message

**Why it matters:** The END node's `output_data` can be complex JSON (`full`, `summary`,
`compact`, `custom` formats per `EndNodeConfig` in
`backend/models/workflow/configs/end_node.py`). Raw JSON in a chat bubble is poor UX.

Current output pipeline:

- `OutputProcessor.process()` builds output per EndNodeConfig
- `FinalOutputExtractor.extract()` gets last `AIMessage` content or last node output
  `raw` text
- `extract_execution_output()` extracts END node output for HTTP responses

| Approach | Description |
|----------|-------------|
| A: Use `FinalOutputExtractor` — last AI message content as plain string | Chat-friendly, but loses multi-node outputs |
| B: Use END node `output_data` as-is, render on frontend | Preserves full structure, but complex to display |
| C: New "chat response" extraction mode with smart fallbacks | Best of both: try to get a clean string, fall back gracefully |

**Suggested: C.** Add a `ChatResponseExtractor` that:

1. For `compact` output structure: extract the single response value (most chat-friendly)
2. For `full`/`summary` with multiple nodes: render as sections with node name headers
3. Fall back to `FinalOutputExtractor` (last AI message content) as a default
4. Last resort: formatted JSON code block

The END node's `output_structure` setting already tells us the author's intent.

### Q6 - Multi-output workflows (parallel agents feeding END)

**Suggested:** Render multi-node outputs as sections within a single chat bubble:

```
**Research Agent**
[research findings...]

**Summary Agent**
[summary text...]
```

This maps naturally to the `full` output structure which includes node name fields.

### Q7 - Long-running executions in chat context

**Suggested:** Show an animated "thinking" indicator with real-time streaming status:

1. Message appears immediately with a "thinking" state
2. Streaming status updates show inline: "Starting... > Agent 1 processing... >
   Calling web_search... > Agent 2 processing..."
3. Once complete, replace thinking indicator with final response
4. If user scrolls away and returns, final response is already rendered

### Q8 - Failed executions

**Suggested:** Show a user-friendly error message in the chat bubble with a "Retry"
button. Full error detail available in the execution detail panel. Message states:
`sending` → `executing` → `completed` | `failed` | `cancelled`.

### Q9 - Cancel running execution from chat

**Suggested: Yes.** Show a "Stop" button on the currently-executing message. Calls
existing `request_stop()` on the execution engine. Message shows "Execution stopped"
as the response.

---

## 3. Streaming & Real-Time

### Q10 - How to stream execution progress inline in chat

The existing `useExecutionWebSocket` hook provides granular events: `node_start`,
`node_complete`, `tool_call_start`, `tool_call_complete`, `token`, `subagent_start`, etc.

| Approach | Description |
|----------|-------------|
| A: All events inline in chat bubble | Comprehensive but messy for complex workflows |
| B: High-level summary in bubble, full detail in side panel | Clean chat, detail available on demand |
| C: Configurable detail level | Flexible but complex to build |

**Suggested: B.** In the chat bubble, show a compact "execution stepper":

```
[Thinking...]
  > Research Agent: searching...
  > Research Agent: found 3 results
  > Summary Agent: generating summary...
```

Side panel shows full node-by-node execution trace, tool call details, timing,
token counts.

### Q11 - Token streaming (word-by-word response display)

**Why it matters:** Users expect ChatGPT-style streaming where the response appears
word by word.

The existing `token` WebSocket event already provides this for LLM agents. The
challenge: we don't know which agent produces the "final" response until the workflow
completes.

| Approach | Description |
|----------|-------------|
| A: Only stream tokens from the last node before END | Requires graph analysis on frontend |
| B: Stream to side panel during execution; show final response in bubble on completion | Simple, reliable |
| C: Stream current node's tokens into bubble, replacing as workflow progresses | Real-time but potentially confusing |

**Suggested: B with optimization.** Default: stream tokens to side panel, show complete
response in bubble once done. For simple linear workflows (one agent to END), detect
this pattern and enable real-time token streaming directly in the bubble.

### Q12 - Transition from streaming status to final response

**Suggested:** State machine per message:

1. `sending` — user clicked send, waiting for execution ID
2. `executing` — execution running, showing streaming progress indicator
3. `streaming` — final response tokens arriving (for simple/linear workflows)
4. `completed` — full response displayed
5. `failed` — error state with retry button
6. `cancelled` — user cancelled

Transition from `executing` to `completed` replaces the progress indicator with the
final response using a smooth animation/fade.

---

## 4. Memory Architecture

This is the most architecturally significant section. The existing memory system is
per-agent (keyed by `agent_node.uniq_id`), with strategies for thread-scoped vs
cross-thread.

### Current memory model (key files)

- `backend/services/execution/agent/memory_handler.py` —
  `MemoryHandler.load_memory_context()` loads memories filtered by `agent_id` and
  optionally `graph_execution_id`
- `backend/models/workflow/configs/agent.py` — Per-agent config: `memory_enabled`,
  `memory_window_size`, `memory_strategy` (thread_scoped/cross_thread),
  `cross_execution_memory`
- `backend/models/memory/conversation.py` — `ConversationMemory` model linked to
  `graph_execution_id`
- `backend/services/workflow/state/schemas.py` — `MemoryContext` TypedDict in
  `WorkflowState`

### Q13 - Per-chat memory vs per-workflow memory vs per-agent memory

**The fundamental tension:** In the current system, each execution is independent. A
"chat" implies a coherent conversation — ALL messages should be visible to memory-enabled
agents, even if `memory_strategy` is `thread_scoped`.

| Approach | Description | Pros | Cons |
|----------|-------------|------|------|
| **A: Chat = new memory scope** | Add `chat_session_id` to `ConversationMemory`. Filter by session when loading. | Clean isolation per chat | Requires changes to `MemoryHandler` and memory repository |
| **B: Execution chaining** | Pass all `graph_execution_id`s from the chat when loading memory | No schema changes to memory tables | Querying by ID list is awkward, grows unbounded |
| **C: Chat history in `MemoryContext`** | Build `MemoryContext` from session's execution records. Inject into state at start. | No changes to `ConversationMemory`; clean separation; simple | Bypasses importance scoring, summarization, pruning |

**Suggested: C for Phase 1, with A as a future enhancement.**

For initial implementation:

1. When a chat message triggers an execution, build a `MemoryContext` from the chat
   session's prior messages (user input + workflow response pairs from `GraphExecution`
   records)
2. Inject this into `WorkflowState.memory_context` with `conversation_id` =
   `chat_session_id`
3. Agents with `memory_enabled` will see this context (existing agent executor already
   reads `memory_context`)
4. The per-agent `ConversationMemory` system continues independently for non-chat
   executions

### Q14 - How does chat memory interact with existing agent-level memory settings

**Suggested mapping:**

| Agent Setting | Behavior in Chat Context |
|---------------|--------------------------|
| `memory_enabled` | Must be `True` for the agent to receive chat history. If `False`, agent executes without prior context. |
| `memory_window_size` | Honored — only inject the last N message pairs from the chat |
| `memory_strategy` | In chat context, `thread_scoped` = only this session's messages. `cross_thread` could include global entries — **recommend thread-scoped within chat for simplicity** |
| `memory_persistence` | Not directly applicable — chat memory is derived from chat history, not stored in `ConversationMemory` |

### Q15 - Memory window, chat level or per-agent settings

**Suggested: Honor per-agent settings.** Each agent may have different
`memory_window_size` values. When building the `MemoryContext`, include the full chat
history up to a reasonable max (e.g., 50 pairs). Each agent's executor applies its own
window size when reading from the context.

Current `MemoryHandler.load_memory_context()` already uses `profile.memory_window_size`
as the limit. If we inject chat history into `WorkflowState.memory_context.messages`,
each agent can truncate to its own window.

### Q16 - Summarization for long chats

**Suggested: Defer to Phase 2.** For initial release, rely on `memory_window_size` to
limit context. For Phase 2:

- After N messages (e.g., 30), summarize older messages using an LLM call
- Store summary on `ChatSession.summary` column
- Inject: `[Summary of earlier conversation] + [last N messages]`
- The existing `MemoryManager.summarize_conversation()` could be enhanced for this

### Q17 - Should memory persist across chat sessions

**Suggested: Isolated by default.** Each chat session is an independent conversation.
An agent in Chat A should not see messages from Chat B. Agents with
`cross_execution_memory` enabled could still access their global `ConversationMemory`
entries from non-chat executions, but that's separate from the chat history injection.

---

## 5. Execution Detail Panel (Right Side)

### Q18 - What should the panel show

The user wants something "nicer and higher-level" than the current execution panel.

**Suggested design — per-message execution summary:**

**When no message is selected:**

- Chat session summary: total messages, total tokens used, total cost, average
  response time

**When a message is selected (clicked):**

- **Header:** execution status, total duration, total tokens, total cost
- **Timeline:** visual stepper showing nodes executed in order
  - Each step: node name, node type icon, duration, status (checkmark/X)
  - Clicking a step expands: input summary, output preview, tokens used, tools called
- **Collapsible sections:**
  - "Tools Used" — list of tool calls with name, duration, result preview
  - "Agent Activity" — for multi-agent workflows, per-agent breakdown
  - "Cost Breakdown" — per-node token and cost totals

**Key design principle:** Focus on WHAT happened (high-level), not raw JSON. Use icons,
color coding, and progressive disclosure.

### Q19 - Streaming progress in the panel

**Suggested: Yes.** During execution, the panel shows live updates (nodes appearing as
they execute). After completion, it shows the final state. The data is already available
via `useExecutionWebSocket` callbacks (`onNodeUpdate`, `onToolCallStart`, etc.).

### Q20 - Token/cost tracking per message

**Suggested: Yes.** Aggregate from `NodeExecution` records. The columns already exist:
`input_tokens`, `output_tokens`, `total_tokens`, `prompt_cost`, `completion_cost`,
`total_cost`.

---

## 6. UI/UX

### Q21 - Left sidebar, workflow selection UX

| Approach | Description |
|----------|-------------|
| A: Dropdown selector at top, chat list below | Matches mockup, clean separation |
| B: Grouped list — workflows as expandable sections, chats nested | Shows everything at once, but busy |
| C: Two-level navigation — workflow list → chat list | Extra click, cleaner |

**Suggested: A.** Searchable dropdown at top to select from published workflows the
user has access to. Below: list of chat sessions for selected workflow, sorted by
`last_message_at DESC`. Matches the mockup.

**Data source:** Existing `GET /api/publish/workflows` returns the user's published
workflows.

### Q22 - Chat list management

- **Create:** "New Chat" button creates a `ChatSession`
- **Rename:** Click on chat title to edit inline
- **Delete:** Context menu; soft-delete via `is_archived` flag
- **Search:** Text filter on chat titles (client-side for small lists)

### Q23 - Message input

| Approach | Description |
|----------|-------------|
| A: Plain text only | Simplest, matches chat paradigm |
| B: Text + file upload | For workflows with FILE_READ nodes |
| C: Dynamic form from `PublishedWorkflow.input_schema` | Rich but complex |

**Suggested: A for Phase 1, B for Phase 2.** Most workflows accept a text message.
Send on Enter, newline on Shift+Enter. Auto-resize textarea up to ~4 lines. Send button
disabled during execution.

### Q24 - Markdown rendering in responses

**Suggested: Yes.** Use existing `SimpleMarkdown` component for rendering. Supports
headings, bold, italic, code blocks with syntax highlighting, tables, lists, links.

### Q25 - Empty states

- **No published workflows:** "No workflows available. Publish a workflow to start
  chatting."
- **No chats for workflow:** "Start a new conversation with [workflow name]" + New
  Chat CTA
- **No messages in chat:** Welcome message using `PublishedWorkflow.description`

### Q26 - Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Send message |
| Shift+Enter | New line |
| Escape | Close execution panel |
| Ctrl/Cmd+N | New chat |

---

## 7. Access Control & Auth

### Q27 - Who can access the chat UI

| Approach | Description |
|----------|-------------|
| A: Any authenticated user can chat with any published workflow they have access to | Open, reuses existing publishing access model |
| B: Only workflow owners/members can chat | Restrictive |
| C: Separate "chat access" permission | Most flexible, most complex |

**Suggested: A.** Reuse the existing published workflow access model. The chat UI is
authenticated (user has a session), so authentication is handled by the session JWT.
The backend checks workflow ownership via `user_id` on the `PublishedWorkflow`.

### Q28 - PAT tokens in chat context

The chat UI is an internal-facing feature — users are already logged in. **No need for
PAT tokens.** Chat API endpoints use the session JWT (via `require_active_user`
dependency). When triggering an execution, the backend uses the session user's identity
to check workflow access.

This means chat executions need a new execution path that authenticates via session
rather than PAT. The chat handler would mirror
`HttpExecutionHandler.trigger_execution()` but replace
`http_auth_service.perform_full_security_check()` with a session-based ownership check.

---

## 8. Navigation & Routing

### Q29 - URL structure

| Approach | Description |
|----------|-------------|
| A: `/chat?workflow=<id>&session=<id>` | Flat, query params |
| B: `/chat/[workflowId]/[sessionId]` | Deep, explicit hierarchy |
| C: `/chat` → `/chat/[sessionId]` | Simple, workflow derived from session |

**Suggested: C.** `/chat` for the main page (no session selected),
`/chat/[sessionId]` for a specific chat. Workflow context derived from the
`ChatSession` record. Simple URLs, supports deep linking.

### Q30 - Navigation integration

Add "Chat" item to `NAV_ITEMS` in `UnifiedNavigationBar.tsx`:

```typescript
{ id: "chat", label: "Chat", icon: MessageSquare, route: "/chat" }
```

With feature access: `NAV_FEATURE_MAP: { chat: "nav.chat" }`.

---

## 9. Proposed Architecture (High-Level)

### Backend

**New API module:** `backend/api/chat/`

```
backend/api/chat/
  routes.py         - REST endpoints
  models.py         - Pydantic request/response models
  exceptions.py     - Chat-specific exceptions
  dependencies.py   - FastAPI dependencies
  handlers/
    session.py      - CRUD for chat sessions
    message.py      - Send message, get history, trigger execution
```

**Key endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/chat/sessions` | List sessions (filter by `workflow_id`) |
| POST | `/api/chat/sessions` | Create new session |
| GET | `/api/chat/sessions/{id}` | Get session details |
| PATCH | `/api/chat/sessions/{id}` | Rename/archive |
| DELETE | `/api/chat/sessions/{id}` | Delete session |
| GET | `/api/chat/sessions/{id}/messages` | Get message history (paginated) |
| POST | `/api/chat/sessions/{id}/messages` | Send message (triggers execution) |
| POST | `/api/chat/sessions/{id}/cancel` | Cancel running execution |

**POST `/messages` flow:**

1. Validate user access (session JWT → user_id → check workflow ownership)
2. Load `ChatSession` → get `workflow_id` → load published workflow → load graph
3. Build chat memory context from prior messages in this session
4. Submit execution via `execution_manager.submit_execution()` with
   `trigger_type="chat"`, `chat_session_id`
5. Return `{ execution_id, websocket_execution_id }` for frontend to connect streaming

**New service:** `ChatMemoryBuilder` — builds `MemoryContext` from chat session's
`GraphExecution` records (user input + output pairs), respecting per-agent
`memory_window_size`.

**WebSocket:** No changes needed. Frontend connects to existing
`/api/ws/execution/{execution_id}` endpoint.

### Frontend

**New page:** `frontend/src/app/chat/`

```
frontend/src/app/chat/
  page.tsx                    - Main chat page (empty state / no session)
  [sessionId]/
    page.tsx                  - Chat with active session
  layout.tsx                  - Shared layout with sidebar
```

**Component hierarchy:**

```
ChatPage
  ChatLayout
    ChatSidebar
      WorkflowSelector       - Dropdown to pick published workflow
      ChatSessionList         - List of sessions for selected workflow
        ChatSessionItem       - Individual session row (title, timestamp, actions)
      NewChatButton
    ChatMain
      ChatHeader              - Session title, workflow name, panel toggle button
      ChatMessages            - Scrollable message list
        ChatMessage           - Individual message bubble
          ChatMessageContent  - Rendered response (markdown)
          ChatStreamingStatus - Inline execution progress stepper
      ChatInput               - Textarea + send button
    ExecutionDetailPanel      - Right panel (toggleable)
      ExecutionSummary        - Per-message execution overview
      ExecutionTimeline       - Visual node execution stepper
      ExecutionMetrics        - Tokens, cost, duration
```

**State management:**

- React Context or Zustand store for: current session, current workflow, messages
  (with pagination), active execution ID, panel state
- Reuse `useExecutionWebSocket` hook for streaming
- New hooks: `useChatSession` (CRUD), `useChatMessages` (history + sending)

---

## 10. Data Flow

### Send Message Flow

```
User types message → hits Enter
  │
  ▼
Frontend: POST /api/chat/sessions/{sessionId}/messages { message: "..." }
  │
  ▼
Backend handler:
  1. Validate user access
  2. Load ChatSession → workflow_id → published workflow → graph
  3. ChatMemoryBuilder.build_context(session_id, window_size)
     └─ Query: GraphExecution WHERE chat_session_id=X ORDER BY created_at
     └─ Extract: (input_data.message, output_data → response text) pairs
     └─ Format as MemoryContext { conversation_id, messages }
  4. execution_manager.submit_execution(
       graph, initial_input, execution_id, user_id,
       workflow_id, trigger_type="chat"
     )
  5. Update GraphExecution with chat_session_id
  6. Return { execution_id, websocket_execution_id }
  │
  ▼
Frontend: useExecutionWebSocket(executionId)
  Streams: node_start, tool_call_start, token, node_complete, execution_complete
  │
  ▼
On execution_complete:
  1. Fetch final output from execution
  2. Extract chat-friendly response (ChatResponseExtractor)
  3. Replace "thinking" bubble with final response
  4. Populate execution detail panel
```

### Memory Flow

```
Prior chat: [M1, R1, M2, R2, M3, R3]  (M=user message, R=response)
  │
  ▼
ChatMemoryBuilder.build_context(session_id)
  → Query GraphExecution records for this session
  → Extract (input_data.message, output_data text) pairs
  → Truncate to max window
  → Return MemoryContext {
      conversation_id: session_id,
      messages: [
        {role: "user", content: M1}, {role: "assistant", content: R1},
        {role: "user", content: M2}, {role: "assistant", content: R2},
        ...
      ]
    }
  │
  ▼
Injected into initial_state["memory_context"]
  │
  ▼
Agent executor reads memory_context → prepends to system prompt or messages
(per-agent memory_window_size applied at this stage)
```

---

## 11. Risks & Considerations

### Performance

- **Many messages per chat:** Paginate messages. Only load `NodeExecution` details for
  the currently-selected message in the detail panel, not for all messages. The message
  list only needs `input_data.message` and `output_data` from `GraphExecution`.
- **Memory context growth:** 50 message pairs = potentially 50K+ tokens. Mitigated by
  `memory_window_size` (typically 10-20). Summarization in Phase 2.

### WebSocket Connection Management

- Only connect WebSocket during active execution. Disconnect after `execution_complete`.
  Reconnect for the next message. (Same pattern as the editor.)

### Concurrent Executions

- **Prevent double-send:** Disable the send button while execution is running. Show
  "Stop" to cancel before sending a new message.
- **Multiple tabs:** Each tab manages its own WebSocket. Messages loaded from DB, so
  refreshing shows latest. No cross-tab sync needed for Phase 1.

### Error Recovery

- **Backend crash mid-execution:** Frontend detects WebSocket disconnect, polls execution
  status via REST fallback. If status is `failed` or gone, show error. Existing
  `fallbackToPolling` in `useExecutionWebSocket` handles this.

### Data Consistency

- **Varied output formats:** `ChatResponseExtractor` handles all END node output
  structures with graceful fallbacks.

### Migration

- Adding nullable `chat_session_id` to `GraphExecution` is non-destructive and
  backward-compatible. Add index on `(chat_session_id, created_at)` for efficient
  queries.

---

## 12. Phasing

### Phase 1 (MVP)

- `ChatSession` model + `chat_session_id` on `GraphExecution`
- Chat API endpoints (CRUD sessions, send messages, get history)
- Chat page with sidebar (workflow selector, session list), message area, input
- Execution via existing engine with `trigger_type="chat"`
- Inline streaming status in chat bubble (high-level node progress)
- Chat memory injection via `MemoryContext` (approach C)
- Basic execution detail panel (timeline + metrics)

### Phase 2 (Enhancements)

- File upload in message input
- LLM-generated chat titles
- Token streaming in chat bubble for linear workflows
- Chat session summarization for long conversations
- Chat-scoped memory in `ConversationMemory` (approach A)
- Cross-tab synchronization
- Search across chat messages

---

## 13. Key Files for Implementation

| Purpose | File |
|---------|------|
| GraphExecution model (add `chat_session_id`) | `backend/models/execution/graph_execution.py` |
| Memory handler (integrate chat context) | `backend/services/execution/agent/memory_handler.py` |
| HTTP execution handler (reference pattern) | `backend/api/http_execution/handlers/execution.py` |
| Execution manager (submit execution) | `backend/api/graph/services/execution_manager.py` |
| Output extraction | `backend/services/io/extractors/final.py` |
| END node config | `backend/models/workflow/configs/end_node.py` |
| WebSocket hook (reuse for streaming) | `frontend/src/hooks/useExecutionWebSocket.ts` |
| Navigation bar (add Chat tab) | `frontend/src/components/layout/UnifiedNavigationBar.tsx` |
| Conversation display (reference pattern) | `frontend/src/components/panels/execution/components/ConversationHistoryTab.tsx` |
| Design system (styling reference) | `docs/for-agents/ui/DESIGN_SYSTEM.md` |
| Publishing API (list accessible workflows) | `backend/api/workflow/publishing.py` |
