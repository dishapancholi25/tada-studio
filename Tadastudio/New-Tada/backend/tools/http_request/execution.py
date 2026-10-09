"""Execution metadata tracking for HTTP request tool."""

import threading
from typing import Any, Callable, Dict, Optional

from .schemas import HttpExecutionMetadata


class ExecutionStorage:
    """Storage for execution metadata with cross-thread support.

    Uses a shared dictionary (with locking) for node-specific metadata to support
    async execution where HTTP requests run in thread pool executors but metadata
    is retrieved from the main async context.

    Thread-local storage is kept as a fallback for last_execution.
    """

    def __init__(self):
        """Initialize execution storage."""
        self._thread_local = threading.local()
        # Shared storage for cross-thread access (node-specific metadata)
        self._shared_node_executions: Dict[str, HttpExecutionMetadata] = {}
        self._shared_lock = threading.Lock()

    def set_last_execution(self, metadata: HttpExecutionMetadata) -> None:
        """Store execution metadata in thread-local storage.

        Args:
            metadata: Execution metadata to store
        """
        self._thread_local.last_execution = metadata

    def get_last_execution(self) -> Optional[HttpExecutionMetadata]:
        """Retrieve the last execution metadata.

        Returns:
            Last execution metadata or None if not available
        """
        return getattr(self._thread_local, "last_execution", None)

    def set_node_execution(self, node_id: str, metadata: HttpExecutionMetadata) -> None:
        """Store execution metadata for a specific node in shared storage.

        This uses shared (not thread-local) storage to support async execution
        where the HTTP request runs in a thread pool but metadata is retrieved
        from the main async context.

        Args:
            node_id: Node identifier
            metadata: Execution metadata to store
        """
        with self._shared_lock:
            self._shared_node_executions[node_id] = metadata

    def get_node_execution(self, node_id: str) -> Optional[HttpExecutionMetadata]:
        """Retrieve execution metadata for a specific node from shared storage.

        Args:
            node_id: Node identifier

        Returns:
            Execution metadata for the node or None if not available
        """
        with self._shared_lock:
            return self._shared_node_executions.get(node_id)

    def clear(self) -> None:
        """Clear all stored execution metadata."""
        if hasattr(self._thread_local, "last_execution"):
            delattr(self._thread_local, "last_execution")
        with self._shared_lock:
            self._shared_node_executions.clear()

    def clear_node_execution(self, node_id: str) -> None:
        """Clear execution metadata for a specific node.

        Args:
            node_id: Node identifier to clear
        """
        with self._shared_lock:
            self._shared_node_executions.pop(node_id, None)


# Global execution storage instance
_execution_storage = ExecutionStorage()


def get_execution_storage() -> ExecutionStorage:
    """Get the global execution storage instance.

    Returns:
        Global ExecutionStorage instance
    """
    return _execution_storage


def attach_execution_metadata(func: Callable, metadata: HttpExecutionMetadata) -> None:
    """Attach execution metadata to a function for retrieval.

    This is used for backward compatibility with the old _last_execution pattern.

    Args:
        func: Function to attach metadata to
        metadata: Execution metadata to attach
    """
    func._last_execution = {
        "request": metadata.request,
        "response": metadata.response,
        "config": metadata.config,
        "timestamp": metadata.timestamp,
        "call_id": metadata.call_id,
    }


def get_function_execution_metadata(func: Callable) -> Optional[Dict[str, Any]]:
    """Retrieve execution metadata attached to a function.

    Args:
        func: Function to retrieve metadata from

    Returns:
        Execution metadata dictionary or None
    """
    return getattr(func, "_last_execution", None)


def get_last_http_execution() -> Optional[Dict[str, Any]]:
    """Get the last HTTP execution metadata from thread-local storage.

    Returns:
        Last execution metadata or None
    """
    storage = get_execution_storage()
    metadata = storage.get_last_execution()
    if metadata:
        return {
            "request": metadata.request,
            "response": metadata.response,
            "config": metadata.config,
            "timestamp": metadata.timestamp,
            "call_id": metadata.call_id,
        }
    return None


def get_http_execution_for_node(node_id: str) -> Optional[Dict[str, Any]]:
    """Get HTTP execution metadata for a specific node.

    Args:
        node_id: Node identifier

    Returns:
        Execution metadata for the node or None
    """
    storage = get_execution_storage()
    metadata = storage.get_node_execution(node_id)
    if metadata:
        return {
            "request": metadata.request,
            "response": metadata.response,
            "config": metadata.config,
            "timestamp": metadata.timestamp,
            "call_id": metadata.call_id,
        }
    return None
