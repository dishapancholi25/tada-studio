"""Execution metadata tracking for web search tool."""

import threading
from typing import Any, Callable, Dict, Optional

from .schemas import WebSearchExecutionMetadata


class ExecutionStorage:
    """Thread-local storage for execution metadata."""

    def __init__(self):
        """Initialize execution storage."""
        self._storage = threading.local()

    def set_last_execution(self, metadata: WebSearchExecutionMetadata) -> None:
        """Store execution metadata in thread-local storage.

        Args:
            metadata: Execution metadata to store
        """
        self._storage.last_execution = metadata

    def get_last_execution(self) -> Optional[WebSearchExecutionMetadata]:
        """Retrieve the last execution metadata.

        Returns:
            Last execution metadata or None if not available
        """
        return getattr(self._storage, "last_execution", None)

    def set_node_execution(
        self, node_id: str, metadata: WebSearchExecutionMetadata
    ) -> None:
        """Store execution metadata for a specific node.

        Args:
            node_id: Node identifier
            metadata: Execution metadata to store
        """
        if not hasattr(self._storage, "node_executions"):
            self._storage.node_executions = {}
        self._storage.node_executions[node_id] = metadata

    def get_node_execution(self, node_id: str) -> Optional[WebSearchExecutionMetadata]:
        """Retrieve execution metadata for a specific node.

        Args:
            node_id: Node identifier

        Returns:
            Execution metadata for the node or None if not available
        """
        if hasattr(self._storage, "node_executions"):
            return self._storage.node_executions.get(node_id)
        return None

    def clear(self) -> None:
        """Clear all stored execution metadata."""
        if hasattr(self._storage, "last_execution"):
            delattr(self._storage, "last_execution")
        if hasattr(self._storage, "node_executions"):
            delattr(self._storage, "node_executions")


# Global execution storage instance
_execution_storage = ExecutionStorage()


def get_execution_storage() -> ExecutionStorage:
    """Get the global execution storage instance.

    Returns:
        Global ExecutionStorage instance
    """
    return _execution_storage


def attach_execution_metadata(
    func: Callable, metadata: WebSearchExecutionMetadata
) -> None:
    """Attach execution metadata to a function for retrieval.

    This is used for backward compatibility with the old _last_execution pattern.

    Args:
        func: Function to attach metadata to
        metadata: Execution metadata to attach
    """
    func._last_execution = {
        "query": metadata.query,
        "provider": metadata.provider,
        "raw_results": metadata.raw_results,
        "formatted_results": metadata.formatted_results,
        "max_results": metadata.max_results,
    }


def get_function_execution_metadata(func: Callable) -> Optional[Dict[str, Any]]:
    """Retrieve execution metadata attached to a function.

    Args:
        func: Function to retrieve metadata from

    Returns:
        Execution metadata dictionary or None
    """
    return getattr(func, "_last_execution", None)
