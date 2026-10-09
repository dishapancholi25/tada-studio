"""
Input Builder for Node Execution.

This module provides functionality for building node inputs from various sources.
Currently wraps the existing _build_node_input method for behavior parity.
Full extraction will happen in Phase 4G (I/O Processing).
"""

from backend.models.workflow import EnhancedNodeData, GraphData
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState


input_builder_logger = get_logger("io.input_builder")


class InputBuilder:
    """
    Builds input data for node execution.

    This class provides methods for constructing input from various sources:
    - Fixed messages
    - Previous node outputs
    - Multiple node outputs combined
    - Template-based construction
    - Memory context integration

    Note: Currently delegates to the main engine's _build_node_input method
    to maintain behavior parity during refactoring. Full extraction planned
    for Phase 4G.

    Example:
        >>> builder = InputBuilder()
        >>> input_message = builder.build(node, state, graph)
    """

    def __init__(self):
        """Initialize input builder."""
        pass

    def build(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: GraphData,
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
        input_builder_logger.debug(f"Building input for node {node.name}")

        # Delegate to the main engine's method for now
        # This maintains behavior parity during refactoring
        from backend.services.execution import get_executor

        executor = get_executor()
        input_message = executor._build_node_input(node, state, graph)

        input_builder_logger.debug(
            f"Built input for {node.name}: {input_message[:100] if len(input_message) > 100 else input_message}..."
        )

        return input_message

    def build_with_memory(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: GraphData,
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

    # Future methods to be implemented in Phase 4G:
    # - _build_from_fixed_message()
    # - _build_from_previous_output()
    # - _build_from_specific_nodes()
    # - _build_from_template()
    # - _extract_structured_fields()
    # - _combine_multiple_sources()
