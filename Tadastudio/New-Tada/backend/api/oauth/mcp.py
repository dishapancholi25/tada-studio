"""Generic MCP OAuth API endpoints.

This module provides REST endpoints for MCP server OAuth flows:
- /api/mcp-oauth/initiate - Start OAuth flow for an MCP server
- /api/mcp-oauth/callback - Handle OAuth callback
- /api/mcp-oauth/status - Check authentication status
- /api/mcp-oauth/revoke - Revoke OAuth access
"""

import base64
import json
import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.api.auth.dependencies import get_current_user
from backend.services.oauth.mcp_handler import McpOAuthHandler
from backend.services.oauth.storage import oauth_storage

logger = logging.getLogger(__name__)
LOG_PREFIX = "[MCP-OAUTH-API]"

router = APIRouter(prefix="/api/mcp-oauth", tags=["mcp-oauth"])


# --- Request/Response Models ---


class InitiateMcpOAuthRequest(BaseModel):
    """Request to initiate MCP OAuth flow."""

    server_url: str
    server_name: str


class InitiateMcpOAuthResponse(BaseModel):
    """Response from initiating MCP OAuth flow."""

    authorization_url: str
    state: str
    server_name: str


class McpOAuthStatusResponse(BaseModel):
    """MCP OAuth authentication status."""

    is_authenticated: bool
    has_token: bool
    has_client_registration: bool
    token_expired: bool
    expires_at: str | None = None
    scope: str | None = None
    server_name: str | None = None


class McpOAuthRevokeResponse(BaseModel):
    """Response from revoking MCP OAuth access."""

    status: str
    message: str


# --- Helpers ---


def _derive_callback_url(request: Request) -> str:
    """Derive the OAuth callback URL from the incoming request context.

    Priority:
    1. MCP_OAUTH_REDIRECT_URI env var (explicit override)
    2. X-Forwarded-Proto + X-Forwarded-Host headers (reverse proxy)
    3. RUNTIME_API_URL env var (separate-domains deployment)
    4. Request base_url (works when not behind a proxy)
    """
    explicit = os.getenv("MCP_OAUTH_REDIRECT_URI")
    if explicit:
        return explicit

    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}/api/mcp-oauth/callback"

    runtime_api_url = os.getenv("RUNTIME_API_URL", "")
    if runtime_api_url:
        return f"{runtime_api_url.rstrip('/')}/api/mcp-oauth/callback"

    # Fallback: use the request's own base URL (works for direct access)
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/mcp-oauth/callback"


# --- Endpoints ---


