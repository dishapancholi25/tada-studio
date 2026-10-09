"""SharePoint MCP Server entry point.

Usage: python -m backend.tools.sharepoint_mcp

Environment variables required:
  SHAREPOINT_TENANT_ID   - Azure AD tenant ID
  SHAREPOINT_CLIENT_ID   - Azure AD app registration client ID
  SHAREPOINT_CLIENT_SECRET - Azure AD app registration client secret
  SHAREPOINT_SITE_URL    - (optional) Specific SharePoint site URL to scope access
"""

from .server import mcp

if __name__ == "__main__":
    mcp.run()
