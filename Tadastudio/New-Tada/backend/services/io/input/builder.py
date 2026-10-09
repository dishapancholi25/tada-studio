"""
Complete Input Builder Implementation.

This module provides the full input building functionality for node execution,
supporting multiple input sources and combination strategies.
"""

from typing import TYPE_CHECKING

from backend.models.workflow import EnhancedNodeData
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

from .sources import (
    CustomTemplateInputSource,
    FieldInputSource,
    PreviousInputSource,
    SpecificNodeInputSource,
    StartInputSource,
)

if TYPE_CHECKING:
    from backend.models import GraphData

input_builder_logger = get_logger("io.input.builder")


class InputBuilder:
    """
    Complete input builder for node execution.

    This class provides comprehensive input building from various sources:
    - Start: Original workflow input
    - Previous: Last node's output
    - Specific: Specific node(s) output
    - Custom: Custom template with substitutions
    - Field: Field extraction from state

    Example:
        >>> builder = InputBuilder()
        >>> input_message = builder.build(node, state, graph)
    """

    def __init__(self, field_extractor: any = None):
        """
        Initialize input builder.

        Args:
            field_extractor: Optional FieldExtractor for structured data
        """
        self.field_extractor = field_extractor

        # Initialize source handlers
        self.start_source = StartInputSource()
        self.previous_source = PreviousInputSource()
        self.specific_source = SpecificNodeInputSource(field_extractor)
        self.custom_source = CustomTemplateInputSource()
        self.field_source = FieldInputSource()

    def build(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
    ) -> str:
        """
        Build input message for a node.

        Args:
            node: The node to build input for
            state: Current workflow state
            graph: The graph definition

        Returns:
            Input message string
        """
        input_builder_logger.info(
            f"[INPUT-CONFIG] Building input for node {node.name} (ID: {node.uniq_id})"
        )

        # Default to previous message if no config
        if not node.input_source_config:
            return self._build_default_input(node, state, graph)

        config = node.input_source_config

        # Log configuration details
        self._log_config_details(node, config)

        # Get source mode
        source_mode = (
            config.source_mode if hasattr(config, "source_mode") else "previous"
        )

        input_builder_logger.info(f"[INPUT-CONFIG] Resolved source_mode: {source_mode}")

        # Route to appropriate source handler
        input_message = self._route_to_source_handler(source_mode, node, state, graph)

        # Log result
        input_builder_logger.debug(
            f"Built input for {node.name}: "
            f"{input_message[:100] if len(input_message) > 100 else input_message}..."
        )

        return input_message

    def _build_default_input(
        self, node: EnhancedNodeData, state: WorkflowState, graph: "GraphData"
    ) -> str:
        """Build default input from previous node's output.

        Default behavior is "previous" mode - delegates to PreviousInputSource
        for consistency. This ensures default behavior matches explicit "previous"
        source mode and follows LangGraph best practices.
        """
        return self.previous_source.extract(node, state, graph)

    def _log_config_details(self, node: EnhancedNodeData, config):
        """Log configuration details for debugging."""
        from backend.services.execution.logging import redact_sensitive_data

        input_builder_logger.info(f"[INPUT-CONFIG] Config type: {type(config)}")
        input_builder_logger.info(
            f"[INPUT-CONFIG] Config value: {redact_sensitive_data(config)}"
        )

        if config:
            input_builder_logger.info(
                f"[INPUT-CONFIG] Config attributes: "
                f"{dir(config) if hasattr(config, '__dict__') else 'Not an object'}"
            )
            if hasattr(config, "__dict__"):
                input_builder_logger.info(
                    f"[INPUT-CONFIG] Config dict: {redact_sensitive_data(config.__dict__)}"
                )

    def _route_to_source_handler(
        self,
        source_mode: str,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
    ) -> str:
        """
        Route to appropriate source handler based on mode.

        Args:
            source_mode: The input source mode
            node: The node to build input for
            state: Current workflow state
            graph: The graph definition

        Returns:
            Input message from appropriate source
        """
        if source_mode == "start":
            return self.start_source.extract(node, state, graph)

        elif source_mode == "previous":
            return self.previous_source.extract(node, state, graph)

        elif source_mode == "specific":
            return self.specific_source.extract(node, state, graph)

        elif source_mode == "custom":
            return self.custom_source.extract(node, state, graph)

        elif source_mode == "field":
            return self.field_source.extract(node, state, graph)

        else:
            input_builder_logger.warning(
                f"Unknown source_mode: {source_mode}, using default"
            )
            return self._build_default_input(node, state, graph)

    def build_with_memory(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
        memory_context: str = "",
    ) -> str:
        """
        Build input message with memory context prepended.

        Args:
            node: The node to build input for
            state: Current workflow state
            graph: The graph definition
            memory_context: Memory context to prepend

        Returns:
            Input message with memory context
        """
        input_message = self.build(node, state, graph)

        if memory_context:
            input_message = f"{memory_context}\n\nCurrent Message: {input_message}"
            input_builder_logger.info(f"Applied memory context for {node.name}")

        return input_message
