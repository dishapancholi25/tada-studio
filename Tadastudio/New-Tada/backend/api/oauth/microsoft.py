"""Microsoft OAuth API endpoints.

Provides REST endpoints for the Microsoft Graph / Fabric OAuth flow:
- /api/microsoft-oauth/initiate - Start OAuth flow
- /api/microsoft-oauth/callback - Handle OAuth callback
- /api/microsoft-oauth/status - Check authentication status
- /api/microsoft-oauth/revoke - Revoke OAuth access
- /api/microsoft-oauth/test - Test API connection
- /api/microsoft-oauth/store-token - Store a manually-provided token
- /api/microsoft-oauth/sharepoint/sites - Browse SharePoint sites
- /api/microsoft-oauth/sharepoint/sites/{site_id}/drives - List document libraries
- /api/microsoft-oauth/sharepoint/drives/{drive_id}/children - Browse folder contents
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.api.auth.dependencies import get_current_user
from backend.services.oauth.microsoft_handler import (
    MicrosoftOAuthHandler,
    fabric_oauth_handler,
    microsoft_oauth_handler,
)


def _get_handler(provider: str = "microsoft"):
    """Return the correct OAuth handler for the given provider."""
    if provider == "fabric":
        return fabric_oauth_handler
    return microsoft_oauth_handler


logger = logging.getLogger(__name__)
LOG_PREFIX = "[MICROSOFT-OAUTH-API]"

router = APIRouter(prefix="/api/microsoft-oauth", tags=["microsoft-oauth"])


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


class StoreTokenRequest(BaseModel):
    """Request to store a manually-provided bearer token."""

    access_token: str
    provider: str = "fabric"


class StoreTokenResponse(BaseModel):
    """Response from storing a manual token."""

    status: str
    message: str
    user_id: str


class TestConnectionResponse(BaseModel):
    """Response from testing API connection."""

    status: str
    message: str
    user_name: str | None = None
    user_email: str | None = None


# --- Endpoints ---


@router.post("/initiate", response_model=InitiateOAuthResponse)
async def initiate_oauth(
    user: Dict[str, Any] = Depends(get_current_user),
    provider: str = Query(
        "microsoft", description="OAuth provider: 'microsoft' or 'fabric'"
    ),
) -> InitiateOAuthResponse:
    """Start the Microsoft OAuth flow.

    Returns an authorization URL to open in a popup for user consent.
    Use ``provider=fabric`` to request Fabric API scopes instead of Graph.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    handler = _get_handler(provider)
    logger.info(
        "%s Initiating OAuth for user=%s provider=%s", LOG_PREFIX, user_id, provider
    )

    try:
        authorization_url, state = await handler.initiate_flow(user_id)

        return InitiateOAuthResponse(
            authorization_url=authorization_url,
            state=state,
            user_id=user_id,
        )
    except Exception as e:
        logger.error("%s Failed to initiate OAuth: %s", LOG_PREFIX, e)
        raise HTTPException(status_code=500, detail=f"Failed to initiate OAuth: {e!s}")


@router.get("/callback", response_class=HTMLResponse)
async def oauth_callback(
    code: str = Query(..., description="Authorization code from Microsoft"),
    state: str = Query(..., description="State for CSRF verification"),
) -> HTMLResponse:
    """Handle the OAuth callback from Microsoft.

    Exchanges the authorization code for tokens and returns HTML that
    notifies the parent window via postMessage and closes the popup.
    """
    logger.info("%s Handling OAuth callback", LOG_PREFIX)

    try:
        # The callback is shared — try the Microsoft (Graph) handler first,
        # then Fabric. The state is stored per-provider, so only one will match.
        result = None
        for handler in (microsoft_oauth_handler, fabric_oauth_handler):
            try:
                result = await handler.handle_callback(code, state)
                break
            except ValueError:
                continue
        if result is None:
            raise ValueError("Invalid or expired state")

        # If this was a Fabric OAuth, also acquire a SQL token using the
        # refresh token so that execute_sql_query works out of the box.
        if handler is fabric_oauth_handler:
            try:
                await fabric_oauth_handler.acquire_cross_resource_token(
                    user_id=result["user_id"],
                    target_scope=MicrosoftOAuthHandler.SQL_SCOPE,
                    target_provider="fabric_sql",
                )
            except Exception as e:
                logger.warning(
                    "%s Failed to auto-acquire SQL token (non-fatal): %s",
                    LOG_PREFIX,
                    e,
                )

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Microsoft Authorization Complete</title>
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
    </style>
