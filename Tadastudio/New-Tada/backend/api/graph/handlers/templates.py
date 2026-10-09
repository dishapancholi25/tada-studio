"""Templates and configuration handlers.

This module provides handler functions for tool and agent templates.
"""

from typing import Any, Dict

from backend.services.config import get_logger
from backend.services.dependency_injection import get_graph_manager

from ..constants import LOG_PREFIX


logger = get_logger(__name__)


async def handle_get_tool_templates() -> Dict[str, Any]:
    """Get available tool templates.

    Note: Tool templates have been removed. Tools are now added as explicit
    node types (DATABASE_QUERY, DOCUMENT_SEARCH, HTTP_REQUEST, WEB_SEARCH, MCP_SERVER, etc.)
    connected via TOOL connections in the graph UI.

    Returns:
        Dictionary with success status and templates
    """
    logger.info(f"{LOG_PREFIX} Getting tool templates")

    templates = get_graph_manager().get_available_tools()
    return {"success": True, "templates": templates}


async def handle_get_agent_templates() -> Dict[str, Any]:
    """Get available agent templates with LLM configurations.

    Returns:
        Dictionary with success status and templates
    """
    logger.info(f"{LOG_PREFIX} Getting agent templates")

    templates = get_graph_manager().get_available_agents()

    # Enhance templates with LLM info
    for template_name, template_data in templates.items():
        if (
            "agent_config" in template_data
            and "llm_config" in template_data["agent_config"]
        ):
            llm_config = template_data["agent_config"]["llm_config"]
            template_data["llm_provider"] = llm_config.get("provider", "unknown")
            template_data["llm_model"] = llm_config.get("model_name", "unknown")
        else:
            template_data["llm_provider"] = "not_configured"
            template_data["llm_model"] = "not_configured"

    return {"success": True, "templates": templates}
