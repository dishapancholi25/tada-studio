"""Wiki search and tree handlers."""

from typing import List

from sqlalchemy import text

from backend.models import WikiPage
from backend.services.config import get_logger
from backend.services.database import get_db

from ..models import WikiPageListItem, WikiTreeNode

logger = get_logger(__name__)


async def handle_get_page_tree(include_unpublished: bool) -> List[WikiTreeNode]:
    """Get hierarchical tree structure of all wiki pages."""
    with get_db() as db:
        query = db.query(WikiPage)

        if not include_unpublished:
            query = query.filter(WikiPage.is_published == True)  # noqa: E712

        pages = query.order_by(WikiPage.order_index, WikiPage.title).all()

        # Build tree structure – construct nodes explicitly with empty children
        # to avoid WikiPage.children backref being picked up by model_validate,
        # which would duplicate children added by the manual loop below.
        page_map = {
            page.id: WikiTreeNode(
                id=page.id,
                slug=page.slug,
                title=page.title,
                parent_id=page.parent_id,
                order_index=page.order_index,
                children=[],
            )
            for page in pages
        }

        logger.debug("Building wiki tree from %d pages", len(pages))

        root_nodes = []
        for page in pages:
            node = page_map[page.id]
            if page.parent_id and page.parent_id in page_map:
                page_map[page.parent_id].children.append(node)
            else:
                root_nodes.append(node)

        logger.debug("Wiki tree: %d root nodes", len(root_nodes))
        return root_nodes


async def handle_search_pages(
    q: str, include_unpublished: bool, limit: int
) -> List[WikiPageListItem]:
    """Search wiki pages using full-text search."""
    with get_db() as db:
        query = db.query(WikiPage)

        if not include_unpublished:
            query = query.filter(WikiPage.is_published == True)  # noqa: E712

        search_query = text(
            """
            SELECT id FROM wiki_pages
            WHERE search_vector @@ to_tsquery('english', :search_query)
            OR title ILIKE :like_query
            OR content ILIKE :like_query
            ORDER BY
                ts_rank(search_vector, to_tsquery('english', :search_query)) DESC,
                updated_at DESC
            LIMIT :limit
        """
        )

        ts_query = " & ".join(q.split())
        like_query = f"%{q}%"

        result = db.execute(
            search_query,
            {"search_query": ts_query, "like_query": like_query, "limit": limit},
        )
        page_ids = [row[0] for row in result]

        if not page_ids:
            return []

        pages = query.filter(WikiPage.id.in_(page_ids)).all()

        # Sort by the order returned from search
        pages_dict = {page.id: page for page in pages}
        sorted_pages = [
            pages_dict[page_id] for page_id in page_ids if page_id in pages_dict
        ]

        return [WikiPageListItem.model_validate(page) for page in sorted_pages]
