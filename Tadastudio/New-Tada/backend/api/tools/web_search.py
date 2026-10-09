"""REST API endpoints for web search tool."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.auth.dependencies import require_active_user

from ...tools.web_search import (
    ConfigValidator,
    SearchProviderInfo,
    SearchProvidersResponse,
    ValidateConfigRequest,
    ValidateConfigResponse,
    WebSearchConfig,
    WebSearchResponse,
    execute_search,
    format_search_results,
)


logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/tools/web-search",
    tags=["tools", "web-search"],
    dependencies=[Depends(require_active_user)],
)


class SearchRequest(BaseModel):
    """Request model for executing a web search."""

    query: str = Field(..., description="Search query string", min_length=1)
    config: WebSearchConfig = Field(
        default_factory=lambda: WebSearchConfig(),
        description="Search configuration (uses defaults if not provided)",
    )


@router.post("/search", response_model=WebSearchResponse)
async def search_web(request: SearchRequest) -> WebSearchResponse:
    """Execute a web search via REST API.

    This endpoint allows executing web searches without using the tool interface,
    useful for direct API access, testing, or integration with other systems.

    Args:
        request: Search request containing query and configuration

    Returns:
        WebSearchResponse with results or error information

    Raises:
        HTTPException: If search fails
    """
    try:
        logger.info(f"[API WebSearch] Executing search: '{request.query}'")

        # Validate configuration
        is_valid, errors, warnings = ConfigValidator.validate(request.config)

        if not is_valid:
            logger.error(f"[API WebSearch] Invalid configuration: {errors}")
            raise HTTPException(
                status_code=400,
                detail={"message": "Invalid configuration", "errors": errors},
            )

        # Log warnings
        for warning in warnings:
            logger.warning(f"[API WebSearch] Configuration warning: {warning}")

        # Execute search
        results = execute_search(request.query, request.config)

        # Format results
        formatted_results = format_search_results(results)

        if not formatted_results:
            return WebSearchResponse(
                success=True,
                results=f"No results found for query: {request.query}",
            )

        logger.info(
            f"[API WebSearch] Search completed successfully for '{request.query}'"
        )

        return WebSearchResponse(
            success=True,
            results=formatted_results,
        )

    except ValueError as e:
        logger.error(f"[API WebSearch] Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"[API WebSearch] Search failed: {str(e)}", exc_info=True)
        return WebSearchResponse(
            success=False,
            error=f"Search failed: {str(e)}",
        )


@router.get("/providers", response_model=SearchProvidersResponse)
async def list_providers() -> SearchProvidersResponse:
    """List available search providers and their capabilities.

    Returns:
        SearchProvidersResponse with provider information
    """
    providers = [
        SearchProviderInfo(
            name="duckduckgo",
            requires_api_key=False,
            features=[
                "Free to use",
                "No API key required",
                "Text search",
                "Image search",
                "Region filtering",
                "Safe search",
                "Time range filtering",
            ],
            description="Free web search provider with no API key requirements. "
            "Good for general purpose searches.",
        ),
        SearchProviderInfo(
            name="tavily",
            requires_api_key=True,
            features=[
                "AI-optimized results",
                "AI-generated answers",
                "Raw content extraction",
                "Image search",
                "Basic and advanced search depth",
                "Optimized for LLMs",
            ],
            description="AI-optimized search provider designed for LLM applications. "
            "Requires API key but provides higher quality results and AI answers.",
        ),
    ]

    return SearchProvidersResponse(providers=providers)


@router.post("/validate", response_model=ValidateConfigResponse)
async def validate_config(request: ValidateConfigRequest) -> ValidateConfigResponse:
    """Validate a web search configuration.

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
    """Health check endpoint for web search API.

    Returns:
        Health status information
    """
    return {
        "status": "healthy",
        "service": "web-search",
        "providers": ["duckduckgo", "tavily"],
    }
