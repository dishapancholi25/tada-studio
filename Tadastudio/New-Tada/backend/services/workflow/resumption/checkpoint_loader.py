"""
Checkpoint loading utilities for subworkflow resumption.

This module handles loading parent graphs and finding subworkflow nodes
from checkpoint metadata.
"""

from typing import Any, Optional

from .utils import log_error, log_info, parse_parent_graph_name


class CheckpointLoader:
    """Handles loading graph and node information from checkpoints."""

    def __init__(self, graph_manager):
        """
        Initialize the checkpoint loader.

        Args:
            graph_manager: The graph manager for accessing graphs
        """
        self.graph_manager = graph_manager

    def load_parent_graph(self, parent_thread_id: str) -> Optional[Any]:
        """
        Load the parent graph from a thread ID.

        Args:
            parent_thread_id: The parent workflow's thread ID

        Returns:
            The loaded graph, or None if loading failed
        """
        parent_graph_name = parse_parent_graph_name(parent_thread_id)
        log_info(f"Loading parent graph: {parent_graph_name}")

        # Try to get from cache first
        parent_graph = self.graph_manager.get_graph(parent_graph_name)

        # If not in cache, load it
        if not parent_graph:
            parent_graph = self.graph_manager.load_graph(parent_graph_name, "default")

        if not parent_graph:
            log_error(f"Could not load parent graph: {parent_graph_name}")
            return None

        log_info(f"Successfully loaded parent graph: {parent_graph_name}")
        return parent_graph

    def find_subworkflow_node(
        self, parent_graph: Any, subworkflow_name: str
    ) -> Optional[Any]:
        """
        Find a subworkflow node in the parent graph.

        Args:
            parent_graph: The parent graph to search
            subworkflow_name: Name of the subworkflow to find

        Returns:
            The subworkflow node, or None if not found
        """
        from backend.models.workflow import NodeType

        log_info(f"Searching for subworkflow node: {subworkflow_name}")

        for node in parent_graph.nodes:
            if node.type == NodeType.SUBWORKFLOW and node.name == subworkflow_name:
                log_info(f"Found subworkflow node: {node.name}")
                return node

        log_error(f"Could not find subworkflow node: {subworkflow_name}")
        return None
