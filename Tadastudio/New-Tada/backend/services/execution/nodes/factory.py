"""
Node Function Factory.

This module provides the factory for creating node execution functions
for LangGraph StateGraphs. It handles node-specific execution logic
and state management.
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.config import get_logger
from backend.services.nodes.registry import NodeExecutorRegistry
from backend.services.workflow.state import NodeOutput, WorkflowState

if TYPE_CHECKING:
    from backend.models import GraphData

factory_logger = get_logger("execution.nodes.factory")

# Node types that should receive workflow-level guardrails egress checks.
# Agent nodes are excluded because they handle their own guardrails internally.
# Control nodes (CHECKPOINT, SUBWORKFLOW, CONDITION) have no content to guard.
_WORKFLOW_GUARDRAILS_NODE_TYPES = frozenset(
    {
        NodeType.HTTP_REQUEST_ACTION,
        NodeType.EMAIL_SEND,
        NodeType.FILE_READ,
        NodeType.DATABASE_INSERT,
        NodeType.DATABASE_QUERY_ACTION,
        NodeType.WEB_SEARCH,
        NodeType.DOCUMENT_SEARCH,
        NodeType.DATABASE_QUERY,
    }
)


class NodeFunctionFactory:
    """
    Factory for creating node execution functions.

    This factory creates async functions that execute workflow nodes
    in a LangGraph StateGraph. Each function:
    - Executes the node based on its type
    - Manages state updates
    - Handles error cases
    - Tracks execution metadata

    The created functions are compatible with LangGraph's StateGraph.
    """

    def __init__(self, checkpoint_executors: Dict[str, Any], adapter: Any = None):
        """
        Initialize node function factory.

        Args:
            checkpoint_executors: Dict mapping checkpoint types to executors
            adapter: Optional adapter for real-time status updates
        """
        self.checkpoint_executors = checkpoint_executors
        self.adapter = adapter

    def create_node_function(
        self, node: EnhancedNodeData, graph: "GraphData"
    ) -> Callable:
        """
        Create a node execution function for StateGraph.

        Args:
            node: The node definition
            graph: The complete graph for context

        Returns:
            An async function that processes workflow state for this node
        """

        async def node_function(state: WorkflowState) -> Dict[str, Any]:
            """Delegate node execution based on type."""
            factory_logger.info(
                f"Node execution starting - Node: {node.name} ({node.uniq_id}), "
                f"Type: {node.type}, Current state node: {state.get('current_node')}"
            )

            # Initialize state updates
            updates = self._initialize_state_updates(node, state)

            # Track node start time
            node_start_time = datetime.now(timezone.utc)

            # Notify adapter about node start
            execution_id = state.get("execution_id")
            self._notify_node_start(execution_id, node, node_start_time)

            try:
                # Resolve guardrails config for non-agent nodes (merges
                # workflow-level + tool/node-specific policy assignments).
                node_guardrails_config = None
                if node.type in _WORKFLOW_GUARDRAILS_NODE_TYPES:
                    node_guardrails_config = await self._resolve_node_guardrails(
                        node, state
                    )

                # Apply ingress guardrails (check_input) before execution.
                # Catches PII, prompt injection, etc. in the data flowing into the node.
                ingress_guardrails_state = None
                if node_guardrails_config:
                    ingress_guardrails_state = await self._apply_node_ingress_guardrails(
                        node, state, graph, node_guardrails_config
                    )

                # Execute node based on type
                result = await self._execute_node(node, state, graph, execution_id)

                # Apply egress guardrails (check_output) on node output.
                # Pass through the ingress-updated guardrails state so per-policy
                # state (PII vault, token budget) is preserved for egress checks.
                if node_guardrails_config:
                    result = await self._apply_node_egress_guardrails(
                        node, state, result, node_guardrails_config,
                        guardrails_state_override=ingress_guardrails_state,
                    )

                # Process node execution result
                updates = self._process_node_result(node, state, result, updates, graph)

                # Track node end time
                node_end_time = datetime.now(timezone.utc)

                # Notify adapter about node completion
                node_output = result.get(
                    "node_output", {"raw": "", "structured": None, "fields": {}}
                )
                self._notify_node_complete(
                    execution_id, node, node_start_time, node_end_time, node_output
                )

                # Log completion
                factory_logger.info(
                    f"Node execution complete - Node: {node.name}, "
                    f"Updates keys: {list(updates.keys())}, "
                    f"New current_node: {updates.get('current_node')}"
                )

                # Log state transition details
                self._log_state_transition(node, updates, graph)

                return updates

            except Exception as e:
                # Handle execution errors
                self._record_block_outcome(node, state, e)
                return await self._handle_node_error(node, e)

        return node_function

    def _record_block_outcome(
        self, node: EnhancedNodeData, state: WorkflowState, error: Exception
    ) -> None:
        """Deposit a guardrail-block outcome onto the node's enriched span.

        When a node fails with a :class:`GuardrailViolationError`, stamp
        ``node.status="blocked"`` plus ``block.reason/category/policy`` so the
        Langfuse span reflects a policy block rather than a generic error.
        Best-effort and non-fatal.
        """
        try:
            from backend.services.guardrails.exceptions import (
                GuardrailViolationError,
            )

            if not isinstance(error, GuardrailViolationError):
                return

            from backend.services.langfuse.node_enrichment import (
                map_block_category,
                record_node_outcome,
            )

            violation = error.violations[0] if error.violations else None
            reason = violation.message if violation else str(error)
            record_node_outcome(
                state.get("execution_id"),
                node.uniq_id,
                **{
                    "node.status": "blocked",
                    "block.reason": (reason[:200] if reason else None),
                    "block.category": (
                        map_block_category(violation.category)
                        if violation
                        else None
                    ),
                    "block.rule": (
                        violation.rule_name if violation else None
                    ),
                    "block.policy": (
                        violation.policy_name if violation else None
                    ),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive
            factory_logger.debug(
                f"Block outcome deposit failed (non-fatal): {exc}"
            )

    def _initialize_state_updates(
        self, node: EnhancedNodeData, state: WorkflowState
    ) -> Dict[str, Any]:
        """Initialize state updates for node execution."""
        return {
            "current_node": node.uniq_id,
            "metadata": {
                **state.get("metadata", {}),
                "current_node_name": node.name,
                "current_node_type": node.type.value,
            },
        }

    def _notify_node_start(
        self,
        execution_id: str,
        node: EnhancedNodeData,
        start_time: datetime,
    ):
        """Notify adapter that node is starting."""
        if self.adapter and execution_id:
            try:
                self.adapter.update_node_status(
                    execution_id=execution_id,
                    node_id=node.uniq_id,
                    node_name=node.name,
                    status="running",
                    start_time=start_time,
                )
            except Exception as e:
                factory_logger.warning(f"Failed to notify node start: {e}")

    def _notify_node_complete(
        self,
        execution_id: str,
        node: EnhancedNodeData,
        start_time: datetime,
        end_time: datetime,
        node_output: NodeOutput,
    ):
        """Notify adapter that node completed."""
        # Skip notification for checkpoint nodes - they handle their own
        if node.type == NodeType.CHECKPOINT:
            return

        if self.adapter and execution_id:
            try:
                self.adapter.update_node_status(
                    execution_id=execution_id,
                    node_id=node.uniq_id,
                    node_name=node.name,
                    status="completed",
                    start_time=start_time,
                    end_time=end_time,
                    output=node_output,
                )
            except Exception as e:
                factory_logger.warning(f"Failed to notify node complete: {e}")

    async def _execute_node(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
        execution_id: str,
    ) -> Dict[str, Any]:
        """
        Execute node based on its type.

        Routes to the appropriate executor based on node type. Node-level
        observability is provided by the OpenInference per-node auto span,
        enriched with TADA metadata by the NodeMetadataSpanProcessor; no
        custom span is created here.

        Returns:
            Dict containing execution result with node_output, messages, etc.
        """
        # Route to appropriate executor based on node type
        if node.type == NodeType.CHECKPOINT:
            result = await self._execute_checkpoint_node(node, state, graph)

        elif node.type == NodeType.SUBWORKFLOW:
            # SUBWORKFLOW nodes executed via agent delegation, not directly
            factory_logger.info(
                f"Skipping SUBWORKFLOW node {node.name} - executed via agent delegation"
            )
            result = {"next": node.nexts[0] if node.nexts else None}

        elif node.type in [
            NodeType.AGENT,
            NodeType.CODE_EXECUTOR,
            NodeType.CONDITION,
            NodeType.DATABASE_INSERT,
            NodeType.DATABASE_QUERY_ACTION,
            NodeType.HTTP_REQUEST_ACTION,
            NodeType.EMAIL_SEND,
            NodeType.FILE_READ,
            NodeType.DOCUMENT_LOAD,
            NodeType.FOR_EACH,
        ]:
            # Use registered executors for these types
            # Extract user_id from state for OAuth token lookup in MCP tools
            user_id = state.get("user_id")
            executor = NodeExecutorRegistry.get_executor(node.type)
            result = await executor.execute(
                node, state, graph, execution_id, user_id=user_id
            )

        else:
            # Default passthrough for unimplemented types
            factory_logger.warning(f"Unimplemented node type: {node.type}")
            result = {}

        return result

    async def _execute_checkpoint_node(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
    ) -> Dict[str, Any]:
        """
        Execute checkpoint node using appropriate executor.

        Args:
            node: The checkpoint node
            state: Current workflow state
            graph: The graph definition

        Returns:
            Checkpoint execution result
        """
        # Build input message for checkpoint
        from backend.services.io.input import InputBuilder

        input_builder = InputBuilder()
        input_message = input_builder.build(node, state, graph)

        # Determine checkpoint type (manual vs email)
        await_mode = "manual"
        if hasattr(node, "checkpoint_config") and node.checkpoint_config:
            await_mode = getattr(node.checkpoint_config, "await_mode", "manual")

        factory_logger.info(
            f"[CHECKPOINT] Node '{node.name}' (ID: {node.uniq_id}), await_mode={await_mode}"
        )

        # Get appropriate executor
        if await_mode == "email":
            email_config = getattr(node.checkpoint_config, "email_config", None)
            if email_config is None:
                factory_logger.warning(
                    f"[CHECKPOINT] Node '{node.name}' has await_mode=email but email_config is None, "
                    "falling through to manual checkpoint"
                )
            elif not email_config.enabled:
                factory_logger.warning(
                    f"[CHECKPOINT] Node '{node.name}' has await_mode=email but email_config.enabled=False, "
                    "falling through to manual checkpoint"
                )
            else:
                executor = self.checkpoint_executors.get("email")
                if executor:
                    factory_logger.info(
                        f"[CHECKPOINT] Routing '{node.name}' to email checkpoint executor"
                    )
                    return await executor.execute(node, state, graph, input_message)
                else:
                    factory_logger.error(
                        f"[CHECKPOINT] No email checkpoint executor registered, "
                        f"falling through to manual for node '{node.name}'"
                    )

        # Default to manual checkpoint
        factory_logger.info(
            f"[CHECKPOINT] Routing '{node.name}' to manual checkpoint executor"
        )
        executor = self.checkpoint_executors.get("manual")
        if executor:
            return await executor.execute(node, state, graph, input_message)

        # Fallback if no executor available
        factory_logger.error(f"No checkpoint executor available for node: {node.name}")
        return {}

    def _process_node_result(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        result: Dict[str, Any],
        updates: Dict[str, Any],
        graph: "GraphData",
    ) -> Dict[str, Any]:
        """
        Process node execution result and merge into state updates.

        Args:
            node: The node that was executed
            state: Current workflow state
            result: Result from node execution
            updates: Current state updates
            graph: The graph definition

        Returns:
            Updated state updates dictionary
        """
        # Handle node_outputs from result (e.g., subagent merging, FILE_READ)
        updates = self._merge_node_outputs(node, result, updates, state)

        # Add to results if present
        updates = self._merge_results(node, result, updates, state)

        # Update messages if provided
        if result.get("messages"):
            updates["messages"] = result["messages"]

        # Merge execution order if provided
        if result.get("execution_order") is not None:
            updates["execution_order"] = result["execution_order"]
            factory_logger.info(
                f"Node {node.name} updated execution_order to: "
                f"{result['execution_order']}"
            )

        # Pass through review_state for review node architecture
        if result.get("review_state") is not None:
            updates["review_state"] = result["review_state"]
            factory_logger.info(
                f"[REVIEW-STATE] Passing review_state from {node.name}: "
                f"keys={list(result['review_state'].keys())}"
            )

        # Propagate guardrails_state (PII vault, token budget tracking) between nodes
        if result.get("guardrails_state") is not None:
            updates["guardrails_state"] = result["guardrails_state"]

        return updates

    def _merge_node_outputs(
        self,
        node: EnhancedNodeData,
        result: Dict[str, Any],
        updates: Dict[str, Any],
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """
        Merge node outputs from result into updates.

        Handles special cases:
        - Subagent outputs from AGENT nodes
        - Direct outputs from FILE_READ nodes
        - Standard node outputs
        """
        # Check if result contains node_outputs (from subagent merging or FILE_READ)
        if "node_outputs" in result:
            updates["node_outputs"] = result["node_outputs"]

            if node.type == NodeType.FILE_READ:
                factory_logger.info(
                    f"[FILE_READ] {node.name} provided direct node_outputs "
                    f"with {len(updates['node_outputs'])} entries"
                )
                # Log content preview
                if node.uniq_id in updates["node_outputs"]:
                    content = updates["node_outputs"][node.uniq_id].get("raw", "")
                    preview = content[:100] + "..." if len(content) > 100 else content
                    factory_logger.info(
                        f"[FILE_READ] {node.name} content preview: {preview}"
                    )
            else:
                factory_logger.info(
                    f"[NODE_OUTPUTS] Transferred {len(updates['node_outputs'])} "
                    "outputs from result to updates"
                )

            # Remove from result to avoid confusion
            del result["node_outputs"]

        # Initialize node_outputs if not present
        if "node_outputs" not in updates:
            updates["node_outputs"] = dict(state.get("node_outputs", {}))
            factory_logger.info(
                f"[NODE_OUTPUTS] Initialized from state with "
                f"{len(updates['node_outputs'])} existing outputs"
            )
        else:
            factory_logger.info(
                f"[NODE_OUTPUTS] Preserving existing updates with "
                f"{len(updates['node_outputs'])} outputs"
            )

        # Log before adding current node
        factory_logger.info(
            f"[NODE_OUTPUTS] Before adding {node.name}: "
            f"{list(updates['node_outputs'].keys())}"
        )

        # Get node output from result
        node_output: NodeOutput = result.get(
            "node_output", {"raw": "", "structured": None, "fields": {}}
        )

        # Don't overwrite FILE_READ/DOCUMENT_LOAD outputs that were already added
        if node.type in (NodeType.FILE_READ, NodeType.DOCUMENT_LOAD) and node.uniq_id in updates.get(
            "node_outputs", {}
        ):
            factory_logger.info(
                f"[NODE_OUTPUTS] Preserving FILE_READ output for {node.name} - "
                "not overwriting with empty node_output"
            )
        else:
            # Check if overwriting (re-execution scenario)
            if node.uniq_id in updates["node_outputs"]:
                factory_logger.info(
                    f"[NODE_OUTPUTS] Overwriting existing output for {node.name} "
                    "(re-execution after checkpoint)"
                )
            else:
                factory_logger.info(
                    f"[NODE_OUTPUTS] Added {node.name} output from "
                    "result['node_output']"
                )

            # Set the current node's output
            updates["node_outputs"][node.uniq_id] = node_output

        # Log after adding current node
        factory_logger.info(
            f"[NODE_OUTPUTS] After adding {node.name}: "
            f"{list(updates['node_outputs'].keys())}"
        )

        # Validate outputs preserved (for debugging agent nodes)
        if node.type == NodeType.AGENT:
            state_outputs = len(state.get("node_outputs", {}))
            current_outputs = len(updates.get("node_outputs", {}))
            if current_outputs > state_outputs + 1:  # More than just current node
                new_count = current_outputs - state_outputs - 1
                factory_logger.info(
                    f"[VALIDATION] {node.name} successfully preserved "
                    f"{new_count} subagent outputs"
                )

        return updates

    def _merge_results(
        self,
        node: EnhancedNodeData,
        result: Dict[str, Any],
        updates: Dict[str, Any],
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Merge results from node execution into updates."""
        if result.get("result") or result.get("node_output"):
            if "results" not in updates:
                updates["results"] = []

            if result.get("result"):
                updates["results"].append(result["result"])
                total_results = len(state.get("results", [])) + len(updates["results"])
                factory_logger.info(
                    f"Node {node.name} added explicit result, "
                    f"total results will be: {total_results}"
                )
            elif result.get("node_output"):
                # If no explicit result but we have node output, create one
                updates["results"].append(
                    {
                        "node": node.name,
                        "output": result["node_output"].get("raw", ""),
                    }
                )
                total_results = len(state.get("results", [])) + len(updates["results"])
                factory_logger.info(
                    f"Node {node.name} added fallback result, "
                    f"total results will be: {total_results}"
                )

        return updates

    async def _handle_node_error(
        self, node: EnhancedNodeData, error: Exception
    ) -> None:
        """
        Handle node execution errors.

        Args:
            node: The node that failed
            error: The exception that occurred

        Raises:
            The original exception after logging
        """
        # Check if this is an Interrupt exception (expected for checkpoints)
        is_interrupt = (
            error.__class__.__name__ == "Interrupt"
            or "interrupt" in str(type(error)).lower()
        )

        if is_interrupt:
            # This is expected behavior for checkpoint nodes
            factory_logger.info(
                f"[CHECKPOINT-DEBUG] Node {node.name} interrupted "
                "(expected for checkpoint)"
            )
        else:
            factory_logger.error(f"Node execution failed: {node.name} - {str(error)}")

        # Re-raise the exception
        raise

    async def _resolve_node_guardrails(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
    ):
        """Resolve the effective guardrails pipeline for a non-agent node.

        Merges workflow-level policies with any tool/node-specific policy
        assignments.  Falls back to the pre-resolved workflow pipeline stored
        in state when the full resolution is unavailable.

        Returns:
            A List[GuardrailsConfig], or None if no guardrails apply.
        """
        try:
            from backend.services.guardrails import get_guardrails_engine

            engine = get_guardrails_engine()
            workflow_id = state.get("workflow_id")

            # Resolve with both workflow and tool-specific layers so that a
            # policy assigned directly to this tool node is included.
            resolved = engine.resolve_unified(
                workflow_id=workflow_id,
                tool_names=[node.uniq_id],
            )
            config = resolved.pipeline_for_tool(node.uniq_id)  # List[GuardrailsConfig]
            if config:
                return config
        except Exception as e:
            factory_logger.debug(
                f"[GUARDRAILS] Per-node resolution failed for {node.name}, "
                f"falling back to workflow pipeline: {e}"
            )

        # Fallback: use the workflow-level pipeline stored in state
        wf_pipeline_dicts = state.get("workflow_guardrails_pipeline")
        if wf_pipeline_dicts:
            try:
                from backend.services.guardrails.serialization import pipeline_entry_to_config

                return [pipeline_entry_to_config(d) for d in wf_pipeline_dicts]
            except Exception:
                pass

        return None

    async def _apply_node_ingress_guardrails(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: "GraphData",
        config,
    ) -> Dict[str, Any] | None:
        """Run check_input() on the text flowing into a non-agent node.

        Catches PII, prompt injection, banned topics, etc. in the data that
        the node will process.  In enforce mode a violation raises
        GuardrailViolationError which aborts the node.

        Returns:
            The updated guardrails_state dict (for threading into egress),
            or None if guardrails did not run.
        """
        try:
            from backend.services.guardrails import get_guardrails_engine
            from backend.services.guardrails.violation_persistence import (
                ViolationPersistenceService,
            )
            from backend.services.io import InputBuilder
            from backend.services.streaming.event_emitter import StreamingEventEmitter

            input_text = InputBuilder().build(node, state, graph)
            if not input_text:
                return

            engine = get_guardrails_engine()
            _gs = dict(state.get("guardrails_state") or {})

            input_result = await engine.check_input(
                input_text,
                config,
                guardrails_state=_gs,
            )

            if input_result.violations:
                execution_id = state.get("execution_id")
                workflow_id = state.get("workflow_id")
                for v in input_result.violations:
                    violation_db_id = ViolationPersistenceService.persist_violation(
                        v,
                        category="node_ingress",
                        action_taken=input_result.action_taken or "blocked",
                        policy_id=v.policy_id or None,
                        policy_name=v.policy_name or None,
                        workflow_id=workflow_id,
                        agent_node_id=node.uniq_id,
                    )
                    StreamingEventEmitter.emit_guardrail_violation(
                        category="node_ingress",
                        rule_name=v.rule_name or "unknown",
                        message=v.message or f"Node ingress violation at {node.name}",
                        severity=v.severity or "block",
                        execution_id=execution_id,
                        violation_db_id=violation_db_id,
                        policy_name=v.policy_name or None,
                        details=v.details,
                        enforcement_mode=v.enforcement_mode or None,
                    )

            if not input_result.passed:
                from backend.services.guardrails.exceptions import (
                    GuardrailViolationError,
                )

                violation_msg = (
                    input_result.violations[0].message
                    if input_result.violations
                    else "Input blocked"
                )
                raise GuardrailViolationError(
                    f"Node input blocked at {node.name}: {violation_msg}",
                    violations=input_result.violations,
                )

            factory_logger.info(
                f"[GUARDRAILS] Ingress check passed for {node.name} "
                f"(violations={len(input_result.violations)})"
            )

            return _gs

        except Exception as e:
            if "GuardrailViolationError" in type(e).__name__:
                raise
            factory_logger.warning(
                f"Node ingress guardrail check failed for {node.name}: {e}"
            )
            return None

    async def _apply_node_egress_guardrails(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        result: Dict[str, Any],
        config,
        guardrails_state_override: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Run check_output() on a non-agent node's output.

        Applies pattern rules, output scanners, and deanonymization on the
        node's raw output.

        Args:
            node: The node that produced output
            state: Current workflow state
            result: Execution result dict (contains node_output)
            config: Resolved GuardrailsConfig for this node
            guardrails_state_override: If provided, use this instead of
                rebuilding from state (preserves ingress-produced per-policy state).

        Returns:
            The result dict, possibly modified if output was blocked or sanitized.
        """
        node_output = result.get("node_output")
        if not node_output:
            return result

        raw_text = node_output.get("raw", "")
        if not raw_text:
            return result

        try:
            from backend.services.guardrails import get_guardrails_engine
            from backend.services.guardrails.violation_persistence import (
                ViolationPersistenceService,
            )
            from backend.services.streaming.event_emitter import StreamingEventEmitter

            engine = get_guardrails_engine()
            _gs = guardrails_state_override if guardrails_state_override is not None else dict(state.get("guardrails_state") or {})

            output_result = await engine.check_output(
                raw_text,
                config,
                guardrails_state=_gs,
            )

            # Persist violations and emit streaming events
            if output_result.violations:
                execution_id = state.get("execution_id")
                workflow_id = state.get("workflow_id")
                for v in output_result.violations:
                    violation_db_id = ViolationPersistenceService.persist_violation(
                        v,
                        category="node_egress",
                        action_taken=output_result.action_taken or "blocked",
                        policy_id=v.policy_id or None,
                        policy_name=v.policy_name or None,
                        workflow_id=workflow_id,
                        agent_node_id=node.uniq_id,
                    )
                    StreamingEventEmitter.emit_guardrail_violation(
                        category="node_egress",
                        rule_name=v.rule_name or "unknown",
                        message=v.message or f"Node egress violation at {node.name}",
                        severity=v.severity or "block",
                        execution_id=execution_id,
                        violation_db_id=violation_db_id,
                        policy_name=v.policy_name or None,
                        details=v.details,
                        enforcement_mode=v.enforcement_mode or None,
                    )

            # Block output in enforce mode — the engine raises for enforce,
            # so this path is only reached in audit mode.
            if not output_result.passed:
                violation_msg = (
                    output_result.violations[0].message
                    if output_result.violations
                    else "Output blocked"
                )
                result["node_output"] = {
                    "raw": f"[Output blocked by guardrail policy: {violation_msg}]",
                    "structured": None,
                    "fields": {},
                }
            elif output_result.sanitized_content is not None:
                factory_logger.info(
                    f"[GUARDRAILS] {node.name} output sanitized by guardrails"
                )
                result["node_output"]["raw"] = output_result.sanitized_content

            # Propagate updated guardrails_state (PII vault, token budget)
            if _gs:
                result["guardrails_state"] = _gs

        except Exception as e:
            if "GuardrailViolationError" in type(e).__name__:
                raise
            factory_logger.warning(
                f"Node egress guardrail check failed for {node.name}: {e}"
            )

        return result

    def _log_state_transition(
        self,
        node: EnhancedNodeData,
        updates: Dict[str, Any],
        graph: "GraphData",
    ):
        """Log state transition details for debugging."""
        factory_logger.info(
            f"[STATE_TRANSITION] Node {node.name} ({node.type.value}) completed"
        )

        if updates.get("node_outputs"):
            node_outputs = updates["node_outputs"]
            factory_logger.info(
                f"[STATE_TRANSITION] Total outputs: {len(node_outputs)}, "
                f"IDs: {list(node_outputs.keys())}"
            )

            # Log brief preview of each output
            for output_id, output in node_outputs.items():
                if isinstance(output, dict) and "raw" in output:
                    preview = (
                        str(output["raw"])[:50] + "..."
                        if len(str(output["raw"])) > 50
                        else str(output["raw"])
                    )
                    # Find node name for this ID
                    node_name = "Unknown"
                    for n in graph.nodes:
                        if n.uniq_id == output_id:
                            node_name = n.name
                            break
                    factory_logger.debug(
                        f"[STATE_TRANSITION]   - {node_name}: {preview}"
                    )
