"""
Slim Execution Engine Coordinator.

This module provides a lightweight execution engine that coordinates
between specialized service modules rather than containing complex logic itself.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict

from backend.models.workflow import GraphData, NodeType
from backend.services.conditions import ConditionEvaluator, ConditionFunctionFactory
from backend.services.config import get_logger
from backend.services.execution.checkpoint import (
    EmailCheckpointExecutor,
    ManualCheckpointExecutor,
)
from backend.services.execution.history import ExecutionHistoryService
from backend.services.execution.nodes import NodeFunctionFactory
from backend.services.execution.resume_handler import ResumeHandler
from backend.services.execution.workflow_executor import WorkflowExecutor
from backend.services.graph import GraphBuilder, GraphCache, GraphManager
from backend.services.graph.tools import ToolNodeFactory
from backend.services.io import (
    FieldExtractor,
    MappingValueExtractor,
    StateProcessor,
    TemplateProcessor,
)
from backend.services.io.input import InputBuilder
from backend.services.nodes.executors import (
    AgentNodeExecutor,
    CodeNodeExecutor,
    ConditionNodeExecutor,
    DatabaseNodeExecutor,
    DatabaseQueryActionNodeExecutor,
    DocumentLoadNodeExecutor,
    EmailNodeExecutor,
    FileNodeExecutor,
    ForEachNodeExecutor,
    HttpNodeExecutor,
)
from backend.services.nodes.registry import NodeExecutorRegistry
from backend.services.subgraph import SubgraphBuilder, SubgraphExecutor
from backend.services.websocket import notifier as ws_notifier
from backend.services.workflow.resumption import SubworkflowResumeHandler


engine_logger = get_logger("execution.engine")

# Global executor instance
_global_executor = None


def initialize_executor(graph_manager: GraphManager):
    """Initialize the global execution engine."""
    global _global_executor
    _global_executor = ExecutionEngine(graph_manager)
    engine_logger.info("Execution engine initialized")
    return _global_executor


def get_executor():
    """Get the global execution engine."""
    if _global_executor is None:
        raise RuntimeError(
            "Executor not initialized. Call initialize_executor() first."
        )
    return _global_executor


class ExecutionEngine:
    """
    Slim execution engine coordinator.

    This engine delegates to specialized services rather than
    containing complex logic. It serves as the main orchestrator
    and dependency provider.

    Responsibilities:
    - Initialize all service components
    - Provide public API surface
    - Coordinate between services
    - Manage execution state
    """

    def __init__(self, graph_manager: GraphManager):
        """
        Initialize execution engine.

        Args:
            graph_manager: Graph manager for workflow definitions
        """
        self.graph_manager = graph_manager
        self.active_executions = {}
        self.execution_history = []
        self.adapter = None  # Optional adapter for real-time updates

        # Initialize checkpointer manager for thread-local checkpointers
        # Each execution thread gets its own checkpointer to avoid asyncio event loop conflicts
        from backend.services.execution.checkpointer_manager import (
            get_checkpointer_manager,
        )

        self.checkpointer_manager = get_checkpointer_manager()

        # Initialize subgraph support
        self.subgraph_builder = SubgraphBuilder(graph_manager)
        self.subgraph_executor = SubgraphExecutor(self.subgraph_builder)
        engine_logger.info("Subgraph support initialized")

        # Initialize subworkflow resumption
        self.subworkflow_resume_handler = SubworkflowResumeHandler(self, graph_manager)
        engine_logger.info("Subworkflow resumption support initialized")

        # Initialize condition evaluation services
        self.condition_evaluator = ConditionEvaluator(graph_manager)
        self.condition_function_factory = ConditionFunctionFactory(
            self.condition_evaluator
        )
        engine_logger.info("Condition evaluation services initialized")

        # Initialize I/O processing services
        self.state_processor = StateProcessor(self.active_executions)
        self.template_processor = TemplateProcessor()
        self.field_extractor = FieldExtractor()
        self.mapping_extractor = MappingValueExtractor()
        self.input_builder = InputBuilder(self.field_extractor)
        engine_logger.info("I/O processing services initialized")

        # Initialize checkpoint executors
        self.checkpoint_executors = {
            "manual": ManualCheckpointExecutor(self.active_executions),
            "email": EmailCheckpointExecutor(
                self.active_executions, self.field_extractor
            ),
        }
        engine_logger.info("Checkpoint executors initialized")

        # Initialize node function factory
        self.node_function_factory = NodeFunctionFactory(
            self.checkpoint_executors, self.adapter
        )
        engine_logger.info("Node function factory initialized")

        # Initialize graph building services
        self.graph_cache = GraphCache()
        self.graph_builder = GraphBuilder(
            node_function_creator=self.node_function_factory.create_node_function,
            tool_node_creator=ToolNodeFactory.create_tool_node,
            should_use_native_tools_fn=ToolNodeFactory.should_use_native_tool_nodes,
            condition_function_factory=self.condition_function_factory,
            llm_factory=self.graph_manager.llm_factory,
            model_service=self.graph_manager.model_service,
        )
        engine_logger.info("Graph building services initialized")

        # Initialize execution orchestrators
        self.resume_handler = ResumeHandler(self)
        self.workflow_executor = WorkflowExecutor(self)
        engine_logger.info(
            "Execution orchestrators initialized (ResumeHandler, WorkflowExecutor)"
        )

        # Register node executors
        self._register_node_executors()
        engine_logger.info("Node executors registered")

    def _register_node_executors(self):
        """Register node executors in the registry."""
        dependencies = {
            "execution_history_service": ExecutionHistoryService,
            "ws_notifier": ws_notifier,
            "subgraph_executor": self.subgraph_executor,
            "graph_manager": self.graph_manager,
        }

        NodeExecutorRegistry.register(
            NodeType.AGENT,
            factory=lambda: AgentNodeExecutor(**dependencies),
        )

        # Database executor needs additional IO services
        database_dependencies = {
            **dependencies,
            "mapping_extractor": self.mapping_extractor,
            "input_builder": self.input_builder,
        }
        NodeExecutorRegistry.register(
            NodeType.DATABASE_INSERT,
            factory=lambda: DatabaseNodeExecutor(**database_dependencies),
        )
        NodeExecutorRegistry.register(
            NodeType.DATABASE_QUERY_ACTION,
            factory=lambda: DatabaseQueryActionNodeExecutor(**{
                **dependencies,
                "input_builder": self.input_builder,
            }),
        )
        NodeExecutorRegistry.register(
            NodeType.CONDITION,
            factory=lambda: ConditionNodeExecutor(**dependencies),
        )
        NodeExecutorRegistry.register(
            NodeType.HTTP_REQUEST_ACTION,
            factory=lambda: HttpNodeExecutor(**dependencies),
        )
        NodeExecutorRegistry.register(
            NodeType.FILE_READ,
            factory=lambda: FileNodeExecutor(**dependencies),
        )
        NodeExecutorRegistry.register(
            NodeType.EMAIL_SEND,
            factory=lambda: EmailNodeExecutor(**dependencies),
        )
        NodeExecutorRegistry.register(
            NodeType.FOR_EACH,
            factory=lambda: ForEachNodeExecutor(**dependencies),
        )
        NodeExecutorRegistry.register(
            NodeType.DOCUMENT_LOAD,
            factory=lambda: DocumentLoadNodeExecutor(**dependencies),
        )
        # CODE_EXECUTOR: Runs Python/JavaScript code in workflows
        # Input: receives previous node output as `input` variable
        # Output: captures `result` variable and passes to next node
        NodeExecutorRegistry.register(
            NodeType.CODE_EXECUTOR,
            factory=lambda: CodeNodeExecutor(**dependencies),
        )

        engine_logger.info(
            "Registered executors: AGENT, DATABASE_INSERT, CONDITION, "
            "HTTP_REQUEST_ACTION, FILE_READ, EMAIL_SEND, FOR_EACH, DOCUMENT_LOAD, CODE_EXECUTOR"
        )

    # Public API Methods

    async def execute_graph(
        self,
        graph: GraphData,
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
        Execute a workflow graph.

        Args:
            graph: The workflow graph definition
            initial_input: Initial input data
            execution_id: Unique execution identifier
            user_id: User executing the graph
            workflow_id: Workflow UUID
            graph_definition_id: Graph definition UUID
            user_access_token: User's JWT access token for MCP servers with oauth2 auth
            evaluation_run_id: Associated evaluation run UUID
            trigger_type: Execution trigger type (editor, api, evaluation, scheduler, chat)
            phoenix_project_name: Override Phoenix project name for trace routing
            chat_session_id: Optional chat session ID for chat-triggered executions

        Returns:
            Execution result with status, outputs, and metadata
        """
        return await self.workflow_executor.execute(
            graph=graph,
            initial_input=initial_input,
            execution_id=execution_id,
            user_id=user_id,
            workflow_id=workflow_id,
            graph_definition_id=graph_definition_id,
            user_access_token=user_access_token,
            evaluation_run_id=evaluation_run_id,
            trigger_type=trigger_type,
            phoenix_project_name=phoenix_project_name,
            chat_session_id=chat_session_id,
        )

    async def resume_from_checkpoint(
        self,
        graph_name: str,
        thread_id: str,
        checkpoint_id: str,
        new_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Resume execution from a checkpoint.

        Args:
            graph_name: Name of the graph to resume
            thread_id: Thread ID for the execution
            checkpoint_id: ID of the checkpoint to resume from
            new_input: Optional new input to provide when resuming

        Returns:
            Execution result with status, outputs, and metadata
        """
        return await self.resume_handler.resume(
            graph_name=graph_name,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            new_input=new_input,
        )

    def request_stop(
        self, execution_id: str, reason: str | None = None
    ) -> dict[str, Any]:
        """Request an immediate stop of an active execution."""
        active = self.active_executions.get(execution_id)
        if not active:
            raise ValueError(f"Execution not found: {execution_id}")

        control = active.setdefault("control", {})
        control.setdefault("pause_trigger_pending", False)
        control.setdefault("pause_target_node_name", None)
        if control.get("force_stop_finalized"):
            return {"status": "stopped", "execution_id": execution_id}

        # Capture partial state BEFORE cancellation for debugging
        active["partial_state_snapshot"] = self._capture_partial_state(execution_id)

        # Set control flags
        control["force_stop"] = True
        control["force_stop_requested"] = True
        control["force_stop_reason"] = reason or "User requested hard stop"

        active["status"] = "stopping"

        # Cancel the execution task directly for immediate termination
        execution_task = active.get("execution_task")
        if execution_task and not execution_task.done():
            execution_task.cancel()
            engine_logger.info(
                f"[HARD-STOP] Cancelled execution task for {execution_id}"
            )
        else:
            # Fallback: try to close the stream generator if task not available
            loop = active.get("event_loop")
            if loop is not None:
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self.workflow_executor.trigger_force_stop(execution_id),
                        loop,
                    )
                    future.add_done_callback(
                        lambda f: (
                            engine_logger.warning(
                                f"[HARD-STOP] Fallback stop failed for {execution_id}: {f.exception()}"
                            )
                            if f.exception()
                            else None
                        )
                    )
                except Exception as exc:
                    engine_logger.warning(
                        f"[HARD-STOP] Failed to trigger fallback stop for {execution_id}: {exc}"
                    )

        return {"status": "stop_requested", "execution_id": execution_id}

    def _capture_partial_state(self, execution_id: str) -> Dict[str, Any]:
        """Capture partial state for debugging before hard stop.

        Args:
            execution_id: The execution ID to capture state for

        Returns:
            Dictionary containing captured partial state
        """
        active = self.active_executions.get(execution_id, {})
        snapshot = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "execution_id": execution_id,
            "current_node": active.get("current_node"),
            "current_node_name": active.get("current_node_name"),
            "status": active.get("status"),
            "node_execution_map": dict(active.get("node_execution_map", {})),
            "control_state": {
                k: v
                for k, v in active.get("control", {}).items()
                if not k.startswith("_")
            },
        }

        # Try to capture checkpoint state if available
        try:
            checkpoint_tuple = self.checkpointer.get_tuple(
                config={"configurable": {"thread_id": execution_id}}
            )
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
                snapshot["checkpoint"] = {
                    "id": checkpoint_tuple.checkpoint.get("id"),
                    "node_outputs_keys": list(
                        channel_values.get("node_outputs", {}).keys()
                    ),
                    "results_count": len(channel_values.get("results", [])),
                    "messages_count": len(channel_values.get("messages", [])),
                }
        except Exception as e:
            engine_logger.warning(
                f"[HARD-STOP] Failed to capture checkpoint state: {e}"
            )
            snapshot["checkpoint_error"] = str(e)

        return snapshot

    def request_pause(self, execution_id: str) -> dict[str, Any]:
        """Request a graceful pause once the current node completes."""
        active = self.active_executions.get(execution_id)
        if not active:
            raise ValueError(f"Execution not found: {execution_id}")

        control = active.setdefault("control", {})
        if control.get("pause_finalized"):
            return {"status": "paused", "execution_id": execution_id}

        control["pause_requested"] = True
        control["pause_request_time"] = datetime.now(timezone.utc).isoformat()
        control["pause_target_node"] = active.get("current_node")
        control["pause_target_node_name"] = (
            active.get("current_node_name") or "User Pause"
        )
        control["pause_ready"] = control["pause_target_node"] is None
        control["pause_is_manual"] = True

        target_node = control.get("pause_target_node")
        engine_logger.info(
            "[PAUSE-CONTROL] Pause requested for execution %s (target_node=%s, target_name=%s, ready=%s)",
            execution_id,
            target_node,
            control.get("pause_target_node_name"),
            control.get("pause_ready"),
        )

        active["status"] = "pause_pending"

        generator = active.get("stream_generator")
        loop = active.get("event_loop")

        if control["pause_ready"]:
            if generator is not None and loop is not None:
                future = asyncio.run_coroutine_threadsafe(
                    self.workflow_executor.trigger_pause(execution_id), loop
                )
                future.add_done_callback(
                    lambda f: (
                        engine_logger.warning(
                            f"[PAUSE] trigger_pause failed for {execution_id}: {f.exception()}"
                        )
                        if f.exception()
                        else None
                    )
                )
            else:
                control["pause_trigger_pending"] = True

        return {"status": "pause_pending", "execution_id": execution_id}

    def _build_state_graph(
        self, graph: GraphData, execution_id: str, db_execution_id: int | None
    ):
        """
        Build a LangGraph StateGraph from workflow definition.

        Args:
            graph: The workflow graph definition
            execution_id: Execution identifier
            db_execution_id: Database execution ID

        Returns:
            Configured StateGraph ready for compilation
        """
        return self.graph_builder.build(graph, execution_id, db_execution_id)

    def get_execution_status(self, execution_id: str) -> dict[str, Any] | None:
        """Get the current status of an execution."""
        return self.active_executions.get(execution_id)

    def cleanup_execution(self, execution_id: str) -> None:
        """Remove an execution from the active_executions tracking dictionary.

        Should be called after an execution completes, fails, or is stopped.
        The execution record is preserved in execution_history so the status
        endpoint can still return it after cleanup.

        Args:
            execution_id: The execution ID to clean up
        """
        if execution_id in self.active_executions:
            engine_logger.debug(f"Cleaning up active execution: {execution_id}")
            self.execution_history.append(self.active_executions[execution_id])
            del self.active_executions[execution_id]

    def get_execution_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get execution history."""
        return self.execution_history[-limit:]

    def get_checkpoints(self, thread_id: str) -> list[dict[str, Any]]:
        """List checkpoints for a given thread_id."""
        items: list[dict[str, Any]] = []
        try:
            # Get thread-local checkpointer for listing checkpoints
            from backend.services.execution.checkpointer_manager import (
                get_thread_checkpointer,
            )

            checkpointer = get_thread_checkpointer()
            for tup in checkpointer.list(
                config={"configurable": {"thread_id": thread_id}}
            ):
                try:
                    ck = tup.checkpoint or {}
                    items.append(
                        {
                            "checkpoint_id": ck.get("id"),
                            "thread_id": thread_id,
                            "timestamp": ck.get("ts"),
                            "metadata": tup.metadata
                            if hasattr(tup, "metadata")
                            else None,
                        }
                    )
                except Exception:
                    continue
        except Exception as e:
            engine_logger.error(f"Failed to list checkpoints: {e}")
        return items

    # Utility methods for backward compatibility with old code
    # These delegate to the appropriate service components

    def _build_node_input(self, node, state, graph):
        """Build input for a node based on configuration - delegates to input_builder."""
        return self.input_builder.build(node, state, graph)

    def _extract_value_for_mapping(
        self,
        source_mode,
        static_value,
        default_value,
        source_node_id,
        source_field_path,
        state,
        idx,
        sql_expressions,
    ):
        """Extract value for parameter/field mapping - delegates to field_extractor."""
        return self.field_extractor.extract_for_mapping(
            source_mode=source_mode,
            static_value=static_value,
            default_value=default_value,
            source_node_id=source_node_id,
            source_field_path=source_field_path,
            state=state,
            idx=idx,
            sql_expressions=sql_expressions,
        )

    def _replace_template_variables(self, template, state):
        """Replace template variables with values from state - delegates to template_processor."""
        return self.template_processor.replace_variables(template, state)

    def _get_previous_node_output(self, node, state, graph):
        """Get output from previous node - delegates to field_extractor."""
        return self.field_extractor.get_previous_node_output(node, state, graph)

    def _extract_field_from_output(self, output, field_path, default=""):
        """Extract field from node output using path - delegates to field_extractor."""
        return self.field_extractor.extract_field_from_output(
            output, field_path, default
        )

    def _extract_field_from_state(self, state, field_path, default=""):
        """Extract field from state using path - delegates to field_extractor."""
        return self.field_extractor.extract_field_from_state(state, field_path, default)
