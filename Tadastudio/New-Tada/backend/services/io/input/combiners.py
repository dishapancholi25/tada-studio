"""
Multi-Source Input Combiners.

This module provides functionality for combining outputs from multiple nodes
into a single input string, with optional labeling and formatting.
"""

from typing import TYPE_CHECKING, Any, Dict, List

from backend.models.workflow import NodeType
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

if TYPE_CHECKING:
    from backend.models import GraphData

combiner_logger = get_logger("io.input.combiners")


class MultiSourceCombiner:
    """
    Combines outputs from multiple nodes into a single input.

    Features:
    - Combines multiple node outputs with separators
    - Optional node name labels
    - Handles missing outputs gracefully
    - Special handling for FILE_READ nodes
    """

    def combine(
        self,
        config: Any,
        source_ids: List[str],
        state: WorkflowState,
        graph: "GraphData",
    ) -> str:
        """
        Combine outputs from multiple source nodes.

        Args:
            config: Input source configuration
            source_ids: List of source node IDs
            state: Current workflow state
            graph: The graph definition

        Returns:
            Combined input string
        """
        outputs = []
        include_labels = (
            hasattr(config, "include_node_labels") and config.include_node_labels
        )

        combiner_logger.info(
            f"[MULTI-SOURCE] Combining {len(source_ids)} sources, "
            f"labels: {include_labels}"
        )

        for node_id in source_ids:
            output = self._extract_node_output(node_id, state, graph)
            if output:
                if include_labels:
                    node_name = self._get_node_name(node_id, graph)
                    outputs.append(f"[{node_name}]:\n{output}")
                else:
                    outputs.append(output)

        result = "\n\n---\n\n".join(outputs)

        combiner_logger.info(
            f"[MULTI-SOURCE] Combined {len(outputs)} outputs, "
            f"total length: {len(result)}"
        )
        combiner_logger.info(
            f"[MULTI-SOURCE] Result preview: {result[:200] if result else 'Empty'}..."
        )

        return result

    def _extract_node_output(
        self, node_id: str, state: WorkflowState, graph: "GraphData"
    ) -> str:
        """
        Extract output from a specific node.

        Args:
            node_id: Node ID to extract from
            state: Current workflow state
            graph: The graph definition

        Returns:
            Node output string or empty string if not found
        """
        output = state.get("node_outputs", {}).get(node_id, {})

        combiner_logger.info(
            f"[MULTI-SOURCE] Processing source {node_id}: found output: {bool(output)}"
        )

        if not output:
            return ""

        raw_output = output.get("raw", "")

        # Enhanced debug logging for FILE_READ nodes
        if self._is_file_read_node(node_id, graph):
            self._log_file_read_output(node_id, output, raw_output)

        combiner_logger.info(
            f"[MULTI-SOURCE] Output from {node_id}: "
            f"{raw_output[:100] if raw_output else 'None'}..."
        )

        return raw_output

    def _is_file_read_node(self, node_id: str, graph: "GraphData") -> bool:
        """Check if node is a FILE_READ type."""
        for node in graph.nodes:
            if node.uniq_id == node_id:
                return node.type == NodeType.FILE_READ
        return False

    def _log_file_read_output(
        self, node_id: str, output: Dict[str, Any], raw_output: str
    ):
        """Log detailed information for FILE_READ node outputs."""
        combiner_logger.info(
            f"[MULTI-SOURCE FILE_READ] Output structure: {list(output.keys())}"
        )
        combiner_logger.info(
            f"[MULTI-SOURCE FILE_READ] Raw content type: {type(raw_output)}"
        )
        combiner_logger.info(
            f"[MULTI-SOURCE FILE_READ] Raw content length: "
            f"{len(raw_output) if raw_output else 0}"
        )

        if output.get("structured"):
            structured_content = output.get("structured", {}).get("content", "")
            combiner_logger.info(
                f"[MULTI-SOURCE FILE_READ] Structured content length: "
                f"{len(structured_content) if structured_content else 0}"
            )

    def _get_node_name(self, node_id: str, graph: "GraphData") -> str:
        """
        Get node name from graph by ID.

        Args:
            node_id: Node ID to look up
            graph: The graph definition

        Returns:
            Node name or node ID if not found
        """
        for node in graph.nodes:
            if node.uniq_id == node_id:
                return node.name
        return node_id  # Fallback to ID if name not found
