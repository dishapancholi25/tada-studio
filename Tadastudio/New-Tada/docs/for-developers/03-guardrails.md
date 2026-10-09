# Guardrails

## Overview

Guardrails enforce safety policies on AI workflow executions. They run as middleware interceptors at six points in the execution pipeline,
checking inputs, outputs, tool calls, token budgets, behavioral patterns, and provider content filters before or after they flow through the system.

Guardrails are configured per-agent via the `guardrails_config` field on `AgentConfig`, with support for
workflow-level defaults that cascade to individual agents. The shared policy system allows guardrail
configurations to be defined once and reused across workflows, agents, tools, and models.

## Architecture

```
User Input
  |
  +---> [INPUT CHECK]              checkpoint.check(..., "input", ctx)
  |     Pattern rules + LLM Guard input scanners + custom ingress filters
  |         |
  |         v
  +---> [SYSTEM PROMPT PROTECTION] Anti-override anchoring on system prompt
  |         |
  |         v
  +---> LLM Invocation
  |         |
  |    +----+----+
  |    |         |
  | (success)  (provider error)
  |    |         |
  |    v         v
  +---> [TOOL CALL GUARDRAILS]   [PROVIDER CONTENT FILTER]
  |     "tool_call"               report_prebuilt_violations()
  |     "tool_ingress"
  |     "tool_egress"
  |     "tool_injection"
  |         |
  |         v
  +---> [TOKEN BUDGET CHECK]       Cumulative budget tracking
  |         |
  |         v
  +---> [OUTPUT CHECK]             checkpoint.check(..., "output", ctx)
  |     Pattern rules + length + LLM Guard output scanners + custom egress filters
  |         |
  |         v
  +---> Review Node (if enabled)   Existing review mechanism (unchanged)
```

All checks (except system prompt protection and token budget tracking) are routed through
`GuardrailCheckpoint.check()`, which handles evaluation, violation reporting (DB + WebSocket),
and enforcement (raise on enforce, log on audit) in a single call. The `GuardrailContext`
dataclass bundles execution metadata (IDs, agent info) so it doesn't need to be threaded
through every function signature.

### Package Structure

```
backend/services/guardrails/
    __init__.py                     # Singleton accessor: get_guardrails_engine()
    engine.py                       # GuardrailsEngine — orchestrator + resolve_unified()
    checkpoint.py                   # GuardrailCheckpoint (unified entry point) + GuardrailContext
    models.py                       # GuardrailResult, Violation dataclasses
    ssrf.py                         # URL/IP validation for SSRF protection
    pattern_rules.py                # PatternRule regex matching (block/redact/warn)
    policy_service.py               # Shared policy CRUD
    resolver.py                     # LayeredPolicyResolver (6-layer merge)
    violation_persistence.py        # Violation DB persistence
    evaluators/
        __init__.py
        input.py                    # InputGuardrailEvaluator
        output.py                   # OutputGuardrailEvaluator
        tool_call.py                # ToolCallGuardrailEvaluator
        token_budget.py             # TokenBudgetEvaluator
        behavioral.py               # BehavioralGuardrailEvaluator (orchestrator)
        input_scanners.py           # LLM Guard input scanner utilities
        llm_judge.py                # LLM-as-judge fallback for adversarial detection
    backends/
        __init__.py                 # Factory: get_scanner_backend()
        protocol.py                 # ScannerBackend protocol, ScannerResult, ScanResult
        local.py                    # LocalScannerBackend (in-process)
        api.py                      # ApiScannerBackend (HTTP to llm-guard service)
        hybrid.py                   # HybridScannerBackend (local + remote)
    filters/
        __init__.py
        evaluator.py                # CustomFilterEvaluator
        templates.py                # Filter template definitions
        executors/
            __init__.py
            python_sandbox.py       # Python sandbox executor (Presidio, Detoxify)
            llm_judge.py            # LLM judge filter executor
            declarative.py          # Declarative template executor
```

Configuration model: `backend/models/workflow/configs/guardrails.py`

## Enforcement Modes

Every guardrails config has an `enforcement_mode` that controls how violations are handled:

| Mode | Behavior |
|------|----------|
| `enforce` | Block violations — the check fails and the content/tool call is rejected |
| `audit` | Log violations but allow through — useful for testing rules before enforcing |
| `disabled` | No checking at all |

