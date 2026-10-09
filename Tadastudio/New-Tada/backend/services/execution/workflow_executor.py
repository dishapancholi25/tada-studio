"""
Workflow Executor for graph execution.

This module handles the complete workflow execution lifecycle,
from initialization through streaming execution to finalization.
"""

import asyncio
import threading
from dataclasses import asdict
from datetime import timezone, datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

from langchain_core.messages import HumanMessage

from backend.models.workflow import NodeType
from backend.services.common.utils.websocket_notifier import ws_notifier
from backend.services.config import get_logger
from backend.services.config.execution import ExecutionConfig
from backend.services.io.extractors.final import FinalOutputExtractor
from backend.services.io.output_processor import OutputProcessor
from backend.services.streaming.event_emitter import StreamWriterRegistry
from backend.services.workflow.state import WorkflowState
from backend.services.execution.checkpointer_manager import (
    get_checkpointer_manager,
    get_thread_checkpointer,
)


from .context import clear_execution_context, set_execution_context
from .history import ExecutionHistoryService

if TYPE_CHECKING:
    from backend.models import GraphData
    from backend.services.execution.engine import ExecutionEngine

# Initialize logger
execution_logger = get_logger("execution.workflow")


def _get_subworkflow_internal_node_ids(graph: "GraphData") -> Set[str]:
    """
    Identify all node IDs that are internal to subworkflows.

    These nodes should not be processed as part of the main workflow -
    they only execute when the subworkflow runs as a tool from an agent.

    Args:
        graph: The workflow graph definition

    Returns:
        Set of node IDs that are internal to subworkflows
    """
    internal_node_ids: Set[str] = set()

    # Find all SUBWORKFLOW nodes
    subworkflow_nodes = [n for n in graph.nodes if n.type == NodeType.SUBWORKFLOW]

    for sw_node in subworkflow_nodes:
        # Traverse from subworkflow's nexts to find all internal nodes
        nodes_to_process = list(sw_node.nexts or [])
        processed: Set[str] = set()

        while nodes_to_process:
            node_id = nodes_to_process.pop(0)
            if node_id in processed:
                continue
            processed.add(node_id)
            internal_node_ids.add(node_id)

            # Find the node and add its nexts (unless it's an END node)
            node = next((n for n in graph.nodes if n.uniq_id == node_id), None)
            if node and node.type != NodeType.END and node.nexts:
                nodes_to_process.extend(node.nexts)

    return internal_node_ids


