"""
Agent Node Executor.

This module handles execution of AGENT nodes, coordinating LLM agents with tools,
memory, database tracking, and WebSocket notifications.
"""

import json
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from langgraph.errors import GraphInterrupt

from backend.models.workflow import EnhancedNodeData
from backend.models.workflow.configs import ReviewConfig
from backend.services.config import get_logger
from backend.services.guardrails import get_guardrails_engine
from backend.services.guardrails.checkpoint import GuardrailCheckpoint, GuardrailContext
from backend.services.guardrails.exceptions import GuardrailViolationError
from backend.services.guardrails.models import Violation
from backend.services.execution.context import update_node_execution_map
from backend.services.io import InputBuilder
from backend.services.memory import get_memory_manager
from backend.services.workflow.state import WorkflowState

from ..base import BaseNodeExecutor
from ..handlers import NodeDatabaseTracker, NodeNotificationHandler

if TYPE_CHECKING:
    pass


agent_executor_logger = get_logger("nodes.executors.agent")


class AgentNodeExecutor(BaseNodeExecutor):
    """
    Executor for AGENT nodes.

    Handles agent execution including:
    - Input building with memory context
    - LLM agent execution with tools
    - Token tracking
    - Database recording
    - WebSocket notifications
    - Error handling

    This executor delegates the actual agent execution to the graph_manager's
    execute_simple_chat method, maintaining behavior parity with the original
    implementation.
    """

    def __init__(
        self,
        execution_history_service: Any = None,
        ws_notifier: Any = None,
        subgraph_executor: Optional[Any] = None,
        graph_manager: Optional[Any] = None,
    ):
        """
        Initialize agent node executor.

        Args:
            execution_history_service: Service for tracking execution history
            ws_notifier: WebSocket notifier for real-time updates
            subgraph_executor: Optional executor for handling subgraphs
            graph_manager: Manager for graph operations
        """
        super().__init__(
            execution_history_service, ws_notifier, subgraph_executor, graph_manager
        )

        # Initialize handlers
        self.database_tracker = NodeDatabaseTracker(execution_history_service)
        self.notification_handler = NodeNotificationHandler(ws_notifier)
        self.input_builder = InputBuilder()

    async def execute(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        execution_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an agent node.

        This method orchestrates the complete agent execution flow:
        1. Send early start notification
        2. Build input with memory context
        3. Create database tracking record
        4. Execute agent with graph_manager
        5. Process response and token counts
        6. Update database and send completion notification
        7. Return state updates

        Args:
            node: The agent node to execute
            state: Current workflow state
            graph: The graph definition
            execution_id: Execution identifier
            user_id: Optional user identifier

        Returns:
            State updates with agent output
        """
        # STATUS-MISMATCH-DEBUG: Track agent execution entry
        db_execution_id = state.get("db_execution_id")
        is_sub_agent = getattr(node, "is_sub_agent", False)
        agent_executor_logger.info(
            f"[STATUS-DEBUG] AgentNodeExecutor.execute() called: "
            f"node_name={node.name}, node_id={node.uniq_id}, "
            f"is_sub_agent={is_sub_agent}, db_execution_id={db_execution_id}"
        )

        agent_executor_logger.info(f"Executing AGENT node: {node.name}")

        # Check if this is a resume scenario (existing paused record)
        # If so, we skip the early notification to avoid duplicate UI entries
        is_resume = False
        if db_execution_id:
            existing = self.database_tracker.execution_history_service.get_node_execution_by_node_id(
                graph_execution_id=db_execution_id,
                node_id=node.uniq_id,
            )
            if existing and existing.get("status") == "paused":
                is_resume = True
                agent_executor_logger.info(
                    f"[STATUS-DEBUG] Resume detected for {node.name} "
                    f"(existing record id={existing.get('id')}) - skipping early notification"
                )

        # NEW ARCHITECTURE: Check for feedback in review_state (from Review Node)
        # This is set by the Review Node when output is rejected
        review_feedback_context = self._get_feedback_from_review_state(node, state)
        if review_feedback_context:
            agent_executor_logger.info(
                f"[REVIEW-NODE] Found feedback for {node.name}, will augment input"
            )

        # Track execution timing
        execution_start_time = time.time()
        node_exec_id = (
            None  # Initialize before try so it's available in except handlers
        )
        guardrails_config = (
            None  # Initialize before try so it's available in except handlers
        )

        try:
            # Step 1: Send early start notification (skip on resume to avoid duplicate UI entries)
            if not is_resume:
                await self._send_early_notification(node, state)

            # Step 2: Build input with memory context
            input_message, conversation_history = await self._build_input_with_memory(
                node, state, graph
            )

            # Step 2.5: Augment input with feedback from Review Node (if resuming after rejection)
            if review_feedback_context:
                input_message = f"{input_message}\n{review_feedback_context}"
                agent_executor_logger.info(
                    f"[REVIEW-NODE] Augmented input for {node.name} with feedback context"
                )

            # This must happen before creating tracking record so it can be stored
            review_iteration = self._get_current_review_iteration(node, state)
            agent_executor_logger.debug(
                f"Review iteration for {node.name}: {review_iteration}"
            )

            # Step 3: Create database tracking record
            node_exec_id = await self._create_tracking_record(
                node,
                state,
                graph,
                input_message,
                conversation_history,
                review_iteration=review_iteration,
            )

            # Step 3.5: Update node execution map for sub-agent parent tracking
            if node_exec_id:
                update_node_execution_map(node.uniq_id, str(node_exec_id))

            # Step 3.6: Build tool-to-node mapping for real-time streaming
            # This maps synthetic tool names to workflow node info (node_id, node_name, node_type)
            tool_node_mapping = self._build_tool_node_mapping(node, graph)
            agent_executor_logger.debug(
                f"Built tool_node_mapping with {len(tool_node_mapping)} entries for streaming"
            )

            # Get execution order for streaming iteration discrimination
            current_order = self.database_tracker.get_execution_order(state)

            # Step 4: Execute agent
            (
                result,
                tool_execution_tracker,
                message_structure,
                result_metadata,
            ) = await self._execute_agent_logic(
                node,
                input_message,
                state,
                graph,
                tool_node_mapping,
                execution_order=current_order,
                db_node_id=str(node_exec_id) if node_exec_id else None,
                review_iteration=review_iteration,
                node_exec_id=node_exec_id,
            )

            # Step 4.5: Resolve guardrails config and build context (shared by steps below)
            agent_guardrails_enabled = (
                getattr(node.agent_config, "guardrails_enabled", True)
                if node.agent_config
                else True
            )
            guardrails_engine = get_guardrails_engine()
            model_id = self._get_model_id(node)
            resolved = guardrails_engine.resolve_unified(
                workflow_id=state.get("workflow_id"),
                node_id=node.uniq_id,
                model_id=model_id,
                agent_guardrails_enabled=agent_guardrails_enabled,
            )
            guardrails_config = resolved.agent_pipeline  # List[GuardrailsConfig]

            guardrail_ctx = GuardrailContext(
                execution_id=state.get("execution_id"),
                db_execution_id=state.get("db_execution_id"),
                node_execution_id=str(node_exec_id) if node_exec_id else None,
                workflow_id=state.get("workflow_id"),
                agent_node_id=node.uniq_id,
                agent_node_name=node.name,
                user_id=state.get("user_id"),
            )
            guardrail_checkpoint = GuardrailCheckpoint(guardrails_engine)

            # Step 4.6: Check for provider content filter block (Azure/OpenAI)
            # When the provider blocked the request but no guardrail policy was
            # configured (or it was in audit mode), the async executor returns
            # gracefully with metadata indicating the block.  Persist a violation
            # and emit a streaming event so the UI shows the warning.
            # Skip if the async executor already persisted violations (pcf guardrail active).
            if result_metadata.get(
                "content_filter_blocked"
            ) and not result_metadata.get("content_filter_violations_persisted"):
                cf_categories = result_metadata.get("content_filter_categories", [])
                cf_provider = result_metadata.get("content_filter_provider", "unknown")
                cf_violations = [
                    Violation(
                        category="content_filter",
                        rule_name=cat["category"]
                        if isinstance(cat, dict)
                        else str(cat),
                        severity="warn",
                        message=f"Provider content filter ({cf_provider}): "
                        f"{cat['category'] if isinstance(cat, dict) else str(cat)} detected",
                    )
                    for cat in cf_categories
                ]
                if cf_violations:
                    GuardrailCheckpoint.report_prebuilt_violations(
                        cf_violations,
                        guardrails_config[0] if guardrails_config else None,
                        "content_filter",
                        guardrail_ctx,
                        action_taken="blocked",
                    )

            # Step 5: Process response
            response, token_counts, raw_llm_response = self._process_agent_response(
                result, node.name
            )

            # Step 5.3: Output guardrails check via unified checkpoint
            # Build a merged guardrails_state combining workflow state with
            # any vault/state produced during input guardrails (returned via
            # result_metadata from the async executor).
            _local_guardrails_state = dict(state.get("guardrails_state") or {})
            _input_guardrails_state = result_metadata.get("guardrails_state") or {}
            _local_guardrails_state.update(_input_guardrails_state)

            if guardrails_config:
                # Use the original user message for output guardrails (relevance,
                # factual-consistency) rather than the memory/review-augmented
                # input_message that is sent to the LLM.
                original_prompt = state.get("original_message") or input_message
                output_result = await guardrail_checkpoint.check(
                    response,
                    guardrails_config,
                    "output",
                    guardrail_ctx,
                    state=_local_guardrails_state,
                    prompt=original_prompt,
                )
                # checkpoint.check() raises GuardrailViolationError in enforce mode.
                # In audit mode, handle violations and sanitized content:
                if not output_result.passed:
                    violation_msg = (
                        output_result.violations[0].message
                        if output_result.violations
                        else "Output blocked"
                    )
                    agent_executor_logger.warning(
                        f"[AGENT-EXECUTOR] Output blocked by guardrails for {node.name}: {violation_msg}"
                    )
                    response = f"[Output blocked by guardrail policy: {violation_msg}]"
                elif output_result.sanitized_content is not None:
                    agent_executor_logger.info(
                        f"[AGENT-EXECUTOR] Output redacted by guardrails for {node.name}"
                    )
                    response = output_result.sanitized_content

            # Step 5.5: Store output in review_state if review enabled (NEW ARCHITECTURE)
            # The actual review is handled by a separate Review Node inserted by GraphBuilder
            review_config = self._get_review_config(node)
            review_state_update = None
            if review_config and review_config.review_enabled:
                agent_executor_logger.info(
                    f"[REVIEW-NODE] Review enabled for {node.name}, storing output in review_state"
                )
                review_state_update = self._prepare_review_state_update(
                    node, state, input_message, response, review_config
                )

            execution_duration = time.time() - execution_start_time

            # Step 6: Complete tracking
            await self._complete_tracking(
                node,
                state,
                node_exec_id,
                response,
                token_counts,
                execution_duration,
                input_message,
                graph,
                tool_execution_tracker,
                execution_start_time=execution_start_time,
                message_structure=message_structure,
            )

            # Step 6.5: Track tool executions (create node_execution records for tools)
            agent_executor_logger.info(
                f"[TOOL-TRACKING-DEBUG] Step 6.5 reached. tool_execution_tracker exists: {tool_execution_tracker is not None}, "
                f"length: {len(tool_execution_tracker) if tool_execution_tracker else 0}, "
                f"content: {tool_execution_tracker if tool_execution_tracker else 'None'}"
            )
            if tool_execution_tracker:
                agent_executor_logger.info(
                    f"[TOOL-TRACKING-DEBUG] Calling _track_tool_executions for {node.name}"
                )
                try:
                    from backend.services.langfuse.node_enrichment import (
                        record_node_outcome,
                    )

                    tool_names = [
                        t.get("tool")
                        for t in tool_execution_tracker
                        if isinstance(t, dict) and t.get("tool")
                    ]
                    if tool_names:
                        record_node_outcome(
                            state.get("execution_id"),
                            node.uniq_id,
                            **{
                                "tools.invoked": tool_names,
                                "tools.count": len(tool_names),
                            },
                        )
                except Exception as _exc:  # pragma: no cover - defensive
                    agent_executor_logger.debug(
                        f"tools outcome deposit failed (non-fatal): {_exc}"
                    )
                await self._track_tool_executions(
                    node,
                    state,
                    graph,
                    tool_execution_tracker,
                    node_exec_id,
                    review_iteration=review_iteration,
                )
            else:
                agent_executor_logger.warning(
                    "[TOOL-TRACKING-DEBUG] Skipping tool tracking - tracker is empty or None"
                )

            # Step 7: Store memory if enabled
            await self._store_memory_if_enabled(
                node, state, input_message, response, raw_llm_response
            )

            # Step 8: Return state updates
            state_update = self._build_state_update(
                node, state, response, token_counts, tool_execution_tracker
            )

            # Store current review iteration in state for downstream tool nodes
            # This allows HTTP_REQUEST, DATABASE_QUERY, etc. nodes to track which
            # agent iteration triggered their execution
            state_update["current_review_iteration"] = review_iteration

            # Include review_state update if review is enabled
            if review_state_update:
                state_update["review_state"] = review_state_update
                agent_executor_logger.info(
                    f"[REVIEW-STATE-DEBUG] {node.name} returning review_state with keys: "
                    f"{list(review_state_update.keys())}"
                )

            # Step 8.5: Always persist guardrails_state (vault + token budget)
            # so downstream output processing and cross-node phases can
            # access the vault for deanonymization.
            if _local_guardrails_state:
                state_update["guardrails_state"] = _local_guardrails_state

            # Update token budget tracking within the guardrails state
            if (
                guardrails_config
                and any(cfg.token_budget for cfg in guardrails_config)
            ):
                existing_budget = _local_guardrails_state.get("token_budget_used", {})
                new_input = token_counts.get("input_tokens", 0) if token_counts else 0
                new_output = token_counts.get("output_tokens", 0) if token_counts else 0
                updated_budget = {
                    "input_tokens": existing_budget.get("input_tokens", 0) + new_input,
                    "output_tokens": existing_budget.get("output_tokens", 0)
                    + new_output,
                    "total_tokens": existing_budget.get("total_tokens", 0)
                    + new_input
                    + new_output,
                    "llm_calls": existing_budget.get("llm_calls", 0) + 1,
                }
                _local_guardrails_state["token_budget_used"] = updated_budget
                state_update["guardrails_state"] = _local_guardrails_state

                # Check if budget is exceeded
                guardrails_engine = get_guardrails_engine()
                budget_result = guardrails_engine.check_token_budget(
                    updated_budget, guardrails_config
                )
                if not budget_result.passed:
                    agent_executor_logger.warning(
                        f"[AGENT-EXECUTOR] Token budget exceeded for {node.name}: "
                        f"{[v.message for v in budget_result.violations]}"
                    )

            return state_update

        except GraphInterrupt:
            # Re-raise GraphInterrupt to allow LangGraph to handle pause/resume
            # This is used by review checkpoints and other interrupt mechanisms
            raise
        except GuardrailViolationError as e:
            # Mark the node execution as failed in the database so the UI
            # transitions from "In Progress"/"Running" to "Failed"
            await self.database_tracker.fail_node_execution(
                node_exec_id,
                str(e),
                error_output={
                    "error": str(e),
                    "success": False,
                    "violation_type": "guardrail",
                    "violations": [v.to_dict() for v in e.violations]
                    if e.violations
                    else [],
                },
            )

            # Send node error notification via WebSocket
            await self.notification_handler.notify_error(
                node, state, str(e), "AGENT", node_exec_id=node_exec_id
            )

            # For block-severity violations in enforce mode, interrupt the graph
            # so the frontend can show a non-dismissable modal instead of silently failing
            if (
                e.violations
                and e.violations[0].severity == "block"
                and guardrails_config
                and any(cfg.enforcement_mode == "enforce" for cfg in guardrails_config)
            ):
                from langgraph.types import interrupt

                policy_name = e.violations[0].policy_name if e.violations else None
                rule_name = e.violations[0].rule_name
                interrupt(
                    {
                        "type": "guardrail_block",
                        "violations": [v.to_dict() for v in e.violations],
                        "resumable": False,
                        "policy_name": policy_name,
                        "rule_name": rule_name,
                    }
                )
            else:
                # Re-raise to propagate guardrail enforcement — fails the workflow
                raise
        except Exception as e:
            agent_executor_logger.error(
                f"Agent execution error for {node.name}: {e}", exc_info=True
            )
            # Mark the node execution as failed in the database so the UI
            # transitions from "Running" to "Failed"
            await self.database_tracker.fail_node_execution(
                node_exec_id,
                str(e),
            )
            return await self._handle_error(
                node, state, str(e), execution_start_time, node_exec_id=node_exec_id
            )

    async def _send_early_notification(
        self, node: EnhancedNodeData, state: WorkflowState
    ) -> None:
        """
        Send early WebSocket notification to prevent UI delay.

        Args:
            node: The agent node
            state: Current workflow state
        """
        ws_start_time = time.time()
        current_order = self.database_tracker.get_execution_order(state)

        is_sub_agent = getattr(node, "is_sub_agent", False)
        parent_agent_id = getattr(node, "parent_agent_id", None)

        await self.notification_handler.notify_start(
            node,
            state,
            "AGENT",
            node_exec_id=None,  # Not yet available
            execution_order=current_order,
            is_sub_agent=is_sub_agent,
            parent_agent_id=parent_agent_id,
        )

        ws_elapsed = time.time() - ws_start_time
        agent_executor_logger.info(
            f"Sent early WebSocket notification for {node.name} in {ws_elapsed:.3f}s"
        )

    async def _build_input_with_memory(
        self, node: EnhancedNodeData, state: WorkflowState, graph: Any
    ) -> tuple[str, Optional[list]]:
        """
        Build input message with memory context if enabled.

        Args:
            node: The agent node
            state: Current workflow state
            graph: The graph definition

        Returns:
            Tuple of (input message with memory context, structured conversation history if used)
        """
        # Build base input
        input_message = self.input_builder.build(node, state, graph)
        conversation_history: Optional[list] = None

        # Check for memory configuration
        memory_enabled = False
        if node.agent_config:
            memory_enabled = getattr(node.agent_config, "memory_enabled", False)

        if not memory_enabled:
            return input_message, conversation_history

        # Load memory context
        try:
            memory_manager = get_memory_manager()
            memory_window = getattr(node.agent_config, "memory_window_size", 10)
            conversation_history = await memory_manager.get_agent_memories(
                agent_id=node.uniq_id,
                graph_execution_id=state.get("db_execution_id"),
                limit=memory_window,
            )
            memory_context = await memory_manager.format_memory_context(
                conversation_history
            )

            if memory_context:
                input_message = self.input_builder.build_with_memory(
                    node, state, graph, memory_context
                )

        except Exception as e:
            agent_executor_logger.error(f"Failed to load memory for {node.name}: {e}")

        return input_message, conversation_history

    async def _create_tracking_record(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        input_message: str,
        conversation_history: Optional[list] = None,
        review_iteration: Optional[int] = None,
    ) -> Optional[int]:
        """
        Create database tracking record for agent execution.

        Args:
            node: The agent node
            state: Current workflow state
            graph: The graph definition
            input_message: Input message for the agent
            conversation_history: Optional structured conversation history used as context
            review_iteration: Review iteration number (for multi-iteration review flows)

        Returns:
            Node execution ID, or None if tracking disabled
        """
        is_sub_agent = getattr(node, "is_sub_agent", False)
        parent_agent_id = getattr(node, "parent_agent_id", None)

        input_payload = {}
        if conversation_history:
            input_payload["conversation_history"] = conversation_history
        input_payload["message"] = input_message

        node_exec_id = await self.database_tracker.create_node_execution(
            node,
            state,
            "AGENT",
            input_payload,
            is_sub_agent=is_sub_agent,
            parent_agent_id=parent_agent_id,
            review_iteration=review_iteration,
        )

        # Send updated notification with database ID
        if node_exec_id:
            current_order = self.database_tracker.get_execution_order(state)
            await self.notification_handler.notify_start(
                node,
                state,
                "AGENT",
                node_exec_id=node_exec_id,
                execution_order=current_order,
                is_sub_agent=is_sub_agent,
                parent_agent_id=parent_agent_id,
            )

        return node_exec_id

    async def _execute_agent_logic(
        self,
        node: EnhancedNodeData,
        input_message: str,
        state: WorkflowState,
        graph: Any,
        tool_node_mapping: Optional[Dict[str, Any]] = None,
        review_iteration: Optional[int] = None,
        node_exec_id: Optional[str] = None,
        execution_order: Optional[int] = None,
        db_node_id: Optional[str] = None,
    ) -> tuple:
        """
        Execute the agent using graph_manager's async method.

        Args:
            node: The agent node
            input_message: Input message for the agent
            state: Current workflow state
            graph: The graph definition
            tool_node_mapping: Mapping from synthetic tool names to workflow node info
                               for real-time streaming updates
            execution_order: Execution order for streaming iteration discrimination
            db_node_id: Database node execution ID for precise streaming attribution

        Returns:
            Tuple of (result, tool_execution_tracker)
        """
        tool_execution_tracker = []

        # Extract graph name for tool discovery
        graph_name = graph.name if hasattr(graph, "name") else None

        # Log state for debugging
        agent_executor_logger.info(
            f"[TOOL-TRACKING-DEBUG] _execute_agent_logic - "
            f"db_execution_id from state: {state.get('db_execution_id')}, "
            f"execution_id from state: {state.get('execution_id')}, "
            f"graph_name: {graph_name}"
        )

        # Extract chat conversation history for chat-triggered executions.
        # Only inject for agents receiving direct user input (from START node),
        # not downstream agents processing intermediate results.
        conversation_history = None
        chat_memory_ctx = state.get("memory_context")
        if chat_memory_ctx and chat_memory_ctx.get("messages"):
            if self._receives_input_from_start(node, graph):
                from langchain_core.messages import AIMessage, HumanMessage as HMsg
                conversation_history = []
                for msg in chat_memory_ctx["messages"]:
                    if msg.get("role") == "user":
                        conversation_history.append(HMsg(content=msg["content"]))
                    elif msg.get("role") == "assistant":
                        conversation_history.append(AIMessage(content=msg["content"]))
                if conversation_history:
                    agent_executor_logger.info(
                        f"Injecting {len(conversation_history)} chat history messages "
                        f"for {node.name}"
                    )

        # Use async execution since we're in an async context.
        # NOTE: tool_execution_tracker is a mutable list mutated by reference during
        # Phase 1 of two-phase (tools + structured output) execution. If Phase 2 (the
        # structured-output formatter) raises, the exception propagates before the
        # normal Step 6.5 tool-tracking runs, and the UI would lose visibility of the
        # tool calls that actually executed. We persist any collected tool records
        # here before re-raising so the tool node's execution details still render.
        try:
            result = await self.graph_manager.execute_agent_async(
                node,
                input_message,
                tool_execution_tracker=tool_execution_tracker,
                db_execution_id=state.get("db_execution_id"),
                return_token_counts=True,
                graph_name=graph_name,
                execution_id=state.get("execution_id"),
                user_id=state.get("user_id"),
                tool_node_mapping=tool_node_mapping,
                review_iteration=review_iteration,
                node_execution_id=str(node_exec_id) if node_exec_id else None,
                execution_order=execution_order,
                db_node_id=db_node_id,
                conversation_history=conversation_history,
                workflow_id=state.get("workflow_id"),
            )
        except Exception:
            if tool_execution_tracker:
                agent_executor_logger.warning(
                    f"[TOOL-TRACKING-DEBUG] Agent {node.name} failed after "
                    f"{len(tool_execution_tracker)} tool execution(s); persisting "
                    f"partial tool records before propagating error"
                )
                try:
                    await self._track_tool_executions(
                        node,
                        state,
                        graph,
                        tool_execution_tracker,
                        str(node_exec_id) if node_exec_id else None,
                        review_iteration=review_iteration,
                    )
                except Exception as track_err:
                    agent_executor_logger.warning(
                        f"[TOOL-TRACKING-DEBUG] Failed to persist partial tool "
                        f"executions for {node.name}: {track_err}"
                    )
            raise

        # Extract tool_executions, message_structure, and metadata from result tuple
        # Format: (response, token_counts, tool_executions, message_structure, metadata)
        message_structure = None
        result_metadata = {}
        if isinstance(result, tuple) and len(result) >= 3:
            tool_execution_tracker = result[2]  # Third element is tool_executions
        if isinstance(result, tuple) and len(result) >= 4:
            message_structure = result[3]  # Fourth element is message_structure
        if isinstance(result, tuple) and len(result) >= 5:
            result_metadata = result[4] or {}  # Fifth element is metadata
        agent_executor_logger.info(
            f"[TOOL-TRACKING-DEBUG] After execute_agent_async - "
            f"tool_execution_tracker length: {len(tool_execution_tracker)}"
        )

        return result, tool_execution_tracker, message_structure, result_metadata

    @staticmethod
    def _receives_input_from_start(node: EnhancedNodeData, graph: Any) -> bool:
        """Check if this agent receives input directly from the START node."""
        from backend.models.workflow import NodeType

        if not hasattr(graph, "connections"):
            return False
        for conn in graph.connections:
            if conn.target_id == node.uniq_id:
                for n in graph.nodes:
                    if n.uniq_id == conn.source_id and n.type == NodeType.START:
                        return True
        return False

    def _process_agent_response(self, result: Any, agent_name: str) -> tuple:
        """
        Process agent execution result from async executor.

        Args:
            result: Result from async agent execution (tuple of response, token_counts, tool_executions)
            agent_name: Name of the agent

        Returns:
            Tuple of (response_content, token_counts, raw_llm_response)
        """
        response = None
        token_counts = None
        raw_llm_response = None

        # Handle tuple from execute_agent_async with return_token_counts=True
        # Format: (response, token_counts, tool_executions, message_structure, metadata)
        if isinstance(result, tuple) and len(result) >= 3:
            response = result[0]
            token_counts = result[1]
            # tool_executions (result[2]) and message_structure (result[3]) handled separately
        elif isinstance(result, tuple) and len(result) == 2:
            response, token_counts = result
        else:
            response = result

        # Extract response content
        if response:
            if hasattr(response, "content"):
                response_content = response.content
            else:
                response_content = str(response)
        else:
            response_content = "No response from agent"

        agent_executor_logger.info(
            f"Agent {agent_name} completed with response length: {len(response_content)}"
        )

        # raw_llm_response is None since async executor doesn't expose it
        # Memory is already handled by async executor internally
        return response_content, token_counts, raw_llm_response

    async def _complete_tracking(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        node_exec_id: Optional[int],
        response: str,
        token_counts: Optional[Dict[str, int]],
        duration_seconds: float,
        input_message: str,
        graph: Any,
        tool_execution_tracker: Optional[List[Dict[str, Any]]] = None,
        execution_start_time: Optional[float] = None,
        message_structure: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Complete database tracking and send notifications.

        Args:
            node: The agent node
            state: Current workflow state
            node_exec_id: Database node execution ID
            response: Response from agent
            token_counts: Token usage counts
            duration_seconds: Execution duration
            input_message: Input message used
            graph: The graph definition
            tool_execution_tracker: Tool execution data including file_id for file writes
            execution_start_time: Unix timestamp when execution started
            message_structure: Full conversation message structure from async executor
        """
        # Complete database record
        output_data = {"response": response}
        if tool_execution_tracker:
            output_data["tool_executions"] = tool_execution_tracker

        # Build LLM metadata with cost calculation and performance metrics
        execution_end_time = (
            (execution_start_time + duration_seconds) if execution_start_time else None
        )
        llm_metadata = self._build_llm_cost_metadata(
            node,
            token_counts,
            start_time=execution_start_time,
            end_time=execution_end_time,
        )

        # Use full conversation message_structure from async executor, or build a
        # minimal fallback from the available data if it wasn't provided
        if not message_structure:
            message_structure = _build_message_structure(
                input_message, response, token_counts, tool_execution_tracker
            )

        await self.database_tracker.complete_node_execution(
            node_exec_id,
            output_data,
            token_counts,
            llm_metadata=llm_metadata,
            message_structure=message_structure,
        )

        # Send completion notification
        is_sub_agent = getattr(node, "is_sub_agent", False)
        parent_agent_id = getattr(node, "parent_agent_id", None)
        current_order = self.database_tracker.get_execution_order(state)

        await self.notification_handler.notify_complete(
            node,
            state,
            output_data,
            "AGENT",
            node_exec_id=node_exec_id,
            duration_seconds=duration_seconds,
            input_data={"message": input_message},
            token_counts=token_counts,
            execution_order=current_order,
            is_sub_agent=is_sub_agent,
            parent_agent_id=parent_agent_id,
        )

    def _build_llm_cost_metadata(
        self,
        node: EnhancedNodeData,
        token_counts: Optional[Dict[str, int]],
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build LLM metadata with cost calculation using deployment pricing.

        Delegates to the shared build_llm_metadata utility.

        Args:
            node: The agent node (has config.llm_config with model info)
            token_counts: Token usage counts from execution
            start_time: Execution start time as unix timestamp
            end_time: Execution end time as unix timestamp

        Returns:
            LLM metadata dict with cost fields, or None if no tokens
        """
        from backend.services.trace.cost_calculator import build_llm_metadata

        return build_llm_metadata(
            node, token_counts, start_time=start_time, end_time=end_time
        )

    async def _track_tool_executions(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        graph: Any,
        tool_execution_tracker: List[Dict[str, Any]],
        parent_node_execution_id: Optional[str],
        review_iteration: Optional[int] = None,
    ) -> None:
        """
        Create node_execution records for tools used by this agent.

        This restores functionality from the old implementation where tool
        executions were tracked as separate node_execution records in the database.

        Args:
            node: The agent node that executed tools
            state: Current workflow state
            graph: The graph definition
            tool_execution_tracker: List of tool execution data
            parent_node_execution_id: Database ID of the agent node execution
        """
        from backend.services.subgraph.agent.tool_tracker import track_tool_executions

        agent_executor_logger.info(
            f"[TOOL-TRACKING-DEBUG] _track_tool_executions called for agent {node.name}"
        )
        agent_executor_logger.info(
            f"[TOOL-TRACKING-DEBUG] Tracking {len(tool_execution_tracker)} tool executions"
        )

        try:
            # Get the actual tool instances to extract MCP metadata
            # This allows us to map individual MCP tool names back to their parent server
            tools = None
            graph_name = graph.name if hasattr(graph, "name") else None
            user_id = state.get("user_id")

            if self.graph_manager and graph_name:
                try:
                    tools = self.graph_manager.get_tools(
                        agent_config=node.agent_config,
                        graph_name=graph_name,
                        agent_node_id=node.uniq_id,
                        user_id=user_id,
                    )
                    agent_executor_logger.debug(
                        f"[TOOL-TRACKING-DEBUG] Retrieved {len(tools) if tools else 0} tools for MCP mapping"
                    )
                except Exception as e:
                    agent_executor_logger.warning(
                        f"[TOOL-TRACKING-DEBUG] Could not retrieve tools for MCP mapping: {e}"
                    )

            # Build tool node mapping (including MCP tool metadata from tool instances)
            tool_node_mapping = self._build_tool_node_mapping(node, graph, tools=tools)
            agent_executor_logger.info(
                f"[TOOL-TRACKING-DEBUG] Built tool_node_mapping with {len(tool_node_mapping)} entries: {list(tool_node_mapping.keys())}"
            )

            # Get execution metadata
            parent_db_execution_id = state.get("db_execution_id")
            parent_execution_id = state.get("execution_id")
            current_order = self.database_tracker.get_execution_order(state)

            agent_executor_logger.info(
                f"[TOOL-TRACKING-DEBUG] Execution metadata - "
                f"parent_db_execution_id: {parent_db_execution_id}, "
                f"parent_execution_id: {parent_execution_id}, "
                f"current_order: {current_order}"
            )

            # Use existing tool tracking infrastructure
            await track_tool_executions(
                tool_execution_tracker=tool_execution_tracker,
                agent_node=node,
                parent_db_execution_id=parent_db_execution_id,
                parent_node_execution_id=parent_node_execution_id,
                parent_execution_id=parent_execution_id,
                execution_order=current_order,
                tool_node_mapping=tool_node_mapping,
                graph_name=graph.name if hasattr(graph, "name") else None,
                graph_manager=self.graph_manager,
                review_iteration=review_iteration,
            )

            agent_executor_logger.info(
                f"Successfully tracked {len(tool_execution_tracker)} tool executions"
            )

        except Exception as e:
            agent_executor_logger.error(
                f"Failed to track tool executions for {node.name}: {e}", exc_info=True
            )

    def _build_tool_node_mapping(
        self, agent_node: EnhancedNodeData, graph: Any, tools: List[Any] = None
    ) -> Dict[str, Any]:
        """
        Build mapping of tool names to node information.

        Creates mappings for:
        1. Synthetic tool names (e.g., "document_search_a6110317")
        2. Base names for compatibility (e.g., "document_search", "search_documents")
        3. MCP tool names mapped to their parent MCP server node

        Args:
            agent_node: The agent node
            graph: The graph definition
            tools: Optional list of tool instances (for extracting MCP metadata)

        Returns:
            Dictionary mapping tool names to node info (node_id, node_name, node_type)
        """
        from backend.models.workflow import NodeType

        tool_mapping = {}

        try:
            # Find tool nodes connected to this agent
            if not hasattr(graph, "connections") or not hasattr(graph, "nodes"):
                agent_executor_logger.warning(
                    "Graph missing connections or nodes, cannot build tool mapping"
                )
                return tool_mapping

            # Find all tool connections from this agent
            for conn in graph.connections:
                if (
                    conn.source_id == agent_node.uniq_id
                    and conn.connection_type == "tool"
                ):
                    # Find the target tool node
                    tool_node = next(
                        (n for n in graph.nodes if n.uniq_id == conn.target_id), None
                    )

                    if tool_node:
                        # Get synthetic tool name
                        synthetic_tool_name = self._get_tool_name_for_node(tool_node)
                        if not synthetic_tool_name:
                            continue

                        # Create node info dict
                        node_info = {
                            "node_id": tool_node.uniq_id,
                            "node_name": tool_node.name,
                            "node_type": tool_node.type,
                        }

                        # Map synthetic name (e.g., "document_search_a6110317")
                        tool_mapping[synthetic_tool_name] = node_info

                        # Also add base name mappings for lookup compatibility
                        # This matches the pattern from agent_delegation_tools.py
                        if tool_node.type == NodeType.DOCUMENT_SEARCH:
                            tool_mapping["document_search"] = node_info
                            tool_mapping["search_documents"] = node_info
                        elif tool_node.type == NodeType.WEB_SEARCH:
                            tool_mapping["web_search"] = node_info
                            tool_mapping["search_web"] = node_info
                        elif tool_node.type == NodeType.DATABASE_QUERY:
                            tool_mapping["database_query"] = node_info
                            tool_mapping["query_db"] = node_info
                            tool_mapping["query_database"] = node_info
                        elif tool_node.type == NodeType.HTTP_REQUEST:
                            tool_mapping["http_request"] = node_info
                        elif tool_node.type == NodeType.MCP_SERVER:
                            # MCP already uses generic name, no additional mapping needed
                            pass
                        elif tool_node.type == NodeType.EMAIL_SEND_TOOL:
                            tool_mapping["email_send"] = node_info
                            tool_mapping["send_email"] = node_info
                        elif tool_node.type == NodeType.FILE_WRITE:
                            tool_mapping["file_write"] = node_info
                            tool_mapping["write_file"] = node_info
                        elif tool_node.type == NodeType.CODE_EXECUTOR:
                            tool_mapping["execute_code"] = node_info
                            tool_mapping["run_code"] = node_info
                            tool_mapping["code_executor"] = node_info

                        agent_executor_logger.debug(
                            f"Mapped tool '{synthetic_tool_name}' to node {tool_node.name} ({tool_node.uniq_id})"
                        )

            # Extract MCP tool mappings from actual tool instances
            # This maps individual MCP tool names (e.g., "notion-search") to their parent server
            if tools:
                mcp_tools_mapped = 0
                for tool in tools:
                    tool_name = getattr(tool, "name", None)
                    mcp_node_id = getattr(tool, "_mcp_server_node_id", None)

                    if tool_name and mcp_node_id:
                        # This tool came from an MCP server - create direct mapping
                        tool_mapping[tool_name] = {
                            "node_id": mcp_node_id,
                            "node_name": getattr(
                                tool, "_mcp_server_node_name", tool_name
                            ),
                            "node_type": getattr(
                                tool, "_mcp_server_node_type", NodeType.MCP_SERVER
                            ),
                            "is_mcp_tool": True,
                        }
                        mcp_tools_mapped += 1
                        agent_executor_logger.debug(
                            f"Mapped MCP tool '{tool_name}' to server node {mcp_node_id}"
                        )

                if mcp_tools_mapped > 0:
                    agent_executor_logger.info(
                        f"Mapped {mcp_tools_mapped} MCP tools to their parent server nodes"
                    )

            agent_executor_logger.info(
                f"Built tool mapping with {len(tool_mapping)} entries for agent {agent_node.name}"
            )

        except Exception as e:
            agent_executor_logger.error(f"Failed to build tool node mapping: {e}")

        return tool_mapping

    def _get_tool_name_for_node(self, tool_node: EnhancedNodeData) -> Optional[str]:
        """
        Get the synthetic tool name that would be used in tool_execution_tracker.

        Uses the same build_tool_name function that creates the actual tool names,
        ensuring the mapping keys match the actual tool names being used.

        Args:
            tool_node: The tool node

        Returns:
            Synthetic tool name, or None if node type not recognized
        """
        from backend.models.workflow import NodeType
        from backend.services.graph.agent_tools.utils import build_tool_name

        # Map node types to their tool type prefixes
        type_to_prefix = {
            NodeType.DOCUMENT_SEARCH: "document_search",
            NodeType.WEB_SEARCH: "web_search",
            NodeType.DATABASE_QUERY: "database_query",
            NodeType.HTTP_REQUEST: "http_request",
            NodeType.MCP_SERVER: "mcp_server",
            NodeType.EMAIL_SEND_TOOL: "email_send",
            NodeType.FILE_WRITE: "file_write",
            NodeType.DOCUMENT_RETRIEVE: "retrieve_document",
            NodeType.CODE_EXECUTOR: "execute_code",
        }

        prefix = type_to_prefix.get(tool_node.type)
        if not prefix:
            return None

        # Use the same function that creates actual tool names
        # This ensures mapping keys match the tool names LLM will call
        return build_tool_name(
            tool_type_prefix=prefix,
            node_name=tool_node.name,
            node_id=tool_node.uniq_id,
        )

    async def _store_memory_if_enabled(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        input_message: str,
        response: str,
        raw_llm_response: Optional[Any],
    ) -> None:
        """
        Store memory if memory is enabled for this agent.

        Note: When using async executor (execute_agent_async), memory is handled
        internally by the async executor, so this method becomes a no-op.

        Args:
            node: The agent node
            state: Current workflow state
            input_message: Input message
            response: Agent response
            raw_llm_response: Raw LLM response object (None for async execution)
        """
        # Skip memory storage - async executor handles it internally
        # This prevents duplicate memory storage
        agent_executor_logger.debug(
            f"Memory storage skipped for {node.name} - handled by async executor"
        )
        return

    def _build_state_update(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        response: str,
        token_counts: Optional[Dict[str, int]],
        tool_execution_tracker: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build state update dictionary.

        Args:
            node: The agent node
            state: Current workflow state
            response: Agent response
            token_counts: Token usage counts
            tool_execution_tracker: Tool execution tracking data

        Returns:
            State update dictionary
        """
        # Default structure - always include response key

        structured_data = {"response": response}
        fields_data = {"response": response}

        # Try to parse response as JSON and spread fields for downstream extraction.
        # This enables FOR_EACH and other nodes to access structured fields via
        # dot-path (e.g., "fields.rows") without requiring structured_outputs config.
        try:
            parsed = json.loads(response)
            if isinstance(parsed, dict):
                structured_data = {**parsed, "response": response}
                fields_data = {**parsed, "response": response}
        except (json.JSONDecodeError, TypeError):
            pass

        node_output = {
            "raw": response,
            "structured": structured_data,
            "fields": fields_data,
        }

        if token_counts:
            node_output["token_counts"] = token_counts

        if tool_execution_tracker:
            node_output["tool_executions"] = tool_execution_tracker

        # Increment execution order
        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": node_output,
            **order_update,
        }

    def _get_review_config(self, node: EnhancedNodeData) -> Optional[ReviewConfig]:
        """
        Extract review configuration from agent config.

        Args:
            node: The agent node

        Returns:
            ReviewConfig if present and valid, None otherwise
        """
        if not node.agent_config:
            return None

        review_config = getattr(node.agent_config, "review_config", None)
        if not review_config:
            return None

        # Handle dict conversion
        if isinstance(review_config, dict):
            return ReviewConfig.from_dict(review_config)

        return review_config

    @staticmethod
    def _get_model_id(node: EnhancedNodeData) -> Optional[str]:
        """Extract model deployment ID from the agent node's LLM config.

        Returns the model_deployment_id if available, falling back to
        model_name. This is used to resolve model-level guardrail policies.
        """
        agent_config = node.agent_config
        if not agent_config or not agent_config.llm_config:
            return None
        llm_config = agent_config.llm_config
        return llm_config.model_deployment_id or llm_config.model_name or None

    def _get_feedback_from_review_state(
        self, node: EnhancedNodeData, state: WorkflowState
    ) -> Optional[str]:
        """
        Get feedback context from review_state for this agent.

        This is used when resuming after rejection - the Review Node stores
        feedback in review_state[node_id].history, and we extract it here
        to augment the agent's input.

        Args:
            node: The agent node
            state: Current workflow state

        Returns:
            Feedback context string if present, None otherwise
        """
        review_state = state.get("review_state", {})
        agent_review_data = review_state.get(node.uniq_id)

        if not agent_review_data:
            return None

        # Check for feedback in history
        history = agent_review_data.get("history", [])
        if not history:
            return None

        # Build feedback context from history
        from backend.services.execution.review.executor import ReviewExecutor

        return ReviewExecutor.build_feedback_context(history)

    def _get_current_review_iteration(
        self, node: EnhancedNodeData, state: WorkflowState
    ) -> int:
        """
        Get current review iteration (1-indexed) from existing review_state.

        This is calculated before execution to allow tool calls to include
        iteration context for proper grouping in the UI.

        Args:
            node: The agent node
            state: Current workflow state

        Returns:
            Current iteration number (1 for first run, 2+ for subsequent runs after review)
        """
        existing_review_state = state.get("review_state", {})
        existing_data = existing_review_state.get(node.uniq_id, {})
        history = existing_data.get("history", [])
        return len(history) + 1

    def _prepare_review_state_update(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        input_message: str,
        response: str,
        review_config: ReviewConfig,
    ) -> Dict[str, Any]:
        """
        Prepare review_state update for the Review Node.

        This stores the agent's output and review context in state.review_state
        so the Review Node can access it for human/LLM review.

        Args:
            node: The agent node
            state: Current workflow state
            input_message: The input message (for re-execution with feedback)
            response: The agent's response to review
            review_config: Review configuration

        Returns:
            Dictionary to update review_state with
        """
        # Get existing review data (may have history from previous iterations)
        existing_review_state = state.get("review_state", {})
        existing_data = existing_review_state.get(node.uniq_id, {})

        # Preserve history from previous iterations
        history = existing_data.get("history", [])
        iteration = len(history) + 1

        agent_executor_logger.info(
            f"[REVIEW-NODE] Preparing review_state for {node.name}: "
            f"iteration={iteration}, history_length={len(history)}"
        )

        # Build config dict with all fields needed for review
        config_dict = {
            "review_enabled": review_config.review_enabled,
            "review_mode": review_config.review_mode,
            "review_prompt": review_config.review_prompt,
            "max_iterations": review_config.max_iterations,
            "auto_approve_on_max_iterations": getattr(
                review_config, "auto_approve_on_max_iterations", True
            ),
            "timeout_seconds": getattr(review_config, "timeout_seconds", None),
        }

        # Include reviewer_llm_config if present (required for LLM review mode)
        if (
            hasattr(review_config, "reviewer_llm_config")
            and review_config.reviewer_llm_config
        ):
            from dataclasses import asdict

            config_dict["reviewer_llm_config"] = asdict(
                review_config.reviewer_llm_config
            )

        return {
            node.uniq_id: {
                "output": response,
                "config": config_dict,
                "iteration": iteration,
                "history": history,
                "input_message": input_message,
            }
        }

    async def _handle_error(
        self,
        node: EnhancedNodeData,
        state: WorkflowState,
        error_message: str,
        start_time: float,
        node_exec_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Handle agent execution error.

        Args:
            node: The agent node
            state: Current workflow state
            error_message: Error message
            start_time: Execution start time
            node_exec_id: Optional database node execution ID for WS matching

        Returns:
            Error state update
        """
        # Send error notification with database ID so the frontend can match the timeline entry
        await self.notification_handler.notify_error(
            node, state, error_message, "AGENT", node_exec_id=node_exec_id
        )

        # Build error state update
        error_output = {
            "raw": f"Error: {error_message}",
            "structured": {"error": error_message, "success": False},
            "fields": {"error": error_message},
        }

        order_update = self.database_tracker.increment_execution_order(state)

        return {
            "node_output": error_output,
            **order_update,
        }


def _build_message_structure(
    input_message: str,
    response: str,
    token_counts: Optional[Dict[str, int]],
    tool_execution_tracker: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Build message structure for trace viewer from available execution data.

    Args:
        input_message: The user/human input message
        response: The agent's response text
        token_counts: Token usage counts (input_tokens, output_tokens, etc.)
        tool_execution_tracker: List of tool execution records

    Returns:
        Message structure dict with messages list for the trace viewer
    """
    messages = []

    # Human/user message
    input_tokens = token_counts.get("input_tokens", 0) if token_counts else 0
    messages.append(
        {
            "role": "human",
            "content": input_message[:1000] if input_message else "",
            "token_count": input_tokens,
        }
    )

    # Build tool_calls summary from tracker
    tool_calls = []
    if tool_execution_tracker:
        for tool_exec in tool_execution_tracker:
            tool_name = tool_exec.get("tool") or tool_exec.get("tool_name") or "unknown"
            tool_calls.append({"name": tool_name})

    # Assistant message
    output_tokens = token_counts.get("output_tokens", 0) if token_counts else 0
    assistant_msg: Dict[str, Any] = {
        "role": "assistant",
        "content": response[:1000] if response else "",
        "token_count": output_tokens,
    }
    if tool_calls:
        assistant_msg["tool_calls"] = tool_calls

    messages.append(assistant_msg)

    return {
        "messages": messages,
        "message_count": len(messages),
    }
