"""Configuration utilities for email send tool."""

from typing import Any, Dict, List, Optional, Tuple, Type

from pydantic import BaseModel, Field, create_model

from .schemas import EmailFieldMode, EmailSendToolConfig


class ToolDescriptionBuilder:
    """Builder for creating tool descriptions based on configuration."""

    # Default descriptions for each field when AI description is empty
    DEFAULT_DESCRIPTIONS = {
        "to_address": "The recipient's email address",
        "subject": "A clear and descriptive email subject line",
        "body": "The full content of the email body",
    }

    @staticmethod
    def build_description(config: EmailSendToolConfig) -> str:
        """Build a dynamic tool description based on configuration.

        Args:
            config: Email send tool configuration

        Returns:
            Formatted tool description string
        """
        parts = [
            "Send an email. Supports file attachments via file_id from file_write tool."
        ]

        # Add field descriptions for AI-populated fields
        ai_fields = []
        for field_name, field_config in [
            ("to_address", config.to_address),
            ("subject", config.subject),
            ("body", config.body),
        ]:
            if field_config.mode == EmailFieldMode.AI:
                desc = (
                    field_config.ai_description
                    or ToolDescriptionBuilder.DEFAULT_DESCRIPTIONS[field_name]
                )
                ai_fields.append(f"  - {field_name}: {desc}")

        if ai_fields:
            parts.append("\nParameters:")
            parts.extend(ai_fields)

        # Mention static fields that are pre-configured
        static_fields = []
        for field_name, field_config in [
            ("to_address", config.to_address),
            ("subject", config.subject),
            ("body", config.body),
        ]:
            if field_config.mode == EmailFieldMode.STATIC and field_config.static_value:
                static_fields.append(field_name)

        if static_fields:
            parts.append(f"\nPre-configured: {', '.join(static_fields)}")

        return "\n".join(parts)


class ArgsSchemaBuilder:
    """Builder for creating dynamic Pydantic argument schemas."""

    @staticmethod
    def build_args_schema(config: EmailSendToolConfig) -> Type[BaseModel]:
        """Build a dynamic Pydantic model with only AI-mode fields.

        Args:
            config: Email send tool configuration

        Returns:
            Dynamically created Pydantic model class
        """
        field_definitions: Dict[str, Tuple[Type, Any]] = {}

        # Add to_address if AI mode
        if config.to_address.mode == EmailFieldMode.AI:
            description = (
                config.to_address.ai_description
                or ToolDescriptionBuilder.DEFAULT_DESCRIPTIONS["to_address"]
            )
            field_definitions["to_address"] = (
                str,
                Field(description=description),
            )

        # Add subject if AI mode
        if config.subject.mode == EmailFieldMode.AI:
            description = (
                config.subject.ai_description
                or ToolDescriptionBuilder.DEFAULT_DESCRIPTIONS["subject"]
            )
            field_definitions["subject"] = (
                str,
                Field(description=description),
            )

        # Add body if AI mode
        if config.body.mode == EmailFieldMode.AI:
            description = (
                config.body.ai_description
                or ToolDescriptionBuilder.DEFAULT_DESCRIPTIONS["body"]
            )
            field_definitions["body"] = (
                str,
                Field(description=description),
            )

        # Always include optional attachment_file_ids field
        field_definitions["attachment_file_ids"] = (
            Optional[List[str]],
            Field(
                default=None,
                description=(
                    "Optional list of file IDs to attach to the email. "
                    "Use the file_id values returned by the file_write tool."
                ),
            ),
        )

        # Create and return dynamic model
        return create_model("EmailSendToolArgs", **field_definitions)


class ConfigValidator:
    """Validator for email send tool configuration."""

    @staticmethod
    def validate(config: EmailSendToolConfig) -> Tuple[bool, List[str], List[str]]:
        """Validate email send tool configuration.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        # Check if at least to_address has a value or is AI-populated
        if (
            config.to_address.mode == EmailFieldMode.STATIC
            and not config.to_address.static_value
        ):
            errors.append(
                "Recipient (to_address) must have a static value or be AI-populated"
            )

        # Warn about missing AI descriptions
        for field_name, field_config in [
            ("to_address", config.to_address),
            ("subject", config.subject),
            ("body", config.body),
        ]:
            if (
                field_config.mode == EmailFieldMode.AI
                and not field_config.ai_description
            ):
                warnings.append(
                    f"Field '{field_name}' is AI-populated but has no description. "
                    "Consider adding a description to guide the AI."
                )

        is_valid = len(errors) == 0
        return is_valid, errors, warnings
