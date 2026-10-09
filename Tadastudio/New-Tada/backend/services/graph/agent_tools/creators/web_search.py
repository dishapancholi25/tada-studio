"""Web search tool creator for agents.

This module creates web search tool instances that agents can use
to search the internet.
"""

from typing import Any, Optional, Set

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import build_tool_name


logger = get_logger(__name__)


def create_web_search_tool_from_node(
    target_node: EnhancedNodeData,
    used_tool_names: Optional[Set[str]] = None,
) -> Optional[Any]:
    """
    Create a web search tool from a WEB_SEARCH node.

    Args:
        target_node: The WEB_SEARCH node configuration
        used_tool_names: Optional set to track used tool names for collision detection

    Returns:
        Web search tool instance, or None if configuration is invalid

    Raises:
        ImportError: If web search tool module is not available
    """
    if not target_node.web_search_config:
        logger.warning(f"Node {target_node.name} missing web_search_config")
        return None

    logger.info(
        f"Creating web search tool from node: {target_node.name} "
        f"for agent {getattr(target_node.web_search_config, 'parent_agent_id', 'unknown')}"
    )

    from backend.tools.web_search import create_web_search_tool

    web_config = target_node.web_search_config

    # Handle both dict and WebSearchConfig object
    if isinstance(web_config, dict):
        # Extract values from dict
        search_provider = web_config.get("search_provider", "duckduckgo")
        api_key = web_config.get("api_key", "")
        max_results = web_config.get("max_results", 5)
        search_depth = web_config.get("search_depth", "basic")
        include_answer = web_config.get("include_answer", False)
        include_raw_content = web_config.get("include_raw_content", False)
        include_images = web_config.get("include_images", False)
        timeout_seconds = web_config.get("timeout_seconds", 10)
        region = web_config.get("region", "wt-wt")
        safe_search = web_config.get("safe_search", "moderate")
        time_range = web_config.get("time_range", "")
    else:
        # Use object attributes
        search_provider = web_config.search_provider
        api_key = web_config.api_key
        max_results = web_config.max_results
        search_depth = web_config.search_depth
        include_answer = web_config.include_answer
        include_raw_content = web_config.include_raw_content
        include_images = web_config.include_images
        timeout_seconds = web_config.timeout_seconds
        region = web_config.region
        safe_search = web_config.safe_search
        time_range = web_config.time_range

    # Build semantic tool name from node name
    tool_name = build_tool_name(
        tool_type_prefix="web_search",
        node_name=target_node.name,
        node_id=target_node.uniq_id,
        default_name="Web Search",
        used_names=used_tool_names,
    )

    # Build description prefix from node name if not default
    description_prefix = None
    if target_node.name and target_node.name != "Web Search":
        description_prefix = f"Web search '{target_node.name}'"
        if target_node.description:
            description_prefix = f"{description_prefix} - {target_node.description}"

    web_search_tool = create_web_search_tool(
        search_provider=search_provider,
        api_key=api_key,
        max_results=max_results,
        search_depth=search_depth,
        include_answer=include_answer,
        include_raw_content=include_raw_content,
        include_images=include_images,
        timeout_seconds=timeout_seconds,
        region=region,
        safe_search=safe_search,
        time_range=time_range,
        node_id=target_node.uniq_id,
        node_name=target_node.name,
        tool_name=tool_name,
        description_prefix=description_prefix,
    )

    logger.info(f"Created web search tool: {tool_name}")
    return web_search_tool
