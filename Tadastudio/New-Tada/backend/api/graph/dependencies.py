"""Shared dependencies for Graph API.

This module provides reusable dependency functions for the Graph API,
including user identification, graph loading, and configuration deserialization.
"""

from datetime import datetime
from typing import Any, Dict

from backend.models.workflow import AgentConfig, ConditionConfig, GraphData, LLMConfig
from backend.services.config import get_logger
from backend.services.dependency_injection import get_graph_manager

from .constants import LOG_PREFIX
from .exceptions import GraphNotFoundError, UnauthorizedError


logger = get_logger(__name__)


def get_user_identifier(current_user: Dict[str, Any]) -> str:
    """Extract user identifier from JWT claims.

    Uses the 'sub' claim which is the unique user identifier used as the
    primary key in the users table. This ensures consistency with how users
    are created via user_sync.py.

    Args:
        current_user: JWT claims dictionary from authentication

    Returns:
        User identifier (sub claim)

    Raises:
        UnauthorizedError: If token is missing user identifier
    """
    user_identifier = current_user.get("sub")
    if not user_identifier:
        logger.error(f"{LOG_PREFIX} Token missing user identifier (sub claim)")
        raise UnauthorizedError("Token missing user identifier")
    return user_identifier


def get_graph_or_404(
    graph_name: str, user_identifier: str, *, reload: bool = False
) -> GraphData:
    """Ensure the graph is loaded for this process, fetching from storage if needed.

    Args:
        graph_name: Name of the graph to load
        user_identifier: User identifier for access control
        reload: If True, force reload from storage

    Returns:
        GraphData object

    Raises:
        GraphNotFoundError: If the graph cannot be found for the user
    """
    graph = None

    if reload:
        logger.info(
            f"{LOG_PREFIX} Force reloading graph '{graph_name}' for user '{user_identifier}'"
        )
        graph = get_graph_manager().load_graph(graph_name, username=user_identifier)
    else:
        # Try to get from cache first
        graph = get_graph_manager().get_graph(graph_name)
        if not graph:
            logger.info(
                f"{LOG_PREFIX} Graph '{graph_name}' not in cache, loading from storage"
            )
            graph = get_graph_manager().load_graph(graph_name, username=user_identifier)

    if graph:
        # Track workspace metadata so downstream saves persist to the right tenant
        if not getattr(graph, "metadata", None):
            graph.metadata = {}
        graph.metadata.setdefault("workspace_id", user_identifier)
        graph.metadata["last_loaded_by"] = user_identifier
        graph.metadata["last_loaded_at"] = datetime.now().isoformat()
        logger.debug(f"{LOG_PREFIX} Graph '{graph_name}' loaded successfully")
        return graph

    logger.error(
        f"{LOG_PREFIX} Graph '{graph_name}' not found for user '{user_identifier}'"
    )
    raise GraphNotFoundError(graph_name)


def deserialize_agent_config(config_dict: Dict[str, Any]) -> AgentConfig:
    """Deserialize agent config with nested LLMConfig object.

    Args:
        config_dict: Dictionary representation of agent config

    Returns:
        AgentConfig object with properly deserialized nested configs

    Raises:
        Exception: If deserialization fails
    """
    try:
        config_copy = config_dict.copy()

        # Handle nested llm_config
        if "llm_config" in config_copy and config_copy["llm_config"]:
            # If it's already an LLMConfig object, keep it
            if not isinstance(config_copy["llm_config"], LLMConfig):
                config_copy["llm_config"] = LLMConfig(**config_copy["llm_config"])

        # Filter out removed fields for backward compatibility
        from dataclasses import fields as dc_fields

        valid_fields = {f.name for f in dc_fields(AgentConfig)}
        config_copy = {k: v for k, v in config_copy.items() if k in valid_fields}

        return AgentConfig(**config_copy)
    except Exception as e:
        from backend.services.execution.logging import redact_sensitive_data

        logger.error(f"{LOG_PREFIX} Error deserializing agent config: {e}")
        logger.error(f"{LOG_PREFIX} Config dict: {redact_sensitive_data(config_dict)}")
        raise


def deserialize_condition_config(config_dict: Dict[str, Any]) -> ConditionConfig:
    """Deserialize condition config with nested LLMConfig object.

    Args:
        config_dict: Dictionary representation of condition config

    Returns:
        ConditionConfig object with properly deserialized nested configs
    """
    config_copy = config_dict.copy()

    # Handle nested llm_config
    if "llm_config" in config_copy and config_copy["llm_config"]:
        config_copy["llm_config"] = LLMConfig(**config_copy["llm_config"])

    return ConditionConfig(**config_copy)


def initialize_langgraph_engine() -> bool:
    """Initialize the LangGraph engine after shared instances are ready.

    This function is called during application startup to ensure the
    LangGraph execution engine is ready via dependency injection.

    Returns:
        True if engine is ready, False otherwise
    """
    try:
        from backend.services.dependency_injection import get_execution_engine

        get_execution_engine()
        logger.info(f"{LOG_PREFIX} LangGraph engine ready via dependency injection")
        return True
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Failed to initialize LangGraph engine: {e}")
        return False
