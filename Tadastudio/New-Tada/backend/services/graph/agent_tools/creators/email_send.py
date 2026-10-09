"""Email send tool creator for agents.

This module creates email send tool instances that agents can use
to send emails with AI-populated or static content.
"""

from typing import Any, Optional, Set

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.feature_flags import (
    EMAIL_COMING_SOON_MESSAGE,
    EMAIL_FEATURE_ENABLED,
)
from backend.services.graph.agent_tools.utils import build_tool_name


logger = get_logger(__name__)


def create_email_send_tool_from_node(
    target_node: EnhancedNodeData,
    user_id: Optional[str] = None,
    used_tool_names: Optional[Set[str]] = None,
) -> Optional[Any]:
    """Create an email send tool from an EMAIL_SEND_TOOL node.

    Args:
        target_node: The EMAIL_SEND_TOOL node configuration
        user_id: User ID for email provider configuration
        used_tool_names: Optional set to track used tool names for collision detection

    Returns:
        Email send tool instance, or None if configuration is invalid
    """
    if not EMAIL_FEATURE_ENABLED:
        logger.warning(
            f"Skipping email send tool for node {target_node.name}: "
            f"{EMAIL_COMING_SOON_MESSAGE}"
        )
        return None

    if not target_node.email_send_tool_config:
        logger.warning(f"Node {target_node.name} missing email_send_tool_config")
        return None

    logger.info(f"Creating email send tool from node: {target_node.name}")

    from backend.tools.email_send import create_email_send_tool

    config = target_node.email_send_tool_config

    # Handle both dict and dataclass config
    if isinstance(config, dict):
        to_address_config = config.get("to_address", {})
        subject_config = config.get("subject", {})
        body_config = config.get("body", {})
    else:
        # Dataclass - convert to dicts for the factory
        to_address_config = _field_config_to_dict(getattr(config, "to_address", None))
        subject_config = _field_config_to_dict(getattr(config, "subject", None))
        body_config = _field_config_to_dict(getattr(config, "body", None))

    # Build semantic tool name from node name
    tool_name = build_tool_name(
        tool_type_prefix="email_send",
        node_name=target_node.name,
        node_id=target_node.uniq_id,
        default_name="Email Send Tool",
        used_names=used_tool_names,
    )

    # Build description prefix from node name if not default
    description_prefix = None
    if target_node.name and target_node.name not in ["Email Send Tool", "Email Send"]:
        description_prefix = f"Email send tool '{target_node.name}'"
        if target_node.description:
            description_prefix = f"{description_prefix} - {target_node.description}"

    email_send_tool = create_email_send_tool(
        to_address_config=to_address_config,
        subject_config=subject_config,
        body_config=body_config,
        node_id=target_node.uniq_id,
        node_name=target_node.name,
        tool_name=tool_name,
        description_prefix=description_prefix,
        user_id=user_id,
    )

    logger.info(f"Created email send tool: {tool_name}")
    return email_send_tool


def _field_config_to_dict(field_config: Any) -> dict:
    """Convert a field config dataclass to dict.

    Args:
        field_config: Field configuration object

    Returns:
        Dictionary representation
    """
    if field_config is None:
        return {}

    if isinstance(field_config, dict):
        return field_config

    return {
        "mode": getattr(field_config, "mode", "ai"),
        "static_value": getattr(field_config, "static_value", ""),
        "ai_description": getattr(field_config, "ai_description", ""),
    }
