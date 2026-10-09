"""Tools API endpoints."""

from .document_search import router as document_search_router
from .web_search import router as web_search_router


__all__ = ["web_search_router", "document_search_router"]
