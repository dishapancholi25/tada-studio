"""Library API routes for workflow and agent template management."""

from time import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from backend.api.auth.dependencies import (
    get_current_user,
    require_active_user,
    require_admin,
)
from backend.services.authorization import require_workflow_access_by_id
from backend.services.library import (
    AgentLibraryService,
    LibraryDiscoveryService,
    LibraryService,
)

from .models import (
    AddAgentTemplateRequest,
    AddToLibraryRequest,
    CloneTemplateRequest,
    ImportAgentJSONRequest,
    UpdateTemplateRequest,
)

# Simple in-memory rate limiter for import endpoint
# Maps user_id -> list of timestamps
_import_rate_limiter: Dict[str, List[float]] = {}
_IMPORT_RATE_LIMIT = 10  # requests per window
_IMPORT_WINDOW_SECONDS = 60  # 1 minute


def check_import_rate_limit(user_identifier: str) -> None:
    """Check if user has exceeded import rate limit.

    Args:
        user_identifier: User identifier

    Raises:
        HTTPException: If rate limit exceeded
    """
    current_time = time()
    window_start = current_time - _IMPORT_WINDOW_SECONDS

    # Get or create user's request history
    if user_identifier not in _import_rate_limiter:
        _import_rate_limiter[user_identifier] = []

    # Remove old timestamps outside the window
    _import_rate_limiter[user_identifier] = [
        ts for ts in _import_rate_limiter[user_identifier] if ts > window_start
    ]

    # Check if limit exceeded
    if len(_import_rate_limiter[user_identifier]) >= _IMPORT_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {_IMPORT_RATE_LIMIT} imports per {_IMPORT_WINDOW_SECONDS} seconds.",
        )

    # Add current request
    _import_rate_limiter[user_identifier].append(current_time)


# Create router
router = APIRouter(
    prefix="/api/library", tags=["library"], dependencies=[Depends(require_active_user)]
)


