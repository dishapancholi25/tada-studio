"""Validation utilities for agent compilation.

This module provides validation logic for agent configurations, ensuring
all required fields and settings are present and valid before compilation.
"""

from dataclasses import dataclass, field
from typing import List

from backend.models.workflow import AgentConfig, EnhancedNodeData, LLMConfig

from .exceptions import ValidationError


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        valid: Whether validation passed
        errors: List of validation error messages
        warnings: List of validation warning messages
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ConfigValidator:
    """Validates agent configurations before compilation.

    Provides methods to validate different aspects of agent configuration,
    ensuring all required fields are present and values are valid.
    """

    @staticmethod
    def validate_node(node: EnhancedNodeData) -> ValidationResult:
        """Validate an agent node for compilation.

        Args:
            node: Agent node to validate

        Returns:
            ValidationResult indicating if the node is valid
        """
        result = ValidationResult(valid=True)

        # Check if agent config exists
        if not node.agent_config:
            result.valid = False
            result.errors.append(f"Agent {node.name} has no configuration")
            return result

        # Validate agent config
        agent_result = ConfigValidator.validate_agent_config(node.agent_config)
        result.errors.extend(agent_result.errors)
        result.warnings.extend(agent_result.warnings)
        result.valid = result.valid and agent_result.valid

        return result

    @staticmethod
    def validate_agent_config(config: AgentConfig) -> ValidationResult:
        """Validate agent configuration.

        Args:
            config: Agent configuration to validate

        Returns:
            ValidationResult indicating if config is valid
        """
        result = ValidationResult(valid=True)

        # Validate LLM config
        if not config.llm_config:
            result.valid = False
            result.errors.append("No LLM configuration provided")
        else:
            llm_result = ConfigValidator.validate_llm_config(config.llm_config)
            result.errors.extend(llm_result.errors)
            result.warnings.extend(llm_result.warnings)
            result.valid = result.valid and llm_result.valid

        # Check system prompt
        if not config.system_prompt:
            result.warnings.append("No system prompt provided")

        # Validate tools if present
        if config.tools:
            tools_result = ConfigValidator.validate_tool_configs(config.tools)
            result.warnings.extend(tools_result.warnings)

        return result

    @staticmethod
    def validate_llm_config(config: LLMConfig) -> ValidationResult:
        """Validate LLM configuration.

        Args:
            config: LLM configuration to validate (can be dict or LLMConfig)

        Returns:
            ValidationResult indicating if config is valid
        """
        result = ValidationResult(valid=True)

        # Handle dict input
        if isinstance(config, dict):
            provider = config.get("provider")
            model_name = config.get("model_name")
        else:
            provider = config.provider
            model_name = config.model_name

        # Check required fields
        if not provider:
            result.valid = False
            result.errors.append("LLM provider not specified")

        if not model_name:
            result.valid = False
            result.errors.append("LLM model name not specified")

        return result

    @staticmethod
    def validate_tool_configs(tool_configs: List) -> ValidationResult:
        """Validate tool configurations.

        Args:
            tool_configs: List of tool configurations

        Returns:
            ValidationResult with any warnings about tool configs
        """
        result = ValidationResult(valid=True)

        if not tool_configs:
            result.warnings.append("No tools configured for agent")

        # Could add more specific tool validation here
        # For now, just check that we have tools

        return result

    @staticmethod
    def raise_if_invalid(validation_result: ValidationResult, agent_id: str) -> None:
        """Raise ValidationError if validation failed.

        Args:
            validation_result: Result to check
            agent_id: Agent identifier for error context

        Raises:
            ValidationError: If validation failed
        """
        if not validation_result.valid:
            error_msg = "; ".join(validation_result.errors)
            raise ValidationError(
                message=f"Agent validation failed: {error_msg}",
                agent_id=agent_id,
            )
