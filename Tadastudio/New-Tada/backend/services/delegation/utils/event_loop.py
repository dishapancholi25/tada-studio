"""Event loop handling utilities for delegation.

This module provides utilities for handling async/sync execution,
event loop detection, and thread-safe async execution.
"""

import asyncio
import concurrent.futures
import contextvars
import gc
from typing import Awaitable, Callable, TypeVar

from backend.services.config import get_logger

logger = get_logger("delegation.event_loop")

T = TypeVar("T")


def _cancel_all_tasks(loop: asyncio.AbstractEventLoop) -> None:
    """Cancel all pending tasks on *loop* and wait for their cancellation.

    This mirrors what asyncio.run() does internally before closing the loop,
    allowing async resource cleanup (e.g. httpx.AsyncClient.aclose()) to
    complete before the loop is torn down.
    """
    to_cancel = asyncio.all_tasks(loop)
    if not to_cancel:
        return
    for task in to_cancel:
        task.cancel()
    loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))


def _graceful_loop_teardown(loop: asyncio.AbstractEventLoop) -> None:
    """Tear down an event loop, minimizing 'Event loop is closed' noise.

    The OpenAI SDK wraps httpx.AsyncClient in AsyncHttpxClientWrapper whose
    __del__ calls ``asyncio.get_running_loop().create_task(self.aclose())``.
    If GC collects these objects after the loop is closed (or on a different
    thread), the resulting task fails with RuntimeError, producing noisy
    "Task exception was never retrieved" warnings.

    Mitigation:
      1. gc.collect() while the loop is set but not running — the SDK's
         ``except Exception: pass`` in __del__ silently absorbs the error.
      2. Standard asyncio teardown (cancel tasks, shutdown generators/executor).
      3. Second gc.collect() for objects freed by step 2.
      4. No-op exception handler before close() to suppress any stragglers.
    """
    try:
        gc.collect()
        _cancel_all_tasks(loop)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        gc.collect()
    except Exception:
        logger.debug("Exception during event loop cleanup", exc_info=True)
    finally:
        loop.set_exception_handler(lambda _loop, _ctx: None)
        asyncio.set_event_loop(None)
        loop.close()


def run_async_in_new_loop(coro: Awaitable[T]) -> T:
    """Run an async coroutine in a new event loop.

    This is useful when you need to run async code from a sync context
    but there's already a running event loop that you can't use.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine

    Raises:
        Any exception raised by the coroutine
    """
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)
    try:
        return new_loop.run_until_complete(coro)
    finally:
        _graceful_loop_teardown(new_loop)


def run_async_in_sync(coro: Awaitable[T], timeout: float = 300) -> T:
    """Run an async coroutine from synchronous code.

    This function handles event loop detection and chooses the appropriate
    execution strategy:
    - If no event loop is running: Use asyncio.run()
    - If event loop is running: Execute in a thread pool with new loop

    Args:
        coro: The coroutine to run
        timeout: Timeout in seconds (default: 300)

    Returns:
        The result of the coroutine

    Raises:
        TimeoutError: If execution exceeds timeout
        Any exception raised by the coroutine
    """
    try:
        # Try to get the current event loop
        asyncio.get_running_loop()
        # We're already in an async context, use threading
        logger.debug("Running async coroutine in thread pool (event loop detected)")
        return _run_in_thread_pool(coro, timeout)
    except RuntimeError as e:
        if "no running event loop" in str(e).lower():
            # No event loop is running, safe to use asyncio.run
            logger.debug("Running async coroutine with asyncio.run (no loop)")
            return asyncio.run(coro)
        else:
            raise


def _run_in_thread_pool(coro: Awaitable[T], timeout: float) -> T:
    """Run a coroutine in a thread pool with a new event loop.

    Args:
        coro: The coroutine to run
        timeout: Timeout in seconds

    Returns:
        The result of the coroutine

    Raises:
        TimeoutError: If execution exceeds timeout
        Any exception raised by the coroutine
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_async_in_new_loop, coro)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Execution timed out after {timeout} seconds")


def run_async_in_sync_isolated(
    coro_factory: Callable[[], Awaitable[T]],
    timeout: float = 300,
) -> T:
    """Run a coroutine factory in sync context with complete context isolation.

    Unlike run_async_in_sync which takes a coroutine, this takes a callable that
    RETURNS a coroutine. The callable is invoked INSIDE a fresh context with no
    inherited context variables, ensuring complete isolation from the parent.

    This is critical for subgraph delegation where we need to prevent the parent
    graph's checkpointer from being inherited through LangChain's context variables.

    IMPORTANT: asyncio.run() copies the current context when it starts. Simply
    deferring coroutine creation is NOT enough - we must also run in a fresh
    contextvars.Context() to prevent LangChain context variables from being
    inherited.

    Args:
        coro_factory: A callable that returns a coroutine
                      (e.g., lambda: subgraph.ainvoke(state))
        timeout: Timeout in seconds (default: 300)

    Returns:
        The result of the coroutine

    Raises:
        TimeoutError: If execution exceeds timeout
        Any exception raised by the coroutine

    Example:
        # Instead of:
        result = run_async_in_sync(subgraph.ainvoke(state, config=config))

        # Use:
        result = run_async_in_sync_isolated(
            lambda: subgraph.ainvoke(state, config={"configurable": {}})
        )
    """

    def _run_in_isolation():
        """Execute in current context (which should be fresh/empty)."""
        try:
            # Try to get the current event loop
            asyncio.get_running_loop()
            # We're already in an async context, use threading with factory
            logger.debug(
                "Running coroutine factory in thread pool (event loop detected)"
            )
            return _run_factory_in_thread_pool(coro_factory, timeout)
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                # No event loop is running, safe to use asyncio.run
                logger.debug(
                    "Running coroutine factory with asyncio.run (fresh context)"
                )

                async def _execute():
                    return await coro_factory()

                return asyncio.run(_execute())
            else:
                raise

    # CRITICAL: Create a completely fresh, empty context.
    # This prevents LangChain/LangGraph context variables (including checkpointer
    # references) from being inherited. asyncio.run() copies the current context,
    # so we must explicitly create an empty one.
    fresh_context = contextvars.Context()
    logger.debug("Running coroutine factory in fresh contextvars.Context()")
    return fresh_context.run(_run_in_isolation)


def _run_factory_in_thread_pool(
    coro_factory: Callable[[], Awaitable[T]],
    timeout: float,
) -> T:
    """Run a coroutine factory in a thread pool with a new event loop.

    The coroutine is created INSIDE the new thread, ensuring complete
    isolation from the parent's context variables.

    Args:
        coro_factory: A callable that returns a coroutine
        timeout: Timeout in seconds

    Returns:
        The result of the coroutine

    Raises:
        TimeoutError: If execution exceeds timeout
        Any exception raised by the coroutine
    """

    def _run():
        async def _execute():
            return await coro_factory()

        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(_execute())
        finally:
            _graceful_loop_teardown(new_loop)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_run)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Execution timed out after {timeout} seconds")