When `enforcement_mode` is `audit`, all violations are logged at WARNING level with the `[GUARDRAILS-AUDIT]` prefix. The check always returns `passed=True` so execution continues, but violations are still recorded and emitted via WebSocket.

## Configuration

### GuardrailsConfig

The top-level config object. Set on `AgentConfig.guardrails_config`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `False` | Master toggle. Nothing runs if this is `False` |
| `enforcement_mode` | `str` | `"enforce"` | `"enforce"`, `"audit"`, or `"disabled"` |
| `inherit_from_workflow` | `bool` | `True` | Whether to merge with workflow-level guardrails |
| `pattern_rules` | `list[PatternRule]` | `[]` | Regex-based content matching rules |
| `tool_call_policy` | `ToolCallPolicy` | `None` | Tool call restrictions |
| `token_budget` | `TokenBudget` | `None` | Token/cost limits |
| `behavioral` | `BehavioralGuardrails` | `None` | Behavioral safety settings (input scanners) |
| `output_scanners` | `OutputScanners` | `None` | LLM Guard output scanner configuration |
| `provider_content_filter` | `ProviderContentFilter` | `None` | Provider-level content filter handling |
| `custom_filters` | `list[CustomFilter]` | `[]` | User-defined ingress/egress filters |
| `source_policies` | `list[dict]` | `[]` | Internal — tracks which shared policies contributed to this config |
| `rule_policy_map` | `dict` | `{}` | Internal — maps rules to source policies for violation attribution |

### PatternRule and PatternEntry

Regex-based pattern matching on input/output text. Each rule contains one or more labeled patterns.

**PatternEntry:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `label` | `str` | `""` | Human-readable name for this pattern |
| `regex` | `str` | `""` | The regex pattern string (Python `re` syntax) |

**PatternRule:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `""` | Human-readable rule name |
| `description` | `str` | `""` | Short description (used in the UI preset picker, optional) |
| `patterns` | `list[PatternEntry]` | `[]` | List of labeled regex patterns |
| `action` | `str` | `"block"` | `"block"` / `"warn"` / `"redact"` |
| `applies_to` | `str` | `"both"` | `"input"` / `"output"` / `"both"` |
| `message` | `str` | `""` | Custom message shown when rule triggers |
| `preset_id` | `str` | `""` | Built-in preset ID (e.g. `"ssn_us"`) if from a preset |

**Actions:**

- `block` — Fails the check. The input/output is rejected.
- `redact` — Replaces matched content with `[REDACTED]` and continues.
- `warn` — Logs the match but allows content through unchanged.

**Regex syntax:**

Patterns use Python `re` module syntax on the backend. Inline flags are supported at the start of the pattern:

- `(?i)` — case-insensitive matching (e.g. `(?i)\b(DROP|DELETE)\b`)

The frontend `RegexInput` validator strips leading Python inline flags (`(?i)`, `(?s)`, `(?m)`, `(?x)`) before testing with `new RegExp()`, so patterns with `(?i)` pass UI validation.

**Built-in presets:**

The frontend defines all presets in a single `PATTERN_RULE_PRESETS` array in `frontend/src/types/guardrails.ts`. Presets are convenience templates — they are not auto-applied. Users select them from a dropdown to pre-fill a pattern rule.

| Preset ID | Name | Patterns | Action |
|-----------|------|----------|--------|
| `ssn_us` | SSN (US) | 1 | `redact` |
| `credit_card` | Credit Card | 1 | `redact` |
| `email` | Email Address | 1 | `warn` |
| `phone_us` | Phone (US) | 1 | `warn` |
| `api_key` | API Key | 1 | `redact` |
| `aws_key` | AWS Access Key | 1 | `block` |
| `private_key` | Private Key | 1 | `block` |
| `sql_injection` | SQL Injection | 2 | `block` |
| `prompt_injection` | Prompt Injection | 3 | `block` |
| `code_execution` | Code Execution | 3 | `block` |
| `confidential_data` | Confidential Data Leak | 3 | `block` |
| `url_filtering` | URL / Link Filtering | 2 | `warn` |

### ToolCallPolicy

