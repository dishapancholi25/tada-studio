"""OneDrive MCP Server entry point.

Usage: python -m backend.tools.onedrive_mcp

Environment variables:
  ONEDRIVE_ACCESS_TOKEN    - Delegated OAuth token (injected by mcp_client_manager)
  ONEDRIVE_TENANT_ID       - Azure AD tenant ID (for client_credentials fallback)
  ONEDRIVE_CLIENT_ID       - Azure AD app client ID
  ONEDRIVE_CLIENT_SECRET   - Azure AD app client secret
"""

from .server import mcp

if __name__ == "__main__":
    mcp.run()
