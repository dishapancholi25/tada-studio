"""OAuth service package for MCP provider authentication.

This package provides OAuth handling for MCP providers that require
Dynamic Client Registration and OAuth authorization flows.

Currently supported providers:
- Notion MCP (Dynamic Client Registration per RFC 7591)
"""

from .storage import OAuthStorageService
from .notion_handler import NotionOAuthHandler

__all__ = [
    "OAuthStorageService",
    "NotionOAuthHandler",
]