@router.post("/initiate", response_model=InitiateMcpOAuthResponse)
async def initiate_mcp_oauth(
    body: InitiateMcpOAuthRequest,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
) -> InitiateMcpOAuthResponse:
    """Start the OAuth flow for an MCP server.

    This endpoint:
    1. Discovers OAuth metadata from the MCP server (RFC 9728 + RFC 8414)
    2. Registers a dynamic OAuth client (RFC 7591)
    3. Generates PKCE challenge
    4. Returns the authorization URL for the frontend to open in a popup
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    callback_url = _derive_callback_url(request)
    logger.info(
        "%s Initiating MCP OAuth for user=%s server=%s callback=%s",
        LOG_PREFIX,
        user_id,
        body.server_name,
        callback_url,
    )

    from backend.services.guardrails.ssrf_mcp import validate_mcp_server_url

    blocked_reason = validate_mcp_server_url(body.server_url)
    if blocked_reason:
        raise HTTPException(status_code=400, detail=blocked_reason)

    try:
        handler = McpOAuthHandler(
            server_url=body.server_url,
            server_name=body.server_name,
            redirect_uri=callback_url,
        )
        authorization_url, state = await handler.initiate_flow(user_id)

        return InitiateMcpOAuthResponse(
            authorization_url=authorization_url,
            state=state,
            server_name=body.server_name,
        )
    except Exception as e:
        logger.error("%s Failed to initiate MCP OAuth: %s", LOG_PREFIX, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate MCP OAuth: {str(e)}"
        )


@router.get("/callback", response_class=HTMLResponse)
async def mcp_oauth_callback(
    code: str = Query(..., description="Authorization code"),
    state: str = Query(..., description="State for CSRF verification"),
) -> HTMLResponse:
    """Handle the OAuth callback from the authorization server.

    This is a generic callback that works for any MCP server. It decodes
    the state to determine the provider and retrieves the stored server_url
    from the client registration metadata.
    """
    logger.info("%s Handling MCP OAuth callback", LOG_PREFIX)

    try:
        # Decode state to extract provider info
        state_json = base64.urlsafe_b64decode(state.encode()).decode()
        state_data = json.loads(state_json)
        provider = state_data.get("provider")
        user_id = state_data.get("user_id")

        if not provider or not provider.startswith("mcp:"):
            raise ValueError(f"Invalid provider in state: {provider}")

        server_name = provider[4:]  # Remove "mcp:" prefix

        # Retrieve server_url from stored client registration metadata
        client_reg = oauth_storage.get_client_registration(user_id, provider)
        if not client_reg or not client_reg.metadata_:
            raise ValueError("Client registration not found for callback")

        server_url = client_reg.metadata_.get("server_url")
        if not server_url:
            raise ValueError("server_url not found in registration metadata")

        handler = McpOAuthHandler(
            server_url=server_url,
            server_name=server_name,
        )
        result = await handler.handle_callback(code, state)

        # Success HTML - posts message to parent and closes popup
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MCP Authorization Complete</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #1a1a2e;
            color: #eee;
        }}
        .container {{
            text-align: center;
            padding: 2rem;
        }}
        .success {{
            color: #4ade80;
            font-size: 3rem;
            margin-bottom: 1rem;
        }}
        h1 {{
            margin-bottom: 0.5rem;
        }}
        p {{
            color: #aaa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="success">&#10003;</div>
        <h1>Authorization Successful</h1>
        <p>You can close this window now.</p>
    </div>
    <script>
        if (window.opener) {{
            window.opener.postMessage({{
                type: 'mcp_oauth_complete',
                success: true,
                user_id: '{result["user_id"]}',
                server_name: '{server_name}'
            }}, '*');
        }}
        setTimeout(function() {{
            window.close();
        }}, 1500);
    </script>
</body>
</html>
"""
        return HTMLResponse(content=html_content)

    except ValueError as e:
        logger.warning("%s MCP OAuth callback validation error: %s", LOG_PREFIX, e)
        error_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Failed</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #1a1a2e;
            color: #eee;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        .error {
            color: #f87171;
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        h1 {
            margin-bottom: 0.5rem;
        }
        p {
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error">&#10007;</div>
        <h1>Authorization Failed</h1>
        <p>Authorization validation failed. Please try again.</p>
    </div>
    <script>
        if (window.opener) {
            window.opener.postMessage({
                type: 'mcp_oauth_complete',
                success: false,
                error: 'Authorization validation failed. Please try again.'
            }, '*');
        }
        setTimeout(function() {
            window.close();
        }, 3000);
    </script>
</body>
</html>
"""
        return HTMLResponse(content=error_html, status_code=400)

    except Exception as e:
        logger.error("%s MCP OAuth callback error: %s", LOG_PREFIX, e)
        error_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Error</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: #1a1a2e;
            color: #eee;
        }
        .container {
            text-align: center;
            padding: 2rem;
        }
        .error {
            color: #f87171;
            font-size: 3rem;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error">&#10007;</div>
        <h1>Authorization Error</h1>
        <p>An unexpected error occurred. Please try again.</p>
    </div>
    <script>
        if (window.opener) {
            window.opener.postMessage({
                type: 'mcp_oauth_complete',
                success: false,
                error: 'An unexpected error occurred'
            }, '*');
        }
        setTimeout(function() {
            window.close();
        }, 3000);
    </script>
</body>
</html>
"""
        return HTMLResponse(content=error_html, status_code=500)


@router.get("/status", response_model=McpOAuthStatusResponse)
async def get_mcp_oauth_status(
    server_name: str = Query(..., description="MCP server name"),
    user: Dict[str, Any] = Depends(get_current_user),
) -> McpOAuthStatusResponse:
    """Check MCP OAuth authentication status for the current user and server."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    # We don't need server_url for status check — just use a placeholder
    handler = McpOAuthHandler(
        server_url="",
        server_name=server_name,
    )
    status = handler.get_status(user_id)
    status["server_name"] = server_name

    return McpOAuthStatusResponse(**status)


@router.delete("/revoke", response_model=McpOAuthRevokeResponse)
async def revoke_mcp_oauth(
    server_name: str = Query(..., description="MCP server name"),
    user: Dict[str, Any] = Depends(get_current_user),
) -> McpOAuthRevokeResponse:
    """Revoke MCP OAuth access for the current user and server."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    logger.info(
        "%s Revoking MCP OAuth for user=%s server=%s",
        LOG_PREFIX,
        user_id,
        server_name,
    )

    handler = McpOAuthHandler(
        server_url="",
        server_name=server_name,
    )
    had_token = handler.revoke(user_id)

    if had_token:
        return McpOAuthRevokeResponse(
            status="success",
            message=f"MCP OAuth access for '{server_name}' revoked successfully",
        )
    else:
        return McpOAuthRevokeResponse(
            status="success",
            message=f"No MCP OAuth credentials found for '{server_name}' to revoke",
        )
