# Configuration

The application is primarily configured via environment variables. Copy `.env.example` to `.env` and customize for your deployment.

## Quick Start

**Minimum required configuration:**

1. At least one LLM provider (Azure OpenAI, OpenAI, or Anthropic)
2. Database connection (DATABASE_URL or KEY_POSTGRES_* variables)
3. Credential encryption key (for production)

## Authentication & Authorization

### RBAC (Role-Based Access Control)

Controls user access levels and permissions throughout the application.

#### User Roles

```bash
# Default role for new users on first login
# Options: PENDING, USER, ADMIN
# Default: USER (backward compatible)
DEFAULT_USER_ROLE=USER
```

- **PENDING**: User account requires admin approval before access
- **USER**: Standard access to workflows, document management, and tools
- **ADMIN**: Full access including user management and system configuration

#### Admin Configuration

```bash
# Option 1: Admin group from OAuth provider (recommended for SSO)
ADMIN_GROUP=admins

# Option 2: Comma-separated list of admin user emails
ADMIN_USERS=admin1@example.com,admin2@example.com
```

**Note:** Users configured via `ADMIN_USERS` or matching `ADMIN_GROUP` are automatically assigned ADMIN role regardless of `DEFAULT_USER_ROLE`.

#### Feature Access Control

```bash
# Cache TTL for feature permissions (seconds)
# Default: 300 (5 minutes)
FEATURE_ACCESS_CACHE_TTL_SECONDS=300
```

- Lower values: Faster permission updates, higher database load
- Higher values: Better performance, slower permission propagation

### Development Authentication

```bash
# Skip authentication for local development
SKIP_AUTH=true
DEV_USER_EMAIL=example@synechron.com
DEV_USER_NAME="Example User"
```

⚠️ **Never enable `SKIP_AUTH=true` in production!**

## LLM Provider Configuration

At least one LLM provider must be configured for the application to function.

### Azure OpenAI (Recommended for Enterprise)

```bash
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_API_VERSION=2023-05-15
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

**Use when:** You have Azure Enterprise Agreement or prefer Azure's compliance/security features.

### OpenAI

```bash
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_VERSION=2023-05-15
OPENAI_DEPLOYMENT_NAME=gpt-4
OPENAI_ENDPOINT=https://api.openai.com/
OPENAI_BASE=https://api.openai.com/
KEY_OPENAI_API_EMBEDDING_MODEL=text-embedding-3-large
```

**Use when:** Direct OpenAI access is preferred or Azure OpenAI is not available.

### Anthropic (Claude)

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key
```

**Use when:** You want to use Claude models for specific workflows.

### Azure OpenAI PTU (Gateway / IBM Integration)

For deployments fronted by an API gateway (e.g. Mashreq/IBM gateway) that uses OAuth2 client-credentials authentication instead of API keys. This provider is configured per model deployment via the Settings UI rather than environment variables.

**Key differences from standard Azure OpenAI:**

- Authentication via OAuth2 `client_credentials` flow (bearer token, no API key)
- Custom gateway headers (`clientid`, `X-USER-ID`) attached to every request
- Streaming is not supported (non-streaming calls only)
- TLS verification disabled by default for internal-CA certificates

**Configuration** is stored in model deployment records (Settings → LLM Providers → Add Deployment):

| Field | Purpose |
|-------|---------|
| `token_url` | OAuth2 token endpoint |
| `client_id` | Gateway client ID |
| `client_secret` | Gateway client secret (encrypted) |
| `oauth_scope` | OAuth scope for token request |
| `endpoint` | Gateway base URL |
| `deployment_name` | Azure OpenAI deployment (e.g. `gpt-4.1`) |
| `api_version` | Azure API version |
| `x_user_id` | User identifier header value |
| `verify_ssl` | Whether to verify TLS certificates (default: false) |

**Use when:** Your organisation routes Azure OpenAI traffic through an API gateway that requires OAuth2 authentication and custom headers.

**Note:** Multiple providers can be configured simultaneously. Users can select which provider to use per workflow.

## Database Configuration

PostgreSQL database with vector extension (pgvector) for document embeddings.

### Option 1: Single Connection String (Recommended)

