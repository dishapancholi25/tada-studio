"""Analytics API – read-only workflow metrics."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.services.analytics import (
    WorkflowNotFoundError,
    get_application_insights,
    get_workflow_metrics,
    get_workflow_performance,
    get_workflow_run_metrics,
)
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization import require_workflow_access_by_id

from .schemas import (
    ApplicationInsightsResponse,
    WorkflowMetricsResponse,
    WorkflowPerformanceResponse,
    WorkflowRunMetricsResponse,
)

router = APIRouter(
    prefix="/api/analytics",
    tags=["analytics"],
    dependencies=[
        Depends(require_active_user),
        Depends(require_scope("workflow:*:read")),
    ],
)


@router.get("/workflows/{workflow_id}/metrics", response_model=WorkflowMetricsResponse)
async def get_metrics(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
) -> WorkflowMetricsResponse:
    """Return the product-quality and usage metrics for one workflow."""
    try:
        uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="workflow_id must be a valid UUID")
    require_workflow_access_by_id(current_user, workflow_id)
    try:
        result = get_workflow_metrics(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowMetricsResponse(**result)


@router.get("/workflows/{workflow_id}/insights", response_model=ApplicationInsightsResponse)
async def get_insights(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
) -> ApplicationInsightsResponse:
    """Return monthly Documents/Queries/Sessions counts for one workflow."""
    try:
        uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="workflow_id must be a valid UUID")
    require_workflow_access_by_id(current_user, workflow_id)
    try:
        result = get_application_insights(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return ApplicationInsightsResponse(**result)


@router.get("/workflows/{workflow_id}/performance", response_model=WorkflowPerformanceResponse)
async def get_performance(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
) -> WorkflowPerformanceResponse:
    """Return latency + reliability metrics for one workflow's last 30 days."""
    require_workflow_access_by_id(current_user, workflow_id)
    try:
        result = get_workflow_performance(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowPerformanceResponse(**result)


@router.get("/workflows/{workflow_id}/run-metrics", response_model=WorkflowRunMetricsResponse)
async def get_run_metrics(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
) -> WorkflowRunMetricsResponse:
    """Return the 5 run-dashboard metrics (today/active/failed/success-rate/volume trend)."""
    try:
        uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="workflow_id must be a valid UUID")
    require_workflow_access_by_id(current_user, workflow_id)
    try:
        result = get_workflow_run_metrics(workflow_id)
    except WorkflowNotFoundError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowRunMetricsResponse(**result)
