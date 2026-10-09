# Phoenix Integration — Agent Guide

## File Map

| File | Responsibility |
|------|---------------|
| `backend/services/phoenix/__init__.py` | Package marker |
| `backend/services/phoenix/config.py` | `PhoenixConfig` dataclass, `get_phoenix_config()`, `resolve_phoenix_config()`, `resolve_project_id()`, `build_trace_path()` / `build_project_path()` / `build_trace_url()` URL helpers |
| `backend/services/phoenix/instrumentation.py` | OTel bootstrap, `initialize_phoenix_instrumentation()`, `GatedSpanProcessor` (runtime toggle), `ProjectRoutingSpanProcessor` registration |
| `backend/services/phoenix/tracing.py` | `phoenix_workflow_context()` (per-workflow project routing, metadata, tags), `phoenix_root_span()` (OTel trace ID capture), `PhoenixContext` dataclass, `sanitize_project_name()` |
| `backend/services/phoenix/annotations.py` | `annotate_execution_span()` — post-execution span annotations (status, duration, node count), returns `trace_reference` dict |
| `backend/services/phoenix/project_routing.py` | `using_project()` context manager (ContextVar-based, concurrency-safe), `ProjectRoutingSpanProcessor`, `get_current_project()` |
| `backend/services/phoenix/evaluators.py` | `PhoenixEvaluatorBridge`, supplementary faithfulness + tool-selection + LLM judge evals |
| `backend/services/phoenix/dataset_sync.py` | `PhoenixDatasetSync`, experiment mirroring |
| `backend/services/evaluation/phoenix_adapter.py` | `PhoenixTraceAdapter`, span correlation + annotation |
| `backend/app.py` | Calls `initialize_phoenix_instrumentation()` in `lifespan()` |
| `backend/config_service.py` | Exposes Phoenix config to the config API (`phoenix` key in `_get_external_services_config()`) |
| `frontend/src/lib/phoenix-url.ts` | `getPhoenixUrl()`, `usePhoenixConfig()`, `usePhoenixProjectUrl()` hooks, `sanitizeProjectName()` |
| `frontend/src/lib/config-api.ts` | `PhoenixServiceConfig` interface |
| `frontend/src/components/trace/TraceViewer.tsx` | "View in Phoenix" link for workflow traces |
| `frontend/src/components/panels/execution/components/ExecutionDetailsPanel.tsx` | Phoenix link in execution panel |
| `frontend/src/app/evaluations/components/runs/ResultDetailPanel.tsx` | Phoenix link per evaluation result |
| `frontend/src/app/evaluations/components/runs/RunDetailView.tsx` | Phoenix project link on run view |
| `frontend/src/components/settings/tabs/ExternalServicesTab.tsx` | Phoenix settings UI (enable/disable, endpoint, project, API key, UI URL) |

## How to Add/Modify Phoenix Config Safely

- Config is read from the `system_settings` DB table first, falling back to environment variables (via `_get_setting()` in `config.py`)
- This allows runtime toggles via the Settings UI without restarting the backend
- Per-run overrides use `resolve_phoenix_config(override_dict)` — the `enabled` field uses permissive merge (either side can enable)
- Never hardcode URLs; use `PhoenixConfig.client_base_url` for browser links and `PhoenixConfig.api_base_url` for server-to-server calls
- Eval-specific fields: `eval_penalty_enabled`, `eval_faithfulness_enabled`, `eval_tool_selection_enabled`, `eval_llm_judge_enabled`, `eval_model_deployment_id`

## How Instrumentation Is Initialised

- `backend/app.py` `lifespan()` calls `initialize_phoenix_instrumentation()` after DB init and settings sync
- The function is idempotent (guarded by `_initialized` module-level flag)
- It skips silently when `PHOENIX_ENABLED` is false or `PHOENIX_ENDPOINT` is empty
- It catches all exceptions and logs a warning — it never raises
- Installs a `GatedSpanProcessor` that checks `get_phoenix_config().enabled` on every span export — disabling Phoenix at runtime stops new spans without a restart
- Registers a `ProjectRoutingSpanProcessor` that stamps `openinference.project.name` from a `ContextVar` onto each span — safe for concurrent asyncio tasks

