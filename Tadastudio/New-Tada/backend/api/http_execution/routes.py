"""FastAPI routes for HTTP execution API.

This module defines all REST API endpoints for HTTP-triggered workflow execution,
including execution triggering, SSE streaming, and checkpoint resumption.

Authentication is provided via the Authorization: Bearer header with one of:
- Workflow trigger tokens (wf_xxx)
- Personal Access Tokens (na_xxx)
- Azure AD / local JWTs
"""

from typing import Any, Dict, Optional, Union
from urllib.parse import unquote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Security,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.services.auth.scope_enforcer import require_scope
from backend.services.authorization.helpers import require_workflow_access
from backend.services.auth.user_api_token_service import UserAPITokenService
from backend.services.workflow.publishing import WorkflowPublishingService
from backend.services.workflow.publishing.responses import build_endpoint_url
from backend.services.config import get_logger
from backend.services.dependency_injection import get_graph_manager
from backend.services.document_storage import DocumentStorageService
from backend.services.execution.history import ExecutionHistoryService

from .exceptions import HttpExecutionException
from .handlers.checkpoint import checkpoint_handler
from .handlers.execution import http_execution_handler
from .handlers.file_upload import file_upload_handler
from .handlers.sse import sse_handler
from .models import (
    ExecutionInfoResponse,
    HttpExecutionRequest,
    HttpExecutionResponse,
    HttpResumeRequest,
    LatestExecutionResponse,
)
from .services.execution_tracker import execution_tracker
from .utils.output import extract_execution_output
from .utils.request import get_base_url


logger = get_logger(__name__)

# Create router
# Note: require_active_user is NOT applied at the router level because the trigger/*
# endpoints are public-facing API endpoints protected by their own PAT token auth.
# Management endpoints (token CRUD, info, etc.) apply require_active_user individually.
router = APIRouter(prefix="/api/http-execution", tags=["HTTP Execution"])

# Reusable bearer scheme for PAT token extraction from Authorization header.
# auto_error=False so endpoints can still work without a token (unauthenticated access).
_pat_bearer = HTTPBearer(auto_error=False)


def _handle_http_execution_exception(e: HttpExecutionException) -> HTTPException:
    """Convert HttpExecutionException to FastAPI HTTPException.

    Args:
        e: HttpExecutionException to convert

    Returns:
        HTTPException with appropriate status code and detail
    """
    headers = {}

    # Add rate limit headers if applicable
    if hasattr(e, "retry_after"):
        headers["Retry-After"] = str(e.retry_after)
    if hasattr(e, "reset_time") and e.reset_time:
        headers["X-RateLimit-Reset"] = str(e.reset_time)

    return HTTPException(
        status_code=e.status_code,
        detail=e.message,
        headers=headers if headers else None,
    )


@router.post("/trigger/{workflow_identifier}")
async def trigger_http_execution_json(
    workflow_identifier: str,
    execution_request: HttpExecutionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(_pat_bearer),
) -> HttpExecutionResponse:
    """Trigger workflow execution via HTTP request (JSON body).

    This endpoint accepts a JSON payload with a message and optional parameters
    for async execution and timeout configuration.

    Authentication is only required when the workflow is published with
    ``require_authentication=true``. Supply a token via the
    ``Authorization: Bearer`` header. Accepted token types:

    - Workflow trigger token (``wf_xxx``)
    - Personal Access Token (``na_xxx``)
    - Azure AD / local JWT

    Args:
        workflow_identifier: Workflow UUID or custom slug
        execution_request: Request body containing the message
        background_tasks: FastAPI background tasks (not currently used)
        request: The incoming FastAPI request (for client metadata)
        credentials: Optional token supplied as a Bearer token in the Authorization header

    Returns:
        If async_mode=True: Execution ID and status endpoint
        If async_mode=False: The actual workflow output

    Example::

        curl -X POST "http://localhost:8000/api/http-execution/trigger/9d04ad87-..." \\
          -H "Authorization: Bearer wf_abc123..." \\
          -H "Content-Type: application/json" \\
          -d '{"message": "Hello world", "async_mode": false, "timeout": 300}'
    """
    try:
        resolved_token = credentials.credentials if credentials else None
        file_data = execution_request.resolve_file_data()
        return await http_execution_handler.trigger_execution(
            graph_name=workflow_identifier,  # Handler will resolve UUID or slug
            message=execution_request.message,
            file_data=file_data,
            token=resolved_token,
            async_mode=execution_request.async_mode,
            timeout=execution_request.timeout,
            clear_memory=execution_request.clear_memory,
            fastapi_request=request,
        )
    except HttpExecutionException as e:
        raise _handle_http_execution_exception(e)
    except Exception as e:
        logger.error(
            f"[HTTP-EXEC-API] Unexpected error in trigger_http_execution_json: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Check server logs for details.",
        )


