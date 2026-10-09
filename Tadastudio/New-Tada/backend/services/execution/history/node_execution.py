"""Node execution CRUD operations.

This module handles creating, updating, and retrieving node execution records
in the execution history database.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from backend.services.database import get_db
from backend.models import NodeExecution
from backend.services.config import get_logger

from .serialization import make_json_serializable


logger = get_logger("execution.history.node")


def create_node_execution(
    graph_execution_id: str,
    node_id: str,
    node_name: str,
    node_type: str,
    execution_order: Optional[int] = None,
    input_data: Optional[Dict[str, Any]] = None,
    node_metadata: Optional[Dict[str, Any]] = None,
    is_sub_agent: bool = False,
    parent_agent_id: Optional[str] = None,
    review_iteration: Optional[int] = None,
    invocation_index: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a new node execution record and return its data.

    Args:
        graph_execution_id: Parent graph execution ID
        node_id: Unique node identifier
        node_name: Human-readable node name
        node_type: Type of node (e.g., "AGENT", "HTTP_REQUEST")
        execution_order: Execution order (auto-generated if None)
        input_data: Input data for the node
        node_metadata: Additional metadata
        is_sub_agent: Whether this is a sub-agent node
        parent_agent_id: Parent agent's node execution ID (for sub-agents)
        review_iteration: Review iteration number (for multi-iteration review flows)
        invocation_index: Invocation index (for multi-call subagent flows)

    Returns:
        Dictionary with key node execution fields (id, node_id, status, execution_order)

    Raises:
        Exception: If database operation fails
    """
    logger.info(f"[EXEC-HISTORY] Creating node execution for {node_name}")
    logger.debug(
        f"[EXEC-HISTORY] node_id={node_id}, is_sub_agent={is_sub_agent}, "
        f"parent_agent_id={parent_agent_id}"
    )

    with get_db() as db:
        # Calculate execution order if not provided
        if execution_order is None:
            result = db.execute(
                text("""
                    SELECT COALESCE(MAX(execution_order), -1) + 1
                    FROM node_executions
                    WHERE graph_execution_id = :graph_execution_id
                """),
                {"graph_execution_id": graph_execution_id},
            )
            execution_order = result.scalar()

        # Resolve node_config_hash from the node version index
        node_config_hash = None
        try:
            from backend.models.execution.graph_execution import GraphExecution

            graph_exec = (
                db.query(GraphExecution)
                .filter(GraphExecution.id == graph_execution_id)
                .first()
            )
            if graph_exec and graph_exec.graph_definition_id:
                from backend.models.workflows.node_version_index import NodeVersionIndex

                nvi = (
                    db.query(NodeVersionIndex)
                    .filter(
                        NodeVersionIndex.graph_definition_id
                        == graph_exec.graph_definition_id,
                        NodeVersionIndex.node_id == node_id,
                    )
                    .first()
                )
                if nvi:
                    node_config_hash = nvi.config_hash
        except Exception as hash_err:
            logger.debug(
                f"[EXEC-HISTORY] Could not resolve node_config_hash: {hash_err}"
            )

        node_execution = NodeExecution(
            graph_execution_id=graph_execution_id,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            execution_order=execution_order,
            status="pending",
            input_data=make_json_serializable(input_data) if input_data else None,
            node_metadata=make_json_serializable(node_metadata)
            if node_metadata
            else None,
            is_sub_agent=is_sub_agent,
            parent_agent_id=parent_agent_id,
            review_iteration=review_iteration,
            invocation_index=invocation_index,
            node_config_hash=node_config_hash,
        )
        db.add(node_execution)
        db.commit()
        db.refresh(node_execution)

        logger.info(
            f"[EXEC-HISTORY] Created node execution: {node_execution.id} "
            f"for {node_name} (order={execution_order})"
        )

        return {
            "id": str(node_execution.id),
            "node_id": node_execution.node_id,
            "status": node_execution.status,
            "execution_order": node_execution.execution_order,
            "review_iteration": node_execution.review_iteration,
            "invocation_index": node_execution.invocation_index,
        }


