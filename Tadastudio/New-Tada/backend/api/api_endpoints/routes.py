"""API routes for managing reusable API endpoint configurations."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.api.datasources.dependencies import get_database, get_user_id_from_claims
from backend.services.api_endpoint import get_api_endpoint_service
from backend.services.auth.rbac import _redact_email


logger = logging.getLogger(__name__)


# --- Pydantic Models ---


class ApiEndpointCreate(BaseModel):
    """Model for creating an API endpoint."""

    name: str = Field(..., description="Unique name for the endpoint")
    description: Optional[str] = Field(None, description="Description of the endpoint")
    service_type: str = Field(
        "generic",
        description="Service type (generic, servicenow, workday, salesforce, azure, aws, gcp, custom)",
    )
    url_template: str = Field(
        ..., description="URL template with optional {placeholders}"
    )
    method: str = Field("GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(None, description="Static headers")
    query_params: Optional[Dict[str, str]] = Field(
        None, description="Static query parameters"
    )
    request_body_template: Optional[str] = Field(
        None, description="Request body template"
    )
    content_type: Optional[str] = Field(None, description="Content type")
    parameter_schema: Optional[Dict[str, Any]] = Field(
        None, description="Dynamic parameter definitions"
    )
    auth_type: str = Field("none", description="Authentication type")
    auth_config: Optional[Dict[str, str]] = Field(
        None, description="Authentication configuration"
    )
    timeout_seconds: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, description="Delay between retries")
    retry_on_status: Optional[List[int]] = Field(
        None, description="Status codes to retry on"
    )
    response_format: str = Field("auto", description="Expected response format")
    extract_path: Optional[str] = Field(
        None, description="JSONPath to extract from response"
    )
    success_status_codes: Optional[List[int]] = Field(
        None, description="Status codes indicating success"
    )
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    follow_redirects: bool = Field(True, description="Follow HTTP redirects")
    max_redirects: int = Field(10, description="Maximum redirects to follow")
    visible_to_groups: List[str] = Field(
        default_factory=list,
        description="Groups that can access this endpoint. Use ['__all__'] for everyone.",
    )


class ApiEndpointUpdate(BaseModel):
    """Model for updating an API endpoint."""

    name: Optional[str] = None
    description: Optional[str] = None
    service_type: Optional[str] = None
    url_template: Optional[str] = None
    method: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    query_params: Optional[Dict[str, str]] = None
    request_body_template: Optional[str] = None
    content_type: Optional[str] = None
    parameter_schema: Optional[Dict[str, Any]] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, str]] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    retry_delay: Optional[float] = None
    retry_on_status: Optional[List[int]] = None
    response_format: Optional[str] = None
    extract_path: Optional[str] = None
    success_status_codes: Optional[List[int]] = None
    verify_ssl: Optional[bool] = None
    follow_redirects: Optional[bool] = None
    max_redirects: Optional[int] = None
    is_active: Optional[bool] = None


class ApiEndpointResponse(BaseModel):
    """Model for API endpoint response."""

    id: str
    name: str
    description: Optional[str]
    service_type: str = "generic"
    url_template: str
    method: str
    headers: Optional[Dict[str, str]]
    query_params: Optional[Dict[str, str]]
    request_body_template: Optional[str]
    content_type: Optional[str]
    parameter_schema: Optional[Dict[str, Any]]
    auth_type: str
    timeout_seconds: int
    max_retries: int
    retry_delay: float
    retry_on_status: Optional[List[int]]
    response_format: str
    extract_path: Optional[str]
    success_status_codes: Optional[List[int]]
    verify_ssl: bool
    follow_redirects: bool
    max_redirects: int
    is_active: bool
    usage_count: int
    last_used: Optional[datetime]
    last_connection_test: Optional[datetime] = None
    last_connection_status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]
    visible_to_groups: List[str] = Field(default_factory=list)
    user_id: Optional[str] = None
    is_read_only: bool = False


class UpdateVisibilityRequest(BaseModel):
    """Model for updating endpoint visibility."""

    visible_to_groups: List[str] = Field(
        ...,
        description="Groups that can access this endpoint. Use ['__all__'] for everyone.",
    )


# --- Helper ---


def _endpoint_to_response(endpoint, user_id: str) -> ApiEndpointResponse:
    """Convert an ApiEndpoint model to an ApiEndpointResponse."""
    return ApiEndpointResponse(
        id=endpoint.id,
        name=endpoint.name,
        description=endpoint.description,
        service_type=getattr(endpoint, "service_type", "generic") or "generic",
        url_template=endpoint.url_template,
        method=endpoint.method,
        headers=endpoint.headers,
        query_params=endpoint.query_params,
        request_body_template=endpoint.request_body_template,
        content_type=endpoint.content_type,
        parameter_schema=endpoint.parameter_schema,
        auth_type=endpoint.auth_type,
        timeout_seconds=endpoint.timeout_seconds,
        max_retries=endpoint.max_retries,
        retry_delay=endpoint.retry_delay,
        retry_on_status=endpoint.retry_on_status,
        response_format=endpoint.response_format,
        extract_path=endpoint.extract_path,
        success_status_codes=endpoint.success_status_codes,
        verify_ssl=endpoint.verify_ssl,
        follow_redirects=endpoint.follow_redirects,
        max_redirects=endpoint.max_redirects,
        is_active=endpoint.is_active,
        usage_count=endpoint.usage_count,
        last_used=endpoint.last_used,
        last_connection_test=getattr(endpoint, "last_connection_test", None),
        last_connection_status=getattr(endpoint, "last_connection_status", None),
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
        visible_to_groups=endpoint.visible_to_groups or [],
        user_id=endpoint.user_id,
        is_read_only=endpoint.user_id != user_id,
    )


# --- Router ---


router = APIRouter(
    prefix="/api/api-endpoints",
    tags=["api-endpoints"],
    dependencies=[Depends(require_active_user)],
)


@router.post("", response_model=ApiEndpointResponse)
async def create_endpoint(
    data: ApiEndpointCreate,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new API endpoint configuration."""
    try:
        user_id = get_user_id_from_claims(current_user)
        service = get_api_endpoint_service()
        endpoint = service.create_endpoint(
            db=db,
            name=data.name,
            description=data.description,
            service_type=data.service_type,
            url_template=data.url_template,
            method=data.method,
            headers=data.headers,
            query_params=data.query_params,
            request_body_template=data.request_body_template,
            content_type=data.content_type,
            parameter_schema=data.parameter_schema,
            auth_type=data.auth_type,
            auth_config=data.auth_config,
            timeout_seconds=data.timeout_seconds,
            max_retries=data.max_retries,
            retry_delay=data.retry_delay,
            retry_on_status=data.retry_on_status,
            response_format=data.response_format,
            extract_path=data.extract_path,
            success_status_codes=data.success_status_codes,
            verify_ssl=data.verify_ssl,
            follow_redirects=data.follow_redirects,
            max_redirects=data.max_redirects,
            user_id=user_id,
            visible_to_groups=data.visible_to_groups,
        )

        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] API endpoint created by {_redact_email(user_email)}: "
            f"id={endpoint.id}, name={endpoint.name}"
        )

        return _endpoint_to_response(endpoint, user_id)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API_ENDPOINTS] Failed to create endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create endpoint")