@router.post("/trigger-form/{workflow_identifier}")
async def trigger_http_execution_form(
    workflow_identifier: str,
    background_tasks: BackgroundTasks,
    request: Request,
    message: Optional[str] = Form(None, alias="Message"),
    file: Optional[UploadFile] = File(None),
    async_mode: bool = Form(False),
    timeout: int = Form(300),
    clear_memory: bool = Form(False),
    credentials: HTTPAuthorizationCredentials = Security(_pat_bearer),
) -> HttpExecutionResponse:
    """Trigger workflow execution via HTTP request (Form data with optional file upload).

    This endpoint accepts form data including an optional file upload for workflows
    that use FILE_READ nodes.

    Authentication is only required when the workflow is published with
    ``require_authentication=true``. Supply a token via the
    ``Authorization: Bearer`` header (workflow token, PAT, or JWT).

    Args:
        workflow_identifier: Workflow UUID or custom slug
        background_tasks: FastAPI background tasks (not currently used)
        request: The incoming FastAPI request (for client metadata)
        message: Optional message from form data
        file: Optional file upload for FILE_READ nodes
        async_mode: If true, return immediately. If false, wait for results
        timeout: Timeout in seconds for sync mode
        credentials: Optional token supplied as a Bearer token in the Authorization header

    Returns:
        If async_mode=True: Execution ID and status endpoint
        If async_mode=False: The actual workflow output

    Note:
        Provide EITHER message OR file, not both

    Example::

        curl -X POST "http://localhost:8000/api/http-execution/trigger-form/my-workflow" \\
          -H "Authorization: Bearer wf_abc123..." \\
          -F "Message=Hello world" \\
          -F "async_mode=false"
    """
    try:
        # Process file if provided
        file_data = None
        if file:
            file_data = await file_upload_handler.process_uploaded_file(file)

        # Validate input
        file_upload_handler.validate_file_input(message, file_data)

        resolved_token = credentials.credentials if credentials else None
        return await http_execution_handler.trigger_execution(
            graph_name=workflow_identifier,
            message=message,
            file_data=file_data,
            token=resolved_token,
            async_mode=async_mode,
            timeout=timeout,
            clear_memory=clear_memory,
            fastapi_request=request,
        )
    except HttpExecutionException as e:
        raise _handle_http_execution_exception(e)
    except Exception as e:
        logger.error(
            f"[HTTP-EXEC-API] Unexpected error in trigger_http_execution_form: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Check server logs for details.",
        )


