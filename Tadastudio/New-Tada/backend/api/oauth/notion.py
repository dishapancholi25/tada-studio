"""Notion OAuth API endpoints.

This module provides REST endpoints for the Notion MCP OAuth flow:
- /api/notion-oauth/initiate - Start OAuth flow
- /api/notion-oauth/callback - Handle OAuth callback
- /api/notion-oauth/status - Check authentication status
- /api/notion-oauth/revoke - Revoke OAuth access
- /api/notion-oauth/test - Test MCP connection
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.api.auth.dependencies import get_current_user
from backend.services.oauth.notion_handler import notion_oauth_handler

logger = logging.getLogger(__name__)
LOG_PREFIX = "[NOTION-OAUTH-API]"

router = APIRouter(prefix="/api/notion-oauth", tags=["notion-oauth"])


# --- Request/Response Models ---


class InitiateOAuthResponse(BaseModel):
    """Response from initiating OAuth flow."""

    authorization_url: str
    state: str
    user_id: str
    message: str = "Redirect user to authorization_url in popup"


class OAuthStatusResponse(BaseModel):
    """OAuth authentication status."""

    is_authenticated: bool
    has_token: bool
    has_client_registration: bool
    token_expired: bool
    expires_at: str | None = None
    scope: str | None = None


class RevokeResponse(BaseModel):
    """Response from revoking OAuth access."""

    status: str
    message: str
    user_id: str


class TestConnectionResponse(BaseModel):
    """Response from testing MCP connection."""

    status: str
    message: str
    tools_count: int | None = None
    tools: list[dict] | None = None


# --- Endpoints ---


@router.post("/initiate", response_model=InitiateOAuthResponse)
async def initiate_oauth(
    user: Dict[str, Any] = Depends(get_current_user),
) -> InitiateOAuthResponse:
    """Start the OAuth flow for Notion MCP.

    This endpoint:
    1. Registers a dynamic OAuth client with Notion
    2. Generates an authorization URL
    3. Returns the URL for the frontend to open in a popup

    Returns:
        InitiateOAuthResponse with authorization_url to redirect user to.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    logger.info("%s Initiating OAuth for user=%s", LOG_PREFIX, user_id)

    try:
        authorization_url, state = await notion_oauth_handler.initiate_flow(user_id)

        return InitiateOAuthResponse(
            authorization_url=authorization_url,
            state=state,
            user_id=user_id,
            message="Redirect user to authorization_url in popup",
        )
    except Exception as e:
        logger.error("%s Failed to initiate OAuth: %s", LOG_PREFIX, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate OAuth: {str(e)}"
        )


@router.get("/callback", response_class=HTMLResponse)
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Notion"),
    state: str = Query(..., description="State for CSRF verification"),
) -> HTMLResponse:
    """Handle the OAuth callback from Notion.

    This endpoint is called by Notion after the user authorizes the app.
    It exchanges the authorization code for tokens and returns HTML that:
    1. Posts a message to the parent window
    2. Closes the popup

    Args:
        code: Authorization code from Notion.
        state: State parameter for CSRF verification.

    Returns:
        HTML page that notifies parent window and closes popup.
    """
    logger.info("%s Handling OAuth callback", LOG_PREFIX)

    try:
        result = await notion_oauth_handler.handle_callback(code, state)

        # Success - return HTML that closes popup and notifies parent
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Notion Authorization Complete</title>
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
        <div class="success">✓</div>
        <h1>Authorization Successful</h1>
        <p>You can close this window now.</p>
    </div>
    <script>
        // Notify parent window
        if (window.opener) {{
            window.opener.postMessage({{
                type: 'notion_oauth_complete',
                success: true,
                user_id: '{result["user_id"]}'
            }}, '*');
        }}
        // Close popup after a short delay
        setTimeout(function() {{
            window.close();
        }}, 1500);
    </script>
</body>
</html>
"""
        return HTMLResponse(content=html_content)

    except ValueError as e:
        # CSRF or validation error
        logger.warning("%s OAuth callback validation error: %s", LOG_PREFIX, e)
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
        <div class="error">✗</div>
        <h1>Authorization Failed</h1>
        <p>Authorization validation failed. Please try again or contact support.</p>
    </div>
    <script>
        if (window.opener) {
            window.opener.postMessage({
                type: 'notion_oauth_complete',
                success: false,
                error: 'Authorization validation failed. Please try again or contact support.'
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
        logger.error("%s OAuth callback error: %s", LOG_PREFIX, e)
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
        <div class="error">✗</div>
        <h1>Authorization Error</h1>
        <p>An unexpected error occurred. Please try again.</p>
    </div>
    <script>
        if (window.opener) {
            window.opener.postMessage({
                type: 'notion_oauth_complete',
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


@router.get("/status", response_model=OAuthStatusResponse)
async def get_oauth_status(
    user: Dict[str, Any] = Depends(get_current_user),
) -> OAuthStatusResponse:
    """Check OAuth authentication status for the current user.

    Returns whether the user has valid Notion OAuth credentials.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    status = notion_oauth_handler.get_status(user_id)

    return OAuthStatusResponse(**status)


