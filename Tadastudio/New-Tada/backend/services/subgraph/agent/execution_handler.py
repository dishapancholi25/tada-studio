"""
Agent execution handler for subgraph execution.

This module contains the core logic for executing agents within subgraphs,
coordinating database tracking, tool tracking, and WebSocket notifications.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from langchain_core.messages import AIMessage
from langgraph.errors import GraphInterrupt

from backend.models.workflow import EnhancedNodeData, NodeType
from backend.services.common.utils.response_extractor import extract_response_content
from backend.services.common.utils.websocket_notifier import (
    send_node_complete_notification,
    send_node_error_notification,
    send_node_start_notification,
)
from backend.services.config import get_logger
from backend.services.execution.subagent import SubagentIterationManager

from ..models import SubAgentState
from .database_tracker import (
    complete_agent_execution_record,
    create_agent_execution_record,
    fail_agent_execution_record,
)
from .tool_tracker import track_tool_executions


execution_handler_logger = get_logger("subgraph.agent.execution_handler")


async def execute_agent_in_subgraph(
    state: SubAgentState,
    agent_node: EnhancedNodeData,
    graph_manager: Any,
) -> Dict[str, Any]:
    """
    Execute an agent within a subgraph.

    This is the main execution function that coordinates all aspects of
    sub-agent execution including database tracking, tool tracking,
    and WebSocket notifications.

    Args:
        state: The current sub-agent state
        agent_node: The agent node to execute
        graph_manager: The graph manager instance

    Returns:
        Updated state dictionary with execution results
    """
    execution_handler_logger.info(f"Executing sub-agent {agent_node.name} in subgraph")

    start_time = datetime.now(timezone.utc)
    execution_order = state["execution_order"]

    # Get or create iteration state for this subagent
    iteration_state = None
    current_iteration = 1

    parent_db_execution_id = state.get("parent_db_execution_id")
    parent_node_id = state.get("parent_node_id")
    thread_id = state.get("thread_id", "")

    if parent_db_execution_id and parent_node_id:
        iteration_state = SubagentIterationManager.get_or_create_iteration_state(
            graph_execution_id=parent_db_execution_id,
            parent_agent_id=parent_node_id,
            subagent_node_id=agent_node.uniq_id,
            thread_id=thread_id,
        )
        current_iteration = iteration_state.get("current_iteration", 1)

        execution_handler_logger.info(
            f"[ITERATION-TRACKING] Sub-agent {agent_node.name} iteration={current_iteration}"
        )

    # Get invocation_index from state (set by subgraph_executor), fallback to current_iteration
    invocation_index = state.get("invocation_index", current_iteration)

    # Generate unique parent_subagent_id for tool-to-subagent association
    # Format matches frontend's uniqueId: "{subagent_node_id}_iter_{iteration}"
    parent_subagent_id = f"{agent_node.uniq_id}_iter_{invocation_index}"
    execution_handler_logger.info(
        f"[TOOL-SUBAGENT-LINK] Generated parent_subagent_id={parent_subagent_id} "
        f"for subagent={agent_node.name}"
    )

    # Create database record
    node_exec_id = await create_agent_execution_record(
        agent_node=agent_node,
        parent_db_execution_id=parent_db_execution_id,
        parent_node_id=parent_node_id,
        parent_node_execution_id=state.get("parent_node_execution_id"),
        execution_order=execution_order,
        task_description=state["task_description"],
        invocation_index=invocation_index,
    )
    execution_handler_logger.info(
        f"[SUBAGENT-TOOL-NESTING] create_agent_execution_record: "
        f"agent={agent_node.name}, invocation_index={invocation_index}, "
        f"result_node_exec_id={node_exec_id}"
    )

    # Send start notification - use agent UUID as node_id to match LangGraph streaming
    # Include step (iteration) for frontend to distinguish multiple invocations
    await send_node_start_notification(
        execution_id=state.get("parent_execution_id"),
        node_id=agent_node.uniq_id,
        node_name=agent_node.name,
        node_type=NodeType.AGENT.value,
        is_sub_agent=True,
        parent_agent_id=parent_node_id,
        step=current_iteration,
    )

    try:
        # Set up execution context
        _setup_execution_context(state, graph_manager)

        # Create tool execution tracker (passed by reference to async executor)
        tool_execution_tracker = []

        # Re-establish execution context variables from state.
        # run_async_in_sync_isolated creates a fresh contextvars.Context() to prevent
        # the parent's PostgreSQL checkpointer from leaking into sub-agent event loops.
        # This clears execution_id/db_execution_id context vars that delegation tools
        # rely on to choose SubgraphDelegationExecutor over SimpleDelegationExecutor.
        # SimpleDelegationExecutor calls execute_simple_chat() without graph_name, so
        # no tools are loaded — causing HTTP REQUEST tools to silently fail for any
        # agent that is itself a sub-orchestrator.
        # Restoring the vars here makes them visible to delegation-tool callsites that
        # run via loop.run_in_executor(), which copies the current context to its thread.
        _restore_execution_context_from_state(state, node_exec_id, agent_node)

        # Check if this is a retry (review_state has history with feedback)
        # If so, augment the task with feedback context
        task_message = _get_task_with_feedback(
            task_description=state["task_description"],
            review_state=state.get("review_state"),
        )

        # Execute the agent
        result = await _execute_agent(
            agent_node,
            task_message,
            graph_manager,
            state.get("parent_db_execution_id"),
            tool_execution_tracker,
            state.get("graph_name"),
            execution_id=state.get("parent_execution_id"),
            user_id=state.get("user_id"),
            execution_order=execution_order,
            tool_node_mapping=state.get("tool_node_mapping", {}),
            invocation_index=invocation_index,
            parent_subagent_id=parent_subagent_id,
        )

        # Process the response
        (
            response_content,
            token_counts,
            result_tool_executions,
            result_message_structure,
        ) = _process_agent_result(result, agent_node.name, tool_execution_tracker)

        # Ensure the tracker includes any tool executions returned from the executor.
        if result_tool_executions:
            execution_handler_logger.info(
                f"[TOOL-TRACKING-DEBUG] Executor returned {len(result_tool_executions)} tool execution(s)"
            )
            if tool_execution_tracker is result_tool_executions:
                pass
            elif not tool_execution_tracker:
                execution_handler_logger.info(
                    "[TOOL-TRACKING-DEBUG] Populating local tool tracker from execution result payload"
                )
                tool_execution_tracker.extend(result_tool_executions)
            else:
                existing_keys = {
                    exec_data.get("id") or exec_data.get("call_id") or repr(exec_data)
                    for exec_data in tool_execution_tracker
                }
                for exec_data in result_tool_executions:
                    key = (
                        exec_data.get("id")
                        or exec_data.get("call_id")
                        or repr(exec_data)
                    )
                    if key not in existing_keys:
                        tool_execution_tracker.append(exec_data)
                        existing_keys.add(key)

        end_time = datetime.now(timezone.utc)

        # Complete database record
        node_exec_data = await complete_agent_execution_record(
            node_exec_id=node_exec_id,
            agent_node=agent_node,
            response_content=response_content,
            tool_execution_tracker=tool_execution_tracker,
            token_counts=token_counts,
            start_time=start_time,
            end_time=end_time,
            input_message=task_message,
            message_structure=result_message_structure,
        )

        # Send completion notification with step for frontend iteration tracking
        await _send_completion_notification(
            state,
            agent_node,
            response_content,
            node_exec_data,
            start_time,
            end_time,
            step=current_iteration,
        )

        # Increment iteration for next invocation of this subagent
        execution_handler_logger.info(
            f"[SUBAGENT-TOOL-NESTING] increment_iteration check: "
            f"iteration_state={iteration_state is not None}, node_exec_id={node_exec_id}"
        )
        if iteration_state and node_exec_id:
            SubagentIterationManager.increment_iteration(
                iteration_state_id=iteration_state["id"],
                node_execution_id=str(node_exec_id),
            )
            execution_handler_logger.info(
                f"[SUBAGENT-TOOL-NESTING] increment_iteration called for state_id={iteration_state['id']}"
            )

        # Track tool executions
        updated_order = await track_tool_executions(
            tool_execution_tracker=tool_execution_tracker,
            agent_node=agent_node,
            parent_db_execution_id=state.get("parent_db_execution_id"),
            parent_node_execution_id=node_exec_id,
            parent_execution_id=state.get("parent_execution_id"),
            execution_order=execution_order,
            tool_node_mapping=state.get("tool_node_mapping", {}),
            graph_name=state.get("graph_name"),
            graph_manager=graph_manager,
            invocation_index=invocation_index,
            parent_subagent_id=parent_subagent_id,
        )

        # Prepare review_state update for the review node (if review is enabled)
        # The review node will read this to process the review
        review_state_update = _prepare_review_state_update(
            agent_node=agent_node,
            response_content=response_content,
            task_description=state["task_description"],
            current_review_state=state.get("review_state"),
        )

        # Return state updates
        return {
            "response": response_content,
            "tool_executions": tool_execution_tracker,
            "execution_order": updated_order + 1,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "messages": [AIMessage(content=response_content)],
            "metadata": {
                **state.get("metadata", {}),
                "token_counts": token_counts,
                "execution_time": (end_time - start_time).total_seconds(),
            },
            **review_state_update,
        }

    except GraphInterrupt as gi:
        # GraphInterrupt means human review is needed
        # Since sub-agents run via delegation tools (not as graph nodes),
        # we can't use LangGraph's standard interrupt propagation.
        # Instead, we return a special "paused" response that indicates
        # the sub-agent is awaiting review.
        execution_handler_logger.info(
            f"[SUBAGENT-REVIEW] GraphInterrupt raised for {agent_node.name}, "
            "returning paused state (WebSocket notification already sent)"
        )

        # Extract interrupt payload if available
        interrupt_data = {}
        if hasattr(gi, "args") and gi.args:
            execution_handler_logger.debug(
                f"[SUBAGENT-REVIEW-DEBUG] Extracting interrupt data from GraphInterrupt.args: "
                f"args_type={type(gi.args)}, args_len={len(gi.args) if hasattr(gi.args, '__len__') else 'N/A'}"
            )

            # GraphInterrupt stores Interrupt objects in args (may be nested in tuples)
            def find_interrupt_value(obj):
                """Recursively find Interrupt.value in nested structure."""
                if hasattr(obj, "value"):
                    return obj.value
                if isinstance(obj, (list, tuple)):
                    for item in obj:
                        result = find_interrupt_value(item)
                        if result is not None:
                            return result
                return None

            interrupt_data = find_interrupt_value(gi.args) or {}
            execution_handler_logger.debug(
                f"[SUBAGENT-REVIEW-DEBUG] Extracted interrupt_data for {agent_node.name}: "
                f"keys={list(interrupt_data.keys()) if interrupt_data else 'empty'}, "
                f"type={interrupt_data.get('type')}"
            )
        else:
            execution_handler_logger.warning(
                f"[SUBAGENT-REVIEW] GraphInterrupt for {agent_node.name} has no args, "
                f"interrupt_data will be empty. gi.args={getattr(gi, 'args', 'N/A')}"
            )

        # Return a paused state - the workflow will pause here
        # and resume when the user provides review feedback
        return {
            "response": f"[AWAITING REVIEW] {agent_node.name} output is pending human review.",
            "paused": True,
            "paused_for_review": True,
            "review_data": interrupt_data,
            "execution_order": execution_order,
            "end_time": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "metadata": {
                **state.get("metadata", {}),
                "paused_for_review": True,
                "review_node_id": agent_node.uniq_id,
                "review_node_name": agent_node.name,
            },
        }

    except Exception as e:
        execution_handler_logger.error(
            f"Sub-agent execution failed: {str(e)}", exc_info=True
        )

        # Handle error
        await fail_agent_execution_record(node_exec_id, agent_node, str(e))
        await send_node_error_notification(
            execution_id=state.get("parent_execution_id"),
            node_id=agent_node.uniq_id,  # Use UUID to match LangGraph streaming
            node_name=agent_node.name,
            error=str(e),
        )

        # Return error state
        return {
            "error": str(e),
            "execution_order": execution_order,
            "end_time": datetime.now(timezone.utc).isoformat(),
        }


def _setup_execution_context(state: SubAgentState, graph_manager: Any) -> None:
    """Set up the execution context for the agent."""
    graph_name = state.get("graph_name")
    execution_handler_logger.info(f"Sub-agent state graph_name: {graph_name}")

    if graph_name:
        graph_manager.current_graph_name = graph_name
        execution_handler_logger.info(
            f"Set graph_manager.current_graph_name to: {graph_name}"
        )
    elif not hasattr(graph_manager, "current_graph_name"):
        # Try to get the graph name from execution context as fallback
        from backend.services.execution.context import get_current_execution_id

        exec_id = get_current_execution_id()
        if exec_id and hasattr(graph_manager, "active_executions"):
            exec_data = graph_manager.active_executions.get(exec_id, {})
            fallback_graph_name = exec_data.get("graph_name")
            if fallback_graph_name:
                graph_manager.current_graph_name = fallback_graph_name
                execution_handler_logger.info(
                    f"Set graph context from execution data: {fallback_graph_name}"
                )


async def _execute_agent(
    agent_node: EnhancedNodeData,
    task_message: str,
    graph_manager: Any,
    db_execution_id: Optional[str],
    tool_execution_tracker: list,
    graph_name: Optional[str] = None,
    execution_id: Optional[str] = None,
    user_id: Optional[str] = None,
    execution_order: Optional[int] = None,
    tool_node_mapping: Optional[Dict[str, Dict[str, str]]] = None,
    invocation_index: Optional[int] = None,
    parent_subagent_id: Optional[str] = None,
) -> Any:
    """Execute the agent using graph manager's async method."""
    result = await graph_manager.execute_agent_async(
        agent_node,
        task_message,
        tool_execution_tracker=tool_execution_tracker,
        db_execution_id=db_execution_id,
        return_token_counts=True,
        graph_name=graph_name,
        execution_id=execution_id,
        user_id=user_id,
        is_subagent=True,
        execution_order=execution_order,
        tool_node_mapping=tool_node_mapping,
        invocation_index=invocation_index,
        parent_subagent_id=parent_subagent_id,
    )

    return result


