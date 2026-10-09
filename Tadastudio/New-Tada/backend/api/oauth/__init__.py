"""OAuth API package for MCP provider authentication."""

from .mcp import router as mcp_oauth_router
from .microsoft import router as microsoft_oauth_router
from .notion import router as notion_oauth_router

__all__ = ["notion_oauth_router", "mcp_oauth_router", "microsoft_oauth_router"]
