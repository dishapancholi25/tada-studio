"""OneDrive MCP Server using FastMCP.

Exposes OneDrive operations as MCP tools via Microsoft Graph API.
Runs as a stdio subprocess spawned by the MCP client manager.

OAuth Scope Requirements:
- Read tools (list_my_drives, list_drive_items, get_file_content,
  find_file_or_folder, get_shared_with_me, get_item_metadata,
  get_item_metadata_by_url): Files.Read.All, User.Read
- Write tools (upload_file, create_folder, rename_file_or_folder,
  delete_file_or_folder, move_file): Files.ReadWrite.All
- share_file_or_folder: Files.ReadWrite.All, Sites.ReadWrite.All
- set_sensitivity_label: Files.ReadWrite.All, InformationProtectionPolicy.Read
"""

import atexit
import base64
import logging
import os
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from backend.tools.shared.microsoft_graph_client import (
    GraphAPIError,
    MicrosoftGraphClient,
)
from backend.tools.shared.search_helpers import (
    build_kql_query,
    extract_aggregations,
    parse_search_hits,
)
from backend.tools.shared.text_extraction import (
    MAX_EXTRACT_SIZE,
    TEXT_EXTENSIONS,
    extract_text_from_binary,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("OneDrive MCP Server")

_client: Optional[MicrosoftGraphClient] = None

# Chunk size for large file uploads (3.125 MiB, must be multiple of 320 KiB)
_UPLOAD_CHUNK_SIZE = 3_276_800
# Simple upload threshold (4MB)
_SIMPLE_UPLOAD_LIMIT = 4 * 1024 * 1024


def _get_client() -> MicrosoftGraphClient:
    """Lazy-initialize the Graph API client from environment variables.

    Checks for a delegated token first (ONEDRIVE_ACCESS_TOKEN),
    falling back to client_credentials (TENANT/CLIENT/SECRET).
    """
    global _client
    if _client is None:
        # Delegated mode: pre-obtained OAuth token injected by mcp_client_manager
        delegated_token = os.environ.get("ONEDRIVE_ACCESS_TOKEN", "").strip()
        if delegated_token:
            logger.info("Using delegated (OAuth) token for OneDrive Graph API")
            _client = MicrosoftGraphClient(access_token=delegated_token)
        else:
            # Fallback: client_credentials flow
            tenant_id = os.environ.get("ONEDRIVE_TENANT_ID", "")
            client_id = os.environ.get("ONEDRIVE_CLIENT_ID", "")
            client_secret = os.environ.get("ONEDRIVE_CLIENT_SECRET", "")

            if not all([tenant_id, client_id, client_secret]):
                raise ValueError(
                    "Missing authentication: set ONEDRIVE_ACCESS_TOKEN (delegated) "
                    "or ONEDRIVE_TENANT_ID + ONEDRIVE_CLIENT_ID + ONEDRIVE_CLIENT_SECRET"
                )

            _client = MicrosoftGraphClient(
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


def _get_default_drive_id() -> Optional[str]:
    """Get a default drive ID from env var (set by the config UI drive picker)."""
    return os.environ.get("ONEDRIVE_DRIVE_ID", "").strip() or None


def _get_scoped_folder_paths() -> list:
    """Get folder paths to scope searches to, from env var.

    ONEDRIVE_FOLDER_PATHS is a comma-separated list of folder web URLs
    set by the config UI folder tree picker.
    """
    raw = os.environ.get("ONEDRIVE_FOLDER_PATHS", "").strip()
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def _build_drive_base(drive_id: str = "") -> str:
    """Build the Graph API drive base path for OneDrive."""
    if drive_id:
        return f"/drives/{drive_id}"
    return "/me/drive"


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


def _encode_sharing_url(url: str) -> str:
    """Encode a sharing URL for use with the Graph API /shares/ endpoint.

    See: https://learn.microsoft.com/en-us/graph/api/shares-get
    """
    encoded = base64.b64encode(url.encode()).decode().rstrip("=")
    return "u!" + encoded.replace("/", "_").replace("+", "-")


def _format_item_metadata(item: Dict[str, Any], drive_id: str = "") -> Dict[str, Any]:
    """Format a raw Graph API driveItem into a standardized metadata dict."""
    parent_ref = item.get("parentReference", {})
    resolved_drive_id = parent_ref.get("driveId", drive_id)

    info: Dict[str, Any] = {
        "id": item.get("id", ""),
        "name": item.get("name", ""),
        "type": "folder" if "folder" in item else "file",
        "size": item.get("size", 0),
        "url": item.get("webUrl", ""),
        "last_modified": item.get("lastModifiedDateTime", ""),
        "created": item.get("createdDateTime", ""),
        "etag": item.get("eTag", ""),
        "drive_id": resolved_drive_id,
    }
    if "folder" in item:
        info["child_count"] = item["folder"].get("childCount", 0)
    if "file" in item:
        info["mime_type"] = item["file"].get("mimeType", "")
    return info


# ---------------------------------------------------------------------------
# Read Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def list_my_drives() -> dict:
    """List the current user's OneDrive drives.

    Returns the user's default drive and any additional drives they have access to.
    Use the drive 'id' from results with other tools like list_drive_items.

    Workflow: list_my_drives() -> list_drive_items(drive_id="...") -> get_file_content(...)

    Returns:
        Dictionary with 'drives' list. Each drive has: id, name, drive_type,
        web_url, total_size, used_size. Use the 'id' field with other tools.
    """
    client = _get_client()

    try:
        # Get the user's default drive
        default_drive = await client.graph_get(
            "/me/drive",
            params={"$select": "id,name,driveType,quota,webUrl,owner"},
        )

        drives = [
            {
                "id": default_drive.get("id", ""),
                "name": default_drive.get("name", ""),
                "drive_type": default_drive.get("driveType", ""),
                "web_url": default_drive.get("webUrl", ""),
                "total_size": default_drive.get("quota", {}).get("total", 0),
                "used_size": default_drive.get("quota", {}).get("used", 0),
                "is_default": True,
            }
        ]

        # Get additional drives (if any)
        try:
            additional, _ = await client.graph_get_all_pages(
                "/me/drives",
                params={"$select": "id,name,driveType,quota,webUrl,owner"},
            )
            default_id = default_drive.get("id", "")
            for drive in additional:
                if drive.get("id") != default_id:
                    drives.append(
                        {
                            "id": drive.get("id", ""),
                            "name": drive.get("name", ""),
                            "drive_type": drive.get("driveType", ""),
                            "web_url": drive.get("webUrl", ""),
                            "total_size": drive.get("quota", {}).get("total", 0),
                            "used_size": drive.get("quota", {}).get("used", 0),
                            "is_default": False,
                        }
                    )
        except GraphAPIError:
            # /me/drives may not be available for all accounts; default drive is enough
            pass

        return {"drives": drives, "count": len(drives)}
    except Exception as e:
        return {**_format_error(e), "drives": [], "count": 0}


@mcp.tool()
async def list_drive_items(
    drive_id: str = "",
    parent_folder_id: str = "",
    folder_path: str = "/",
) -> dict:
    """List files and folders in a OneDrive drive.

    Browse drive contents to find files. Each result includes 'id', 'drive_id',
    and 'etag' which can be passed to other tools.

    Prefer using parent_folder_id (from a previous listing) over folder_path for
    more reliable navigation. folder_path is a fallback for root-relative paths.

    Workflow:
    1. list_drive_items() — list root of default OneDrive
    2. list_drive_items(parent_folder_id="<folder_id>") — browse a subfolder by ID
    3. get_file_content(item_id="<id>", drive_id="<drive_id>") — get a file

    Args:
        drive_id: Drive ID (from list_my_drives). If empty, uses the user's default OneDrive.
        parent_folder_id: ID of the folder to list (from a prior listing). Takes priority
                          over folder_path when provided.
        folder_path: Folder path to list (e.g., "/Documents", "/Projects/Reports").
                     Used only when parent_folder_id is empty. Defaults to root.

    Returns:
        Dictionary with 'items' list. Each item has: id, name, type ('file'/'folder'),
        size, url, last_modified, created, drive_id, etag. Files also have mime_type.
        Folders also have child_count.
    """
    client = _get_client()

    if not drive_id:
        drive_id = _get_default_drive_id() or ""

    try:
        base = _build_drive_base(drive_id)

        if parent_folder_id:
            endpoint = f"{base}/items/{parent_folder_id}/children"
        elif folder_path and folder_path != "/":
            path = folder_path.strip("/")
            endpoint = f"{base}/root:/{path}:/children"
        else:
            endpoint = f"{base}/root/children"

        raw_items, truncated = await client.graph_get_all_pages(
            endpoint,
            params={
                "$top": "50",
                "$select": "id,name,size,webUrl,lastModifiedDateTime,createdDateTime,folder,file,parentReference,eTag",
            },
        )

        items = [_format_item_metadata(item, drive_id) for item in raw_items]
        result: Dict[str, Any] = {"items": items, "count": len(items)}
        if truncated:
            result["truncated"] = True
        return result
    except Exception as e:
        return {**_format_error(e), "items": [], "count": 0}


@mcp.tool()
async def get_file_content(item_id: str, drive_id: str = "") -> dict:
    """Get the content of a file from OneDrive.

    Retrieves file content up to 5MB. Supports:
    - Text files (txt, csv, md, json, xml, html, py, js, etc.) — returned as-is.
    - Office documents (docx, xlsx) and PDFs — text is automatically extracted.
    - Other binary files (images, etc.) — returns metadata and a web URL for direct access.

    The item_id parameter accepts EITHER:
    - A Graph API item ID (recommended): e.g., "01QIGVBRV6Y2GOVW7725BZO354PWSELRRZ"
      Get this from the 'id' field in list_drive_items or find_file_or_folder results.
    - A file path within the drive: e.g., "Documents/report.csv" or "Projects/data.xlsx"
      Paths containing '/' are automatically detected.

    Prefer using item IDs from list_drive_items or find_file_or_folder over manual paths.

    Args:
        item_id: File identifier — either a Graph API item ID (from list_drive_items/
                 find_file_or_folder 'id' field) or a file path (e.g., "Documents/report.csv").
        drive_id: Drive ID (from list_my_drives or list_drive_items 'drive_id' field).
                  If empty, uses the user's default OneDrive.

    Returns:
        Dictionary with file metadata. For text files and supported Office/PDF formats,
        includes 'content' with extracted text. For unsupported binary files, includes
        'url' for direct access.
    """
    client = _get_client()

    if not item_id or not item_id.strip():
        return {
            "error": "item_id is required — provide a file ID from list_drive_items/find_file_or_folder, or a file path"
        }

    try:
        base = _build_drive_base(drive_id)

        # Get file metadata — support both item IDs and file paths
        if _is_item_id(item_id):
            meta_path = f"{base}/items/{item_id}"
        else:
            file_path = item_id.strip("/")
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

        if is_text and file_size < MAX_EXTRACT_SIZE:
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
        elif file_size < MAX_EXTRACT_SIZE:
            # Try to extract text from binary formats (docx, pdf, xlsx, pptx)
            content_path = f"{meta_path}/content"
            content_bytes = await client.graph_get_content(content_path)
            extracted = extract_text_from_binary(content_bytes, file_name, mime_type)
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
                f"File too large for text extraction ({file_size} bytes, limit {MAX_EXTRACT_SIZE}). "
                f"Use the web URL to access this file directly."
            )

        return result
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def find_file_or_folder(search_query: str) -> dict:
    """Find a file or folder in the user's OneDrive by search query.

    Searches within the user's personal OneDrive by name or partial name.
    More efficient than searching all accessible files when you know the item
    is in the user's OneDrive.

    Returns file/folder metadata including 'id' and 'drive_id' which can be
    passed directly to get_file_content or get_item_metadata.

    Args:
        search_query: Search query — can be the entire or partial file/folder name
                      (e.g., "quarterly report", "budget.xlsx", "project plan").

    Returns:
        Dictionary with 'items' list. Each item has: id, name, type, url, size,
        last_modified, drive_id, etag. Files also have mime_type.
        Use 'id' and 'drive_id' with get_file_content to retrieve file content.
    """
    client = _get_client()

    try:
        safe_query = search_query.replace("'", "''")
        raw_items, truncated = await client.graph_get_all_pages(
            f"/me/drive/search(q='{safe_query}')",
            params={
                "$select": "id,name,size,webUrl,lastModifiedDateTime,folder,file,parentReference,eTag",
            },
        )

        items = [_format_item_metadata(item) for item in raw_items]
        result: Dict[str, Any] = {
            "items": items,
            "count": len(items),
            "query": search_query,
        }
        if truncated:
            result["truncated"] = True
        return result
    except Exception as e:
        return {**_format_error(e), "items": [], "count": 0}


@mcp.tool()
async def search_files(
    query: str,
    file_types: str = "",
    author: str = "",
    date_from: str = "",
    date_to: str = "",
    path: str = "",
    sort_by: str = "",
    page_size: int = 25,
    page: int = 0,
) -> dict:
    """Search for files across OneDrive by name or content keywords.

    Uses the Microsoft Graph Search API for full-text search with advanced
    filtering. Returns file metadata including 'id' and 'drive_id' which
    can be passed directly to get_file_content.

    For quick name lookups in your personal drive, use find_file_or_folder
    instead. Use this tool for broader, filtered searches.

    The query parameter supports full KQL (Keyword Query Language) syntax, or
    you can use the convenience filter parameters which build KQL for you.

    Args:
        query: Search query — matches file names and content. Supports KQL
               syntax (e.g., "quarterly report", "budget filetype:xlsx",
               "project plan author:\\"John\\"").
        file_types: Comma-separated file extensions to filter by
                    (e.g., "pptx,docx,pdf"). Appends filetype: KQL filters.
        author: Filter results to a specific author display name.
        date_from: ISO date (YYYY-MM-DD). Only return files modified on or after
                   this date.
        date_to: ISO date (YYYY-MM-DD). Only return files modified on or before
                 this date.
        path: Path to scope results (e.g., "/Documents/Projects").
        sort_by: Sort results — one of "lastModifiedDateTime", "name", "size",
                 or "lastModifiedDateTime desc" (append " desc" for descending).
                 Default is relevance ranking.
        page_size: Number of results per page (1-500, default 25).
        page: Zero-based page index for pagination (default 0 = first page).

    Returns:
        Dictionary with 'files' list, 'total' count of all matching results,
        'page' index, 'page_size', and 'more_results_available' flag.
        Each file has: id, name, url, size, last_modified, created_by,
        drive_id, and snippet (highlighted matching text).
        Use 'id' and 'drive_id' with get_file_content to retrieve the file.
    """
    client = _get_client()

    try:
        # Apply default folder path scoping if no explicit path filter
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

        data = await client.graph_post("/search/query", {"requests": [request_body]})

        files, total, more_available = parse_search_hits(data)
        facets = extract_aggregations(data)

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

        return result
    except Exception as e:
        return {**_format_error(e), "files": [], "count": 0, "total": 0}


@mcp.tool()
async def get_item_metadata(file_or_folder_id: str, drive_id: str = "") -> dict:
    """Get metadata of a file or folder from the user's OneDrive by ID.

    Returns full metadata including the 'etag' field required for rename,
    delete, and move operations.

    Args:
        file_or_folder_id: ID of the file or folder (from list_drive_items or
                           find_file_or_folder).
        drive_id: Drive ID (from list_my_drives). If empty, uses default OneDrive.

    Returns:
        Dictionary with: id, name, type, size, url, last_modified, created,
        etag, drive_id. Files also have mime_type. Folders also have child_count.
        The 'etag' is required for rename, delete, and move operations.
    """
    client = _get_client()

    try:
        base = _build_drive_base(drive_id)
        item = await client.graph_get(
            f"{base}/items/{file_or_folder_id}",
            params={
                "$select": "id,name,size,webUrl,lastModifiedDateTime,createdDateTime,folder,file,parentReference,eTag"
            },
        )
        return _format_item_metadata(item, drive_id)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_item_metadata_by_url(file_or_folder_url: str) -> dict:
    """Get metadata of a file or folder from the user's OneDrive by sharing URL.

    Only users with existing explicit permissions to access the file will be
    allowed to get the metadata. The URL will not be redeemed to grant access.

    Args:
        file_or_folder_url: URL of the file or folder (sharing link or web URL).
                            The user must already have explicit access.

    Returns:
        Dictionary with: id, name, type, size, url, last_modified, created,
        etag, drive_id. Files also have mime_type. Folders also have child_count.
    """
    client = _get_client()

    try:
        encoded = _encode_sharing_url(file_or_folder_url)
        item = await client.graph_get(
            f"/shares/{encoded}/driveItem",
            params={
                "$select": "id,name,size,webUrl,lastModifiedDateTime,createdDateTime,folder,file,parentReference,eTag"
            },
        )
        return _format_item_metadata(item)
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def get_shared_with_me() -> dict:
    """List files and folders that have been shared with the current user.

    Returns items shared via OneDrive sharing links or direct permissions.
    Each result includes 'id' and 'drive_id' for use with get_file_content.

    Returns:
        Dictionary with 'items' list. Each item has: id, name, size, url,
        shared_by, shared_on, drive_id, type ('file'/'folder').
    """
    client = _get_client()

    try:
        raw_items, truncated = await client.graph_get_all_pages(
            "/me/drive/sharedWithMe"
        )

        items = []
        for item in raw_items:
            shared_info = item.get("shared", {})
            shared_by = shared_info.get("sharedBy", {}).get("user", {})
            parent_ref = item.get("parentReference", {})

            item_info: Dict[str, Any] = {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "type": "folder" if "folder" in item else "file",
                "size": item.get("size", 0),
                "url": item.get("webUrl", ""),
                "shared_by": shared_by.get("displayName", ""),
                "shared_on": shared_info.get("sharedDateTime", ""),
            }
            if parent_ref.get("driveId"):
                item_info["drive_id"] = parent_ref["driveId"]
            if "file" in item:
                item_info["mime_type"] = item["file"].get("mimeType", "")
            items.append(item_info)

        result: Dict[str, Any] = {"items": items, "count": len(items)}
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
    file_name: str,
    content: str,
    folder_path: str = "/",
    drive_id: str = "",
    content_encoding: str = "text",
) -> dict:
    """Upload a file to OneDrive.

    For text content, pass the content directly as a string.
    For binary content, pass base64-encoded content and set content_encoding="base64".

    Small files (<4MB) use a simple PUT. Large files use a chunked upload session.

    Args:
        file_name: Name for the file (e.g., "report.docx", "data.csv").
        content: File content as a string (text) or base64-encoded string (binary).
        folder_path: Folder path to upload into (e.g., "/Documents"). Defaults to root.
        drive_id: Drive ID (from list_my_drives). If empty, uses default OneDrive.
        content_encoding: "text" for plain text content, "base64" for base64-encoded binary.

    Returns:
        Dictionary with the created file metadata: id, name, size, url, drive_id.
    """
    client = _get_client()

    try:
        base = _build_drive_base(drive_id)

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
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def create_folder(
    folder_name: str,
    parent_path: str = "/",
    drive_id: str = "",
) -> dict:
    """Create a new folder in OneDrive.

    If a folder with the same name already exists, a numeric suffix is added
    (e.g., "NewFolder (1)").

    Args:
        folder_name: Name for the new folder.
        parent_path: Parent folder path (e.g., "/Documents"). Defaults to root.
        drive_id: Drive ID (from list_my_drives). If empty, uses default OneDrive.

    Returns:
        Dictionary with the created folder metadata: id, name, url, drive_id.
    """
    client = _get_client()

    try:
        base = _build_drive_base(drive_id)

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
                "@microsoft.graph.conflictBehavior": "rename",
            },
        )

        parent_ref = result.get("parentReference", {})
        return {
            "id": result.get("id", ""),
            "name": result.get("name", ""),
            "url": result.get("webUrl", ""),
            "drive_id": parent_ref.get("driveId", ""),
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def rename_file_or_folder(
    file_or_folder_id: str,
    new_name: str,
    etag: str,
    drive_id: str = "",
) -> dict:
    """Rename a file or folder in the user's OneDrive.

    Requires the current eTag for concurrency control. Get the eTag from
    get_item_metadata or list_drive_items. The operation fails if the item
    has been modified since the eTag was fetched (412 Precondition Failed).

    Args:
        file_or_folder_id: ID of the file or folder to rename.
        new_name: The new name for the file or folder.
        etag: ETag value for concurrency control (from get_item_metadata or
              list_drive_items). Operation succeeds only if the current ETag matches.
        drive_id: Drive ID (from list_my_drives). If empty, uses default OneDrive.

    Returns:
        Dictionary with updated metadata: id, name, url, etag, drive_id.
    """
    client = _get_client()

    try:
        base = _build_drive_base(drive_id)
        result = await client.graph_patch(
            f"{base}/items/{file_or_folder_id}",
            {"name": new_name},
            extra_headers={"If-Match": etag},
        )
        parent_ref = result.get("parentReference", {})
        return {
            "id": result.get("id", ""),
            "name": result.get("name", ""),
            "url": result.get("webUrl", ""),
            "etag": result.get("eTag", ""),
            "drive_id": parent_ref.get("driveId", drive_id),
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def delete_file_or_folder(
    file_or_folder_id: str,
    etag: str,
    drive_id: str = "",
) -> dict:
    """Delete a file or folder from the user's OneDrive.

    Requires the current eTag for concurrency control. Get the eTag from
    get_item_metadata or list_drive_items.

    Args:
        file_or_folder_id: ID of the file or folder to delete.
        etag: ETag value for concurrency control (from get_item_metadata or
              list_drive_items). Operation succeeds only if the current ETag matches.
        drive_id: Drive ID (from list_my_drives). If empty, uses default OneDrive.

    Returns:
        Dictionary with: success (bool), id of deleted item.
    """
    client = _get_client()

    try:
        base = _build_drive_base(drive_id)
        await client.graph_delete(
            f"{base}/items/{file_or_folder_id}",
            extra_headers={"If-Match": etag},
        )
        return {"success": True, "id": file_or_folder_id}
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def move_file(
    file_id: str,
    new_parent_folder_id: str,
    etag: str,
    drive_id: str = "",
) -> dict:
    """Move a file in the user's OneDrive to another folder.

    Only supports files (not folders). The target folder must be in the user's OneDrive.
    Requires the current eTag for concurrency control.

    Args:
        file_id: ID of the file to move.
        new_parent_folder_id: ID of the target folder (must be in the user's OneDrive).
        etag: ETag value for concurrency control (from get_item_metadata or
              list_drive_items). Operation succeeds only if the current ETag matches.
        drive_id: Drive ID (from list_my_drives). If empty, uses default OneDrive.

    Returns:
        Dictionary with updated metadata: id, name, url, size, drive_id.
    """
    client = _get_client()

    try:
        base = _build_drive_base(drive_id)
        result = await client.graph_patch(
            f"{base}/items/{file_id}",
            {"parentReference": {"id": new_parent_folder_id}},
            extra_headers={"If-Match": etag},
        )
        parent_ref = result.get("parentReference", {})
        return {
            "id": result.get("id", ""),
            "name": result.get("name", ""),
            "url": result.get("webUrl", ""),
            "size": result.get("size", 0),
            "drive_id": parent_ref.get("driveId", drive_id),
        }
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def share_file_or_folder(
    file_or_folder_id: str,
    recipient_emails: List[str],
    roles: List[str],
    message: str = "Here's the file we're collaborating on.",
    send_invitation: bool = True,
    drive_id: str = "",
) -> dict:
    """Share a file or folder in the user's OneDrive with other users.

    Sends a sharing invitation granting read or write permissions.

    Args:
        file_or_folder_id: ID of the file or folder to share.
        recipient_emails: List of email addresses of recipients to invite.
        roles: List of roles to assign. Accepted values: 'read', 'write'
               (write grants both read and write permissions).
        message: Custom message to include in the invitation email.
        send_invitation: Whether to send a sharing invitation email (default: True).
        drive_id: Drive ID (from list_my_drives). If empty, uses default OneDrive.

    Returns:
        Dictionary with 'permissions' list. Each permission has: id, grantee_email,
        grantee_name, roles.
    """
    client = _get_client()

    try:
        base = _build_drive_base(drive_id)
        result = await client.graph_post(
            f"{base}/items/{file_or_folder_id}/invite",
            {
                "recipients": [{"email": email} for email in recipient_emails],
                "roles": roles,
                "message": message,
                "sendInvitation": send_invitation,
            },
        )

        permissions = []
        for perm in result.get("value", []):
            grantee = perm.get("grantedTo", {}) or perm.get("grantedToV2", {})
            user = grantee.get("user", {})
            permissions.append(
                {
                    "id": perm.get("id", ""),
                    "grantee_email": user.get("email", ""),
                    "grantee_name": user.get("displayName", ""),
                    "roles": perm.get("roles", []),
                }
            )

        return {"permissions": permissions, "count": len(permissions)}
    except Exception as e:
        return _format_error(e)


@mcp.tool()
async def set_sensitivity_label(
    file_id: str,
    sensitivity_label_id: str,
    justification_text: str,
    assignment_method: str = "privileged",
    drive_id: str = "",
) -> dict:
    """Set the sensitivity label of a file in the user's OneDrive.

    Requires appropriate Microsoft Purview licensing and configuration.
    Pass an empty string for sensitivity_label_id to remove an existing label.

    Args:
        file_id: The driveItemId of the file.
        sensitivity_label_id: ID of the sensitivity label to assign, or empty
                              string to remove the current label.
        assignment_method: Assignment method — 'standard', 'privileged', 'auto',
                          or 'unknownFutureValue' (default: 'privileged').
        justification_text: Justification text for audit purposes. Required when
                           downgrading or removing a label (default: 'Changed by MCPServer').
        drive_id: Drive ID (from list_my_drives). If empty, uses default OneDrive.

    Returns:
        Dictionary with: success (bool), file_id, label_id.
    """
    client = _get_client()

    try:
        base = _build_drive_base(drive_id)
        await client.graph_post(
            f"{base}/items/{file_id}/assignSensitivityLabel",
            {
                "sensitivityLabelId": sensitivity_label_id,
                "assignmentMethod": assignment_method,
                "justificationText": justification_text,
            },
        )
        return {"success": True, "file_id": file_id, "label_id": sensitivity_label_id}
    except Exception as e:
        return _format_error(e)
