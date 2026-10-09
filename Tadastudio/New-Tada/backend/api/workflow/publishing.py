"""Workflow publishing API endpoints."""

from datetime import datetime
from typing import Annotated, Any, Dict, List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.workflow.publication import WorkflowPublicationConfig
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization import require_workflow_access

from ...services.config import get_logger
from ...services.workflow.publishing import WorkflowPublishingService
from ...services.workflow.publishing.helpers import (
    ensure_publication_config,
    load_and_validate_published_graph,
    load_and_validate_unpublished_graph,
    load_graph,
    save_graph_with_warning,
    update_graph_timestamps,
    validate_graph_for_publishing,
)
from ...services.workflow.publishing.responses import (
    build_endpoint_url,
    build_publication_config_dict,
    sync_graph_config_from_request,
)
from ..auth.dependencies import get_current_user

# Get logger for this module
logger = get_logger(__name__)
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]

# Create router
publish_router = APIRouter(prefix="/api/publish", tags=["workflow-publishing"])


def get_user_identifier(current_user: Dict[str, Any]) -> str:
    """Extract user identifier from JWT claims.

    For AIPE users (basic auth), uses email.
    For legacy Azure AD users, falls back to sub.
    """
    user_identifier = current_user.get("sub")
    if not user_identifier:
        raise HTTPException(status_code=401, detail="Token missing user identifier")
    return user_identifier


class PublishWorkflowRequest(BaseModel):
    """Request model for publishing a workflow."""

    custom_slug: Optional[str] = Field(
        None, description="Custom URL slug for the endpoint"
    )
    description: str = Field("", description="Description of the published workflow")
    require_authentication: bool = Field(
        True, description="Whether to require authentication token"
    )
    rate_limit: Optional[Dict[str, int]] = Field(
        None, description="Rate limiting configuration"
    )
    allowed_origins: List[str] = Field(
        default_factory=list, description="Allowed CORS origins"
    )
    webhook_url: Optional[str] = Field(
        None, description="Webhook URL for execution completion callbacks"
    )
    input_schema: Optional[Dict[str, Any]] = Field(
        None, description="JSON schema for input validation"
    )


class PublishWorkflowResponse(BaseModel):
    """Response model for workflow publishing."""

    success: bool
    message: str
    graph_name: str
    endpoint_url: str
    publication_config: Dict[str, Any]
    pat_info: str = "Create a Personal Access Token at Settings → API Tokens to authenticate requests"


class PublishedWorkflowInfo(BaseModel):
    """Information about a published workflow."""

    workflow_id: str
    graph_name: str
    is_published: bool
    endpoint_url: str
    custom_slug: Optional[str]
    description: str
    require_authentication: bool
    published_at: Optional[str]
    last_accessed: Optional[str]
    access_count: int
    workflow_updated_at: Optional[str]
    rate_limit: Optional[Dict[str, int]]
    allowed_origins: List[str]
    webhook_url: Optional[str]


