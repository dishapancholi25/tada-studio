"""API endpoints for managing paused executions."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.services.database import SessionLocal
from ...services.config import get_logger
from ...services.dependency_injection import get_execution_engine
from ...services.execution.control import ExecutionControlService
from ...services.execution.paused.service import PausedExecutionService
from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization.helpers import (
    get_user_identifier,
    require_execution_access,
    require_workflow_access,
    verify_execution_access,
)
from .models import (
    AllPausedExecutionsResponse,
    CancelExecutionResponse,
    CheckpointDataResponse,
    ExecutionStateResponse,
    PauseExecutionResponse,
    PausedExecutionsResponse,
    StopExecutionResponse,
    ManualResumeResponse,
)


# Get logger
logger = get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/api/executions",
    tags=["paused_executions"],
    dependencies=[Depends(require_active_user)],
)


def get_db():
    """
    Database session dependency for FastAPI.

    Yields:
        Session: SQLAlchemy database session

    Note:
        The session is automatically closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_paused_execution_service() -> PausedExecutionService:
    """
    Get the paused execution service instance.

    Returns:
        PausedExecutionService: Initialized service with execution engine

    Raises:
        HTTPException: If execution engine is not available
    """
    try:
        execution_engine = get_execution_engine()
        return PausedExecutionService(execution_engine)
    except Exception as e:
        logger.error(f"[PAUSED-EXEC-API] Execution engine not available: {e}")
        raise HTTPException(status_code=503, detail="Execution engine not available")


def get_execution_control_service() -> ExecutionControlService:
    """Get the execution control service instance."""
    try:
        execution_engine = get_execution_engine()
        return ExecutionControlService(execution_engine)
    except Exception as e:
        logger.error(f"[EXEC-CONTROL-API] Execution engine not available: {e}")
        raise HTTPException(
            status_code=503,
            detail="Execution engine not available",
        )


