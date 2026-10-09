# Guardrails & Policies Architecture

This document describes the guardrails and shared policy system in Agentic Studio. Guardrails provide
safety, compliance, and governance controls that intercept workflow execution at multiple points to
validate inputs, outputs, tool calls, and resource usage.

---

## Design Goals

1. **Defence in depth** - Multiple interception points (input, output, tool call, token budget, provider content filter) ensure no single bypass defeats all controls.
2. **Composable policies** - Reusable policy definitions can be shared across workflows, assigned to specific targets, and enforced at the organisation level.
3. **Layered resolution** - Policies merge from six priority layers so that admin-mandated rules cannot be weakened by individual users.
4. **Pluggable evaluation** - New guardrail types can be added by implementing an evaluator and registering it with the engine, without changing the execution pipeline.
5. **Audit-first** - Every violation is persisted and streamed in real time, even when enforcement mode is set to audit-only.
6. **Role-based access** - The guardrails page is gated by a `nav.guardrails` feature flag, controllable per-role from the admin settings.

---

## High-Level Architecture

```text
                         +----------------------------+
                         |   Guardrail Policy DB      |
                         |  (policies, assignments,   |
                         |   versions, violations,    |
                         |   feedback)                |
                         +-------------+--------------+
                                       |
                         +-------------v--------------+
                         |  LayeredPolicyResolver     |
                         |  (6-layer merge with TTL   |
                         |   cache for compulsory)    |
                         +-------------+--------------+
                                       |
                         +-------------v--------------+
                         |    GuardrailsEngine        |
                         |  (central orchestrator,    |
                         |   resolve_unified())       |
                         +-------------+--------------+
                                       |
                         +-------------v--------------+
                         |   GuardrailCheckpoint      |
                         |  (unified entry point:     |
                         |   route -> evaluate ->     |
                         |   report -> enforce)       |
                         +--+---+---+---+---+---+----+
                            |   |   |   |   |   |
               +------------+   |   |   |   |   +------------+
               v                v   |   v   v                v
        +------------+  +----------+|  +----------+  +-----------+
        |   Input    |  |  Output  ||  |ToolCall  |  |  Token    |
        | Evaluator  |  |Evaluator ||  |Evaluator |  |  Budget   |
        +------------+  +----------+|  +----------+  | Evaluator |
                                    v                +-----------+
                            +--------------+
                            |  Custom      |
                            |  Filter      |
                            |  Evaluator   |
                            +--+---+---+---+
                               |   |   |
                  +------------+   |   +------------+
                  v                v                 v
           +-----------+  +------------+  +--------------+
           |  Python   |  | LLM Judge  |  | Declarative  |
           |  Sandbox  |  |  Executor  |  |   Executor   |
           +-----------+  +------------+  +--------------+
```

The `GuardrailCheckpoint` sits between the engine and all call sites. It provides a single
`check(content, config, checkpoint_type, ctx)` method that routes to the correct evaluator,
persists and streams violations, and applies enforcement (raise on enforce, warn on audit).
The `GuardrailContext` dataclass bundles execution metadata (execution IDs, workflow ID, agent
info, user ID) so it doesn't need to be threaded through every function signature.

In addition to the evaluators above, provider-level content filter errors (Azure OpenAI, OpenAI) are
intercepted at the exception-handling layer and treated as violations when a `ProviderContentFilter`
policy is active. These use `GuardrailCheckpoint.report_prebuilt_violations()` for the same
centralised persist-and-emit flow.

---

## Core Data Models

### GuardrailResult and Violation

Every evaluator returns the same result type, making them composable via `merge()`.

```python
@dataclass
class Violation:
    category: str      # input | output | tool_call | token_budget | behavioral | custom_filter | content_filter
    rule_name: str
    severity: str      # block | warn | info
    message: str
    details: Dict[str, Any]
    timestamp: str     # ISO 8601 UTC, auto-populated

@dataclass
class GuardrailResult:
    passed: bool                          # False if any blocking violation
    violations: List[Violation]
    action_taken: str                     # none | blocked | redacted | warned | transformed
    sanitized_content: Optional[str]      # Content after redaction/transformation
    vault_id: Optional[str]              # PII anonymization vault session ID
    vault_secret: Optional[str]          # Ownership token for vault session
```

**Merge semantics:** When two results are merged, the output fails if either fails, violations are
concatenated, and the most severe action wins using the priority order:
`blocked (4) > redacted (3) > transformed (2) > warned (1) > none (0)`.
Vault fields are carried forward from whichever result has them.

**Location:** `backend/services/guardrails/models.py`

### GuardrailsConfig

The complete configuration dataclass that controls all guardrail behaviour for a given scope.

