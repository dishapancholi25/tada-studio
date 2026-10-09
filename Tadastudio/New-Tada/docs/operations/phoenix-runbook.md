# Phoenix Runbook

## Local Development Startup

Phoenix is defined in `docker-compose.yml` as the `phoenix` service, image `arizephoenix/phoenix:latest`, port `6006:6006`, volume `phoenix-data`.

For development with PostgreSQL-backed Phoenix and Nginx proxy, use `docker-compose.dev.yml` which builds from a local `../phoenix` directory, configures a Phoenix-specific PostgreSQL database, and routes `/phoenix` through Nginx on port 8080.

Start Phoenix:

```bash
# Phoenix only (production image)
docker compose up phoenix

# Full stack (includes Phoenix)
docker compose up

# Development stack (with PostgreSQL backend and Nginx proxy)
docker compose -f docker-compose.dev.yml up
```

Set in `.env`:

```bash
PHOENIX_ENABLED=true
PHOENIX_ENDPOINT=http://phoenix:6006/v1/traces
PHOENIX_UI_URL=http://localhost:6006
PHOENIX_PROJECT_NAME=agentic-studio
```

> **Note:** When using `docker-compose.dev.yml` with Nginx proxy, set `PHOENIX_UI_URL=http://localhost:8080/phoenix` instead, since Phoenix is accessed through the Nginx reverse proxy.

## Runtime Configuration

Phoenix settings can be changed at runtime via **Settings → External Services → Phoenix** in the UI. Changes are persisted to the `system_settings` database table and take effect without restarting the backend.

The `GatedSpanProcessor` checks `get_phoenix_config().enabled` on every span export, so disabling Phoenix in the UI immediately stops new spans from being sent.

## Validating Phoenix Locally

1. **UI reachable**: `curl http://localhost:6006/healthz` returns 200
2. **Backend instrumentation active**: look for `"Phoenix OTel instrumentation registered (project=agentic-studio, endpoint=http://phoenix:6006/v1/traces)"` in backend logs
3. **Spans arriving**: run any workflow, then open `http://localhost:6006` and navigate to the project named after your workflow (workflows are routed to per-workflow Phoenix projects)
4. **GatedSpanProcessor active**: look for `"GatedSpanProcessor installed"` in backend debug logs
5. **Project routing active**: look for `"ProjectRoutingSpanProcessor registered"` in backend debug logs

## Configuration Checklist

| Variable | Example value | Notes |
|----------|--------------|-------|
| `PHOENIX_ENABLED` | `true` | Master toggle (also settable via UI) |
| `PHOENIX_ENDPOINT` | `http://phoenix:6006/v1/traces` | OTLP collector URL (used by OTel exporter) |
| `PHOENIX_PROJECT_NAME` | `agentic-studio` | Default project; workflows override this with per-workflow projects |
| `PHOENIX_API_KEY` | _(empty for local)_ | Required only if Phoenix auth is enabled |
| `PHOENIX_UI_URL` | `http://localhost:6006` | Base URL for deep-links and REST client |

### Evaluation Configuration

These control the supplementary Phoenix evaluators that run alongside the built-in 4-pillar scoring:

| Variable | Default | Notes |
|----------|---------|-------|
| `PHOENIX_EVAL_FAITHFULNESS_ENABLED` | `true` | Run hallucination/faithfulness evaluator |
| `PHOENIX_EVAL_TOOL_SELECTION_ENABLED` | `true` | Run tool-selection evaluator |
| `PHOENIX_EVAL_LLM_JUDGE_ENABLED` | `false` | Run Phoenix LLM quality judge (supplementary) |
| `PHOENIX_EVAL_PENALTY_ENABLED` | `false` | Apply quality penalty for low-faithfulness results |
| `PHOENIX_EVAL_MODEL_DEPLOYMENT_ID` | _(empty)_ | LLM deployment used by Phoenix evaluators |

## Troubleshooting

### Phoenix UI Not Reachable

- Check container is running: `docker compose ps phoenix`
- Check port binding: `docker compose logs phoenix`
- Verify healthcheck: `curl http://localhost:6006/healthz`

### No Spans Arriving

- Confirm `PHOENIX_ENABLED=true` and `PHOENIX_ENDPOINT` is correct
- Check backend logs for `"Phoenix instrumentation skipped"` — indicates disabled or missing endpoint
- Confirm `openinference-instrumentation-langchain` is installed (`pip show openinference-instrumentation-langchain`)
- Confirm `phoenix.otel` is installed (`pip show arize-phoenix-otel`)

### Spans Arriving in Wrong Project

- Workflows are routed to per-workflow Phoenix projects via `ProjectRoutingSpanProcessor`
- If spans appear in the default project instead, check for `"ProjectRoutingSpanProcessor registered"` in startup logs
- If missing, `opentelemetry-sdk` or `openinference-semantic-conventions` may not be installed

### Instrumentation Skipped Due to Missing Config/Packages

- Backend logs will show `"Phoenix instrumentation skipped (disabled or no endpoint)"` or `"phoenix.otel not installed, skipping instrumentation"`
- Install missing packages per `backend/pyproject.toml`

### No Phoenix Links in Frontend

- Confirm `PHOENIX_UI_URL` is set and accessible from the browser (not just from the backend container)
- Confirm `PHOENIX_ENABLED=true` is visible to the config API (`GET /api/config/environment`)
- Check `trace_reference` field on evaluation results via the API

### Evaluation Annotations Missing

- Check backend logs for `"Phoenix trace export completed for run ... correlated=0"` — means span correlation failed
- Ensure `agentic_studio.execution_id` is being set in span metadata (this is handled by `phoenix_workflow_context()` in `tracing.py`)
- Confirm `PHOENIX_UI_URL` or derivable base URL is configured (required for REST client)

### Dataset/Experiment Sync Missing or Partial

- Check backend logs for `"Phoenix dataset creation failed"` or `"Phoenix experiment creation failed"`
- `PhoenixDatasetSync` is idempotent — re-running the evaluation will retry if `phoenix_experiment_name` is not yet in `external_eval_summary`
- Confirm `arize-phoenix-client` is installed

### Phoenix Disabled at Runtime but Spans Still Flowing

- The `GatedSpanProcessor` checks `enabled` on every `on_end()` call
- If config read fails (e.g. DB unavailable), it allows spans through as a safety measure
- Restart the backend to fully stop instrumentation

## Deployment Notes

Phoenix deployment manifests are not yet present in the GitOps repository. Before cluster rollout, a Phoenix `Deployment`, `Service`, and `PersistentVolumeClaim` must be added to the appropriate Kustomize overlay.

Follow the GitOps procedure in `docs/for-agents/RELEASE_AND_DEPLOYMENT.md` — always deploy UAT first, confirm healthy, then promote to production.

Phoenix environment variables must be added to the Kubernetes `ConfigMap` / `Secret` for the `agent-designer` namespace.

## Health / Readiness Checks

- Phoenix exposes `GET /healthz` — use this for liveness/readiness probes
- **Success indicators**: HTTP 200 from `/healthz`, spans visible in UI after a workflow run, backend logs show `"Phoenix OTel instrumentation registered"`
