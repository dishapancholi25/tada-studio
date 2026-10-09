# Development Environment

## Docker Compose (Recommended)

### Create Configuration

Copy `.env.example` to `.env` and update as required for your environment.

For example, to run against a local PostgreSQL instance and Azure OpenAI service:

```dotenv
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_API_VERSION=your_api_version
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/langgraph?sslmode=disable # suitable for local dev
CREDENTIAL_ENCRYPTION_KEY=your_32_byte_encryption_key # See .env.example for details of how to generate
DEV_USER_EMAIL=your.email@example.com
DEV_USER_NAME=Your Name
```

### Run the Application

```bash
docker compose -f docker-compose.yml up --build
```

> Note: omit `--build` to use existing images.

### Access the Application

The application will be available at <http://localhost:3000>

### Additional Services

| File                            | Purpose                                                                              |
|---------------------------------|--------------------------------------------------------------------------------------|
| docker-compose.yml              | Launches frontend, backend and PostgreSQL services for local development             |
| docker-compose.demoapi.yml      | Launches the DemoAPI service, used to simulate third party APIs in example workflows |

---

## Local Development (Without Docker)

Run the backend and frontend as separate processes for faster iteration.

### Prerequisites

- Python 3.11+
- Node 18+
- PostgreSQL running locally (or use `docker compose up postgres` to start just the database)

### Backend

```bash
# Install dependencies
pip install -e ".[dev]"

# Start the backend (with auto-reload)
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # Dev server on :3000 with Turbopack
```

The frontend dev server proxies `/api/*` requests to `localhost:8000` via Next.js rewrites, so no nginx is required locally.

---

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Backend won't start | Verify `DATABASE_URL` is set and PostgreSQL is reachable |
| `No LLM provider configured` | Ensure at least one of `AZURE_OPENAI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` is set |
| 502 Bad Gateway from nginx | Backend may still be starting — check `docker compose logs backend` |
| Auth failures on Azure deployment | See [OAuth2 Proxy / Azure Setup](./02-oauth2-proxy-azure-setup.md) |

For configuration details see [Architecture: Configuration](../architecture/05-configuration.md).