| Field | Type | Purpose |
|-------|------|---------|
| `enabled` | `bool` | Master toggle |
| `enforcement_mode` | `str` | `enforce` (block), `audit` (log only), or `disabled` |
| `inherit_from_workflow` | `bool` | Agent inherits workflow-level guardrails |
| `pattern_rules` | `List[PatternRule]` | Regex-based content matching rules |
| `tool_call_policy` | `ToolCallPolicy` | Tool-level constraints (HTTP, SQL, file) |
| `token_budget` | `TokenBudget` | Token and LLM call limits |
| `behavioral` | `BehavioralGuardrails` | Input safety: LLM Guard ML scanners + LLM-as-judge fallback |
| `output_scanners` | `OutputScanners` | LLM Guard output scanner configuration |
| `provider_content_filter` | `ProviderContentFilter` | Provider-level content filter handling (Azure/OpenAI) |
| `custom_filters` | `List[CustomFilter]` | User-defined ingress/egress filters |
| `source_policies` | `Dict` | Internal metadata mapping rules to source policy IDs |
| `rule_policy_map` | `Dict` | Internal metadata mapping individual rules to their originating policy |

**Location:** `backend/models/workflow/configs/guardrails.py`

### ProviderContentFilter

Configures how the system handles provider-level content filter errors (e.g. Azure OpenAI's
Responsible AI filters for hate speech, violence, jailbreak, etc.).

```python
@dataclass
class ProviderContentFilter:
    enabled: bool = True
    categories: List[str] = field(default_factory=list)  # empty = all categories
```

When a provider blocks a request, the system parses the structured error response to extract
which categories were triggered. If `categories` is empty, all triggered categories are treated
as violations. If specific categories are listed, only those are matched.

**Location:** `backend/models/workflow/configs/guardrails.py`

---

## Evaluators

All evaluators are instantiated by the `GuardrailsEngine` and follow a consistent pattern:
accept content/args plus a config, return a `GuardrailResult`.

### Input Evaluator

Validates user input before it reaches the LLM.

1. Applies `PatternRule` regex matching (direction=input).
2. Runs `BehavioralGuardrailEvaluator` if any detection category is enabled.
3. Merges results from both checks.

**Location:** `backend/services/guardrails/evaluators/input.py`

### Output Evaluator

Validates agent responses before they are returned. Three stages:

1. Applies `PatternRule` regex matching (direction=output).
2. Checks `max_output_length` from behavioural config.
3. Runs LLM Guard output scanners when any `OutputScanners` flag is enabled or when PII
   deanonymization is needed (vault round-trip from input phase).

Output scanners available:

| Scanner | Config Field | Default Action |
|---------|-------------|---------------|
| Toxicity | `detect_toxicity` | `"off"` |
| No-Refusal | `detect_refusal` | `"off"` |
| Sensitive Data | `detect_sensitive_data` | `"off"` |
| Ban Topics | `ban_topics` | `[]` |
| Language | `allowed_languages` | `[]` |
| Relevance | `check_relevance` | `"off"` |
| Gibberish | `detect_gibberish` | `"off"` |
| Ban Competitors | `ban_competitors` | `[]` |
| Bias | `detect_bias` | `"off"` |
| Factual Consistency | `check_factual_consistency` | `"off"` |
| Deanonymize | (automatic when vault used on input) | transform |

**Location:** `backend/services/guardrails/evaluators/output.py`

### Tool Call Evaluator

Validates tool arguments before tool execution. Routes to type-specific checks based on tool name
or node type.

| Tool Type | Checks Performed |
|-----------|-----------------|
| **HTTP** | SSRF protection (DNS resolution, blocked IP ranges, URL pattern matching) |
| **Database** | SQL operation type (e.g. only SELECT), blocked table names |
| **File Write** | Path traversal (`..`), blocked paths, allowed extensions, max file size |
| **All** | Cumulative tool call count against `max_tool_calls_per_execution` |

Default SSRF protection applies even without an explicit tool call policy, blocking private IP
ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, etc.) and dangerous schemes
(file, ftp, gopher, data, ldap, telnet).

**Location:** `backend/services/guardrails/evaluators/tool_call.py`, `backend/services/guardrails/ssrf.py`

### Token Budget Evaluator

Tracks cumulative token usage across the execution and enforces budget limits.

- Checks `max_input_tokens`, `max_output_tokens`, `max_total_tokens`, and `max_llm_calls`.
- Issues warning violations when usage reaches `warn_at_percentage` threshold (default 80%).
- Blocking violations when limits are exceeded.

**Location:** `backend/services/guardrails/evaluators/token_budget.py`

### Behavioural Evaluator

Thin orchestrator that routes evaluation to one of two backends:

1. **LLM Guard input scanners** (primary) -- fast, offline ML classifiers. Used when any scanner
   flag is enabled. Executes in two phases:
   - **Phase 1 (Sanitization):** PII anonymization and secret redaction run first, so downstream
     classifiers are not confused by PII/secret patterns.
   - **Phase 2 (Detection):** Adversarial and content scanners run on the sanitized text.
2. **LLM-as-judge** (fallback) -- context-aware adversarial detection via a dedicated LLM. Used
   only when prompt injection/jailbreak detection is enabled but no non-adversarial scanners are
   active. Evaluates two categories: `prompt_injection` and `jailbreak_attempt`.

