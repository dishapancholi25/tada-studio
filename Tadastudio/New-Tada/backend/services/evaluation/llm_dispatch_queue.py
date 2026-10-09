"""LLM dispatch queue for evaluation workloads.

Provides a fixed-size async worker pool to manage concurrent LLM calls
during evaluation runs, preventing resource exhaustion while ensuring
no requests are dropped.
"""

import asyncio
import os
from typing import Any, Coroutine, Optional

from backend.services.config import get_logger

logger = get_logger("evaluation.llm_dispatch_queue")

DEFAULT_WORKER_COUNT = int(os.getenv("EVAL_LLM_QUEUE_WORKERS", "5"))
DEFAULT_QUEUE_MAX_SIZE = int(os.getenv("EVAL_LLM_QUEUE_MAX_SIZE", "50"))


class EvaluationLLMDispatchQueue:
    """Async worker pool for dispatching LLM calls during evaluation.

    Uses a bounded ``asyncio.Queue`` with a fixed number of workers to provide
    backpressure — callers block on ``submit()`` when the queue is full,
    preventing burst rate-limit failures. Never drops requests.

    Usage:
        queue = EvaluationLLMDispatchQueue.get_instance()
        result = await queue.submit(some_llm_coroutine())
    """

    _instance: Optional["EvaluationLLMDispatchQueue"] = None

    def __init__(
        self,
        worker_count: int = DEFAULT_WORKER_COUNT,
        max_size: int = DEFAULT_QUEUE_MAX_SIZE,
    ):
        self._worker_count = worker_count
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._workers: list[asyncio.Task] = []
        self._started = False
        self._bound_loop: Optional[asyncio.AbstractEventLoop] = None

    @classmethod
    def get_instance(cls) -> "EvaluationLLMDispatchQueue":
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the worker pool. Idempotent — safe to call multiple times.

        Detects when the current event loop differs from the one workers were
        originally bound to (e.g. after an ``asyncio.run()`` cycle) and
        restarts workers on the current loop.
        """
        current_loop = asyncio.get_running_loop()

        if self._started and self._bound_loop is current_loop:
            # Workers are alive on this loop — nothing to do.
            return

        if self._started and self._bound_loop is not current_loop:
            # Workers were created on a now-dead loop.  Reset and restart.
            logger.warning(
                "LLM dispatch queue workers bound to stale event loop — restarting"
            )
            self._workers.clear()
            self._queue = asyncio.Queue(maxsize=self._queue.maxsize)
            self._started = False

        logger.info(f"Starting LLM dispatch queue with {self._worker_count} workers")
        self._started = True
        self._bound_loop = current_loop
        for i in range(self._worker_count):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)

    async def stop(self) -> None:
        """Gracefully stop all workers by sending sentinel values."""
        if not self._started:
            return

        logger.info("Stopping LLM dispatch queue")
        # Send sentinel None for each worker
        for _ in self._workers:
            await self._queue.put(None)

        # Wait for all workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False
        logger.info("LLM dispatch queue stopped")

    async def submit(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Submit a coroutine for execution and await its result.

        If the queue is not started (or workers are stale), it will be
        (re)started automatically.

        Args:
            coro: The coroutine to execute (e.g. an LLM call).

        Returns:
            The result of the coroutine.

        Raises:
            Exception: Re-raises any exception from the coroutine.
        """
        # start() is idempotent and handles stale-loop detection.
        await self.start()

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        await self._queue.put((coro, future))
        return await future

    async def _worker(self, worker_id: int) -> None:
        """Worker loop that processes coroutines from the queue."""
        logger.debug(f"LLM dispatch worker {worker_id} started")
        while True:
            item = await self._queue.get()
            if item is None:
                # Sentinel value — shut down this worker
                self._queue.task_done()
                break

            coro, future = item
            try:
                # Skip work if the caller already cancelled/timed out
                if future.done():
                    coro.close()
                    self._queue.task_done()
                    continue

                task = asyncio.create_task(coro)

                # If the caller cancels while we wait, cancel the LLM task too
                def _on_caller_done(f: asyncio.Future) -> None:
                    if f.cancelled() and not task.done():
                        task.cancel()

                future.add_done_callback(_on_caller_done)

                result = await task
                if not future.done():
                    future.set_result(result)
            except asyncio.CancelledError:
                if not future.done():
                    future.cancel()
            except Exception as exc:
                if not future.done():
                    future.set_exception(exc)
            finally:
                self._queue.task_done()

        logger.debug(f"LLM dispatch worker {worker_id} stopped")


def get_llm_dispatch_queue() -> EvaluationLLMDispatchQueue:
    """Module-level helper to get the singleton dispatch queue."""
    return EvaluationLLMDispatchQueue.get_instance()
