"""Wiki revision handlers."""

from typing import Any, Dict, List

from sqlalchemy import desc

from backend.models import WikiPage, WikiRevision
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.wiki import sanitize_wiki_content

from ..dependencies import get_wiki_user_id
from ..exceptions import WikiPageNotFoundError, WikiRevisionNotFoundError
from ..models import WikiPageResponse, WikiRevisionResponse

from .page_crud import (
    _build_page_response,
    _create_revision,
    _get_current_version,
    _update_search_vector,
)

logger = get_logger(__name__)


async def handle_get_page_revisions(slug: str) -> List[WikiRevisionResponse]:
    """Get revision history for a wiki page."""
    with get_db() as db:
        page = db.query(WikiPage).filter(WikiPage.slug == slug).first()

        if not page:
            raise WikiPageNotFoundError(slug)

        revisions = (
            db.query(WikiRevision)
            .filter(WikiRevision.page_id == page.id)
            .order_by(desc(WikiRevision.version))
            .all()
        )

        return [WikiRevisionResponse.model_validate(rev) for rev in revisions]


async def handle_get_page_revision(slug: str, version: int) -> WikiRevisionResponse:
    """Get a specific revision of a wiki page."""
    with get_db() as db:
        page = db.query(WikiPage).filter(WikiPage.slug == slug).first()

        if not page:
            raise WikiPageNotFoundError(slug)

        revision = (
            db.query(WikiRevision)
            .filter(WikiRevision.page_id == page.id, WikiRevision.version == version)
            .first()
        )

        if not revision:
            raise WikiRevisionNotFoundError(slug, version)

        return WikiRevisionResponse.model_validate(revision)


async def handle_restore_page_revision(
    slug: str, version: int, current_user: Dict[str, Any]
) -> WikiPageResponse:
    """Restore a wiki page to a previous revision."""
    user_id = get_wiki_user_id(current_user)
    with get_db() as db:
        page = db.query(WikiPage).filter(WikiPage.slug == slug).first()

        if not page:
            raise WikiPageNotFoundError(slug)

        revision = (
            db.query(WikiRevision)
            .filter(WikiRevision.page_id == page.id, WikiRevision.version == version)
            .first()
        )

        if not revision:
            raise WikiRevisionNotFoundError(slug, version)

        page.title = revision.title
        # Sanitize content when restoring (may be from pre-sanitization era)
        page.content = (
            sanitize_wiki_content(revision.content) if revision.content else None
        )
        page.updated_by = user_id

        _create_revision(db, page, user_id, f"Restored to version {version}")
        _update_search_vector(db, page)

        db.commit()
        db.refresh(page)

        current_version = _get_current_version(db, page.id)
        return _build_page_response(page, current_version)