def _process_agent_result(
    result: Any, agent_name: str, tool_execution_tracker: list
) -> tuple:
    """
    Process agent execution result.

    Returns:
        Tuple of (response_content, token_counts, tool_executions, message_structure)
    """
    tool_executions = []
    message_structure = None

    if isinstance(result, tuple):
        # Handle 4-tuple from ExecutionResult.to_tuple():
        # (response, token_counts, tool_executions, message_structure)
        if len(result) >= 4:
            response, token_counts, tool_executions, message_structure = result[:4]
        elif len(result) >= 3:
            response, token_counts, tool_executions = result[:3]
        elif len(result) == 2:
            response, token_counts = result
        elif len(result) == 1:
            response = result[0]
            token_counts = None
        else:
            response = None
            token_counts = None
    else:
        response = result
        token_counts = None

    # Extract content
    response_content = extract_response_content(
        response, agent_name, tool_execution_tracker
    )

    return response_content, token_counts, tool_executions, message_structure


async def _send_completion_notification(
    state: SubAgentState,
    agent_node: EnhancedNodeData,
    response_content: str,
    node_exec_data: Optional[Dict[str, Any]],
    start_time: datetime,
    end_time: datetime,
    step: Optional[int] = None,
) -> None:
    """Send WebSocket completion notification with complete data."""
    # Extract data from database record if available
    duration_seconds = None
    start_time_str = None
    end_time_str = None
    input_tokens = None
    output_tokens = None
    total_tokens = None
    input_data = None

    if node_exec_data and isinstance(node_exec_data, dict):
        duration_seconds = node_exec_data.get("duration_seconds")
        start_time_str = (
            str(node_exec_data.get("start_time"))
            if node_exec_data.get("start_time")
            else None
        )
        end_time_str = (
            str(node_exec_data.get("end_time"))
            if node_exec_data.get("end_time")
            else None
        )
        input_tokens = node_exec_data.get("input_tokens")
        output_tokens = node_exec_data.get("output_tokens")
        total_tokens = node_exec_data.get("total_tokens")
        input_data = node_exec_data.get("input_data")
    else:
        # Fallback calculation
        duration_seconds = (end_time - start_time).total_seconds()

    await send_node_complete_notification(
        execution_id=state.get("parent_execution_id"),
        node_id=agent_node.uniq_id,  # Use UUID to match LangGraph streaming
        node_name=agent_node.name,
        output={"response": response_content},
        node_type=NodeType.AGENT.value,
        duration_seconds=duration_seconds,
        input_data=input_data,
        start_time=start_time_str,
        end_time=end_time_str,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        is_sub_agent=True,
        parent_agent_id=state.get("parent_node_id"),
        step=step,
    )

    execution_handler_logger.info(
        f"Sent WebSocket node complete for sub-agent {agent_node.name} with full data"
    )