```bash
# Format: postgresql+psycopg2://user:password@host:port/database?sslmode=require
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/langgraph?sslmode=prefer
```

**Benefits:**

- Simpler configuration
- Easier to override in Kubernetes ConfigMaps
- Preferred for production deployments

### Option 2: Individual Components

```bash
KEY_POSTGRES_HOST=localhost
KEY_POSTGRES_DBNAME=langgraph
KEY_POSTGRES_USER=postgres
KEY_POSTGRES_PASSWORD=postgres
KEY_POSTGRES_PORT=5432
KEY_POSTGRES_SSLMODE=prefer
```

**Note:** Ignored if `DATABASE_URL` is set.

### Database Features

```bash
# Enable workflow state persistence (recommended)
ENABLE_POSTGRES_CHECKPOINTING=true
```

**Benefits of checkpointing:**

- Resume interrupted workflows
- Human-in-the-loop approvals
- Email response triggers
- Debug workflow execution

## Security Configuration

### Credential Encryption

```bash
# Required for production - encrypts stored credentials
CREDENTIAL_ENCRYPTION_KEY=your_generated_encryption_key
```

**Generate a key:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### MCP Server Security

Controls command execution for Model Context Protocol servers:

```bash
# Allowed commands for stdio MCP servers (comma-separated)
# Default: npx,node,python,python3,python3.11,python3.12,uvx,uv,deno,bun,tsx,ts-node
MCP_ALLOWED_COMMANDS=npx,node,python,python3

# Dangerous characters blocked in commands
# Default: ;|&$`\n\r><()
MCP_DANGEROUS_CHARS_COMMAND=;|&$`\n\r><()

# Dangerous characters blocked in arguments
# Default: ;|&$`\n\r
MCP_DANGEROUS_CHARS_ARGS=;|&$`\n\r
```

⚠️ **Warning:** Only modify these if absolutely necessary. Removing characters reduces security against command injection attacks.

## Feature Flags

Control application behavior and feature availability:

```bash
# Workflow state persistence (recommended: true)
ENABLE_POSTGRES_CHECKPOINTING=true

# Optimized tool execution (recommended: true)
ENABLE_NATIVE_TOOL_NODES=true

# Performance debugging (recommended: false in production)
ENABLE_PERFORMANCE_LOGGING=false

# Email workflow triggers (recommended: true if using email)
EMAIL_CHECKPOINT_ENABLED=true

# Native LangGraph engine (experimental)
USE_LANGGRAPH_ENGINE=false
```

## External Services

### Web Search (Optional)

Required for web search functionality in agent tools:

```bash
TAVILY_API_KEY=your_tavily_api_key
```

### GitHub Integration (Optional)

Required for GitHub-related agent tools:

```bash
GITHUB_PAT=your_github_personal_access_token
```

### Tracing & Observability

#### Phoenix Observability (Recommended — Active Integration)

Phoenix is the primary integrated observability layer, providing LLM trace exploration, span annotations, and evaluation deep-links via OpenTelemetry auto-instrumentation.

```bash
# Master toggle — enables OTel instrumentation and Phoenix integration
PHOENIX_ENABLED=true

# OTLP collector URL — where auto-instrumented spans are sent
# This is the machine-to-machine endpoint used by phoenix.otel.register()
PHOENIX_ENDPOINT=http://phoenix:6006/v1/traces

# Project name — groups traces in the Phoenix UI
PHOENIX_PROJECT_NAME=agentic-studio

# API key — only required if Phoenix authentication is enabled
PHOENIX_API_KEY=

# Human-facing base URL — used for deep-links in the frontend and the REST client
# If not set, derived by stripping /v1/traces from PHOENIX_ENDPOINT
PHOENIX_UI_URL=http://localhost:6006
```

Phoenix settings can also be changed at runtime via **Settings → External Services → Phoenix** in the UI — changes are persisted to the database and take effect without restarting the backend.

#### Phoenix Evaluation Configuration

