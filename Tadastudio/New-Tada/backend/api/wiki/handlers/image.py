"""Wiki image handlers."""

import mimetypes
import uuid
from typing import Any, Dict
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import text

from backend.services.config import get_logger
from backend.services.database import get_db

from ..dependencies import get_wiki_user_id
from ..exceptions import (
    WikiImageNotFoundError,
    WikiImageProxyDomainError,
    WikiImageProxySchemeError,
    WikiImageTooLargeError,
    WikiInvalidImageError,
)

logger = get_logger(__name__)

_PROXY_ALLOWED_DOMAINS = ("github.com", "githubusercontent.com")
_MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB


async def handle_proxy_image(url: str) -> Response:
    """Proxy an external image through the backend to avoid CORS/hotlink restrictions."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise WikiImageProxySchemeError()
    host = parsed.netloc.lower().removeprefix("www.")
    if not any(host == d or host.endswith(f".{d}") for d in _PROXY_ALLOWED_DOMAINS):
        raise WikiImageProxyDomainError()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            resp = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                    "Referer": "https://github.com/",
                },
            )
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "application/octet-stream")
            return Response(
                content=resp.content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code, detail="Image fetch failed"
        )
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Failed to fetch image")


async def handle_upload_wiki_image(
    file: UploadFile, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Upload an image for use in wiki pages."""
    content = await file.read()
    if len(content) > _MAX_IMAGE_BYTES:
        raise WikiImageTooLargeError()
    mime_type = (
        file.content_type
        or mimetypes.guess_type(file.filename or "")[0]
        or "application/octet-stream"
    )
    if not mime_type.startswith("image/"):
        raise WikiInvalidImageError()
    user_id = get_wiki_user_id(current_user)
    image_id = str(uuid.uuid4())
    with get_db() as db:
        db.execute(
            text(
                """
                INSERT INTO wiki_images (id, filename, mime_type, file_size, content, created_by)
                VALUES (:id, :filename, :mime_type, :file_size, :content, :created_by)
            """
            ),
            {
                "id": image_id,
                "filename": file.filename or "image",
                "mime_type": mime_type,
                "file_size": len(content),
                "content": content,
                "created_by": user_id,
            },
        )
    return {"id": image_id, "url": f"/api/wiki/images/{image_id}"}


async def handle_get_wiki_image(image_id: str) -> Response:
    """Serve a stored wiki image."""
    with get_db() as db:
        row = db.execute(
            text("SELECT content, mime_type FROM wiki_images WHERE id = :id"),
            {"id": image_id},
        ).fetchone()
    if not row:
        raise WikiImageNotFoundError()
    return Response(
        content=bytes(row[0]),
        media_type=row[1],
        headers={"Cache-Control": "public, max-age=31536000"},
    )
