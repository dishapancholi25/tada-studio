# Repository Guidelines

## Project Structure & Module Organization

- `backend/` houses the LangGraph-driven API; `app.py` exposes FastAPI, core logic sits in `graph_manager.py`, and
  supporting services live under `services/` (although this refactor hasn't been fully completed). Domain tests reside
  in `backend/test_*.py`.
- `frontend/` contains the Next.js UI (`src/app`, `src/components`) with shared assets in `public/`.
- `docs/` captures architecture decisions and rollout plans referenced during onboarding and reviews.
- `workspace/` retains persisted workflow graphs and document uploads during development; treat it as local state only
  please.
- Docker compose manifests (`docker-compose.*.yml`) describe deployment targets; adjust environment variables per
  `README.md`.

### build

## Build, Test, and Development Commands

Run npm run build to verify changes to the frontend. Frontend testing.

## Coding Style & Naming Conventions

- Python code uses 4-space indentation, `snake_case` for functions and `PascalCase` classes; mirror existing names such
  as `GraphData` and `ToolConfig`.
- Type hints are expected on new public functions, aligned with data models in `backend/enhanced_nodedata.py`.
- Frontend components follow the Next.js conventions: `PascalCase` components, `camelCase` hooks/utilities, and
  colocated styles via Tailwind classes.
- Follow best Python, FastAPI, Next.js and LangGraph practices. Be preventitive about Pylint Javascript errors/issues,

## Phoenix Observability

- `backend/services/phoenix/` contains the Phoenix OTel integration: `config.py` (configuration), `instrumentation.py` (OTel bootstrap), `evaluators.py` (supplementary evaluators), and `dataset_sync.py` (experiment mirroring).
- Phoenix documentation: `docs/for-agents/PHOENIX.md` (agent guide), `docs/architecture/phoenix-integration.md` (ADR), `docs/operations/phoenix-runbook.md` (runbook).
- Docker Compose includes a `phoenix` service for local observability on port 6006.

## Security & Configuration Tips

- Load secrets through environment variables consumed by `backend/config_service.py` and the docker compose files; never
  commit `.env` values.
- Scrub workflow exports before sharing—node metadata stored under `workspace/` can contain credentials.

## Release and Deployment

- See `docs/for-agents/RELEASE_AND_DEPLOYMENT.md` for full instructions on releasing and deploying new versions.
- Deployments run on AKS in the `agent-designer` namespace across UAT (`SHAREDSERVICES-01-AKS-UAT`) and
  production (`SHAREDSERVICES-01-AKS-PROD`) kubectl contexts.
- Always restart UAT first and confirm healthy before restarting production.
