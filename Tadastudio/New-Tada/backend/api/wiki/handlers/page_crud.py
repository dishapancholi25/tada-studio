"""Wiki page CRUD handlers."""

import re
from typing import Any, Dict, List, Optional

from sqlalchemy import func, text

from backend.models import WikiPage, WikiRevision
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.wiki import sanitize_wiki_content

from ..dependencies import get_wiki_user_id
from ..exceptions import (
    WikiCircularParentError,
    WikiPageAlreadyExistsError,
    WikiPageHasChildrenError,
    WikiPageNotFoundError,
    WikiParentNotFoundError,
    WikiSelfParentError,
)
from ..models import WikiPageCreate, WikiPageListItem, WikiPageResponse, WikiPageUpdate

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _generate_slug(title: str, db_session) -> str:
    """Generate a unique URL-friendly slug from title."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")

    original_slug = slug
    counter = 1
    while db_session.query(WikiPage).filter(WikiPage.slug == slug).first():
        slug = f"{original_slug}-{counter}"
        counter += 1

    return slug


def _get_current_version(db, page_id: str) -> int:
    """Get the current max revision version for a page."""
    return (
        db.query(func.max(WikiRevision.version))
        .filter(WikiRevision.page_id == page_id)
        .scalar()
        or 0
    )


def _create_revision(
    db_session,
    page: WikiPage,
    user_id: Optional[str],
    change_summary: Optional[str] = None,
) -> WikiRevision:
    """Create a new revision for a wiki page."""
    max_version = _get_current_version(db_session, page.id)

    revision = WikiRevision(
        page_id=page.id,
        title=page.title,
        content=page.content,
        version=max_version + 1,
        created_by=user_id,
        change_summary=change_summary,
    )
    db_session.add(revision)
    return revision


def _update_search_vector(db_session, page: WikiPage):
    """Update the full-text search vector for a page."""
    search_content = f"{page.title} {page.content}"
    db_session.execute(
        text(
            """
            UPDATE wiki_pages
            SET search_vector = to_tsvector('english', :content)
            WHERE id = :page_id
        """
        ),
        {"content": search_content, "page_id": page.id},
    )


def _check_circular_parent(db_session, page_id: str, parent_id: str) -> None:
    """Walk the parent chain from parent_id upward; raise if page_id is found."""
    current = parent_id
    seen: set[str] = set()
    while current:
        if current == page_id:
            raise WikiCircularParentError()
        if current in seen:
            break  # already-broken chain in DB, stop walking
        seen.add(current)
        ancestor = (
            db_session.query(WikiPage.parent_id).filter(WikiPage.id == current).first()
        )
        current = ancestor[0] if ancestor else None


def _build_page_response(page: WikiPage, version: int) -> WikiPageResponse:
    """Build a WikiPageResponse from an ORM instance and version number."""
    return WikiPageResponse(
        id=page.id,
        slug=page.slug,
        title=page.title,
        content=page.content,
        parent_id=page.parent_id,
        order_index=page.order_index,
        is_published=page.is_published,
        tags=page.tags,
        created_by=page.created_by,
        updated_by=page.updated_by,
        created_at=page.created_at,
        updated_at=page.updated_at,
        version=version,
    )


# ---------------------------------------------------------------------------
# Handler functions
# ---------------------------------------------------------------------------


async def handle_list_pages(
    include_unpublished: bool, parent_id: Optional[str], tag: Optional[str]
) -> List[WikiPageListItem]:
    """List all wiki pages with optional filters."""
    with get_db() as db:
        query = db.query(WikiPage)

        if not include_unpublished:
            query = query.filter(WikiPage.is_published == True)  # noqa: E712

        if parent_id == "null":
            query = query.filter(WikiPage.parent_id.is_(None))
        elif parent_id:
            query = query.filter(WikiPage.parent_id == parent_id)

        if tag:
            query = query.filter(WikiPage.tags.contains([tag]))

        pages = query.order_by(WikiPage.order_index, WikiPage.title).all()

        return [WikiPageListItem.model_validate(page) for page in pages]


async def handle_get_page(slug: str) -> WikiPageResponse:
    """Get a wiki page by slug."""
    with get_db() as db:
        page = db.query(WikiPage).filter(WikiPage.slug == slug).first()

        if not page:
            raise WikiPageNotFoundError(slug)

        version = _get_current_version(db, page.id)
        return _build_page_response(page, version)


async def handle_create_page(
    page_data: WikiPageCreate, current_user: Dict[str, Any]
) -> WikiPageResponse:
    """Create a new wiki page."""
    user_id = get_wiki_user_id(current_user)
    with get_db() as db:
        slug = page_data.slug or _generate_slug(page_data.title, db)

        existing = db.query(WikiPage).filter(WikiPage.slug == slug).first()
        if existing:
            raise WikiPageAlreadyExistsError(slug)

        if page_data.parent_id:
            parent = (
                db.query(WikiPage).filter(WikiPage.id == page_data.parent_id).first()
            )
            if not parent:
                raise WikiParentNotFoundError(page_data.parent_id)

        # Sanitize content to prevent XSS attacks
        sanitized_content = (
            sanitize_wiki_content(page_data.content) if page_data.content else None
        )

        page = WikiPage(
            slug=slug,
            title=page_data.title,
            content=sanitized_content,
            parent_id=page_data.parent_id,
            tags=page_data.tags if page_data.tags else None,
            is_published=page_data.is_published,
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(page)
        db.flush()

        _create_revision(db, page, user_id, "Initial version")
        _update_search_vector(db, page)

        db.commit()
        db.refresh(page)

        return _build_page_response(page, 1)


async def handle_update_page(
    slug: str, page_data: WikiPageUpdate, current_user: Dict[str, Any]
) -> WikiPageResponse:
    """Update a wiki page."""
    user_id = get_wiki_user_id(current_user)
    with get_db() as db:
        page = db.query(WikiPage).filter(WikiPage.slug == slug).first()

        if not page:
            raise WikiPageNotFoundError(slug)

        content_changed = False

        if page_data.title is not None:
            if page_data.title != page.title:
                content_changed = True
            page.title = page_data.title

        if page_data.content is not None:
            # Sanitize content to prevent XSS attacks
            sanitized_content = sanitize_wiki_content(page_data.content)
            if sanitized_content != page.content:
                content_changed = True
            page.content = sanitized_content

        if page_data.parent_id is not None:
            if page_data.parent_id:
                parent = (
                    db.query(WikiPage)
                    .filter(WikiPage.id == page_data.parent_id)
                    .first()
                )
                if not parent:
                    raise WikiParentNotFoundError(page_data.parent_id)
                if page_data.parent_id == page.id:
                    raise WikiSelfParentError()
                _check_circular_parent(db, page.id, page_data.parent_id)
            page.parent_id = page_data.parent_id

        if page_data.tags is not None:
            page.tags = page_data.tags if page_data.tags else None

        if page_data.is_published is not None:
            page.is_published = page_data.is_published

        page.updated_by = user_id

        if content_changed:
            _create_revision(db, page, user_id, page_data.change_summary)
            _update_search_vector(db, page)

        db.commit()
        db.refresh(page)

        version = _get_current_version(db, page.id)
        return _build_page_response(page, version)


async def handle_delete_page(slug: str) -> Dict[str, Any]:
    """Delete a wiki page."""
    with get_db() as db:
        page = db.query(WikiPage).filter(WikiPage.slug == slug).first()

        if not page:
            raise WikiPageNotFoundError(slug)

        children_count = (
            db.query(WikiPage).filter(WikiPage.parent_id == page.id).count()
        )
        if children_count > 0:
            raise WikiPageHasChildrenError(children_count)

        db.delete(page)
        db.commit()

        return {"success": True, "message": f"Page '{slug}' deleted successfully"}
