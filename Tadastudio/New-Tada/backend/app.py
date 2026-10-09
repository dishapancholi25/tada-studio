"""FastAPI application initialization and configuration."""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.config_api import get_config_service
from .api.security import CSPMiddleware, SensitiveHeaderStripMiddleware

# psycopg (used by the LangGraph Postgres checkpointer) cannot run on Windows'
# default ProactorEventLoop; force the SelectorEventLoop policy at import time,
# before any event loop or connection pool is created. No-op on Linux/AKS.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Load environment variables from env file
load_dotenv()

# Local imports that may depend on environment variables
from .services.database import init_db  # noqa: E402
from .log_filters import EndpointFilter  # noqa: E402
from .services.config import setup_logging  # noqa: E402
from .services.dependency_injection import initialize_dependencies  # noqa: E402
from .services.feature_flags import EMAIL_FEATURE_ENABLED  # noqa: E402
from .api.admin.routes import router as admin_router  # noqa: E402
from .api.analytics import router as analytics_router  # noqa: E402
from .api.execution import router as paused_executions_router  # noqa: E402
from .api.http_execution import router as http_execution_router  # noqa: E402
from .api.memory import router as memory_router  # noqa: E402
from .api.model_deployments import router as model_deployment_router  # noqa: E402
from .api.monitoring import router as monitoring_router  # noqa: E402
from .api.tools import document_search_router, web_search_router  # noqa: E402
from .api.trace import router as trace_router  # noqa: E402
from .api.trace import websocket_router as trace_ws_router  # noqa: E402
from .api.websocket import execution_router, http_listener_router  # noqa: E402
from .api.wiki.routes import wiki_router  # noqa: E402
from .api.workflow.publishing import publish_router  # noqa: E402
from .api.workflow.scheduling import schedule_router  # noqa: E402
from .api.auth import router as auth_router  # noqa: E402
from .api.chat import router as chat_router  # noqa: E402
from .api.checkpoints import router as checkpoint_router  # noqa: E402
from .config_api import router as config_router  # noqa: E402
from .api.api_endpoints import router as api_endpoint_router  # noqa: E402
from .api.datasources import router as datasource_router  # noqa: E402
from .api.documents import router as document_router, pat_router as document_pat_router  # noqa: E402
from .api.groups.router import router as groups_router  # noqa: E402
from .api.execution_history import router as execution_history_router  # noqa: E402
from .api.graph import public_router as graph_public_router, router as graph_router  # noqa: E402
from .api.library import router as library_router  # noqa: E402
from .mcp_test_endpoint import mcp_test_router  # noqa: E402
from .api.oauth import mcp_oauth_router, microsoft_oauth_router, notion_oauth_router  # noqa: E402
from .api.user_settings import router as user_settings_router  # noqa: E402
from .api.evaluation import router as evaluation_router  # noqa: E402
from .api.files import router as files_router  # noqa: E402
from .api.guardrails import router as guardrails_router  # noqa: E402
from .api.guardrails.versions.routes import router as guardrail_versions_router  # noqa: E402
from .api.guardrails.feedback.routes import router as guardrail_feedback_router  # noqa: E402
from .api.guardrails.violations.routes import router as guardrail_violations_router  # noqa: E402
from .api.guardrails.compliance.routes import router as guardrail_compliance_router  # noqa: E402
from .api.schemas import router as schemas_router  # noqa: E402
from .api.guardrails.compliance.routes import user_router as guardrail_compliance_user_router  # noqa: E402
from .api.guardrails.sandbox.routes import router as guardrail_sandbox_router  # noqa: E402
from .api.guardrails.metrics.routes import router as guardrail_metrics_router  # noqa: E402
from .api.sharing import router as sharing_router  # noqa: E402
from .api.tutorial import router as tutorial_router  # noqa: E402
from .api.collaboration import collaboration_router  # noqa: E402
from .api.notifications import router as notifications_router  # noqa: E402


setup_logging()

