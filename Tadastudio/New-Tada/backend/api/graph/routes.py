"""Graph API routes.

This module defines all API endpoints for graph management, node operations,
execution, and configuration.
"""

import logging
import secrets
from typing import Any, Dict, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from backend.models import Workflow, WorkflowMembership
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization.helpers import (
    require_execution_access,
    require_workflow_access,
)
from backend.services.database import get_db
from backend.services.dependency_injection import get_graph_manager
from backend.services.guardrails.ssrf_mcp import BLOCKED_MESSAGE as SSRF_BLOCKED_MESSAGE

from ..auth.dependencies import get_current_user, require_active_user
from .constants import DEFAULT_USERNAME
from .dependencies import get_user_identifier
from .handlers import (
    connection_crud,
    execution,
    export_python,
    file_upload,
    graph_crud,
    llm_config,
    node_crud,
    template_upload,
    templates,
    validation,
)
from .models import (
    ChatRequest,
    CreateConnectionRequest,
    CreateGraphRequest,
    CreateNodeRequest,
    CreateSubAgentRequest,
    DeleteConnectionRequest,
    DuplicateWorkflowRequest,
    GraphExecutionRequest,
    ImportRawWorkflowRequest,
    LLMConfigRequest,
    NodeConfigRequest,
    TestLLMRequest,
    UpdateNodeRequest,
    UpdateWorkflowDescriptionRequest,
    UpdateWorkflowNameRequest,
)

# Public router - no auth required (used for health probes)
public_router = APIRouter(prefix="/api/graph", tags=["graph"])

# Create main router with require_active_user dependency
router = APIRouter(
    prefix="/api/graph", tags=["graph"], dependencies=[Depends(require_active_user)]
)


# ============================================================================
# Health & Utilities
# ============================================================================


@public_router.get("/health")
async def health_check():
    """Health check endpoint."""
    from datetime import datetime

    from backend.services.dependency_injection import (
        get_execution_engine,
        get_graph_manager,
    )

    return {
        "success": True,
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_graphs": len(get_graph_manager().active_graphs),
        "active_executions": len(get_execution_engine().active_executions),
        "total_executions": len(get_execution_engine().execution_history),
    }


@router.get("/types")
async def get_node_types():
    """Get available node types."""
    from backend.models.workflow import NodeType

    from .constants import NODE_TYPE_DESCRIPTIONS

    return {
        "success": True,
        "node_types": [
            {
                "value": node_type.value,
                "label": node_type.value.title(),
                "description": NODE_TYPE_DESCRIPTIONS.get(node_type.value, "Node type"),
            }
            for node_type in NodeType
        ],
    }


# ============================================================================
# Graph Management
# ============================================================================


@router.get("/list", dependencies=[Depends(require_scope("workflow:*:read"))])
async def list_graphs(current_user: Dict[str, Any] = Depends(get_current_user)):
    """List graphs that belong to or are shared with the current user."""
    return await graph_crud.handle_list_graphs(current_user)