@router.get("/paused/{graph_name}", response_model=PausedExecutionsResponse, dependencies=[Depends(require_scope("execution:*:read"))])
async def get_paused_executions(
    graph_name: str,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    service: PausedExecutionService = Depends(get_paused_execution_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get all paused executions for a specific graph/workflow with pagination.

    This endpoint retrieves workflow executions that are currently paused at
    checkpoint nodes, allowing users to inspect and manage pending work items.

    Args:
        graph_name: Name of the graph/workflow to query
        skip: Number of records to skip for pagination (default: 0)
        limit: Maximum number of records to return (default: 20, max: 100)
        db: Database session (injected)
        service: Paused execution service (injected)

    Returns:
        Dictionary with paused execution summaries and pagination metadata

    Raises:
        HTTPException: If query fails or service unavailable
    """
    try:
        # Enforce maximum limit
        if limit > 100:
            limit = 100

        # Verify user has access to this workflow
        require_workflow_access(current_user, graph_name)

        logger.info(
            f"[PAUSED-EXEC-API] GET /paused/{graph_name} (skip={skip}, limit={limit})"
        )

        result = service.get_paused_executions_by_graph(db, graph_name, skip, limit)
        return result

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-API] Failed to get paused executions "
            f"for graph '{graph_name}': {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/paused", response_model=AllPausedExecutionsResponse, dependencies=[Depends(require_scope("execution:*:read"))])
async def get_all_paused_executions(
    db: Session = Depends(get_db),
    service: PausedExecutionService = Depends(get_paused_execution_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the paused executions the caller is entitled to see.

    Grouped by workflow name for easy navigation.

    Args:
        db: Database session (injected)
        service: Paused execution service (injected)
        current_user: Authenticated caller, used to scope the results

    Returns:
        Dictionary with total count and executions grouped by graph name

    Raises:
        HTTPException: If query fails or service unavailable
    """
    try:
        logger.info("[PAUSED-EXEC-API] GET /paused (all graphs)")

        # The endpoint previously returned every tenant's paused executions
        # (ISG F-40 row 9). Visibility reuses verify_execution_access, so this
        # list shows exactly the executions the caller could also open through
        # /{execution_id}/state rather than a second, divergent rule.
        user_identifier = get_user_identifier(current_user)
        is_admin = current_user.get("is_admin", False)

        def _is_visible(execution: Any) -> bool:
            if is_admin:
                return True
            try:
                verify_execution_access(user_identifier, execution.id, False)
                return True
            except HTTPException:
                return False

        result = service.get_all_paused_executions(db, is_visible=_is_visible)
        return result

    except Exception as e:
        logger.error(f"[PAUSED-EXEC-API] Failed to get all paused executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/state", response_model=ExecutionStateResponse, dependencies=[Depends(require_scope("execution:*:read"))])
async def get_execution_state(
    execution_id: str,
    db: Session = Depends(get_db),
    service: PausedExecutionService = Depends(get_paused_execution_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the complete state of an execution, including all node executions.
    """
    try:
        require_execution_access(current_user, execution_id)
        logger.info(f"[PAUSED-EXEC-API] GET /{execution_id}/state")

        result = service.get_execution_state(db, execution_id)
        return result

    except ValueError as e:
        # Handle not found errors
        logger.warning(f"[PAUSED-EXEC-API] Execution not found: {execution_id}")
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-API] Failed to get execution state for {execution_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{execution_id}/cancel", response_model=CancelExecutionResponse, dependencies=[Depends(require_scope("execution:*:write"))])
async def cancel_paused_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    service: PausedExecutionService = Depends(get_paused_execution_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Cancel a paused execution."""
    try:
        require_execution_access(current_user, execution_id)
        logger.info(f"[PAUSED-EXEC-API] POST /{execution_id}/cancel")

        result = service.cancel_paused_execution(db, execution_id)
        return result

    except ValueError as e:
        # Handle validation errors (not found, not paused, etc.)
        logger.warning(f"[PAUSED-EXEC-API] Cannot cancel execution {execution_id}: {e}")
        # Determine appropriate status code
        if "not found" in str(e).lower():
            status_code = 404
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=str(e))

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-API] Failed to cancel execution {execution_id}: {e}"
        )
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{execution_id}/stop", response_model=StopExecutionResponse, dependencies=[Depends(require_scope("execution:*:write"))])
async def stop_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    control_service: ExecutionControlService = Depends(get_execution_control_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Forcefully stop an active execution."""
    try:
        require_execution_access(current_user, execution_id)
        logger.info(f"[EXEC-CONTROL-API] POST /{execution_id}/stop")
        return await control_service.request_stop(db, execution_id)
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"[EXEC-CONTROL-API] Failed to stop execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{execution_id}/pause", response_model=PauseExecutionResponse, dependencies=[Depends(require_scope("execution:*:write"))])
async def pause_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    control_service: ExecutionControlService = Depends(get_execution_control_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Request a graceful pause for an active execution."""
    try:
        require_execution_access(current_user, execution_id)
        logger.info(f"[EXEC-CONTROL-API] POST /{execution_id}/pause")
        return await control_service.request_pause(db, execution_id)
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(
            f"[EXEC-CONTROL-API] Failed to pause execution {execution_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{execution_id}/resume-manual",
    response_model=ManualResumeResponse,
    dependencies=[Depends(require_scope("execution:*:write"))],
)
async def resume_manual_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    control_service: ExecutionControlService = Depends(get_execution_control_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Resume an execution that was paused manually by the user."""

    try:
        require_execution_access(current_user, execution_id)
        logger.info(f"[EXEC-CONTROL-API] POST /{execution_id}/resume-manual")
        return await control_service.resume_manual_pause(db, execution_id)
    except ValueError as e:
        message = str(e)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(
            f"[EXEC-CONTROL-API] Failed to resume manual execution {execution_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{execution_id}/checkpoint-data", response_model=CheckpointDataResponse, dependencies=[Depends(require_scope("execution:*:read"))])
async def get_checkpoint_data(
    execution_id: str,
    db: Session = Depends(get_db),
    service: PausedExecutionService = Depends(get_paused_execution_service),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get checkpoint-specific data for resuming an execution."""
    try:
        require_execution_access(current_user, execution_id)
        logger.info(f"[PAUSED-EXEC-API] GET /{execution_id}/checkpoint-data")

        result = service.get_checkpoint_data(db, execution_id)
        return result

    except ValueError as e:
        # Handle validation errors
        logger.warning(
            f"[PAUSED-EXEC-API] Cannot get checkpoint data for "
            f"execution {execution_id}: {e}"
        )
        # Determine appropriate status code
        if "not found" in str(e).lower():
            status_code = 404
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=str(e))

    except Exception as e:
        logger.error(
            f"[PAUSED-EXEC-API] Failed to get checkpoint data "
            f"for execution {execution_id}: {e}"
        )
        raise HTTPException(status_code=500, detail=str(e))
