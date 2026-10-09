# TADA Studio Documentation

TADA Studio (formerly Agentic Studio) is a no-code/low-code AI workflow builder that lets you create, visualise, and execute
sophisticated AI agent workflows through a visual drag-and-drop interface. It combines LangGraph's state
management, FastAPI, and Next.js to support multi-agent orchestration, real-time streaming, document search
(RAG), real-time collaboration, and checkpoint-based pause/resume execution.

---

## For Users

Documentation for people using TADA Studio to build and run workflows.

| Document | Description |
|----------|-------------|
| [Creating a Workflow](./for-users/01-creating-a-workflow.md) | Step-by-step guide to building and running your first workflow on the canvas |
| [Workflow Library](./for-users/02-workflow-library.md) | Browse, search, run, and clone shared workflows from the Library tab |
| [Publishing a Workflow](./for-users/03-publishing-a-workflow.md) | Expose a workflow as an HTTP endpoint and trigger it with a PAT |
| [Data Sources](./for-users/04-data-sources.md) | Document collections (RAG) and database connections — creating, sharing, and using them in workflows |
| [Evaluations](./for-users/05-evaluations.md) | Systematically test workflows with datasets, score results across quality pillars, and get AI-generated recommendations |
| [Executions](./for-users/06-executions.md) | Live node view, execution history, node trace detail, feedback, LangSmith integration, and trace export |
| [Settings](./for-users/07-settings.md) | API tokens, external services, MCP servers, appearance, and admin settings (model deployments, user management, feature access) |
| [Importing Agents](./for-users/08-importing-agents.md) | Import agent configurations from JSON, including schema reference, validation rules, and examples |
| [User API Tokens](./for-users/09-user-api-tokens.md) | Create and manage Personal Access Tokens (PATs) for authenticating API and CI/CD requests |
| [Phoenix Trace Analysis](./for-users/10-phoenix-trace-analysis.md) | Explore LLM traces, evaluation annotations, and experiments in Phoenix |
| [Guardrails](./for-users/11-guardrails.md) | Configure safety policies, content filtering, and behavioral detection for workflow agents |
| [Real-Time Collaboration](./for-users/12-collaboration.md) | Work on workflows simultaneously with other users — live cursors, conflict-free edits, and access requests |
| [Keyboard Shortcuts](./for-users/13-keyboard-shortcuts.md) | Cross-platform keyboard shortcuts for common canvas and workflow actions |

---

## For Developers

Documentation for engineers deploying, configuring, or extending TADA Studio.

| Document | Description |
|----------|-------------|
| [Running the App](./for-developers/00-running-the-app.md) | Local development setup with Docker Compose or bare-metal |
| [Nginx Setup](./for-developers/01-nginx-setup.md) | Nginx reverse proxy configuration for routing frontend/backend traffic |
| [OAuth2 Proxy / Azure Setup](./for-developers/02-oauth2-proxy-azure-setup.md) | Deploy with Azure AD authentication via oauth2-proxy on Azure Web Apps |
| [Guardrails](./for-developers/03-guardrails.md) | Safety policy enforcement: content filtering, SSRF protection, token budgets, and behavioral detection |
| [Database: Orphaned Workflows Cleanup](./for-developers/04-database-orphaned-workflows-cleanup.md) | Script to find and remove orphaned workflow records in the database |
| [API Authentication](./for-developers/05-api-authentication.md) | Token types (`wf_`, `na_`, JWT, OAuth2 proxy) and which endpoints each can access |

---

## Architecture & Operator Guide

Reference documentation for understanding the system design and operating in production.

| Document | Description |
|----------|-------------|
| [Architecture Overview](./architecture/00-overview.md) | High-level system summary, technology stack, and layer diagram |
| [Architecture Diagrams](./architecture/01-architecture-diagrams.md) | Visual diagrams of the system architecture |
| [Data Flows](./architecture/02-data-flows.md) | How data moves through the system |
| [Design Principles](./architecture/03-design-principles.md) | Core architectural decisions, patterns, and rationale |
| [Architecture Reference](./architecture/04-architecture-reference.md) | Execution flow, WorkflowState, key subsystems, and security architecture |
| [Configuration](./architecture/05-configuration.md) | All environment variables, configuration priority order, and production checklist |
| [Phoenix Integration ADR](./architecture/06-phoenix-integration.md) | Architecture decision record for Phoenix OTel observability |
| [Guardrails & Policies](./architecture/07-guardrails-and-policies.md) | Guardrails engine architecture, 6 interception points, layered policy resolution |
| [Chat UI Design](./architecture/07-chat-ui-design.md) | Design document for the conversational Chat UI feature |