Scanner fields use action enums (`"off"` / `"block"` / `"warn"`) instead of booleans. PII detection
supports a fourth action: `"anonymize"` (vault round-trip with optional faker replacement).

| Scanner | Config Field | Actions | Default |
|---------|-------------|---------|---------|
| Prompt Injection | `detect_prompt_injection` | off / block / warn | `"block"` |
| Jailbreak | `detect_jailbreak_attempts` | off / block / warn | `"block"` |
| Toxicity | `detect_toxicity` | off / block / warn | `"off"` |
| PII Anonymize | `anonymize_pii` | off / block / warn / anonymize | `"off"` |
| Secrets | `detect_secrets` | off / block / warn | `"off"` |
| Gibberish | `detect_gibberish` | off / block / warn | `"off"` |
| Ban Code | `ban_code` | off / block / warn | `"off"` |
| Ban Topics | `ban_topics` | list of topic strings | `[]` |
| Language | `allowed_languages` | list of language codes | `[]` |
| Token Limit | `max_input_tokens` | integer or null | `None` |

Configurable thresholds: `prompt_injection_threshold` (0.75), `jailbreak_threshold` (0.75),
`toxicity_threshold` (0.5).

**Location:** `backend/services/guardrails/evaluators/behavioral.py`, `input_scanners.py`, `llm_judge.py`

### Custom Filter Evaluator

Executes user-defined filters with three pluggable executor backends:

| Executor | Description |
|----------|-------------|
| **Python Sandbox** | AST-validated, restricted-builtin Python code with 30-second timeout and 100KB output limit. Blocks imports outside the allowlist, `eval`/`exec`, file I/O, and async constructs. User implements a `filter(content, direction, **context) -> dict` function. The `context` dict includes the filter's `action` ("warn", "block", or "transform") and other metadata. Supports pre-approved modules including **Presidio** and **Detoxify** (see below). Compiled sandboxes are cached by code hash (max 64 entries). |
| **LLM Judge** | Natural language policy evaluation via LLM. User provides a policy description; the LLM returns a violation/confidence/reasoning JSON response, compared against a configurable threshold. |
| **Declarative** | Template-based filters with predefined patterns: topic guard, language detection, and word count limits. Complex templates delegate to the LLM judge internally. (PII and toxicity detection are now handled natively via LLM Guard scanners in `BehavioralGuardrails` and `OutputScanners`.) |

Filters run in priority order (lower number = higher priority). Transform results cascade through
the chain (filter N's output becomes filter N+1's input). A `block` action halts the pipeline
immediately.

Each filter has a `scope` field: `ingress` (before LLM), `egress` (after LLM), or `both`.

**Location:** `backend/services/guardrails/filters/`

#### Pre-Approved Sandbox Modules

The Python sandbox executor allows a curated set of third-party modules:

| Module | Purpose |
|--------|---------|
| `presidio_analyzer` | Microsoft Presidio PII entity recognition |
| `presidio_anonymizer` | Microsoft Presidio PII anonymization/redaction |
| `detoxify` | ML-based toxicity classification (hate, threat, obscene, insult, etc.) |

These modules are declared in `ALLOWED_MODULES` and `LAZY_MODULES` in the sandbox executor.
At application startup, `preload_heavy_modules()` pre-warms all Python code filters found
in existing policies so that first-request latency is avoided.

**Location:** `backend/services/guardrails/filters/executors/python_sandbox.py` (pre-warming called from `backend/app.py`)

### Provider Content Filter (Exception-Based)

Unlike the evaluators above, provider content filter handling is not a pre/post check but an
**exception interceptor**. When the LLM provider (Azure OpenAI, OpenAI) rejects a request due to
its built-in content safety filters, the system catches the error and extracts structured violation
data.

**Detection flow:**

1. LLM call raises `BadRequestError` with `body.code == "content_filter"`.
2. `_parse_content_filter_error()` walks the exception `__cause__` and `__context__` chain
   (up to 10 levels) to find the original provider error, even when wrapped by
   `ToolExecutionError`, `StructuredOutputError`, etc.
3. Extracts triggered categories from `body.innererror.content_filter_result` (e.g. `jailbreak`,
   `hate`, `violence`, `sexual`, `self_harm`).
4. Falls back to string-based detection (`"content_filter"` or `"content management policy"` in
   error message) when structured body is unavailable.

**Enforcement:**

| Scenario | Behaviour |
|----------|-----------|
| Provider content filter policy active + enforce mode | Violations persisted and streamed, workflow fails with `GuardrailViolationError` |
| Provider content filter policy active + audit mode | Violations persisted and streamed, graceful blocked response returned |
| No provider content filter policy configured | Violations persisted via fallback path (severity=warn), graceful blocked response returned |

The fallback path ensures provider-level blocks are always visible in the violations dashboard,
even when no explicit provider content filter policy has been configured.

