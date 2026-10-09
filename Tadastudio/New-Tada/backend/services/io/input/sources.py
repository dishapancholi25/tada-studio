"""
Input Source Handlers.

This module provides handlers for different input sources:
- Start: Use original workflow input
- Previous: Use output from previous node
- Specific: Use output from specific node(s)
- Custom: Use custom template with substitutions
- Field: Extract field from workflow state
"""

import json
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.config import get_logger
from backend.services.workflow.state import WorkflowState

if TYPE_CHECKING:
    from backend.models import GraphData

source_logger = get_logger("io.input.sources")


class InputSource(ABC):
    """Base class for input sources."""

    @abstractmethod
    def extract(
        self, node: EnhancedNodeData, state: WorkflowState, graph: "GraphData"
    ) -> str:
        """
        Extract input from this source.

        Args:
            node: The node to build input for
            state: Current workflow state
            graph: The graph definition

        Returns:
            Extracted input string
        """
        pass


class StartInputSource(InputSource):
    """Extract input from workflow start (original message)."""

    def extract(
        self, node: EnhancedNodeData, state: WorkflowState, graph: "GraphData"
    ) -> str:
        """Extract original workflow message."""
        return state.get("original_message", "")


class PreviousInputSource(InputSource):
    """Extract input from previous node's output."""

    # Node types that are routing-only (no data output) and should be
    # traversed through when looking for the previous data-producing node.
    _PASSTHROUGH_TYPES = {NodeType.CONDITION}

    def extract(
        self, node: EnhancedNodeData, state: WorkflowState, graph: "GraphData"
    ) -> str:
        """Extract input from previous node's output using node_outputs.

        This uses the LangGraph pattern of storing node outputs in the state's
        node_outputs dictionary, which properly tracks execution results.

        Condition nodes are routing-only and produce no data output, so this
        method traverses through them to find the nearest upstream
        data-producing node.
        """
        # Get the current node being executed
        current_node_id = node.uniq_id

        # Find incoming connections to this node
        incoming_nodes = self._find_incoming_nodes(current_node_id, graph)

        if not incoming_nodes:
            # First node - use original workflow input
            source_logger.info(
                f"[PREVIOUS] No incoming nodes for {node.name}, using original_message"
            )
            return state.get("original_message", "")

        # Get node outputs from state
        node_outputs = state.get("node_outputs", {})

        # Get output from the last incoming node.
        # If the incoming node is a pass-through type (e.g. CONDITION) with no
        # meaningful data output, traverse upstream to find the actual
        # data-producing node.
        previous_output = None
        for prev_node_id in reversed(incoming_nodes):
            resolved_id = self._resolve_through_passthrough(
                prev_node_id, node_outputs, graph
            )
            if resolved_id and resolved_id in node_outputs:
                previous_output = node_outputs[resolved_id].get("raw", "")
                if previous_output:
                    source_logger.info(
                        f"[PREVIOUS] {node.name} using output from node {resolved_id}"
                    )
                    break

        if previous_output:
            return previous_output

        # Fallback to original message if no outputs found
        source_logger.warning(
            f"[PREVIOUS] No outputs found for incoming nodes of {node.name}, "
            "using original_message"
        )
        return state.get("original_message", "")

    def _resolve_through_passthrough(
        self,
        node_id: str,
        node_outputs: Dict[str, Any],
        graph: "GraphData",
        _visited: Optional[set] = None,
    ) -> Optional[str]:
        """Resolve a node ID through pass-through (routing-only) nodes.

        If *node_id* refers to a pass-through node (e.g. CONDITION) whose
        ``raw`` output is empty, walk upstream through the graph until a
        data-producing node with non-empty output is found.

        Returns the resolved node ID, or *node_id* itself if it already
        has output.  Returns ``None`` when no data-producing ancestor is
        reachable.
        """
        if _visited is None:
            _visited = set()
        if node_id in _visited:
            return None
        _visited.add(node_id)

        # If this node has non-empty output, it's a data producer — use it.
        output = node_outputs.get(node_id, {})
        if output.get("raw"):
            return node_id

        # Only traverse through known pass-through types.
        graph_node = next((n for n in graph.nodes if n.uniq_id == node_id), None)
        if graph_node is None or graph_node.type not in self._PASSTHROUGH_TYPES:
            return node_id  # Not a pass-through; return as-is even if empty.

        # Walk upstream through the pass-through node.
        upstream_ids = self._find_incoming_nodes(node_id, graph)
        for uid in reversed(upstream_ids):
            resolved = self._resolve_through_passthrough(
                uid, node_outputs, graph, _visited
            )
            if resolved and node_outputs.get(resolved, {}).get("raw"):
                return resolved

        return None

    def _find_incoming_nodes(self, node_id: str, graph: "GraphData") -> List[str]:
        """Find all nodes that connect to this node.

        Args:
            node_id: ID of the target node
            graph: The graph definition

        Returns:
            List of source node IDs that connect to this node
        """
        incoming = []
        for conn in graph.connections:
            # Handle both Connection object and dict formats
            target_id = (
                conn.target_id if hasattr(conn, "target_id") else conn.get("target_id")
            )
            source_id = (
                conn.source_id if hasattr(conn, "source_id") else conn.get("source_id")
            )
            if target_id == node_id:
                incoming.append(source_id)
        return incoming