@router.post("/create", dependencies=[Depends(require_scope("workflow:*:write"))])
async def create_graph(
    request: CreateGraphRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new graph."""
    return await graph_crud.handle_create_graph(request, current_user)


@router.post("/import-raw", dependencies=[Depends(require_scope("workflow:*:write"))])
async def import_raw_workflow(
    request: ImportRawWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Import a workflow by directly storing the raw JSON definition."""
    return await graph_crud.handle_import_raw_workflow(request, current_user)


@router.get("/executions")
async def list_executions(
    limit: int = 50,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List recent executions visible to the caller."""
    return await execution.handle_list_executions(limit, current_user)


@router.post("/{graph_name}/duplicate", dependencies=[Depends(require_scope("workflow:*:write"))])
async def duplicate_workflow(
    graph_name: str,
    request: DuplicateWorkflowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Duplicate a workflow with a new name."""
    return await graph_crud.handle_duplicate_workflow(graph_name, request, current_user)


@router.get("/{graph_name}", dependencies=[Depends(require_scope("workflow:*:read"))])
async def get_graph(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a specific graph."""
    return await graph_crud.handle_get_graph(graph_name, current_user)


@router.get("/by-id/{workflow_id}", dependencies=[Depends(require_scope("workflow:*:read"))])
async def get_graph_by_workflow_id(
    workflow_id: str,
    version: Optional[int] = None,
    graph_definition_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a graph by workflow ID instead of name.

    Optional query params to load a specific version:
        - version: version number (e.g. ?version=3)
        - graph_definition_id: specific graph definition UUID
    """
    return await graph_crud.handle_get_graph_by_id(
        workflow_id,
        current_user,
        version=version,
        graph_definition_id=graph_definition_id,
    )


@router.get("/by-id/{workflow_id}/versions", dependencies=[Depends(require_scope("workflow:*:read"))])
async def get_workflow_versions(
    workflow_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get all versions of a workflow by workflow ID."""
    return await graph_crud.handle_get_workflow_versions(workflow_id, current_user)


@router.delete("/{graph_name}", dependencies=[Depends(require_scope("workflow:*:write"))])
async def delete_graph(
    graph_name: str,
    username: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a graph from both database and file system."""
    return await graph_crud.handle_delete_graph(graph_name, username, current_user)


@router.post("/save/{graph_name}")
async def save_graph(
    graph_name: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Save a graph to disk."""
    return await graph_crud.handle_save_graph(graph_name, current_user)


@router.post("/reload/{graph_name}")
async def reload_graph(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),  # noqa: B008
):
    """Force reload a graph from disk, bypassing cache."""
    return await graph_crud.handle_reload_graph(graph_name, current_user)


@router.post("/batch-update")
async def batch_update_graph(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Apply multiple graph changes in a single transaction."""
    return await graph_crud.handle_batch_update(request, current_user)


@router.put("/{graph_name}/name", dependencies=[Depends(require_scope("workflow:*:write"))])
async def update_workflow_name(
    graph_name: str,
    request: UpdateWorkflowNameRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update a workflow's name."""
    return await graph_crud.handle_update_workflow_name(
        graph_name, request, current_user
    )


@router.put("/{graph_name}/description", dependencies=[Depends(require_scope("workflow:*:write"))])
async def update_workflow_description(
    graph_name: str,
    request: UpdateWorkflowDescriptionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update a workflow's description."""
    return await graph_crud.handle_update_workflow_description(
        graph_name, request, current_user
    )


@router.get("/state/{graph_name}")
async def get_graph_state(
    graph_name: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current graph state for real-time GUI updates."""
    return await node_crud.handle_get_graph_state(graph_name, current_user)


# ============================================================================
# Node Management
# ============================================================================


@router.post("/node/create")
async def create_node(
    request: CreateNodeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new node in a graph."""
    return await node_crud.handle_create_node(request, current_user)


@router.post("/node/create-sub-agent")
async def create_sub_agent(
    request: CreateSubAgentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a sub-agent for an orchestrator."""
    return await node_crud.handle_create_sub_agent(request, current_user)


@router.put("/node/update")
async def update_node(
    request: UpdateNodeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update a node in a graph."""
    return await node_crud.handle_update_node(request, current_user)


@router.delete("/node/{graph_name}/{node_id}")
async def delete_node(
    graph_name: str,
    node_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a node from a graph."""
    require_workflow_access(current_user, graph_name)
    return await node_crud.handle_delete_node(graph_name, node_id)


@router.get("/node/{graph_name}/{node_id}")
async def get_node(
    graph_name: str,
    node_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a specific node from a graph."""
    return await node_crud.handle_get_node(graph_name, node_id, current_user)


@router.put("/node/configure")
async def configure_node(
    request: NodeConfigRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Configure node-specific settings."""
    require_workflow_access(current_user, request.graph_name)
    return await node_crud.handle_configure_node(request)


@router.get("/graph/{graph_name}/agents")
async def get_graph_agents(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get all agent nodes in a graph with their LLM configurations."""
    require_workflow_access(current_user, graph_name)
    return await node_crud.handle_get_graph_agents(graph_name)


# ============================================================================
# Node Template Assets
# ============================================================================


@router.post("/node/{graph_name}/{node_id}/template")
async def upload_node_template(
    graph_name: str,
    node_id: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload a custom Word template for a FILE_WRITE node."""
    return await template_upload.handle_upload_node_template(
        graph_name, node_id, file, current_user
    )


@router.delete("/node/{graph_name}/{node_id}/template")
async def delete_node_template(
    graph_name: str,
    node_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete the custom Word template from a FILE_WRITE node."""
    return await template_upload.handle_delete_node_template(
        graph_name, node_id, current_user
    )


# ============================================================================
# Connection Management
# ============================================================================


@router.post("/connection/create")
async def create_connection(
    request: CreateConnectionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a connection between two nodes."""
    return await connection_crud.handle_create_connection(request, current_user)


@router.delete("/connection/delete")
async def delete_connection(
    request: DeleteConnectionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a connection between two nodes."""
    return await connection_crud.handle_delete_connection(request, current_user)


# ============================================================================
# LLM Configuration
# ============================================================================


@router.get("/llm/providers")
async def get_llm_providers():
    """Get available LLM providers and their supported models."""
    return await llm_config.handle_get_llm_providers()


@router.get("/llm/models/{provider}")
async def get_llm_models(provider: str):
    """Get available models for a specific LLM provider."""
    return await llm_config.handle_get_llm_models(provider)


@router.post("/llm/test")
async def test_llm_connection(request: TestLLMRequest):
    """Test LLM connection and configuration."""
    return await llm_config.handle_test_llm_connection(request)


@router.put("/node/llm/configure")
async def configure_node_llm(
    request: LLMConfigRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Configure LLM settings for an agent node."""
    require_workflow_access(current_user, request.graph_name)
    return await llm_config.handle_configure_node_llm(request)


@router.get("/node/{graph_name}/{node_id}/llm")
async def get_node_llm_config(
    graph_name: str,
    node_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get LLM configuration for an agent node."""
    return await llm_config.handle_get_node_llm_config(
        graph_name, node_id, current_user
    )


# ============================================================================
# Execution
# ============================================================================


@router.post("/execute", dependencies=[Depends(require_scope("workflow:*:execute"))])
async def execute_graph(
    execution_request: GraphExecutionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Execute a graph using the execution engine."""
    return await execution.handle_execute_graph(
        execution_request, current_user, request
    )


@router.get("/execution/{execution_id}/status")
async def get_execution_status(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the status of a graph execution with node execution details."""
    require_execution_access(current_user, execution_id)
    return await execution.handle_get_execution_status(execution_id)


@router.get("/execution/{execution_id}/history")
async def get_execution_history(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get detailed execution history for a graph execution."""
    require_execution_access(current_user, execution_id)
    return await execution.handle_get_execution_history(execution_id)


@router.get("/execution/{execution_id}/agent/{agent_id}/tools")
async def get_agent_tool_executions(
    execution_id: str,
    agent_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get all tool executions for a specific agent within an execution."""
    require_execution_access(current_user, execution_id)
    return await execution.handle_get_agent_tool_executions(execution_id, agent_id)


@router.post("/execution/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cancel a running execution."""
    require_execution_access(current_user, execution_id)
    return await execution.handle_cancel_execution(execution_id)


@router.post("/agent/{graph_name}/{agent_id}/chat")
async def chat_with_agent(
    graph_name: str,
    agent_id: str,
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Chat with agent using LangChain."""
    require_workflow_access(current_user, graph_name)
    return await execution.handle_chat_with_agent(graph_name, agent_id, request)


# ============================================================================
# File Operations
# ============================================================================


@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),  # noqa: B008
):
    """Upload a file for processing by FILE_READ nodes."""
    return await file_upload.handle_upload_file(file, current_user)


@router.get("/file-metadata/{file_path:path}")
async def get_file_metadata(
    file_path: str,
    current_user: Dict[str, Any] = Depends(get_current_user),  # noqa: B008
):
    """Get metadata about a file without processing it."""
    return await file_upload.handle_get_file_metadata(file_path, current_user)


@router.post("/process-file")
async def process_file(
    file_path: str = Form(...),
    extraction_mode: str = Form("auto"),
    output_format: str = Form("markdown"),
    ocr_library: str = Form("easyocr"),
    language: str = Form("en"),
    current_user: Dict[str, Any] = Depends(get_current_user),  # noqa: B008
):
    """Process a file using document service directly."""
    return await file_upload.handle_process_file(
        file_path, current_user, extraction_mode, output_format, ocr_library, language
    )


@router.post("/execute-with-file", dependencies=[Depends(require_scope("workflow:*:execute"))])
async def execute_graph_with_file(
    graph_name: str = Form(...),
    username: str = Form(DEFAULT_USERNAME),
    async_execution: bool = Form(True),
    message: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Execute a graph with optional file input."""
    return await file_upload.handle_execute_with_file(
        graph_name, username, async_execution, message, file, current_user
    )


# ============================================================================
# Workflow File Storage (Persistent)
# ============================================================================


@router.post("/{graph_name}/file")
async def upload_workflow_file(
    graph_name: str,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload and store a file for a workflow (persistent across executions)."""
    from .handlers import workflow_file
    return await workflow_file.handle_upload_workflow_file(graph_name, file, current_user)


@router.get("/{graph_name}/file")
async def get_workflow_file(
    graph_name: str,
    include_content: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get file info for a workflow."""
    from .handlers import workflow_file
    return await workflow_file.handle_get_workflow_file(graph_name, current_user, include_content)


@router.delete("/{graph_name}/file")
async def delete_workflow_file(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete the stored file for a workflow."""
    from .handlers import workflow_file
    return await workflow_file.handle_delete_workflow_file(graph_name, current_user)


@router.get("/{graph_name}/file/content")
async def get_workflow_file_content(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the full file content for a workflow (for RAG processing)."""
    from .handlers import workflow_file
    return await workflow_file.handle_get_workflow_file_content(graph_name, current_user)


# ============================================================================
# Validation & Export
# ============================================================================


@router.get("/validate/{graph_name}")
async def validate_graph(
    graph_name: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Validate a graph for completeness and correctness."""
    return await validation.handle_validate_graph(graph_name, current_user)


@router.get("/export/{graph_name}")
async def export_graph(
    graph_name: str,
    export_format: str = "langgraph",
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Export graph in specified format."""
    return await validation.handle_export_graph(graph_name, export_format, current_user)


@router.get("/export/{graph_name}/python")
async def export_graph_python(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Export graph as a self-contained Python file."""
    return await export_python.handle_export_python(graph_name, current_user)


@router.post("/structured-outputs/validate")
async def validate_structured_output_schema(schema_data: Dict[str, Any]):
    """Validate a structured output schema."""
    return await validation.handle_validate_structured_output_schema(schema_data)


@router.post("/structured-outputs/preview")
async def preview_structured_output_code(schema_data: Dict[str, Any]):
    """Preview the generated Pydantic model code for a schema."""
    return await validation.handle_preview_structured_output_code(schema_data)


# ============================================================================
# Templates
# ============================================================================


@router.get("/templates/tools")
async def get_tool_templates():
    """Get available tool templates."""
    return await templates.handle_get_tool_templates()


@router.get("/templates/agents")
async def get_agent_templates():
    """Get available agent templates with LLM configurations."""
    return await templates.handle_get_agent_templates()


# ============================================================================
# MCP Server Testing
# ============================================================================


@router.post("/test-mcp-server")
async def test_mcp_server(
    request: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
):
    """Test MCP server connection and discover capabilities."""
    from backend.api.graph.handlers.mcp_test import (
        McpServerTestRequest,
        test_mcp_server_connection,
    )

    try:
        user_id = get_user_identifier(current_user)
        mcp_request = McpServerTestRequest(**request)
        result = await test_mcp_server_connection(mcp_request, user_id=user_id)
        # Build a clean response dict to prevent internal info exposure (py/stack-trace-exposure).
        # Never return the original result object — construct a new dict with only safe fields.
        if isinstance(result, dict) and result.get("success"):
            return {
                "success": True,
                "message": result.get("message", "Connection successful"),
                "capabilities": result.get("capabilities"),
                "server_name": result.get("server_name"),
                "tool_count": result.get("tool_count", 0),
            }
        if isinstance(result, dict) and "error" in result:
            logging.getLogger(__name__).warning(
                "MCP server test error: %s", result["error"]
            )
            # Surface known-safe guardrail messages (e.g. SSRF policy blocks) to the
            # caller as-is; everything else falls back to the generic message below
            # to avoid leaking internal details (py/stack-trace-exposure).
            if result["error"] == SSRF_BLOCKED_MESSAGE:
                return {
                    "success": False,
                    "error": SSRF_BLOCKED_MESSAGE,
                    "capabilities": None,
                }
        return {
            "success": False,
            "error": "MCP server connection test failed",
            "capabilities": None,
        }
    except Exception as e:
        logging.getLogger(__name__).error("MCP server test failed: %s", e)
        raise HTTPException(
            status_code=400, detail="Invalid request or MCP server test failed"
        ) from None


# ============================================================================
# Workflow HTTP Trigger Token
# ============================================================================


def _check_workflow_access(user_identifier: str, workflow_id: str) -> None:
    """Verify user owns or is a member of the workflow. Raises 403 if not."""
    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        is_owner = workflow.created_by_user_id == user_identifier
        is_member = (
            db.query(WorkflowMembership)
            .filter(
                WorkflowMembership.workflow_id == workflow_id,
                WorkflowMembership.user_id == user_identifier,
            )
            .first()
            is not None
        )
        if not is_owner and not is_member:
            raise HTTPException(status_code=403, detail="Access denied")


@router.get("/{graph_name}/http-trigger-token")
async def get_workflow_http_trigger_token(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the HTTP trigger token for a workflow.

    Returns the auto-generated ``wf_`` token used to authenticate
    ``Authorization: Bearer`` requests to the HTTP execution endpoints.

    Args:
        graph_name: Name of the workflow
        current_user: Authenticated user (must own or have access to the workflow)

    Returns:
        Workflow trigger token

    Example::

        curl "http://localhost:8000/api/graph/my-workflow/http-trigger-token"
    """
    user_identifier = get_user_identifier(current_user)
    graph = get_graph_manager().get_graph(graph_name)
    if not graph:
        graph = get_graph_manager().load_graph(graph_name, user_identifier)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found")

    workflow_id = getattr(graph, "workflow_id", None)
    if not workflow_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    _check_workflow_access(user_identifier, workflow_id)

    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow or not workflow.http_trigger_token:
            raise HTTPException(
                status_code=404, detail="Workflow trigger token not found"
            )

        return {
            "success": True,
            "token": workflow.http_trigger_token,
            "graph_name": graph_name,
        }


@router.post("/{graph_name}/http-trigger-token/regenerate")
async def regenerate_workflow_http_trigger_token(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Regenerate the HTTP trigger token for a workflow.

    Generates a new ``wf_`` token, invalidating the previous one.

    Args:
        graph_name: Name of the workflow
        current_user: Authenticated user (must own or have access to the workflow)

    Returns:
        New workflow trigger token

    Example::

        curl -X POST "http://localhost:8000/api/graph/my-workflow/http-trigger-token/regenerate"
    """
    user_identifier = get_user_identifier(current_user)
    graph = get_graph_manager().get_graph(graph_name)
    if not graph:
        graph = get_graph_manager().load_graph(graph_name, user_identifier)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_name}' not found")

    workflow_id = getattr(graph, "workflow_id", None)
    if not workflow_id:
        raise HTTPException(status_code=404, detail="Workflow not found")

    _check_workflow_access(user_identifier, workflow_id)

    with get_db() as db:
        workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        new_token = "wf_" + secrets.token_urlsafe(32)
        workflow.http_trigger_token = new_token
        db.commit()

        return {
            "success": True,
            "token": new_token,
            "graph_name": graph_name,
            "message": "Token regenerated successfully. The previous token is now invalid.",
        }
