"""
Individual node execution within workflows.

This module handles executing specific node types (AGENT, END)
within a subworkflow execution.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from langchain_core.messages import AIMessage
from backend.models.workflow import EnhancedNodeData
from backend.services.execution.history import ExecutionHistoryService
from backend.services.common.utils.websocket_notifier import (
    send_node_complete_notification,
    send_node_start_notification,
)
from backend.services.config import get_logger

from ..agent.tool_tracker import track_tool_executions
from .database_tracker import create_end_node_record


node_executor_logger = get_logger("subgraph.workflow.node_executor")


async def execute_agent_node(
    node: EnhancedNodeData,
    current_output: str,
    parent_db_execution_id: Optional[str],
    parent_node_id: str,
    parent_execution_id: str,
    current_order: int,
    graph_manager: Any,
    user_id: Optional[str] = None,
    parent_node_exec_id: Optional[int] = None,
) -> tuple:
    """
    Execute an AGENT node within a workflow.

    Args:
        node: The agent node to execute
        current_output: Current workflow output (input to this node)
        parent_db_execution_id: Parent graph's database execution ID
        parent_node_id: Parent orchestrator's node ID
        parent_execution_id: Parent execution ID for WebSocket
        current_order: Current execution order
        graph_manager: Graph manager instance

    Returns:
        Tuple of (output_content, token_usage)
    """
    node_executor_logger.info(
        f"[SUBWORKFLOW AGENT] Starting execution of agent node: {node.name}"
    )

    agent_start_time = datetime.now(timezone.utc)
    agent_node_exec_id = None

    # Create database record
    if parent_db_execution_id:
        try:
            node_executor_logger.info(
                f"[SUBWORKFLOW AGENT] Creating DB record for {node.name}"
            )

            node_exec_result = ExecutionHistoryService.create_node_execution(
                graph_execution_id=parent_db_execution_id,
                node_id=node.uniq_id,
                node_name=node.name,
                node_type=node.type.value,
                execution_order=current_order,
                is_sub_agent=True,
                parent_agent_id=parent_node_exec_id,
                input_data={
                    "parent_node_id": parent_node_id,
                    "message": current_output,
                },
            )

            agent_node_exec_id = (
                node_exec_result.get("id") if node_exec_result else None
            )

            # Start the node execution
            if agent_node_exec_id:
                ExecutionHistoryService.start_node_execution(agent_node_exec_id)

            node_executor_logger.info(
                f"[SUBWORKFLOW AGENT] Created DB record: {agent_node_exec_id}"
            )

        except Exception as e:
            node_executor_logger.error(
                f"Failed to create node execution for {node.name}: {e}"
            )

    # Send start notification
    await send_node_start_notification(
        execution_id=parent_execution_id,
        node_id=node.uniq_id,
        node_name=node.name,
        node_type=node.type.value,
        is_sub_agent=False,
        parent_agent_id=parent_node_id,
        database_node_id=agent_node_exec_id,
    )

    # Execute agent
    node_executor_logger.info(
        f"[SUBWORKFLOW AGENT] Executing agent {node.name} with input: "
        f"{current_output[:100] if current_output else 'None'}"
    )

    tool_execution_tracker = []

    try:
        result = await graph_manager.execute_agent_async(
            node,
            current_output,
            tool_execution_tracker=tool_execution_tracker,
            db_execution_id=parent_db_execution_id,
            execution_id=parent_execution_id,
            graph_name=getattr(graph_manager, "current_graph_name", None),
            user_id=user_id,
            return_token_counts=True,
            node_execution_id=str(agent_node_exec_id) if agent_node_exec_id else None,
            execution_order=current_order,
            db_node_id=str(agent_node_exec_id) if agent_node_exec_id else None,
            is_subagent=True,
        )

        node_executor_logger.info(
            f"[SUBWORKFLOW AGENT] Agent {node.name} execution completed"
        )

        # Extract response and token usage
        # to_tuple() returns (response, token_counts, tool_executions, message_structure, metadata)
        if isinstance(result, tuple):
            response, token_usage, *_rest = result
            node_executor_logger.info(
                f"[SUBWORKFLOW AGENT] Got token usage: {token_usage}"
            )
        else:
            response = result
            token_usage = None
            _tool_executions = []
            node_executor_logger.info("[SUBWORKFLOW AGENT] No token usage returned")

        # Extract content from response
        if isinstance(response, AIMessage):
            output_content = response.content
        elif hasattr(response, "content"):
            output_content = response.content
        else:
            output_content = str(response)

        node_executor_logger.info(
            f"[SUBWORKFLOW AGENT] Agent {node.name} output: "
            f"{output_content[:100] if output_content else 'None'}"
        )

    except Exception as e:
        node_executor_logger.error(
            f"[SUBWORKFLOW AGENT] Error executing agent {node.name}: {e}",
            exc_info=True,
        )
        raise

    # Complete database record
    if agent_node_exec_id:
        agent_end_time = datetime.now(timezone.utc)
        duration = (agent_end_time - agent_start_time).total_seconds()

        node_executor_logger.info(
            f"[SUBWORKFLOW AGENT] Completing DB record for {node.name}, "
            f"duration: {duration}s"
        )

        try:
            from backend.services.trace.cost_calculator import build_llm_metadata

            llm_metadata = build_llm_metadata(
                node,
                token_usage,
                start_time=agent_start_time.timestamp(),
                end_time=agent_end_time.timestamp(),
            )

            ExecutionHistoryService.complete_node_execution(
                node_execution_id=agent_node_exec_id,
                status="completed",
                output_data={"response": output_content},
                token_counts=token_usage if token_usage else None,
                llm_metadata=llm_metadata,
            )

            node_executor_logger.info(
                f"[SUBWORKFLOW AGENT] DB record completed for {node.name}"
            )

        except Exception as e:
            node_executor_logger.error(
                f"Failed to complete node execution for {node.name}: {e}"
            )

    # Track tool executions (creates DB records for tools/sub-agents under this agent)
    if tool_execution_tracker and parent_db_execution_id:
        try:
            await track_tool_executions(
                tool_execution_tracker=tool_execution_tracker,
                agent_node=node,
                parent_db_execution_id=parent_db_execution_id,
                parent_node_execution_id=str(agent_node_exec_id)
                if agent_node_exec_id
                else None,
                parent_execution_id=parent_execution_id,
                execution_order=current_order,
                tool_node_mapping={},
                graph_name=getattr(graph_manager, "current_graph_name", None),
                graph_manager=graph_manager,
            )
            node_executor_logger.info(
                f"[SUBWORKFLOW AGENT] Tracked {len(tool_execution_tracker)} tool executions for {node.name}"
            )
        except Exception as e:
            node_executor_logger.error(
                f"[SUBWORKFLOW AGENT] Failed to track tool executions for {node.name}: {e}"
            )

    # Send completion notification
    await send_node_complete_notification(
        execution_id=parent_execution_id,
        node_id=node.uniq_id,
        node_name=node.name,
        output={"response": output_content},
        node_type=node.type.value,
        duration_seconds=duration if agent_node_exec_id else None,
        is_sub_agent=False,
        parent_agent_id=parent_node_id,
        database_node_id=agent_node_exec_id,
        input_tokens=token_usage.get("input_tokens", 0) if token_usage else 0,
        output_tokens=token_usage.get("output_tokens", 0) if token_usage else 0,
    )

    return output_content, token_usage, agent_node_exec_id


async def process_end_node(
    node: EnhancedNodeData,
    current_output: str,
    parent_db_execution_id: Optional[str],
    parent_node_id: str,
    parent_execution_id: str,
    parent_node_exec_id: Optional[int] = None,
) -> str:
    """
    Process an END node in the workflow.

    Args:
        node: The END node
        current_output: Current workflow output (becomes final output)
        parent_db_execution_id: Parent graph's database execution ID
        parent_node_id: Parent orchestrator's node ID
        parent_execution_id: Parent execution ID for WebSocket notifications

    Returns:
        The final workflow output
    """
    node_executor_logger.info(f"[SUBWORKFLOW END] Processing END node: {node.name}")

    workflow_output = current_output

    node_executor_logger.info(
        f"[SUBWORKFLOW END] Workflow completed with output: "
        f"{workflow_output[:200] if workflow_output else 'None'}"
    )

    # Create database record for END node
    if parent_db_execution_id:
        await create_end_node_record(
            node=node,
            parent_db_execution_id=parent_db_execution_id,
            parent_node_id=parent_node_id,
            parent_execution_id=parent_execution_id,
            workflow_output=workflow_output,
            parent_node_exec_id=parent_node_exec_id,
        )

    return workflow_output
