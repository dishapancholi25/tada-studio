"""File write tool creator for agents.

This module creates file write tool instances that agents can use
to write files stored in the database.
"""

from typing import Any, Callable, Optional, Set

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.graph.agent_tools.utils import build_tool_name


logger = get_logger(__name__)


def create_file_write_tool_from_node(
    target_node: EnhancedNodeData,
    used_tool_names: Optional[Set[str]] = None,
    node_execution_id_provider: Optional[Callable[[], Optional[str]]] = None,
) -> Optional[Any]:
    """Create a file write tool from a FILE_WRITE node.

    Args:
        target_node: The FILE_WRITE node configuration
        used_tool_names: Optional set to track used tool names for collision detection
        node_execution_id_provider: Callback to get node_execution_id at runtime

    Returns:
        File write tool instance, or None if configuration is invalid
    """
    if not target_node.file_write_config:
        logger.warning(f"Node {target_node.name} missing file_write_config")
        return None

    logger.info(f"Creating file write tool from node: {target_node.name}")

    from backend.tools.file_write import create_file_write_tool

    config = target_node.file_write_config

    # Handle both dict and dataclass config
    if isinstance(config, dict):
        allowed_extensions = config.get(
            "allowed_extensions",
            [
                ".txt",
                ".md",
                ".json",
                ".csv",
                ".yaml",
                ".yml",
                ".pdf",
                ".docx",
                ".xlsx",
                ".pptx",
            ],
        )
        max_file_size_mb = config.get("max_file_size_mb", 10)
        default_template = config.get("default_template", None)
        custom_template_asset_id = config.get("custom_template_asset_id", None)
        custom_template_variables = config.get("custom_template_variables", None)
    else:
        allowed_extensions = getattr(
            config,
            "allowed_extensions",
            [
                ".txt",
                ".md",
                ".json",
                ".csv",
                ".yaml",
                ".yml",
                ".pdf",
                ".docx",
                ".xlsx",
                ".pptx",
            ],
        )
        max_file_size_mb = getattr(config, "max_file_size_mb", 10)
        default_template = getattr(config, "default_template", None)
        custom_template_asset_id = getattr(config, "custom_template_asset_id", None)
        custom_template_variables = getattr(config, "custom_template_variables", None)

    # Build semantic tool name from node name
    tool_name = build_tool_name(
        tool_type_prefix="file_write",
        node_name=target_node.name,
        node_id=target_node.uniq_id,
        default_name="File Write",
        used_names=used_tool_names,
    )

    # Build description prefix from node name if not default
    description_prefix = None
    if target_node.name and target_node.name not in ["File Write", "File Write Tool"]:
        description_prefix = f"File write tool '{target_node.name}'"
        if target_node.description:
            description_prefix = f"{description_prefix} - {target_node.description}"

    file_write_tool = create_file_write_tool(
        allowed_extensions=allowed_extensions,
        max_file_size_mb=max_file_size_mb,
        node_id=target_node.uniq_id,
        node_name=target_node.name,
        tool_name=tool_name,
        description_prefix=description_prefix,
        node_execution_id_provider=node_execution_id_provider,
        default_template=default_template,
        custom_template_asset_id=custom_template_asset_id,
        custom_template_variables=custom_template_variables,
    )

    logger.info(f"Created file write tool: {tool_name}")
    return file_write_tool
