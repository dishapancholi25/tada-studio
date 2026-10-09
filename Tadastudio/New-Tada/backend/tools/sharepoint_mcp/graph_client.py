"""Backward-compatible re-export from shared Microsoft Graph client.

The actual implementation lives in backend.tools.shared.microsoft_graph_client.
This module re-exports with the original name (SharePointGraphClient) so
existing imports in server.py continue to work unchanged.
"""

from backend.tools.shared.microsoft_graph_client import (
    GraphAPIError,
    MicrosoftGraphClient as SharePointGraphClient,
    clear_cached_tokens,
)

__all__ = ["GraphAPIError", "SharePointGraphClient", "clear_cached_tokens"]
