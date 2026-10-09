"""API endpoints for checkpoint management (LangGraph).

This module provides REST API endpoints for managing workflow checkpoints,
including retrieving checkpoint history, resuming from checkpoints, and
checking checkpoint system status.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.models.execution.graph_execution import GraphExecution
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization import get_user_identifier, require_workflow_access
from backend.services.config import ExecutionConfig, get_logger
from backend.services.database import get_db
from backend.services.dependency_injection import get_execution_engine

from .dependencies import require_langgraph_engine
from .models import CheckpointResponse, CheckpointStatusResponse, ResumeExecutionRequest


def _verify_thread_access(
    thread_id: str, current_user: dict[str, Any]
) -> GraphExecution | None:
    """Verify the authenticated user owns the graph execution for this thread.

    Args:
        thread_id: LangGraph thread ID to verify ownership for.
        current_user: JWT claims dict for the authenticated user.

    Returns:
        The resolved GraphExecution for non-admin users, or None for admins.

    Raises:
        HTTPException: 404 if no execution exists for the thread, or 403 if
            the thread belongs to a different user.
    """
    user_identifier = get_user_identifier(current_user)
    is_admin = bool(current_user.get("is_admin"))
    if is_admin:
        return None

    with get_db() as db:
        execution = (
            db.query(GraphExecution)
            .filter(GraphExecution.thread_id == thread_id)
            .first()
        )
        if not execution:
            raise HTTPException(status_code=404, detail="Thread not found")
        if execution.user_id and execution.user_id != user_identifier:
            raise HTTPException(
                status_code=403, detail="Not authorized to access this thread"
            )
        return execution

# Get logger
logger = get_logger("checkpoint_api")

# Create router
router = APIRouter(
    prefix="/api/checkpoints",
    tags=["checkpoints"],
    dependencies=[Depends(require_active_user)],
)


@router.get(
    "/threads/{thread_id}",
    response_model=list[CheckpointResponse],
    dependencies=[
        Depends(require_langgraph_engine),
        Depends(require_scope("execution:*:read")),
    ],
    summary="Get thread checkpoints",
    description="Retrieve all checkpoints for a specific thread ID",
)
async def get_thread_checkpoints(
    thread_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> list[CheckpointResponse]:
    """Get all checkpoints for a thread.

    Args:
        thread_id: The thread ID to retrieve checkpoints for.

    Returns:
        List[CheckpointResponse]: List of checkpoint data for the thread.

    Raises:
        HTTPException: 501 if engine doesn't support checkpoints, 500 on error.

    Example:
        >>> # GET /api/checkpoints/threads/thread_123
        >>> [
        ...     {
        ...         "checkpoint_id": "cp_1",
        ...         "thread_id": "thread_123",
        ...         "timestamp": "2025-10-19T12:00:00Z",
        ...         "metadata": {"status": "paused"}
        ...     }
        ... ]
    """
    try:
        logger.info(f"[CHECKPOINT-API] Retrieving checkpoints for thread: {thread_id}")

        _verify_thread_access(thread_id, current_user)

        engine = get_execution_engine()

        # Check if engine has checkpoint support
        if not hasattr(engine, "get_checkpoints"):
            logger.error(
                "[CHECKPOINT-API] Engine does not support get_checkpoints method"
            )
            raise HTTPException(
                status_code=501,
                detail="Current execution engine does not support checkpoints",
            )

        checkpoints = engine.get_checkpoints(thread_id)
        logger.info(
            f"[CHECKPOINT-API] Found {len(checkpoints)} checkpoints for thread: {thread_id}"
        )

        return [
            CheckpointResponse(
                checkpoint_id=cp.get("checkpoint_id", ""),
                thread_id=cp.get("thread_id", thread_id),
                timestamp=cp.get("timestamp", ""),
                metadata=cp.get("metadata"),
            )
            for cp in checkpoints
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"[CHECKPOINT-API] Failed to get checkpoints for thread {thread_id}",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve checkpoints: {e!s}",
        ) from e


@router.post(
    "/resume",
    dependencies=[
        Depends(require_langgraph_engine),
        Depends(require_scope("execution:*:write")),
    ],
    summary="Resume from checkpoint",
    description="Resume workflow execution from a specific checkpoint with optional new input",
)
async def resume_from_checkpoint(
    request: ResumeExecutionRequest,
    current_user: dict[str, Any] = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """Resume execution from a checkpoint.

    Args:
        request: Resume request containing graph name, thread ID, checkpoint ID,
                 and optional new input.

    Returns:
        Dict[str, Any]: Resume result with status, thread_id, checkpoint_id, and result.

    Raises:
        HTTPException: 501 if engine doesn't support resumption, 500 on error.

    Example:
        >>> # POST /api/checkpoints/resume
        >>> {
        ...     "graph_name": "my-workflow",
        ...     "thread_id": "thread_123",
        ...     "checkpoint_id": "cp_1",
        ...     "new_input": {"value": "user response"}
        ... }
        >>> # Response:
        >>> {
        ...     "status": "resumed",
        ...     "thread_id": "thread_123",
        ...     "checkpoint_id": "cp_1",
        ...     "result": {...}
        ... }
    """
    logger.info(
        f"[CHECKPOINT-API] Resume request - graph: {request.graph_name}, "
        f"thread: {request.thread_id}, checkpoint: {request.checkpoint_id}"
    )

    if request.new_input:
        logger.debug(f"[CHECKPOINT-API] Resume with new input: {request.new_input}")

    try:
        execution = _verify_thread_access(request.thread_id, current_user)
        workflow_id = require_workflow_access(current_user, request.graph_name)
        if execution is not None and workflow_id is not None:
            if execution.workflow_id:
                thread_matches_graph = execution.workflow_id == workflow_id
            else:
                thread_matches_graph = execution.graph_name == request.graph_name
            if not thread_matches_graph:
                raise HTTPException(
                    status_code=403,
                    detail="Thread does not belong to this graph",
                )

        engine = get_execution_engine()

        # Check if engine has checkpoint support
        if not hasattr(engine, "resume_from_checkpoint"):
            logger.error(
                "[CHECKPOINT-API] Engine does not support resume_from_checkpoint method"
            )
            raise HTTPException(
                status_code=501,
                detail="Current execution engine does not support checkpoint resumption",
            )

        logger.info(
            f"[CHECKPOINT-API] Calling engine.resume_from_checkpoint for thread: {request.thread_id}"
        )

        # Resume execution
        result = await engine.resume_from_checkpoint(
            graph_name=request.graph_name,
            thread_id=request.thread_id,
            checkpoint_id=request.checkpoint_id,
            new_input=request.new_input,
        )

        logger.info(
            f"[CHECKPOINT-API] Resume completed for thread: {request.thread_id}, "
            f"status: {result.get('status', 'unknown')}"
        )

        return {
            "status": "resumed",
            "thread_id": request.thread_id,
            "checkpoint_id": request.checkpoint_id,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"[CHECKPOINT-API] Failed to resume from checkpoint {request.checkpoint_id}",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume from checkpoint: {e!s}",
        ) from e


@router.get(
    "/status",
    response_model=CheckpointStatusResponse,
    dependencies=[Depends(require_scope("execution:*:read"))],
    summary="Get checkpoint status",
    description="Get the current status of the checkpoint system",
)
async def get_checkpoint_status() -> CheckpointStatusResponse:
    """Get checkpoint system status.

    Returns:
        CheckpointStatusResponse: Current checkpoint system configuration and capabilities.

    Example:
        >>> # GET /api/checkpoints/status
        >>> {
        ...     "checkpointing_enabled": true,
        ...     "engine_type": "langgraph",
        ...     "engine_supports_checkpoints": true
        ... }
    """
    logger.debug("[CHECKPOINT-API] Retrieving checkpoint system status")

    return CheckpointStatusResponse(
        checkpointing_enabled=ExecutionConfig.use_checkpointing(),
        engine_type=ExecutionConfig.get_execution_engine_type(),
        engine_supports_checkpoints=True,  # Always true now
    )