Controls what tool calls are permitted.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `allowed_url_patterns` | `list[str]` | `[]` | Glob patterns for allowed URLs. Empty = allow all |
| `blocked_url_patterns` | `list[str]` | `[]` | Glob patterns for blocked URLs |
| `blocked_ip_ranges` | `list[str]` | See below | CIDR ranges blocked for SSRF |
| `allowed_sql_operations` | `list[str]` | `["SELECT"]` | Allowed SQL operations |
| `blocked_tables` | `list[str]` | `[]` | Table names that cannot be queried |
| `max_query_rows` | `int` | `1000` | Maximum rows a query can return |
| `allowed_file_extensions` | `list[str]` | `[]` | Allowed file extensions for writes. Empty = allow all |
| `blocked_file_paths` | `list[str]` | `[]` | Path patterns blocked for file writes |
| `max_file_size_mb` | `float` | `10.0` | Maximum file size in MB |
| `max_tool_calls_per_execution` | `int` | `50` | Total tool call limit |
| `tool_timeout_seconds` | `int` | `60` | Timeout for individual tool calls |

**Default blocked IP ranges (SSRF protection):**

- `10.0.0.0/8` — Private network (Class A)
- `172.16.0.0/12` — Private network (Class B)
- `192.168.0.0/16` — Private network (Class C)
- `127.0.0.0/8` — Loopback
- `169.254.0.0/16` — Link-local / cloud metadata (AWS `169.254.169.254`)
- `0.0.0.0/8` — Current network

SSRF protection also blocks these URL schemes: `file`, `ftp`, `gopher`, `data`, `dict`, `ldap`, `telnet`.

### TokenBudget