**Location:** `backend/services/execution/async_agent/executor.py` (`_parse_content_filter_error`, exception handler in `execute_agent`)

---

## Execution Pipeline Integration

Guardrails intercept the execution pipeline at eight checkpoint types. All checks are routed
through a single `GuardrailCheckpoint.check()` call that handles evaluation, violation reporting,
and enforcement uniformly. A `GuardrailContext` carries execution metadata through all checkpoints.

```text
User Input
    |
    v
+-----------------------------+
| 1. INPUT CHECK              |  checkpoint.check(..., "input", ctx)
|    Pattern rules + LLM      |  AsyncAgentExecutor.execute_agent()
|    Guard input scanners      |
|    + custom ingress filters  |
+-------------+---------------+
              |
              v
+-----------------------------+
| 2. SYSTEM PROMPT PROTECTION |  MessageBuilder
|    XML anchor wrapping       |  (preventive, not blocking)
+-------------+---------------+
              |
              v
         LLM Invocation
              |
         +----+----+
         |         |
    (success)  (provider error)
         |         |
         v         v
+---------------+ +-------------------------------+
| 3. TOOL CALL  | | 3a. PROVIDER CONTENT FILTER   |
|    CHECK      | |  report_prebuilt_violations()  |
|  "tool_call"  | +-------------------------------+
|  "tool_ingress"|
|  "tool_egress" |
|  "tool_injection"|
+-------+-------+
        |
        v
+-----------------------------+
| 4. TOKEN BUDGET CHECK       |  AgentNodeExecutor.execute()
|    Cumulative usage tracking |
+-------------+---------------+
              |
              v
+-----------------------------+
| 5. OUTPUT CHECK             |  checkpoint.check(..., "output", ctx)
|    Pattern rules + length   |  AgentNodeExecutor.execute()
|    + LLM Guard output       |
|    scanners + deanonymize   |
|    + custom egress filters  |
+-------------+---------------+
              |
              v
         Agent Response
```

### Checkpoint Types

| Type | Route | Purpose |
|------|-------|---------|
| `input` | `check_input()` | User message validation (pattern rules, behavioral scanners, custom ingress) |
| `output` | `check_output()` | Agent response validation (pattern rules, output scanners, custom egress) |
| `tool_call` | `check_tool_call()` | Tool argument validation (SSRF, SQL, file path) |
| `tool_ingress` | `check_input()` | Input guardrails on data sent to tools |
| `tool_egress` | `check_output()` | Output filtering on data received from tools |
| `tool_injection` | `check_input()` (behavioral-only) | Prompt injection scan on tool results before they become ToolMessages |
| `token_budget` | `check_token_budget()` | Cumulative usage tracking |
| `content_filter` | (reporting only) | Provider content filter errors (Azure/OpenAI) |

### Enforcement Mode Behaviour

| Interception Point | Enforce Mode | Audit Mode |
|--------------------|-------------|------------|
| **Input** | Raises `GuardrailViolationError`, fails workflow | Returns blocked response, logs violations |
| **System Prompt** | Wraps with anti-override delimiters | Same (preventive only) |
| **Tool Call** | Always blocks tool execution; LLM sees error message | Always blocks (no audit pass-through) |
| **Provider Content Filter** | Raises `GuardrailViolationError`, fails workflow | Returns blocked response, logs violations |
| **Token Budget** | Logs warning, continues execution | Logs warning, continues execution |
| **Output** | Raises `GuardrailViolationError`, fails workflow | Replaces response with blocked message, logs violations |

### Content Transformation

When a pattern rule uses the `redact` action, the evaluator replaces matched content with
`[REDACTED]` and passes the sanitized version forward. The LLM (for input) or the user (for output)
sees only the sanitized content while the original violation is logged.

---

## Workflow State Integration

The `WorkflowState` TypedDict includes two guardrails-related fields that flow through the
LangGraph execution:

| Field | Type | Purpose |
|-------|------|---------|
| `workflow_id` | `Optional[str]` | Set from `graph.workflow_id` at execution start. Used to attribute violations to the correct workflow in the violations dashboard. |
| `guardrails_state` | `Optional[Dict[str, Any]]` | Cumulative tracking across the execution. Tracks token budget usage (`input_tokens`, `output_tokens`, `total_tokens`, `llm_calls`), `tool_calls_count`, and accumulated violations. Uses `last_value_reducer`. |

**Location:** `backend/services/workflow/state/schemas.py`

---

## Shared Policy System

The shared policy system allows guardrail configurations to be defined once and reused across
workflows, agents, tools, and models.

### Database Schema