@router.get("", response_model=List[ApiEndpointResponse])
async def list_endpoints(
    active_only: bool = Query(True, description="Only return active endpoints"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    filter_type: str = Query("all", description="Filter: 'all', 'owned', or 'shared'"),
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List API endpoints for the authenticated user (owned + shared)."""
    try:
        user_id = get_user_id_from_claims(current_user)
        service = get_api_endpoint_service()
        endpoints = service.list_endpoints(
            db=db,
            active_only=active_only,
            skip=skip,
            limit=limit,
            user_id=user_id,
            filter_type=filter_type,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API_ENDPOINTS] Error listing endpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list endpoints")

    return [_endpoint_to_response(ep, user_id) for ep in endpoints]


@router.get("/templates")
async def list_templates():
    """List available service templates for pre-configuring API endpoints."""
    from backend.services.api_endpoint.templates import get_templates

    return get_templates()


@router.get("/{endpoint_id}", response_model=ApiEndpointResponse)
async def get_endpoint(
    endpoint_id: str,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a specific API endpoint."""
    user_id = get_user_id_from_claims(current_user)
    service = get_api_endpoint_service()
    endpoint = service.get_endpoint_for_user(db, endpoint_id, user_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")

    return _endpoint_to_response(endpoint, user_id)


@router.put("/{endpoint_id}", response_model=ApiEndpointResponse)
async def update_endpoint(
    endpoint_id: str,
    update_data: ApiEndpointUpdate,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update an API endpoint configuration."""
    try:
        user_id = get_user_id_from_claims(current_user)
        update_dict = update_data.dict(exclude_unset=True)

        service = get_api_endpoint_service()
        endpoint = service.update_endpoint(
            db=db, endpoint_id=endpoint_id, user_id=user_id, **update_dict
        )

        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        user_email = current_user.get("email", "unknown")
        updated_fields = ", ".join(update_dict.keys())
        logger.info(
            f"[AUDIT] API endpoint updated by {_redact_email(user_email)}: "
            f"id={endpoint_id}, fields={updated_fields}"
        )

        return _endpoint_to_response(endpoint, user_id)

    except PermissionError:
        raise HTTPException(
            status_code=403, detail="Only the owner can update this endpoint"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API_ENDPOINTS] Failed to update endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update endpoint")


@router.patch("/{endpoint_id}/visibility", response_model=ApiEndpointResponse)
async def update_endpoint_visibility(
    endpoint_id: str,
    request: UpdateVisibilityRequest,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update endpoint visibility groups. Only the endpoint owner can change visibility."""
    try:
        user_id = get_user_id_from_claims(current_user)
        service = get_api_endpoint_service()
        endpoint = service.update_visibility(
            db=db,
            endpoint_id=endpoint_id,
            visible_to_groups=request.visible_to_groups,
            user_id=user_id,
        )

        if not endpoint:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] API endpoint visibility updated by {_redact_email(user_email)}: "
            f"id={endpoint_id}, groups={request.visible_to_groups}"
        )

        return _endpoint_to_response(endpoint, user_id)

    except PermissionError:
        raise HTTPException(
            status_code=403, detail="Only the owner can change visibility"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API_ENDPOINTS] Failed to update visibility: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update visibility")


@router.delete("/{endpoint_id}")
async def delete_endpoint(
    endpoint_id: str,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete an API endpoint configuration."""
    try:
        user_id = get_user_id_from_claims(current_user)
        service = get_api_endpoint_service()
        success = service.delete_endpoint(db, endpoint_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Endpoint not found")

        user_email = current_user.get("email", "unknown")
        logger.info(
            f"[AUDIT] API endpoint deleted by {_redact_email(user_email)}: "
            f"id={endpoint_id}"
        )

        return {"message": "Endpoint deleted successfully"}

    except PermissionError:
        raise HTTPException(
            status_code=403, detail="Only the owner can delete this endpoint"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API_ENDPOINTS] Failed to delete endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete endpoint")


@router.post("/{endpoint_id}/test")
async def test_endpoint(
    endpoint_id: str,
    db: Session = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Test connectivity to a saved API endpoint."""
    try:
        user_id = get_user_id_from_claims(current_user)
        service = get_api_endpoint_service()
        result = await service.test_endpoint(db, endpoint_id, user_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API_ENDPOINTS] Failed to test endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to test endpoint")