Limits on LLM usage per execution.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_input_tokens_per_execution` | `int` | `None` | Max input tokens across all LLM calls |
| `max_output_tokens_per_execution` | `int` | `None` | Max output tokens across all LLM calls |
| `max_total_tokens_per_execution` | `int` | `None` | Max total tokens across all LLM calls |
| `max_llm_calls_per_execution` | `int` | `20` | Max number of LLM invocations |
| `warn_at_percentage` | `float` | `0.8` | Emit warning when usage hits this fraction (0.0-1.0) |

Token usage is tracked cumulatively in `WorkflowState.guardrails_state` and checked after each LLM call.

### BehavioralGuardrails

Settings for behavioral safety checks on **input**. Uses LLM Guard ML scanners as the primary detection engine, with LLM-as-judge as a fallback for adversarial detection when no non-adversarial scanners are enabled.

Scanner fields use action enums: `"off"` (disabled), `"block"` (fail execution), or `"warn"` (log but continue).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `detect_prompt_injection` | `str` | `"block"` | Prompt injection scanner action |
| `detect_jailbreak_attempts` | `str` | `"block"` | Jailbreak scanner action |
| `system_prompt_protection` | `bool` | `True` | Wrap system prompt with anti-override anchoring |
| `max_input_length` | `int` | `50000` | Maximum input character length |
| `max_output_length` | `int` | `100000` | Maximum output character length |
| `judge_llm_config` | `LLMConfig` | `None` | LLM configuration for the behavioral judge model |
| `detect_toxicity` | `str` | `"off"` | Toxicity input scanner action |
| `anonymize_pii` | `str` | `"off"` | PII detection action (`"off"` / `"block"` / `"warn"` / `"anonymize"`) |
| `use_faker` | `bool` | `False` | When anonymize_pii is `"anonymize"`, use realistic fake data instead of `[REDACTED_*]` |
| `pii_entity_types` | `list[str]` | `[]` | Which Presidio entity types to detect. Empty = all 38+ types. See `pii-entity-types.ts` for full list |
| `detect_secrets` | `str` | `"off"` | Secrets input scanner action |
| `ban_topics` | `list[str]` | `[]` | Topics to ban via BanTopics scanner |
| `allowed_languages` | `list[str]` | `[]` | Language codes to allow via Language scanner |
| `detect_gibberish` | `str` | `"off"` | Gibberish input scanner action |
| `ban_code` | `str` | `"off"` | BanCode input scanner action |
| `max_input_tokens` | `int` | `None` | Max input tokens via TokenLimit scanner |
| `prompt_injection_threshold` | `float` | `0.75` | Confidence threshold for prompt injection (0.0-1.0) |
| `jailbreak_threshold` | `float` | `0.75` | Confidence threshold for jailbreak (0.0-1.0) |
| `toxicity_threshold` | `float` | `0.5` | Confidence threshold for input toxicity (0.0-1.0) |

**Two-path detection architecture:**

1. **LLM Guard input scanners** (primary) — fast, offline ML classifiers. Used when any scanner flag is enabled. Runs in two phases:
   - Phase 1 (Sanitization): PII anonymization and secret redaction run first, so downstream classifiers are not confused by PII patterns.
   - Phase 2 (Detection): Adversarial and content scanners run on sanitized text.
2. **LLM-as-judge** (fallback) — context-aware adversarial detection via a dedicated LLM. Used only when
   prompt injection/jailbreak detection is enabled but no non-adversarial scanners are active.
   The judge evaluates two categories: `prompt_injection` and `jailbreak_attempt`.

### OutputScanners

LLM Guard output scanner configuration. Controls ML-based scanners that run on LLM responses.

All scanner fields use the same action enum: `"off"` / `"block"` / `"warn"`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `detect_toxicity` | `str` | `"off"` | Toxicity output scanner |
| `detect_refusal` | `str` | `"off"` | No-refusal scanner (detects when LLM refuses to answer) |
| `detect_sensitive_data` | `str` | `"off"` | Sensitive data output scanner |
| `ban_topics` | `list[str]` | `[]` | Topics to ban in output |
| `allowed_languages` | `list[str]` | `[]` | Allowed language codes for output |
| `check_relevance` | `str` | `"off"` | Relevance checker (requires original prompt) |
| `detect_gibberish` | `str` | `"off"` | Gibberish output scanner |
| `ban_competitors` | `list[str]` | `[]` | Competitor names to detect in output |
| `detect_bias` | `str` | `"off"` | Bias detection |
| `check_factual_consistency` | `str` | `"off"` | Factual consistency checker (requires original prompt) |
| `toxicity_threshold` | `float` | `0.5` | Confidence threshold for output toxicity (0.0-1.0) |

When PII anonymization was used on input (vault round-trip), the output evaluator also runs a **deanonymize** scanner to restore original PII in the final output.

### ProviderContentFilter

Configures how the system handles provider-level content filter errors (e.g. Azure OpenAI's Responsible AI filters).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `True` | Whether to treat provider content filter errors as violations |
| `categories` | `list[str]` | `[]` | Which filter categories to act on (empty = all). Common: `violence`, `sexual`, `self_harm`, `hate_speech`, `jailbreak`, `protected_material` |

When a provider blocks a request, the system catches the error, extracts triggered categories, and records them as violations. The enforcement mode controls whether execution fails (`enforce`) or continues with logging (`audit`).

### CustomFilter

A user-defined filter for ingress/egress content processing.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `""` | Unique filter identifier (UUID) |
| `name` | `str` | `""` | Human-readable filter name |
| `filter_type` | `str` | `"python_code"` | `"python_code"` / `"llm_judge"` / `"declarative"` |
| `action` | `str` | `"block"` | `"block"` / `"warn"` / `"transform"` |
| `scope` | `str` | `"both"` | `"ingress"` / `"egress"` / `"both"` |
| `enabled` | `bool` | `True` | Per-filter toggle |
| `priority` | `int` | `100` | Execution order (lower = first, 0-999) |
| `python_code` | `str` | `""` | Python function source (for python_code type) |
| `judge_prompt` | `str` | `""` | Natural language policy (for llm_judge type) |
| `judge_llm_config` | `LLMConfig` | `None` | LLM config for judge (for llm_judge type) |
| `judge_threshold` | `float` | `0.7` | Confidence threshold (for llm_judge type) |
| `template_id` | `str` | `""` | Template identifier (for declarative type) |
| `template_params` | `dict` | `{}` | Template-specific parameters (for declarative type) |
| `message` | `str` | `""` | Custom violation/transform message |

**Executor backends:**

| Executor | Description |
|----------|-------------|
| **Python Sandbox** | AST-validated, restricted-builtin Python with 30s timeout and 100KB output limit. Supports Presidio and Detoxify modules. Compiled code cached by hash. |
| **LLM Judge** | Natural language policy evaluated by an LLM. Returns violation/confidence/reasoning JSON. |
| **Declarative** | Template-based filters: Topic Guard, Language Detector, Word Count Limit. Complex templates delegate to the LLM judge internally. |

## Insertion Points

All guardrail checks (except system prompt protection and token budget tracking) use the unified
`GuardrailCheckpoint` pattern:

```python
from backend.services.guardrails import get_guardrails_engine
from backend.services.guardrails.checkpoint import GuardrailCheckpoint, GuardrailContext

