"""SharePoint MCP Server using FastMCP.

Exposes SharePoint operations as MCP tools via Microsoft Graph API.
Runs as a stdio subprocess spawned by the MCP client manager.

OAuth Scope Requirements:
- Read tools (list_sites, search_files, list_drive_items, get_file_content, get_site_info,
  get_list_items): Sites.Read.All, Files.Read.All
- Write tools (upload_file, create_folder, create_list_item, create_list,
  update_list_item, rename_file_or_folder, move_file, share_file_or_folder):
  Files.ReadWrite.All, Sites.ReadWrite.All
- Delete tools (delete_file_or_folder, delete_list_item):
  Files.ReadWrite.All, Sites.ReadWrite.All
"""

import atexit
import base64
import json
import logging
import os
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from backend.tools.shared.text_extraction import (
    MAX_EXTRACT_SIZE as _MAX_EXTRACT_SIZE,
    TEXT_EXTENSIONS,
    extract_text_from_binary as _extract_text_from_binary,
)

from backend.tools.shared.search_helpers import (
    build_kql_query,
    extract_aggregations,
    parse_search_hits,
)

from .graph_client import GraphAPIError, SharePointGraphClient

logger = logging.getLogger(__name__)

mcp = FastMCP("SharePoint MCP Server")

_client: Optional[SharePointGraphClient] = None


