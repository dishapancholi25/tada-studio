"""Node validation logic.

This module provides validation for individual workflow nodes,
split into focused functions to reduce complexity.
"""

import logging
from typing import TYPE_CHECKING, List

from ..enums import NodeType
from .llm_validator import validate_llm_config

if TYPE_CHECKING:
    from ..node import EnhancedNodeData

logger = logging.getLogger(__name__)


class NodeValidator:
    """Validates node configurations with low complexity methods."""

    @staticmethod
    def validate_node(node: "EnhancedNodeData") -> List[str]:
        """Validate node configuration.

        Args:
            node: Node to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Basic validation
        errors.extend(NodeValidator._validate_basic_fields(node))

        # Type-specific validation
        if node.type == NodeType.TOOL:
            errors.extend(NodeValidator._validate_tool_node(node))
        elif node.type == NodeType.AGENT:
            errors.extend(NodeValidator._validate_agent_node(node))
        elif node.type == NodeType.CONDITION:
            errors.extend(NodeValidator._validate_condition_node(node))
        elif node.type == NodeType.FOR_EACH:
            errors.extend(NodeValidator._validate_for_each_node(node))
        elif node.type == NodeType.CODE_EXECUTOR:
            errors.extend(NodeValidator._validate_code_executor_node(node))

        # Execution configuration
        errors.extend(NodeValidator._validate_execution_config(node))

        return errors

    @staticmethod
    def _validate_basic_fields(node: "EnhancedNodeData") -> List[str]:
        """Validate basic required fields.

        Args:
            node: Node to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not node.uniq_id:
            errors.append("Node ID is required")

        if not node.name:
            errors.append("Node name is required")

        return errors

    @staticmethod
    def _validate_tool_node(node: "EnhancedNodeData") -> List[str]:
        """Validate tool node configuration.

        Args:
            node: Tool node to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not node.tool_config:
            errors.append("Tool configuration is required for TOOL nodes")
        elif not node.tool_config.tool_name and not node.tool_config.tool_code:
            errors.append("Tool name or tool code is required")

        return errors

    @staticmethod
    def _validate_agent_node(node: "EnhancedNodeData") -> List[str]:
        """Validate agent node configuration.

        Args:
            node: Agent node to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not node.agent_config:
            errors.append("Agent configuration is required for AGENT nodes")
            return errors

        # Validate system prompt
        if not node.agent_config.system_prompt:
            errors.append("System prompt is required for agents")

        # Validate LLM configuration
        if not node.agent_config.llm_config:
            errors.append("LLM configuration is required for AGENT nodes")
        else:
            llm_errors = validate_llm_config(node.agent_config.llm_config)
            errors.extend(llm_errors)

        # Validate tool configuration
        errors.extend(NodeValidator._validate_agent_tools(node))

        return errors

    @staticmethod
    def _validate_agent_tools(node: "EnhancedNodeData") -> List[str]:
        """Validate agent tool configuration.

        Args:
            node: Agent node to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not node.agent_config:
            return errors

        if (
            node.agent_config.tool_binding_mode == "automatic"
            and not node.agent_config.tools
            and not node.agent_config.structured_outputs
        ):
            errors.append(
                "Agent has automatic tool binding but no tools or structured outputs specified"
            )

        return errors

    @staticmethod
    def _validate_condition_node(node: "EnhancedNodeData") -> List[str]:
        """Validate condition node configuration.

        Args:
            node: Condition node to validate

        Returns:
            List of validation errors
        """
        logger.info(f"    Validating CONDITION node '{node.name}'")
        errors = []

        if not node.condition_config:
            logger.error(f"    No condition_config found for node '{node.name}'")
            errors.append("Condition configuration is required for CONDITION nodes")
            return errors

        logger.info(f"    Condition type: {node.condition_config.condition_type}")
        logger.info(f"    Branch mode: {node.condition_config.branch_mode}")

        # Validate condition type specific requirements
        errors.extend(NodeValidator._validate_condition_type(node))

        # Validate branch configuration
        if node.condition_config.condition_type == "simple":
            errors.extend(NodeValidator._validate_simple_conditions(node))

        # Validate LLM config for LLM-based conditions
        if (
            node.condition_config.condition_type == "llm"
            and node.condition_config.llm_config
        ):
            llm_errors = validate_llm_config(node.condition_config.llm_config)
            errors.extend(llm_errors)

        return errors

    @staticmethod
    def _validate_condition_type(node: "EnhancedNodeData") -> List[str]:
        """Validate condition type specific requirements.

        Args:
            node: Condition node to validate

        Returns:
            List of validation errors
        """
        errors = []
        config = node.condition_config

        if not config:
            return errors

        if not config.condition_prompt and config.condition_type == "llm":
            errors.append("Condition prompt is required for LLM-based conditions")

        if config.condition_type == "code" and not config.code_condition:
            errors.append("Code expression is required for code-based conditions")

        return errors

    @staticmethod
    def _validate_simple_conditions(node: "EnhancedNodeData") -> List[str]:
        """Validate simple condition configuration.

        Args:
            node: Condition node with simple conditions

        Returns:
            List of validation errors
        """
        errors = []
        config = node.condition_config

        if not config:
            return errors

        # Check if using multi-branch mode
        if config.branch_mode == "multi":
            logger.info(
                f"    Multi-branch mode with {len(config.branches or [])} branches"
            )
            errors.extend(NodeValidator._validate_multi_branch(config))
        else:
            # Binary mode validation
            logger.info(
                f"    Binary mode with {len(config.simple_conditions or [])} simple conditions"
            )
            errors.extend(NodeValidator._validate_binary_conditions(config))

        return errors

    @staticmethod
    def _validate_multi_branch(config) -> List[str]:
        """Validate multi-branch configuration.

        Args:
            config: Condition configuration

        Returns:
            List of validation errors
        """
        errors = []

        if not config.branches or len(config.branches) == 0:
            errors.append("At least one branch is required for multi-branch conditions")
            return errors

        # Validate each branch
        for i, branch in enumerate(config.branches):
            branch_label = (
                branch.get("label")
                if isinstance(branch, dict)
                else getattr(branch, "label", None)
            )
            if not branch_label:
                errors.append(f"Branch {i + 1}: Label is required")

            # Validate branch conditions if they exist
            branch_condition = (
                branch.get("condition")
                if isinstance(branch, dict)
                else getattr(branch, "condition", None)
            )
            if branch_condition and isinstance(branch_condition, dict):
                errors.extend(
                    NodeValidator._validate_branch_condition(branch_condition, i)
                )

        return errors

    @staticmethod
    def _validate_branch_condition(condition: dict, branch_index: int) -> List[str]:
        """Validate a single branch condition.

        Args:
            condition: Branch condition dictionary
            branch_index: Index of the branch

        Returns:
            List of validation errors
        """
        errors = []

        if condition.get("type") == "simple" and condition.get("conditions"):
            for j, cond in enumerate(condition["conditions"]):
                if not isinstance(cond, dict):
                    continue

                if not cond.get("operator"):
                    errors.append(
                        f"Branch {branch_index + 1}, Condition {j + 1}: Operator is required"
                    )

                operator = cond.get("operator", "")
                if (
                    operator not in ["is_empty", "is_not_empty"]
                    and cond.get("value") is None
                ):
                    errors.append(
                        f"Branch {branch_index + 1}, Condition {j + 1}: Value is required for operator '{operator}'"
                    )

        return errors

    @staticmethod
    def _validate_binary_conditions(config) -> List[str]:
        """Validate binary mode conditions.

        Supports two modes:
        - Passthrough mode: Uses input_source directly (no simple_conditions needed)
        - Legacy mode: Requires simple_conditions with operators

        Args:
            config: Condition configuration

        Returns:
            List of validation errors
        """
        errors = []

        # Check if passthrough mode is active (input_source configured, no simple_conditions)
        has_input_source = (
            hasattr(config, "input_source")
            and config.input_source
            and config.input_source != ""
        )
        has_simple_conditions = (
            config.simple_conditions and len(config.simple_conditions) > 0
        )

        # Passthrough mode: input_source is configured, no simple_conditions needed
        if has_input_source and not has_simple_conditions:
            logger.info("    Binary mode using passthrough boolean evaluation")
            return errors

        # Legacy mode: requires simple_conditions
        if not has_simple_conditions:
            logger.error("    No simple conditions found for binary mode")
            errors.append("At least one condition is required for simple conditions")
            return errors

        # Validate each condition (legacy mode)
        for i, condition in enumerate(config.simple_conditions):
            if not isinstance(condition, dict):
                continue

            if not condition.get("operator"):
                errors.append(f"Condition {i + 1}: Operator is required")

            operator = condition.get("operator", "")
            if (
                operator not in ["is_empty", "is_not_empty"]
                and condition.get("value") is None
            ):
                errors.append(
                    f"Condition {i + 1}: Value is required for operator '{operator}'"
                )

        return errors

    @staticmethod
    def _validate_for_each_node(node: "EnhancedNodeData") -> List[str]:
        """Validate For Each node configuration.

        Args:
            node: For Each node to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not node.for_each_config:
            errors.append("For Each configuration is required for FOR_EACH nodes")
            return errors

        config = node.for_each_config

        source_mode = getattr(config, "source_mode", "specific") or "specific"
        if source_mode == "specific" and not config.source_node_id:
            errors.append(f"For Each node '{node.name}': source node ID is required")

        if not config.field_path or not config.field_path.strip():
            errors.append(f"For Each node '{node.name}': field path is required")

        if config.concurrency_limit < 1:
            errors.append(
                f"For Each node '{node.name}': concurrency limit must be at least 1"
            )

        if config.max_iterations < 1:
            errors.append(
                f"For Each node '{node.name}': max iterations must be at least 1"
            )

        return errors

    @staticmethod
    def _validate_code_executor_node(node: "EnhancedNodeData") -> List[str]:
        """Validate Code Executor node configuration.

        Args:
            node: Code Executor node to validate

        Returns:
            List of validation errors
        """
        errors = []

        if not node.code_executor_config:
            errors.append("Code Executor configuration is required for CODE_EXECUTOR nodes")
            return errors

        config = node.code_executor_config

        if not config.code or not config.code.strip():
            errors.append(f"Code Executor node '{node.name}': code is required")

        if config.language not in ("python", "javascript"):
            errors.append(
                f"Code Executor node '{node.name}': language must be 'python' or 'javascript'"
            )

        if config.timeout_seconds < 1:
            errors.append(
                f"Code Executor node '{node.name}': timeout must be at least 1 second"
            )

        if config.memory_limit_mb < 1:
            errors.append(
                f"Code Executor node '{node.name}': memory limit must be at least 1 MB"
            )

        return errors

    @staticmethod
    def _validate_execution_config(node: "EnhancedNodeData") -> List[str]:
        """Validate execution configuration.

        Args:
            node: Node to validate

        Returns:
            List of validation errors
        """
        errors = []

        if node.execution_timeout <= 0:
            errors.append("Execution timeout must be positive")

        if node.max_retries < 0:
            errors.append("Max retries cannot be negative")

        return errors
