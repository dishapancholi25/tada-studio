"""LLM configuration handlers.

This module provides handler functions for LLM provider and model configuration.
"""

from datetime import datetime
from typing import Any, Dict

from backend.models.workflow import AgentConfig, LLMConfig, NodeType
from backend.services.config import get_logger
from backend.services.dependency_injection import get_graph_manager
from backend.services.llm_models import LLMFactory

from ..constants import LOG_PREFIX, MSG_LLM_CONFIG_UPDATED
from ..dependencies import get_graph_or_404, get_user_identifier
from ..exceptions import GraphNotFoundError, InvalidRequestError, NodeNotFoundError
from ..models import LLMConfigRequest, TestLLMRequest


logger = get_logger(__name__)


async def handle_get_llm_providers() -> Dict[str, Any]:
    """Get available LLM providers and their supported models.

    Returns:
        Dictionary with success status and list of providers
    """
    logger.info(f"{LOG_PREFIX} Getting LLM providers")

    factory = LLMFactory()
    providers_dict = factory.get_available_models()

    # Transform to more usable format
    providers = []
    for provider_name, models in providers_dict.items():
        providers.append(
            {
                "name": provider_name,
                "display_name": provider_name.replace("_", " ").title(),
                "models": models,
            }
        )

    return {"success": True, "providers": providers}


async def handle_get_llm_models(provider: str) -> Dict[str, Any]:
    """Get available models for a specific LLM provider.

    Args:
        provider: LLM provider name

    Returns:
        Dictionary with success status, provider, and models

    Raises:
        InvalidRequestError: If provider not supported
    """
    logger.info(f"{LOG_PREFIX} Getting LLM models for provider '{provider}'")

    factory = LLMFactory()
    all_models = factory.get_available_models()
    models = all_models.get(provider, [])

    if not models:
        raise InvalidRequestError(f"Provider '{provider}' not supported")

    return {
        "success": True,
        "provider": provider,
        "models": [{"name": model, "display_name": model} for model in models],
    }


async def handle_test_llm_connection(request: TestLLMRequest) -> Dict[str, Any]:
    """Test LLM connection and configuration.

    Args:
        request: Test LLM request

    Returns:
        Dictionary with success status and test result
    """
    logger.info(f"{LOG_PREFIX} Testing LLM connection")

    try:
        # Create LLM config from request
        llm_config = LLMConfig(**request.llm_config)

        # Test connection
        factory = LLMFactory()
        result = factory.test_llm_connection(llm_config)

        return {"success": True, "test_result": result}
    except Exception as e:
        logger.error(f"{LOG_PREFIX} LLM connection test failed: {e}")
        return {
            "success": False,
            "error": "LLM connection test failed. Check server logs for details.",
            "message": "LLM connection test failed",
        }


async def handle_configure_node_llm(request: LLMConfigRequest) -> Dict[str, Any]:
    """Configure LLM settings for an agent node.

    Args:
        request: LLM config request

    Returns:
        Dictionary with success status, message, and node data

    Raises:
        GraphNotFoundError: If graph not found
        NodeNotFoundError: If node not found
        InvalidRequestError: If node is not an AGENT node
    """
    logger.info(
        f"{LOG_PREFIX} Configuring LLM for node '{request.node_id}' "
        f"in graph '{request.graph_name}'"
    )

    graph = get_graph_manager().get_graph(request.graph_name)
    if not graph:
        raise GraphNotFoundError(request.graph_name)

    node = graph.get_node_by_id(request.node_id)
    if not node:
        raise NodeNotFoundError(request.node_id, request.graph_name)

    if node.type != NodeType.AGENT:
        raise InvalidRequestError("LLM configuration only applies to AGENT nodes")

    # Create and validate LLM config
    llm_config = LLMConfig(**request.llm_config)

    # Update agent config with LLM config
    if not node.agent_config:
        node.agent_config = AgentConfig()

    node.agent_config.llm_config = llm_config
    node.updated_at = datetime.now().isoformat()
    graph.updated_at = datetime.now().isoformat()

    logger.info(f"{LOG_PREFIX} LLM configuration updated successfully")
    return {
        "success": True,
        "message": MSG_LLM_CONFIG_UPDATED,
        "node": node.to_dict(),
    }


async def handle_get_node_llm_config(
    graph_name: str, node_id: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Get LLM configuration for an agent node.

    Args:
        graph_name: Name of the graph (URL-encoded)
        node_id: Agent node ID
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, node ID, and LLM config

    Raises:
        GraphNotFoundError: If graph not found
        NodeNotFoundError: If node not found
        InvalidRequestError: If node is not an AGENT node
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Getting LLM config for node '{node_id}' "
        f"in graph '{graph_name}' for user '{user_identifier}'"
    )

    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    node = graph.get_node_by_id(node_id)
    if not node:
        raise NodeNotFoundError(node_id, graph_name)

    if node.type != NodeType.AGENT:
        raise InvalidRequestError("LLM configuration only applies to AGENT nodes")

    llm_config = None
    if node.agent_config and node.agent_config.llm_config:
        llm_config = node.agent_config.llm_config.to_dict()

    return {"success": True, "node_id": node_id, "llm_config": llm_config}