def _get_client() -> SharePointGraphClient:
    """Lazy-initialize the Graph API client from environment variables.

    Checks for a delegated token first (SHAREPOINT_ACCESS_TOKEN),
    falling back to client_credentials (TENANT/CLIENT/SECRET).
    """
    global _client
    if _client is None:
        # Delegated mode: pre-obtained OAuth token injected by mcp_client_manager
        delegated_token = os.environ.get("SHAREPOINT_ACCESS_TOKEN", "").strip()
        if delegated_token:
            logger.info("Using delegated (OAuth) token for SharePoint Graph API")
            _client = SharePointGraphClient(access_token=delegated_token)
        else:
            # Fallback: client_credentials flow
            tenant_id = os.environ.get("SHAREPOINT_TENANT_ID", "")
            client_id = os.environ.get("SHAREPOINT_CLIENT_ID", "")
            client_secret = os.environ.get("SHAREPOINT_CLIENT_SECRET", "")

            if not all([tenant_id, client_id, client_secret]):
                raise ValueError(
                    "Missing authentication: set SHAREPOINT_ACCESS_TOKEN (delegated) "
                    "or SHAREPOINT_TENANT_ID + SHAREPOINT_CLIENT_ID + SHAREPOINT_CLIENT_SECRET"
                )

            _client = SharePointGraphClient(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
    return _client


def _cleanup() -> None:
    """Close the HTTP client on process exit."""
    global _client
    if _client is not None:
        import asyncio

        try:
            asyncio.run(_client.close())
        except Exception:
            pass


atexit.register(_cleanup)


def _get_default_site_id() -> Optional[str]:
    """Get a site ID from the SHAREPOINT_SITE_ID or SHAREPOINT_SITE_URL env var.

    Prefers SHAREPOINT_SITE_ID (Graph API ID set by the config UI picker).
    Falls back to converting SHAREPOINT_SITE_URL into a Graph API site identifier.
    """
    # Preferred: direct Graph API site ID from the config UI picker
    site_id = os.environ.get("SHAREPOINT_SITE_ID", "").strip()
    if site_id:
        return site_id

    # Fallback: convert URL to Graph API format
    site_url = os.environ.get("SHAREPOINT_SITE_URL", "").strip()
    if not site_url:
        return None

    # Remove protocol
    url = site_url
    if url.startswith("https://"):
        url = url[8:]
    elif url.startswith("http://"):
        url = url[7:]
    url = url.rstrip("/")

    # Split into hostname and path: "tenant.sharepoint.com/sites/mysite"
    parts = url.split("/", 1)
    hostname = parts[0]
    path = f"/{parts[1]}" if len(parts) > 1 else ""

    if path:
        return f"{hostname}:{path}"
    return hostname


def _get_default_drive_id() -> Optional[str]:
    """Get a default drive ID from env var (set by the config UI library picker).

    Supports both SHAREPOINT_DRIVE_IDS (comma-separated, multi-library) and
    the legacy SHAREPOINT_DRIVE_ID (single). Returns the first ID.
    """
    multi = os.environ.get("SHAREPOINT_DRIVE_IDS", "").strip()
    if multi:
        first = multi.split(",")[0].strip()
        if first:
            return first
    return os.environ.get("SHAREPOINT_DRIVE_ID", "").strip() or None


def _get_scoped_folder_paths() -> list:
    """Get folder paths to scope searches to, from env var.

    SHAREPOINT_FOLDER_PATHS is a comma-separated list of folder paths
    set by the config UI folder tree picker.
    """
    raw = os.environ.get("SHAREPOINT_FOLDER_PATHS", "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _get_all_scoped_drive_ids() -> list:
    """Get all configured drive IDs from SHAREPOINT_DRIVE_IDS env var.

    Returns a list of all drive IDs, or empty list if not configured.
    """
    raw = os.environ.get("SHAREPOINT_DRIVE_IDS", "").strip()
    if not raw:
        single = os.environ.get("SHAREPOINT_DRIVE_ID", "").strip()
        return [single] if single else []
    return [d.strip() for d in raw.split(",") if d.strip()]


def _is_item_id(value: str) -> bool:
    """Determine if a value is a Graph API item ID vs a file path.

    Graph API item IDs are opaque alphanumeric strings (e.g., '01QIGVBRV6Y2GOVW...')
    that never contain slashes. File paths always contain at least one '/'.
    """
    if not value or not value.strip():
        return False
    return "/" not in value and "\\" not in value


def _format_error(e: Exception) -> dict:
    """Format an exception into a standardized error response."""
    if isinstance(e, GraphAPIError):
        return {
            "error": e.message,
            "error_code": e.error_code,
            "status_code": e.status_code,
        }
    elif isinstance(e, ValueError):
        return {"error": str(e), "error_code": "ConfigurationError"}
    else:
        return {"error": str(e), "error_code": "UnexpectedError"}


async def _resolve_site_id(client: SharePointGraphClient, site_id: str) -> str:
    """Resolve a site hostname:path format to a proper Graph API site ID."""
    if ":" in site_id or "." in site_id:
        site_data = await client.graph_get(f"/sites/{site_id}")
        return site_data.get("id", site_id)
    return site_id


def _build_drive_base(site_id: str, drive_id: str) -> str:
    """Build the base Graph API path for a drive."""
    if drive_id:
        return f"/sites/{site_id}/drives/{drive_id}"
    return f"/sites/{site_id}/drive"


# Chunk size for large file uploads (3.125 MB, must be multiple of 320 KiB)
_UPLOAD_CHUNK_SIZE = 3_276_800
# Simple upload threshold (4MB)
_SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024


# ---------------------------------------------------------------------------
# Read Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_sites(search_query: str = "") -> dict:
    """List accessible SharePoint sites, optionally filtered by search query.

    Use this first to discover available sites and their IDs. The site 'id'
    from results is required by most other SharePoint tools.

    Workflow: list_sites() -> get_site_info() or list_drive_items() -> get_file_content()

    Args:
        search_query: Optional search term to filter sites by name (e.g., "Marketing").
                      If empty, returns all accessible sites.

    Returns:
        Dictionary with 'sites' list. Each site has: id, name, url, description,
        created, last_modified. Use the 'id' field with other tools.
    """
    client = _get_client()

    try:
        # When a default site is configured, return only that site's info
        default_site_id = _get_default_site_id()
        if default_site_id:
            site = await client.graph_get(f"/sites/{default_site_id}")
            sites = [
                {
                    "id": site.get("id", ""),
                    "name": site.get("displayName", ""),
                    "url": site.get("webUrl", ""),
                    "description": site.get("description", ""),
                    "created": site.get("createdDateTime", ""),
                    "last_modified": site.get("lastModifiedDateTime", ""),
                }
            ]
            return {"sites": sites, "count": 1, "scoped": True}

        raw_sites, truncated = await client.graph_get_all_pages(
            "/sites", params={"search": search_query or "*"}
        )

        sites = []
        for site in raw_sites:
            sites.append(
                {
                    "id": site.get("id", ""),
                    "name": site.get("displayName", ""),
                    "url": site.get("webUrl", ""),
                    "description": site.get("description", ""),
                    "created": site.get("createdDateTime", ""),
                    "last_modified": site.get("lastModifiedDateTime", ""),
                }
            )

        result: Dict[str, Any] = {"sites": sites, "count": len(sites)}
        if truncated:
            result["truncated"] = True
        return result
    except Exception as e:
        return {**_format_error(e), "sites": [], "count": 0}


@mcp.tool()
async def search_files(
    query: str,
    site_id: str = "",
    file_types: str = "",
    author: str = "",
    date_from: str = "",
    date_to: str = "",
    path: str = "",
    sort_by: str = "",
    page_size: int = 25,
    page: int = 0,
) -> dict:
    """Search for files across SharePoint by name or content keywords.

    Searches all accessible SharePoint sites. Returns file metadata including
    'id' and 'drive_id' which can be passed directly to get_file_content.

    The query parameter supports full KQL (Keyword Query Language) syntax, or
    you can use the convenience filter parameters which build KQL for you.

    KQL examples you can pass directly in ``query``:
    - "quarterly report filetype:pptx"
    - "budget author:\\"Jane Doe\\""
    - "proposal lastModifiedTime>=2024-01-01"
    - "Acme path:\\"/sites/Sales/Proposals\\""

    Args:
        query: Search query — matches file names and content. Supports KQL
               syntax (e.g., "quarterly report", "budget filetype:xlsx",
               "project plan author:\\"John\\"").
        site_id: Optional site ID to scope the search. Get from list_sites results.
        file_types: Comma-separated file extensions to filter by
                    (e.g., "pptx,docx,pdf"). Appends filetype: KQL filters.
        author: Filter results to a specific author display name.
        date_from: ISO date (YYYY-MM-DD). Only return files modified on or after
                   this date.
        date_to: ISO date (YYYY-MM-DD). Only return files modified on or before
                 this date.
        path: SharePoint path to scope results (e.g., "/sites/Sales/Proposals").
        sort_by: Sort results — one of "lastModifiedDateTime", "name", "size",
                 or "lastModifiedDateTime desc" (append " desc" for descending).
                 Default is relevance ranking.
        page_size: Number of results per page (1-500, default 25).
        page: Zero-based page index for pagination (default 0 = first page).

    Returns:
        Dictionary with 'files' list, 'total' count of all matching results,
        'page' index, 'page_size', and 'more_results_available' flag.
        Each file has: id, name, url, size, last_modified, created_by,
        site_id, drive_id, and snippet (highlighted matching text).
        Use 'id' and 'drive_id' with get_file_content to retrieve the file.
    """
    client = _get_client()

    if not site_id:
        site_id = _get_default_site_id() or ""

    try:
        # Apply default folder path scoping if no explicit path filter
        effective_path = path
        if not effective_path:
            scoped_paths = _get_scoped_folder_paths()
            if scoped_paths:
                # Use the first scoped path as the KQL path filter
                effective_path = scoped_paths[0]

        # Build KQL query from convenience params
        kql = build_kql_query(
            query,
            file_types=file_types,
            author=author,
            date_from=date_from,
            date_to=date_to,
            path=effective_path,
        )

        page_size = max(1, min(page_size, 500))
        offset = max(0, page) * page_size

        request_body: Dict[str, Any] = {
            "entityTypes": ["driveItem"],
            "query": {"queryString": kql},
            "from": offset,
            "size": page_size,
        }

        # Sort
        if sort_by:
            field = sort_by.strip()
            descending = False
            if field.endswith(" desc"):
                field = field[:-5].strip()
                descending = True
            elif field.endswith(" asc"):
                field = field[:-4].strip()
            request_body["sortProperties"] = [
                {"name": field, "isDescending": descending}
            ]

        # Request aggregations for facets
        request_body["aggregations"] = [
            {
                "field": "fileType",
                "size": 10,
                "bucketDefinition": {"sortBy": "count", "isDescending": True},
            },
            {
                "field": "lastModifiedTime",
                "size": 5,
                "bucketDefinition": {
                    "sortBy": "keyAsString",
                    "isDescending": True,
                    "ranges": [
                        {"from": "", "to": "2024-01-01T00:00:00Z"},
                        {"from": "2024-01-01T00:00:00Z", "to": "2025-01-01T00:00:00Z"},
                        {"from": "2025-01-01T00:00:00Z", "to": "2026-01-01T00:00:00Z"},
                        {"from": "2026-01-01T00:00:00Z", "to": ""},
                    ],
                },
            },
        ]

        search_request: Dict[str, Any] = {"requests": [request_body]}

        data = await client.graph_post("/search/query", search_request)

        files, total, more_available = parse_search_hits(data)

        facets = extract_aggregations(data)

        # Post-filter by configured drive IDs
        scoped_drives = _get_all_scoped_drive_ids()
        scope_filtered = False
        if scoped_drives:
            drive_set = set(scoped_drives)
            files = [f for f in files if f.get("drive_id") in drive_set]
            scope_filtered = True

        result: Dict[str, Any] = {
            "files": files,
            "total": total,
            "count": len(files),
            "page": page,
            "page_size": page_size,
            "more_results_available": more_available,
            "query": kql,
        }
        if facets:
            result["facets"] = facets
        if scope_filtered:
            result["scope_filtered"] = True
            result["scope_drives"] = scoped_drives

        return result
    except Exception as e:
        return {**_format_error(e), "files": [], "count": 0, "total": 0}


@mcp.tool()
async def search_content(
    query: str,
    entity_types: str = "driveItem,listItem",
    site_id: str = "",
    file_types: str = "",
    author: str = "",
    date_from: str = "",
    date_to: str = "",
    path: str = "",
    sort_by: str = "",
    page_size: int = 25,
    page: int = 0,
) -> dict:
    """Search across all SharePoint content types — files, list items, and site pages.

    Unlike search_files (which only searches files/driveItems), this tool
    searches across multiple entity types including list items and site pages.
    Ideal for broad knowledge discovery: "What do we know about Client X?"

    Args:
        query: Search query — supports KQL syntax. Examples:
               "Acme Corp proposal", "budget filetype:xlsx",
               "project plan author:\\"John\\"".
        entity_types: Comma-separated entity types to search. Options:
                      "driveItem" (files), "listItem" (list items/site pages),
                      "site" (sites). Default: "driveItem,listItem".
        site_id: Optional site ID to scope the search.
        file_types: Comma-separated file extensions (e.g., "pptx,docx,pdf").
        author: Filter to a specific author display name.
        date_from: ISO date (YYYY-MM-DD). Only results modified on or after.
        date_to: ISO date (YYYY-MM-DD). Only results modified on or before.
        path: SharePoint path to scope results.
        sort_by: Sort field — "lastModifiedDateTime", "name", etc.
                 Append " desc" for descending.
        page_size: Results per page (1-500, default 25).
        page: Zero-based page index (default 0).

    Returns:
        Dictionary with 'results' list, 'total', pagination info, and 'facets'.
        Each result has: id, name, url, size, last_modified, created_by,
        site_id, drive_id, snippet (highlighted text), and entity_type.
    """
    client = _get_client()

    if not site_id:
        site_id = _get_default_site_id() or ""

    try:
        effective_path = path
        if not effective_path:
            scoped_paths = _get_scoped_folder_paths()
            if scoped_paths:
                effective_path = scoped_paths[0]

        kql = build_kql_query(
            query,
            file_types=file_types,
            author=author,
            date_from=date_from,
            date_to=date_to,
            path=effective_path,
        )

        types = [t.strip() for t in entity_types.split(",") if t.strip()]
        if not types:
            types = ["driveItem", "listItem"]

        page_size = max(1, min(page_size, 500))
        offset = max(0, page) * page_size

        request_body: Dict[str, Any] = {
            "entityTypes": types,
            "query": {"queryString": kql},
            "from": offset,
            "size": page_size,
        }

        if sort_by:
            field = sort_by.strip()
            descending = False
            if field.endswith(" desc"):
                field = field[:-5].strip()
                descending = True
            elif field.endswith(" asc"):
                field = field[:-4].strip()
            request_body["sortProperties"] = [
                {"name": field, "isDescending": descending}
            ]

        request_body["aggregations"] = [
            {
                "field": "fileType",
                "size": 10,
                "bucketDefinition": {"sortBy": "count", "isDescending": True},
            },
        ]

        data = await client.graph_post("/search/query", {"requests": [request_body]})

        # Parse results — same structure, but we tag each with entity_type
        results = []
        total = 0
        more_available = False

        for response in data.get("value", []):
            for hit_container in response.get("hitsContainers", []):
                total += hit_container.get("total", 0)
                more_available = more_available or hit_container.get(
                    "moreResultsAvailable", False
                )

                for hit in hit_container.get("hits", []):
                    resource = hit.get("resource", {})
                    parent_ref = resource.get("parentReference", {})
                    odata_type = resource.get("@odata.type", "")

                    item: Dict[str, Any] = {
                        "id": resource.get("id", ""),
                        "name": resource.get("name") or resource.get("displayName", ""),
                        "url": resource.get("webUrl", ""),
                        "last_modified": resource.get("lastModifiedDateTime", ""),
                        "created_by": (
                            resource.get("createdBy", {})
                            .get("user", {})
                            .get("displayName", "")
                        ),
                        "site_id": parent_ref.get("siteId", ""),
                    }

                    # Add drive-specific fields for driveItems
                    if "driveItem" in odata_type:
                        item["entity_type"] = "driveItem"
                        item["size"] = resource.get("size", 0)
                        item["drive_id"] = parent_ref.get("driveId", "")
                    elif "listItem" in odata_type:
                        item["entity_type"] = "listItem"
                        item["list_id"] = parent_ref.get(
                            "listId", resource.get("listId", "")
                        )
                    elif "site" in odata_type:
                        item["entity_type"] = "site"
                        item["description"] = resource.get("description", "")
                    else:
                        item["entity_type"] = (
                            odata_type.split(".")[-1] if odata_type else "unknown"
                        )

                    summary = hit.get("hitHighlightedSummary") or hit.get("summary", "")
                    if summary:
                        item["snippet"] = summary

                    results.append(item)

        facets = extract_aggregations(data)

        # Post-filter by configured scope
        scoped_drives = _get_all_scoped_drive_ids()
        scoped_site = _get_default_site_id()
        scope_filtered = False
        if scoped_drives or scoped_site:
            drive_set = set(scoped_drives) if scoped_drives else None
            filtered = []
            for item in results:
                etype = item.get("entity_type", "")
                if etype == "driveItem" and drive_set:
                    if item.get("drive_id") in drive_set:
                        filtered.append(item)
                elif etype in ("listItem", "site") and scoped_site:
                    if item.get("site_id") == scoped_site:
                        filtered.append(item)
                else:
                    # No filter applicable for this entity type
                    filtered.append(item)
            results = filtered
            scope_filtered = True

        result: Dict[str, Any] = {
            "results": results,
            "total": total,
            "count": len(results),
            "page": page,
            "page_size": page_size,
            "more_results_available": more_available,
            "query": kql,
        }
        if facets:
            result["facets"] = facets
        if scope_filtered:
            result["scope_filtered"] = True
            if scoped_drives:
                result["scope_drives"] = scoped_drives

        return result
    except Exception as e:
        return {**_format_error(e), "results": [], "count": 0, "total": 0}


@mcp.tool()
async def list_drive_items(
    site_id: str = "", drive_id: str = "", folder_path: str = "/"
) -> dict:
    """List files and folders in a SharePoint document library.

    Browse drive contents to find files. Each result includes 'id' and 'drive_id'
    which should be passed to get_file_content to retrieve file contents.

    Workflow:
    1. list_drive_items(site_id="...") — list root of default document library
    2. list_drive_items(site_id="...", folder_path="/Reports") — browse a subfolder
    3. get_file_content(site_id="...", item_id="<id>", drive_id="<drive_id>") — get a file

    Args:
        site_id: SharePoint site ID (from list_sites). If empty, uses pre-configured site.
        drive_id: Document library ID (from get_site_info 'drives' list).
                  If empty, uses the site's default document library.
        folder_path: Folder path to list (e.g., "/Reports", "/Shared Documents/Projects").
                     Use "/" for the drive root. Defaults to root.

    Returns:
        Dictionary with 'items' list. Each item has: id, name, type ('file'/'folder'),
        size, url, last_modified, created, drive_id. Files also have mime_type.
        Folders also have child_count.
    """
    client = _get_client()

    if not site_id:
        site_id = _get_default_site_id()
        if not site_id:
            return {
                "error": "site_id is required (or set SHAREPOINT_SITE_URL env var)",
                "items": [],
                "count": 0,
            }

    if not drive_id:
        drive_id = _get_default_drive_id() or ""

    try:
        site_id = await _resolve_site_id(client, site_id)
        base = _build_drive_base(site_id, drive_id)

        if folder_path and folder_path != "/":
            path = folder_path.strip("/")
            endpoint = f"{base}/root:/{path}:/children"
        else:
            endpoint = f"{base}/root/children"

        raw_items, truncated = await client.graph_get_all_pages(
            endpoint,
            params={
                "$top": "50",
                "$select": "id,name,size,webUrl,lastModifiedDateTime,createdDateTime,folder,file,parentReference",
            },
        )

        items = []
        for item in raw_items:
            item_info = {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "type": "folder" if "folder" in item else "file",
                "size": item.get("size", 0),
                "url": item.get("webUrl", ""),
                "last_modified": item.get("lastModifiedDateTime", ""),
                "created": item.get("createdDateTime", ""),
            }
            if "folder" in item:
                item_info["child_count"] = item["folder"].get("childCount", 0)
            if "file" in item:
                item_info["mime_type"] = item["file"].get("mimeType", "")
            # Include drive ID for use in get_file_content
            parent_ref = item.get("parentReference", {})
            if parent_ref.get("driveId"):
                item_info["drive_id"] = parent_ref["driveId"]
            items.append(item_info)

        result: Dict[str, Any] = {
            "items": items,
            "count": len(items),
            "site_id": site_id,
        }
        if truncated:
            result["truncated"] = True
        return result
    except Exception as e:
        return {**_format_error(e), "items": [], "count": 0}


@mcp.tool()
async def get_file_content(site_id: str, item_id: str, drive_id: str = "") -> dict:
    """Get the content of a file from SharePoint.

    Retrieves file content up to 5MB. Supports:
    - Text files (txt, csv, md, json, xml, html, py, js, etc.) — returned as-is.
    - Office documents (docx, xlsx) and PDFs — text is automatically extracted.
    - Other binary files (images, etc.) — returns metadata and a web URL for direct access.

    The item_id parameter accepts EITHER:
    - A Graph API item ID (recommended): e.g., "01QIGVBRV6Y2GOVW7725BZO354PWSELRRZ"
      Get this from the 'id' field in list_drive_items or search_files results.
    - A file path within the drive: e.g., "Reports/Q4.xlsx" or "Client Documents/report.docx"
      Paths containing '/' are automatically detected. Paths are relative to the drive root;
      "Shared Documents/" is stripped automatically if present since it's the drive name itself.

    Prefer using item IDs from list_drive_items or search_files over manual paths.

    Args:
        site_id: SharePoint site ID (from list_sites, list_drive_items, or search_files).
        item_id: File identifier — either a Graph API item ID (from list_drive_items/search_files
                 'id' field) or a file path (e.g., "Documents/report.csv").
        drive_id: Document library drive ID (from list_drive_items/search_files 'drive_id' field).
                  If empty, uses the site's default drive.

    Returns:
        Dictionary with file metadata. For text files and supported Office/PDF formats,
        includes 'content' with extracted text. For unsupported binary files, includes
        'url' for direct access.
    """
    client = _get_client()

    if not item_id or not item_id.strip():
        return {
            "error": "item_id is required — provide a file ID from list_drive_items/search_files, or a file path"
        }

    try:
        site_id = await _resolve_site_id(client, site_id)

        # Get file metadata — support both item IDs and file paths
        if _is_item_id(item_id):
            base = _build_drive_base(site_id, drive_id)
            meta_path = f"{base}/items/{item_id}"
        else:
            # Path-based lookup using Graph API path syntax
            file_path = item_id.strip("/")
            # When using the default drive, strip the drive name prefix if present.
            if not drive_id:
                for prefix in (
                    "Shared Documents/",
                    "Documents/",
                    "Shared%20Documents/",
                ):
                    if file_path.startswith(prefix):
                        file_path = file_path[len(prefix) :]
                        break
            base = _build_drive_base(site_id, drive_id)
            meta_path = f"{base}/root:/{file_path}:"
            logger.info("Using path-based file access for: %s", file_path)

        metadata = await client.graph_get(
            meta_path,
            params={
                "$select": "id,name,size,webUrl,lastModifiedDateTime,createdBy,file"
            },
        )

        file_name = metadata.get("name", "")
        file_size = metadata.get("size", 0)
        mime_type = metadata.get("file", {}).get("mimeType", "")
        web_url = metadata.get("webUrl", "")

        ext = ""
        if "." in file_name:
            ext = f".{file_name.rsplit('.', 1)[-1].lower()}"

        is_text = ext in TEXT_EXTENSIONS or mime_type.startswith("text/")

        result: Dict[str, Any] = {
            "name": file_name,
            "size": file_size,
            "mime_type": mime_type,
            "url": web_url,
            "last_modified": metadata.get("lastModifiedDateTime", ""),
            "created_by": metadata.get("createdBy", {})
            .get("user", {})
            .get("displayName", ""),
        }

        if is_text and file_size < _MAX_EXTRACT_SIZE:
            content_path = f"{meta_path}/content"
            content_bytes = await client.graph_get_content(content_path)
            try:
                result["content"] = content_bytes.decode("utf-8")
                result["content_type"] = "text"
            except UnicodeDecodeError:
                result["content_type"] = "binary"
                result["message"] = (
                    f"File '{file_name}' appears to be a text file but contains non-UTF-8 encoding. "
                    f"Use the web URL to access this file directly: {web_url}"
                )
        elif file_size < _MAX_EXTRACT_SIZE:
            # Try to extract text from binary formats (docx, pdf, xlsx, pptx)
            content_path = f"{meta_path}/content"
            content_bytes = await client.graph_get_content(content_path)
            extracted = _extract_text_from_binary(content_bytes, file_name, mime_type)
            if extracted:
                result["content"] = extracted["text"]
                result["content_type"] = "text"
                result["extraction_method"] = extracted["method"]
                if "page_count" in extracted:
                    result["page_count"] = extracted["page_count"]
                if "sheet_count" in extracted:
                    result["sheet_count"] = extracted["sheet_count"]
                if "slide_count" in extracted:
                    result["slide_count"] = extracted["slide_count"]
            else:
                result["content_type"] = "binary"
                result["message"] = (
                    f"Unsupported binary format ({mime_type or ext}). "
                    f"Use the web URL to access this file directly."
                )
        else:
            result["content_type"] = "binary"
            result["message"] = (
                f"File too large for text extraction ({file_size} bytes, limit {_MAX_EXTRACT_SIZE}). "
                f"Use the web URL to access this file directly."
            )

        return result
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_site_info(site_id: str = "") -> dict:
    """Get detailed information about a SharePoint site, including its document libraries and lists.

    Use this to discover available drives (document libraries) and their IDs,
    which can be passed to list_drive_items or get_file_content.

    Workflow:
    1. list_sites() — find the site
    2. get_site_info(site_id="...") — discover drives and lists
    3. list_drive_items(site_id="...", drive_id="<drive id>") — browse a specific library

    Args:
        site_id: SharePoint site ID or URL path (from list_sites results).
                 If empty, uses the pre-configured site.

    Returns:
        Dictionary with: id, name, url, description, created, last_modified,
        drives (list of document libraries with id/name), lists (SharePoint lists).
    """
    client = _get_client()

    if not site_id:
        site_id = _get_default_site_id()
        if not site_id:
            return {"error": "site_id is required (or set SHAREPOINT_SITE_URL env var)"}

    try:
        # Get site info
        site_data = await client.graph_get(f"/sites/{site_id}")
        resolved_site_id = site_data.get("id", site_id)

        # Get drives (document libraries)
        drives_data = await client.graph_get(
            f"/sites/{resolved_site_id}/drives",
            params={"$select": "id,name,description,webUrl,quota"},
        )
        drives = []
        for drive in drives_data.get("value", []):
            drives.append(
                {
                    "id": drive.get("id", ""),
                    "name": drive.get("name", ""),
                    "description": drive.get("description", ""),
                    "url": drive.get("webUrl", ""),
                    "total_size": drive.get("quota", {}).get("total", 0),
                    "used_size": drive.get("quota", {}).get("used", 0),
                }
            )

        # Get lists
        lists_data = await client.graph_get(
            f"/sites/{resolved_site_id}/lists",
            params={"$select": "id,displayName,description,webUrl,list"},
        )
        lists = []
        for lst in lists_data.get("value", []):
            lists.append(
                {
                    "id": lst.get("id", ""),
                    "name": lst.get("displayName", ""),
                    "description": lst.get("description", ""),
                    "url": lst.get("webUrl", ""),
                    "item_count": lst.get("list", {}).get("itemCount", 0),
                }
            )

        return {
            "id": resolved_site_id,
            "name": site_data.get("displayName", ""),
            "url": site_data.get("webUrl", ""),
            "description": site_data.get("description", ""),
            "created": site_data.get("createdDateTime", ""),
            "last_modified": site_data.get("lastModifiedDateTime", ""),
            "drives": drives,
            "drive_count": len(drives),
            "lists": lists,
            "list_count": len(lists),
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_list_items(
    site_id: str, list_id: str, filter: str = "", select: str = "", top: int = 50
) -> dict:
    """Get items from a SharePoint list with optional filtering.

    Use get_site_info first to discover available lists and their IDs.

    Args:
        site_id: SharePoint site ID (from list_sites).
        list_id: SharePoint list ID (from get_site_info 'lists' results).
        filter: OData $filter expression (e.g., "fields/Status eq 'Active'").
        select: Comma-separated field names to return (e.g., "fields/Title,fields/Status").
        top: Maximum items per page (default 50, max 200).

    Returns:
        Dictionary with 'items' list. Each item has: id, fields (dict of field values),
        created, last_modified.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)

        params: Dict[str, str] = {
            "$expand": "fields",
            "$top": str(min(top, 200)),
        }
        if filter:
            params["$filter"] = filter
        if select:
            params["$select"] = select

        raw_items, truncated = await client.graph_get_all_pages(
            f"/sites/{site_id}/lists/{list_id}/items",
            params=params,
        )

        items = []
        for item in raw_items:
            items.append(
                {
                    "id": item.get("id", ""),
                    "fields": item.get("fields", {}),
                    "created": item.get("createdDateTime", ""),
                    "last_modified": item.get("lastModifiedDateTime", ""),
                }
            )

        result: Dict[str, Any] = {
            "items": items,
            "count": len(items),
            "site_id": site_id,
            "list_id": list_id,
        }
        if truncated:
            result["truncated"] = True
        return result
    except Exception as e:
        return {**_format_error(e), "items": [], "count": 0}


# ---------------------------------------------------------------------------
# Write Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def upload_file(
    site_id: str,
    file_name: str,
    content: str,
    folder_path: str = "/",
    drive_id: str = "",
    content_encoding: str = "text",
) -> dict:
    """Upload a file to a SharePoint document library.

    For text content, pass the content directly as a string.
    For binary content, pass base64-encoded content and set content_encoding="base64".

    Small files (<4MB) use a simple PUT. Large files use a chunked upload session.

    Args:
        site_id: SharePoint site ID (from list_sites).
        file_name: Name for the file (e.g., "report.docx", "data.csv").
        content: File content as a string (text) or base64-encoded string (binary).
        folder_path: Folder path to upload into (e.g., "/Reports"). Defaults to root.
        drive_id: Document library drive ID. If empty, uses default drive.
        content_encoding: "text" for plain text content, "base64" for base64-encoded binary.

    Returns:
        Dictionary with the created file metadata: id, name, size, url, drive_id.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)
        base = _build_drive_base(site_id, drive_id)

        # Encode content to bytes
        if content_encoding == "base64":
            try:
                content_bytes = base64.b64decode(content)
            except Exception as e:
                return {
                    "error": f"Invalid base64 content: {e}",
                    "error_code": "InvalidInput",
                }
        else:
            content_bytes = content.encode("utf-8")

        # Build the upload path
        folder = folder_path.strip("/")
        if folder:
            upload_path = f"{base}/root:/{folder}/{file_name}:/content"
        else:
            upload_path = f"{base}/root:/{file_name}:/content"

        if len(content_bytes) < _SIMPLE_UPLOAD_LIMIT:
            # Simple upload for small files
            result = await client.graph_put(upload_path, content_bytes)
        else:
            # Chunked upload for large files
            if folder:
                session_path = f"{base}/root:/{folder}/{file_name}:/createUploadSession"
            else:
                session_path = f"{base}/root:/{file_name}:/createUploadSession"

            session = await client.graph_post(
                session_path,
                {
                    "item": {"@microsoft.graph.conflictBehavior": "rename"},
                },
            )
            upload_url = session["uploadUrl"]

            result = {}
            total_size = len(content_bytes)
            for start in range(0, total_size, _UPLOAD_CHUNK_SIZE):
                end = min(start + _UPLOAD_CHUNK_SIZE, total_size)
                chunk = content_bytes[start:end]
                content_range = f"bytes {start}-{end - 1}/{total_size}"
                result = await client.graph_put_chunk(upload_url, chunk, content_range)

        parent_ref = result.get("parentReference", {})
        return {
            "id": result.get("id", ""),
            "name": result.get("name", ""),
            "size": result.get("size", 0),
            "url": result.get("webUrl", ""),
            "drive_id": parent_ref.get("driveId", ""),
            "site_id": site_id,
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_folder(
    site_id: str,
    folder_name: str,
    parent_path: str = "/",
    drive_id: str = "",
) -> dict:
    """Create a new folder in a SharePoint document library.

    Args:
        site_id: SharePoint site ID (from list_sites).
        folder_name: Name for the new folder.
        parent_path: Parent folder path (e.g., "/Reports"). Defaults to root.
        drive_id: Document library drive ID. If empty, uses default drive.

    Returns:
        Dictionary with the created folder metadata: id, name, url, drive_id.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)
        base = _build_drive_base(site_id, drive_id)

        parent = parent_path.strip("/")
        if parent:
            endpoint = f"{base}/root:/{parent}:/children"
        else:
            endpoint = f"{base}/root/children"

        result = await client.graph_post(
            endpoint,
            {
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "fail",
            },
        )

        parent_ref = result.get("parentReference", {})
        return {
            "id": result.get("id", ""),
            "name": result.get("name", ""),
            "url": result.get("webUrl", ""),
            "drive_id": parent_ref.get("driveId", ""),
            "site_id": site_id,
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_list_item(site_id: str, list_id: str, fields: str) -> dict:
    """Create a new item in a SharePoint list.

    Use get_site_info to discover available lists, then get_list_items to
    see existing items and understand the field schema.

    Args:
        site_id: SharePoint site ID (from list_sites).
        list_id: SharePoint list ID (from get_site_info 'lists' results).
        fields: JSON string of field name -> value pairs.
                Example: '{"Title": "New Item", "Status": "Active", "Priority": "High"}'

    Returns:
        Dictionary with the created item: id, fields, url.
    """
    client = _get_client()

    try:
        # Parse fields JSON
        try:
            fields_dict = json.loads(fields)
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON in fields parameter: {e}",
                "error_code": "InvalidInput",
            }

        if not isinstance(fields_dict, dict):
            return {
                "error": "fields must be a JSON object (dict), not a list or scalar",
                "error_code": "InvalidInput",
            }

        site_id = await _resolve_site_id(client, site_id)

        result = await client.graph_post(
            f"/sites/{site_id}/lists/{list_id}/items",
            {"fields": fields_dict},
        )

        return {
            "id": result.get("id", ""),
            "fields": result.get("fields", {}),
            "url": result.get("webUrl", ""),
            "site_id": site_id,
            "list_id": list_id,
        }
    except Exception as e:
        return _format_error(e)


# ---------------------------------------------------------------------------
# File / Folder Management Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def rename_file_or_folder(
    site_id: str, drive_id: str, item_id: str, new_name: str
) -> dict:
    """Rename a file or folder in a SharePoint document library.

    Args:
        site_id: SharePoint site ID (from list_sites).
        drive_id: Document library drive ID (from list_drive_items 'drive_id' field).
        item_id: Item ID of the file or folder to rename (from list_drive_items 'id' field).
        new_name: New name for the file or folder (e.g., "updated-report.docx").

    Returns:
        Dictionary with updated item metadata: id, name, url, drive_id.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)
        base = _build_drive_base(site_id, drive_id)

        result = await client.graph_patch(
            f"{base}/items/{item_id}",
            {"name": new_name},
        )

        parent_ref = result.get("parentReference", {})
        return {
            "id": result.get("id", ""),
            "name": result.get("name", ""),
            "url": result.get("webUrl", ""),
            "drive_id": parent_ref.get("driveId", ""),
            "site_id": site_id,
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_file_or_folder(site_id: str, drive_id: str, item_id: str) -> dict:
    """Delete a file or folder from a SharePoint document library.

    WARNING: This moves the item to the recycle bin.
    Folders and all their contents will be deleted recursively.

    Args:
        site_id: SharePoint site ID (from list_sites).
        drive_id: Document library drive ID (from list_drive_items 'drive_id' field).
        item_id: Item ID of the file or folder to delete (from list_drive_items 'id' field).

    Returns:
        Dictionary with success confirmation.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)
        base = _build_drive_base(site_id, drive_id)

        await client.graph_delete(f"{base}/items/{item_id}")

        return {
            "success": True,
            "message": "Item deleted successfully",
            "item_id": item_id,
            "site_id": site_id,
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def move_file(
    site_id: str, drive_id: str, item_id: str, new_parent_folder_id: str
) -> dict:
    """Move a file or folder to a different folder within the same document library.

    Only supports moving within the same drive. To move between drives,
    download and re-upload the file.

    Args:
        site_id: SharePoint site ID (from list_sites).
        drive_id: Document library drive ID.
        item_id: Item ID of the file or folder to move (from list_drive_items 'id' field).
        new_parent_folder_id: Item ID of the destination folder (from list_drive_items 'id' field).

    Returns:
        Dictionary with updated item metadata: id, name, url, drive_id.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)
        base = _build_drive_base(site_id, drive_id)

        result = await client.graph_patch(
            f"{base}/items/{item_id}",
            {"parentReference": {"id": new_parent_folder_id}},
        )

        parent_ref = result.get("parentReference", {})
        return {
            "id": result.get("id", ""),
            "name": result.get("name", ""),
            "url": result.get("webUrl", ""),
            "drive_id": parent_ref.get("driveId", ""),
            "site_id": site_id,
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def share_file_or_folder(
    site_id: str,
    drive_id: str,
    item_id: str,
    recipient_emails: str,
    roles: str = "read",
    message: str = "",
) -> dict:
    """Share a file or folder with specific users via email invitation.

    Sends a sharing invitation granting the specified permission level.
    Recipients receive an email notification with a link.

    Args:
        site_id: SharePoint site ID (from list_sites).
        drive_id: Document library drive ID.
        item_id: Item ID of the file or folder to share (from list_drive_items 'id' field).
        recipient_emails: Comma-separated email addresses (e.g., "user@example.com,other@example.com").
        roles: Permission level — "read" for view-only or "write" for edit access. Defaults to "read".
        message: Optional personal message for the invitation email.

    Returns:
        Dictionary with sharing permission details.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)
        base = _build_drive_base(site_id, drive_id)

        emails = [e.strip() for e in recipient_emails.split(",") if e.strip()]
        if not emails:
            return {
                "error": "At least one recipient email is required",
                "error_code": "InvalidInput",
            }

        role = roles.strip().lower()
        if role not in {"read", "write"}:
            return {
                "error": f"Invalid role '{roles}'. Must be 'read' or 'write'.",
                "error_code": "InvalidInput",
            }

        invite_body: Dict[str, Any] = {
            "recipients": [{"email": email} for email in emails],
            "roles": [role],
            "requireSignIn": True,
            "sendInvitation": True,
        }
        if message:
            invite_body["message"] = message

        result = await client.graph_post(
            f"{base}/items/{item_id}/invite",
            invite_body,
        )

        permissions = []
        for perm in result.get("value", []):
            perm_info: Dict[str, Any] = {
                "id": perm.get("id", ""),
                "roles": perm.get("roles", []),
                "granted_to": perm.get("grantedTo", {})
                .get("user", {})
                .get("email", ""),
            }
            link = perm.get("link")
            if link:
                perm_info["share_link"] = link.get("webUrl", "")
            permissions.append(perm_info)

        return {
            "permissions": permissions,
            "count": len(permissions),
            "site_id": site_id,
        }
    except Exception as e:
        return _format_error(e)


# ---------------------------------------------------------------------------
# List Management Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def update_list_item(
    site_id: str, list_id: str, item_id: str, fields: str
) -> dict:
    """Update an existing item in a SharePoint list.

    Use get_list_items to find the item ID, then pass updated field values.
    Only specified fields are updated; omitted fields keep their values.

    Args:
        site_id: SharePoint site ID (from list_sites).
        list_id: SharePoint list ID (from get_site_info 'lists' results).
        item_id: Item ID to update (from get_list_items 'id' field).
        fields: JSON string of field name -> new value pairs.
                Example: '{"Status": "Completed", "Priority": "Low"}'

    Returns:
        Dictionary with updated item: id, fields, site_id, list_id.
    """
    client = _get_client()

    try:
        try:
            fields_dict = json.loads(fields)
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON in fields parameter: {e}",
                "error_code": "InvalidInput",
            }

        if not isinstance(fields_dict, dict):
            return {
                "error": "fields must be a JSON object (dict), not a list or scalar",
                "error_code": "InvalidInput",
            }

        site_id = await _resolve_site_id(client, site_id)

        result = await client.graph_patch(
            f"/sites/{site_id}/lists/{list_id}/items/{item_id}/fields",
            fields_dict,
        )

        return {
            "id": item_id,
            "fields": result,
            "site_id": site_id,
            "list_id": list_id,
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_list_item(site_id: str, list_id: str, item_id: str) -> dict:
    """Delete an item from a SharePoint list.

    WARNING: This permanently deletes the list item.

    Args:
        site_id: SharePoint site ID (from list_sites).
        list_id: SharePoint list ID (from get_site_info 'lists' results).
        item_id: Item ID to delete (from get_list_items 'id' field).

    Returns:
        Dictionary with success confirmation.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)

        await client.graph_delete(f"/sites/{site_id}/lists/{list_id}/items/{item_id}")

        return {
            "success": True,
            "message": "List item deleted successfully",
            "item_id": item_id,
            "list_id": list_id,
            "site_id": site_id,
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_list(site_id: str, display_name: str, columns: str = "") -> dict:
    """Create a new SharePoint list on a site.

    Creates a generic list. Optionally define columns at creation time.

    Args:
        site_id: SharePoint site ID (from list_sites).
        display_name: Display name for the new list (e.g., "Project Tasks").
        columns: Optional JSON string defining list columns.
                 Each column needs a 'name' and a type property object.
                 Supported types: 'text', 'number', 'boolean', 'dateTime', 'choice'.
                 Example: '[{"name": "Status", "choice": {"choices": ["Active", "Done"]}},
                           {"name": "DueDate", "dateTime": {}},
                           {"name": "Priority", "number": {}}]'
                 If empty, creates a list with only the default Title column.

    Returns:
        Dictionary with created list metadata: id, name, url, site_id.
    """
    client = _get_client()

    try:
        site_id = await _resolve_site_id(client, site_id)

        list_body: Dict[str, Any] = {
            "displayName": display_name,
            "list": {"template": "genericList"},
        }

        if columns and columns.strip():
            try:
                columns_list = json.loads(columns)
            except json.JSONDecodeError as e:
                return {
                    "error": f"Invalid JSON in columns parameter: {e}",
                    "error_code": "InvalidInput",
                }

            if not isinstance(columns_list, list):
                return {
                    "error": "columns must be a JSON array of column definitions",
                    "error_code": "InvalidInput",
                }

            list_body["columns"] = columns_list

        result = await client.graph_post(
            f"/sites/{site_id}/lists",
            list_body,
        )

        return {
            "id": result.get("id", ""),
            "name": result.get("displayName", ""),
            "url": result.get("webUrl", ""),
            "site_id": site_id,
        }
    except Exception as e:
        return _format_error(e)