```text
+----------------------+     +-------------------------+
|  GuardrailPolicy     |     |  GuardrailAssignment     |
+----------------------+     +-------------------------+
|  id (UUID)           |<----|  policy_id (FK)          |
|  name                |     |  target_type             |
|  description         |     |  target_id               |
|  config (JSONB)      |     |  workflow_id (FK)        |
|  scope               |     |  priority                |
|  is_compulsory       |     |  override_mode           |
|  is_template         |     |  assigned_by             |
|  is_builtin          |     +-------------------------+
|  shared_with (JSONB) |
|  tags (JSONB)        |     +-------------------------+
|  version             |     | GuardrailPolicyVersion   |
|  created_by (FK)     |<----+-------------------------+
+----------+-----------+     |  policy_id (FK)          |
           |                 |  version                 |
           |                 |  config_snapshot (JSONB)  |
           v                 |  change_summary          |
+----------------------+     +-------------------------+
| GuardrailViolation   |
| Event                |     +-------------------------+
+----------------------+     | GuardrailViolation       |
|  graph_execution_id  |     | Feedback                |
|  node_execution_id   |     +-------------------------+
|  policy_id (FK)      |     |  violation_event_id (FK) |
|  policy_name         |     |  user_id                 |
|  rule_name           |     |  rating (positive/       |
|  category            |     |          negative)       |
|  severity            |     |  comment                 |
|  action_taken        |     +-------------------------+
|  message             |
|  details (JSONB)     |
|  workflow_id (FK)    |
|  agent_node_id       |
|  agent_node_name     |
|  user_id             |
|  is_compulsory_policy|
+----------------------+
```

**Location:** `backend/models/guardrails/`

### Policy Scopes and Sharing

| Scope | Visibility |
|-------|-----------|
| `user` | Creator only (default) |
| `organization` | All users in the organisation |
| `global` | Platform-wide; required for compulsory policies |

Policies can also be shared with specific users via the `shared_with` list or with groups via
group-based visibility. Policies marked `is_template` appear in the template catalogue for easy
reuse.

### Policy Versioning

Every update to a policy creates an immutable `GuardrailPolicyVersion` snapshot. This enables:

- **Audit trail** - Full history of who changed what and when.
- **Rollback** - Any prior version can be restored, which creates a new version record.
- **Diff review** - Config snapshots can be compared between versions.

### Layered Policy Resolution

When an agent node executes, the `LayeredPolicyResolver` merges policies from six layers in
priority order (highest to lowest):

```text
Layer 1:  Compulsory policies  (scope=global, is_compulsory=true)  <- TTL-cached (60s)
Layer 2:  Organisation-level   (scope=organization)
Layer 3:  Workflow-level       (target_type=workflow)
Layer 4:  Tool-specific        (target_type=tool)
Layer 5:  Model-specific       (target_type=model)
Layer 6:  Agent-node           (target_type=agent_node)
```

**Merge rules:**

- **Pattern rules** - Additive across all layers; higher-priority rules cannot be removed.
- **Enforcement mode** - Strictest wins (`enforce` > `audit` > `disabled`).
- **Tool call policy** - Restrictive merge (blocked patterns union, allowed patterns intersect).
- **Token budget** - Strictest limits from any layer.
- **Behavioural detection** - OR across layers (if any layer enables a category, it stays enabled). Action enums escalate to strictest (`block` > `warn` > `off`). Thresholds take the lowest value.
- **Output scanners** - OR across layers, same escalation rules as behavioural.
- **Provider content filter** - OR across layers (enabled if any layer enables it; categories are merged).
- **Custom filters** - Additive across all layers.

Compulsory policies are TTL-cached for 60 seconds. On database failure, stale cached values are
served as a fallback.

**Location:** `backend/services/guardrails/resolver.py`

---

## Violation Tracking

### Dual Persistence

Every violation is both:

1. **Persisted to database** via `ViolationPersistenceService` for audit, compliance reporting, and analytics.
2. **Streamed via WebSocket** via `StreamingEventEmitter.emit_guardrail_violation()` for real-time UI notifications.

This dual-persistence pattern is centralised in `GuardrailCheckpoint._report_violations()`, which
is called automatically by `check()` when violations are detected. For pre-built violations (e.g.
provider content filter errors), the static `report_prebuilt_violations()` method provides the
same persist-and-emit flow. Call sites no longer need to interact with `ViolationPersistenceService`
or `StreamingEventEmitter` directly.

The persisted violation's database ID is included in the WebSocket event so the frontend can
correlate streaming notifications with stored records.

### Violation Attribution

Each violation record captures its full context:

- `workflow_id` and enriched `workflow_name` - which workflow was running
- `agent_node_id` and `agent_node_name` - which agent triggered the violation
- `policy_id` and `policy_name` - which policy was violated
- `graph_execution_id` - links to the execution history for deep-dive
- `is_compulsory_policy` - whether the violated policy was admin-enforced

The violations API enriches records with `workflow_name` and `policy_name` from related tables
when they are not stored directly on the violation event.

### Violation Feedback

Users can submit feedback on violations (`positive` = legitimate violation, `negative` = false
positive) with an optional comment. Feedback uses upsert semantics (submitting again toggles or
updates the rating). This feeds into policy effectiveness metrics and helps administrators tune
rules.

### Guardrail Block Modal