engine = get_guardrails_engine()
config = engine.resolve_unified(
    workflow_id=..., node_id=..., model_id=...,
    inline_config=..., agent_guardrails_enabled=True,
)
ctx = GuardrailContext(
    execution_id=..., db_execution_id=..., node_execution_id=...,
    workflow_id=..., agent_node_id=..., agent_node_name=..., user_id=...,
)
checkpoint = GuardrailCheckpoint(engine)

# Single call handles evaluate -> report violations -> enforce
result = await checkpoint.check(content, config, "input", ctx, state=guardrails_state)
# Raises GuardrailViolationError in enforce mode if violations block.
# In audit mode, returns result with violations logged but passed=True.
```

### Config Resolution

`engine.resolve_unified()` replaces three separate resolution paths with one call:

| Old Path | When Used | resolve_unified() Equivalent |
|----------|-----------|------------------------------|
| `resolve_config_from_policies()` | Policies only (no inline config) | `inline_config=None` |
| `resolve_config_with_policies()` | Policies + inline agent config | `inline_config=<config>` |
| `resolve_compulsory_only()` | Agent has guardrails disabled | `agent_guardrails_enabled=False` |

### 1. Input Guardrails

**File:** `backend/services/execution/async_agent/executor.py`

Runs in `execute_agent()` between tool resolution and message building.
Uses `checkpoint.check(user_message, config, "input", ctx)`. Checks `user_message` against pattern rules,
LLM Guard input scanners (behavioral detection), and custom ingress filters. If blocked in enforce mode,
raises `GuardrailViolationError`; in audit mode, returns a blocked response without invoking the LLM.

### 2. System Prompt Protection

**File:** `backend/services/execution/async_agent/message_builder.py`

If `behavioral.system_prompt_protection` is enabled, wraps the system prompt with XML instruction-anchoring
delimiters and an anti-override directive. This makes it harder for user input to override core instructions.
(Does not use `GuardrailCheckpoint` — preventive only.)

### 3. Tool Call Guardrails

**File:** `backend/services/execution/async_agent/tool_executor.py`

Runs in `_execute_single_tool()` with four checkpoint types:

- **`tool_call`** — Validates tool arguments against `ToolCallPolicy` (SSRF, SQL, file path, call count)
- **`tool_ingress`** — Runs input guardrails on data sent to the tool
- **`tool_egress`** — Runs output guardrails on data received from the tool (PII deanonymization, content filtering)
- **`tool_injection`** — Behavioral-only scan of tool results for prompt injection before they become ToolMessages fed back to the LLM

If blocked, the tool returns an error message (the LLM sees "Tool call blocked by guardrail policy: [reason]") and a `guardrail_violation` WebSocket event is emitted.

### 3a. Provider Content Filter

**File:** `backend/services/execution/async_agent/executor.py`

When the LLM provider rejects a request due to built-in content safety filters, the system catches the
`BadRequestError`, parses the triggered categories, and uses `GuardrailCheckpoint.report_prebuilt_violations()`
to persist and stream them. Enforcement mode controls whether the execution fails or continues.

### 4. Token Budget

**File:** `backend/services/nodes/executors/agent.py`

Runs in `execute()` after the LLM response is processed. Updates cumulative token usage in `guardrails_state` and checks against budget limits. Uses the engine's `check_token_budget()` directly (cumulative tracking semantics, not enforce/audit).

### 5. Output Guardrails

**File:** `backend/services/nodes/executors/agent.py`

Runs in `execute()` after `_process_agent_response` but before review state. Uses `checkpoint.check(response, config, "output", ctx)`. Three stages:

1. **Pattern rules** — regex matching on output content
2. **Output length check** — max character length from behavioral config
3. **LLM Guard output scanners** — ML-based scanners (toxicity, refusal, sensitive data, relevance, gibberish, bias, factual consistency, deanonymize for vault round-trip)

## Configuration Inheritance

When an agent has `inherit_from_workflow: true` (default), its guardrails config is merged with the workflow-level config:

- Pattern rules are concatenated (workflow rules + agent rules)
- Agent-specific sub-configs (`tool_call_policy`, `token_budget`, `behavioral`) override workflow defaults
- Setting `inherit_from_workflow: false` uses only the agent-level config

Resolution is handled by `GuardrailsEngine.resolve_unified()`, which selects the correct
resolution path based on whether the agent has inline config and whether guardrails are enabled.
Compulsory (admin-enforced) policies are always included, even when the agent has guardrails disabled.

## WebSocket Events

All guardrail violations emit a `guardrail_violation` event through the `StreamingEventEmitter`:

```json
{
  "event_type": "guardrail_violation",
  "category": "tool_call",
  "rule_name": "ssrf_blocked_ip",
  "message": "Hostname 'localhost' resolves to blocked IP 127.0.0.1",
  "severity": "block",
  "action_taken": "blocked",
  "agent_id": "agent-1",
  "agent_name": "Research Agent",
  "tool_name": "http_request"
}
```

## Example Configuration

```python
from backend.models.workflow.configs.guardrails import (
    GuardrailsConfig,
    PatternRule,
    PatternEntry,
    ToolCallPolicy,
    TokenBudget,
    BehavioralGuardrails,
    OutputScanners,
)