class WorkflowExecutor:
    """
    Handles complete workflow execution lifecycle.

    This class orchestrates:
    - Graph setup and context initialization
    - Database tracking and WebSocket notifications
    - START node processing
    - Streaming execution with pause/resume support
    - END node processing and finalization

    Attributes:
        engine: Reference to the main execution engine
    """

    def __init__(self, engine: "ExecutionEngine"):
        """
        Initialize the WorkflowExecutor.

        Args:
            engine: The main execution engine instance
        """
        self.engine = engine

    @staticmethod
    def _build_chat_memory_context(chat_session_id: str | None):
        """Build memory context from chat history if this is a chat execution.

        Uses synchronous DB operations to avoid async/event-loop issues
        when called from executor threads.

        Args:
            chat_session_id: Chat session ID, or None for non-chat executions

        Returns:
            MemoryContext dict or None
        """
        if not chat_session_id:
            return None

        try:
            from backend.services.chat.memory import ChatMemoryService

            chat_memory = ChatMemoryService()
            return chat_memory.build_memory_context_sync(chat_session_id)
        except Exception as e:
            execution_logger.warning(f"Failed to build chat memory context: {e}")
            return None

    @staticmethod
    def _store_chat_memory(
        chat_session_id: str,
        user_message: str,
        graph_name: str,
        db_execution_id: str,
    ) -> None:
        """Store chat conversation turn after execution completes.

        Uses synchronous DB operations to avoid async/event-loop issues
        when called from executor threads.

        Args:
            chat_session_id: Chat session ID
            user_message: The user's original message
            graph_name: Workflow name
            db_execution_id: Database execution ID
        """
        try:
            from backend.services.chat.memory import ChatMemoryService
            from backend.services.chat.response_extractor import ChatResponseExtractor
            from backend.services.execution.history import ExecutionHistoryService

            execution_data = ExecutionHistoryService.get_graph_execution_dict(db_execution_id)
            if not execution_data:
                execution_logger.warning(
                    f"Cannot store chat memory: execution {db_execution_id} not found"
                )
                return

            response_text = ChatResponseExtractor.extract(execution_data)

            chat_memory = ChatMemoryService()
            chat_memory.store_chat_turn_sync(
                chat_session_id=chat_session_id,
                user_message=user_message,
                assistant_response=response_text,
                graph_execution_id=str(db_execution_id),
                workflow_name=graph_name,
            )

            execution_logger.info(
                f"Stored chat memory for session {chat_session_id}"
            )
        except Exception as e:
            execution_logger.warning(f"Failed to store chat memory: {e}")

    async def execute(
        self,
        graph: "GraphData",
        initial_input: dict[str, Any],
        execution_id: str,
        user_id: str | None = None,
        workflow_id: str | None = None,
        graph_definition_id: str | None = None,
        user_access_token: str | None = None,
        evaluation_run_id: str | None = None,
        trigger_type: str | None = None,
        phoenix_project_name: str | None = None,
        chat_session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a complete workflow graph.

        Args:
            graph: The workflow graph definition
            initial_input: Initial input data
            execution_id: Unique execution identifier (thread_id)
            user_id: User executing the graph
            workflow_id: Workflow UUID
            graph_definition_id: Graph definition UUID
            user_access_token: User's JWT access token for MCP servers with oauth2 auth
            evaluation_run_id: Associated evaluation run UUID
            trigger_type: Execution trigger type (editor, api, evaluation, scheduler, chat)
            phoenix_project_name: Override Phoenix project name (used by evaluations
                to route traces to the workflow project instead of a separate eval project)
            chat_session_id: Optional chat session ID for chat-triggered executions

        Returns:
            Execution result with status, outputs, and metadata
        """
        execution_logger.info(
            f"Starting LangGraph execution: {execution_id} for graph: {graph.name}"
        )
        execution_logger.debug(f"Initial input: {initial_input}")

        db_execution_id = None

        try:
            # Phase 1: Initialize execution context
            db_execution_id = await self._initialize_execution_context(
                graph,
                initial_input,
                execution_id,
                user_id,
                workflow_id,
                graph_definition_id,
                user_access_token,
                evaluation_run_id=evaluation_run_id,
                trigger_type=trigger_type,
                chat_session_id=chat_session_id,
            )

            # Define the main execution coroutine to be wrapped in a cancellable task
            async def _run_execution() -> Dict[str, Any]:
                # Wrap all execution phases in Phoenix per-workflow context
                # so spans are routed to a project named after the workflow
                # and carry execution metadata for correlation.
                from backend.services.phoenix.tracing import phoenix_workflow_context

                with phoenix_workflow_context(
                    graph_name=phoenix_project_name or graph.name,
                    execution_id=execution_id,
                    db_execution_id=str(db_execution_id) if db_execution_id else None,
                    workflow_id=workflow_id,
                    user_id=user_id,
                    trigger_type=trigger_type,
                    evaluation_run_id=evaluation_run_id,
                ) as phoenix_ctx:
                    return await self._run_execution_phases(
                        graph=graph,
                        initial_input=initial_input,
                        execution_id=execution_id,
                        db_execution_id=db_execution_id,
                        user_id=user_id,
                        phoenix_project=phoenix_ctx.project_name,
                        phoenix_ctx=phoenix_ctx,
                        chat_session_id=chat_session_id,
                    )

            # Create execution as a cancellable task for hard stop support
            # Initialize task reference placeholder first to prevent race condition
            # where request_stop could be called between task creation and storage
            if execution_id in self.engine.active_executions:
                self.engine.active_executions[execution_id]["execution_task"] = None

            execution_task = asyncio.create_task(_run_execution())

            # Store actual task reference
            if execution_id in self.engine.active_executions:
                self.engine.active_executions[execution_id]["execution_task"] = (
                    execution_task
                )

            return await execution_task

        except asyncio.CancelledError:
            # Hard stop - execution was cancelled via task.cancel()
            execution_logger.info(
                f"[HARD-STOP] Execution {execution_id} was hard stopped (CancelledError)"
            )
            await self._handle_hard_stop(graph, execution_id, db_execution_id)
            return {
                "status": "stopped",
                "execution_id": db_execution_id,
                "graph_name": graph.name,
                "stopped_reason": "Hard stop requested by user",
                "partial_state": self.engine.active_executions.get(
                    execution_id, {}
                ).get("partial_state_snapshot"),
            }
        finally:
            # Always clear execution context to prevent resource leaks
            clear_execution_context()

    async def _run_execution_phases(
        self,
        *,
        graph: "GraphData",
        initial_input: dict[str, Any],
        execution_id: str,
        db_execution_id: int | None,
        user_id: str | None,
        phoenix_project: str,
        phoenix_ctx: Optional[Any] = None,
        chat_session_id: str | None = None,
    ) -> Dict[str, Any]:
        """Run execution phases 2-6, called inside Phoenix context."""
        from backend.services.phoenix.tracing import PhoenixContext, phoenix_root_span

        if phoenix_ctx is None:
            phoenix_ctx = PhoenixContext(project_name=phoenix_project)

        # Phase 1.5: Resolve workflow-level guardrails once for the entire execution
        workflow_guardrails_pipeline = None
        guardrails_state: Dict[str, Any] = {}
        if graph.workflow_id:
            try:
                from backend.services.guardrails import get_guardrails_engine

                guardrails_engine = get_guardrails_engine()
                resolved = guardrails_engine.resolve_unified(
                    workflow_id=graph.workflow_id,
                )
                workflow_guardrails_pipeline = resolved.agent_pipeline  # List[GuardrailsConfig]
                if workflow_guardrails_pipeline:
                    modes = [c.enforcement_mode for c in workflow_guardrails_pipeline if c.enabled]
                    execution_logger.info(
                        f"Resolved workflow guardrails for workflow_id={graph.workflow_id}: "
                        f"{len(workflow_guardrails_pipeline)} policies, enforcement_modes={modes}"
                    )
                else:
                    workflow_guardrails_pipeline = None
            except Exception as e:
                execution_logger.warning(f"Failed to resolve workflow guardrails: {e}")
                workflow_guardrails_pipeline = None

        # Phase 2: Process START node (with workflow ingress guardrails)
        await self._process_start_node(
            graph,
            initial_input,
            execution_id,
            db_execution_id,
            workflow_guardrails_pipeline=workflow_guardrails_pipeline,
            guardrails_state=guardrails_state,
        )

        # Phase 3: Build and compile graph
        app, initial_state = await self._build_and_compile_graph(
            graph,
            initial_input,
            execution_id,
            db_execution_id,
            user_id,
            workflow_guardrails_pipeline=workflow_guardrails_pipeline,
            guardrails_state=guardrails_state,
            chat_session_id=chat_session_id,
        )

        # Phase 4: Execute workflow with streaming.
        # phoenix_root_span establishes the Phoenix trace root when Phoenix is
        # enabled; when disabled it short-circuits and the OpenInference
        # LangGraph span is the effective trace root. Langfuse trace/observation
        # metadata is applied onto the native auto spans by the
        # NodeMetadataSpanProcessor.
        user_input = (
            initial_input.get("message", "")
            or initial_input.get("user_message", "")
        )
        with phoenix_root_span(
            phoenix_ctx,
            graph_name=graph.name,
            execution_id=execution_id,
            input_value=user_input,
        ):
            final_state, control_result = await self._execute_streaming(
                app, graph, initial_state, execution_id, db_execution_id
            )

        # Phase 5: Handle control outcomes (pause, stop, guardrail block)
        if control_result is not None:
            status = control_result.get("status")
            if status == "paused":
                return control_result
            if status == "stopped":
                await self._finalize_force_stop(
                    graph,
                    execution_id,
                    db_execution_id,
                    control_result,
                )
                return control_result
            if status == "failed":
                # Guardrail block or other failure handled during streaming
                return control_result

        # Phase 6: Finalize execution
        result = await self._finalize_execution(
            graph, final_state, execution_id, db_execution_id
        )

        # Phase 6b: Store chat memory if this is a chat-triggered execution
        user_message = initial_input.get("message", "") or initial_input.get(
            "user_message", ""
        )
        if chat_session_id and db_execution_id:
            self._store_chat_memory(
                chat_session_id=chat_session_id,
                user_message=user_message,
                graph_name=graph.name,
                db_execution_id=str(db_execution_id),
            )

        # Phase 6c: Judge the chat response for the dashboard Accuracy metric.
        # Chat executions always run inside their own per-execution event loop
        # in a background thread (see execution_manager.execute_graph_in_thread),
        # which is closed immediately after this coroutine returns -- a
        # fire-and-forget asyncio.create_task() here would never get scheduled
        # before loop.close() destroys it. The real chat HTTP response was
        # already returned earlier (submit_execution doesn't block on this
        # thread), so awaiting directly here adds no user-facing latency.
        # Failures are swallowed here too (not just inside score_chat_response)
        # so this optional feature can never break chat execution.
        if chat_session_id and db_execution_id:
            try:
                from backend.services.evaluation.chat_scoring import score_chat_response

                await score_chat_response(graph, db_execution_id, result, user_message)
            except Exception as e:
                execution_logger.warning(f"Failed to schedule chat response scoring: {e}")

        # Attach trace context for callers (e.g. evaluation orchestrator)
        # that need a Phoenix deep-link.
        if phoenix_ctx.trace_id:
            result["phoenix_trace_ref"] = {
                "project": phoenix_ctx.project_name,
                "trace_id": phoenix_ctx.trace_id,
                "span_id": phoenix_ctx.span_id,
            }

            # Langfuse shares the same OTel trace_id, so reuse it for a
            # Langfuse deep-link. Returns None when Langfuse is disabled.
            from backend.services.langfuse.tracing import build_langfuse_trace_ref

            langfuse_ref = build_langfuse_trace_ref(phoenix_ctx.trace_id)
            if langfuse_ref:
                result["langfuse_trace_ref"] = langfuse_ref

        # Best-effort: build the Phoenix deep-link from the actual project the
        # spans landed in, looked up by the execution's session id
        # (execution_id == session.id). This mirrors the standalone test script
        # and corrects the link when another SDK (e.g. Langfuse) relocates the
        # spans to a different Phoenix project. Independent of the trace context
        # above so it never affects the Phoenix tracer or the Langfuse path.
        try:
            from backend.services.phoenix.config import (
                build_phoenix_trace_ref_by_session,
            )

            # Force-flush pending spans so Phoenix has ingested them before we
            # query by session id. Without this, the by-session lookup can race
            # the OTel BatchSpanProcessor and return nothing (notably when
            # Langfuse is disabled and adds no incidental delay). Best-effort.
            try:
                from opentelemetry import trace as _otel_trace

                _provider = _otel_trace.get_tracer_provider()
                if hasattr(_provider, "force_flush"):
                    _provider.force_flush(timeout_millis=10_000)
            except Exception as e:
                execution_logger.debug(
                    f"Phoenix span force_flush failed (non-fatal): {e}"
                )

            phoenix_ref = build_phoenix_trace_ref_by_session(execution_id)
            if phoenix_ref:
                result["phoenix_trace_ref"] = phoenix_ref
        except Exception as e:
            execution_logger.debug(
                f"Could not build Phoenix trace ref by session (non-fatal): {e}"
            )
        

        if phoenix_ctx.trace_id or result.get("phoenix_trace_ref"):

            # Persist the trace refs to the execution record so they can be
            # retrieved later via GET /execution/{id}/history. The first DB
            # update in _finalize_execution() runs before these refs are
            # attached, so a lightweight second update is needed here.
            if db_execution_id:
                try:
                    ExecutionHistoryService.update_graph_execution(
                        execution_id=db_execution_id,
                        output_data=result,
                    )
                except Exception as e:
                    execution_logger.warning(
                        f"Failed to persist trace refs to DB (non-fatal): {e}"
                    )
            
           

        try:
            
            from backend.services.langfuse.tracing import get_langfuse_session_url

            langfuse_url = get_langfuse_session_url(str(execution_id))
            result["langfuse_trace_ref"]= {'url': langfuse_url}
            print(f"Langfuse session URL: {langfuse_url}")

                

        except Exception as e:
            execution_logger.warning(f"Error creating Langfuse session URL: {e}")
        if db_execution_id:
                try:
                    ExecutionHistoryService.update_graph_execution(
                        execution_id=db_execution_id,
                        output_data=result,
                    )
                except Exception as e:
                    execution_logger.warning(
                        f"Failed to persist trace refs to DB (non-fatal): {e}"
                    )
        
        return result

    async def _initialize_execution_context(
        self,
        graph: "GraphData",
        initial_input: dict[str, Any],
        execution_id: str,
        user_id: str | None,
        workflow_id: str | None,
        graph_definition_id: str | None,
        user_access_token: str | None = None,
        evaluation_run_id: str | None = None,
        trigger_type: str | None = None,
        chat_session_id: str | None = None,
    ) -> int | None:
        """Initialize execution context and database record."""
        # Set the current graph name on graph_manager for tool resolution
        try:
            self.engine.graph_manager.current_graph_name = graph.name
            execution_logger.info(
                f"Set graph_manager.current_graph_name to: {graph.name}"
            )
        except AttributeError as e:
            execution_logger.warning(
                f"Could not set current_graph_name on graph_manager: {e}"
            )
            # Try to set it as a new attribute if it doesn't exist
            self.engine.graph_manager.current_graph_name = graph.name
            execution_logger.info(
                f"Added current_graph_name attribute to graph_manager: {graph.name}"
            )

        # Create execution record in database
        db_execution = None
        db_execution_id = None
        try:
            execution_logger.info(
                f"[EXEC TRACKING] Creating execution record with workflow_id={workflow_id}, "
                f"graph_definition_id={graph_definition_id}, user_id={user_id}"
            )

            db_execution = ExecutionHistoryService.create_graph_execution(
                graph_id=graph.name,
                graph_name=graph.name,
                graph_definition=asdict(graph),
                input_data=initial_input,
                user_id=user_id,
                thread_id=execution_id,
                websocket_execution_id=execution_id,
                workflow_id=workflow_id,
                graph_definition_id=graph_definition_id,
                evaluation_run_id=evaluation_run_id,
                trigger_type=trigger_type,
                chat_session_id=chat_session_id,
            )
            db_execution_id = db_execution["id"]
            try:
                from backend.services.websocket import manager as ws_manager

                ws_manager.consume_pending(execution_id)
            except Exception as pending_error:
                execution_logger.debug(
                    f"Failed to consume pending WebSocket registration for {execution_id}: {pending_error}"
                )
            execution_logger.info(
                f"[EXEC TRACKING] Created database execution record: {db_execution_id} "
                f"(workflow_id={workflow_id}, definition_id={graph_definition_id}, user={user_id})"
            )
        except Exception as e:
            execution_logger.error(f"Failed to create execution record: {e}")
            execution_logger.warning("Continuing with in-memory tracking only")

        # Register active execution
        self.engine.active_executions[execution_id] = {
            "execution_id": execution_id,
            "status": "running",
            "start_time": str(datetime.now(timezone.utc)),
            "graph_name": graph.name,
            "current_node": None,
            "current_node_name": None,
            "error": None,
            "db_execution_id": db_execution_id,
            "node_execution_map": {},
            "control": {
                "force_stop": False,
                "force_stop_requested": False,
                "force_stop_finalized": False,
                "pause_requested": False,
                "pause_target_node": None,
                "pause_request_time": None,
                "pause_target_node_name": None,
                "pause_finalized": False,
                "pause_ready": False,
                "pause_node_execution_id": None,
                "pause_trigger_pending": False,
            },
            "event_loop": asyncio.get_running_loop(),
            "stream_generator": None,
        }

        # Notify adapter about db_execution_id if available
        if db_execution_id and hasattr(self.engine, "adapter") and self.engine.adapter:
            self.engine.adapter.update_execution_metadata(execution_id, db_execution_id)

        # Set execution context for sub-agent tracking
        set_execution_context(
            execution_id,
            db_execution_id,
            {},
            user_access_token=user_access_token,
            user_id=user_id,
        )

        return db_execution_id

    async def _process_start_node(
        self,
        graph: "GraphData",
        initial_input: dict[str, Any],
        execution_id: str,
        db_execution_id: int | None,
        workflow_guardrails_pipeline=None,
        guardrails_state: dict[str, Any] | None = None,
    ) -> datetime:
        """Process START node execution and tracking."""
        start_nodes = [n for n in graph.nodes if n.type == NodeType.START]
        if not start_nodes:
            return datetime.now(timezone.utc)

        start_node = start_nodes[0]
        start_time = datetime.now(timezone.utc)

        # Get the message for START node output
        message = initial_input.get("message", "") or initial_input.get(
            "user_message", ""
        )

        # Apply workflow ingress guardrails to the user's input message
        if workflow_guardrails_pipeline and message:
            try:
                from backend.services.guardrails import get_guardrails_engine
                from backend.services.guardrails.violation_persistence import (
                    ViolationPersistenceService,
                )
                from backend.services.streaming.event_emitter import (
                    StreamingEventEmitter,
                )

                engine = get_guardrails_engine()
                _gs = guardrails_state if guardrails_state is not None else {}
                input_result = await engine.check_input(
                    message,
                    workflow_guardrails_pipeline,
                    guardrails_state=_gs,
                )

                if input_result.violations:
                    for v in input_result.violations:
                        violation_db_id = ViolationPersistenceService.persist_violation(
                            v,
                            category="workflow_ingress",
                            action_taken=input_result.action_taken or "blocked",
                            policy_id=v.policy_id or None,
                            policy_name=v.policy_name or None,
                            workflow_id=graph.workflow_id,
                            graph_execution_id=str(db_execution_id)
                            if db_execution_id
                            else None,
                        )
                        StreamingEventEmitter.emit_guardrail_violation(
                            category="workflow_ingress",
                            rule_name=v.rule_name or "unknown",
                            message=v.message or "Workflow input violation",
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
                        else "Workflow input blocked by guardrail"
                    )
                    raise GuardrailViolationError(
                        f"Workflow input blocked: {violation_msg}",
                        violations=input_result.violations,
                    )

                if input_result.sanitized_content is not None:
                    execution_logger.info(
                        "[WORKFLOW-GUARDRAILS] START input sanitized by workflow guardrails"
                    )
                    message = input_result.sanitized_content
                    # Update initial_input so downstream code uses the sanitized message
                    if "message" in initial_input:
                        initial_input["message"] = message
                    elif "user_message" in initial_input:
                        initial_input["user_message"] = message

            except ImportError:
                execution_logger.warning(
                    "Guardrails modules not available, skipping START ingress check"
                )
            except Exception as e:
                if "GuardrailViolationError" in type(e).__name__:
                    raise
                execution_logger.warning(
                    f"Workflow START ingress guardrail check failed: {e}"
                )

        # Create database record for START node
        if db_execution_id:
            try:
                # Create the node execution first
                node_exec = ExecutionHistoryService.create_node_execution(
                    graph_execution_id=db_execution_id,
                    node_id=start_node.uniq_id,
                    node_name=start_node.name,
                    node_type="START",
                    execution_order=0,
                    input_data=initial_input,
                )

                # Mark it as started
                ExecutionHistoryService.start_node_execution(node_exec["id"])

                # Complete it immediately since START nodes execute instantly
                start_message = message if message else "Workflow started"
                start_output = {
                    "raw": start_message,
                    "structured": None,
                    "fields": {},
                    "file_info": initial_input.get("file_info"),
                }
                ExecutionHistoryService.complete_node_execution(
                    node_execution_id=node_exec["id"],
                    status="completed",
                    output_data=start_output,
                )
                execution_logger.info(
                    "Created START node execution record with proper timestamps"
                )

                # Send WebSocket notifications for START node
                if ws_notifier and execution_id:
                    await self._send_start_notifications(
                        execution_id,
                        start_node,
                        start_output,
                        initial_input,
                        start_time,
                        node_exec["id"],
                    )

            except Exception as e:
                execution_logger.error(f"Failed to create START node execution: {e}")

        # Update adapter if available
        if hasattr(self.engine, "adapter") and self.engine.adapter:
            self.engine.adapter.update_node_status(
                execution_id=execution_id,
                node_id=start_node.uniq_id,
                node_name=start_node.name,
                status="completed",
                start_time=start_time,
                end_time=start_time,
            )

        return start_time

    async def _send_start_notifications(
        self,
        execution_id: str,
        start_node,
        start_output: dict[str, Any],
        initial_input: dict[str, Any],
        start_time: datetime,
        node_exec_id: int,
    ):
        """Send START node WebSocket notifications."""
        try:

            async def send_notifications():
                await ws_notifier.on_node_start(
                    execution_id,
                    start_node.uniq_id,
                    start_node.name,
                    "START",
                    None,  # is_sub_agent
                    None,  # parent_agent_id
                    node_exec_id,
                )
                await ws_notifier.on_node_complete(
                    execution_id,
                    start_node.uniq_id,
                    start_node.name,
                    start_output,
                    "START",
                    0.0,  # START nodes execute instantly
                    initial_input,
                    str(start_time) if start_time else None,
                    str(start_time) if start_time else None,
                    None,  # input_tokens
                    None,  # output_tokens
                    None,  # total_tokens
                    None,  # is_sub_agent
                    None,  # parent_agent_id
                    node_exec_id,
                )
                execution_logger.info("Sent WebSocket notifications for START node")

            # ConnectionManager handles cross-loop dispatch internally via its
            # drain queue, so we can await directly from any event loop.
            await send_notifications()

        except Exception as e:
            execution_logger.error(
                f"Failed to send START node WebSocket notifications: {e}"
            )

    async def _build_and_compile_graph(
        self,
        graph: "GraphData",
        initial_input: dict[str, Any],
        execution_id: str,
        db_execution_id: int | None,
        user_id: str | None = None,
        workflow_guardrails_pipeline=None,
        guardrails_state: dict[str, Any] | None = None,
        chat_session_id: str | None = None,
    ):
        """Build and compile the state graph with initial state."""
        # Build the LangGraph StateGraph
        workflow = self.engine._build_state_graph(graph, execution_id, db_execution_id)

        # Compile with thread-local checkpointer for persistence.
        # Use the async path so the connection pool is initialised on the same
        # event loop that will drive graph execution, avoiding cross-loop I/O hangs
        # that cause the execution to stall silently after StateGraph build.
        checkpointer = await get_checkpointer_manager().get_checkpointer_async()
        app = workflow.compile(checkpointer=checkpointer)

        # Prepare initial state
        message = initial_input.get("message", "") or initial_input.get(
            "user_message", ""
        )

        # Find the START node to add its output to state
        start_node = None
        for node in graph.nodes:
            if node.type == NodeType.START:
                start_node = node
                break

        # Initialize node_outputs with START node's output
        initial_node_outputs = {}
        if start_node:
            start_output = message if message else "Workflow started"
            initial_node_outputs[start_node.uniq_id] = {
                "raw": start_output,
                "structured": None,
                "fields": {},
                "file_info": initial_input.get("file_info"),
            }
            execution_logger.info(
                f"Added START node output to state: {start_node.uniq_id} -> "
                f"output: '{start_output[:100]}...'"
            )

        initial_state: WorkflowState = {
            "messages": [HumanMessage(content=message)],
            "original_message": message,
            "node_outputs": initial_node_outputs,
            "results": [],
            "current_node": None,
            "execution_id": execution_id,
            "db_execution_id": db_execution_id,
            "graph_name": graph.name,
            "file_info": initial_input.get("file_info"),
            "metadata": {
                "execution_started": datetime.now(timezone.utc).isoformat(),
                "initial_input": initial_input,
            },
            "memory_context": self._build_chat_memory_context(chat_session_id),
            "orchestration_context": None,
            "custom_data": None,
            "execution_order": 1,  # START=0, first agent=1
            "subgraph_context": None,
            "user_id": user_id,  # For OAuth token lookup in MCP tools
            "workflow_id": graph.workflow_id or graph.name,  # Fallback to graph name for MCP tools
            "review_state": {},  # For agent review loop (Review Node)
            "pending_review": None,  # Legacy field for review resumption
            "guardrails_state": guardrails_state if guardrails_state else {},
            "workflow_guardrails_pipeline": (
                [c.to_dict() for c in workflow_guardrails_pipeline]
                if workflow_guardrails_pipeline else None
            ),
        }

        execution_logger.info(
            f"Initial state created with execution_order: {initial_state['execution_order']}"
        )

        return app, initial_state

    async def _execute_streaming(
        self,
        app,
        graph: "GraphData",
        initial_state: WorkflowState,
        execution_id: str,
        db_execution_id: int | None,
    ):
        """Execute workflow with streaming for real-time updates."""
        final_state = None
        paused_result = None
        stream_generator = None
        node_metadata_token = None

        # Register a bridge writer for subagent streaming
        # This allows subagent tools to send events to WebSocket even when running
        # in an isolated context (where get_stream_writer() returns None)
        main_loop = asyncio.get_running_loop()

        def bridge_stream_writer(event: dict) -> None:
            """Bridge function to send events to WebSocket from any thread.

            This is called by StreamingEventEmitter when get_stream_writer() fails
            (e.g., in subagent contexts). Uses run_coroutine_threadsafe to schedule
            the send on the main event loop, which is required because WebSocket
            connections are bound to that loop.
            """

            event_type = event.get("event_type", "unknown")
            tool_name = event.get("tool_name", event.get("subagent_name", "N/A"))
            thread_id = threading.current_thread().name

            execution_logger.info(
                f"[BRIDGE-STREAM] Received event: type={event_type}, "
                f"tool/agent={tool_name}, thread={thread_id}, exec_id={execution_id}"
            )

            try:
                # Check if we're on the main loop - if so, use create_task directly
                try:
                    running_loop = asyncio.get_running_loop()
                    if running_loop is main_loop:
                        # Same loop - just create a task (normal case, not subagent)
                        execution_logger.info(
                            f"[BRIDGE-STREAM] Same event loop, using create_task for {event_type}"
                        )
                        asyncio.create_task(
                            self._handle_stream_event(execution_id, "custom", event)
                        )
                        return
                except RuntimeError:
                    # No running loop - must be called from sync context (subagent case)
                    execution_logger.info(
                        f"[BRIDGE-STREAM] No running loop (subagent context), "
                        f"will use run_coroutine_threadsafe for {event_type}"
                    )

                # Schedule the coroutine on the main event loop from any thread.
                # This is critical: WebSocket connections are bound to main_loop,
                # so we cannot create a new event loop to send messages.
                execution_logger.info(
                    f"[BRIDGE-STREAM] Scheduling {event_type} on main loop via run_coroutine_threadsafe"
                )
                future = asyncio.run_coroutine_threadsafe(
                    self._handle_stream_event(execution_id, "custom", event),
                    main_loop,
                )
                # Wait for completion with timeout to ensure event is sent
                # before the calling context exits. Use a short timeout since
                # stream events should be fast.
                try:
                    future.result(timeout=5.0)
                    execution_logger.info(
                        f"[BRIDGE-STREAM] Successfully sent {event_type} for {tool_name}"
                    )
                except TimeoutError:
                    execution_logger.warning(
                        f"[BRIDGE-STREAM] Timeout sending {event_type} for {execution_id}"
                    )
            except Exception as e:
                execution_logger.error(
                    f"[BRIDGE-STREAM] Failed to send {event_type} for {execution_id}: {e}",
                    exc_info=True,
                )

        StreamWriterRegistry.register(execution_id, bridge_stream_writer)
        execution_logger.debug(
            f"Registered bridge stream writer for execution: {execution_id}"
        )

        try:
            # Configure stream modes
            stream_kwargs: dict[str, Any] = {}
            if ExecutionConfig.enable_streaming():
                stream_kwargs["stream_mode"] = ExecutionConfig.get_stream_modes()
                stream_kwargs["subgraphs"] = ExecutionConfig.include_subgraphs()
            else:
                stream_kwargs["stream_mode"] = ["updates"]

            # Populate task-local node metadata BEFORE app.astream() so the
            # NodeMetadataSpanProcessor can enrich each per-node auto CHAIN span
            # (human-readable name + node.* attributes) at span on_start.
            try:
                from backend.services.langfuse.node_enrichment import (
                    set_current_node_metadata,
                )

                node_metadata_map = {
                    node.uniq_id: {
                        "id": node.uniq_id,
                        "name": node.name,
                        "type": getattr(node.type, "value", str(node.type)),
                        "execution_id": execution_id,
                    }
                    for node in graph.nodes
                    if getattr(node, "uniq_id", None)
                }
                # Reserved key consumed by NodeMetadataSpanProcessor.on_start to
                # stamp the Langfuse trace name (workflow name) on the root span.
                node_metadata_map["__workflow_root__"] = {
                    "graph_name": graph.name,
                    "execution_id": execution_id,
                    "workflow_id": graph.workflow_id,
                }
                node_metadata_token = set_current_node_metadata(node_metadata_map)
            except Exception as meta_exc:
                execution_logger.debug(
                    f"Could not populate node metadata for span enrichment "
                    f"(non-fatal): {meta_exc}"
                )

            # Create the async generator
            stream_generator = app.astream(
                initial_state,
                config={
                    "configurable": {"thread_id": execution_id},
                    "recursion_limit": 50,
                },
                **stream_kwargs,
            )
            if execution_id in self.engine.active_executions:
                self.engine.active_executions[execution_id]["stream_generator"] = (
                    stream_generator
                )
                control = self.engine.active_executions[execution_id].get("control", {})
                if control.get("pause_trigger_pending"):
                    await self.trigger_pause(execution_id)
                    control = self.engine.active_executions[execution_id].get(
                        "control", {}
                    )
                if control.get("force_stop"):
                    await self.trigger_force_stop(execution_id)
                    control = self.engine.active_executions[execution_id].get(
                        "control", {}
                    )

            async for raw_chunk in stream_generator:
                # Normalize stream payload shape
                # Handle both (namespace, mode, data) and (mode, data) formats
                mode = None
                chunk = raw_chunk
                namespace = ()  # Root namespace is empty tuple
                if isinstance(raw_chunk, tuple):
                    if len(raw_chunk) == 3:
                        # subgraphs=True format: (namespace, mode, data)
                        namespace, mode, chunk = raw_chunk
                    elif len(raw_chunk) == 2:
                        # subgraphs=False format: (mode, data)
                        mode, chunk = raw_chunk
                if mode is None:
                    # Backward-compatible default when stream_mode is ["updates"]
                    mode = "updates"

                control = self.engine.active_executions.get(execution_id, {}).get(
                    "control", {}
                )

                # Check for __interrupt__ in ANY dict chunk, regardless of mode
                # This ensures interrupts are detected even when stream_mode includes
                # multiple modes like ["updates", "messages", "custom"]
                if isinstance(chunk, dict) and "__interrupt__" in chunk:
                    execution_logger.info(
                        f"__interrupt__ detected in stream (mode: {mode})"
                    )
                    paused_result = await self._handle_interrupt(
                        chunk, execution_id, db_execution_id, graph
                    )
                    if paused_result:
                        execution_logger.info(
                            "Workflow paused at checkpoint, breaking from stream"
                        )
                        break

                # Stop immediately if a force stop was requested
                if control.get("force_stop"):
                    execution_logger.info(
                        f"Force stop flag detected for execution {execution_id}"
                    )
                    break

                # Handle token/custom streaming
                if mode == "messages":
                    await self._handle_stream_event(execution_id, "token", chunk)
                    continue
                if mode == "custom":
                    await self._handle_stream_event(execution_id, "custom", chunk)
                    continue

                # Process state update chunks (updates/values)
                if mode in {"updates", "values"} and isinstance(chunk, dict):
                    for node_name, node_updates in chunk.items():
                        if node_updates:
                            if final_state is None:
                                final_state = {}
                            # Merge state updates
                            if "node_outputs" in node_updates:
                                final_state.setdefault("node_outputs", {}).update(
                                    node_updates["node_outputs"]
                                )
                            if "results" in node_updates:
                                final_state.setdefault("results", []).extend(
                                    node_updates.get("results", [])
                                )
                            for key in [
                                "messages",
                                "current_node",
                                "metadata",
                                "execution_order",
                            ]:
                                if key in node_updates:
                                    final_state[key] = node_updates[key]

                            # Process state update for tracking
                            await self.engine.state_processor.process_update(
                                node_updates, execution_id, db_execution_id
                            )

                        # Mark pause-ready when the targeted node finishes
                        if (
                            control.get("pause_requested")
                            and not control.get("pause_ready")
                            and control.get("pause_target_node")
                        ):
                            target_node = control.get("pause_target_node")
                            node_id = node_updates.get("node_id")
                            status_value = node_updates.get("status")
                            if node_id == target_node and status_value in {
                                "completed",
                                "failed",
                                "cancelled",
                            }:
                                execution_logger.info(
                                    "[PAUSE-CONTROL] Target node %s finished with status %s for execution %s; marking pause_ready",
                                    target_node,
                                    status_value,
                                    execution_id,
                                )
                                control["pause_ready"] = True
                                break

                # Evaluate pause readiness after processing updates
                if control.get("pause_requested"):
                    if control.get("pause_ready"):
                        execution_logger.info(
                            "[PAUSE-CONTROL] pause_ready flag set for execution %s; breaking stream",
                            execution_id,
                        )
                        break
                    current_node = self.engine.active_executions.get(
                        execution_id, {}
                    ).get("current_node")
                    target_node = control.get("pause_target_node")
                    if target_node is None or (
                        current_node is not None and current_node != target_node
                    ):
                        control["pause_ready"] = True
                        execution_logger.info(
                            "[PAUSE-CONTROL] Current node advanced (current=%s, target=%s) for execution %s; breaking stream",
                            current_node,
                            target_node,
                            execution_id,
                        )
                        break

        except asyncio.CancelledError:
            execution_logger.warning(f"Workflow execution cancelled: {execution_id}")
            raise
        except Exception as e:
            execution_logger.error(f"Error during workflow streaming: {e}")
            await self._handle_execution_error(execution_id, db_execution_id, e)
            raise
        finally:
            # Ensure proper cleanup
            # Unregister stream writer bridge to prevent memory leaks
            StreamWriterRegistry.unregister(execution_id)
            execution_logger.debug(
                f"Unregistered bridge stream writer for execution: {execution_id}"
            )

            # Clear task-local node metadata used for span enrichment.
            if node_metadata_token is not None:
                try:
                    from backend.services.langfuse.node_enrichment import (
                        reset_current_node_metadata,
                    )

                    reset_current_node_metadata(node_metadata_token)
                except Exception as meta_reset_exc:
                    execution_logger.debug(
                        f"Failed to reset node metadata context (non-fatal): "
                        f"{meta_reset_exc}"
                    )

            if stream_generator is not None:
                try:
                    await stream_generator.aclose()
                except Exception as cleanup_error:
                    execution_logger.warning(
                        f"Error closing stream generator: {cleanup_error}"
                    )
            active_record = self.engine.active_executions.get(execution_id)
            if active_record is not None:
                active_record["stream_generator"] = None

                control = active_record.get("control", {})
                if control.get("force_stop"):
                    control["force_stop_finalized"] = True
                    return final_state, {
                        "status": "stopped",
                        "db_execution_id": db_execution_id,
                    }

                if (
                    control.get("pause_requested")
                    and control.get("pause_ready")
                    and not control.get("pause_finalized")
                ):
                    pause_result = await self._finalize_manual_pause(
                        graph,
                        execution_id,
                        db_execution_id,
                        control,
                    )
                    return final_state, pause_result

        return final_state, paused_result

    async def _handle_stream_event(
        self,
        execution_id: str,
        event_type: str,
        chunk: Any,
    ):
        """Serialize and forward streaming events to WebSocket clients.

        Includes detailed logging for debugging token streaming to correct node iterations.
        Also bridges tool streaming events to node updates for timeline display.
        """
        if not ws_notifier or not execution_id:
            return

        payload = self._serialize_stream_chunk(chunk)

        # Bridge tool streaming events to node updates for timeline
        # This allows tool nodes to show "running" spinner during execution
        if isinstance(payload, dict):
            event_type_inner = payload.get("event_type")

            # DEBUG: Log all tool-related events coming through
            if event_type_inner and "tool" in event_type_inner:
                execution_logger.info(
                    "[TOOL-BRIDGE-DEBUG] Received event_type=%s, payload_keys=%s, tool_node_id=%s",
                    event_type_inner,
                    list(payload.keys()),
                    payload.get("tool_node_id"),
                )

            # Debug: log when we see tool events without node info
            if event_type_inner == "tool_call_start" and not payload.get(
                "tool_node_id"
            ):
                execution_logger.warning(
                    "[TOOL-BRIDGE] tool_call_start received WITHOUT tool_node_id - cannot bridge. "
                    "tool_name=%s, keys=%s",
                    payload.get("tool_name"),
                    list(payload.keys()),
                )

            # NOTE: Tool streaming events (tool_call_start/complete/error) are NOT
            # bridged to on_node_start/complete/error anymore. The frontend now
            # handles these events directly via streaming callbacks to update
            # tool status in real-time. The tool_tracker.py still creates the
            # database record and sends a single node_update for the timeline.

        # Continue with existing stream event routing
        try:
            await ws_notifier.on_stream_event(
                execution_id,
                event_type,
                payload,
            )
        except Exception as exc:
            execution_logger.debug(
                "Failed to send stream event (%s) for %s: %s",
                event_type,
                execution_id,
                exc,
            )

    @staticmethod
    def _serialize_stream_chunk(chunk: Any) -> Any:
        """
        Convert LangGraph stream chunks to JSON-serializable payloads.

        Falls back to string representation if rich serialization isn't available.
        """
        if chunk is None:
            return None

        # Preserve path metadata if present (helps attribute tokens to nodes)
        path_value = None
        try:
            path_value = getattr(chunk, "path", None)
            if path_value:
                path_value = list(path_value)
        except Exception:
            path_value = None

        # Already serializable types
        if isinstance(chunk, (str, int, float, bool)):
            if path_value:
                return {"path": path_value, "content": chunk}
            return chunk
        if isinstance(chunk, dict):
            # Structured events from StreamingEventEmitter (guardrail_violation,
            # tool_call_start, etc.) are already JSON-serializable plain dicts.
            # Skip recursive serialization which mangles lists (e.g. single-element
            # arrays like entity_types:["CREDIT_CARD"] get unwrapped to bare strings
            # by the list/tuple branch designed for LangGraph message chunks).
            if "event_type" in chunk:
                return chunk
            data = {
                k: WorkflowExecutor._serialize_stream_chunk(v) for k, v in chunk.items()
            }
            if path_value and "path" not in data:
                data["path"] = path_value
            return data
        if isinstance(chunk, (list, tuple)):
            # Handle (message, metadata) tuples from "messages" stream mode
            # Extract content from message objects and node_id/step from metadata
            content_parts = []
            node_id = None  # Track which node this chunk belongs to
            step = None  # Track langgraph_step for iteration discrimination
            for item in chunk:
                if hasattr(item, "content"):
                    # This is a message chunk - extract just the content
                    content = item.content
                    if isinstance(content, list):
                        # Handle list content (multimodal)
                        content = "".join(
                            part if isinstance(part, str) else str(part)
                            for part in content
                        )
                    # Only add non-empty content
                    if content:
                        content_parts.append(content)
                elif isinstance(item, dict):
                    # Extract node_id and step from LangGraph metadata BEFORE skipping
                    # This allows us to attribute tokens to the correct node iteration
                    if "langgraph_node" in item and node_id is None:
                        node_id = item.get("langgraph_node")
                    if "langgraph_step" in item and step is None:
                        step = item.get("langgraph_step")
                    # Skip LangGraph metadata dicts (have keys like thread_id, langgraph_step)
                    # These are streaming metadata, not content we want to display
                    if any(
                        key in item
                        for key in (
                            "thread_id",
                            "langgraph_step",
                            "langgraph_node",
                            "checkpoint_ns",
                        )
                    ):
                        continue
                    # For other dicts, recursively serialize
                    content_parts.append(WorkflowExecutor._serialize_stream_chunk(item))
                else:
                    content_parts.append(WorkflowExecutor._serialize_stream_chunk(item))

            # Build result - either single item or joined string
            if len(content_parts) == 1:
                result = content_parts[0]
            elif len(content_parts) == 0:
                result = ""
            else:
                result = content_parts

            # Include node_id and step in result if available (for token attribution)
            if node_id:
                result_dict = {"content": result, "node_id": node_id}
                if step is not None:
                    result_dict["step"] = step
                return result_dict
            return result

        # Message chunks (AIMessageChunk, HumanMessageChunk, etc.) - extract content FIRST
        # before falling back to Pydantic model_dump() which would serialize the entire object
        content = getattr(chunk, "content", None)
        if content is not None:
            if isinstance(content, list):
                # Handle list content (multimodal)
                content = "".join(
                    part if isinstance(part, str) else str(part) for part in content
                )
            if path_value:
                return {"path": path_value, "content": content}
            return content

        # Pydantic/BaseModel style (for non-message objects)
        for attr in ("model_dump", "dict", "json"):
            fn = getattr(chunk, attr, None)
            if callable(fn):
                try:
                    data = fn()
                    if isinstance(data, str):
                        return (
                            {"path": path_value, "content": data}
                            if path_value
                            else data
                        )
                    data = WorkflowExecutor._serialize_stream_chunk(data)
                    if path_value and isinstance(data, dict) and "path" not in data:
                        data["path"] = path_value
                    return data
                except Exception:
                    pass

        # Fallback
        if path_value:
            return {"path": path_value, "content": str(chunk)}
        return str(chunk)

    async def trigger_force_stop(self, execution_id: str):
        """Close the active stream generator to enforce an immediate stop."""
        active = self.engine.active_executions.get(execution_id)
        if not active:
            execution_logger.info(
                f"Force stop requested for unknown execution {execution_id}"
            )
            return

        control = active.setdefault("control", {})
        control["force_stop"] = True

        generator = active.get("stream_generator")
        if generator is None:
            execution_logger.debug(
                f"No stream generator to close for execution {execution_id}"
            )
            return

        try:
            await generator.aclose()
            execution_logger.info(
                f"Closed stream generator for execution {execution_id}"
            )
        except Exception as exc:
            execution_logger.warning(
                f"Failed closing stream generator for execution {execution_id}: {exc}"
            )

    async def trigger_pause(self, execution_id: str):
        """Close the stream generator to transition into a manual pause."""
        active = self.engine.active_executions.get(execution_id)
        if not active:
            execution_logger.info(
                f"Pause trigger requested for unknown execution {execution_id}"
            )
            return

        control = active.setdefault("control", {})
        control["pause_ready"] = True
        control["pause_trigger_pending"] = False

        generator = active.get("stream_generator")
        if generator is None:
            execution_logger.debug(
                f"Pause trigger deferred; no generator for execution {execution_id}"
            )
            return

        try:
            await generator.aclose()
            execution_logger.info(
                f"Closed stream generator for manual pause on execution {execution_id}"
            )
        except Exception as exc:
            execution_logger.warning(
                f"Failed closing generator during pause for execution {execution_id}: {exc}"
            )

    async def _handle_interrupt(
        self,
        chunk: dict[str, Any],
        execution_id: str,
        db_execution_id: int | None,
        graph: "GraphData",
    ) -> dict[str, Any] | None:
        """Handle workflow interruption (pause)."""
        interrupts = chunk.get("__interrupt__") or ()
        prompt_value = None
        inbox_address = None
        node_name = "Checkpoint"
        paused_node_id = None
        interrupt_type = "unknown"

        # Extract interrupt data
        if isinstance(interrupts, (list, tuple)) and len(interrupts) > 0:
            try:
                interrupt_value = getattr(interrupts[0], "value", None)
                if isinstance(interrupt_value, dict):
                    prompt_value = interrupt_value.get("prompt", interrupt_value)
                    inbox_address = interrupt_value.get("inbox_address")
                    node_name = interrupt_value.get("node_name", "Checkpoint")
                    paused_node_id = interrupt_value.get("node_id")
                    interrupt_type = interrupt_value.get("type", "unknown")
                    interrupt_error = interrupt_value.get("error")

                    execution_logger.info(
                        f"[CHECKPOINT-DEBUG] Interrupt received: type={interrupt_type}, "
                        f"node_name={node_name}, node_id={paused_node_id}"
                    )
                    if interrupt_error:
                        execution_logger.warning(
                            f"[CHECKPOINT-DEBUG] Checkpoint error for '{node_name}': {interrupt_error}"
                        )
                else:
                    prompt_value = interrupt_value
            except Exception:
                prompt_value = None

        # Guardrail block interrupts are non-resumable — treat as failure
        if interrupt_type == "guardrail_block":
            return await self._handle_guardrail_block_interrupt(
                interrupts,
                execution_id,
                db_execution_id,
                graph,
            )

        # Get checkpoint ID using thread-local checkpointer
        checkpoint_tuple = None
        checkpoint_id = None
        try:
            thread_checkpointer = get_thread_checkpointer()
            checkpoint_tuple = await thread_checkpointer.aget_tuple(
                config={"configurable": {"thread_id": execution_id}}
            )
            if checkpoint_tuple and getattr(checkpoint_tuple, "checkpoint", None):
                checkpoint_id = checkpoint_tuple.checkpoint.get("id")
        except Exception as e:
            execution_logger.warning(f"Failed to get checkpoint tuple: {e}")

        # Determine paused node
        if not paused_node_id:
            paused_node_id = self.engine.active_executions.get(execution_id, {}).get(
                "current_node"
            )

        # Update database
        paused_db_node_id = None
        if db_execution_id:
            try:
                # Update graph execution to paused
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id, status="paused"
                )
                # Try to find running checkpoint or agent node to mark paused
                try:
                    node_execs = ExecutionHistoryService.get_node_executions(
                        db_execution_id
                    )
                    # Look for running CHECKPOINT or AGENT nodes (for agent review)
                    running_nodes = [
                        ne
                        for ne in node_execs
                        if ne.get("node_type") in ("CHECKPOINT", "AGENT")
                        and ne.get("status") == "running"
                    ]
                    # STATUS-MISMATCH-DEBUG: Log all nodes and their statuses
                    execution_logger.info(
                        f"[STATUS-DEBUG] _finalize_checkpoint_pause: Found {len(node_execs)} node executions, "
                        f"{len(running_nodes)} running AGENT/CHECKPOINT nodes"
                    )
                    for ne in node_execs:
                        execution_logger.info(
                            f"[STATUS-DEBUG]   - {ne.get('node_name')} (id={ne.get('id')}, "
                            f"node_id={ne.get('node_id')}, type={ne.get('node_type')}, "
                            f"status={ne.get('status')})"
                        )
                    if running_nodes:
                        paused_db_node_id = running_nodes[-1]["id"]
                        paused_node_name = running_nodes[-1].get("node_name", "Unknown")
                        execution_logger.info(
                            f"[STATUS-DEBUG] Marking node as PAUSED: {paused_node_name} "
                            f"(db_id={paused_db_node_id}, node_id={running_nodes[-1].get('node_id')})"
                        )
                        ExecutionHistoryService.complete_node_execution(
                            node_execution_id=paused_db_node_id,
                            status="paused",
                            output_data={"prompt": prompt_value},
                            node_metadata={
                                "prompt": prompt_value,
                                "checkpoint_id": checkpoint_id,
                            },
                        )
                        execution_logger.info(
                            f"[STATUS-DEBUG] Successfully marked {paused_node_name} as paused (db_id={paused_db_node_id})"
                        )
                except Exception as e2:
                    execution_logger.debug(
                        f"Could not update node status while pausing: {e2}"
                    )
            except Exception as e:
                execution_logger.warning(f"Failed to update DB to paused: {e}")

        # Update in-memory status
        try:
            self.engine.active_executions[execution_id]["status"] = "paused"
            self.engine.active_executions[execution_id]["paused"] = {
                "checkpoint_id": checkpoint_id,
                "node_id": paused_node_id,
                "node_name": node_name,
                "prompt": prompt_value,
            }
        except Exception:
            pass

        # Send WebSocket notification ONLY if we have a valid prompt
        # If prompt is None, the executor that called interrupt() has already sent
        # a notification with the correct data (e.g., agent review payload).
        # Sending another notification with null prompt would overwrite it.
        if ws_notifier and prompt_value is not None:
            try:
                payload = {
                    "checkpoint_id": checkpoint_id,
                    "thread_id": execution_id,
                    "node_id": paused_node_id,
                    "node_name": node_name,
                    "prompt": prompt_value,
                    "db_execution_id": db_execution_id,
                }
                if inbox_address:
                    payload["inbox_address"] = inbox_address
                await ws_notifier.on_execution_paused(execution_id, payload)
                execution_logger.info("Sent execution_paused notification")
            except Exception as e:
                execution_logger.error(f"Failed to send pause notification: {e}")
        elif ws_notifier and prompt_value is None:
            # Agent review case: review.py already sent the prompt payload,
            # but we need to send the checkpoint_id which wasn't available then
            execution_logger.info(
                f"Sending checkpoint_id update for agent review: {checkpoint_id}"
            )
            try:
                await ws_notifier.on_execution_paused(
                    execution_id,
                    {
                        "checkpoint_id": checkpoint_id,
                        "thread_id": execution_id,
                        "node_id": paused_node_id,
                        "node_name": node_name,
                        "review_type": "agent_review",
                    },
                )
            except Exception as e:
                execution_logger.error(f"Failed to send checkpoint_id update: {e}")

        return {
            "execution_id": db_execution_id,
            "graph_name": graph.name,
            "status": "paused",
            "checkpoint_id": checkpoint_id,
            "thread_id": execution_id,
            "paused_at_node": paused_node_id,
            "paused_node_name": node_name,
            "prompt": prompt_value,
        }

    async def _handle_guardrail_block_interrupt(
        self,
        interrupts: tuple | list,
        execution_id: str,
        db_execution_id: int | None,
        graph: "GraphData",
    ) -> dict[str, Any]:
        """Handle a guardrail_block interrupt by failing the execution.

        Guardrail block interrupts are non-resumable — the workflow must stop.
        This sets the execution status to 'failed' with the violation details.
        """
        # Extract violation details from the interrupt
        violations = []
        policy_name = None
        try:
            interrupt_value = (
                getattr(interrupts[0], "value", None) if interrupts else None
            )
            if isinstance(interrupt_value, dict):
                violations = interrupt_value.get("violations", [])
                policy_name = interrupt_value.get("policy_name")
        except Exception:
            pass

        # Build error message
        violation_messages = []
        for v in violations:
            msg = v.get("message", "") if isinstance(v, dict) else str(v)
            if msg:
                violation_messages.append(msg)
        error_message = (
            "Guardrail violation blocked execution"
            + (f" (policy: {policy_name})" if policy_name else "")
            + (f": {'; '.join(violation_messages)}" if violation_messages else "")
        )

        execution_logger.warning(
            f"[GUARDRAIL-BLOCK] Execution {execution_id} blocked by guardrail: {error_message}"
        )

        # Update database to failed
        if db_execution_id:
            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id,
                    status="failed",
                    error_message=error_message,
                    end_time=datetime.now(timezone.utc),
                )
            except Exception as db_error:
                execution_logger.error(
                    f"Failed to update DB on guardrail block: {db_error}"
                )

        # Update in-memory state
        if execution_id in self.engine.active_executions:
            self.engine.active_executions[execution_id]["status"] = "failed"
            self.engine.active_executions[execution_id]["error"] = error_message
            self.engine.active_executions[execution_id]["end_time"] = str(
                datetime.now(timezone.utc)
            )

        # Send WebSocket error notification
        if ws_notifier:
            try:
                await ws_notifier.on_execution_error(execution_id, error_message)
            except Exception as ws_error:
                execution_logger.error(
                    f"Failed to send guardrail block notification: {ws_error}"
                )

        # Clean up active execution
        self.engine.cleanup_execution(execution_id)

        return {
            "execution_id": db_execution_id,
            "graph_name": graph.name,
            "status": "failed",
            "error": error_message,
            "guardrail_block": True,
            "violations": violations,
        }

    async def _finalize_manual_pause(
        self,
        graph: "GraphData",
        execution_id: str,
        db_execution_id: int | None,
        control: dict[str, Any],
    ) -> dict[str, Any]:
        """Finalize a user-requested pause once the current node has completed."""
        if control.get("pause_finalized"):
            return {
                "execution_id": db_execution_id,
                "graph_name": graph.name,
                "status": "paused",
                "checkpoint_id": control.get("pause_checkpoint_id"),
                "thread_id": execution_id,
                "paused_at_node": control.get("pause_target_node"),
                "paused_node_name": control.get("pause_target_node_name"),
                "prompt": control.get("pause_prompt"),
            }

        checkpoint_id = None
        try:
            thread_checkpointer = get_thread_checkpointer()
            checkpoint_tuple = await thread_checkpointer.aget_tuple(
                config={"configurable": {"thread_id": execution_id}}
            )
            if checkpoint_tuple and getattr(checkpoint_tuple, "checkpoint", None):
                checkpoint_id = checkpoint_tuple.checkpoint.get("id")
        except Exception as exc:
            execution_logger.warning(
                f"Failed to retrieve checkpoint for manual pause {execution_id}: {exc}"
            )

        pause_prompt = "Workflow paused by user. Resume when ready."
        control["pause_checkpoint_id"] = checkpoint_id
        control["pause_prompt"] = pause_prompt
        control["pause_is_manual"] = True

        node_name = control.get("pause_target_node_name") or "User Pause"
        node_id = control.get("pause_target_node") or "__user_pause__"

        if db_execution_id:
            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id,
                    status="paused",
                )
            except Exception as exc:
                execution_logger.warning(
                    f"Failed to mark execution {db_execution_id} paused: {exc}"
                )
            else:
                execution_logger.info(
                    "[PAUSE-CONTROL] Marked execution %s paused in history",
                    db_execution_id,
                )

            if control.get("pause_node_execution_id") is None:
                try:
                    existing = ExecutionHistoryService.get_node_executions(
                        db_execution_id
                    )
                    next_order = 1
                    if existing:
                        next_order = (
                            max((item.get("execution_order") or 0) for item in existing)
                            + 1
                        )

                    pause_node = ExecutionHistoryService.create_node_execution(
                        graph_execution_id=db_execution_id,
                        node_id=node_id,
                        node_name=node_name,
                        node_type="CHECKPOINT",
                        execution_order=next_order,
                        input_data={"reason": "user_pause"},
                        node_metadata={
                            "manual_pause": True,
                            "checkpoint_id": checkpoint_id,
                            "requested_at": control.get("pause_request_time"),
                        },
                    )
                    pause_node_id = pause_node.get("id") if pause_node else None
                    if pause_node_id:
                        try:
                            ExecutionHistoryService.start_node_execution(pause_node_id)
                        except Exception:
                            pass
                        ExecutionHistoryService.complete_node_execution(
                            node_execution_id=pause_node_id,
                            status="paused",
                            output_data={"message": pause_prompt},
                        )
                        control["pause_node_execution_id"] = pause_node_id
                        execution_logger.info(
                            "[PAUSE-CONTROL] Recorded manual pause node %s for execution %s",
                            pause_node_id,
                            execution_id,
                        )
                except Exception as exc:
                    execution_logger.warning(
                        f"Failed to record manual pause node for execution {execution_id}: {exc}"
                    )

        # Update in-memory state
        if execution_id in self.engine.active_executions:
            self.engine.active_executions[execution_id]["status"] = "paused"
            self.engine.active_executions[execution_id]["paused"] = {
                "checkpoint_id": checkpoint_id,
                "node_id": node_id,
                "node_name": node_name,
                "prompt": pause_prompt,
                "manual": True,
            }

        control["pause_requested"] = False
        control["pause_ready"] = False
        control["pause_finalized"] = True
        control["pause_trigger_pending"] = False

        if ws_notifier:
            try:
                await ws_notifier.on_execution_paused(
                    execution_id,
                    {
                        "checkpoint_id": checkpoint_id,
                        "thread_id": execution_id,
                        "node_id": node_id,
                        "node_name": node_name,
                        "prompt": pause_prompt,
                        "db_execution_id": db_execution_id,
                        "manual": True,
                    },
                )
            except Exception as exc:
                execution_logger.error(
                    f"Failed to send manual pause notification for {execution_id}: {exc}"
                )

        execution_logger.info(
            "[PAUSE-CONTROL] Manual pause finalized for execution %s (checkpoint=%s, node=%s)",
            execution_id,
            checkpoint_id,
            node_id,
        )

        return {
            "execution_id": db_execution_id,
            "graph_name": graph.name,
            "status": "paused",
            "checkpoint_id": checkpoint_id,
            "thread_id": execution_id,
            "paused_at_node": node_id,
            "paused_node_name": node_name,
            "prompt": pause_prompt,
        }

    async def _handle_execution_error(
        self,
        execution_id: str,
        db_execution_id: int | None,
        error: Exception,
    ):
        """Handle execution error and update tracking."""
        # Update in-memory state
        if execution_id in self.engine.active_executions:
            self.engine.active_executions[execution_id]["status"] = "failed"
            self.engine.active_executions[execution_id]["error"] = str(error)
            self.engine.active_executions[execution_id]["end_time"] = str(
                datetime.now(timezone.utc)
            )

        # Update database
        if db_execution_id:
            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id,
                    status="failed",
                    error_message=str(error),
                    end_time=datetime.now(timezone.utc),
                )
            except Exception as db_error:
                execution_logger.error(f"Failed to update DB on error: {db_error}")

        # Send WebSocket notification
        if ws_notifier:
            try:
                await ws_notifier.on_execution_error(execution_id, str(error))
            except Exception as ws_error:
                execution_logger.error(f"Failed to send error notification: {ws_error}")

        # Clean up active execution entry to prevent memory leaks
        self.engine.cleanup_execution(execution_id)

    async def _handle_hard_stop(
        self,
        graph: "GraphData",
        execution_id: str,
        db_execution_id: Optional[int],
    ) -> None:
        """Handle cleanup after a hard stop (task cancellation).

        This is called when the execution task is cancelled via task.cancel(),
        which happens during a hard stop request. It updates the database and
        in-memory state, and stores partial state for debugging.

        Args:
            graph: The workflow graph definition
            execution_id: The execution thread ID
            db_execution_id: The database execution ID (if any)
        """
        timestamp = datetime.now(timezone.utc)

        # Update in-memory state
        active = self.engine.active_executions.get(execution_id)
        if active:
            active["status"] = "stopped"
            active["end_time"] = str(timestamp)
            control = active.setdefault("control", {})
            control["force_stop_finalized"] = True
            control["force_stop"] = False
            control["force_stop_requested"] = False

        # Update database
        if db_execution_id:
            # Get partial state snapshot for storage
            partial_state = None
            if active:
                partial_state = active.get("partial_state_snapshot")

            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id,
                    status="stopped",
                    end_time=timestamp,
                    error="Execution hard stopped by user",
                    output_data={"partial_state_snapshot": partial_state}
                    if partial_state
                    else None,
                )
                execution_logger.info(
                    f"[HARD-STOP] Updated database execution {db_execution_id} to stopped"
                )
            except Exception as exc:
                execution_logger.warning(
                    f"[HARD-STOP] Failed to update execution {db_execution_id} in DB: {exc}"
                )

            # Mark all running nodes as stopped
            try:
                running_nodes = ExecutionHistoryService.get_all_running_nodes(
                    db_execution_id
                )
                for node in running_nodes:
                    node_id = node.get("id")
                    if not node_id:
                        continue
                    try:
                        ExecutionHistoryService.complete_node_execution(
                            node_execution_id=node_id,
                            status="stopped",
                            error_message="Execution hard stopped by user",
                        )
                    except Exception as node_exc:
                        execution_logger.debug(
                            f"[HARD-STOP] Failed to mark node {node_id} stopped: {node_exc}"
                        )
            except Exception as exc:
                execution_logger.warning(
                    f"[HARD-STOP] Failed to enumerate running nodes for {db_execution_id}: {exc}"
                )

        # Send WebSocket notification
        if ws_notifier:
            try:
                await ws_notifier.on_execution_stopped(
                    execution_id,
                    {
                        "graph_name": graph.name,
                        "db_execution_id": db_execution_id,
                        "timestamp": timestamp.isoformat(),
                        "hard_stopped": True,
                    },
                )
                execution_logger.info(
                    f"[HARD-STOP] Sent WebSocket notification for {execution_id}"
                )
            except Exception as exc:
                execution_logger.error(
                    f"[HARD-STOP] Failed to send stopped notification for {execution_id}: {exc}"
                )

    async def _finalize_force_stop(
        self,
        graph: "GraphData",
        execution_id: str,
        db_execution_id: int | None,
        control_result: dict[str, Any],
    ):
        """Finalize execution bookkeeping for a force stop."""
        timestamp = datetime.now(timezone.utc)

        active = self.engine.active_executions.get(execution_id)
        if active:
            active["status"] = "stopped"
            active["end_time"] = str(timestamp)
            active.setdefault("control", {}).setdefault("force_stop_finalized", True)
            active["control"]["force_stop"] = False
            active["control"]["force_stop_requested"] = False

        if db_execution_id:
            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id,
                    status="stopped",
                    end_time=timestamp,
                )
            except Exception as exc:
                execution_logger.warning(
                    f"Failed to mark execution {db_execution_id} stopped: {exc}"
                )

            try:
                running_nodes = ExecutionHistoryService.get_all_running_nodes(
                    db_execution_id
                )
                for node in running_nodes:
                    node_id = node.get("id")
                    if not node_id:
                        continue
                    try:
                        ExecutionHistoryService.complete_node_execution(
                            node_execution_id=node_id,
                            status="stopped",
                            error_message="Execution stopped by user",
                        )
                    except Exception as node_exc:
                        execution_logger.debug(
                            f"Failed to mark node {node_id} stopped: {node_exc}"
                        )
            except Exception as exc:
                execution_logger.warning(
                    f"Failed to enumerate running nodes for {db_execution_id}: {exc}"
                )

        if ws_notifier:
            try:
                await ws_notifier.on_execution_stopped(
                    execution_id,
                    {
                        "graph_name": graph.name,
                        "db_execution_id": db_execution_id,
                        "timestamp": timestamp.isoformat(),
                    },
                )
            except Exception as exc:
                execution_logger.error(
                    f"Failed to send stopped notification for {execution_id}: {exc}"
                )

        # Clean up active execution entry to prevent memory leaks
        self.engine.cleanup_execution(execution_id)

    async def _finalize_execution(
        self,
        graph: "GraphData",
        final_state: dict[str, Any] | None,
        execution_id: str,
        db_execution_id: int | None,
    ) -> dict[str, Any]:
        """Finalize execution and process END node."""
        # Track END node execution — if a guardrail enforcement blocks the
        # END output, route through the failure pathway instead of completing.
        try:
            await self._process_end_node(graph, final_state, execution_id, db_execution_id)
        except Exception as end_err:
            if "GuardrailViolationError" in type(end_err).__name__:
                error_message = f"Workflow output blocked by guardrail: {end_err}"
                execution_logger.warning(
                    f"[GUARDRAIL-BLOCK] Execution {execution_id} failed at END node: {error_message}"
                )
                await self._handle_execution_error(execution_id, db_execution_id, end_err)
                return {
                    "execution_id": db_execution_id,
                    "graph_name": graph.name,
                    "status": "failed",
                    "error": error_message,
                    "guardrail_block": True,
                }
            raise

        # Update in-memory state
        if execution_id in self.engine.active_executions:
            self.engine.active_executions[execution_id]["status"] = "completed"
            self.engine.active_executions[execution_id]["end_time"] = str(
                datetime.now(timezone.utc)
            )

        # Build final result
        final_result = {
            "execution_id": db_execution_id,
            "graph_name": graph.name,
            "status": "completed",
            "results": final_state.get("results", []) if final_state else [],
            "node_outputs": final_state.get("node_outputs", {}) if final_state else {},
            "final_output": FinalOutputExtractor.extract(final_state)
            if final_state
            else None,
        }

        # Update database
        if db_execution_id:
            try:
                ExecutionHistoryService.update_graph_execution(
                    execution_id=db_execution_id,
                    status="completed",
                    output_data=final_result,
                    end_time=datetime.now(timezone.utc),
                )
                ExecutionHistoryService.update_execution_summary(
                    graph.name, db_execution_id
                )
            except Exception as e:
                execution_logger.error(f"Failed to update DB on completion: {e}")

        # Send completion notification
        if ws_notifier:
            try:
                await ws_notifier.on_execution_complete(execution_id, final_result)
            except Exception as e:
                execution_logger.error(f"Failed to send completion notification: {e}")

        execution_logger.info(f"Execution completed: {execution_id}")

        # Clean up active execution entry to prevent memory leaks
        self.engine.cleanup_execution(execution_id)

        return final_result

    async def _process_end_node(
        self,
        graph: "GraphData",
        final_state: dict[str, Any] | None,
        execution_id: str,
        db_execution_id: int | None,
    ):
        """Process END node execution tracking."""
        # Get all END nodes, then filter out subworkflow internal ones
        all_end_nodes = [n for n in graph.nodes if n.type == NodeType.END]
        if not all_end_nodes:
            return

        # Filter out END nodes that are internal to subworkflows
        subworkflow_internal_ids = _get_subworkflow_internal_node_ids(graph)
        end_nodes = [
            n for n in all_end_nodes if n.uniq_id not in subworkflow_internal_ids
        ]

        if not end_nodes:
            execution_logger.warning(
                "All END nodes are subworkflow-internal, no main END node to process"
            )
            return

        if len(end_nodes) < len(all_end_nodes):
            execution_logger.info(
                f"Filtered {len(all_end_nodes) - len(end_nodes)} subworkflow-internal END nodes. "
                f"Processing main END node: {end_nodes[0].name}"
            )

        end_node = end_nodes[0]
        try:
            node_exec = None
            if db_execution_id:
                # Create END node execution
                node_exec = ExecutionHistoryService.create_node_execution(
                    graph_execution_id=db_execution_id,
                    node_id=end_node.uniq_id,
                    node_name=end_node.name,
                    node_type="END",
                    execution_order=final_state.get("execution_order", 1)
                    if final_state
                    else 1,
                    input_data={},
                )
                ExecutionHistoryService.start_node_execution(node_exec["id"])

                # Process END output
                end_output_data = OutputProcessor.process(
                    final_state if final_state else {}, end_node, graph
                )

                # Apply workflow egress guardrails to END output
                wf_pipeline_dicts = (
                    final_state.get("workflow_guardrails_pipeline")
                    if final_state
                    else None
                )
                if wf_pipeline_dicts and end_output_data:
                    try:
                        from backend.models.workflow.configs.guardrails import (
                            GuardrailsConfig,
                        )
                        from backend.services.guardrails import get_guardrails_engine
                        from backend.services.guardrails.exceptions import (
                            GuardrailViolationError,
                        )
                        from backend.services.guardrails.violation_persistence import (
                            ViolationPersistenceService,
                        )
                        from backend.services.streaming.event_emitter import (
                            StreamingEventEmitter,
                        )

                        wf_pipeline = [GuardrailsConfig.from_dict(d) for d in wf_pipeline_dicts]
                        if wf_pipeline:
                            engine = get_guardrails_engine()
                            _gs = (
                                dict(final_state.get("guardrails_state") or {})
                                if final_state
                                else {}
                            )

                            end_text = (
                                end_output_data.get("raw", "")
                                if isinstance(end_output_data, dict)
                                else str(end_output_data)
                            )

                            if end_text:
                                output_result = await engine.check_output(
                                    end_text,
                                    wf_pipeline,
                                    guardrails_state=_gs,
                                )

                                if output_result.violations:
                                    for v in output_result.violations:
                                        violation_db_id = ViolationPersistenceService.persist_violation(
                                            v,
                                            category="workflow_egress",
                                            action_taken=output_result.action_taken
                                            or "blocked",
                                            policy_id=v.policy_id or None,
                                            policy_name=v.policy_name or None,
                                            workflow_id=graph.workflow_id,
                                            graph_execution_id=str(db_execution_id)
                                            if db_execution_id
                                            else None,
                                        )
                                        StreamingEventEmitter.emit_guardrail_violation(
                                            category="workflow_egress",
                                            rule_name=v.rule_name or "unknown",
                                            message=v.message
                                            or "Workflow output violation",
                                            severity=v.severity or "block",
                                            execution_id=execution_id,
                                            violation_db_id=violation_db_id,
                                            policy_name=v.policy_name or None,
                                            details=v.details,
                                            enforcement_mode=v.enforcement_mode or None,
                                        )

                                if not output_result.passed:
                                    violation_msg = (
                                        output_result.violations[0].message
                                        if output_result.violations
                                        else "Output blocked"
                                    )
                                    end_output_data = {
                                        "raw": f"[Output blocked by workflow guardrail policy: {violation_msg}]",
                                        "structured": None,
                                        "fields": {},
                                    }
                                elif output_result.sanitized_content is not None:
                                    execution_logger.info(
                                        "[WORKFLOW-GUARDRAILS] END output sanitized by workflow guardrails"
                                    )
                                    if isinstance(end_output_data, dict):
                                        end_output_data["raw"] = (
                                            output_result.sanitized_content
                                        )
                                    else:
                                        end_output_data = (
                                            output_result.sanitized_content
                                        )
                    except GuardrailViolationError as gve:
                        execution_logger.warning(
                            f"[GUARDRAIL-BLOCK] END output blocked by guardrail: {gve}"
                        )
                        # Persist violations from the exception and emit events
                        for v in gve.violations:
                            violation_db_id = ViolationPersistenceService.persist_violation(
                                v,
                                category="workflow_egress",
                                action_taken="blocked",
                                policy_id=v.policy_id or None,
                                policy_name=v.policy_name or None,
                                workflow_id=graph.workflow_id,
                                graph_execution_id=str(db_execution_id)
                                if db_execution_id
                                else None,
                            )
                            StreamingEventEmitter.emit_guardrail_violation(
                                category="workflow_egress",
                                rule_name=v.rule_name or "unknown",
                                message=v.message or "Workflow output violation",
                                severity=v.severity or "block",
                                execution_id=execution_id,
                                violation_db_id=violation_db_id,
                                policy_name=v.policy_name or None,
                                details=v.details,
                                enforcement_mode=v.enforcement_mode or None,
                            )
                        # Set blocked output and complete END node as failed
                        violation_msg = (
                            gve.violations[0].message
                            if gve.violations
                            else str(gve)
                        )
                        end_output_data = {
                            "raw": f"[Output blocked by workflow guardrail policy: {violation_msg}]",
                            "structured": None,
                            "fields": {},
                        }
                        ExecutionHistoryService.complete_node_execution(
                            node_execution_id=node_exec["id"],
                            status="failed",
                            output_data=end_output_data,
                            error_message=str(gve),
                        )
                        # Propagate to fail the execution
                        raise
                    except Exception as e:
                        execution_logger.warning(
                            f"Workflow END egress guardrail check failed: {e}"
                        )

                ExecutionHistoryService.complete_node_execution(
                    node_execution_id=node_exec["id"],
                    status="completed",
                    output_data=end_output_data,
                )

                # Send WebSocket notifications for END
                if ws_notifier:
                    await ws_notifier.on_node_start(
                        execution_id,
                        end_node.uniq_id,
                        end_node.name,
                        "END",
                        None,
                        None,
                        node_exec["id"],
                    )
                    await ws_notifier.on_node_complete(
                        execution_id,
                        end_node.uniq_id,
                        end_node.name,
                        end_output_data,
                        "END",
                        0.0,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        None,
                        node_exec["id"],
                    )
        except Exception as e:
            if "GuardrailViolationError" in type(e).__name__:
                raise
            execution_logger.debug(f"Failed END node processing: {e}")
