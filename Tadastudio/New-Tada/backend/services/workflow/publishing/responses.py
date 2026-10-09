"""Response builders for workflow publishing."""

from typing import Any, Dict
from urllib.parse import quote

from ...config import get_endpoint_url


def build_endpoint_url(workflow_id: str, custom_slug: str = None) -> str:
    """Build the endpoint URL for a published workflow.

    Args:
        workflow_id: The workflow UUID (used if no custom_slug)
        custom_slug: Optional custom slug (takes precedence over workflow_id)

    Returns:
        Full endpoint URL
    """
    identifier = custom_slug or workflow_id
    return get_endpoint_url(f"/api/http-execution/trigger/{quote(identifier, safe='')}")


def build_publication_config_dict(
    request, published_workflow=None, include_timestamps: bool = True
) -> Dict[str, Any]:
    """Build a publication configuration dictionary."""
    config = {
        "is_published": True,
        "custom_slug": request.custom_slug,
        "description": request.description,
        "require_authentication": request.require_authentication,
        "rate_limit": request.rate_limit,
        "allowed_origins": request.allowed_origins,
        "webhook_url": request.webhook_url,
        "input_schema": request.input_schema,
    }

    if include_timestamps and published_workflow:
        if published_workflow.published_at:
            config["published_at"] = published_workflow.published_at.isoformat()
        config["access_count"] = published_workflow.access_count

    return config


def sync_graph_config_from_request(graph, request):
    """Sync graph publication config from request data."""
    config = graph.publication_config

    config.is_published = True
    config.custom_slug = request.custom_slug
    config.description = request.description
    config.require_authentication = request.require_authentication
    config.rate_limit = request.rate_limit
    config.allowed_origins = request.allowed_origins
    config.webhook_url = request.webhook_url
    config.input_schema = request.input_schema