When a guardrail blocks execution in enforce mode, the frontend displays a `GuardrailBlockModal` -
a full-screen alert dialog showing the policy name and triggered rule. The modal includes a
`ViolationFeedbackControl` for immediate positive/negative feedback and an "End Execution" button.

**Location:** `frontend/src/components/core/GuardrailBlockModal.tsx`

### Admin Dashboards

- **Compliance summary** - Enforcement breakdown across workflows, unprotected workflows/nodes with criticality levels.
- **Platform metrics** - Violation trends, top triggered rules, false positive rates (30-day window).
- **Per-policy metrics** - Effectiveness data for individual policies (block/warn rates, feedback summary).

---

## API Surface

All guardrail endpoints are organised into route modules under `/api/guardrails`.

### Main Routes (`/api/guardrails`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/policies` | User (admin for global/compulsory) | Create a new guardrail policy |
| GET | `/policies` | User | List policies visible to current user |
| GET | `/policies/{id}` | User | Get a single policy |
| PUT | `/policies/{id}` | User | Update a policy |
| DELETE | `/policies/{id}` | User | Delete a policy |
| PATCH | `/policies/{id}/visibility` | User | Update group-based visibility |
| POST | `/policies/{id}/share` | User | Share a policy with users or groups |
| DELETE | `/policies/{id}/share/{target}` | User | Remove shared access |
| POST | `/policies/{id}/clone` | User | Clone a policy |
| POST | `/assignments` | User | Assign a policy to a target |
| PATCH | `/assignments/{id}` | User | Update an assignment |
| DELETE | `/assignments/{id}` | User | Remove an assignment |
| GET | `/assignments` | User | List assignments |
| GET | `/resolve` | User | Preview effective merged config |
| GET | `/templates` | User | List template policies |

### Admin Routes

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/admin/compulsory` | Admin | List compulsory policies |
| POST | `/admin/compulsory` | Admin | Promote/demote a policy to compulsory |
| DELETE | `/admin/compulsory/{id}` | Admin | Remove compulsory status |
| GET | `/admin/compliance` | Admin | Enforcement compliance summary |
| GET | `/admin/metrics` | Admin | Platform-wide violation metrics |

### Violations Routes (`/api/guardrails/violations`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/` | User (admin sees all) | List violations with filters (policy, severity, workflow, time range) |
| GET | `/summary` | Admin | Aggregated violation summary |
| GET | `/{id}` | User | Single violation with feedback details |

### Feedback Routes (`/api/guardrails/violations/{id}/feedback`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/` | User | Submit or update feedback (positive/negative + comment) |
| DELETE | `/` | User | Remove feedback |

### Sandbox / Test Routes (`/api/guardrails/policies/{id}/test`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/preview` | User | Metadata about sandbox test (e.g. whether LLM call required) |
| POST | `/` | User | Run sandbox evaluation without persisting violations |

### Version Routes (`/api/guardrails/policies/{id}/versions`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/` | User | List all versions of a policy |
| GET | `/{version_id}` | User | Get a specific version snapshot |
| POST | `/{version_id}/rollback` | User | Rollback to a prior version |

### Metrics Routes (`/api/guardrails/policies/{id}`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/metrics` | User | Aggregated violation and feedback metrics for a policy |

**Location:** `backend/api/guardrails/`

---

## Key File Map