@router.post("/trigger-sse/{workflow_identifier}")
async def trigger_http_execution_sse(
    workflow_identifier: str,
    execution_request: HttpExecutionRequest,
    fastapi_request: Request,
    credentials: HTTPAuthorizationCredentials = Security(_pat_bearer),
):
    """Trigger workflow execution with Server-Sent Events for real-time updates.

    This endpoint provides a streaming connection that sends real-time execution
    updates as Server-Sent Events (SSE).

    Authentication is only required when the workflow is published with
    ``require_authentication=true``. Supply a token via the
    ``Authorization: Bearer`` header (workflow token, PAT, or JWT).

    Args:
        workflow_identifier: Workflow UUID or custom slug
        execution_request: Request body containing the message
        fastapi_request: The incoming FastAPI request (for Authorization header)
        credentials: Optional token supplied as a Bearer token in the Authorization header

    Returns:
        SSE stream with execution updates

    Example::

        curl -N -X POST "http://localhost:8000/api/http-execution/trigger-sse/9d04ad87-..." \\
          -H "Authorization: Bearer wf_abc123..." \\
          -H "Content-Type: application/json" \\
          -d '{"message": "Hello world"}'

    SSE Events:
        - acknowledged: Request received
        - started: Execution started (includes execution_id)
        - node_executing: Node is being executed (includes node name)
        - completed: Execution completed (includes output)
        - failed: Execution failed (includes error)
        - error: Error occurred
        - done: Stream complete
    """
    resolved_token = credentials.credentials if credentials else None
    file_data = execution_request.resolve_file_data()
    return StreamingResponse(
        sse_handler.stream_execution(
            workflow_identifier,
            execution_request.message,
            resolved_token,
            file_data=file_data,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


@router.post("/resume/{graph_name}")
async def resume_http_execution(
    graph_name: str, request: HttpResumeRequest
) -> Union[HttpExecutionResponse, Dict[str, Any]]:
    """Resume a paused HTTP execution from checkpoint.

    When a workflow pauses at a CHECKPOINT node, this endpoint can be used
    to provide user input and resume execution.

    Args:
        graph_name: Name of the graph to resume
        request: Resume request with thread_id, checkpoint_id, and user_input

    Returns:
        If execution completes: Final output
        If another checkpoint: New checkpoint pause response
        If async_mode: Status endpoint

    Example:
        ```bash
        curl -X POST "http://localhost:8000/api/http-execution/resume/my-workflow" \\
          -H "Content-Type: application/json" \\
          -d '{
            "thread_id": "exec_20241014_123456_my-workflow",
            "checkpoint_id": "checkpoint_abc123",
            "user_input": "User response here",
            "async_mode": false
          }'
        ```
    """
    try:
        return await checkpoint_handler.resume_checkpoint(
            graph_name=graph_name,
            thread_id=request.thread_id,
            checkpoint_id=request.checkpoint_id,
            user_input=request.user_input,
        )
    except HttpExecutionException as e:
        raise _handle_http_execution_exception(e)
    except Exception as e:
        logger.error(f"[HTTP-EXEC-API] Unexpected error in resume_http_execution: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Check server logs for details.",
        )


@router.get(
    "/latest-execution/{graph_name}",
    dependencies=[Depends(require_active_user), Depends(require_scope("execution:*:read"))],
)
async def get_latest_http_execution(
    graph_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> LatestExecutionResponse:
    """Get the latest HTTP-triggered execution for a graph.

    Args:
        graph_name: Name of the graph
        current_user: Authenticated user (must own or be a member of the workflow)

    Returns:
        Latest execution info if available

    Example:
        ```bash
        curl "http://localhost:8000/api/http-execution/latest-execution/my-workflow"
        ```
    """
    try:
        # URL decode the graph name
        graph_name = unquote(graph_name)

        # Executions are resolved by workflow name, so the caller must be
        # entitled to that workflow (ISG F-40 row 18). Without this any
        # authenticated user could read another tenant's latest run by name.
        require_workflow_access(current_user, graph_name)

        return execution_tracker.get_latest_execution(graph_name)

    except HTTPException:
        # Authorization outcomes (403/404) must reach the caller instead of
        # being reported as a server error by the handler below.
        raise
    except Exception as e:
        logger.error(f"[HTTP-EXEC-API] Error getting latest execution: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Check server logs for details.",
        )


@router.get("/info/{graph_name}", dependencies=[Depends(require_active_user), Depends(require_scope("workflow:*:read"))])
async def get_http_execution_info(
    graph_name: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> ExecutionInfoResponse:
    """Get HTTP execution information for a graph.

    This endpoint provides information about how to execute a workflow via HTTP,
    including example curl commands and endpoint details.

    Args:
        graph_name: Name of the graph
        request: FastAPI request (for base URL extraction)
        current_user: Authenticated user (must own or be a member of the workflow)

    Returns:
        HTTP execution endpoint details and examples

    Example:
        ```bash
        curl "http://localhost:8000/api/http-execution/info/my-workflow"
        ```
    """
    try:
        from backend.models import Workflow
        from backend.services.database import get_db

        # URL decode the graph name
        graph_name = unquote(graph_name)

        # Authorize before touching the graph manager: its cache and the
        # "default" workspace fallback below are name-keyed and process-global,
        # so an unauthorized caller would otherwise learn whether another
        # tenant's workflow exists and whether it has a trigger token
        # (ISG F-40 row 18).
        require_workflow_access(current_user, graph_name)

        # Check if graph exists
        graph = get_graph_manager().get_graph(graph_name)
        if not graph:
            # Try loading from disk
            graph = get_graph_manager().load_graph(graph_name, "default")

        if not graph:
            raise HTTPException(
                status_code=404, detail=f"Graph '{graph_name}' not found"
            )

        # Report only whether a trigger token exists. The token itself is a
        # bearer secret that authorizes POST /api/http-execution/trigger/... ,
        # and this route performs no per-workflow authorization, so returning
        # it would hand any authenticated user who knows a graph name the
        # ability to execute that workflow. Callers who are entitled to the
        # value fetch it from GET /api/graph/{graph_name}/http-trigger-token,
        # which verifies workflow access.
        has_token = False
        workflow_id = getattr(graph, "workflow_id", None)
        if workflow_id:
            with get_db() as db:
                workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
                has_token = bool(workflow and workflow.http_trigger_token)

        # Derive base URL from request
        base_url = get_base_url(request)
        endpoint = f"{base_url}/api/http-execution/trigger/{graph_name}"

        # Example carries a placeholder, never the real secret
        curl_example = f'''curl -X POST "{endpoint}" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{{"message": "Your message here"}}' '''

        return ExecutionInfoResponse(
            success=True,
            graph_name=graph_name,
            endpoint=endpoint,
            method="POST",
            headers={"Content-Type": "application/json"},
            body_format={"message": "string"},
            has_token=has_token,
            example_curl=curl_example,
            example_body={"message": "Your message here"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HTTP-EXEC-API] Error getting HTTP execution info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Check server logs for details.",
        )


@router.get("/execution/{execution_id}")
async def get_pat_execution_status(
    execution_id: str,
    credentials: HTTPAuthorizationCredentials = Security(_pat_bearer),
) -> HttpExecutionResponse:
    """Get the status and output of a PAT-triggered execution.

    Allows polling for the result of an async-triggered execution using
    the same PAT that was used to trigger it. Only executions owned by
    the authenticated PAT user are accessible.

    Args:
        execution_id: The execution ID returned by the trigger endpoint
        credentials: PAT supplied as a Bearer token in the Authorization header

    Returns:
        HttpExecutionResponse with current status and output if completed

    Example::

        curl "http://localhost:8000/api/http-execution/execution/exec_20260224_..." \\
          -H "Authorization: Bearer na_abc123..."
    """
    resolved_token = credentials.credentials if credentials else None

    if not resolved_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not resolved_token.startswith("na_"):
        raise HTTPException(
            status_code=401,
            detail="Only Personal Access Tokens (na_...) are accepted",
        )

    result = UserAPITokenService.validate_token(resolved_token)
    if not result:
        raise HTTPException(
            status_code=401, detail="Invalid or expired Personal Access Token"
        )

    _, user_id = result

    try:
        execution_data = ExecutionHistoryService.get_graph_execution_dict(execution_id)
    except Exception as e:
        logger.error(f"[HTTP-EXEC-API] Error fetching execution {execution_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Check server logs for details.",
        )

    if not execution_data:
        raise HTTPException(
            status_code=404, detail=f"Execution '{execution_id}' not found"
        )

    if execution_data.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    status = execution_data.get("status", "unknown")
    output = extract_execution_output(execution_data) if status == "completed" else None

    node_execs = execution_data.get("node_executions") or []
    terminal = {"completed", "success", "failed", "interrupted", "cancelled", "stopped"}
    nodes_completed = sum(1 for n in node_execs if n.get("status") in terminal)

    return HttpExecutionResponse(
        success=True,
        execution_id=execution_id,
        status=status,
        output=output,
        nodes_completed=nodes_completed,
    )


def _serialize_published_workflow(pw: Any) -> Dict[str, Any]:
    """Serialize a PublishedWorkflow ORM object to a response dict."""
    endpoint_url = build_endpoint_url(
        workflow_id=str(pw.workflow_id),
        custom_slug=pw.custom_slug,
    )
    workflow_updated_at = None
    if pw.workflow and pw.workflow.updated_at:
        workflow_updated_at = pw.workflow.updated_at.isoformat()

    return {
        "workflow_id": str(pw.workflow_id),
        "graph_name": pw.graph_name,
        "is_published": pw.is_published,
        "endpoint_url": endpoint_url,
        "custom_slug": pw.custom_slug,
        "description": pw.description,
        "require_authentication": pw.require_authentication,
        "published_at": pw.published_at.isoformat() if pw.published_at else None,
        "last_accessed": pw.last_accessed.isoformat() if pw.last_accessed else None,
        "access_count": pw.access_count,
        "workflow_updated_at": workflow_updated_at,
        "rate_limit": pw.rate_limit,
        "allowed_origins": pw.allowed_origins,
        "webhook_url": pw.webhook_url,
    }


@router.get("/workflows")
async def list_workflows_for_pat(
    credentials: HTTPAuthorizationCredentials = Security(_pat_bearer),
) -> Dict[str, Any]:
    """List published workflows accessible to the caller.

    Mirrors the auth behaviour of the /trigger endpoints:

    - **With a valid PAT** (via ``Authorization: Bearer na_xxx`` header):
      returns all published workflows the token owner has access to
      (owned or shared via membership).
    - **Without a token**: returns only workflows published with
      ``require_authentication=false``, i.e. the publicly discoverable ones.

    If a token is supplied but is invalid or expired a ``401`` is returned.

    Args:
        credentials: Optional Bearer token from the Authorization header

    Returns:
        List of published workflow information and total count

    Example — authenticated::

        curl "http://localhost:8000/api/http-execution/workflows" \\
          -H "Authorization: Bearer na_abc123..."

    Example — unauthenticated (public workflows only)::

        curl "http://localhost:8000/api/http-execution/workflows"
    """
    resolved_token = credentials.credentials if credentials else None

    if resolved_token:
        if not resolved_token.startswith("na_"):
            raise HTTPException(
                status_code=401,
                detail="Only Personal Access Tokens (na_...) are accepted",
            )

        result = UserAPITokenService.validate_token(resolved_token)
        if not result:
            raise HTTPException(
                status_code=401, detail="Invalid or expired Personal Access Token"
            )

        _, user_id = result

        try:
            published_workflows_db = (
                WorkflowPublishingService.list_published_workflows_for_user(user_id)
            )
        except Exception as e:
            logger.error(
                f"[HTTP-EXEC-API] Error listing workflows for PAT user '{user_id}': {e}"
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error. Check server logs for details.",
            )
    else:
        # No token — return only publicly accessible workflows
        try:
            published_workflows_db = (
                WorkflowPublishingService.list_public_published_workflows()
            )
        except Exception as e:
            logger.error(f"[HTTP-EXEC-API] Error listing public workflows: {e}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error. Check server logs for details.",
            )

    published_workflows = [
        _serialize_published_workflow(pw) for pw in published_workflows_db
    ]

    return {
        "success": True,
        "published_workflows": published_workflows,
        "total_count": len(published_workflows),
    }


@router.get("/presigned-url/{document_id}")
async def get_presigned_url_for_document(
    document_id: str,
    credentials: HTTPAuthorizationCredentials = Security(_pat_bearer),
) -> Dict[str, Any]:
    """Get a pre-signed download URL for a document using PAT authentication.

    This endpoint is designed for external services (e.g., TADA Chat) that need
    to fetch document download URLs without OAuth2-Proxy authentication.
    It uses the same PAT token authentication as the trigger endpoints.

    Accepted token types (via Authorization: Bearer header):
    - Workflow trigger token (wf_xxx)
    - Personal Access Token (na_xxx)
    - Azure AD / local JWT

    Args:
        document_id: UUID of the document to get a pre-signed URL for
        credentials: PAT supplied as a Bearer token in the Authorization header

    Returns:
        JSON with pre-signed URL or local download fallback

    Example::

        curl "http://localhost:8000/api/http-execution/presigned-url/abc-123" \\
          -H "Authorization: Bearer wf_xxx"
    """
    resolved_token = credentials.credentials if credentials else None

    if not resolved_token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a PAT or workflow token via Authorization: Bearer header.",
        )

    # Validate the token is a valid PAT or workflow token
    is_valid = False

    if resolved_token.startswith("na_"):
        # Personal Access Token — validate without workflow scope check
        result = UserAPITokenService.validate_token_no_scope_check(resolved_token)
        is_valid = result is not None
    elif resolved_token.startswith("wf_"):
        # Workflow trigger token — check it matches any workflow's http_trigger_token
        from backend.models import Workflow
        from backend.services.database import get_db
        import hmac as _hmac

        with get_db() as db:
            workflows_with_token = (
                db.query(Workflow)
                .filter(Workflow.http_trigger_token.isnot(None))
                .all()
            )
            for wf in workflows_with_token:
                if _hmac.compare_digest(resolved_token, wf.http_trigger_token):
                    is_valid = True
                    break
    else:
        # JWT — verify it decodes successfully
        from backend.services.auth.config import get_auth_config
        import jwt as pyjwt

        auth_config = get_auth_config()
        try:
            pyjwt.decode(
                resolved_token,
                auth_config.jwt_secret,
                algorithms=["HS256"],
                audience="http-execution",
                issuer="agenticstudio",
            )
            is_valid = True
        except pyjwt.PyJWTError:
            # Try Azure AD
            from backend.services.auth.providers.oauth2_proxy import get_oauth_proxy_auth

            oauth_auth = get_oauth_proxy_auth()
            if oauth_auth:
                try:
                    oauth_auth._decode_token(resolved_token)
                    is_valid = True
                except Exception:
                    is_valid = False

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
        )

    # Fetch document and generate presigned URL
    try:
        document_service = DocumentStorageService()
        doc_info = document_service.repository.get_document(document_id)

        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")

        if not doc_info.storage_path:
            raise HTTPException(
                status_code=404,
                detail="Stored file path is not available for this document",
            )

        download_name = doc_info.file_name or doc_info.name or f"{document_id}.bin"

        presigned_url = document_service.resolve_document_download_url(
            storage_path=doc_info.storage_path,
            file_name=download_name,
        )

        if presigned_url:
            return {
                "success": True,
                "document_id": document_id,
                "file_name": download_name,
                "url": presigned_url,
                "url_type": "presigned",
            }

        # Fallback: return the download endpoint for local files
        return {
            "success": True,
            "document_id": document_id,
            "file_name": download_name,
            "url": f"/api/documents/{document_id}/download",
            "url_type": "local",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HTTP-EXEC-API] Error generating presigned URL for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