def _get_review_config_safe(agent_node: EnhancedNodeData) -> Optional[Any]:
    """
    Safely get review config from agent node.

    Args:
        agent_node: The agent node to get review config from

    Returns:
        ReviewConfig object or None if not available
    """
    if not agent_node.agent_config:
        return None

    review_config = agent_node.agent_config.review_config
    if review_config is None:
        return None

    # Handle dict representation
    if isinstance(review_config, dict):
        from backend.models.workflow.configs import ReviewConfig

        try:
            return ReviewConfig(**review_config)
        except Exception:
            return None

    return review_config


def _get_task_with_feedback(
    task_description: str,
    review_state: Optional[Dict[str, Any]],
) -> str:
    """
    Get the task description, augmented with feedback from previous review iterations.

    If this is a retry after rejection, the review_state will contain history
    with feedback that should be included in the task.

    Args:
        task_description: Original task description
        review_state: Current review state (may contain history with feedback)

    Returns:
        Task message, potentially augmented with feedback context
    """
    if not review_state:
        return task_description

    history = review_state.get("history", [])
    if not history:
        return task_description

    # Build feedback context from history
    from backend.services.execution.review.executor import ReviewExecutor

    feedback_context = ReviewExecutor.build_feedback_context(history)

    if feedback_context:
        execution_handler_logger.info(
            f"[SUBAGENT-EXECUTION] Augmenting task with feedback from "
            f"{len(history)} previous review iteration(s)"
        )
        return f"{task_description}{feedback_context}"

    return task_description


