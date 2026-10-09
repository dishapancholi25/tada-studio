"""Database repository for collection operations."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import cast, func, literal, or_, text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.types import Text

from ...database import get_db
from ....models import (
    Document,
    DocumentChunk,
    DocumentCollection,
    GraphDefinition,
    User,
)
from ..config import LOG_PREFIX
from ..models import CollectionInfo


logger = logging.getLogger(__name__)


class CollectionRepository:
    """Repository for collection database operations."""

    @staticmethod
    def create_collection(
        collection_id: str,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        visible_to_groups: Optional[List[str]] = None,
    ) -> CollectionInfo:
        """Create a new collection.

        Args:
            collection_id: Unique collection ID
            name: Collection name
            description: Optional description
            user_id: Optional user ID
            visible_to_groups: List of group names that can access this collection

        Returns:
            CollectionInfo for created collection
        """
        from sqlalchemy.exc import IntegrityError

        with get_db() as db:
            collection = DocumentCollection(
                id=collection_id,
                name=name,
                description=description,
                user_id=user_id,
                created_at=datetime.now(timezone.utc),
            )
            collection.visible_to_groups = visible_to_groups or []
            db.add(collection)
            try:
                db.commit()
                db.refresh(collection)
            except IntegrityError as e:
                db.rollback()
                if "unique" in str(e).lower() and "name" in str(e).lower():
                    raise ValueError("You already have a collection with this name")
                raise

            # Get creator info
            created_by_name = None
            created_by_email = None
            if collection.user_id:
                user = db.query(User).filter(User.id == collection.user_id).first()
                if user:
                    created_by_name = user.name
                    created_by_email = user.email

            logger.info(f"{LOG_PREFIX} Created collection in database: {collection_id}")

            return CollectionInfo(
                id=str(collection.id),
                name=collection.name,
                description=collection.description,
                user_id=collection.user_id,
                visible_to_groups=collection.visible_to_groups or [],
                created_by_name=created_by_name,
                created_by_email=created_by_email,
                document_count=0,
                is_read_only=False,
                created_at=collection.created_at,
                updated_at=collection.updated_at,
                embedding_deployment_id=collection.embedding_deployment_id,
            )

    @staticmethod
    def get_collection(collection_id: str) -> Optional[CollectionInfo]:
        """Get collection by ID.

        Args:
            collection_id: Collection ID

        Returns:
            CollectionInfo or None if not found
        """
        with get_db() as db:
            col = (
                db.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            if not col:
                return None

            # Get creator info
            created_by_name = None
            created_by_email = None
            if col.user_id:
                user = db.query(User).filter(User.id == col.user_id).first()
                if user:
                    created_by_name = user.name
                    created_by_email = user.email

            # Get document count and embedding aggregates
            doc_stats = (
                db.query(
                    func.count(Document.id),
                    func.coalesce(func.sum(Document.embedding_tokens), 0),
                    func.coalesce(func.sum(Document.embedding_cost), 0),
                )
                .filter(Document.collection_id == col.id)
                .first()
            )
            document_count = doc_stats[0] if doc_stats else 0
            total_embedding_tokens = int(doc_stats[1]) if doc_stats else 0
            total_embedding_cost = float(doc_stats[2]) if doc_stats else 0.0

            return CollectionInfo(
                id=str(col.id),
                name=col.name,
                description=col.description,
                user_id=col.user_id,
                visible_to_groups=col.visible_to_groups or [],
                created_by_name=created_by_name,
                created_by_email=created_by_email,
                document_count=document_count,
                is_read_only=False,
                created_at=col.created_at,
                updated_at=col.updated_at,
                embedding_deployment_id=col.embedding_deployment_id,
                total_embedding_tokens=total_embedding_tokens,
                total_embedding_cost=total_embedding_cost,
            )

    @staticmethod
    def get_collections(
        user_id: str,
        user_groups: Optional[List[str]] = None,
        filter_type: str = "owned",
    ) -> List[CollectionInfo]:
        """Get collections with group-based visibility filtering.

        Uses JSONB GIN operators for efficient group overlap queries.

        Args:
            user_id: User ID requesting collections
            user_groups: List of group names the user belongs to
            filter_type: 'owned' (user's own), 'shared' (shared with user),
                         or 'all' (both owned and shared)

        Returns:
            List of CollectionInfo objects with all fields populated
        """
        if user_groups is None:
            user_groups = []

        with get_db() as db:
            # Subquery for document counts and embedding aggregates
            doc_count_subq = (
                db.query(
                    Document.collection_id,
                    func.count(Document.id).label("doc_count"),
                    func.coalesce(func.sum(Document.embedding_tokens), 0).label(
                        "total_embedding_tokens"
                    ),
                    func.coalesce(func.sum(Document.embedding_cost), 0).label(
                        "total_embedding_cost"
                    ),
                )
                .group_by(Document.collection_id)
                .subquery()
            )

            # Base query joining users for creator info and doc counts
            base_query = (
                db.query(
                    DocumentCollection,
                    User.name.label("creator_name"),
                    User.email.label("creator_email"),
                    func.coalesce(doc_count_subq.c.doc_count, 0).label("doc_count"),
                    func.coalesce(doc_count_subq.c.total_embedding_tokens, 0).label(
                        "total_embedding_tokens"
                    ),
                    func.coalesce(doc_count_subq.c.total_embedding_cost, 0).label(
                        "total_embedding_cost"
                    ),
                )
                .outerjoin(User, DocumentCollection.user_id == User.id)
                .outerjoin(
                    doc_count_subq,
                    DocumentCollection.id == doc_count_subq.c.collection_id,
                )
            )

            # JSONB GIN visibility conditions:
            # @> for __all__ containment, ?| for group overlap
            all_visible = DocumentCollection.visible_to_groups.op("@>")(
                text("'[\"__all__\"]'::jsonb")
            )

            if user_groups:
                groups_overlap = DocumentCollection.visible_to_groups.op("?|")(
                    cast(literal(user_groups), PG_ARRAY(Text))
                )
                shared_condition = or_(all_visible, groups_overlap)
            else:
                shared_condition = all_visible

            owned_condition = DocumentCollection.user_id == user_id

            if filter_type == "owned":
                query = base_query.filter(owned_condition)
            elif filter_type == "shared":
                query = base_query.filter(
                    shared_condition, DocumentCollection.user_id != user_id
                )
            else:  # 'all'
                query = base_query.filter(or_(owned_condition, shared_condition))

            rows = query.order_by(DocumentCollection.created_at.desc()).all()

            results = []
            for (
                col,
                creator_name,
                creator_email,
                doc_count,
                total_tokens,
                total_cost,
            ) in rows:
                is_read_only = col.user_id != user_id
                results.append(
                    CollectionInfo(
                        id=str(col.id),
                        name=col.name,
                        description=col.description,
                        user_id=col.user_id,
                        visible_to_groups=col.visible_to_groups or [],
                        created_by_name=creator_name,
                        created_by_email=creator_email,
                        document_count=doc_count,
                        is_read_only=is_read_only,
                        created_at=col.created_at,
                        updated_at=col.updated_at,
                        embedding_deployment_id=col.embedding_deployment_id,
                        total_embedding_tokens=int(total_tokens),
                        total_embedding_cost=float(total_cost),
                        search_count=col.search_count or 0,
                    )
                )

            return results

    @staticmethod
    def update_collection(
        collection_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        embedding_deployment_id: Optional[str] = None,
    ) -> Optional[CollectionInfo]:
        """Update collection name and/or description. Only the owner can update.

        Args:
            collection_id: Collection ID
            user_id: User ID requesting the update (must be owner)
            name: New name (if provided)
            description: New description (if provided)

        Returns:
            Updated CollectionInfo, or None if not found or not authorized
        """
        from sqlalchemy.exc import IntegrityError

        with get_db() as db:
            collection = (
                db.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            if not collection:
                return None

            if collection.user_id != user_id:
                return None

            if name is not None:
                collection.name = name
            if description is not None:
                collection.description = description
            if embedding_deployment_id is not None:
                collection.embedding_deployment_id = embedding_deployment_id
            collection.updated_at = datetime.now(timezone.utc)

            try:
                db.commit()
                db.refresh(collection)
            except IntegrityError as e:
                db.rollback()
                if "unique" in str(e).lower() and "name" in str(e).lower():
                    raise ValueError("You already have a collection with this name")
                raise

            # Get creator info
            created_by_name = None
            created_by_email = None
            if collection.user_id:
                user = db.query(User).filter(User.id == collection.user_id).first()
                if user:
                    created_by_name = user.name
                    created_by_email = user.email

            # Get document count
            document_count = (
                db.query(func.count(Document.id))
                .filter(Document.collection_id == collection.id)
                .scalar()
            ) or 0

            return CollectionInfo(
                id=str(collection.id),
                name=collection.name,
                description=collection.description,
                user_id=collection.user_id,
                visible_to_groups=collection.visible_to_groups or [],
                created_by_name=created_by_name,
                created_by_email=created_by_email,
                document_count=document_count,
                is_read_only=False,
                created_at=collection.created_at,
                updated_at=collection.updated_at,
                embedding_deployment_id=collection.embedding_deployment_id,
            )

    @staticmethod
    def update_collection_visibility(
        collection_id: str, visible_to_groups: List[str], user_id: str
    ) -> bool:
        """Update collection visibility groups. Only the owner can update.

        Args:
            collection_id: Collection ID
            visible_to_groups: New list of group names
            user_id: User ID requesting the update (must be owner)

        Returns:
            True if updated, False if not found or not authorized
        """
        with get_db() as db:
            collection = (
                db.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            if not collection:
                return False

            # Check ownership
            if collection.user_id != user_id:
                return False

            collection.visible_to_groups = visible_to_groups
            collection.updated_at = datetime.now(timezone.utc)
            db.commit()

            return True

    @staticmethod
    def check_collection_access(
        collection_id: str, user_id: str, user_groups: List[str]
    ) -> bool:
        """Check if a user has access to a collection.

        Args:
            collection_id: Collection ID
            user_id: User ID to check access for
            user_groups: List of group names the user belongs to

        Returns:
            True if user has access, False otherwise
        """
        with get_db() as db:
            collection = (
                db.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            if not collection:
                return False

            # Owner always has access
            if collection.user_id == user_id:
                return True

            visible_groups = collection.visible_to_groups or []

            # __all__ grants access to everyone
            if "__all__" in visible_groups:
                return True

            # Check group overlap
            if any(group in visible_groups for group in user_groups):
                return True

            return False

    @staticmethod
    def get_collection_references(collection_id: str) -> Dict[str, Any]:
        """Get documents, chunks, and workflows referencing a collection.

        Args:
            collection_id: Collection ID

        Returns:
            Dict with document_count, chunk_count, documents list,
            and referencing workflows
        """
        with get_db() as db:
            collection = (
                db.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            if not collection:
                return {
                    "document_count": 0,
                    "chunk_count": 0,
                    "documents": [],
                    "workflow_count": 0,
                    "workflows": [],
                }

            # Get documents and chunk counts
            documents = (
                db.query(Document).filter(Document.collection_id == collection_id).all()
            )

            document_count = len(documents)
            doc_ids = [doc.id for doc in documents]

            # Single query for all chunk counts (avoids N+1)
            chunk_counts_query = (
                (
                    db.query(
                        DocumentChunk.document_id,
                        func.count(DocumentChunk.id).label("chunk_count"),
                    )
                    .filter(DocumentChunk.document_id.in_(doc_ids))
                    .group_by(DocumentChunk.document_id)
                    .all()
                )
                if doc_ids
                else []
            )

            chunk_count_map = {doc_id: count for doc_id, count in chunk_counts_query}

            chunk_count = sum(chunk_count_map.values())
            doc_list = []
            for doc in documents:
                doc_chunk_count = chunk_count_map.get(doc.id, 0)
                doc_list.append(
                    {
                        "id": str(doc.id),
                        "name": doc.name,
                        "status": doc.status,
                        "chunk_count": doc_chunk_count,
                    }
                )

            # Get referencing workflows
            collection_id_str = str(collection.id)
            workflows = (
                db.query(GraphDefinition)
                .filter(GraphDefinition.is_latest.is_(True))
                .all()
            )

            referencing_workflows = []
            for workflow in workflows:
                definition = workflow.definition_json
                if not definition:
                    continue

                nodes = definition.get("nodes", [])
                for node in nodes:
                    config = node.get("data", {}).get("document_search_config", {})
                    collections = config.get("document_collections", [])
                    if collection_id_str in collections:
                        referencing_workflows.append(workflow.name)
                        break

            return {
                "document_count": document_count,
                "chunk_count": chunk_count,
                "documents": doc_list,
                "workflow_count": len(referencing_workflows),
                "workflows": referencing_workflows,
            }

    @staticmethod
    def set_embedding_deployment_id(
        collection_id: str, embedding_deployment_id: str
    ) -> bool:
        """Persist the embedding model deployment used for this collection.

        Should only be called once, when the first document is uploaded.

        Args:
            collection_id: Collection ID
            embedding_deployment_id: Deployment ID from model_deployments table

        Returns:
            True if updated, False if collection not found
        """
        with get_db() as db:
            collection = (
                db.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )
            if not collection:
                return False
            collection.embedding_deployment_id = embedding_deployment_id
            collection.updated_at = datetime.now(timezone.utc)
            db.commit()
            return True

    @staticmethod
    def delete_collection(collection_id: str) -> bool:
        """Delete a collection.

        Args:
            collection_id: Collection ID

        Returns:
            True if deleted, False if not found
        """
        with get_db() as db:
            collection = (
                db.query(DocumentCollection)
                .filter(DocumentCollection.id == collection_id)
                .first()
            )

            if not collection:
                return False

            # Documents will be cascade deleted due to foreign key
            db.delete(collection)
            db.commit()

            logger.info(
                f"{LOG_PREFIX} Deleted collection {collection_id} from database"
            )

            return True
