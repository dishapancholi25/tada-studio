"""Execution configuration module.

Simplified configuration for the execution engine.
"""

import os
from urllib.parse import quote_plus

from .logging import get_logger


logger = get_logger("execution_config")


# Execution modes removed in Phase 4 - simplified to production defaults


# Feature flags removed in Phase 4 - all features now enabled by default
# Migration to native LangGraph is complete


class ExecutionConfig:
    """Configuration for the execution engine."""

    @staticmethod
    def get_execution_engine_type() -> str:
        """Get the execution engine type."""
        return "execution_engine"

    # ------------------------------------------------------------------ #
    # Streaming configuration
    # ------------------------------------------------------------------ #
    @staticmethod
    def enable_streaming() -> bool:
        """Whether LangGraph streaming is enabled."""
        return os.getenv("ENABLE_STREAMING", "true").lower() == "true"

    @staticmethod
    def get_stream_modes() -> list[str]:
        """
        Stream modes to request from LangGraph.
        Accepts comma-separated env STREAM_MODES (e.g. "updates,messages,custom").
        Defaults to a full-fidelity set that includes state updates, token streams,
        and custom tool progress.
        """
        raw = os.getenv("STREAM_MODES")
        if raw:
            modes = [m.strip() for m in raw.split(",") if m.strip()]
            return modes or ["updates"]
        return ["updates", "messages", "custom"]

    @staticmethod
    def include_subgraphs() -> bool:
        """Whether to include subgraph events in the stream."""
        return os.getenv("STREAM_INCLUDE_SUBGRAPHS", "true").lower() == "true"

    @staticmethod
    def use_checkpointing() -> bool:
        """Check if checkpointing is enabled (default: true)."""
        return os.getenv("ENABLE_CHECKPOINTING", "true").lower() == "true"

    @staticmethod
    def use_memory() -> bool:
        """Check if memory system is enabled globally."""
        return os.getenv("ENABLE_MEMORY_SYSTEM", "true").lower() == "true"

    @staticmethod
    def wiki_enabled() -> bool:
        """Check if wiki feature is enabled.

        When disabled, wiki routes will return 404 Not Found.
        This is a security control - hiding navigation alone is not sufficient.
        """
        return os.getenv("ENABLE_WIKI", "true").lower() == "true"

    # ------------------------------------------------------------------ #
    # For Each iteration ceilings
    # ------------------------------------------------------------------ #
    # These are system-level hard limits. A workflow author can lower their
    # own For Each limits, but cannot exceed these - otherwise the per-node
    # "safety cap" is only a suggestion and a single node can fan out
    # unbounded work.
    @staticmethod
    def get_for_each_max_items() -> int:
        """Hard ceiling on items a single For Each node may iterate.

        Returns:
            Positive item ceiling (default 5000)
        """
        return ExecutionConfig._positive_int_env("FOR_EACH_MAX_ITEMS", 5000)

    @staticmethod
    def get_for_each_max_concurrency() -> int:
        """Hard ceiling on concurrent iterations of a single For Each node.

        Bounds simultaneous LLM/API calls and in-flight iteration state.

        Returns:
            Positive concurrency ceiling (default 20)
        """
        return ExecutionConfig._positive_int_env("FOR_EACH_MAX_CONCURRENCY", 20)

    @staticmethod
    def _positive_int_env(name: str, default: int) -> int:
        """Read a positive integer environment variable.

        Falls back to the default when unset, unparseable or non-positive, so
        a misconfigured value can never disable the limit it guards.

        Args:
            name: Environment variable name
            default: Value to use when unset or invalid

        Returns:
            The configured value, or the default
        """
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            value = int(raw)
        except (TypeError, ValueError):
            logger.warning(
                "%s=%r is not an integer; falling back to %d", name, raw, default
            )
            return default
        if value < 1:
            logger.warning(
                "%s=%d must be >= 1; falling back to %d", name, value, default
            )
            return default
        return value

    @staticmethod
    def get_postgres_connection_string() -> str:
        """Get PostgreSQL connection string for checkpointing."""
        # Try DATABASE_URL first (standard for most deployments)
        conn_string = os.getenv("DATABASE_URL")

        if not conn_string:
            # Try specific connection string
            conn_string = os.getenv("EXECUTION_POSTGRES_CONNECTION")

        if not conn_string:
            # Build from components
            pg_host = os.getenv("KEY_POSTGRES_HOST", "localhost")
            pg_dbname = os.getenv("KEY_POSTGRES_DBNAME", "langgraph")
            pg_user = os.getenv("KEY_POSTGRES_USER", "postgres")
            pg_password = os.getenv("KEY_POSTGRES_PASSWORD", "postgres")
            pg_port = os.getenv("KEY_POSTGRES_PORT", "5432")
            pg_sslmode = os.getenv("KEY_POSTGRES_SSLMODE", "prefer")

            conn_string = (
                f"postgresql://{quote_plus(pg_user)}:{quote_plus(pg_password)}@{pg_host}:{pg_port}/{pg_dbname}"
                f"?sslmode={pg_sslmode}"
            )

        return conn_string


def create_execution_engine(graph_manager):
    """Create the execution engine."""
    from backend.services.execution import ExecutionEngine

    logger.info("Creating execution engine")
    return ExecutionEngine(graph_manager)
