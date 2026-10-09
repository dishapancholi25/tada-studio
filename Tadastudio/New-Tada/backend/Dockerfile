# ---- Stage 1: builder ----
FROM python:3.11-slim AS builder

WORKDIR /app

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install build-time system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first (layer cache for deps)
COPY pyproject.toml uv.lock ./

# Install dependencies only (frozen from lockfile, no dev deps, no project itself)
RUN uv sync --frozen --no-install-project --no-dev

# LLM Guard scanner models (~3.5GB) can be served by the dedicated
# llm-guard-service container (synechron/llm-guard) when LLM_GUARD_MODE=api
# (the default for Docker deploys), in which case no model downloads are
# needed here. For LLM_GUARD_MODE=local, the runtime stage below can bake all
# scanner models into the image via the BAKE_GUARDRAIL_MODELS build arg.

# ---- Stage 2: runtime ----
FROM python:3.11-slim

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    libodbc2 \
    curl \
    ca-certificates \
    # WeasyPrint dependencies for PDF generation
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-noto-core \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver 18 for SQL Server (required by Fabric SQL tools)
RUN apt-get update \
    && apt-get install -y gnupg \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get purge -y gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x LTS (required for MCP STDIO servers)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version \
    && npm --version


# Install build dependencies + CA tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    unixodbc-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ? Copy custom certificates
COPY certs/*.crt /usr/local/share/ca-certificates/
COPY certs/*.cer /usr/local/share/ca-certificates/
COPY certs/*.pem /usr/local/share/ca-certificates/
COPY certs/*.p7b /usr/local/share/ca-certificates/

# ? Register certificates
RUN update-ca-certificates

# ? Set certificate environment variables (IMPORTANT)
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV PIP_CERT=/etc/ssl/certs/ca-certificates.crt


# Copy uv/uvx binaries (needed at runtime for Python-based MCP servers)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy virtual environment from builder stage and set ownership to appuser
COPY --from=builder /app/.venv /app/.venv

# Copy backend source (context is already ./backend from docker-compose)
COPY . ./backend

# Create necessary directories that the app expects and set ownership
RUN mkdir -p logs backend/static workspace/documents workspace/default

# Put the venv on PATH
ENV PATH="/app/.venv/bin:$PATH"

# ---- Optional: pre-bake local-mode guardrail models into the image ----
# When BAKE_GUARDRAIL_MODELS=true (default), download every LLM Guard model
# used by LLM_GUARD_MODE=local into GUARDRAIL_MODELS_DIR so the container never
# fetches a model at runtime (cold-start free, works fully offline). This adds
# several GB to the image and lengthens the build; pass
#   --build-arg BAKE_GUARDRAIL_MODELS=false
# for a lean image when deploying with LLM_GUARD_MODE=api.
# NOTE: the runtime app reads the same GUARDRAIL_MODELS_DIR; if your orchestrator
# (compose/K8s) overrides GUARDRAIL_MODELS_DIR, point it at this same path or a
# volume that contains these files. Downloads use the CA certs registered above.
ARG BAKE_GUARDRAIL_MODELS=true
ENV GUARDRAIL_MODELS_DIR=/app/models/guardrail
RUN if [ "$BAKE_GUARDRAIL_MODELS" = "true" ]; then \
        echo "Baking guardrail models into image at $GUARDRAIL_MODELS_DIR ..." && \
        python backend/scripts/download_all_models.py ; \
    else \
        echo "Skipping guardrail model bake (BAKE_GUARDRAIL_MODELS=$BAKE_GUARDRAIL_MODELS)" ; \
    fi

# Set Python optimizations for production
ENV PYTHONOPTIMIZE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Start the backend in production mode (no auto-reload)
CMD ["/app/.venv/bin/python", "-m", "backend.app", "--no-reload"]