config = GuardrailsConfig(
    enabled=True,
    enforcement_mode="enforce",

    pattern_rules=[
        PatternRule(
            name="block_pii_ssn",
            patterns=[PatternEntry(label="US SSN", regex=r"\b\d{3}-\d{2}-\d{4}\b")],
            action="redact",
            applies_to="output",
            message="SSN detected in output",
        ),
        PatternRule(
            name="block_profanity",
            patterns=[PatternEntry(label="Profanity", regex=r"\b(badword1|badword2)\b")],
            action="block",
            applies_to="both",
        ),
    ],

    tool_call_policy=ToolCallPolicy(
        allowed_url_patterns=["https://api.example.com/*"],
        allowed_sql_operations=["SELECT"],
        blocked_tables=["users", "credentials"],
        max_tool_calls_per_execution=20,
    ),

    token_budget=TokenBudget(
        max_total_tokens_per_execution=100000,
        max_llm_calls_per_execution=10,
        warn_at_percentage=0.8,
    ),

    behavioral=BehavioralGuardrails(
        detect_prompt_injection="block",
        detect_jailbreak_attempts="block",
        system_prompt_protection=True,
        max_input_length=10000,
        detect_toxicity="warn",
        anonymize_pii="anonymize",
        use_faker=True,
        detect_secrets="block",
        prompt_injection_threshold=0.75,
        jailbreak_threshold=0.75,
        toxicity_threshold=0.5,
    ),

    output_scanners=OutputScanners(
        detect_toxicity="block",
        detect_refusal="warn",
        detect_sensitive_data="warn",
        detect_bias="warn",
        check_relevance="warn",
        toxicity_threshold=0.5,
    ),
)
```

JSON equivalent (as stored in graph data):

```json
{
  "enabled": true,
  "enforcement_mode": "enforce",
  "pattern_rules": [
    {
      "name": "block_pii_ssn",
      "patterns": [{"label": "US SSN", "regex": "\\b\\d{3}-\\d{2}-\\d{4}\\b"}],
      "action": "redact",
      "applies_to": "output",
      "message": "SSN detected in output",
      "preset_id": ""
    }
  ],
  "tool_call_policy": {
    "allowed_url_patterns": ["https://api.example.com/*"],
    "allowed_sql_operations": ["SELECT"],
    "blocked_tables": ["users", "credentials"],
    "max_tool_calls_per_execution": 20
  },
  "token_budget": {
    "max_total_tokens_per_execution": 100000,
    "max_llm_calls_per_execution": 10,
    "warn_at_percentage": 0.8
  },
  "behavioral": {
    "detect_prompt_injection": "block",
    "detect_jailbreak_attempts": "block",
    "system_prompt_protection": true,
    "max_input_length": 10000,
    "max_output_length": 100000,
    "detect_toxicity": "warn",
    "anonymize_pii": "anonymize",
    "use_faker": true,
    "detect_secrets": "block",
    "ban_topics": [],
    "allowed_languages": [],
    "detect_gibberish": "off",
    "ban_code": "off",
    "max_input_tokens": null,
    "prompt_injection_threshold": 0.75,
    "jailbreak_threshold": 0.75,
    "toxicity_threshold": 0.5
  },
  "output_scanners": {
    "detect_toxicity": "block",
    "detect_refusal": "warn",
    "detect_sensitive_data": "warn",
    "ban_topics": [],
    "allowed_languages": [],
    "check_relevance": "warn",
    "detect_gibberish": "off",
    "ban_competitors": [],
    "detect_bias": "warn",
    "check_factual_consistency": "off",
    "toxicity_threshold": 0.5
  }
}
```

## Frontend UI

Guardrails are configured through a card-based builder UI embedded in the **Guardrail Policies** page and the agent node properties panel.

### Key Frontend Files

| File | Purpose |
|------|---------|
| `frontend/src/types/guardrails.ts` | TypeScript types + defaults mirroring backend dataclasses |
| `frontend/src/types/guardrail-items.ts` | `GuardrailItem` discriminated union + per-type config interfaces |
| `frontend/src/lib/guardrail-item-mapper.ts` | Bidirectional mapper (`configToItems` / `itemsToConfig`) |
| `frontend/src/components/core/guardrails/GuardrailBuilder.tsx` | Full policy editor with guard cards, catalog, sandbox |
| `frontend/src/components/core/guardrails/GuardrailCard.tsx` | Individual guard configuration (toggle, threshold, scope) |
| `frontend/src/components/core/guardrails/PIIEntitySelector.tsx` | PII entity tag input with compliance presets (GDPR, HIPAA, PCI-DSS, CCPA, PIPEDA) |
| `frontend/src/components/core/guardrails/GuardrailCatalogModal.tsx` | Browse and add guards from the catalog |
| `frontend/src/components/core/guardrails/catalog.ts` | Guard definitions grouped by category |
| `frontend/src/constants/pii-entity-types.ts` | All 38+ Presidio entity types with categories |
| `frontend/src/constants/pii-compliance-presets.ts` | Compliance framework preset definitions |

### Guardrail Item Types

Each `GuardrailItem` has a `type` discriminator that maps to a section of the nested `GuardrailsConfig`:

| Item Type | Category | Maps To |
|-----------|----------|---------|
| `pattern_rule` | Data Protection | `pattern_rules[]` (one item per rule) |
| `llm_judge` | Input Safety | `behavioral.judge_llm_config` |
| `general_safety` | Input Safety | `behavioral.system_prompt_protection`, length limits |
| `llm_guard_adversarial` | Input Safety | `behavioral.detect_prompt_injection`, `detect_jailbreak_attempts` |
| `llm_guard_pii` | Input Safety | `behavioral.anonymize_pii`, `use_faker`, `pii_entity_types` |
| `llm_guard_input_content` | Input Safety | `behavioral.detect_toxicity`, `detect_gibberish`, `ban_code` |
| `llm_guard_input_policy` | Input Safety | `behavioral.ban_topics`, `allowed_languages`, `detect_secrets`, `max_input_tokens` |
| `llm_guard_output_quality` | Output Safety | `output_scanners.detect_refusal`, `check_relevance`, `check_factual_consistency` |
| `llm_guard_output_content` | Output Safety | `output_scanners.detect_toxicity`, `detect_bias`, `detect_gibberish` |
| `llm_guard_output_policy` | Output Safety | `output_scanners.detect_sensitive_data`, `ban_competitors`, `ban_topics`, `allowed_languages` |
| `tool_network` | Tool Restrictions | `tool_call_policy` URL/IP fields |
| `tool_database` | Tool Restrictions | `tool_call_policy` SQL fields |
| `tool_filesystem` | Tool Restrictions | `tool_call_policy` file fields |
| `tool_execution_limits` | Tool Restrictions | `tool_call_policy` limits fields |
| `provider_content_filter` | Provider Safety | `provider_content_filter` |
| `token_budget` | Cost Controls | `token_budget` |
| `custom_filter` | Custom Filters | `custom_filters[]` (one item per filter) |

### Types

- **`frontend/src/types/guardrails.ts`** -- Exports `GuardrailsConfig`, `PatternRule`, `PatternEntry`, `ToolCallPolicy`, `TokenBudget`, `BehavioralGuardrails`, `OutputScanners`, plus defaults (`DEFAULT_GUARDRAILS_CONFIG`, `DEFAULT_TOOL_CALL_POLICY`, etc.)
- **`frontend/src/types/guardrail-items.ts`** -- Exports the `GuardrailItem` discriminated union, per-type config interfaces (e.g. `PatternRuleItemConfig`, `AdversarialItemConfig`), and `SINGLETON_TYPES` (item types that can only appear once)
- **`frontend/src/lib/guardrail-item-mapper.ts`** -- Exports `configToItems()` and `itemsToConfig()` for converting between the flat item list and nested config

### Data Flow

1. `GuardrailsConfig` (nested backend format) is loaded from the API
2. `configToItems()` decomposes the nested config into a flat `GuardrailItem[]` list for the builder UI
3. User adds/removes/configures items via `GuardrailCard` components in the `GuardrailBuilder`
4. `itemsToConfig()` reassembles the flat item list back into a nested `GuardrailsConfig`
5. The config is saved to the backend via `guardrails-api.ts`

## LLM Guard Service Deployment

Heavy ML scanners (prompt injection, toxicity, PII, etc.) can run in three modes, controlled by the `LLM_GUARD_MODE` environment variable:

| Mode | Description | When to use |
|------|-------------|-------------|
| `local` (default) | Scanners run in-process inside the backend container (~3.5 GB RAM) | Single-container deployments |
| `api` | All scanners delegated to a dedicated `llm-guard` service over HTTP | Docker Compose / Kubernetes |
| `hybrid` | Lightweight scanners (TokenLimit, Secrets) run locally; ML scanners forwarded to the service | Optimal latency vs. resource balance |

### Scanner Backend Protocol

All backends implement the `ScannerBackend` protocol defined in `backends/protocol.py`:

```python
class ScannerBackend(Protocol):
    async def scan_input(
        self, content: str, scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None, vault_secret: Optional[str] = None,
    ) -> ScanResult: ...

    async def scan_output(
        self, prompt: str, content: str, scanners: Dict[str, Dict[str, Any]],
        vault_id: Optional[str] = None, vault_secret: Optional[str] = None,
    ) -> ScanResult: ...