```bash
# Run hallucination/faithfulness evaluator (default: true)
PHOENIX_EVAL_FAITHFULNESS_ENABLED=true

# Run tool-selection evaluator (default: true)
PHOENIX_EVAL_TOOL_SELECTION_ENABLED=true

# Run Phoenix LLM quality judge — supplementary to built-in judge (default: false)
PHOENIX_EVAL_LLM_JUDGE_ENABLED=false

# Apply quality penalty for low-faithfulness results (default: false)
PHOENIX_EVAL_PENALTY_ENABLED=false

# LLM deployment used by Phoenix evaluators (optional)
PHOENIX_EVAL_MODEL_DEPLOYMENT_ID=
```

All Phoenix features degrade gracefully when not configured — no errors are raised, and evaluation/execution results remain fully functional without Phoenix.

#### Langfuse Observability (Alternative)

Langfuse is an alternative open-source LLM observability platform supported alongside Phoenix. It uses its native SDK with OpenTelemetry export and captures LLM/embedding spans via OpenInference auto-instrumentation.

```bash
# Master toggle — enables Langfuse SDK initialisation
LANGFUSE_ENABLED=true

# Langfuse server URL (self-hosted or cloud)
LANGFUSE_BASE_URL=https://your-langfuse-instance.com

# Authentication credentials (required when enabled)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Project name — groups traces in the Langfuse UI
LANGFUSE_PROJECT_NAME=agentic-studio
```

Langfuse settings can also be changed at runtime via **Settings → External Services → Langfuse** in the UI — changes are persisted to the database and take effect without restarting the backend.

**Use when:** Your team prefers Langfuse's UI, already has a Langfuse instance, or wants an alternative to Phoenix for LLM trace exploration.

**Key differences from Phoenix:**
- Uses the native Langfuse SDK (not raw OTel export)
- Provides per-trace deep-links via `client.get_trace_url()`
- Can run alongside Phoenix simultaneously — both receive spans from the same OpenInference instrumentor
- Non-fatal: missing packages or bad credentials are logged and swallowed

#### LangSmith (Legacy / Optional)

LangSmith configuration remains available for teams that prefer it. Phoenix and Langfuse are now the primary integrated observability layers.

```bash
LANGSMITH_TRACING=false
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=agentic-studio
```

**Use when:** Your team already has LangSmith infrastructure or prefers its managed service model.

## Email Service Configuration

Enables email-based workflow triggers and notifications.

### Mailgun (Recommended)

```bash
EMAIL_PROVIDER=mailgun
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your_mailgun_domain
```

### MailSlurp (Alternative)

```bash
EMAIL_PROVIDER=mailslurp
MAILSLURP_API_KEY=your_mailslurp_api_key
```

### Email Webhooks

```bash
EMAIL_WEBHOOKS_ENABLED=false
EMAIL_WEBHOOK_BASE_URL=http://localhost:8000
```

**Production setup:**

1. Set `EMAIL_WEBHOOKS_ENABLED=true`
2. Configure `EMAIL_WEBHOOK_BASE_URL` to your public URL
3. Register webhook with email provider
4. Enable `EMAIL_CHECKPOINT_ENABLED=true` for workflow pausing

## MCP (Model Context Protocol) Configuration

Optional configuration for MCP server sidecars:

```bash
# Enable MCP sidecar services
MCP_USE_SIDECARS=false

# Sidecar configuration (if enabled)
MCP_SIDECAR_NOTION_TYPE=http
MCP_SIDECAR_NOTION_HOST=localhost
MCP_SIDECAR_NOTION_PORT=8080

# Cloud provider for managed identity
# Options: 'aws', 'azure', 'none'
CLOUD_PROVIDER=none
```

## API Configuration

```bash
# Backend API URL for frontend and external services
API_BASE_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
```

**Production:** Set to your public-facing URL (e.g., `https://api.yourdomain.com`)

## Logging & Monitoring

