"""
For Each Node Executor.

This module handles execution of FOR_EACH nodes, which iterate over arrays
(CSV rows, JSON arrays, etc.) and execute a body subgraph once per item
with bounded concurrency.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.models.workflow.configs.for_each import ForEachConfig
from backend.services.config import ExecutionConfig, get_logger
from backend.services.workflow.state import WorkflowState

from ..base import BaseNodeExecutor
from ..handlers import NodeDatabaseTracker, NodeNotificationHandler


for_each_logger = get_logger("nodes.executors.for_each")


@dataclass
class IterationResult:
    """Result of a single For Each iteration."""

    index: int
    status: Literal["success", "error"]
    input_item: Any
    output: Optional[Dict] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


class AsyncRateLimiter:
    """Simple token bucket rate limiter for controlling iteration throughput."""

    def __init__(self, rate_per_second: float):
        self.rate = rate_per_second
        self.tokens = rate_per_second
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a token, waiting if necessary."""
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


class ForEachNodeExecutor(BaseNodeExecutor):
    """
    Executor for FOR_EACH nodes.

    Iterates over an array from a source node's output and executes a body
    subgraph once per item with bounded concurrency via asyncio.Semaphore.
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        """Initialize For Each node executor."""
        super().__init__(
            execution_history_service, ws_notifier, subgraph_executor, graph_manager
        )
        self.database_tracker = NodeDatabaseTracker(execution_history_service)
        self.notification_handler = NodeNotificationHandler(ws_notifier)

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a For Each node.

        Steps:
        1. Extract items from source node output
        2. Validate items array
        3. Build body subgraph (once, reused)
        4. Execute iterations with bounded concurrency
        5. Aggregate and return results

        Args:
            node: The For Each node to execute
            state: Current workflow state
            graph: The graph definition
            execution_id: Execution identifier
            user_id: Optional user identifier

        Returns:
            State updates with aggregated iteration results
        """
        for_each_logger.info(f"Executing FOR_EACH node: {node.name}")
        execution_start_time = time.time()

        config = node.for_each_config
        if not config:
            raise ValueError(f"For Each node '{node.name}' missing configuration")

        # Create tracking record for the For Each node itself
        node_exec_id = await self.database_tracker.create_node_execution(
            node,
            state,
            "FOR_EACH",
            {"source_node_id": config.source_node_id, "field_path": config.field_path},
        )

        # Notify start
        await self.notification_handler.notify_start(
            node, state, "FOR_EACH", node_exec_id
        )

        try:
            # 1. Extract items from source
            items = self._extract_items(node, state, config, graph)

            # 2. Validate
            if not isinstance(items, list):
                raise ValueError(
                    f"For Each source must resolve to an array. "
                    f"Got {type(items).__name__} at path '{config.field_path}'"
                )

            # Apply the deliberate subset first, so "process the first N of a
            # large source" is a supported request rather than a cap breach.
            source_total = len(items)
            items, skipped = self._apply_item_limit(items, config, node.name)

            # Apply system ceilings on top of the node's own limits
            max_items, concurrency_limit = self._resolve_limits(config, node.name)

            if len(items) > max_items:
                system_max = ExecutionConfig.get_for_each_max_items()
                limit_source = (
                    f"system limit of {system_max} (FOR_EACH_MAX_ITEMS)"
                    if max_items == system_max and config.max_iterations > system_max
                    else f"max_iterations limit of {max_items}"
                )
                raise ValueError(
                    f"For Each source has {len(items)} items, exceeding {limit_source}. "
                    f"Raise Max Iterations to process them all, or set "
                    f"'Process First N Items' to run over a subset on purpose."
                )

            for_each_logger.info(
                f"For Each '{node.name}': processing {len(items)} items "
                f"(concurrency={concurrency_limit})"
            )

            # 3. Handle empty array
            if len(items) == 0:
                node_output = self._build_empty_result()
                await self._complete_execution(
                    node, state, node_exec_id, node_output, execution_start_time
                )
                return self._build_state_update(node, node_output, state)

            # 4. Execute iterations with bounded concurrency
            results = await self._execute_iterations(
                node=node,
                items=items,
                state=state,
                config=config,
                graph=graph,
                concurrency_limit=concurrency_limit,
            )

            # 5. Build aggregated output
            node_output = self._build_output(
                results, items, skipped=skipped, source_total=source_total
            )

            # Complete tracking
            await self._complete_execution(
                node, state, node_exec_id, node_output, execution_start_time
            )

            return self._build_state_update(
                node, node_output, state, iterations_run=len(items)
            )

        except Exception as e:
            for_each_logger.error(f"For Each error for {node.name}: {e}", exc_info=True)
            error_output = {
                "raw": f"For Each failed: {e}",
                "structured": {"error": str(e)},
                "fields": {"error": str(e)},
            }

            await self.database_tracker.fail_node_execution(
                node_exec_id, str(e), error_output
            )
            await self.notification_handler.notify_error(
                node, state, str(e), "FOR_EACH", node_exec_id
            )

            return self._build_state_update(node, error_output, state)

    @staticmethod
    def _iteration_slot_size(config: Any) -> int:
        """How many ordering slots to reserve for one iteration's body.

        Sized from the body node count so an iteration cannot run past its own
        slice, with one spare slot for the iteration's own summary record.

        Args:
            config: The For Each configuration

        Returns:
            Number of ordering slots per iteration (at least 2)
        """
        body_size = len(getattr(config, "body_node_ids", None) or [])
        return max(body_size, 1) + 1

    @classmethod
    def _iteration_order_base(
        cls, parent_state: WorkflowState, index: int, config: Any
    ) -> int:
        """First execution_order value belonging to iteration ``index``.

        Args:
            parent_state: The state the For Each node executed in
            index: Zero-based iteration index
            config: The For Each configuration

        Returns:
            The iteration's starting execution order
        """
        for_each_order = parent_state.get("execution_order", 0) or 0
        return for_each_order + 1 + index * cls._iteration_slot_size(config)

    @classmethod
    def _order_after_iterations(
        cls, parent_state: WorkflowState, total_items: int, config: Any
    ) -> int:
        """First execution_order value free for nodes after the loop.

        Keeps whatever follows the loop (typically END) sorted after every
        body node instead of interleaving with them.

        Args:
            parent_state: The state the For Each node executed in
            total_items: Number of iterations that ran
            config: The For Each configuration

        Returns:
            The next free execution order
        """
        for_each_order = parent_state.get("execution_order", 0) or 0
        return for_each_order + 1 + max(total_items, 0) * cls._iteration_slot_size(
            config
        )

    @staticmethod
    def _apply_item_limit(
        items: List[Any], config: ForEachConfig, node_name: str
    ) -> tuple[List[Any], int]:
        """Trim the source array to the configured deliberate subset.

        Unlike ``max_iterations`` (a safety cap that fails), ``item_limit`` is
        an explicit request to process only the first N items - typically to
        try a loop against a few rows of a large source. The number skipped is
        returned so the node output can report the run as partial.

        Args:
            items: The full source array
            config: The node's For Each configuration
            node_name: Node name, for log messages

        Returns:
            Tuple of (items to process, number of items skipped)
        """
        item_limit = getattr(config, "item_limit", None)
        if not item_limit or item_limit < 1 or len(items) <= item_limit:
            return items, 0

        skipped = len(items) - item_limit
        for_each_logger.info(
            "For Each '%s': item_limit=%d - processing first %d of %d items, "
            "skipping %d",
            node_name,
            item_limit,
            item_limit,
            len(items),
            skipped,
        )
        return items[:item_limit], skipped

    @staticmethod
    def _resolve_limits(config: ForEachConfig, node_name: str) -> tuple[int, int]:
        """Apply system ceilings to a node's configured limits.

        The per-node values are honoured when they are at or below the system
        ceilings, and clamped otherwise. Clamping (rather than rejecting) keeps
        existing workflows runnable while still bounding the work a single node
        can fan out.

        Args:
            config: The node's For Each configuration
            node_name: Node name, for log messages

        Returns:
            Tuple of (effective max items, effective concurrency limit)
        """
        system_max_items = ExecutionConfig.get_for_each_max_items()
        system_max_concurrency = ExecutionConfig.get_for_each_max_concurrency()

        max_items = min(config.max_iterations, system_max_items)
        if config.max_iterations > system_max_items:
            for_each_logger.warning(
                "For Each '%s': max_iterations %d exceeds system limit %d; "
                "capping at %d (FOR_EACH_MAX_ITEMS)",
                node_name,
                config.max_iterations,
                system_max_items,
                system_max_items,
            )

        concurrency_limit = min(config.concurrency_limit, system_max_concurrency)
        if config.concurrency_limit > system_max_concurrency:
            for_each_logger.warning(
                "For Each '%s': concurrency_limit %d exceeds system limit %d; "
                "capping at %d (FOR_EACH_MAX_CONCURRENCY)",
                node_name,
                config.concurrency_limit,
                system_max_concurrency,
                system_max_concurrency,
            )

        return max_items, concurrency_limit

    def _extract_items(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        config: ForEachConfig,
        graph: Any = None,
    ) -> Any:
        """Extract the array from source node output using field path.

        The concrete source node is resolved dynamically based on
        ``config.source_mode``, mirroring how Agent nodes resolve their
        `input_source_config`:
        - "previous": the node directly connected before this For Each node
        - "start": the workflow's START node
        - "specific" (default): the explicitly configured `source_node_id`

        Args:
            node: The For Each node (used to resolve "previous" via graph)
            state: Current workflow state
            config: For Each configuration
            graph: The graph definition, needed for "previous"/"start" modes

        Returns:
            The extracted array value

        Raises:
            ValueError: If source node or path is invalid
        """
        source_node_id = self._resolve_source_node_id(node, config, graph)
        node_outputs = state.get("node_outputs", {})
        source_output = node_outputs.get(source_node_id)
        if source_output is None:
            raise ValueError(f"Source node '{source_node_id}' has no output")

        # Navigate dot-path (e.g., "fields.rows")
        value = source_output
        for part in config.field_path.split("."):
            # If value is a JSON string, try to parse it before traversing
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    raise ValueError(
                        f"Cannot traverse path '{config.field_path}': "
                        f"'{part}' is not accessible on string value"
                    )

            if isinstance(value, dict):
                if part not in value:
                    available = ", ".join(sorted(value.keys())) or "<none>"
                    raise ValueError(
                        f"Cannot traverse path '{config.field_path}': "
                        f"key '{part}' not found in dict. "
                        f"Available keys at this level: {available}"
                    )
                value = value[part]
            else:
                raise ValueError(
                    f"Cannot traverse path '{config.field_path}': "
                    f"'{part}' is not accessible on {type(value).__name__}"
                )

        # If the final value is a JSON string, try to parse it
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    value = parsed
            except (json.JSONDecodeError, TypeError):
                pass

        return value

    @staticmethod
    def _resolve_source_node_id(
        node: EnhancedNodeData,
        config: ForEachConfig,
        graph: Any = None,
    ) -> str:
        """Resolve the actual source node id for the configured source mode.

        Dynamically derives the id from the live graph/connections rather
        than relying on any hardcoded id, so the For Each node stays correct
        even if the workflow is edited (nodes reconnected/reordered) after
        the source mode was chosen.

        Args:
            node: The For Each node itself (used to find its incoming edge)
            config: For Each configuration
            graph: The graph definition (required for "previous"/"start")

        Returns:
            The resolved source node id

        Raises:
            ValueError: If the mode can't be resolved (e.g. no incoming
                connection for "previous", or no START node for "start")
        """
        source_mode = getattr(config, "source_mode", "specific") or "specific"

        if source_mode == "specific":
            if not config.source_node_id:
                raise ValueError(
                    f"For Each node '{node.name}' is set to 'Specific Node' "
                    f"source mode but no source node is selected"
                )
            return config.source_node_id

        if graph is None or not getattr(graph, "nodes", None):
            raise ValueError(
                f"For Each node '{node.name}' uses source_mode='{source_mode}' "
                f"which requires graph context, but none was provided"
            )

        if source_mode == "start":
            start_node = next(
                (n for n in graph.nodes if n.type == NodeType.START), None
            )
            if start_node is None:
                raise ValueError(
                    f"For Each node '{node.name}' uses source_mode='start' "
                    f"but no START node was found in the workflow"
                )
            return start_node.uniq_id

        if source_mode == "previous":
            incoming_ids = [
                (
                    conn.source_id
                    if hasattr(conn, "source_id")
                    else conn.get("source_id")
                )
                for conn in graph.connections
                if (
                    conn.target_id
                    if hasattr(conn, "target_id")
                    else conn.get("target_id")
                )
                == node.uniq_id
                and (
                    conn.connection_type
                    if hasattr(conn, "connection_type")
                    else conn.get("connection_type")
                )
                in (None, "workflow")
            ]
            if not incoming_ids:
                raise ValueError(
                    f"For Each node '{node.name}' uses source_mode='previous' "
                    f"but has no incoming workflow connection"
                )
            # Last incoming connection wins, consistent with
            # PreviousInputSource's handling of multiple incoming edges.
            return incoming_ids[-1]

        raise ValueError(
            f"For Each node '{node.name}' has unknown source_mode='{source_mode}'"
        )

    async def _execute_iterations(
        self,
        node: EnhancedNodeData,
        items: List[Any],
        state: WorkflowState,
        config: ForEachConfig,
        graph: Any = None,
        concurrency_limit: Optional[int] = None,
    ) -> List[IterationResult]:
        """Execute all iterations with bounded concurrency.

        Args:
            node: The For Each node
            items: List of items to iterate over
            state: Current workflow state
            config: For Each configuration
            graph: The graph definition, needed to resolve body node objects
            concurrency_limit: Effective concurrency after system ceilings.
                Falls back to the node's configured value when omitted.

        Returns:
            Sorted list of IterationResult
        """
        if concurrency_limit is None:
            concurrency_limit = config.concurrency_limit
        semaphore = asyncio.Semaphore(concurrency_limit)
        rate_limiter = (
            AsyncRateLimiter(config.rate_limit_per_second)
            if config.rate_limit_per_second
            else None
        )

        completed_count = 0
        failed_count = 0
        results_lock = asyncio.Lock()

        async def process_item(index: int, item: Any) -> IterationResult:
            nonlocal completed_count, failed_count

            async with semaphore:
                if rate_limiter:
                    await rate_limiter.acquire()

                start_time = time.monotonic()

                try:
                    # Build iteration-specific state
                    iteration_state = self._build_iteration_state(
                        parent_state=state,
                        item=item,
                        index=index,
                        total=len(items),
                        for_each_node_id=node.uniq_id,
                        config=config,
                    )

                    # Execute body nodes through the subgraph executor
                    body_result = await self._execute_body(
                        node=node,
                        iteration_state=iteration_state,
                        index=index,
                        graph=graph,
                    )

                    duration = time.monotonic() - start_time

                    # Record iteration to database
                    await self._record_iteration(
                        node=node,
                        state=state,
                        index=index,
                        item=item,
                        result=body_result,
                        status="success",
                        duration=duration,
                        config=config,
                    )

                    async with results_lock:
                        completed_count += 1
                        await self._emit_progress(
                            node, state, completed_count, failed_count, len(items)
                        )

                    return IterationResult(
                        index=index,
                        status="success",
                        input_item=item,
                        output=body_result,
                        duration_seconds=duration,
                    )

                except Exception as e:
                    duration = time.monotonic() - start_time

                    await self._record_iteration(
                        node=node,
                        state=state,
                        index=index,
                        item=item,
                        result=None,
                        status="error",
                        error=str(e),
                        duration=duration,
                        config=config,
                    )

                    async with results_lock:
                        failed_count += 1
                        await self._emit_progress(
                            node, state, completed_count, failed_count, len(items)
                        )

                    if config.error_strategy == "fail_fast":
                        raise

                    return IterationResult(
                        index=index,
                        status="error",
                        input_item=item,
                        error=str(e),
                        duration_seconds=duration,
                    )

        # Launch all iterations
        tasks = [process_item(i, item) for i, item in enumerate(items)]

        if config.error_strategy == "fail_fast":
            results = list(await asyncio.gather(*tasks, return_exceptions=False))
        else:
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)
            results = [
                r
                if isinstance(r, IterationResult)
                else IterationResult(
                    index=-1, status="error", input_item=None, error=str(r)
                )
                for r in raw_results
            ]

        return sorted(results, key=lambda r: r.index)

    async def _execute_body(
        self,
        node: EnhancedNodeData,
        iteration_state: Dict[str, Any],
        index: int,
        graph: Any = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute the body subgraph for a single iteration.

        Uses the subgraph executor to run the body nodes with the
        iteration-specific state.

        Args:
            node: The For Each node
            iteration_state: State for this iteration
            index: Iteration index
            graph: The graph definition, needed to resolve body node objects

        Returns:
            Body execution result, or None
        """
        config = node.for_each_config
        if not config or not config.body_node_ids:
            for_each_logger.warning(
                f"For Each '{node.name}' has no body nodes, skipping iteration {index}"
            )
            # No body configured: surface the current item as the output so
            # downstream aggregation still reflects the source data.
            return iteration_state.get("node_outputs", {}).get("__for_each_current")

        if not self.subgraph_executor:
            for_each_logger.warning(
                f"For Each '{node.name}' iteration {index}: "
                f"no subgraph executor available, returning input item"
            )
            return iteration_state.get("node_outputs", {}).get("__for_each_current")

        return await self.subgraph_executor.execute_for_each_body(
            node, iteration_state, index, graph
        )

    def _build_iteration_state(
        self,
        parent_state: WorkflowState,
        item: Any,
        index: int,
        total: int,
        for_each_node_id: str,
        config: Any = None,
    ) -> Dict[str, Any]:
        """Build isolated state for a single iteration.

        Exposes the current item as a virtual node output at
        `node_outputs["__for_each_current"]`.

        Args:
            parent_state: Parent workflow state
            item: Current iteration item
            index: Current index
            total: Total item count
            for_each_node_id: The For Each node's ID
            config: The For Each config (for allowed_fields / max_item_bytes)

        Returns:
            Iteration state dictionary
        """
        # Apply the optional field allow-list. When configured and the item is
        # a dict, only whitelisted keys are exposed to body nodes; every other
        # column is dropped before it can reach an LLM. This is a deterministic
        # data-residency control (unlike PII guardrails, it also removes custom
        # identifiers and non-PII sensitive columns).
        allowed_fields = getattr(config, "allowed_fields", None) if config else None
        if allowed_fields and isinstance(item, dict):
            exposed_item: Any = {k: item[k] for k in allowed_fields if k in item}
        else:
            exposed_item = item

        # Build the virtual node output for the current item
        item_fields = {
            "item": exposed_item,
            "index": index,
            "total": total,
            "is_first": index == 0,
            "is_last": index == total - 1,
        }
        # If item is a dict, spread its keys for easy access
        if isinstance(exposed_item, dict):
            item_fields.update(exposed_item)

        # ``raw`` is what the default "previous" input source hands to a
        # downstream agent as its user message. Serialise dict items as JSON
        # so body agents actually receive the row content (previously ``raw``
        # was ``None`` for dicts, which caused agents to see an empty prompt
        # and reply with a "your message is empty" apology).
        if isinstance(exposed_item, dict):
            try:
                raw_value = json.dumps(exposed_item, default=str, ensure_ascii=False)
            except (TypeError, ValueError):
                raw_value = str(exposed_item)
        else:
            raw_value = str(exposed_item)

        # Optional per-item size guard: truncate an oversized ``raw`` payload so
        # a single fat row can't blow the model context window or inflate token
        # cost. The structured/fields views are left intact for downstream
        # non-LLM consumers; only the prompt-facing ``raw`` string is capped.
        max_item_bytes = getattr(config, "max_item_bytes", None) if config else None
        if max_item_bytes and max_item_bytes > 0:
            encoded = raw_value.encode("utf-8")
            if len(encoded) > max_item_bytes:
                truncated = encoded[:max_item_bytes].decode("utf-8", errors="ignore")
                raw_value = (
                    f"{truncated}\n...[truncated: item exceeded "
                    f"{max_item_bytes} bytes]"
                )
                for_each_logger.warning(
                    "For Each item %d truncated from %d to %d bytes (max_item_bytes)",
                    index,
                    len(encoded),
                    max_item_bytes,
                )

        current_item_output = {
            "raw": raw_value,
            "structured": exposed_item
            if isinstance(exposed_item, dict)
            else {"value": exposed_item},
            "fields": item_fields,
        }

        # Copy parent node outputs and add the virtual current item
        parent_outputs = dict(parent_state.get("node_outputs", {}))
        parent_outputs["__for_each_current"] = current_item_output

        # Also expose the current item as the For Each node's own output for
        # this iteration. Body nodes are connected downstream from the For
        # Each node in the graph, so their default "previous" input source
        # looks up ``node_outputs[for_each_node_id]``. Without this alias,
        # that lookup misses (the aggregated result isn't written until the
        # loop finishes) and body agents receive an empty message.
        # The parent scope's aggregated For Each output is written after
        # iterations complete, so this per-iteration alias never leaks out.
        parent_outputs[for_each_node_id] = current_item_output

        # Start from a shallow copy of the full parent state so body nodes
        # (AGENT, HTTP, DATABASE, etc.) retain access to context they may
        # need (user_id, workflow_id, graph_name, tool_node_mapping, ...).
        # Only node_outputs/messages/results/execution_order are isolated
        # per-iteration so concurrent iterations don't clobber each other.
        iteration_state: Dict[str, Any] = dict(parent_state)
        iteration_state["node_outputs"] = parent_outputs
        iteration_state["messages"] = []
        iteration_state["results"] = []

        # Give each iteration its own slice of the ordering sequence, starting
        # after the For Each node itself. Iterations run concurrently, so the
        # slice is derived from the iteration index rather than a shared
        # counter. Without this every iteration restarted at 0 and body nodes
        # collided with the main graph's own order, which scattered them
        # through the execution timeline.
        iteration_state["execution_order"] = self._iteration_order_base(
            parent_state, index, config
        )

        # Mark as FOR_EACH body execution so the database tracker creates
        # separate records per iteration instead of deduplicating by node_id.
        iteration_state["__for_each_body_execution"] = True
        iteration_state["__for_each_iteration_index"] = index
        iteration_state["__for_each_total"] = total
        iteration_state["__for_each_node_id"] = for_each_node_id

        return iteration_state

    async def _emit_progress(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        completed: int,
        failed: int,
        total: int,
    ):
        """Emit WebSocket progress event for For Each iterations.

        Args:
            node: The For Each node
            state: Current workflow state
            completed: Number of completed iterations
            failed: Number of failed iterations
            total: Total iterations
        """
        ws_execution_id = state.get("execution_id")
        if not self.ws_notifier or not ws_execution_id:
            return

        try:
            progress_percent = (
                round((completed + failed) / total * 100, 1) if total > 0 else 100
            )
            await self.ws_notifier.on_stream_event(
                ws_execution_id,
                "for_each_progress",
                {
                    "event_type": "for_each_progress",
                    "node_id": node.uniq_id,
                    "node_name": node.name,
                    "completed": completed,
                    "failed": failed,
                    "total": total,
                    "progress_percent": progress_percent,
                },
            )
        except Exception as e:
            for_each_logger.warning(f"Failed to emit progress for {node.name}: {e}")

    async def _record_iteration(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        index: int,
        item: Any,
        result: Optional[Dict],
        status: str,
        duration: float,
        error: Optional[str] = None,
        config: Any = None,
    ):
        """Record individual iteration to the database.

        Args:
            node: The For Each node
            state: Current workflow state
            index: Iteration index
            item: Input item
            result: Iteration result
            status: "success" or "error"
            duration: Duration in seconds
            error: Error message if failed
            config: The For Each configuration, used to compute the iteration's
                execution order so it sorts alongside its body nodes instead of
                colliding with top-level nodes.
        """
        db_execution_id = state.get("db_execution_id")
        if not db_execution_id:
            return

        try:
            input_data = {"item": item, "index": index}
            output_data = result if status == "success" else {"error": error}

            iteration_config = config if config is not None else node.for_each_config
            if iteration_config is not None:
                iteration_order = self._iteration_order_base(
                    state, index, iteration_config
                )
            else:
                iteration_order = index

            node_exec = self.execution_history_service.create_node_execution(
                graph_execution_id=db_execution_id,
                node_id=node.uniq_id,
                node_name=f"{node.name} [Iteration {index + 1}]",
                node_type="FOR_EACH_ITERATION",
                execution_order=iteration_order,
                input_data=input_data,
            )
            if node_exec:
                node_exec_id = node_exec["id"]
                self.execution_history_service.start_node_execution(node_exec_id)
                self.execution_history_service.complete_node_execution(
                    node_execution_id=node_exec_id,
                    status="completed" if status == "success" else "failed",
                    output_data=output_data,
                    error_message=error,
                )
        except Exception as e:
            for_each_logger.warning(
                f"Failed to record iteration {index} for {node.name}: {e}"
            )

    async def _complete_execution(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        node_output: Dict[str, Any],
        execution_start_time: float,
    ):
        """Complete the For Each node execution tracking and notifications.

        Args:
            node: The For Each node
            state: Current workflow state
            node_exec_id: Database execution record ID
            node_output: The aggregated output
            execution_start_time: When execution started
        """
        duration = time.time() - execution_start_time

        await self.database_tracker.complete_node_execution(node_exec_id, node_output)
        await self.notification_handler.notify_complete(
            node, state, node_output, "FOR_EACH", node_exec_id, duration
        )

    def _build_state_update(
        self,
        node: EnhancedNodeData,
        node_output: Dict[str, Any],
        state: WorkflowState,
        iterations_run: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build state update dictionary.

        Args:
            node: The For Each node
            node_output: Output from iteration processing
            state: Current workflow state
            iterations_run: Number of iterations executed. When given, the
                execution order advances past every body node so nodes after
                the loop sort after them rather than interleaving.

        Returns:
            State update dictionary
        """
        if iterations_run:
            from backend.services.execution.state import StateExecutionTracker

            order_update = StateExecutionTracker.set_execution_order(
                state,
                self._order_after_iterations(
                    state, iterations_run, node.for_each_config
                ),
            )
        else:
            order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": node_output,
            **order_update,
        }

    def _build_output(
        self,
        results: List[IterationResult],
        items: List[Any],
        skipped: int = 0,
        source_total: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build the For Each node's aggregated output structure.

        Args:
            results: List of iteration results
            items: Items that were actually processed
            skipped: Items excluded by ``item_limit``
            source_total: Size of the original source array. Defaults to the
                processed count when no items were skipped.

        Returns:
            Standard NodeOutput format (raw/structured/fields)
        """
        succeeded = [r for r in results if r.status == "success"]
        failed = [r for r in results if r.status == "error"]

        result_entries = [
            {
                "index": r.index,
                "status": r.status,
                "input": r.input_item,
                "output": r.output,
                "error": r.error,
                "duration_seconds": r.duration_seconds,
            }
            for r in results
        ]

        total_duration = sum(r.duration_seconds for r in results)
        avg_duration = total_duration / len(results) if results else 0

        if source_total is None:
            source_total = len(items) + skipped

        summary = {
            "total": len(items),
            "succeeded": len(succeeded),
            "failed": len(failed),
            "success_rate": len(succeeded) / len(items) if items else 0,
            "total_duration_seconds": total_duration,
            "avg_duration_seconds": avg_duration,
            # Present so a partial run is never mistaken for a full one
            "source_total": source_total,
            "skipped": skipped,
            "partial": skipped > 0,
        }

        return {
            "raw": (
                (
                    f"Processed {len(items)} of {source_total} items "
                    f"({skipped} skipped by item limit): "
                    f"{len(succeeded)} succeeded, {len(failed)} failed"
                )
                if skipped
                else (
                    f"Processed {len(items)} items: "
                    f"{len(succeeded)} succeeded, {len(failed)} failed"
                )
            ),
            "structured": {"results": result_entries},
            "fields": {
                "results": result_entries,
                "summary": summary,
                "succeeded": [r.output for r in succeeded],
                "failed": [
                    {"index": r.index, "input": r.input_item, "error": r.error}
                    for r in failed
                ],
            },
        }

    def _build_empty_result(self) -> Dict[str, Any]:
        """Build output for empty source array.

        Returns:
            Standard NodeOutput for zero items
        """
        return {
            "raw": "For Each completed with 0 items (empty source array)",
            "structured": {"results": []},
            "fields": {
                "results": [],
                "summary": {
                    "total": 0,
                    "succeeded": 0,
                    "failed": 0,
                    "success_rate": 1.0,
                    "total_duration_seconds": 0,
                    "avg_duration_seconds": 0,
                    "source_total": 0,
                    "skipped": 0,
                    "partial": False,
                },
                "succeeded": [],
                "failed": [],
            },
        }

    async def validate_config(self, node: EnhancedNodeData) -> bool:
        """Validate For Each node configuration.

        Args:
            node: The node to validate

        Returns:
            True if valid
        """
        config = node.for_each_config
        if not config:
            return False
        source_mode = getattr(config, "source_mode", "specific") or "specific"
        if source_mode == "specific" and not config.source_node_id:
            return False
        if not config.field_path:
            return False
        if config.concurrency_limit < 1:
            return False
        if config.max_iterations < 1:
            return False
        return True
