"""Graph and node validation services.

This module provides comprehensive validation for graphs, nodes, and configurations,
ensuring execution readiness and preventing invalid states.

Example:
    >>> from backend.services.graph.validation import ValidationService
    >>> validator = ValidationService()
    >>> result = validator.validate_graph(graph)
    >>> if not result["valid"]:
    ...     print(f"Errors: {result['errors']}")
"""

from typing import Any, Dict, List, Tuple

from backend.models.workflow import AgentConfig, GraphData, NodeType
from backend.services.config import get_logger

from .constants import (
    LOG_PREFIX_VALIDATION,
    MAX_TEMPERATURE,
    MIN_TEMPERATURE,
    MIN_TIMEOUT,
)
from .exceptions import GraphValidationError


logger = get_logger(__name__)


class ValidationService:
    """Service for validating graphs, nodes, and configurations.

    This service provides comprehensive validation logic for:
    - Graph structure and execution readiness
    - Node configurations
    - LLM configurations
    - Connection validity

    Methods:
        validate_graph: Validate a complete graph for execution
        validate_agent_llm_config: Validate agent LLM configuration
        validate_node_config: Validate node-specific configuration
    """

    def validate_graph(self, graph: GraphData) -> Dict[str, Any]:
        """Validate a graph for execution readiness.

        Performs comprehensive validation including:
        - Presence of required nodes (START, END)
        - Agent node configurations
        - Connection validity
        - Orphaned node detection

        Args:
            graph: The graph to validate

        Returns:
            Dict containing:
                - valid: bool - Whether the graph is valid
                - errors: List[str] - Validation errors
                - warnings: List[str] - Validation warnings

        Example:
            >>> result = validator.validate_graph(my_graph)
            >>> if result["valid"]:
            ...     print("Graph is ready for execution")
        """
        logger.debug(f"{LOG_PREFIX_VALIDATION} Validating graph: {graph.name}")

        errors = []
        warnings = []

        # Check for at least one START node
        start_nodes = [n for n in graph.nodes if n.type == NodeType.START]
        if not start_nodes:
            errors.append("Graph must have at least one START node")
            logger.warning(
                f"{LOG_PREFIX_VALIDATION} Graph '{graph.name}' has no START nodes"
            )

        # Check for at least one END node
        end_nodes = [n for n in graph.nodes if n.type == NodeType.END]
        if not end_nodes:
            warnings.append("Graph has no END nodes")
            logger.debug(
                f"{LOG_PREFIX_VALIDATION} Graph '{graph.name}' has no END nodes"
            )

        # Validate agent nodes
        for node in graph.nodes:
            if node.type == NodeType.AGENT:
                node_errors = self._validate_agent_node(node, graph.name)
                errors.extend(node_errors)

        # Check for orphaned nodes (nodes with no connections)
        orphaned_nodes = self._find_orphaned_nodes(graph)
        if orphaned_nodes:
            for node_name in orphaned_nodes:
                warnings.append(f"Node '{node_name}' has no connections")

        logger.info(
            f"{LOG_PREFIX_VALIDATION} Graph '{graph.name}' validation: "
            f"{len(errors)} errors, {len(warnings)} warnings"
        )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    def _validate_agent_node(self, node: Any, graph_name: str) -> List[str]:
        """Validate an agent node configuration.

        Args:
            node: The agent node to validate
            graph_name: Name of the graph (for error messages)

        Returns:
            List of validation error messages
        """
        errors = []

        if not node.agent_config:
            errors.append(f"Agent node '{node.name}' has no configuration")
            return errors

        # Validate LLM config
        is_valid, config_errors = self.validate_agent_llm_config(node.agent_config)
        if not is_valid:
            errors.extend([f"Agent '{node.name}': {e}" for e in config_errors])

        return errors

    def _find_orphaned_nodes(self, graph: GraphData) -> List[str]:
        """Find nodes with no connections.

        Args:
            graph: The graph to check

        Returns:
            List of orphaned node names
        """
        orphaned = []

        for node in graph.nodes:
            # START and END nodes can be orphaned
            if node.type in [NodeType.START, NodeType.END]:
                continue

            has_connection = any(
                conn.source_id == node.uniq_id or conn.target_id == node.uniq_id
                for conn in graph.connections
            )

            if not has_connection:
                orphaned.append(node.name)

        return orphaned

    def validate_agent_llm_config(
        self, agent_config: AgentConfig
    ) -> Tuple[bool, List[str]]:
        """Validate LLM configuration for an agent.

        Validates:
        - Required fields (provider, model, API key)
        - Provider-specific requirements (Azure, etc.)
        - Parameter ranges (temperature, timeout, etc.)

        Args:
            agent_config: The agent configuration to validate

        Returns:
            Tuple of (is_valid: bool, errors: List[str])

        Example:
            >>> is_valid, errors = validator.validate_agent_llm_config(config)
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Config error: {error}")
        """
        errors = []

        if not agent_config.llm_config:
            errors.append("Agent missing LLM configuration")
            return False, errors

        llm_config = agent_config.llm_config

        # Validate required fields
        if not llm_config.model_deployment_id and not llm_config.provider:
            errors.append("LLM provider not specified")

        if not llm_config.model_name:
            errors.append("LLM model name not specified")

        if not llm_config.model_deployment_id and not llm_config.api_key_env_var:
            errors.append("API key environment variable not specified")

        # Validate provider-specific requirements
        if llm_config.provider == "azure_openai" and not llm_config.model_deployment_id:
            if not llm_config.base_url_env_var:
                errors.append("Azure OpenAI requires base URL environment variable")
            if not llm_config.api_version:
                errors.append("Azure OpenAI requires API version")

        # Validate parameter ranges
        if (
            llm_config.temperature < MIN_TEMPERATURE
            or llm_config.temperature > MAX_TEMPERATURE
        ):
            errors.append(
                f"Temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}"
            )

        if llm_config.max_tokens and llm_config.max_tokens < 1:
            errors.append("Max tokens must be positive")

        if llm_config.timeout < MIN_TIMEOUT:
            errors.append(f"Timeout must be at least {MIN_TIMEOUT} second")

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(
                f"{LOG_PREFIX_VALIDATION} LLM config validation failed: {errors}"
            )

        return is_valid, errors

    def validate_node_config(
        self, node_type: NodeType, config: Any
    ) -> Tuple[bool, List[str]]:
        """Validate node-specific configuration.

        Args:
            node_type: The type of node
            config: The configuration to validate

        Returns:
            Tuple of (is_valid: bool, errors: List[str])
        """
        errors = []

        # Add type-specific validation as needed
        # This is a placeholder for future enhancements

        if node_type == NodeType.AGENT and not config:
            errors.append("Agent node requires configuration")

        return len(errors) == 0, errors

    def raise_if_invalid(self, graph: GraphData) -> None:
        """Validate a graph and raise exception if invalid.

        This is a convenience method that validates and raises an exception
        instead of returning a result dictionary.

        Args:
            graph: The graph to validate

        Raises:
            GraphValidationError: If the graph is invalid

        Example:
            >>> try:
            ...     validator.raise_if_invalid(graph)
            ... except GraphValidationError as e:
            ...     print(f"Validation failed: {e.errors}")
        """
        result = self.validate_graph(graph)

        if not result["valid"]:
            raise GraphValidationError(
                graph.name, result["errors"], result.get("warnings", [])
            )