```bash
# Logging verbosity
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

**Recommendations:**

- Development: `DEBUG` or `INFO`
- Production: `INFO` or `WARNING`
- Troubleshooting: `DEBUG` (temporary)

## Service Configuration Classes

Configuration is managed through service-specific classes in `backend/services/config/`:

- **ExecutionConfig**: Workflow execution engine settings
- **DatabaseConfig**: Database connection pooling and timeouts
- **EmailConfig**: Email service provider settings
- **MetricsConfig**: Performance metrics collection

These are typically auto-configured from environment variables.

## Production Deployment Checklist

- [ ] Set `SKIP_AUTH=false` (or remove variable)
- [ ] Configure `CREDENTIAL_ENCRYPTION_KEY`
- [ ] Use `DATABASE_URL` for database connection
- [ ] Set `DATABASE_URL` with `sslmode=require`
- [ ] Configure at least one LLM provider
- [ ] Set `ENABLE_PERFORMANCE_LOGGING=false`
- [ ] Configure `ADMIN_USERS` or `ADMIN_GROUP`
- [ ] Set appropriate `DEFAULT_USER_ROLE` (PENDING for approval workflow)
- [ ] Set `API_BASE_URL` to public URL
- [ ] Enable TLS/HTTPS for all endpoints
- [ ] Review MCP security settings if using stdio servers
- [ ] Configure Phoenix observability (`PHOENIX_ENABLED`, `PHOENIX_ENDPOINT`, `PHOENIX_UI_URL`) or LangSmith if desired

## Docker Compose Configuration

For Docker deployments, environment variables can be configured in:

1. `.env` file (loaded automatically)
2. `docker-compose.yml` environment section
3. `docker-compose.override.yml` (for local overrides)

**Example docker-compose.override.yml:**

```yaml
version: '3.8'
services:
  backend:
    environment:
      - LOG_LEVEL=DEBUG
      - ENABLE_PERFORMANCE_LOGGING=true
```

## Kubernetes Configuration

**Recommended approach:**

1. Store secrets in Kubernetes Secrets
2. Store non-sensitive config in ConfigMaps
3. Use `DATABASE_URL` format for simpler overrides
4. Mount secrets as environment variables

**Example ConfigMap:**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-studio-config
data:
  LOG_LEVEL: "INFO"
  DEFAULT_USER_ROLE: "PENDING"
  ENABLE_POSTGRES_CHECKPOINTING: "true"
```

## Troubleshooting

### Common Issues

**"No LLM provider configured"**

- Ensure at least one of: `AZURE_OPENAI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` is set

**"Database connection failed"**

- Verify `DATABASE_URL` or `KEY_POSTGRES_*` variables
- Check database is running: `docker compose ps postgres`
- Verify network connectivity and credentials

**"Feature access not updating"**

- Reduce `FEATURE_ACCESS_CACHE_TTL_SECONDS` for faster propagation
- Restart backend services to clear cache

**"Collection name already exists" errors**

- Collection names are globally unique across all users
- Workaround: Prefix collection names with username (e.g., "johndoe-TechnicalDocs")
- See [Issue #195](https://github.com/synechron/agentic-studio/issues/195) for per-user unique names roadmap

## Environment Variable Priority

The Python application resolves configuration in this order (highest to lowest):

1. **System environment variables** — Variables already set in the process environment at startup (includes values injected by Docker `environment:`, Kubernetes Secrets/ConfigMaps, or shell `export`)
2. **`.env` file** — Loaded at startup via python-dotenv; only applied if the variable is not already set in the environment
3. **Default values in code** — Hardcoded defaults used when no environment variable is present

In practice:

- Docker Compose `environment:` and Kubernetes ConfigMaps/Secrets are mechanisms for setting system
  environment variables (priority 1), not a separate layer.
- `.env` file values are silently ignored if the same variable is already in the environment — this is
  intentional so container orchestration can always override local defaults.

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Rotate credentials regularly** - Especially API keys and database passwords
3. **Use managed identities** - In cloud environments (Azure, AWS)
4. **Enable audit logging** - Monitor admin actions and role changes
5. **Restrict admin access** - Use `ADMIN_GROUP` from SSO provider
6. **Use PENDING role** - For user approval workflow in production
7. **Enable MCP command restrictions** - Never disable without careful review

## Related Documentation

- [Running the App](../for-developers/00-running-the-app.md) — Local development and Docker Compose setup
- [OAuth2 Proxy / Azure Deployment](../for-developers/02-oauth2-proxy-azure-setup.md) — Production authentication configuration
- [API Authentication](../for-developers/05-api-authentication.md) — Token types and endpoint requirements