@router.delete("/revoke", response_model=RevokeResponse)
async def revoke_oauth(
    user: Dict[str, Any] = Depends(get_current_user),
) -> RevokeResponse:
    """Revoke Notion OAuth access for the current user.

    Deletes all stored OAuth data (client registration, tokens, state).
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    logger.info("%s Revoking OAuth for user=%s", LOG_PREFIX, user_id)

    had_token = notion_oauth_handler.revoke(user_id)

    if had_token:
        return RevokeResponse(
            status="success",
            message="Notion OAuth access revoked successfully",
            user_id=user_id,
        )
    else:
        return RevokeResponse(
            status="success",
            message="No Notion OAuth credentials found to revoke",
            user_id=user_id,
        )


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(
    user: Dict[str, Any] = Depends(get_current_user),
) -> TestConnectionResponse:
    """Test the Notion MCP connection.

    Attempts to connect to the Notion MCP server and list available tools.
    Requires the user to have valid OAuth credentials.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    logger.info("%s Testing MCP connection for user=%s", LOG_PREFIX, user_id)

    # Check if user has OAuth credentials
    status = notion_oauth_handler.get_status(user_id)
    if not status["is_authenticated"]:
        return TestConnectionResponse(
            status="error",
            message="Not authenticated with Notion. Please connect first.",
        )

    try:
        # Get valid token
        access_token = await notion_oauth_handler.get_valid_token(user_id)

        # Try to list tools from Notion MCP
        import httpx
        import json

        base_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        async with httpx.AsyncClient() as client:
            # Initialize MCP connection
            init_response = await client.post(
                "https://mcp.notion.com/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"execute": True},
                            "resources": {"read": True},
                        },
                        "clientInfo": {
                            "name": "agenticstudio-test",
                            "version": "1.0.0",
                        },
                    },
                    "id": 1,
                },
                headers=base_headers,
                timeout=30.0,
            )
            init_response.raise_for_status()

            # Capture session ID from response headers
            session_id = init_response.headers.get("Mcp-Session-Id")

            # Parse response (handle both JSON and SSE)
            content_type = init_response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                # Parse SSE response
                for line in init_response.text.strip().split("\n"):
                    if line.startswith("data:"):
                        init_data = json.loads(line[5:].strip())
                        break
            else:
                init_data = init_response.json()

            # Check for session ID in result
            if not session_id and "result" in init_data:
                session_id = init_data["result"].get("sessionId")

            # Prepare headers for tools/list (include session ID if we have one)
            tools_headers = base_headers.copy()
            if session_id:
                tools_headers["Mcp-Session-Id"] = session_id

            # List tools
            tools_response = await client.post(
                "https://mcp.notion.com/mcp",
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": 2,
                },
                headers=tools_headers,
                timeout=30.0,
            )
            tools_response.raise_for_status()

            # Parse response (handle both JSON and SSE)
            content_type = tools_response.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                for line in tools_response.text.strip().split("\n"):
                    if line.startswith("data:"):
                        tools_data = json.loads(line[5:].strip())
                        break
            else:
                tools_data = tools_response.json()

            tools = tools_data.get("result", {}).get("tools", [])

            return TestConnectionResponse(
                status="success",
                message=f"Successfully connected to Notion MCP. Found {len(tools)} tools.",
                tools_count=len(tools),
                tools=[
                    {"name": t["name"], "description": t.get("description", "")}
                    for t in tools
                ],
            )

    except httpx.HTTPStatusError as e:
        # Try to get more details from response body
        error_detail = ""
        try:
            error_detail = e.response.text
        except Exception:
            pass
        logger.error(
            "%s MCP connection HTTP error: %s - %s", LOG_PREFIX, e, error_detail
        )
        return TestConnectionResponse(
            status="error",
            message=f"Failed to connect to Notion MCP: HTTP {e.response.status_code} - {error_detail[:200]}",
        )
    except Exception as e:
        logger.error("%s MCP connection error: %s", LOG_PREFIX, e)
        return TestConnectionResponse(
            status="error",
            message=f"Failed to connect to Notion MCP: {str(e)}",
        )