</head>
<body>
    <div class="container">
        <div class="success">&#10003;</div>
        <h1>Authorization Successful</h1>
        <p style="color: #aaa;">You can close this window now.</p>
    </div>
    <script>
        if (window.opener) {{
            window.opener.postMessage({{
                type: 'microsoft_oauth_complete',
                success: true,
                user_id: '{result["user_id"]}'
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
        logger.warning("%s OAuth callback validation error: %s", LOG_PREFIX, e)
        error_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Authorization Failed</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex; justify-content: center; align-items: center;
            height: 100vh; margin: 0; background: #1a1a2e; color: #eee;
        }
        .error { color: #f87171; font-size: 3rem; margin-bottom: 1rem; }
        .container { text-align: center; padding: 2rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="error">&#10007;</div>
        <h1>Authorization Failed</h1>
        <p style="color: #aaa;">Validation failed. Please try again.</p>
    </div>
    <script>
        if (window.opener) {
            window.opener.postMessage({
                type: 'microsoft_oauth_complete',
                success: false,
                error: 'Authorization validation failed'
            }, '*');
        }
        setTimeout(function() { window.close(); }, 3000);
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
            display: flex; justify-content: center; align-items: center;
            height: 100vh; margin: 0; background: #1a1a2e; color: #eee;
        }
        .error { color: #f87171; font-size: 3rem; margin-bottom: 1rem; }
        .container { text-align: center; padding: 2rem; }
    </style>
</head>
<body>
    <div class="container">
        <div class="error">&#10007;</div>
        <h1>Authorization Error</h1>
        <p style="color: #aaa;">An unexpected error occurred. Please try again.</p>
    </div>
    <script>
        if (window.opener) {
            window.opener.postMessage({
                type: 'microsoft_oauth_complete',
                success: false,
                error: 'An unexpected error occurred'
            }, '*');
        }
        setTimeout(function() { window.close(); }, 3000);
    </script>
</body>
</html>
"""
        return HTMLResponse(content=error_html, status_code=500)


@router.get("/status", response_model=OAuthStatusResponse)
async def get_oauth_status(
    user: Dict[str, Any] = Depends(get_current_user),
    provider: str = Query(
        "microsoft", description="OAuth provider: 'microsoft' or 'fabric'"
    ),
) -> OAuthStatusResponse:
    """Check Microsoft OAuth authentication status for the current user."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    handler = _get_handler(provider)
    status = handler.get_status(user_id)
    return OAuthStatusResponse(**status)


@router.delete("/revoke", response_model=RevokeResponse)
async def revoke_oauth(
    user: Dict[str, Any] = Depends(get_current_user),
    provider: str = Query(
        "microsoft", description="OAuth provider: 'microsoft' or 'fabric'"
    ),
) -> RevokeResponse:
    """Revoke Microsoft OAuth access for the current user."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    handler = _get_handler(provider)
    logger.info(
        "%s Revoking OAuth for user=%s provider=%s", LOG_PREFIX, user_id, provider
    )

    had_token = handler.revoke(user_id)

    # Also clean up the derived SQL token when revoking Fabric OAuth
    if provider == "fabric":
        from backend.services.oauth.storage import oauth_storage

        oauth_storage.delete_token(user_id, "fabric_sql")

    if had_token:
        return RevokeResponse(
            status="success",
            message="Microsoft OAuth access revoked successfully",
            user_id=user_id,
        )
    return RevokeResponse(
        status="success",
        message="No Microsoft OAuth credentials found to revoke",
        user_id=user_id,
    )


@router.post("/test", response_model=TestConnectionResponse)
async def test_connection(
    user: Dict[str, Any] = Depends(get_current_user),
    provider: str = Query(
        "microsoft", description="OAuth provider: 'microsoft' or 'fabric'"
    ),
) -> TestConnectionResponse:
    """Test the API connection.

    For ``microsoft``: calls GET /me on Graph API.
    For ``fabric``: calls GET /workspaces on Fabric API.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    handler = _get_handler(provider)
    logger.info(
        "%s Testing %s API connection for user=%s", LOG_PREFIX, provider, user_id
    )

    status = handler.get_status(user_id)
    if not status["is_authenticated"]:
        return TestConnectionResponse(
            status="error",
            message=f"Not authenticated with {provider}. Please connect first.",
        )

    try:
        access_token = await handler.get_valid_token(user_id)

        if provider == "fabric":
            # Test Fabric API — list workspaces
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    "https://api.fabric.microsoft.com/v1/workspaces",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()

            workspaces = response.json().get("value", [])
            ws_names = [ws.get("displayName", "?") for ws in workspaces[:3]]
            return TestConnectionResponse(
                status="success",
                message=f"Connected! Found {len(workspaces)} workspace(s): {', '.join(ws_names)}",
            )
        else:
            # Test Graph API — get user profile
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                response.raise_for_status()

            me_data = response.json()
            return TestConnectionResponse(
                status="success",
                message=f"Connected as {me_data.get('displayName', 'Unknown')}",
                user_name=me_data.get("displayName"),
                user_email=me_data.get("mail") or me_data.get("userPrincipalName"),
            )
    except httpx.HTTPStatusError as e:
        error_msg = f"API error: HTTP {e.response.status_code}"
        if e.response.status_code == 401:
            error_msg = "Token is invalid or expired. Please reconnect."
        elif e.response.status_code == 403:
            error_msg = "Insufficient permissions. Check app registration scopes."
        return TestConnectionResponse(status="error", message=error_msg)
    except Exception as e:
        return TestConnectionResponse(
            status="error",
            message=f"Connection test failed: {e!s}",
        )


@router.post("/store-token", response_model=StoreTokenResponse)
async def store_manual_token(
    body: StoreTokenRequest,
    user: Dict[str, Any] = Depends(get_current_user),
) -> StoreTokenResponse:
    """Store a manually-provided bearer token.

    Useful when the app registration lacks the required API permissions
    for the OAuth popup flow. The user obtains a token locally via
    ``az account get-access-token --resource https://api.fabric.microsoft.com``
    and pastes it here.
    """
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    logger.info(
        "%s Storing manual token for user=%s provider=%s",
        LOG_PREFIX,
        user_id,
        body.provider,
    )

    try:
        from backend.services.oauth.storage import oauth_storage

        # Store with a 1-hour expiry (standard Azure token lifetime)
        oauth_storage.store_token(
            user_id=user_id,
            provider=body.provider,
            client_id="manual",
            access_token=body.access_token,
            refresh_token=None,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            scope="manual",
        )

        return StoreTokenResponse(
            status="success",
            message="Token stored successfully",
            user_id=user_id,
        )
    except Exception as e:
        logger.error("%s Failed to store manual token: %s", LOG_PREFIX, e)
        raise HTTPException(status_code=500, detail=f"Failed to store token: {e!s}")


# ---------------------------------------------------------------------------
# SharePoint Browsing Endpoints (for config UI)
# ---------------------------------------------------------------------------

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


async def _graph_get(token: str, path: str, params: dict | None = None) -> dict:
    """Make an authenticated GET request to Microsoft Graph API."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{GRAPH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        if not resp.is_success:
            detail = resp.text[:200]
            raise HTTPException(status_code=resp.status_code, detail=detail)
        return resp.json()


async def _get_graph_token(user: Dict[str, Any]) -> str:
    """Get a valid Microsoft Graph token for the current user."""
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in claims")

    handler = _get_handler("microsoft")
    status = handler.get_status(user_id)
    if not status["is_authenticated"]:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with Microsoft. Please connect first.",
        )

    return await handler.get_valid_token(user_id)


class ResolveUrlRequest(BaseModel):
    """Request body for URL resolution."""

    url: str


@router.post("/sharepoint/resolve-url")
async def resolve_sharepoint_url(
    body: ResolveUrlRequest,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Resolve a SharePoint URL to site ID, drive ID, and folder path.

    Accepts URLs like:
    - https://tenant.sharepoint.com/sites/MySite
    - https://tenant.sharepoint.com/sites/MySite/Shared Documents/Folder
    - https://tenant.sharepoint.com/sites/MySite/Asset Library?xsdata=...

    Returns the resolved Graph API IDs for auto-populating the config UI.
    """
    token = await _get_graph_token(user)
    url = body.url.strip()

    # Strip query params and fragments
    clean_url = url.split("?")[0].split("#")[0].rstrip("/")

    # Remove protocol
    if clean_url.startswith("https://"):
        clean_url = clean_url[8:]
    elif clean_url.startswith("http://"):
        clean_url = clean_url[7:]

    # Parse: hostname/sites/SiteName[/LibraryOrFolder/...]
    parts = clean_url.split("/")
    hostname = parts[0]

    # Find site path: /sites/X or /teams/X
    site_path = ""
    library_hint = ""
    for i, part in enumerate(parts[1:], 1):
        if part.lower() in ("sites", "teams") and i + 1 < len(parts):
            site_path = f"/{parts[i]}/{parts[i + 1]}"
            # Everything after site path could be library/folder
            remaining = parts[i + 2 :]
            if remaining:
                # URL-decode the library name (e.g., "Asset%20Library" -> "Asset Library")
                from urllib.parse import unquote

                library_hint = unquote(remaining[0])
            break

    if not site_path:
        raise HTTPException(
            status_code=400,
            detail="Could not parse site path from URL. Expected format: https://tenant.sharepoint.com/sites/MySite/...",
        )

    result: Dict[str, Any] = {
        "hostname": hostname,
        "site_path": site_path,
        "library_hint": library_hint,
    }

    # Resolve site
    try:
        site_data = await _graph_get(token, f"/sites/{hostname}:{site_path}")
        result["site_id"] = site_data.get("id", "")
        result["site_name"] = site_data.get("displayName", "")
        result["site_url"] = site_data.get("webUrl", "")
    except Exception:
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve site: {hostname}{site_path}",
        )

    # Try to match library by name
    if library_hint and result.get("site_id"):
        try:
            drives_data = await _graph_get(token, f"/sites/{result['site_id']}/drives")
            for d in drives_data.get("value", []):
                if d.get("name", "").lower() == library_hint.lower():
                    result["drive_id"] = d.get("id", "")
                    result["drive_name"] = d.get("name", "")
                    break
        except Exception:
            pass  # Non-critical: library match is best-effort

    return result


@router.get("/sharepoint/sites")
async def list_sharepoint_sites(
    user: Dict[str, Any] = Depends(get_current_user),
    search: str = Query("", description="Optional search filter for site names"),
) -> Dict[str, Any]:
    """List accessible SharePoint sites for the config UI site picker."""
    token = await _get_graph_token(user)

    data = await _graph_get(
        token, "/sites", params={"search": search or "*", "$top": "100"}
    )
    sites = [
        {
            "id": s.get("id", ""),
            "name": s.get("displayName", ""),
            "url": s.get("webUrl", ""),
            "description": s.get("description", ""),
        }
        for s in data.get("value", [])
    ]
    # Sort alphabetically by name
    sites.sort(key=lambda s: s["name"].lower())
    return {"sites": sites, "count": len(sites)}


@router.get("/sharepoint/sites/{site_id}/drives")
async def list_sharepoint_drives(
    site_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List document libraries (drives) for a SharePoint site."""
    token = await _get_graph_token(user)

    data = await _graph_get(token, f"/sites/{site_id}/drives")
    drives = [
        {
            "id": d.get("id", ""),
            "name": d.get("name", ""),
            "description": d.get("description", ""),
            "web_url": d.get("webUrl", ""),
            "drive_type": d.get("driveType", ""),
        }
        for d in data.get("value", [])
    ]
    drives.sort(key=lambda d: d["name"].lower())
    return {"drives": drives, "count": len(drives)}


@router.get("/sharepoint/drives/{drive_id}/children")
async def list_drive_children(
    drive_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    folder_id: str = Query(
        "root", description="Folder item ID, or 'root' for drive root"
    ),
) -> Dict[str, Any]:
    """List folders inside a drive folder (for the folder tree browser).

    Only returns folders, not files — this is for navigation/scoping only.
    """
    token = await _get_graph_token(user)

    path = f"/drives/{drive_id}/items/{folder_id}/children"
    params = {
        "$filter": "folder ne null",
        "$select": "id,name,folder,webUrl,parentReference",
        "$top": "200",
        "$orderby": "name asc",
    }
    data = await _graph_get(token, path, params=params)

    folders = [
        {
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "child_count": item.get("folder", {}).get("childCount", 0),
            "web_url": item.get("webUrl", ""),
        }
        for item in data.get("value", [])
    ]
    return {"folders": folders, "count": len(folders)}


# ---------------------------------------------------------------------------
# OneDrive Browsing Endpoints (for config UI)
# ---------------------------------------------------------------------------


@router.get("/onedrive/drives")
async def list_onedrive_drives(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """List the user's OneDrive drives for the config UI drive picker."""
    token = await _get_graph_token(user)

    # Get default drive
    default_drive = await _graph_get(
        token, "/me/drive", params={"$select": "id,name,driveType,quota,webUrl"}
    )
    drives = [
        {
            "id": default_drive.get("id", ""),
            "name": default_drive.get("name", "OneDrive"),
            "description": "Personal OneDrive",
            "web_url": default_drive.get("webUrl", ""),
            "drive_type": default_drive.get("driveType", "personal"),
            "is_default": True,
        }
    ]

    # Get additional drives (shared drives, etc.)
    try:
        additional = await _graph_get(
            token, "/me/drives", params={"$select": "id,name,driveType,quota,webUrl"}
        )
        default_id = default_drive.get("id", "")
        for d in additional.get("value", []):
            if d.get("id") != default_id:
                drives.append(
                    {
                        "id": d.get("id", ""),
                        "name": d.get("name", ""),
                        "description": d.get("driveType", ""),
                        "web_url": d.get("webUrl", ""),
                        "drive_type": d.get("driveType", ""),
                        "is_default": False,
                    }
                )
    except Exception:
        pass  # Additional drives may not be available

    return {"drives": drives, "count": len(drives)}


@router.get("/onedrive/drives/{drive_id}/children")
async def list_onedrive_drive_children(
    drive_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    folder_id: str = Query(
        "root", description="Folder item ID, or 'root' for drive root"
    ),
) -> Dict[str, Any]:
    """List folders inside a OneDrive folder (for the folder tree browser)."""
    token = await _get_graph_token(user)

    path = f"/drives/{drive_id}/items/{folder_id}/children"
    params = {
        "$filter": "folder ne null",
        "$select": "id,name,folder,webUrl,parentReference",
        "$top": "200",
        "$orderby": "name asc",
    }
    data = await _graph_get(token, path, params=params)

    folders = [
        {
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "child_count": item.get("folder", {}).get("childCount", 0),
            "web_url": item.get("webUrl", ""),
        }
        for item in data.get("value", [])
    ]
    return {"folders": folders, "count": len(folders)}