def start_node_execution(node_execution_id: str) -> Optional[NodeExecution]:
    """Mark a node execution as started.

    Args:
        node_execution_id: Node execution ID

    Returns:
        Updated NodeExecution object, or None if not found
    """
    with get_db() as db:
        node_execution = (
            db.query(NodeExecution)
            .filter(NodeExecution.id == node_execution_id)
            .first()
        )
        if not node_execution:
            logger.warning(
                f"[EXEC-HISTORY] Node execution not found: {node_execution_id}"
            )
            return None

        node_execution.status = "running"
        node_execution.start_time = datetime.now(timezone.utc)

        db.commit()
        db.refresh(node_execution)

        logger.info(
            f"[EXEC-HISTORY] Started node execution: {node_execution_id} "
            f"({node_execution.node_name})"
        )
        return node_execution


def complete_node_execution(
    node_execution_id: str,
    status: str = "completed",
    output_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    token_counts: Optional[Dict[str, Any]] = None,
    llm_metadata: Optional[Dict[str, Any]] = None,
    message_structure: Optional[Dict[str, Any]] = None,
    tool_metadata: Optional[Dict[str, Any]] = None,
    orchestration_metadata: Optional[Dict[str, Any]] = None,
    memory_metadata: Optional[Dict[str, Any]] = None,
    environment_metadata: Optional[Dict[str, Any]] = None,
    node_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[NodeExecution]:
    """Mark a node execution as completed with enhanced metadata.

    This method has been refactored to reduce complexity by extracting
    update logic into separate helper functions.

    Args:
        node_execution_id: Node execution ID
        status: Final status (default: "completed")
        output_data: Output data from node execution
        error_message: Error message if execution failed
        token_counts: Token usage counts
        llm_metadata: LLM-specific metadata (model, costs, performance)
        message_structure: Message structure metadata
        tool_metadata: Tool usage metadata
        orchestration_metadata: Orchestration metadata
        memory_metadata: Memory usage metadata
        environment_metadata: Environment metadata
        node_metadata: Additional node-specific metadata (e.g., interrupt payload)

    Returns:
        Updated NodeExecution object, or None if not found
    """
    with get_db() as db:
        node_execution = (
            db.query(NodeExecution)
            .filter(NodeExecution.id == node_execution_id)
            .first()
        )
        if not node_execution:
            logger.warning(
                f"[EXEC-HISTORY] Node execution not found: {node_execution_id}"
            )
            return None

        # Update basic fields
        _update_basic_fields(node_execution, status, output_data, error_message)

        # Update token counts
        if token_counts:
            _update_token_counts(node_execution, token_counts)

        # Update LLM metadata and costs
        if llm_metadata:
            _update_llm_metadata(node_execution, llm_metadata)

        # Update enhanced metadata
        _update_enhanced_metadata(
            node_execution,
            message_structure,
            tool_metadata,
            orchestration_metadata,
            memory_metadata,
            environment_metadata,
        )

        # Update node metadata (for interrupt payloads, etc.)
        if node_metadata is not None:
            if node_execution.node_metadata:
                # Merge with existing metadata
                existing = dict(node_execution.node_metadata)
                existing.update(node_metadata)
                node_execution.node_metadata = existing
            else:
                node_execution.node_metadata = node_metadata

        db.commit()
        db.refresh(node_execution)

        logger.info(
            f"[EXEC-HISTORY] Completed node execution: {node_execution_id} "
            f"({node_execution.node_name}) with status={status}"
        )
        return node_execution


def _update_basic_fields(
    node_execution: NodeExecution,
    status: str,
    output_data: Optional[Dict[str, Any]],
    error_message: Optional[str],
) -> None:
    """Update basic execution fields (status, times, output, errors).

    Args:
        node_execution: NodeExecution instance to update
        status: New status
        output_data: Output data
        error_message: Error message
    """
    node_execution.status = status
    node_execution.end_time = datetime.now(timezone.utc)

    # Calculate duration
    if node_execution.start_time:
        duration = (node_execution.end_time - node_execution.start_time).total_seconds()
        node_execution.duration_seconds = duration

    # Set output data
    if output_data is not None:
        node_execution.output_data = make_json_serializable(output_data)

    # Set error message
    if error_message:
        node_execution.error_message = error_message


def _update_token_counts(
    node_execution: NodeExecution, token_counts: Dict[str, Any]
) -> None:
    """Update token counting fields.

    Args:
        node_execution: NodeExecution instance to update
        token_counts: Token counts dictionary
    """
    node_execution.input_tokens = token_counts.get("input_tokens")
    node_execution.output_tokens = token_counts.get("output_tokens")
    node_execution.total_tokens = token_counts.get("total_tokens")
    node_execution.token_metadata = token_counts.get("metadata")


def _update_llm_metadata(
    node_execution: NodeExecution, llm_metadata: Dict[str, Any]
) -> None:
    """Update LLM metadata including costs and performance metrics.

    Args:
        node_execution: NodeExecution instance to update
        llm_metadata: LLM metadata dictionary
    """
    node_execution.llm_metadata = make_json_serializable(llm_metadata)

    # Update cost fields if available
    if llm_metadata.get("total_cost"):
        node_execution.total_cost = llm_metadata["total_cost"]
        node_execution.prompt_cost = llm_metadata.get("prompt_cost")
        node_execution.completion_cost = llm_metadata.get("completion_cost")

    # Update performance metrics
    if llm_metadata.get("tokens_per_second"):
        node_execution.tokens_per_second = llm_metadata["tokens_per_second"]
    if llm_metadata.get("time_to_first_token"):
        node_execution.time_to_first_token = llm_metadata["time_to_first_token"]


def _update_enhanced_metadata(
    node_execution: NodeExecution,
    message_structure: Optional[Dict[str, Any]],
    tool_metadata: Optional[Dict[str, Any]],
    orchestration_metadata: Optional[Dict[str, Any]],
    memory_metadata: Optional[Dict[str, Any]],
    environment_metadata: Optional[Dict[str, Any]],
) -> None:
    """Update enhanced metadata fields for trace viewer.

    Args:
        node_execution: NodeExecution instance to update
        message_structure: Message structure metadata
        tool_metadata: Tool metadata
        orchestration_metadata: Orchestration metadata
        memory_metadata: Memory metadata
        environment_metadata: Environment metadata
    """
    if message_structure:
        node_execution.message_structure = make_json_serializable(message_structure)

    if tool_metadata:
        node_execution.tool_metadata = make_json_serializable(tool_metadata)

    if orchestration_metadata:
        node_execution.orchestration_metadata = make_json_serializable(
            orchestration_metadata
        )

    if memory_metadata:
        node_execution.memory_metadata = make_json_serializable(memory_metadata)

    if environment_metadata:
        node_execution.environment_metadata = make_json_serializable(
            environment_metadata
        )


def get_node_executions(graph_execution_id: str) -> List[Dict[str, Any]]:
    """Get all node executions for a graph execution.

    Args:
        graph_execution_id: Parent graph execution ID

    Returns:
        List of node execution dictionaries
    """
    with get_db() as db:
        node_executions = (
            db.query(NodeExecution)
            .filter(NodeExecution.graph_execution_id == graph_execution_id)
            .order_by(NodeExecution.execution_order)
            .all()
        )

        result = []
        for node_exec in node_executions:
            result.append(
                {
                    "id": str(node_exec.id),
                    "node_id": node_exec.node_id,
                    "node_name": node_exec.node_name,
                    "node_type": node_exec.node_type,
                    "execution_order": node_exec.execution_order,
                    "status": node_exec.status,
                    "start_time": node_exec.start_time,
                    "end_time": node_exec.end_time,
                    "duration_seconds": node_exec.duration_seconds,
                    "input_data": node_exec.input_data,
                    "output_data": node_exec.output_data,
                    "error_message": node_exec.error_message,
                    "is_sub_agent": node_exec.is_sub_agent,
                    "parent_agent_id": node_exec.parent_agent_id,
                    "node_metadata": node_exec.node_metadata,
                    "invocation_index": node_exec.invocation_index,
                }
            )

        logger.debug(
            f"[EXEC-HISTORY] Retrieved {len(result)} node executions for "
            f"graph execution {graph_execution_id}"
        )
        return result


def get_running_sub_agents(graph_execution_id: str) -> List[Dict[str, Any]]:
    """Get all running sub-agents for a graph execution.

    Args:
        graph_execution_id: Parent graph execution ID

    Returns:
        List of running sub-agent dictionaries
    """
    with get_db() as db:
        running_sub_agents = (
            db.query(NodeExecution)
            .filter(
                NodeExecution.graph_execution_id == graph_execution_id,
                NodeExecution.is_sub_agent,
                NodeExecution.status == "running",
            )
            .all()
        )

        result = []
        for node_exec in running_sub_agents:
            result.append(
                {
                    "id": str(node_exec.id),
                    "node_id": node_exec.node_id,
                    "node_name": node_exec.node_name,
                    "start_time": node_exec.start_time,
                    "is_sub_agent": True,
                }
            )

        logger.debug(
            f"[EXEC-HISTORY] Found {len(result)} running sub-agents for "
            f"graph execution {graph_execution_id}"
        )
        return result


def get_all_running_nodes(graph_execution_id: str) -> List[Dict[str, Any]]:
    """Get all running nodes (including sub-agents) for a graph execution.

    Args:
        graph_execution_id: Parent graph execution ID

    Returns:
        List of running node dictionaries
    """
    with get_db() as db:
        running_nodes = (
            db.query(NodeExecution)
            .filter(
                NodeExecution.graph_execution_id == graph_execution_id,
                NodeExecution.status == "running",
            )
            .all()
        )

        result = []
        for node_exec in running_nodes:
            result.append(
                {
                    "id": str(node_exec.id),
                    "node_id": node_exec.node_id,
                    "node_name": node_exec.node_name,
                    "start_time": node_exec.start_time,
                    "is_sub_agent": getattr(node_exec, "is_sub_agent", False),
                }
            )

        logger.debug(
            f"[EXEC-HISTORY] Found {len(result)} running nodes for "
            f"graph execution {graph_execution_id}"
        )
        return result


def update_node_execution_metadata(
    node_execution_id: str,
    update_data: Dict[str, Any],
) -> Optional[NodeExecution]:
    """Update node execution metadata without completing it.

    This allows updating status, output_data, and node_metadata fields
    without setting end_time or marking the execution as completed.
    Useful for tracking pending review state.

    Args:
        node_execution_id: Node execution ID
        update_data: Dictionary with fields to update. Supported fields:
            - status: New status (e.g., "pending_review", "running")
            - output_data: Output data dictionary
            - node_metadata: Metadata dictionary (merged with existing)

    Returns:
        Updated NodeExecution object, or None if not found
    """
    with get_db() as db:
        node_execution = (
            db.query(NodeExecution)
            .filter(NodeExecution.id == node_execution_id)
            .first()
        )
        if not node_execution:
            logger.warning(
                f"[EXEC-HISTORY] Node execution not found for update: {node_execution_id}"
            )
            return None

        # Update status if provided
        if "status" in update_data:
            node_execution.status = update_data["status"]
            logger.debug(f"[EXEC-HISTORY] Updated status to: {update_data['status']}")

        # Update output_data if provided
        if "output_data" in update_data:
            node_execution.output_data = make_json_serializable(
                update_data["output_data"]
            )

        # Update node_metadata if provided (merge with existing)
        if "node_metadata" in update_data:
            new_metadata = update_data["node_metadata"]
            if node_execution.node_metadata:
                existing = dict(node_execution.node_metadata)
                existing.update(new_metadata)
                node_execution.node_metadata = make_json_serializable(existing)
            else:
                node_execution.node_metadata = make_json_serializable(new_metadata)

        db.commit()
        db.refresh(node_execution)

        logger.info(
            f"[EXEC-HISTORY] Updated node execution metadata: {node_execution_id} "
            f"({node_execution.node_name})"
        )
        return node_execution


def get_node_execution_by_node_id(
    graph_execution_id: str, node_id: str
) -> Optional[Dict[str, Any]]:
    """Get a node execution by graph execution ID and node ID.

    Args:
        graph_execution_id: Parent graph execution ID
        node_id: Node identifier

    Returns:
        Node execution dictionary, or None if not found
    """
    logger.debug(
        f"[EXEC-HISTORY] Querying node execution by node_id: {node_id} "
        f"in execution: {graph_execution_id}"
    )

    with get_db() as db:
        node_execution = (
            db.query(NodeExecution)
            .filter(
                NodeExecution.graph_execution_id == graph_execution_id,
                NodeExecution.node_id == node_id,
            )
            .first()
        )

        if not node_execution:
            logger.warning(
                f"[EXEC-HISTORY] Node execution not found for node_id: {node_id}"
            )
            return None

        logger.info(
            f"[EXEC-HISTORY] Found node execution: {node_execution.node_name} "
            f"with duration: {node_execution.duration_seconds}"
        )

        return {
            "id": node_execution.id,
            "graph_execution_id": node_execution.graph_execution_id,
            "node_id": node_execution.node_id,
            "node_name": node_execution.node_name,
            "node_type": node_execution.node_type,
            "status": node_execution.status,
            "start_time": node_execution.start_time,
            "end_time": node_execution.end_time,
            "duration_seconds": node_execution.duration_seconds,
            "input_data": node_execution.input_data,
            "output_data": node_execution.output_data,
            "error_message": node_execution.error_message,
            "execution_order": node_execution.execution_order,
            "input_tokens": node_execution.input_tokens,
            "output_tokens": node_execution.output_tokens,
            "total_tokens": node_execution.total_tokens,
            "token_metadata": node_execution.token_metadata,
            "is_sub_agent": node_execution.is_sub_agent,
            "parent_agent_id": node_execution.parent_agent_id,
            "created_at": node_execution.created_at,
            "updated_at": node_execution.updated_at,
        }


def create_review_node_execution(
    graph_execution_id: str,
    agent_node_id: str,
    agent_node_name: str,
    review_mode: str,
    iteration: int,
    max_iterations: int,
    approved: bool,
    feedback: Optional[str],
    agent_output: str,
    review_prompt: Optional[str] = None,
    reviewer_model: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    llm_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a node_execution record for a completed review.

    This creates a separate node_execution entry for each review iteration,
    making reviews visible in the execution timeline.

    Args:
        graph_execution_id: Parent graph execution ID
        agent_node_id: The agent node that was reviewed
        agent_node_name: Name of the agent node
        review_mode: "human" or "llm"
        iteration: Current review iteration (1-based)
        max_iterations: Maximum allowed iterations
        approved: Whether the review was approved
        feedback: Reviewer feedback (if rejected)
        agent_output: The agent output that was reviewed
        review_prompt: The review criteria/prompt
        reviewer_model: Model used for LLM review (if applicable)
        duration_seconds: Time taken for the review
        llm_metadata: Optional LLM review metadata (contains raw_response, model, usage, etc.)

    Returns:
        Dictionary with node execution data
    """
    # Use same node ID format as LangGraph (builder.py:343) for consistency
    review_node_id = f"{agent_node_id}_review"

    output_data = {
        "approved": approved,
        "feedback": feedback,
        "iteration": iteration,
        "max_iterations": max_iterations,
        "agent_output_reviewed": agent_output[:1000] if agent_output else None,
        "llm_metadata": llm_metadata,
    }

    node_metadata = {
        "review_mode": review_mode,
        "reviewer_model": reviewer_model,
        "review_prompt": review_prompt,
        "parent_agent_node_id": agent_node_id,
    }

    input_data = {
        "agent_output": agent_output,
        "review_prompt": review_prompt,
    }

    logger.info(
        f"[EXEC-HISTORY] Creating review node execution for {agent_node_name} "
        f"(iteration {iteration}, approved={approved})"
    )

    with get_db() as db:
        # Calculate execution order
        result = db.execute(
            text("""
                SELECT COALESCE(MAX(execution_order), -1) + 1
                FROM node_executions
                WHERE graph_execution_id = :graph_execution_id
            """),
            {"graph_execution_id": graph_execution_id},
        )
        execution_order = result.scalar()

        now = datetime.now(timezone.utc)

        node_execution = NodeExecution(
            graph_execution_id=graph_execution_id,
            node_id=review_node_id,
            node_name=f"Review: {agent_node_name} (Iteration {iteration})",
            node_type="REVIEW",
            execution_order=execution_order,
            status="completed",
            input_data=make_json_serializable(input_data),
            output_data=make_json_serializable(output_data),
            node_metadata=make_json_serializable(node_metadata),
            start_time=now,
            end_time=now,
            duration_seconds=duration_seconds or 0.0,
            is_sub_agent=False,
            parent_agent_id=None,
        )

        db.add(node_execution)
        db.commit()
        db.refresh(node_execution)

        logger.info(
            f"[EXEC-HISTORY] Created review node execution: {node_execution.id} "
            f"(order={execution_order})"
        )

        return {
            "id": str(node_execution.id),
            "node_id": node_execution.node_id,
            "node_name": node_execution.node_name,
            "node_type": node_execution.node_type,
            "status": node_execution.status,
            "execution_order": node_execution.execution_order,
            "output_data": node_execution.output_data,
        }