| Area | Files |
|------|-------|
| **Engine** | `backend/services/guardrails/engine.py`, `backend/services/guardrails/__init__.py` |
| **Checkpoint** | `backend/services/guardrails/checkpoint.py` (`GuardrailCheckpoint`, `GuardrailContext`) |
| **Config models** | `backend/models/workflow/configs/guardrails.py` |
| **Result models** | `backend/services/guardrails/models.py` |
| **Evaluators** | `backend/services/guardrails/evaluators/input.py`, `output.py`, `tool_call.py`, `token_budget.py`, `behavioral.py`, `input_scanners.py`, `llm_judge.py` |
| **Scanner backends** | `backend/services/guardrails/backends/__init__.py`, `protocol.py`, `local.py`, `api.py`, `hybrid.py` |
| **Pattern rules** | `backend/services/guardrails/pattern_rules.py` |
| **SSRF validation** | `backend/services/guardrails/ssrf.py` |
| **Custom filters** | `backend/services/guardrails/filters/evaluator.py`, `filters/executors/python_sandbox.py`, `llm_judge.py`, `declarative.py` |
| **Policy service** | `backend/services/guardrails/policy_service.py` |
| **Policy resolver** | `backend/services/guardrails/resolver.py` |
| **DB models** | `backend/models/guardrails/guardrail_policy.py`, `guardrail_assignment.py`, `violation_event.py`, `policy_version.py`, `violation_feedback.py` |
| **API routes** | `backend/api/guardrails/routes.py`, `violations/routes.py`, `sandbox/routes.py`, `metrics/routes.py`, `feedback/routes.py`, `compliance/routes.py`, `versions/routes.py` |
| **Violation persistence** | `backend/services/guardrails/violation_persistence.py` |
| **Pipeline integration** | `backend/services/execution/async_agent/executor.py`, `tool_executor.py`, `backend/services/nodes/executors/agent.py` |
| **Workflow state** | `backend/services/workflow/state/schemas.py` (`workflow_id`, `guardrails_state`) |
| **Navigation feature** | `backend/services/auth/constants.py` (`NAV_GUARDRAILS`), migration in `schema_updates.py` |
| **Frontend - policy hub** | `frontend/src/components/core/GuardrailPolicies.tsx` |
| **Frontend - builder** | `frontend/src/components/core/guardrails/GuardrailBuilder.tsx`, `GuardrailCard.tsx` |
| **Frontend - catalogue** | `frontend/src/components/core/guardrails/GuardrailCatalogModal.tsx`, `catalog.ts` |
| **Frontend - sandbox** | `frontend/src/components/core/guardrails/PolicyTestSandbox.tsx`, `SandboxPanel.tsx` |
| **Frontend - compliance** | `frontend/src/components/core/guardrails/ComplianceView.tsx` |
| **Frontend - violations** | `frontend/src/components/core/ViolationDashboard.tsx`, `frontend/src/components/core/guardrails/ViolationsDashboard.tsx` |
| **Frontend - feedback** | `frontend/src/components/core/ViolationFeedbackControl.tsx` |
| **Frontend - block modal** | `frontend/src/components/core/GuardrailBlockModal.tsx` |
| **Frontend - config preview** | `frontend/src/components/core/guardrails/EffectiveConfigPreview.tsx` |
| **Frontend - assignments** | `frontend/src/components/core/guardrails/AssignmentList.tsx` |
| **Frontend - policy picker** | `frontend/src/components/core/guardrails/PolicyPicker.tsx` |
| **Frontend - tool guardrails** | `frontend/src/components/core/guardrails/ToolGuardrailsSection.tsx` |
| **Frontend - version history** | `frontend/src/components/core/guardrails/PolicyVersionHistory.tsx` |
| **Frontend - policy metrics** | `frontend/src/components/core/PolicyMetrics.tsx` |
| **Frontend - Monaco editor** | `frontend/src/components/panels/properties/sections/guardrails/filters/PythonCodeFilterEditor.tsx` |
| **Frontend - API client** | `frontend/src/lib/guardrails-api.ts` |
| **Frontend - types** | `frontend/src/types/guardrail-policies.ts`, `frontend/src/types/guardrails.ts` |

---

## Frontend UI

The guardrails frontend is centred on the `/guardrails` page (gated by `nav.guardrails` feature
flag), which renders the `GuardrailPolicies` component. This single component contains the policy
hub, inline sub-components for cards and modals, and the compulsory promotion workflow.

### Tab Structure

| Tab | Visibility | Contents |
|-----|-----------|----------|
| **My Policies** | All users | Policies created by the current user |
| **Shared with Me** | All users | Policies shared by others (non-template, non-compulsory) |
| **Templates** | All users | Policies marked as reusable templates |
| **Violations** | All users | `ViolationDashboard` with filtering, feedback controls, and workflow/node attribution |
| **Compulsory** | Admin only | All compulsory policies with status banner and management actions |

### Guardrail Catalogue

The `GuardrailCatalogModal` presents available guardrail types organised into seven categories:

| Category | Items |
|----------|-------|
| **Data Protection** | Custom pattern rules (regex-based DLP) |
| **Input Safety** | Adversarial Detection, PII Detection, Input Content Safety (toxicity, gibberish, ban code), Input Policy Controls (topics, languages, secrets, token limit), LLM Judge, General Safety |
| **Output Safety** | Response Quality (refusal, relevance, factual consistency), Output Content Safety (toxicity, bias, gibberish), Output Policy Controls (sensitive data, competitors, topics, languages) |
| **Provider Safety** | Provider content filter (singleton) |
| **Tool Restrictions** | Network/SSRF protection, database restrictions, file system restrictions, execution limits (all singletons) |
| **Cost Controls** | Token budget and call limits (singleton) |
| **Custom Filters** | Python code filter, LLM judge filter, declarative template filters (topic guard, language detector, word count limit) |

Singleton items can only be added once per policy configuration.

Three **quick-start bundles** provide one-click setup: LLM Safety, Compliance Kit, and AI Safety Suite.

**Location:** `frontend/src/components/core/guardrails/catalog.ts`

### Python Code Filter Editor

The node properties panel includes a Monaco editor for writing Python sandbox filter code, with
syntax highlighting, a custom dark theme, and a full-screen modal mode.

**Location:** `frontend/src/components/panels/properties/sections/guardrails/filters/PythonCodeFilterEditor.tsx`

### Key Components

- **PolicyCard** - Grid card showing policy name, scope badge, enforcement mode, rule count, tags,
  and hover actions (clone, delete, promote/demote).
- **CreatePolicyDialog** - Modal with name/description fields and a full `GuardrailBuilder` for
  adding rules from the catalogue.