@router.get("/templates")
async def list_templates(
    search: Optional[str] = Query(None, description="Search term"),
    category: Optional[str] = Query(None, description="Filter by category"),
    complexity: Optional[str] = Query(None, description="Filter by complexity"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: Optional[int] = Query(None, description="Maximum results"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    List workflow templates with optional filtering and search.

    Query parameters:
    - search: Search in name, description, or tags
    - category: Filter by category
    - complexity: Filter by complexity (beginner/intermediate/advanced)
    - sort_by: Field to sort by (created_at, name, category, complexity, usage_count)
    - sort_order: asc or desc
    - limit: Maximum number of results
    """
    try:
        templates = LibraryService.list_templates(
            search=search,
            category=category,
            complexity=complexity,
            tags=tags,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
        )

        return {"success": True, "templates": templates, "count": len(templates)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing templates: {str(e)}"
        )


@router.get("/agents")
async def list_agents(
    search: Optional[str] = Query(None, description="Search term"),
    category: Optional[str] = Query(None, description="Filter by category"),
    complexity: Optional[str] = Query(None, description="Filter by complexity"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: Optional[int] = Query(None, description="Maximum results"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List agent templates."""
    try:
        agents = AgentLibraryService.list_agents(
            search=search,
            category=category,
            complexity=complexity,
            tags=tags,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
        )
        return {"success": True, "agents": agents, "count": len(agents)}
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error listing agents: {exc}"
        ) from exc


@router.get("/discovery")
async def list_discovery_items(
    search: Optional[str] = Query(None, description="Search term"),
    category: Optional[str] = Query(None, description="Filter by category"),
    complexity: Optional[str] = Query(None, description="Filter by complexity"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    limit: Optional[int] = Query(None, description="Maximum results"),
    count_only: bool = Query(False, description="Return only counts without full data"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return combined agents + workflows honoring shared filters.

    When count_only=True, only returns counts without loading full item data,
    significantly reducing response payload size for category counting.
    """
    try:
        payload = LibraryDiscoveryService.list_items(
            search=search,
            category=category,
            complexity=complexity,
            tags=tags,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            count_only=count_only,
        )
        return {"success": True, **payload}
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error listing library items: {exc}"
        ) from exc


@router.get("/discovery/category-counts")
async def get_all_category_counts(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return counts of agents and workflows for all categories in a single request.

    This endpoint optimizes the common use case of fetching counts for all categories
    by returning them in one request instead of requiring multiple API calls.

    Returns a dictionary mapping each category to its agent and workflow counts.
    """
    try:
        # Define all categories (should match frontend TEMPLATE_CATEGORIES)
        categories = [
            "Finance",
            "Sales",
            "Recruitment",
            "Marketing",
            "Customer Service",
            "Education",
            "Operations",
            "Analytics",
            "Technology",
            "Risk & Compliance",
            "Human Resources",
            "Cybersecurity",
            "General",
        ]

        # Fetch counts for each category
        category_counts = {}
        for category in categories:
            workflow_count = LibraryService.count_templates(category=category)
            agent_count = AgentLibraryService.count_agents(category=category)
            category_counts[category] = {
                "agents": agent_count,
                "workflows": workflow_count,
            }

        return {"success": True, "category_counts": category_counts}
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error fetching category counts: {exc}"
        ) from exc


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Retrieve a single workflow template with its graph definition.
    """
    try:
        template = LibraryService.get_template_with_graph(template_id=template_id)

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return {"success": True, "template": template}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving template: {str(e)}"
        )


@router.get("/templates/{template_id}/dependencies")
async def get_template_dependencies(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Get collection dependencies for a workflow template.

    Returns list of collections referenced by DocumentSearchNode types
    in the workflow, with access status for the current user.
    """
    try:
        user_id = current_user.get("sub")

        dependencies = LibraryService.get_template_dependencies(
            template_id=template_id,
            user_id=user_id,
        )

        if dependencies is None:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "success": True,
            "dependencies": dependencies,
            "count": len(dependencies),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving template dependencies: {str(e)}",
        )


@router.get("/agents/{agent_id}")
async def get_agent_template(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Retrieve a single agent template plus graph data."""
    try:
        agent = AgentLibraryService.get_agent_with_graph(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent template not found")
        return {"success": True, "agent": agent}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving agent template: {exc}"
        ) from exc


@router.get("/template/{template_id}")
async def get_template_alias(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Alias endpoint for retrieving a single workflow template.
    """
    return await get_template(template_id=template_id, current_user=current_user)


@router.get("/templates/by-workflow-name/{workflow_name}")
async def find_template_by_workflow_name(
    workflow_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Find an existing library template by workflow name.

    This checks if a template already exists in the library with the given workflow name,
    using the same logic as the add_to_library endpoint. Useful for prepopulating the
    "Add to Library" dialog when updating an existing template.

    Returns the template metadata if found, or a 404 if no template exists.
    """
    try:
        template = LibraryService.find_template_by_workflow_name(workflow_name)

        if template:
            return {"success": True, "template": template}
        else:
            return {"success": False, "template": None}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error finding template by workflow name: {str(e)}",
        )


@router.post("/templates")
async def add_to_library(
    request: AddToLibraryRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Add a workflow to the library.

    Creates a copy of the workflow with global access and template metadata.
    """
    try:
        # Get user identifier from current_user
        user_identifier = current_user.get("sub")

        # Verify the user owns (or has access to) the source workflow before
        # publishing it globally to the library (ISG Finding 6430 - BOLA).
        require_workflow_access_by_id(current_user, request.workflow_id)

        template_id = LibraryService.add_to_library(
            workflow_id=request.workflow_id,
            name=request.name,
            description=request.description,
            category=request.category,
            tags=request.tags,
            user_identifier=user_identifier,
            complexity=request.complexity,
            icon_color=request.icon_color,
        )

        if template_id:
            return {
                "success": True,
                "template_id": template_id,
                "message": "Workflow added to library successfully",
            }
        else:
            raise HTTPException(
                status_code=400, detail="Failed to add workflow to library"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error adding to library: {str(e)}"
        )


@router.post("/templates/import-csv", dependencies=[Depends(require_admin)])
async def import_templates_from_csv(
    workflows_csv: UploadFile = File(..., description="workflows table CSV export"),
    graph_definitions_csv: UploadFile = File(
        ..., description="graph_definitions table CSV export"
    ),
    workflow_templates_csv: UploadFile = File(
        ..., description="workflow_templates table CSV export"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Import workflow templates from CSV files exported from another database.

    Accepts three CSV files (workflows, graph_definitions, workflow_templates)
    and inserts non-duplicate templates into the library.
    Duplicates are detected by matching name + tags.
    """
    try:
        user_identifier = current_user.get("sub")
        check_import_rate_limit(user_identifier)

        # Validate file extensions
        for upload, label in [
            (workflows_csv, "workflows"),
            (graph_definitions_csv, "graph_definitions"),
            (workflow_templates_csv, "workflow_templates"),
        ]:
            if upload.filename and not upload.filename.endswith(".csv"):
                raise HTTPException(
                    status_code=400,
                    detail=f"{label} file must be a .csv file",
                )

        # Read file contents as strings
        workflows_content = (await workflows_csv.read()).decode("utf-8")
        graph_defs_content = (await graph_definitions_csv.read()).decode("utf-8")
        templates_content = (await workflow_templates_csv.read()).decode("utf-8")

        result = LibraryService.import_templates_from_csv(
            workflows_csv_content=workflows_content,
            graph_definitions_csv_content=graph_defs_content,
            workflow_templates_csv_content=templates_content,
        )

        return {
            "success": True,
            "message": f"Import complete: {result['inserted']} inserted, {result['skipped_duplicates']} skipped",
            **result,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error importing templates from CSV: {str(e)}",
        )


@router.post("/agents")
async def add_agent_to_library(
    request: AddAgentTemplateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Publish a single agent node as a library template."""
    try:
        user_identifier = current_user.get("sub")

        require_workflow_access_by_id(current_user, request.workflow_id)

        template_id = AgentLibraryService.add_agent_to_library(
            workflow_id=request.workflow_id,
            agent_node_id=request.agent_node_id,
            name=request.name,
            description=request.description,
            category=request.category,
            tags=request.tags,
            user_identifier=user_identifier,
            icon_color=request.icon_color,
        )

        if template_id:
            return {
                "success": True,
                "template_id": template_id,
                "message": "Agent added to library successfully",
            }

        raise HTTPException(status_code=400, detail="Failed to add agent to library")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error adding agent to library: {exc}"
        ) from exc


@router.post("/agents/import", dependencies=[Depends(require_admin)])
async def import_agent_from_json(
    request: ImportAgentJSONRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Import an agent from JSON configuration.

    Accepts agent configuration in A2A-inspired format with Agentic Studio extensions.
    Rate limited to 10 requests per minute per user.
    """
    try:
        user_identifier = current_user.get("sub")

        # Check rate limit before processing
        check_import_rate_limit(user_identifier)

        template_id = AgentLibraryService.import_agent_from_json(
            agent_data=request.agent_json,
            user_identifier=user_identifier,
            metadata_override=request.metadata_override,
        )

        if template_id:
            return {
                "success": True,
                "template_id": template_id,
                "message": "Agent imported successfully",
            }

        raise HTTPException(status_code=400, detail="Failed to import agent")
    except ValueError as exc:
        # Validation errors from Pydantic
        raise HTTPException(
            status_code=400, detail=f"Invalid agent JSON: {exc}"
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error importing agent: {exc}"
        ) from exc


@router.post("/agents/{agent_id}/clone")
async def clone_agent_template(
    agent_id: str,
    request: CloneTemplateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Clone an agent template into the user's workspace as a workflow."""
    try:
        user_identifier = current_user.get("sub")
        workspace_id = request.workspace_id or user_identifier

        workflow_id = AgentLibraryService.clone_agent_template(
            agent_id=agent_id,
            user_identifier=user_identifier,
            workspace_id=workspace_id,
            target_name=request.target_name,
        )

        if workflow_id:
            return {
                "success": True,
                "workflow_id": workflow_id,
                "message": "Agent template cloned successfully",
            }

        raise HTTPException(
            status_code=404, detail="Agent template not found or inactive"
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error cloning agent template: {exc}"
        ) from exc


@router.post("/templates/{template_id}/clone")
async def clone_template(
    template_id: str,
    request: CloneTemplateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Clone a template to the user's workspace.

    Creates a new workflow based on the template and increments usage count.
    """
    try:
        # Get user identifier from current_user
        user_identifier = current_user.get("sub")

        # Use provided workspace_id or default to user's email
        workspace_id = request.workspace_id or user_identifier

        workflow_id = LibraryService.clone_template(
            template_id=template_id,
            user_identifier=user_identifier,
            workspace_id=workspace_id,
            target_name=request.target_name,
        )

        if workflow_id:
            return {
                "success": True,
                "workflow_id": workflow_id,
                "message": "Template cloned successfully",
            }
        else:
            raise HTTPException(status_code=404, detail="Template not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cloning template: {str(e)}")


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update template metadata.

    Creates a new version of the template with updated metadata.
    Only the template creator can update their own templates.
    """
    try:
        user_identifier = current_user.get("sub")

        # Reuse the same ownership check as deletion: only the creator may
        # mutate template metadata (ISG Finding 6430 - BOLA).
        if not LibraryService.can_delete_template(
            template_id=template_id, user_identifier=user_identifier
        ):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to modify this template. Only the creator can update their templates.",
            )

        new_template_id = LibraryService.update_template(
            template_id=template_id,
            name=request.name,
            description=request.description,
            category=request.category,
            tags=request.tags,
            complexity=request.complexity,
            icon_color=request.icon_color,
        )

        if new_template_id:
            return {
                "success": True,
                "template_id": new_template_id,
                "message": "Template updated successfully",
            }
        else:
            raise HTTPException(status_code=404, detail="Template not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating template: {str(e)}"
        )


@router.delete("/templates/{template_id}")
async def deactivate_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Deactivate a template (soft delete).

    Marks the template as inactive so it no longer appears in listings.
    Only the template creator can delete their own templates.
    """
    try:
        # Get user identifier from current_user
        user_identifier = current_user.get("sub")

        # Check if user has permission to delete this template
        if not LibraryService.can_delete_template(
            template_id=template_id, user_identifier=user_identifier
        ):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to delete this template. Only the creator can delete their templates.",
            )

        success = LibraryService.deactivate_template(template_id=template_id)

        if success:
            return {"success": True, "message": "Template deactivated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Template not found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deactivating template: {str(e)}"
        )


@router.delete("/agents/{agent_id}")
async def deactivate_agent_template(
    agent_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Deactivate (soft delete) an agent template. Only the creator may delete."""
    try:
        user_identifier = current_user.get("sub")

        if not AgentLibraryService.can_delete_agent_template(agent_id, user_identifier):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to delete this agent template.",
            )

        success = AgentLibraryService.deactivate_agent_template(agent_id)
        if success:
            return {"success": True, "message": "Agent template deleted successfully"}

        raise HTTPException(status_code=404, detail="Agent template not found")

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Error deleting agent template: {exc}"
        ) from exc