class SpecificNodeInputSource(InputSource):
    """Extract input from specific node(s) output."""

    def __init__(self, field_extractor: Any = None):
        """
        Initialize specific node input source.

        Args:
            field_extractor: Optional FieldExtractor for structured data
        """
        self.field_extractor = field_extractor

    def extract(
        self, node: EnhancedNodeData, state: WorkflowState, graph: "GraphData"
    ) -> str:
        """Extract input from specific node(s)."""
        config = node.input_source_config
        if not config:
            return ""

        # Get source node IDs
        source_ids = self._get_source_ids(config)
        if not source_ids:
            return ""

        source_logger.info(
            f"[MULTI-SOURCE] Building input for {node.name} from "
            f"{len(source_ids)} source(s)"
        )
        source_logger.info(f"[MULTI-SOURCE] Source IDs: {source_ids}")
        source_logger.info(
            f"[MULTI-SOURCE] Available outputs: "
            f"{list(state.get('node_outputs', {}).keys())}"
        )

        # Log START node requests for debugging
        self._log_start_node_requests(source_ids, state, graph)

        if len(source_ids) == 1:
            return self._extract_single_source(config, source_ids[0], state)
        else:
            return self._extract_multiple_sources(config, source_ids, state, graph)

    def _get_source_ids(self, config) -> List[str]:
        """Extract source node IDs from config."""
        source_ids = []

        # Try source_node_ids (multiple)
        if hasattr(config, "source_node_ids") and config.source_node_ids:
            source_ids = config.source_node_ids

        # Fallback to source_node_id (single)
        if (
            not source_ids
            and hasattr(config, "source_node_id")
            and config.source_node_id
        ):
            source_ids = [config.source_node_id]

        # Filter None values
        return [s for s in source_ids if s]

    def _log_start_node_requests(
        self, source_ids: List[str], state: WorkflowState, graph: "GraphData"
    ):
        """Log START node requests for debugging."""
        for sid in source_ids:
            node_info = next((n for n in graph.nodes if n.uniq_id == sid), None)
            if node_info and node_info.type == NodeType.START:
                source_logger.info(
                    f"[MULTI-SOURCE] Requesting input from START node: {sid}"
                )
                if sid in state.get("node_outputs", {}):
                    source_logger.info(
                        "[MULTI-SOURCE] START node output found in state"
                    )
                else:
                    source_logger.warning(
                        "[MULTI-SOURCE] START node output NOT found in state!"
                    )

    def _extract_single_source(
        self, config, source_id: str, state: WorkflowState
    ) -> str:
        """Extract from single source node."""
        node_output = state.get("node_outputs", {}).get(source_id, {})

        # Check if using structured fields
        use_structured = (
            hasattr(config, "use_structured_field") and config.use_structured_field
        )

        if use_structured and node_output.get("fields"):
            return self._extract_structured_fields(config, node_output)

        return node_output.get("raw", "")

    def _extract_structured_fields(self, config, node_output: Dict[str, Any]) -> str:
        """Extract specific structured fields."""
        fields = node_output.get("fields", {})
        selected_fields = (
            config.selected_fields
            if hasattr(config, "selected_fields") and config.selected_fields
            else []
        )

        if selected_fields:
            selected = {f: fields[f] for f in selected_fields if f in fields}
            if len(selected) > 1:
                return json.dumps(selected)
            elif len(selected) == 1:
                return str(list(selected.values())[0])

        return json.dumps(fields)

    def _extract_multiple_sources(
        self,
        config,
        source_ids: List[str],
        state: WorkflowState,
        graph: "GraphData",
    ) -> str:
        """Extract from multiple source nodes and combine."""
        from .combiners import MultiSourceCombiner

        combiner = MultiSourceCombiner()
        return combiner.combine(config, source_ids, state, graph)


class CustomTemplateInputSource(InputSource):
    """Extract input using custom template with substitutions."""

    def extract(
        self, node: EnhancedNodeData, state: WorkflowState, graph: "GraphData"
    ) -> str:
        """Extract input using custom template."""
        config = node.input_source_config
        if not config or not hasattr(config, "custom_template"):
            return ""

        template = config.custom_template
        if not template:
            return ""

        # Replace {original} with original message
        template = template.replace("{original}", state.get("original_message", ""))

        # Replace {previous} with previous message
        messages = state.get("messages", [])
        if messages:
            template = template.replace("{previous}", messages[-1].content)

        # Replace node outputs: {node_id} and {node_id.field}
        for node_id, output in state.get("node_outputs", {}).items():
            template = template.replace(f"{{{node_id}}}", output.get("raw", ""))

            # Replace field references
            if output.get("fields"):
                for field, value in output["fields"].items():
                    template = template.replace(f"{{{node_id}.{field}}}", str(value))

        return template


class FieldInputSource(InputSource):
    """Extract input from workflow state field using field path."""

    def extract(
        self, node: EnhancedNodeData, state: WorkflowState, graph: "GraphData"
    ) -> str:
        """Extract field from state using field path."""
        config = node.input_source_config
        if not config or not hasattr(config, "source_field_path"):
            return ""

        field_path = config.source_field_path
        if not field_path:
            return ""

        return self._extract_field_from_state(state, field_path, "")

    def _extract_field_from_state(
        self, state: WorkflowState, field_path: str, default: str
    ) -> str:
        """Extract field from state using dot notation."""
        try:
            current = state
            for part in field_path.split("."):
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return default
                if current is None:
                    return default
            return str(current) if current is not None else default
        except Exception:
            return default