# Don't log health checks
filters = [
    "/health",
    "/health/liveness",
    "/health/readiness",
    "/api/graph/health",
    "/api/monitoring/health",
    "/api/monitoring/health/detailed",
    "/api/tools/document-search/health",
    "/api/tools/web-search/health",
]
logging.getLogger("uvicorn.access").addFilter(EndpointFilter(filters))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events.

    Handles startup tasks including dependency initialization,
    LangGraph engine setup, and database initialization.
    """
    # Startup
    try:
        initialize_dependencies()
        print("Application dependencies initialized")
    except Exception as e:
        print(f"Error initializing dependencies: {e}")
        import traceback

        traceback.print_exc()
        raise

    # Initialize LangGraph engine if enabled
    try:
        from .api.graph import initialize_engine

        if initialize_engine():
            print("LangGraph engine initialized")
    except Exception as e:
        print(f"Error initializing LangGraph engine: {e}")
        import traceback

        traceback.print_exc()

    # Initialize database tables
    try:
        init_db()
        print("Database tables initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize database: {e}")
        print("Execution history features will not be available")

    # Seed built-in guardrail policy packs
    try:
        from .services.guardrails.packs.seeder import seed_built_in_packs

        seed_built_in_packs()
        print("Built-in guardrail policy packs seeded")
    except Exception as e:
        print(f"Warning: Failed to seed built-in guardrail packs: {e}")

    # Initialize one observability provider at startup.
    try:
        from .services.langfuse.config import get_langfuse_env_config
        from .services.phoenix.config import get_phoenix_env_config

        langfuse_config = get_langfuse_env_config()
        phoenix_config = get_phoenix_env_config()

        config_service = get_config_service()
        config_service.update_configuration(
            "external_services.langfuse", "enabled", langfuse_config.enabled
        )
        config_service.update_configuration(
            "external_services.phoenix", "enabled", phoenix_config.enabled
        )
        config_service.sync_db_settings_to_env()



        if langfuse_config.is_configured:
            try:
                from .services.langfuse.instrumentation import initialize_langfuse_instrumentation

                initialize_langfuse_instrumentation(langfuse_config)
                print("Langfuse instrumentation initialized")
            except Exception as e:
                print(f"Warning: Langfuse instrumentation initialization failed: {e}")
            print("Phoenix instrumentation skipped because Langfuse is active")
        elif phoenix_config.enabled and phoenix_config.endpoint:
            try:
                from .services.phoenix.instrumentation import initialize_phoenix_instrumentation

                initialize_phoenix_instrumentation(phoenix_config)
                print("Phoenix instrumentation initialized")
            except Exception as e:
                print(f"Warning: Phoenix instrumentation initialization failed: {e}")
        else:
            print("No observability instrumentation initialized")
    except Exception as e:
        print(f"Warning: Observability instrumentation configuration check failed: {e}")
    
    # Initialize workflow scheduler unless explicitly disabled.
    try:
        from .services.scheduling import is_scheduling_enabled, scheduler_service

        if is_scheduling_enabled():
            scheduler_service.initialize()
            print("Workflow scheduler initialized")
        else:
            print("Workflow scheduler disabled (SCHEDULING_ENABLED is false)")
    except Exception as e:
        print(f"Warning: Scheduler initialization failed: {e}")

    # Reconcile missed evaluation runs (at-most-once delivery)
    try:
        from .services.evaluation.trigger import EvaluationTriggerService

        EvaluationTriggerService().reconcile_missed_runs_on_startup()
        print("Evaluation trigger reconciliation complete")
    except Exception as e:
        print(f"Warning: Evaluation trigger reconciliation failed: {e}")

    # Pre-load guardrail models and sandbox caches.
    # Skip ALL local model loading when using API or hybrid mode — models
    # live in the remote llm-guard service, not in this process.
    import asyncio

    llm_guard_mode = os.environ.get("LLM_GUARD_MODE", "local").lower()
    if llm_guard_mode == "local":
        # Pre-load heavy sandbox modules (Presidio, spaCy, Detoxify) in background
        # so the first guardrail filter execution doesn't pay the model-loading cost.
        try:
            from .services.guardrails.filters.executors.python_sandbox import preload_heavy_modules

            asyncio.get_event_loop().run_in_executor(None, preload_heavy_modules)
            print("Guardrail sandbox module pre-loading started (background)")
        except Exception as e:
            print(f"Warning: Sandbox module pre-loading failed to start: {e}")

        # Pre-load local guardrail models (prompt injection, jailbreak, toxicity, anonymize)
        try:
            from .services.guardrails.local_models import preload_models

            app.state.guardrail_preload_task = asyncio.create_task(
                preload_models(["all"])
            )
            print("Local guardrail models pre-loading started (background, all scanners)")
        except Exception as e:
            print(f"Warning: Local model pre-loading failed to start: {e}")
    else:
        print(f"Skipping local model/sandbox pre-loading (LLM_GUARD_MODE={llm_guard_mode})")

    # Initialize LiteLLM pricing service (background refresh)
    _pricing_scheduler = None
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        from .services.token_counting.litellm_pricing import (
            REFRESH_INTERVAL_HOURS,
            litellm_pricing_service,
        )

        # Fire-and-forget initial remote fetch so it doesn't block startup
        asyncio.create_task(litellm_pricing_service.refresh_pricing_data())

        # Schedule periodic refresh
        _pricing_scheduler = AsyncIOScheduler()
        _pricing_scheduler.add_job(
            litellm_pricing_service.refresh_pricing_data_sync,
            "interval",
            hours=REFRESH_INTERVAL_HOURS,
        )
        _pricing_scheduler.start()
        print(
            f"LiteLLM pricing service initialized (refresh every {REFRESH_INTERVAL_HOURS}h)"
        )
    except Exception as e:
        print(f"Warning: LiteLLM pricing service initialization failed: {e}")

    yield
    # Shutdown
    try:
        if _pricing_scheduler is not None and _pricing_scheduler.running:
            _pricing_scheduler.shutdown(wait=False)
            print("LiteLLM pricing scheduler shutdown complete")
    except Exception:
        pass

    # Workflow scheduler shutdown (no-op if it was never initialized).
    try:
        from .services.scheduling import scheduler_service

        scheduler_service.shutdown()
        print("Workflow scheduler shutdown complete")
    except Exception as e:
        print(f"Warning: Scheduler shutdown error: {e}")

    try:
        from .services.websocket import notifier as ws_notifier

        if ws_notifier:
            await ws_notifier.shutdown()
            print("WebSocket notifier shutdown complete")
    except Exception as e:
        print(f"Warning: WebSocket notifier shutdown error: {e}")

    try:
        from .services.langfuse.instrumentation import shutdown_langfuse

        shutdown_langfuse()
    except Exception as e:
        print(f"Warning: Langfuse shutdown error: {e}")


# Create rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
_docs_prefix = os.getenv("ROOT_PATH", "")
app = FastAPI(
    title="AgenticStudio Builder API",
    description="No-code/Low-code AI workflow builder",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=f"{_docs_prefix}/docs",
    redoc_url=f"{_docs_prefix}/redoc",
    openapi_url=f"{_docs_prefix}/openapi.json",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Content Security Policy middleware for XSS protection
# Set CSP_REPORT_ONLY=true to monitor violations before enforcing
# Set CSP_REPORT_URI to collect violation reports
app.add_middleware(CSPMiddleware)

# ISG Finding 1.9: Strip oauth2-proxy internal headers from responses
# (defense-in-depth — Ingress proxy_hide_header is the primary control)
app.add_middleware(SensitiveHeaderStripMiddleware)

# Mount static files directory
static_dir = Path("backend/static")
if not static_dir.exists():
    static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


app.include_router(graph_public_router)
app.include_router(graph_router)
app.include_router(library_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(execution_history_router)
app.include_router(memory_router)
app.include_router(checkpoint_router)
app.include_router(document_router)
app.include_router(document_pat_router)
app.include_router(groups_router)
app.include_router(datasource_router)
app.include_router(api_endpoint_router)
app.include_router(http_execution_router)
app.include_router(publish_router)
app.include_router(schedule_router)
app.include_router(web_search_router)
app.include_router(document_search_router)
app.include_router(wiki_router)
app.include_router(monitoring_router)
app.include_router(config_router)
app.include_router(paused_executions_router)
if EMAIL_FEATURE_ENABLED:
    from .api.email import router as email_checkpoint_router

    app.include_router(email_checkpoint_router)
else:
    logging.getLogger(__name__).info(
        "Email feature is disabled (coming soon); /api/email routes are not registered"
    )
app.include_router(trace_router)
app.include_router(mcp_test_router)
app.include_router(notion_oauth_router)
app.include_router(mcp_oauth_router)
app.include_router(microsoft_oauth_router)
app.include_router(model_deployment_router)
app.include_router(user_settings_router)
app.include_router(evaluation_router)
app.include_router(files_router)
app.include_router(guardrails_router)
app.include_router(guardrail_versions_router)
app.include_router(guardrail_feedback_router)
app.include_router(guardrail_violations_router)
app.include_router(guardrail_compliance_router)
app.include_router(guardrail_compliance_user_router)
app.include_router(guardrail_sandbox_router)
app.include_router(guardrail_metrics_router)
app.include_router(sharing_router)
app.include_router(schemas_router)
app.include_router(chat_router)
app.include_router(tutorial_router)
# WebSocket routers
app.include_router(execution_router)
app.include_router(http_listener_router)
app.include_router(trace_ws_router)
app.include_router(collaboration_router)
app.include_router(notifications_router)


@app.get("/")
async def root():
    """Return API information and documentation link."""
    return {"message": "AgenticStudio Builder API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    """Health check endpoint for monitoring service availability."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # Check if --no-reload flag is passed
    no_reload = "--no-reload" in sys.argv

    if no_reload:
        print("Running without auto-reload")
        uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=False)
    else:
        # Try to exclude log files - on Windows, we need to be more specific
        uvicorn.run(
            "backend.app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=["backend"],  # Watch backend directory
            reload_excludes=[
                "*.log",
                "*.pyc",
                "__pycache__",
                "logs",
                "workspace",
                "*.db",
                "*.sqlite",
            ],
        )