@publish_router.post("/workflow/{graph_name}", dependencies=[Depends(require_scope("workflow:*:write"))])
async def publish_workflow(
    graph_name: str,
    request: PublishWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> PublishWorkflowResponse:
    """
    Publish a workflow as an HTTP endpoint.

    Args:
        graph_name: Name of the workflow to publish
        request: Publication configuration
        current_user: Authenticated user

    Returns:
        Publication details including endpoint URL and authentication token
    """
    try:
        graph_name = unquote(graph_name)
        require_workflow_access(current_user, graph_name)
        user_identifier = get_user_identifier(current_user)
        logger.info(
            f"User '{user_identifier}' publishing workflow '{graph_name}' with config: {request.dict()}"
        )

        # Load and validate graph
        graph = load_and_validate_unpublished_graph(graph_name, user_identifier)
        validate_graph_for_publishing(graph)

        # Publish workflow in database
        try:
            published_workflow = WorkflowPublishingService.publish_workflow(
                graph_name=graph_name,
                user_identifier=user_identifier,
                custom_slug=request.custom_slug,
                description=request.description,
                require_authentication=request.require_authentication,
                rate_limit=request.rate_limit,
                allowed_origins=request.allowed_origins,
                webhook_url=request.webhook_url,
                input_schema=request.input_schema,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Update in-memory graph for backwards compatibility
        ensure_publication_config(graph)
        sync_graph_config_from_request(graph, request)
        update_graph_timestamps(graph)
        save_graph_with_warning(graph, user_identifier)

        # Build response using workflow_id
        endpoint_url = build_endpoint_url(
            workflow_id=str(published_workflow.workflow_id),
            custom_slug=request.custom_slug,
        )

        return PublishWorkflowResponse(
            success=True,
            message=f"Workflow '{graph_name}' published successfully. Create a Personal Access Token at Settings → API Tokens to authenticate requests.",
            graph_name=graph_name,
            endpoint_url=endpoint_url,
            publication_config=build_publication_config_dict(
                request, published_workflow
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing workflow '{graph_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


class PublicationStatusResponse(BaseModel):
    """Lightweight response for publication status check."""

    graph_name: str
    is_published: bool


@publish_router.get("/workflow/{graph_name}/status", dependencies=[Depends(require_scope("workflow:*:read"))])
async def get_workflow_publication_status(
    graph_name: str,
    current_user: CurrentUser,
) -> PublicationStatusResponse:
    """
    Lightweight check for whether a workflow is published.

    Only queries the published_workflows table — does NOT load
    the full graph definition. Intended for UI status indicators.
    """
    try:
        graph_name = unquote(graph_name)
        require_workflow_access(current_user, graph_name)
        is_published = WorkflowPublishingService.check_publication_status(graph_name)
        return PublicationStatusResponse(
            graph_name=graph_name,
            is_published=is_published,
        )
    except Exception as e:
        logger.error(f"Error checking publication status for '{graph_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@publish_router.get("/workflow/{graph_name}", dependencies=[Depends(require_scope("workflow:*:read"))])
async def get_workflow_publication(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> PublishedWorkflowInfo:
    """
    Get publication information for a workflow.

    Args:
        graph_name: Name of the workflow
        current_user: Authenticated user

    Returns:
        Publication details
    """
    try:
        graph_name = unquote(graph_name)
        require_workflow_access(current_user, graph_name)
        user_identifier = get_user_identifier(current_user)
        graph = load_graph(graph_name, user_identifier)

        if not graph:
            raise HTTPException(
                status_code=404, detail=f"Workflow '{graph_name}' not found"
            )

        # Check the database for published status (source of truth)
        db_published = WorkflowPublishingService.get_published_workflow(graph_name)

        if db_published:
            # Use database record as source of truth
            endpoint_url = build_endpoint_url(
                workflow_id=str(db_published.workflow_id),
                custom_slug=db_published.custom_slug,
            )
            return PublishedWorkflowInfo(
                workflow_id=str(db_published.workflow_id)
                if db_published.workflow_id
                else (graph.workflow_id or ""),
                graph_name=graph_name,
                is_published=db_published.is_published,
                endpoint_url=endpoint_url,
                custom_slug=db_published.custom_slug,
                description=db_published.description or "",
                require_authentication=db_published.require_authentication,
                published_at=db_published.published_at.isoformat()
                if db_published.published_at
                else None,
                last_accessed=db_published.last_accessed.isoformat()
                if db_published.last_accessed
                else None,
                access_count=db_published.access_count or 0,
                workflow_updated_at=graph.updated_at,
                rate_limit=db_published.rate_limit,
                allowed_origins=db_published.allowed_origins or [],
                webhook_url=db_published.webhook_url,
            )

        # No database record — workflow is not published
        pub_config = graph.publication_config or WorkflowPublicationConfig()
        slug = pub_config.custom_slug or graph_name
        endpoint_url = build_endpoint_url(slug)

        return PublishedWorkflowInfo(
            workflow_id=graph.workflow_id or "",
            graph_name=graph_name,
            is_published=False,
            endpoint_url=endpoint_url,
            custom_slug=pub_config.custom_slug,
            description=pub_config.description,
            require_authentication=pub_config.require_authentication,
            published_at=pub_config.published_at,
            last_accessed=pub_config.last_accessed,
            access_count=pub_config.access_count,
            workflow_updated_at=graph.updated_at,
            rate_limit=pub_config.rate_limit,
            allowed_origins=pub_config.allowed_origins,
            webhook_url=pub_config.webhook_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting workflow publication info for '{graph_name}': {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@publish_router.delete("/workflow/{graph_name}", dependencies=[Depends(require_scope("workflow:*:write"))])
async def unpublish_workflow(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Unpublish a workflow (remove from public access).

    Args:
        graph_name: Name of the workflow to unpublish
        current_user: Authenticated user

    Returns:
        Success confirmation
    """
    try:
        graph_name = unquote(graph_name)
        require_workflow_access(current_user, graph_name)
        user_identifier = get_user_identifier(current_user)
        logger.info(f"Unpublishing workflow '{graph_name}'")

        # Unpublish in database (scoped to the requesting user)
        unpublished = WorkflowPublishingService.unpublish_workflow(
            graph_name, user_identifier=user_identifier
        )
        if not unpublished:
            raise HTTPException(
                status_code=404, detail=f"Published workflow '{graph_name}' not found"
            )

        # Update in-memory graph for backwards compatibility
        graph = load_graph(graph_name, user_identifier)
        if graph:
            ensure_publication_config(graph)
            graph.publication_config.is_published = False
            graph.updated_at = datetime.now().isoformat()
            save_graph_with_warning(graph, user_identifier)

        return {
            "success": True,
            "message": f"Workflow '{graph_name}' unpublished successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unpublishing workflow '{graph_name}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@publish_router.put("/workflow/{graph_name}", dependencies=[Depends(require_scope("workflow:*:write"))])
async def update_workflow_publication(
    graph_name: str,
    request: PublishWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update publication settings for a workflow.

    Args:
        graph_name: Name of the workflow to update
        request: Updated publication configuration
        current_user: Authenticated user

    Returns:
        Updated publication details
    """
    try:
        graph_name = unquote(graph_name)
        require_workflow_access(current_user, graph_name)
        user_identifier = get_user_identifier(current_user)
        logger.info(f"Updating publication settings for workflow '{graph_name}'")

        # Load and validate
        graph = load_and_validate_published_graph(graph_name, user_identifier)

        # Update configuration
        sync_graph_config_from_request(graph, request)
        graph.updated_at = datetime.now().isoformat()

        # Save the graph
        if not save_graph_with_warning(graph, user_identifier):
            raise HTTPException(
                status_code=500, detail="Failed to save updated workflow configuration"
            )

        # Build response
        slug = request.custom_slug or graph_name
        endpoint_url = build_endpoint_url(slug)

        return PublishWorkflowResponse(
            success=True,
            message=f"Workflow '{graph_name}' publication settings updated successfully. Use Personal Access Tokens to authenticate requests.",
            graph_name=graph_name,
            endpoint_url=endpoint_url,
            publication_config=graph.publication_config.to_dict(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error updating workflow publication settings for '{graph_name}': {str(e)}"
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@publish_router.get("/workflows", dependencies=[Depends(require_scope("workflow:*:read"))])
async def list_published_workflows(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get a list of published workflows accessible to the current user.

    Args:
        current_user: Authenticated user

    Returns:
        List of published workflow information accessible to the user
    """
    try:
        user_identifier = get_user_identifier(current_user)
        logger.info(f"User '{user_identifier}' fetching list of published workflows")

        # Get published workflows accessible to this user
        published_workflows_db = (
            WorkflowPublishingService.list_published_workflows_for_user(user_identifier)
        )
        published_workflows = []

        for published_workflow in published_workflows_db:
            endpoint_url = build_endpoint_url(
                workflow_id=str(published_workflow.workflow_id),
                custom_slug=published_workflow.custom_slug,
            )

            # Get workflow updated_at timestamp
            workflow_updated_at = None
            if published_workflow.workflow and published_workflow.workflow.updated_at:
                workflow_updated_at = published_workflow.workflow.updated_at.isoformat()

            published_workflows.append(
                PublishedWorkflowInfo(
                    workflow_id=str(published_workflow.workflow_id),
                    graph_name=published_workflow.graph_name,
                    is_published=published_workflow.is_published,
                    endpoint_url=endpoint_url,
                    custom_slug=published_workflow.custom_slug,
                    description=published_workflow.description,
                    require_authentication=published_workflow.require_authentication,
                    published_at=published_workflow.published_at.isoformat()
                    if published_workflow.published_at
                    else None,
                    last_accessed=published_workflow.last_accessed.isoformat()
                    if published_workflow.last_accessed
                    else None,
                    access_count=published_workflow.access_count,
                    workflow_updated_at=workflow_updated_at,
                    rate_limit=published_workflow.rate_limit,
                    allowed_origins=published_workflow.allowed_origins,
                    webhook_url=published_workflow.webhook_url,
                )
            )

        return {
            "success": True,
            "published_workflows": published_workflows,
            "total_count": len(published_workflows),
        }

    except Exception as e:
        logger.error(f"Error listing published workflows: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
