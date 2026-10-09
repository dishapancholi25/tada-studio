"""Subgraph executor for delegation with full tracking and state management.

This executor uses LangGraph subgraphs for proper execution tracking,
state management, and tool resolution.
"""

import time
from typing import Any, Dict

from langgraph.errors import GraphInterrupt

from backend.services.config import get_logger
from backend.services.delegation.config import generate_task_id
from backend.services.delegation.models import DelegationRequest, DelegationResult
from backend.services.delegation.utils import run_async_in_sync_isolated
from backend.services.execution.subagent import SubagentIterationManager
from backend.services.streaming import streaming_emitter

logger = get_logger("delegation.subgraph_executor")


class SubgraphDelegationExecutor:
    """Executor for delegation using LangGraph subgraphs.

    This executor provides full execution tracking, state management,
    and tool resolution through LangGraph subgraphs.
    """

    def __init__(self, graph_manager):
        """Initialize the subgraph executor.

        Args:
            graph_manager: GraphManager instance for executing agents
        """
        self.graph_manager = graph_manager

    def execute(self, request: DelegationRequest) -> DelegationResult:
        """Execute delegation using subgraph approach.

        Args:
            request: The delegation request

        Returns:
            Delegation result
        """
        logger.info(f"Executing sub-agent {request.agent_node.name} using subgraph")

        # Track execution time
        start_time = time.time()

        # Get parent agent name and context info
        context = request.context or {}
        parent_agent_name = context.get("parent_node_name", "Orchestrator")
        db_exec_id = context.get("db_execution_id")

        # Get current iteration for this subagent
        current_iteration = 1
        if db_exec_id and request.orchestrator_id:
            current_iteration = SubagentIterationManager.get_current_iteration(
                graph_execution_id=db_exec_id,
                parent_agent_id=request.orchestrator_id,
                subagent_node_id=request.agent_node.uniq_id,
            )
            logger.debug(
                f"[ITERATION-TRACKING] Subagent {request.agent_node.name} iteration={current_iteration}"
            )

        # Emit sub-agent start event with iteration
        streaming_emitter.emit_subagent_start(
            subagent_id=request.agent_node.uniq_id,
            subagent_name=request.agent_node.name,
            task_description=request.task_description,
            parent_agent_id=request.orchestrator_id,
            parent_agent_name=parent_agent_name,
            iteration=current_iteration,
            subagent_node_type=request.agent_node.type.value,
        )
        logger.info(
            f"[SUBAGENT-TOOL-NESTING] emit_subagent_start: "
            f"subagent={request.agent_node.name}, iteration={current_iteration}, "
            f"db_exec_id={db_exec_id}, orchestrator_id={request.orchestrator_id}"
        )

        try:
            # Get the execution engine
            from backend.services.execution import get_executor

            executor = get_executor()

            # Verify subgraph support is available
            if (
                not hasattr(executor, "subgraph_builder")
                or not executor.subgraph_builder
            ):
                logger.warning("Subgraph builder not available, cannot execute")
                duration_ms = (time.time() - start_time) * 1000
                streaming_emitter.emit_subagent_complete(
                    subagent_id=request.agent_node.uniq_id,
                    subagent_name=request.agent_node.name,
                    success=False,
                    response_preview="Subgraph builder not available",
                    duration_ms=duration_ms,
                    tools_used=[],
                    iteration=current_iteration,
                )
                return DelegationResult(
                    success=False,
                    error="Subgraph builder not available",
                    metadata={"agent_name": request.agent_node.name},
                )

            # Prepare initial state for subgraph
            initial_state = self._prepare_subagent_state(request, current_iteration)

            # Get or create the subgraph
            subgraph = executor.subgraph_builder.create_subagent_graph(
                request.agent_node
            )

            # Execute the subgraph with complete context isolation.
            #
            # CRITICAL: We use run_async_in_sync_isolated with a LAMBDA because:
            # 1. LangGraph automatically propagates the parent's checkpointer via context vars
            # 2. When subgraph.ainvoke() is called, it creates a coroutine that captures the
            #    current context at creation time - including the parent's PostgreSQL checkpointer
            # 3. Even passing config={"configurable": {}} doesn't help because LangChain MERGES
            #    configs rather than replacing them
            # 4. By using a lambda, we defer coroutine creation until INSIDE the new event loop,
            #    where there's no inherited context to capture
            #
            # This prevents the "asyncio.Lock bound to different event loop" error.
            #
            # Phoenix project routing: run_async_in_sync_isolated creates a
            # fresh contextvars.Context(), which clears the project ContextVar.
            # We restore it inside the lambda so sub-agent spans are routed to
            # the correct Phoenix project.
            phoenix_project = context.get("phoenix_project")

            def _run_subgraph():
                async def _invoke():
                    if phoenix_project:
                        from backend.services.phoenix.project_routing import (
                            using_project,
                        )

                        with using_project(phoenix_project):
                            return await subgraph.ainvoke(
                                initial_state, config={"configurable": {}}
                            )
                    return await subgraph.ainvoke(
                        initial_state, config={"configurable": {}}
                    )

                return _invoke()

            result_state = run_async_in_sync_isolated(_run_subgraph)

            # Debug log: Show pause-related state fields for troubleshooting
            logger.debug(
                f"[SUBAGENT-REVIEW-DEBUG] Subgraph result for {request.agent_node.name}: "
                f"paused={result_state.get('paused')}, "
                f"paused_for_review={result_state.get('paused_for_review')}, "
                f"review_data={result_state.get('review_data')}, "
                f"state_keys={list(result_state.keys())}"
            )

            # Check for errors
            if result_state.get("error"):
                error_msg = result_state["error"]
                logger.error(f"Subgraph delegation failed: {error_msg}")
                duration_ms = (time.time() - start_time) * 1000
                streaming_emitter.emit_subagent_complete(
                    subagent_id=request.agent_node.uniq_id,
                    subagent_name=request.agent_node.name,
                    success=False,
                    response_preview=error_msg,
                    duration_ms=duration_ms,
                    tools_used=[
                        te.get("tool", "unknown")
                        for te in result_state.get("tool_executions", [])
                    ],
                    iteration=current_iteration,
                )
                return DelegationResult(
                    success=False,
                    error=error_msg,
                    metadata={
                        "agent_name": request.agent_node.name,
                        "execution_type": "subgraph",
                    },
                )

            # Check if sub-agent is paused for review
            if result_state.get("paused_for_review"):
                logger.info(
                    f"[SUBAGENT-REVIEW] Sub-agent {request.agent_node.name} is paused for review, "
                    "raising GraphInterrupt to pause parent workflow"
                )
                # Get review data from result state
                review_data = result_state.get("review_data", {})
                review_data["sub_agent_name"] = request.agent_node.name
                review_data["sub_agent_id"] = request.agent_node.uniq_id

                logger.debug(
                    f"[SUBAGENT-REVIEW-DEBUG] Interrupt payload for {request.agent_node.name}: "
                    f"type={review_data.get('type')}, node_id={review_data.get('node_id')}, "
                    f"review_mode={review_data.get('review_mode')}, "
                    f"full_data={review_data}"
                )

                # Raise GraphInterrupt to pause the parent workflow
                from langgraph.types import Interrupt

                raise GraphInterrupt((Interrupt(value=review_data),))

            # Extract result
            result = result_state.get("response", "")
            new_order = result_state.get(
                "execution_order", request.context.get("execution_order", 0) + 1
            )

            logger.info(
                f"Subgraph delegation to {request.agent_node.name} completed "
                f"with execution order: {new_order}"
            )

            # Store subagent output
            self._store_subagent_output(request, result_state)

            # Calculate duration and get tools used
            duration_ms = (time.time() - start_time) * 1000
            tools_used = [
                te.get("tool", "unknown")
                for te in result_state.get("tool_executions", [])
            ]

            # Emit sub-agent completion event with iteration
            streaming_emitter.emit_subagent_complete(
                subagent_id=request.agent_node.uniq_id,
                subagent_name=request.agent_node.name,
                success=True,
                response_preview=result,
                duration_ms=duration_ms,
                tools_used=tools_used,
                iteration=current_iteration,
            )

            return DelegationResult(
                success=True,
                response=result,
                metadata={
                    "agent_name": request.agent_node.name,
                    "agent_id": request.agent_node.uniq_id,
                    "execution_type": "subgraph",
                    "execution_order": new_order,
                    "structured_output": result_state.get("structured_output"),
                },
            )

        except GraphInterrupt as gi:
            # GraphInterrupt means the sub-agent needs human review
            # Re-raise to propagate to the parent graph so the whole workflow pauses
            logger.info(
                f"[SUBAGENT-REVIEW] Sub-agent {request.agent_node.name} requires review, "
                "propagating interrupt to parent graph"
            )
            raise gi

        except Exception as e:
            # Check if this is a wrapped GraphInterrupt (from run_async_in_sync)
            if "GraphInterrupt" in str(type(e).__name__) or "Interrupt" in str(e):
                logger.info(
                    f"[SUBAGENT-REVIEW] Sub-agent {request.agent_node.name} requires review, "
                    "propagating interrupt to parent graph"
                )
                # Re-raise as properly formatted GraphInterrupt with Interrupt tuple
                from langgraph.types import Interrupt

                interrupt_value = {
                    "error": str(e),
                    "source": "subgraph_delegation",
                    "sub_agent_name": request.agent_node.name,
                    "sub_agent_id": request.agent_node.uniq_id,
                }
                raise GraphInterrupt((Interrupt(value=interrupt_value),)) from e

            # Calculate duration for error case
            duration_ms = (time.time() - start_time) * 1000

            # Emit sub-agent failure event with iteration
            streaming_emitter.emit_subagent_complete(
                subagent_id=request.agent_node.uniq_id,
                subagent_name=request.agent_node.name,
                success=False,
                response_preview=str(e),
                duration_ms=duration_ms,
                tools_used=[],
                iteration=current_iteration,
            )

            logger.error(f"Subgraph delegation failed: {e}", exc_info=True)
            return DelegationResult(
                success=False,
                error=str(e),
                metadata={
                    "agent_name": request.agent_node.name,
                    "execution_type": "subgraph",
                },
            )

    def _prepare_subagent_state(
        self, request: DelegationRequest, current_iteration: int = 1
    ) -> Dict[str, Any]:
        """Prepare initial state for subgraph execution.

        Args:
            request: The delegation request
            current_iteration: The current invocation index for this subagent

        Returns:
            Initial state dictionary for subgraph
        """
        context = request.context or {}
        exec_id = context.get("execution_id")
        db_exec_id = context.get("db_execution_id")
        current_order = context.get("execution_order", 0)
        graph_name = context.get("graph_name")
        tool_node_mapping = context.get("tool_node_mapping", {})

        task_id = generate_task_id(exec_id, request.agent_node.uniq_id)

        logger.debug(
            f"Preparing subagent state - exec_id: {exec_id}, "
            f"db_exec_id: {db_exec_id}, order: {current_order}"
        )

        from backend.services.subgraph.models import SubAgentState

        initial_state: SubAgentState = {
            "task_description": request.task_description,
            "task_id": task_id,
            "parent_execution_id": exec_id,
            "parent_db_execution_id": db_exec_id,
            "parent_node_id": request.orchestrator_id,
            "parent_node_execution_id": context.get("parent_node_execution_id"),
            "parent_node_name": "",  # TODO: Get from context if needed
            "execution_order": current_order + 1,
            "invocation_index": current_iteration,
            "start_time": None,
            "end_time": None,
            "agent_node_id": request.agent_node.uniq_id,
            "agent_node_name": request.agent_node.name,
            "agent_config": request.agent_node.agent_config.__dict__
            if request.agent_node.agent_config
            else None,
            "user_id": context.get("user_id"),
            "graph_name": graph_name,
            "tool_node_mapping": tool_node_mapping,
            "response": None,
            "structured_output": None,
            "tool_executions": [],
            "error": None,
            "paused": None,
            "paused_for_review": None,
            "review_data": None,
            "messages": [],
            "metadata": {},
        }

        return initial_state

    def _store_subagent_output(
        self, request: DelegationRequest, result_state: Dict[str, Any]
    ) -> None:
        """Store subagent output for later retrieval.

        Args:
            request: The delegation request
            result_state: The result state from subgraph execution
        """
        exec_id = request.context.get("execution_id") if request.context else None
        if not exec_id or not self.graph_manager:
            return

        # Initialize storage if needed
        if not hasattr(self.graph_manager, "_subagent_outputs"):
            self.graph_manager._subagent_outputs = {}
        if exec_id not in self.graph_manager._subagent_outputs:
            self.graph_manager._subagent_outputs[exec_id] = {}

        # Store the subagent's output with its node ID
        output_data = {
            "raw": result_state.get("response"),
            "structured": result_state.get("structured_output"),
            "fields": result_state.get("structured_output", {}),
        }
        self.graph_manager._subagent_outputs[exec_id][request.agent_node.uniq_id] = (
            output_data
        )

        logger.info(
            f"[SUBAGENT_STORE] Stored output for {request.agent_node.name} "
            f"(ID: {request.agent_node.uniq_id})"
        )
        logger.debug(
            f"[SUBAGENT_STORE] Execution ID: {exec_id}, "
            f"Output preview: {str(result_state.get('response', ''))[:200]}"
        )
