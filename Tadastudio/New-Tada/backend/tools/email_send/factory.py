"""Factory functions for creating email send tools."""

from typing import Any, Dict, Optional

from langchain_core.tools import StructuredTool

from .config import ArgsSchemaBuilder, ToolDescriptionBuilder
from .handlers import handle_email_send_execution
from .schemas import EmailFieldConfig, EmailFieldMode, EmailSendToolConfig


def create_email_send_tool(
    to_address_config: Optional[Dict[str, Any]] = None,
    subject_config: Optional[Dict[str, Any]] = None,
    body_config: Optional[Dict[str, Any]] = None,
    node_id: str = "",
    node_name: str = "Email Send Tool",
    tool_name: Optional[str] = None,
    description_prefix: Optional[str] = None,
    user_id: Optional[str] = None,
) -> StructuredTool:
    """Create an email send tool with the given configuration.

    Args:
        to_address_config: Configuration for to_address field (mode, static_value, ai_description)
        subject_config: Configuration for subject field
        body_config: Configuration for body field
        node_id: Node ID for tracking
        node_name: Node name for display
        tool_name: Optional custom tool name
        description_prefix: Optional prefix for the tool description
        user_id: User ID for email provider configuration

    Returns:
        StructuredTool instance for email sending
    """
    # Parse field configs
    to_field = _parse_field_config(to_address_config)
    subject_field = _parse_field_config(subject_config)
    body_field = _parse_field_config(body_config)

    # Build configuration
    config = EmailSendToolConfig(
        to_address=to_field,
        subject=subject_field,
        body=body_field,
        node_id=node_id,
        node_name=node_name,
    )

    # Build tool description
    tool_description = ToolDescriptionBuilder.build_description(config)
    if description_prefix:
        tool_description = f"{description_prefix}. {tool_description}"

    # Build dynamic args schema based on which fields are AI-populated
    EmailArgs = ArgsSchemaBuilder.build_args_schema(config)

    def send_email_impl(**kwargs) -> str:
        """Send an email with the provided parameters.

        This tool sends an email using the configured email provider.
        Some fields may be pre-configured (static) while others are
        provided dynamically based on context.
        """
        return handle_email_send_execution(kwargs, config, user_id)

    # Generate tool name
    final_tool_name = tool_name or "send_email"

    # Create and return the tool
    return StructuredTool(
        name=final_tool_name,
        description=tool_description,
        func=send_email_impl,
        args_schema=EmailArgs,
    )


def _parse_field_config(config: Optional[Dict[str, Any]]) -> EmailFieldConfig:
    """Parse a field configuration from dict to EmailFieldConfig.

    Args:
        config: Field configuration dictionary

    Returns:
        EmailFieldConfig instance
    """
    if not config:
        return EmailFieldConfig()

    # Handle both dict and dataclass
    if isinstance(config, dict):
        mode_str = config.get("mode", "ai")
        mode = EmailFieldMode.STATIC if mode_str == "static" else EmailFieldMode.AI

        return EmailFieldConfig(
            mode=mode,
            static_value=config.get("static_value", ""),
            ai_description=config.get("ai_description", ""),
        )
    else:
        # Assume it's a dataclass-like object
        mode_str = getattr(config, "mode", "ai")
        mode = EmailFieldMode.STATIC if mode_str == "static" else EmailFieldMode.AI

        return EmailFieldConfig(
            mode=mode,
            static_value=getattr(config, "static_value", ""),
            ai_description=getattr(config, "ai_description", ""),
        )