def _prepare_review_state_update(
    agent_node: EnhancedNodeData,
    response_content: str,
    task_description: str,
    current_review_state: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Prepare review_state update for the review node.

    If review is enabled for this agent, stores the output and config
    in review_state so the review node can process it.

    Args:
        agent_node: The agent node that was executed
        response_content: The agent's output
        task_description: Original task description
        current_review_state: Current review state (may contain history)

    Returns:
        Dictionary with review_state update, or empty dict if review not enabled
    """
    review_config = _get_review_config_safe(agent_node)
    if not review_config or not review_config.review_enabled:
        return {}

    # Get current iteration and history from existing review_state
    # Match regular agent pattern: iteration = len(history) + 1
    history = []
    if current_review_state:
        history = current_review_state.get("history", [])
    iteration = len(history) + 1

    execution_handler_logger.info(
        f"[SUBAGENT-EXECUTION] Preparing review_state for {agent_node.name}, "
        f"iteration={iteration}, history_len={len(history)}"
    )

    # Build review config dict for review node (match regular agent pattern)
    config_dict = {
        "review_enabled": True,
        "review_mode": review_config.review_mode,
        "review_prompt": review_config.review_prompt,
        "max_iterations": review_config.max_iterations,
        "auto_approve_on_max_iterations": getattr(
            review_config, "auto_approve_on_max_iterations", True
        ),
        "timeout_seconds": getattr(review_config, "timeout_seconds", None),
    }

    # Include reviewer_llm_config for LLM review mode
    if review_config.review_mode == "llm" and review_config.reviewer_llm_config:
        llm_config = review_config.reviewer_llm_config
        if hasattr(llm_config, "model_dump"):
            config_dict["reviewer_llm_config"] = llm_config.model_dump()
        elif isinstance(llm_config, dict):
            config_dict["reviewer_llm_config"] = llm_config
        else:
            # Try to convert to dict
            config_dict["reviewer_llm_config"] = {
                "model_id": getattr(llm_config, "model_id", None),
                "provider": getattr(llm_config, "provider", None),
                "temperature": getattr(llm_config, "temperature", 0.7),
            }

    return {
        "review_state": {
            "output": response_content,
            "config": config_dict,
            "iteration": iteration,
            "history": history,
            "input_message": task_description,
        }
    }


def _restore_execution_context_from_state(
    state: SubAgentState,
    node_exec_id: Any,
    agent_node: EnhancedNodeData,
) -> None:
    """Re-establish execution context variables from subagent state.

    run_async_in_sync_isolated() deliberately creates a fresh contextvars.Context()
    to prevent the parent graph's PostgreSQL checkpointer from leaking into the
    sub-agent's event loop.  The side-effect is that execution_id /
    db_execution_id context variables are cleared.

    Delegation tools (AgentDelegationToolFactory.delegate_to_agent) read these
    context variables at call-time.  When they are absent the factory falls back
    to _execute_simple(), which calls execute_simple_chat() without graph_name,
    so no connected tool-nodes (HTTP REQUEST, etc.) are resolved and the agent
    silently has no tools.

    Restoring the vars here makes them available to any delegation-tool closures
    that this sub-agent may invoke.  asyncio.get_event_loop().run_in_executor()
    copies the current context to its worker thread (Python ≥ 3.7), so the vars
    are reliably visible inside the synchronous delegate_to_agent() closure.
    """
    parent_exec_id = state.get("parent_execution_id")
    parent_db_exec_id = state.get("parent_db_execution_id")

    if not (parent_exec_id and parent_db_exec_id):
        execution_handler_logger.debug(
            "[SUBAGENT-CONTEXT] Skipping context restore — "
            "parent execution IDs not available in state"
        )
        return

    try:
        from backend.services.execution.context import (
            set_execution_context,
            update_node_execution_map,
        )

        set_execution_context(
            execution_id=str(parent_exec_id),
            db_execution_id=str(parent_db_exec_id),
        )

        # Register current agent's node execution ID so child delegation tools
        # can look it up via get_node_execution_id(orchestrator_id).
        if node_exec_id:
            update_node_execution_map(agent_node.uniq_id, str(node_exec_id))

        execution_handler_logger.debug(
            f"[SUBAGENT-CONTEXT] Restored execution context for {agent_node.name}: "
            f"execution_id={parent_exec_id}, node_exec_id={node_exec_id}"
        )
    except Exception as ctx_err:
        execution_handler_logger.warning(
            f"[SUBAGENT-CONTEXT] Could not restore execution context for "
            f"{agent_node.name}: {ctx_err}"
        )
