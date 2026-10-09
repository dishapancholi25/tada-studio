"""
Async Checkpointer Adapter for LangGraph.

This module provides an adapter that wraps synchronous checkpointer implementations
to provide async methods required by LangGraph's astream functionality. It includes
proper resource management, cancellation handling, and automatic retry logic for
connection errors.
"""

import asyncio
import inspect
from typing import Any, Dict, Optional, Set

from backend.services.config import get_logger


adapter_logger = get_logger("execution.checkpoint_adapter")


class AsyncCheckpointerAdapter:
    """
    Adapter to provide async checkpointer methods by delegating to sync ones.

    Used when the underlying checkpointer (e.g., PostgresSaver, MemorySaver) lacks
    async methods required by LangGraph's astream. Includes proper resource management
    and cancellation handling for graceful shutdown.

    Features:
    - Runs synchronous checkpointer methods in thread pool
    - Automatic retry with exponential backoff for connection errors
    - Tracks active tasks for cleanup on cancellation
    - Forwards unknown attributes to the inner checkpointer

    Args:
        inner: The synchronous checkpointer implementation to wrap

    Example:
        >>> from langgraph.checkpoint.postgres import PostgresSaver
        >>> sync_checkpointer = PostgresSaver(connection_string)
        >>> async_checkpointer = AsyncCheckpointerAdapter(sync_checkpointer)
        >>> # Now can be used with LangGraph's async streaming
    """

    def __init__(self, inner: Any):
        """
        Initialize the adapter with a synchronous checkpointer.

        Args:
            inner: The synchronous checkpointer to wrap (e.g., PostgresSaver, MemorySaver)
        """
        self._inner = inner
        self._active_tasks: Set[asyncio.Task] = set()
        adapter_logger.info("AsyncCheckpointerAdapter initialized")

    def __getattr__(self, name: str) -> Any:
        """
        Delegate unknown attributes to the inner checkpointer.

        This allows the adapter to pass through any attributes or methods
        that aren't explicitly overridden.

        Args:
            name: The attribute name to retrieve

        Returns:
            The attribute from the inner checkpointer
        """
        return getattr(self._inner, name)

    @staticmethod
    def _call_sync(func: callable, *args, **kwargs) -> Any:
        """
        Call a sync function with only the kwargs it accepts.

        Inspects the function signature and filters out any kwargs that
        aren't accepted by the function to avoid TypeErrors.

        Args:
            func: The function to call
            *args: Positional arguments
            **kwargs: Keyword arguments (will be filtered)

        Returns:
            The result of calling func with filtered arguments
        """
        sig = inspect.signature(func)
        accepted = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return func(*args, **accepted)

    async def _run_in_thread_with_cleanup(self, func: callable, *args, **kwargs) -> Any:
        """
        Run a sync function in a thread with proper cleanup and retry logic.

        This method:
        1. Tracks the current task for cleanup on cancellation
        2. Runs the sync function in a thread pool
        3. Retries on connection errors with exponential backoff
        4. Properly handles cancellation
        5. Cleans up task tracking

        Args:
            func: The synchronous function to run
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function call

        Raises:
            asyncio.CancelledError: If the task is cancelled
            Exception: Any exception from the function after retries exhausted
        """
        task = asyncio.current_task()
        self._active_tasks.add(task)
        max_retries = 3
        retry_delay = 0.5

        try:
            for attempt in range(max_retries):
                try:
                    return await asyncio.to_thread(func, *args, **kwargs)
                except asyncio.CancelledError:
                    adapter_logger.debug(
                        f"Task cancelled in AsyncCheckpointerAdapter: "
                        f"{func.__name__ if hasattr(func, '__name__') else 'unknown'}"
                    )
                    raise
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check if it's a connection error that might be recoverable
                    is_connection_error = any(
                        err in error_msg
                        for err in [
                            "ssl error",
                            "connection",
                            "closed",
                            "eof detected",
                            "bad length",
                        ]
                    )

                    if is_connection_error and attempt < max_retries - 1:
                        adapter_logger.warning(
                            f"Connection error in AsyncCheckpointerAdapter "
                            f"(attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        # Exponential backoff
                        await asyncio.sleep(retry_delay * (2**attempt))
                        continue

                    adapter_logger.error(f"Error in AsyncCheckpointerAdapter: {e}")
                    raise
        finally:
            self._active_tasks.discard(task)

    async def aget_tuple(
        self,
        config: Dict[str, Any],
        *,
        filter_criteria: Optional[Dict[str, Any]] = None,
        before: Optional[Any] = None,
    ) -> Any:
        """
        Async version of get_tuple.

        Retrieves a checkpoint tuple for the given configuration.

        Args:
            config: Configuration dict with thread_id in configurable
            filter_criteria: Optional filter criteria
            before: Optional before timestamp

        Returns:
            The checkpoint tuple
        """
        adapter_logger.debug(
            f"aget_tuple called with thread_id: "
            f"{config.get('configurable', {}).get('thread_id')}"
        )
        return await self._run_in_thread_with_cleanup(
            self._call_sync,
            self._inner.get_tuple,
            config,
            filter=filter_criteria,
            before=before,
        )

    async def aget(self, config: Dict[str, Any]) -> Any:
        """
        Async version of get.

        Retrieves a checkpoint for the given configuration.

        Args:
            config: Configuration dict with thread_id in configurable

        Returns:
            The checkpoint
        """
        adapter_logger.debug(
            f"aget called with thread_id: "
            f"{config.get('configurable', {}).get('thread_id')}"
        )
        return await self._run_in_thread_with_cleanup(self._inner.get, config)

    async def alist(
        self,
        config: Dict[str, Any],
        *,
        filter_criteria: Optional[Dict[str, Any]] = None,
        before: Optional[Any] = None,
        limit: Optional[int] = None,
    ) -> list:
        """
        Async version of list.

        Lists checkpoints for the given configuration.

        Args:
            config: Configuration dict with thread_id in configurable
            filter_criteria: Optional filter criteria
            before: Optional before timestamp
            limit: Optional limit on number of results

        Returns:
            List of checkpoints
        """
        adapter_logger.debug(
            f"alist called with thread_id: "
            f"{config.get('configurable', {}).get('thread_id')}"
        )

        def _list():
            return list(
                self._call_sync(
                    self._inner.list,
                    config,
                    filter=filter_criteria,
                    before=before,
                    limit=limit,
                )
            )

        return await self._run_in_thread_with_cleanup(_list)

    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Any,
        metadata: Dict[str, Any],
        parent_config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Async version of put.

        Saves a checkpoint with the given configuration and metadata.

        Args:
            config: Configuration dict with thread_id in configurable
            checkpoint: The checkpoint data to save
            metadata: Metadata to associate with the checkpoint
            parent_config: Optional parent configuration

        Returns:
            Result of the put operation
        """
        adapter_logger.debug(
            f"aput called with thread_id: "
            f"{config.get('configurable', {}).get('thread_id')}"
        )
        return await self._run_in_thread_with_cleanup(
            self._inner.put, config, checkpoint, metadata, parent_config
        )

    async def aput_writes(
        self, config: Dict[str, Any], writes: list, task_id: str
    ) -> Any:
        """
        Async version of put_writes.

        Saves intermediate writes during checkpoint creation.

        Args:
            config: Configuration dict with thread_id in configurable
            writes: List of writes to save
            task_id: Task identifier

        Returns:
            Result of the put_writes operation
        """
        adapter_logger.debug(
            f"aput_writes called with thread_id: "
            f"{config.get('configurable', {}).get('thread_id')}"
        )
        return await self._run_in_thread_with_cleanup(
            self._inner.put_writes, config, writes, task_id
        )

    async def adelete_thread(self, thread_id: str) -> Any:
        """
        Async version of delete_thread.

        Deletes all checkpoints for a given thread.

        Args:
            thread_id: The thread ID to delete

        Returns:
            Result of the delete operation
        """
        adapter_logger.debug(f"adelete_thread called for thread_id: {thread_id}")
        return await self._run_in_thread_with_cleanup(
            self._inner.delete_thread, thread_id
        )

    async def cleanup(self) -> None:
        """
        Cancel all active tasks for proper shutdown.

        This method should be called when shutting down the application
        to ensure all pending checkpoint operations are properly cancelled.
        """
        adapter_logger.info(
            f"Cleaning up {len(self._active_tasks)} active tasks in AsyncCheckpointerAdapter"
        )
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
        # Wait briefly for tasks to cancel
        await asyncio.sleep(0.1)
        self._active_tasks.clear()