- **PolicyDetailModal** - Full detail view with three inner tabs (Configuration, Version History,
  Metrics), edit/save mode, sandbox testing, and promote/demote buttons for admins. Edit/save
  buttons are restricted to the policy owner or admins (compulsory policies are always read-only
  for non-owners).
- **PromoteCompulsoryDialog** - Confirmation dialog for promoting a policy to compulsory status,
  with enforcement mode selection (audit-first recommended vs enforce immediately).
- **GuardrailBuilder** - Ordered list of guardrail items with enforcement mode selector and
  drag-reorder. The "Add" button opens `GuardrailCatalogModal`.
- **PolicyTestSandbox** - Test a policy against sample input/output text with violation results.
- **EffectiveConfigPreview** - Shows the resolved/merged guardrails config for a given context.
- **PolicyPicker** - Dropdown for selecting and assigning policies to targets.
- **AssignmentList** - Displays policy assignments for a target with management actions.
- **PolicyVersionHistory** - Timeline view of policy versions with rollback capability.
- **PolicyMetrics** - Charts and metrics for policy effectiveness (violations, feedback, block rates).
- **ViolationFeedbackControl** - Thumbs up/down buttons with optimistic UI updates for rating violations.
- **GuardrailBlockModal** - Full-screen alert when execution is blocked, with feedback controls.

---

## Compulsory Policy Lifecycle

Compulsory policies are admin-enforced rules that apply to every workflow in the organisation.
They sit at the top of the resolution stack (Layer 1) and cannot be weakened by user-level policies.

### Recommended Workflow

The system is designed so that admins follow a graduated Create -> Test -> Audit -> Enforce workflow
rather than immediately imposing blocking rules organisation-wide.

```text
Step 1: CREATE                 Step 2: TEST                  Step 3: PROMOTE
---------------------          ------------------            ------------------
Admin creates a                Test policy in                Promote via card
personal policy                the sandbox with              hover action or
in "My Policies"               sample inputs.                detail modal
tab (scope=user).              Optionally assign             "Make Compulsory"
                               to 1-2 workflows              button.
                               in audit mode to
                               observe real                  Choose enforcement:
                               violations.                   * Audit first
                                                               (recommended)
                                                             * Enforce immediately


Step 4: MONITOR                Step 5: ENFORCE (optional)    Step 6: DEMOTE (if needed)
-------------------            -------------------------     --------------------------
Review violations              Once confident, switch        Remove compulsory status
in the Compulsory              enforcement mode from         via "Remove Compulsory"
tab and Violations             audit to enforce on           button. Policy returns
dashboard. Check               the policy. This can          to personal scope.
per-policy metrics.            be done by editing
                               the policy config.
```

### Promotion UI

Admins can promote any non-compulsory policy to compulsory status from two places:

1. **PolicyCard hover action** - An arrow-up icon appears on hover (admin only).
2. **PolicyDetailModal header** - A "Make Compulsory" button appears next to "Test Policy".

Both open the `PromoteCompulsoryDialog`, which:

- Explains the impact ("applies to all workflows, cannot be overridden").
- Offers two enforcement modes:
  - **Audit first** (recommended) - Switches the policy's `enforcement_mode` to `audit` before
    promoting, so violations are logged but not blocked. The admin can later switch to enforce.
  - **Enforce immediately** - Promotes with the current enforcement mode unchanged.
- Displays a summary of the policy's rules (pattern rules, custom filters, behavioural checks,
  token budget, tool restrictions).

### Demotion

Compulsory policies can be demoted (compulsory status removed) from:

1. **PolicyCard hover action** - An arrow-down icon on compulsory policy cards.
2. **PolicyDetailModal header** - A "Remove Compulsory" button replaces "Make Compulsory".

Demotion calls `DELETE /api/guardrails/admin/compulsory/{policy_id}`, which sets `is_compulsory=false`.
The policy reverts to a personal policy and is no longer included in Layer 1 resolution.

### Compulsory Tab

The Compulsory tab (admin-only) serves as the management hub:

- **Status banner** - Shows the count of active compulsory policies and a link to the compliance view.
- **Policy grid** - Standard `PolicyCard` layout with promote/demote hover actions.
- **Empty state** - Guided workflow showing the three-step process (Create -> Test -> Promote)
  with a shortcut to navigate to "My Policies".

### Backend API Integration

| Action | Frontend function | Backend endpoint |
|--------|------------------|-----------------|
| Promote | `setCompulsoryPolicy(id, true)` | `POST /api/guardrails/admin/compulsory` |
| Demote | `deactivateCompulsoryPolicy(id)` | `DELETE /api/guardrails/admin/compulsory/{id}` |
| List compulsory | `listCompulsoryPolicies()` | `GET /api/guardrails/admin/compulsory` |
| Update enforcement mode | `updatePolicy(id, { config })` | `PUT /api/guardrails/policies/{id}` |

All compulsory management endpoints require `is_admin=true`. Non-admin users see compulsory
policies as read-only entries when they appear in the resolution stack.
