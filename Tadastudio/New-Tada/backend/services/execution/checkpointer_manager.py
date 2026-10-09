"""
Thread-local checkpointer manager for event loop isolation.

Provides checkpointer instances that are bound to the current thread's event loop,
preventing asyncio.Lock binding conflicts across different execution threads.
"""

import asyncio
import concurrent.futures
import threading

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from backend.services.config import get_logger

from .checkpointer import POSTGRES_AVAILABLE, build_postgres_connection_string

if POSTGRES_AVAILABLE:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

logger = get_logger("execution.checkpointer_manager")


class ThreadLocalCheckpointerManager:
    """
    Manages thread-local checkpointer instances.

    Each thread gets its own checkpointer instance bound to its event loop,
    preventing asyncio.Lock conflicts when execution spans multiple threads/loops.
    """

    def __init__(self):
        self._local = threading.local()
        self._conn_string = build_postgres_connection_string()
        self._use_postgres = self._conn_string is not None and POSTGRES_AVAILABLE

    def get_checkpointer(self) -> BaseCheckpointSaver:
        """
        Get or create a checkpointer for the current thread.

        Note: When called from an async context (running event loop), this
        creates checkpointers in a worker thread whose internal asyncio.Lock
        objects will be bound to that worker's temporary event loop.  If the
        checkpointer is later used from the main async loop (e.g. via
        ``get_checkpointer_async()``), those Locks will fail.  Prefer
        ``get_checkpointer_async()`` in async code.

        Returns:
            A checkpointer instance bound to the current thread's event loop
        """
        # Check if we already have a checkpointer for this thread
        if (
            hasattr(self._local, "checkpointer")
            and self._local.checkpointer is not None
        ):
            return self._local.checkpointer

        # Create new checkpointer for this thread
        if self._use_postgres:
            try:
                checkpointer = self._create_postgres_checkpointer()
                self._local.checkpointer = checkpointer
                logger.debug(
                    f"Created PostgreSQL checkpointer for thread {threading.current_thread().name}"
                )
                return checkpointer
            except Exception as e:
                logger.warning(
                    f"Failed to create PostgreSQL checkpointer: {e}, using MemorySaver"
                )

        # Fallback to MemorySaver
        self._local.checkpointer = MemorySaver()
        logger.debug(
            f"Created MemorySaver for thread {threading.current_thread().name}"
        )
        return self._local.checkpointer

    async def get_checkpointer_async(self) -> BaseCheckpointSaver:
        """
        Get or create a checkpointer for the current thread, running async
        initialisation on the caller's event loop.

        Preferred over get_checkpointer() when called from an async context
        because it initialises the connection pool on the same loop that will
        drive graph execution, avoiding cross-loop I/O hangs.

        Includes event-loop validation: if a cached checkpointer was created by
        the synchronous ``get_checkpointer()`` path (which delegates to a worker
        thread with its own temporary event loop), its internal ``asyncio.Lock``
        will be bound to that dead loop.  This method detects the mismatch and
        recreates the checkpointer on the current loop.

        Also serialises creation so that concurrent coroutines (e.g. evaluation
        test cases fanned out via ``asyncio.gather``) share a single checkpointer
        instead of each racing to create their own.

        Returns:
            A checkpointer instance bound to the current event loop
        """
        current_loop = asyncio.get_running_loop()

        # Check cache with event-loop validation
        cached = getattr(self._local, "checkpointer", None)
        if cached is not None:
            # AsyncPostgresSaver stores the loop it was created on as self.loop.
            # If the cached instance was built on a different loop (e.g. a worker
            # thread's temporary loop from the sync path), its internal
            # asyncio.Lock is bound to that dead loop and will raise
            # "bound to a different event loop" on acquire.  Discard it.
            stale = (
                POSTGRES_AVAILABLE
                and isinstance(cached, AsyncPostgresSaver)
                and getattr(cached, "loop", None) is not current_loop
            )
            if stale:
                logger.warning(
                    "Cached checkpointer bound to different event loop "
                    "(likely created via sync path), recreating on current loop"
                )
                self._local.checkpointer = None
            else:
                return cached

        # Serialise creation: if another coroutine is already creating,
        # wait for it to finish then use its result.
        init_event = getattr(self._local, "_checkpointer_init_event", None)
        if init_event is not None:
            await init_event.wait()
            cached = getattr(self._local, "checkpointer", None)
            if cached is not None:
                return cached

        # We are the first coroutine — create the checkpointer.
        self._local._checkpointer_init_event = asyncio.Event()
        try:
            if self._use_postgres:
                try:
                    checkpointer = await self._create_postgres_checkpointer_async()
                    self._local.checkpointer = checkpointer
                    logger.debug(
                        f"Created PostgreSQL checkpointer (async) for thread "
                        f"{threading.current_thread().name}"
                    )
                    return checkpointer
                except Exception as e:
                    logger.warning(
                        f"Failed to create PostgreSQL checkpointer (async): {e}, "
                        f"using MemorySaver"
                    )

            self._local.checkpointer = MemorySaver()
            logger.debug(
                f"Created MemorySaver for thread {threading.current_thread().name}"
            )
            return self._local.checkpointer
        finally:
            self._local._checkpointer_init_event.set()
            self._local._checkpointer_init_event = None

    async def _create_postgres_checkpointer_async(self) -> BaseCheckpointSaver:
        """
        Create a PostgreSQL checkpointer on the *current* running event loop.

        By awaiting directly on the caller's loop the pool is bound to the same
        loop that will drive graph execution, eliminating cross-loop I/O hangs.
        """
        pool = AsyncConnectionPool(
            conninfo=self._conn_string,
            max_size=5,  # Smaller pool per thread
            open=False,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )
        try:
            await pool.open()
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()
            return checkpointer
        except Exception as e:
            logger.warning(f"Checkpointer creation failed, closing pool: {e}")
            try:
                await pool.close()
            except Exception as close_error:
                logger.warning(f"Error closing pool during cleanup: {close_error}")
            raise

    def _create_postgres_checkpointer(self) -> BaseCheckpointSaver:
        """
        Create a PostgreSQL checkpointer bound to current thread's event loop.

        When no event loop is running this uses asyncio.run() directly.
        When a loop IS already running a worker thread is used, but with
        shutdown(wait=False) to prevent a permanent deadlock: if the DB
        connection hangs and future.result(timeout=30) fires, the `with`
        context-manager pattern would call shutdown(wait=True) and block
        forever — suppressing the TimeoutError and freezing the execution
        thread silently.  shutdown(wait=False) returns immediately so the
        TimeoutError propagates and the caller falls back to MemorySaver.
        """

        async def _create():
            pool = AsyncConnectionPool(
                conninfo=self._conn_string,
                max_size=5,  # Smaller pool per thread
                open=False,
                kwargs={"autocommit": True, "row_factory": dict_row},
            )
            try:
                await pool.open()
                checkpointer = AsyncPostgresSaver(pool)
                await checkpointer.setup()
                return checkpointer
            except Exception as e:
                # Ensure pool is closed on any failure to prevent resource leaks
                logger.warning(f"Checkpointer creation failed, closing pool: {e}")
                try:
                    await pool.close()
                except Exception as close_error:
                    logger.warning(f"Error closing pool during cleanup: {close_error}")
                raise

        # Get or create event loop for this thread
        try:
            asyncio.get_running_loop()
            # A loop is already running (e.g. called synchronously from inside an
            # async context).  We must not call loop.run_until_complete() here, so
            # we delegate to a worker thread.
            #
            # IMPORTANT: do NOT use `with ThreadPoolExecutor() as executor:`.
            # That context manager calls executor.shutdown(wait=True) on __exit__,
            # which blocks indefinitely when the worker thread hangs (e.g. the DB
            # is unreachable and asyncio.run() never returns).  Use explicit
            # shutdown(wait=False) in a finally block instead.
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(lambda: asyncio.run(_create()))
            try:
                return future.result(timeout=30)
            except concurrent.futures.TimeoutError:
                logger.warning(
                    "PostgreSQL checkpointer init timed out after 30 s; "
                    "falling back to MemorySaver"
                )
                raise
            finally:
                # shutdown(wait=False) returns immediately, leaving any lingering
                # worker thread to finish (or be GC'd) on its own.
                executor.shutdown(wait=False)
        except RuntimeError:
            # No running loop - create one
            return asyncio.run(_create())

    def cleanup_thread(self) -> None:
        """Clean up checkpointer for current thread."""
        if (
            hasattr(self._local, "checkpointer")
            and self._local.checkpointer is not None
        ):
            # Close connection pool if PostgreSQL
            checkpointer = self._local.checkpointer
            if hasattr(checkpointer, "pool"):
                try:
                    asyncio.run(checkpointer.pool.close())
                except Exception as e:
                    logger.warning(f"Error closing checkpointer pool: {e}")
            self._local.checkpointer = None
            logger.debug(
                f"Cleaned up checkpointer for thread {threading.current_thread().name}"
            )


# Global manager instance
_checkpointer_manager: ThreadLocalCheckpointerManager | None = None


def get_checkpointer_manager() -> ThreadLocalCheckpointerManager:
    """Get the global checkpointer manager instance."""
    global _checkpointer_manager
    if _checkpointer_manager is None:
        _checkpointer_manager = ThreadLocalCheckpointerManager()
    return _checkpointer_manager


def get_thread_checkpointer() -> BaseCheckpointSaver:
    """Convenience function to get checkpointer for current thread."""
    return get_checkpointer_manager().get_checkpointer()