```

`ScanResult` aggregates per-scanner `ScannerResult` objects (each with `scanner_name`, `is_valid`, `risk_score`, `sanitized`) plus optional `vault_id`/`vault_secret` for PII anonymization round-trips.

### Service Authentication

When running in `api` or `hybrid` mode, the backend communicates with the `llm-guard` service over HTTP. To prevent unauthorized access to the scanner endpoints, set a shared bearer token:

1. Generate a secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Set `LLM_GUARD_API_KEY=<secret>` in `.env` (or as a Kubernetes secret)
3. Both the backend and `llm-guard` service read this variable -- the backend sends it as `Authorization: Bearer <key>`, and the service rejects requests without a valid token (HTTP 401).

The `/health` endpoint is always unauthenticated so container healthchecks continue working.

If `LLM_GUARD_API_KEY` is unset or empty, authentication is disabled (backward compatible).

### Key Files

| Component | File |
|-----------|------|
| Backend factory (mode selection) | `backend/services/guardrails/backends/__init__.py` |
| Backend protocol | `backend/services/guardrails/backends/protocol.py` |
| Local backend | `backend/services/guardrails/backends/local.py` |
| API backend (HTTP client) | `backend/services/guardrails/backends/api.py` |
| Hybrid backend | `backend/services/guardrails/backends/hybrid.py` |

## What Guardrails Do NOT Replace

- **Review nodes** gate quality and correctness. Guardrails enforce safety. They complement each other.
- **Authentication and RBAC** control who can access workflows. Guardrails control what workflows can do once running.
- **Rate limiting** controls how often workflows run. Guardrails control what happens within a single execution.
