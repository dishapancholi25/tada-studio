"""
Configuration validation for tool creation.

This module provides validation utilities to ensure tool configurations
are valid before attempting to create tool instances.
"""

from typing import Any, Dict, List, Optional

from ..config import get_logger


logger = get_logger("tool-validation")


class ValidationError(Exception):
    """Raised when tool configuration validation fails."""

    pass


class ConfigValidator:
    """
    Validates tool configurations.

    Provides methods for validating common configuration patterns
    and requirements.
    """

    @staticmethod
    def validate_required_keys(
        config: Dict[str, Any], required_keys: List[str], tool_name: str
    ) -> None:
        """
        Validate that all required keys are present in configuration.

        Args:
            config: Configuration dictionary to validate
            required_keys: List of required key names
            tool_name: Name of the tool (for error messages)

        Raises:
            ValidationError: If any required keys are missing
        """
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            error_msg = (
                f"Tool '{tool_name}' missing required configuration keys: "
                f"{', '.join(missing_keys)}"
            )
            logger.error(f"[TOOL-VALIDATION] {error_msg}")
            raise ValidationError(error_msg)

    @staticmethod
    def validate_type(
        config: Dict[str, Any], key: str, expected_type: type, tool_name: str
    ) -> None:
        """
        Validate that a configuration value has the expected type.

        Args:
            config: Configuration dictionary
            key: Key to validate
            expected_type: Expected type
            tool_name: Name of the tool (for error messages)

        Raises:
            ValidationError: If type doesn't match
        """
        if key in config and not isinstance(config[key], expected_type):
            error_msg = (
                f"Tool '{tool_name}' config key '{key}' must be {expected_type.__name__}, "
                f"got {type(config[key]).__name__}"
            )
            logger.error(f"[TOOL-VALIDATION] {error_msg}")
            raise ValidationError(error_msg)

    @staticmethod
    def validate_range(
        config: Dict[str, Any],
        key: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        tool_name: str = "",
    ) -> None:
        """
        Validate that a numeric value is within a specified range.

        Args:
            config: Configuration dictionary
            key: Key to validate
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            tool_name: Name of the tool (for error messages)

        Raises:
            ValidationError: If value is out of range
        """
        if key not in config:
            return

        value = config[key]

        if not isinstance(value, (int, float)):
            error_msg = f"Tool '{tool_name}' config key '{key}' must be numeric"
            logger.error(f"[TOOL-VALIDATION] {error_msg}")
            raise ValidationError(error_msg)

        if min_value is not None and value < min_value:
            error_msg = (
                f"Tool '{tool_name}' config key '{key}' must be >= {min_value}, "
                f"got {value}"
            )
            logger.error(f"[TOOL-VALIDATION] {error_msg}")
            raise ValidationError(error_msg)

        if max_value is not None and value > max_value:
            error_msg = (
                f"Tool '{tool_name}' config key '{key}' must be <= {max_value}, "
                f"got {value}"
            )
            logger.error(f"[TOOL-VALIDATION] {error_msg}")
            raise ValidationError(error_msg)

    @staticmethod
    def validate_choices(
        config: Dict[str, Any],
        key: str,
        choices: List[Any],
        tool_name: str = "",
    ) -> None:
        """
        Validate that a value is one of a set of allowed choices.

        Args:
            config: Configuration dictionary
            key: Key to validate
            choices: List of allowed values
            tool_name: Name of the tool (for error messages)

        Raises:
            ValidationError: If value is not in choices
        """
        if key not in config:
            return

        value = config[key]

        if value not in choices:
            error_msg = (
                f"Tool '{tool_name}' config key '{key}' must be one of {choices}, "
                f"got '{value}'"
            )
            logger.error(f"[TOOL-VALIDATION] {error_msg}")
            raise ValidationError(error_msg)

    @staticmethod
    def validate_config(tool_name: str, config: Dict[str, Any]) -> bool:
        """
        Perform general validation on tool configuration.

        Args:
            tool_name: Name of the tool
            config: Configuration to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If configuration is invalid
        """
        # Ensure config is a dictionary
        if not isinstance(config, dict):
            error_msg = f"Tool '{tool_name}' config must be a dictionary, got {type(config).__name__}"
            logger.error(f"[TOOL-VALIDATION] {error_msg}")
            raise ValidationError(error_msg)

        # Validate common timeout parameter if present
        if "timeout" in config or "timeout_seconds" in config:
            timeout_key = (
                "timeout_seconds" if "timeout_seconds" in config else "timeout"
            )
            ConfigValidator.validate_range(
                config, timeout_key, min_value=1, max_value=600, tool_name=tool_name
            )

        # Validate common max_retries parameter if present
        if "max_retries" in config:
            ConfigValidator.validate_range(
                config, "max_retries", min_value=0, max_value=10, tool_name=tool_name
            )

        logger.debug(f"[TOOL-VALIDATION] Configuration validated for tool: {tool_name}")
        return True