## How Per-Workflow Project Routing Works

1. `phoenix_workflow_context()` in `tracing.py` wraps each workflow execution
2. It calls `using_project(sanitized_name)` to set a `ContextVar` with the workflow's project name
3. The `ProjectRoutingSpanProcessor` reads this `ContextVar` on every `on_start` and stamps `openinference.project.name` onto the span's resource
4. `phoenix_root_span()` creates an OTel root span scoping the streaming execution, capturing `trace_id` and `span_id` for deep-linking
5. Metadata (`agentic_studio.execution_id`, `agentic_studio.workflow_id`, etc.) is attached via `using_metadata()` and propagated to all child spans

## How Evaluation Trace Correlation Works

1. During evaluation execution, each test case run is wrapped in `phoenix_workflow_context()` which tags all spans with `agentic_studio.execution_id` via OpenInference metadata
2. After scoring, `PhoenixTraceAdapter.export_run_traces()` queries Phoenix for spans matching that ID using `client.spans.get_spans_dataframe(query=SpanQuery().where("metadata['agentic_studio.execution_id'] == '...'"))`
3. Matched spans are annotated with the five pillar scores via `client.spans.log_span_annotations_dataframe()`
4. The resulting `trace_reference` dict (`{project, trace_id, span_id, execution_id, path}`) is returned and persisted on the `EvaluationResult` model

## How `trace_reference` and `external_eval_summary` Reach the Frontend

- `trace_reference` is stored on `EvaluationResult` (DB model), serialised in `backend/api/evaluation/routes.py`, typed in `backend/api/evaluation/schemas.py`, and consumed by `frontend/src/lib/evaluation-api.ts`
- `external_eval_summary` is stored on `EvaluationRun`, serialised similarly
- `frontend/src/lib/phoenix-url.ts` `getPhoenixUrl()` resolves the display URL from `trace_reference.url` (priority 1), then trace-id deep-link (priority 2), then project-level fallback (priority 3)

## How Post-Execution Annotations Work

After a workflow completes, `annotate_execution_span()` in `annotations.py`:

1. Queries Phoenix for the root span matching `agentic_studio.execution_id`
2. Adds an "Execution Summary" annotation with status, duration, node count, and trigger type
3. Returns a `trace_reference` dict (`{project, trace_id, span_id, execution_id, path}`) persisted on the execution record

## How to Debug Missing Phoenix Links in the UI

1. Confirm `PHOENIX_ENABLED=true` and `PHOENIX_ENDPOINT` is set — check backend startup logs for `"Phoenix OTel instrumentation registered"`
2. Confirm `PHOENIX_UI_URL` is set (or that `PHOENIX_ENDPOINT` ends with `/v1/traces` so `client_base_url` can be derived)
3. Check that spans are arriving in Phoenix UI after running a workflow — they should appear under a project named after the workflow
4. For evaluation links: check that `agentic_studio.execution_id` is present in span metadata; check backend logs for `"Phoenix trace export completed"` with `correlated_count > 0`
5. If `correlated_count=0`, the span query returned empty — spans may not have been emitted or the metadata key is missing

## Best-Effort / Non-Fatal Semantics

- Every Phoenix call is wrapped in `try/except`; failures log at `WARNING` level and return empty/skipped results
- Never add `raise` inside Phoenix service code
- Never make Phoenix a dependency of evaluation correctness

## Common Pitfalls

| Pitfall | Correct approach |
|---------|-----------------|
| Confusing `PHOENIX_ENDPOINT` (OTLP, `/v1/traces`) with `PHOENIX_UI_URL` (base URL for UI/client) | Use `PhoenixConfig.client_base_url` for REST client; use `endpoint` only for `phoenix.otel.register()` |
| Using undocumented `phoenix.client.Client` constructor signatures | Always use `Client(base_url=...)` with explicit keyword args |
| Assuming Phoenix failures should block evaluation runs | All Phoenix code is non-fatal; wrap in try/except |
| Forgetting that `trace_reference.url` is the canonical link | `getPhoenixUrl()` in `phoenix-url.ts` already handles priority ordering |
| Calling `initialize_phoenix_instrumentation()` more than once | The function is idempotent; safe to call multiple times |
