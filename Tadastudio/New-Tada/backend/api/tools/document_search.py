"""REST API endpoints for document search tool."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.auth.dependencies import get_current_user, require_active_user
from backend.models import User
from backend.services.database import get_db
from backend.services.document_storage import DocumentStorageService

from ...tools.document_search import (
    ConfigValidator,
    DocumentSearchConfig,
    DocumentSearchResponse,
    ValidateConfigRequest,
    ValidateConfigResponse,
    execute_search,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/tools/document-search",
    tags=["tools", "document-search"],
    dependencies=[Depends(require_active_user)],
)


class SearchRequest(BaseModel):
    """Request model for executing a document search."""

    query: str = Field(
        ...,
        description="Search query string",
        min_length=1,
    )
    config: DocumentSearchConfig = Field(
        default_factory=lambda: DocumentSearchConfig(),
        description="Search configuration (uses defaults if not provided)",
    )


def get_user_id_from_claims(current_user: Dict[str, Any]) -> str:
    """Extract the database user id from authentication claims."""
    email = current_user.get("email")
    sub = current_user.get("sub")

    with get_db() as db:
        if sub:
            user = db.query(User).filter(User.id == sub).first()
            if user:
                return user.id

        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                return user.id

    raise HTTPException(status_code=401, detail="User not found")


def verify_document_search_access(
    config: DocumentSearchConfig,
    current_user: Dict[str, Any],
) -> None:
    """Verify the caller can access all requested collections/documents."""
    document_service = DocumentStorageService()
    user_id = get_user_id_from_claims(current_user)

    for collection_id in config.collection_names or []:
        if not document_service.check_collection_access(collection_id, user_id):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have access to collection {collection_id}",
            )

    for document_id in config.document_ids or []:
        doc_info = document_service.repository.get_document(document_id)
        if not doc_info:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have access to document {document_id}",
            )
        if not document_service.check_collection_access(
            doc_info.collection_id,
            user_id,
        ):
            raise HTTPException(
                status_code=403,
                detail=f"You do not have access to collection {doc_info.collection_id}",
            )


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> DocumentSearchResponse:
    """Execute a document search via REST API.

    This endpoint allows executing document searches without using the tool interface,
    useful for direct API access, testing, or integration with other systems.

    Args:
        request: Search request containing query and configuration

    Returns:
        DocumentSearchResponse with results or error information

    Raises:
        HTTPException: If search configuration is invalid
    """
    try:
        logger.info(f"[API DocumentSearch] Executing search: '{request.query}'")

        # Validate configuration
        is_valid, errors, warnings = ConfigValidator.validate(request.config)

        if not is_valid:
            logger.error(f"[API DocumentSearch] Invalid configuration: {errors}")
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid configuration", "errors": errors},
            )

        # Log warnings
        for warning in warnings:
            logger.warning(f"[API DocumentSearch] Configuration warning: {warning}")

        verify_document_search_access(request.config, current_user)

        # Execute search
        results = execute_search(request.query, request.config)

        if not results or results.startswith("No relevant"):
            return DocumentSearchResponse(
                success=True,
                results=results or f"No results found for query: {request.query}",
                metadata={
                    "query": request.query,
                    "result_count": 0,
                },
            )

        logger.info(
            f"[API DocumentSearch] Search completed successfully for '{request.query}'"
        )

        return DocumentSearchResponse(
            success=True,
            results=results,
            metadata={
                "query": request.query,
                "collections_searched": request.config.collection_names,
                "documents_searched": request.config.document_ids,
                "search_mode": request.config.search_mode,
            },
        )

    except HTTPException:
        raise

    except ValueError as e:
        logger.error(f"[API DocumentSearch] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(
            f"[API DocumentSearch] Search failed: {str(e)}",
            exc_info=True,
        )
        return DocumentSearchResponse(
            success=False,
            error=f"Search failed: {str(e)}",
        )


@router.post("/validate", response_model=ValidateConfigResponse)
async def validate_config(
    request: ValidateConfigRequest,
) -> ValidateConfigResponse:
    """Validate a document search configuration.

    Useful for checking configuration before executing searches,
    especially when building UIs or workflows.

    Args:
        request: Configuration to validate

    Returns:
        ValidateConfigResponse with validation results
    """
    is_valid, errors, warnings = ConfigValidator.validate(request.config)

    return ValidateConfigResponse(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
    )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for document search API.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "service": "document-search",
        "search_types": ["similarity", "hybrid", "keyword", "mmr"],
        "citation_formats": ["structured", "inline", "footnote", "none"],
    }
