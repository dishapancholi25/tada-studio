"""Execution metadata tracking for document search tool."""

import contextvars
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

from .schemas import DocumentSearchConfig, DocumentSearchExecutionMetadata


logger = logging.getLogger(__name__)

# Context-local storage: each asyncio task (i.e., each request) gets its own values,
# preventing concurrent document searches from overwriting each other's metadata.
_last_execution_var: contextvars.ContextVar[
    Optional[DocumentSearchExecutionMetadata]
] = contextvars.ContextVar("doc_search_last_execution", default=None)
_node_executions_var: contextvars.ContextVar[
    Optional[Dict[str, DocumentSearchExecutionMetadata]]
] = contextvars.ContextVar("doc_search_node_executions", default=None)


class ExecutionStorage:
    """Context-local storage for document search execution metadata.

    Uses contextvars.ContextVar so that concurrent requests each see only their own
    execution metadata, preventing race conditions on the shared singleton.
    """

    def store(
        self,
        node_id: Optional[str],
        metadata: DocumentSearchExecutionMetadata,
    ) -> None:
        """Store execution metadata.

        Args:
            node_id: Optional node identifier
            metadata: Execution metadata to store
        """
        _last_execution_var.set(metadata)
        if node_id:
            node_map = _node_executions_var.get(None)
            if node_map is None:
                node_map = {}
                _node_executions_var.set(node_map)
            node_map[node_id] = metadata
            logger.debug(f"Stored document search execution for node: {node_id}")

    def get_last(self) -> Optional[DocumentSearchExecutionMetadata]:
        """Get the most recent execution metadata for the current request context.

        Returns:
            Most recent execution metadata or None
        """
        return _last_execution_var.get(None)

    def get_for_node(self, node_id: str) -> Optional[DocumentSearchExecutionMetadata]:
        """Get execution metadata for a specific node.

        Args:
            node_id: Node identifier

        Returns:
            Execution metadata for the node or None
        """
        node_map = _node_executions_var.get(None) or {}
        return node_map.get(node_id)

    def clear(self) -> None:
        """Clear all stored execution metadata for the current request context."""
        _last_execution_var.set(None)
        _node_executions_var.set(None)
        logger.debug("Cleared document search execution storage")


# Global execution storage instance
_execution_storage = ExecutionStorage()


def get_execution_storage() -> ExecutionStorage:
    """Get the global execution storage instance.

    Returns:
        Global ExecutionStorage instance
    """
    return _execution_storage


def attach_execution_metadata(
    node_id: Optional[str] = None,
) -> Callable:
    """Attach execution metadata to search function.

    Args:
        node_id: Optional node identifier for tracking

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(query: str, *args, **kwargs) -> Any:
            # Get config from kwargs or use defaults
            config = kwargs.get("config")
            if not config:
                # Try to construct config from kwargs
                config = DocumentSearchConfig(
                    collection_names=kwargs.get("collection_names", []),
                    document_ids=kwargs.get("document_ids", []),
                    search_k=kwargs.get("search_k", 3),
                    search_type=kwargs.get("search_type", "similarity"),
                )

            import time

            start_time = time.time()

            # Execute the actual search
            result = func(query, *args, **kwargs)

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Determine result count (approximate from result string)
            result_count = 0
            if isinstance(result, str):
                # Count number of references/results in structured format
                if "## References" in result:
                    result_count = result.count("[") - result.count("##")
                elif result.startswith("No relevant"):
                    result_count = 0
                else:
                    # Estimate based on paragraph breaks
                    result_count = max(1, result.count("\n\n"))

            # Determine search mode used
            search_mode_used = "similarity"
            if config.hybrid_search_enabled:
                if config.search_mode == "hybrid":
                    search_mode_used = "hybrid"
                elif config.search_mode == "keyword":
                    search_mode_used = "keyword"

            # Retrieve query embedding cost from search service
            embedding_tokens = 0
            embedding_cost_val = 0.0
            try:
                from ...services.document_storage.search_service import (
                    get_last_query_embedding_cost,
                )

                query_embedding_cost = get_last_query_embedding_cost()
                if query_embedding_cost:
                    embedding_tokens = query_embedding_cost.get("tokens", 0)
                    embedding_cost_val = query_embedding_cost.get("cost", 0.0)
            except Exception:
                pass

            # Create metadata
            metadata = DocumentSearchExecutionMetadata(
                query=query,
                config=config,
                result_count=result_count,
                search_time_ms=execution_time_ms,
                collections_searched=config.collection_names,
                documents_searched=config.document_ids,
                search_mode_used=search_mode_used,
                embedding_tokens=embedding_tokens,
                embedding_cost=embedding_cost_val,
            )

            # Store metadata
            _execution_storage.store(node_id, metadata)

            return result

        return wrapper

    return decorator


def get_last_document_search_execution() -> Optional[DocumentSearchExecutionMetadata]:
    """Get metadata from the most recent document search execution.

    Returns:
        Most recent execution metadata or None
    """
    return _execution_storage.get_last()


def get_document_search_execution_for_node(
    node_id: str,
) -> Optional[DocumentSearchExecutionMetadata]:
    """Get metadata for a specific node's document search execution.

    Args:
        node_id: Node identifier

    Returns:
        Execution metadata for the node or None
    """
    return _execution_storage.get_for_node(node_id)
