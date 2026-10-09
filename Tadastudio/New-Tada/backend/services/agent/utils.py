"""Utility functions for agent compilation.

This module provides helper functions used throughout the compilation process,
including cache key generation and graph analysis.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from backend.models.workflow import AgentConfig, EnhancedNodeData, GraphData


def generate_cache_key(node: EnhancedNodeData) -> str:
    """Generate a unique cache key for a compiled agent.

    The cache key is based on relevant configuration that affects compilation,
    including agent ID, LLM config, tools, and system prompt hash.

    Args:
        node: Agent node to generate cache key for

    Returns:
        MD5 hash string representing the cache key
    """
    config_data: Dict[str, Any] = {
        "agent_id": node.uniq_id,
        "name": node.name,
        "version": getattr(node, "version", "1.0"),
        "is_orchestrator": (
            node.agent_config.is_orchestrator if node.agent_config else False
        ),
    }

    if node.agent_config:
        config_data["llm"] = {
            "provider": (
                node.agent_config.llm_config.provider
                if node.agent_config.llm_config
                else None
            ),
            "model": (
                node.agent_config.llm_config.model_name
                if node.agent_config.llm_config
                else None
            ),
        }
        config_data["tools"] = node.agent_config.tools or []
        config_data["system_prompt_hash"] = hashlib.md5(
            (node.agent_config.system_prompt or "").encode()
        ).hexdigest()

    config_str = json.dumps(config_data, sort_keys=True)
    return hashlib.md5(config_str.encode()).hexdigest()


def find_connected_tools(
    node: EnhancedNodeData, graph: GraphData
) -> List[EnhancedNodeData]:
    """Find tool nodes connected to an agent in the graph.

    Searches the graph for tool nodes that are connected to the given agent
    node via tool connections.

    Args:
        node: Agent node to find connected tools for
        graph: Graph containing nodes and connections

    Returns:
        List of tool nodes connected to the agent
    """
    from backend.models.workflow import ConnectionType, NodeType
    from backend.services.config import get_logger

    logger = get_logger("agent.utils")
    connected_tools: List[EnhancedNodeData] = []

    # Find connections where this node is the source
    for connection in graph.connections:
        if (
            connection.source_id == node.uniq_id
            and connection.connection_type == ConnectionType.TOOL
        ):
            # Find the target node
            for target_node in graph.nodes:
                if (
                    target_node.uniq_id == connection.target_id
                    and target_node.type == NodeType.TOOL
                ):
                    connected_tools.append(target_node)
                    logger.debug(
                        f"Found connected tool {target_node.name} for agent {node.name}"
                    )

    return connected_tools


def compile_structured_output(config: AgentConfig) -> Optional[Dict[str, Any]]:
    """Compile structured output schema from agent configuration.

    Extracts and returns the structured output schema if configured.
    Currently returns the first schema if multiple are defined.

    Args:
        config: Agent configuration

    Returns:
        Structured output schema dictionary, or None if not configured
    """
    if not config.structured_outputs:
        return None

    # Return the first schema
    # Note: In future enhancements, this could support multiple schemas
    # or schema selection based on context
    if config.structured_outputs and len(config.structured_outputs) > 0:
        return config.structured_outputs[0]

    return None
