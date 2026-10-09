"""Wiki page API endpoints."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile

from .dependencies import require_wiki_access, require_wiki_admin_access
from .handlers import image, page_crud, revision, search
from .models import (
    WikiPageCreate,
    WikiPageListItem,
    WikiPageResponse,
    WikiPageUpdate,
    WikiRevisionResponse,
    WikiTreeNode,
)

wiki_router = APIRouter(
    prefix="/api/wiki",
    tags=["wiki"],
    dependencies=[Depends(require_wiki_access)],
)


# ============================================================================
# Page CRUD
# ============================================================================


@wiki_router.get("/pages", response_model=List[WikiPageListItem])
async def list_pages(
    include_unpublished: bool = Query(False),
    parent_id: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
):
    """List all wiki pages."""
    return await page_crud.handle_list_pages(include_unpublished, parent_id, tag)


@wiki_router.get("/pages/{slug}", response_model=WikiPageResponse)
async def get_page(slug: str):
    """Get a wiki page by slug."""
    return await page_crud.handle_get_page(slug)


@wiki_router.post("/pages", response_model=WikiPageResponse)
async def create_page(
    page_data: WikiPageCreate,
    current_user: Dict[str, Any] = Depends(require_wiki_admin_access),
):
    """Create a new wiki page."""
    return await page_crud.handle_create_page(page_data, current_user)


@wiki_router.put("/pages/{slug}", response_model=WikiPageResponse)
async def update_page(
    slug: str,
    page_data: WikiPageUpdate,
    current_user: Dict[str, Any] = Depends(require_wiki_admin_access),
):
    """Update a wiki page."""
    return await page_crud.handle_update_page(slug, page_data, current_user)


@wiki_router.delete("/pages/{slug}", dependencies=[Depends(require_wiki_admin_access)])
async def delete_page(slug: str):
    """Delete a wiki page."""
    return await page_crud.handle_delete_page(slug)


# ============================================================================
# Revisions
# ============================================================================


@wiki_router.get("/pages/{slug}/revisions", response_model=List[WikiRevisionResponse])
async def get_page_revisions(slug: str):
    """Get revision history for a wiki page."""
    return await revision.handle_get_page_revisions(slug)


@wiki_router.get(
    "/pages/{slug}/revisions/{version}", response_model=WikiRevisionResponse
)
async def get_page_revision(slug: str, version: int):
    """Get a specific revision of a wiki page."""
    return await revision.handle_get_page_revision(slug, version)


@wiki_router.post("/pages/{slug}/restore/{version}", response_model=WikiPageResponse)
async def restore_page_revision(
    slug: str,
    version: int,
    current_user: Dict[str, Any] = Depends(require_wiki_admin_access),
):
    """Restore a wiki page to a previous revision."""
    return await revision.handle_restore_page_revision(slug, version, current_user)


# ============================================================================
# Search & Tree
# ============================================================================


@wiki_router.get("/tree", response_model=List[WikiTreeNode])
async def get_page_tree(include_unpublished: bool = Query(False)):
    """Get hierarchical tree structure of all wiki pages."""
    return await search.handle_get_page_tree(include_unpublished)


@wiki_router.get("/search", response_model=List[WikiPageListItem])
async def search_pages(
    q: str = Query(..., min_length=1),
    include_unpublished: bool = Query(False),
    limit: int = Query(50, le=100),
):
    """Search wiki pages using full-text search."""
    return await search.handle_search_pages(q, include_unpublished, limit)


# ============================================================================
# Images
# ============================================================================


@wiki_router.get("/image-proxy")
async def proxy_image(url: str = Query(...)):
    """Proxy an external image through the backend to avoid CORS/hotlink restrictions."""
    return await image.handle_proxy_image(url)


@wiki_router.post("/images")
async def upload_wiki_image(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(require_wiki_admin_access),
):
    """Upload an image for use in wiki pages."""
    return await image.handle_upload_wiki_image(file, current_user)


@wiki_router.get("/images/{image_id}")
async def get_wiki_image(image_id: str):
    """Serve a stored wiki image."""
    return await image.handle_get_wiki_image(image_id)
