"""API endpoint service module for managing reusable HTTP endpoint configurations."""

from .resolver import resolve_endpoint_config
from .service import ApiEndpointService


_api_endpoint_service = None


def get_api_endpoint_service() -> ApiEndpointService:
    """Get or create the singleton API endpoint service instance.

    Returns:
        ApiEndpointService instance
    """
    global _api_endpoint_service
    if _api_endpoint_service is None:
        _api_endpoint_service = ApiEndpointService()
    return _api_endpoint_service


__all__ = [
    "ApiEndpointService",
    "get_api_endpoint_service",
    "resolve_endpoint_config",
]
