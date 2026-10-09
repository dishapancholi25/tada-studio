"""Database repository for document storage operations."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import cast, func, literal, or_, text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.types import Text

from ...database import get_db
from ....models import Document as DocumentModel
from ....models import DocumentChunk, DocumentCollection, User
from ..config import LOG_PREFIX
from ..exceptions import DocumentNotFoundError
from ..models import ChunkInfo, DocumentInfo


logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository for document database operations."""

    @staticmethod
    def create_document(
        file_id: str,
        collection_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
        storage_path: Optional[str] = None,
    ) -> DocumentModel:
        """Create a new document record.

        Args:
            file_id: Unique file ID
            collection_id: Collection ID
            file_name: Original filename
            file_type: File type/extension
            file_size: File size in bytes
            storage_path: Optional path to stored file (not used for ephemeral processing)

        Returns:
            Created DocumentModel
        """
        with get_db() as db:
            document = DocumentModel(
                id=file_id,
                collection_id=collection_id,
                name=file_name,
                file_name=file_name,
                file_type=file_type.upper() if file_type else "UNKNOWN",
                file_size=file_size,
                status="processing",
                storage_path=storage_path,
                uploaded_at=datetime.now(timezone.utc),
            )
            db.add(document)
            db.commit()
            db.refresh(document)

            logger.info(
                f"{LOG_PREFIX} Created document record: {file_id} ({file_name})"
            )

            return document

    @staticmethod
    def update_document_status(
        document_id: str,
        status: str,
        full_text: Optional[str] = None,
        error_message: Optional[str] = None,
        embedding_tokens: Optional[int] = None,
        embedding_cost: Optional[float] = None,
        embedding_model: Optional[str] = None,
    ) -> None:
        """Update document status and content.

        Args:
            document_id: Document ID
            status: New status ('processing', 'processed', 'failed')
            full_text: Optional full text content
            error_message: Optional error message
            embedding_tokens: Optional number of tokens used for embedding
            embedding_cost: Optional cost of embedding in USD
            embedding_model: Optional name of the embedding model used
        """
        with get_db() as db:
            document = (
                db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
            )

            if not document:
                raise DocumentNotFoundError(document_id)

            document.status = status
            if full_text:
                document.full_text_content = full_text
            if error_message:
                document.error_message = error_message
            if embedding_tokens is not None:
                document.embedding_tokens = embedding_tokens
            if embedding_cost is not None:
                document.embedding_cost = embedding_cost
            if embedding_model is not None:
                document.embedding_model = embedding_model

            db.commit()

            logger.info(
                f"{LOG_PREFIX} Updated document {document_id} status to: {status}"
            )

    @staticmethod
    def store_chunks(
        document_id: str,
        chunks: List[tuple[str, Optional[List[float]], dict]],
        db_session=None,
    ) -> List[ChunkInfo]:
        """Store document chunks with embeddings.

        Args:
            document_id: Document ID
            chunks: List of (content, embedding, metadata) tuples
            db_session: Optional existing database session

        Returns:
            List of ChunkInfo objects
        """

        def _store(db):
            stored_chunks = []

            for i, (content, embedding, metadata) in enumerate(chunks):
                try:
                    db_chunk = DocumentChunk(
                        document_id=str(document_id),
                        chunk_index=i,
                        content=content,
                        embedding=embedding,
                        chunk_metadata=metadata,
                    )
                    db.add(db_chunk)
                    db.flush()  # Flush to get the ID

                    stored_chunks.append(
                        ChunkInfo(
                            id=db_chunk.id,
                            index=i,
                            content=content[:100] + "..."
                            if len(content) > 100
                            else content,
                            has_embedding=embedding is not None,
                        )
                    )

                except Exception as e:
                    logger.error(f"{LOG_PREFIX} Error storing chunk {i}: {e}")
                    # Continue with other chunks

            db.commit()

            logger.info(
                f"{LOG_PREFIX} Stored {len(stored_chunks)} chunks for document {document_id}"
            )

            return stored_chunks

        if db_session:
            return _store(db_session)
        else:
            with get_db() as db:
                return _store(db)

    @staticmethod
    def get_document(document_id: str) -> Optional[DocumentInfo]:
        """Get document by ID.

        Args:
            document_id: Document ID

        Returns:
            DocumentInfo or None if not found
        """
        with get_db() as db:
            doc = (
                db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
            )

            if not doc:
                return None

            # Get chunk count
            chunk_count = (
                db.query(func.count(DocumentChunk.id))
                .filter(DocumentChunk.document_id == document_id)
                .scalar()
            )

            return DocumentInfo(
                id=str(doc.id),
                collection_id=str(doc.collection_id),
                name=doc.name,
                file_name=doc.file_name,
                file_type=doc.file_type,
                file_size=doc.file_size,
                status=doc.status,
                storage_path=doc.storage_path,
                uploaded_at=doc.uploaded_at,
                updated_at=doc.updated_at,
                chunk_count=chunk_count or 0,
                error_message=doc.error_message
                if hasattr(doc, "error_message")
                else None,
                embedding_tokens=doc.embedding_tokens,
                embedding_cost=doc.embedding_cost,
                embedding_model=doc.embedding_model,
            )

    @staticmethod
    def get_documents(
        collection_id: Optional[str] = None,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        user_groups: Optional[List[str]] = None,
        filter_type: Optional[str] = None,
    ) -> List[DocumentInfo]:
        """Get documents with optional filtering.

        Args:
            collection_id: Optional collection ID filter
            status: Optional status filter
            user_id: Optional user ID for ownership/visibility filtering
            user_groups: Optional list of group names the user belongs to
            filter_type: Optional filter type ('owned', 'shared', or 'all')

        Returns:
            List of DocumentInfo objects
        """
        if user_groups is None:
            user_groups = []

        with get_db() as db:
            # Query with chunk count, collection name, and owner info
            query = (
                db.query(
                    DocumentModel,
                    func.count(DocumentChunk.id).label("chunk_count"),
                    DocumentCollection.name.label("collection_name"),
                    DocumentCollection.user_id.label("collection_user_id"),
                    User.name.label("owner_name"),
                    User.email.label("owner_email"),
                )
                .join(
                    DocumentCollection,
                    DocumentModel.collection_id == DocumentCollection.id,
                )
                .outerjoin(User, DocumentCollection.user_id == User.id)
                .outerjoin(DocumentChunk, DocumentModel.id == DocumentChunk.document_id)
                .group_by(
                    DocumentModel.id,
                    DocumentCollection.name,
                    DocumentCollection.user_id,
                    User.name,
                    User.email,
                )
            )

            if collection_id:
                query = query.filter(DocumentModel.collection_id == collection_id)

            if status:
                query = query.filter(DocumentModel.status == status)

            # Apply visibility-based filtering when user_id and filter_type are provided
            if user_id and filter_type:
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
                    query = query.filter(owned_condition)
                elif filter_type == "shared":
                    query = query.filter(
                        shared_condition, DocumentCollection.user_id != user_id
                    )
                else:  # 'all'
                    query = query.filter(or_(owned_condition, shared_condition))

            results = query.order_by(DocumentModel.uploaded_at.desc()).all()

            documents = []
            for (
                doc,
                chunk_count,
                collection_name,
                collection_user_id,
                owner_name,
                owner_email,
            ) in results:
                documents.append(
                    DocumentInfo(
                        id=str(doc.id),
                        collection_id=str(doc.collection_id),
                        name=doc.name,
                        file_name=doc.file_name,
                        file_type=doc.file_type,
                        file_size=doc.file_size,
                        status=doc.status,
                        storage_path=doc.storage_path,
                        uploaded_at=doc.uploaded_at,
                        updated_at=doc.updated_at,
                        chunk_count=chunk_count or 0,
                        error_message=doc.error_message
                        if hasattr(doc, "error_message")
                        else None,
                        embedding_tokens=doc.embedding_tokens,
                        embedding_cost=doc.embedding_cost,
                        embedding_model=doc.embedding_model,
                        collection_name=collection_name,
                        collection_user_id=collection_user_id,
                        owner_name=owner_name,
                        owner_email=owner_email,
                    )
                )

            return documents

    @staticmethod
    def delete_document(document_id: str) -> bool:
        """Delete document from database.

        Args:
            document_id: Document ID

        Returns:
            True if deleted, False if not found
        """
        with get_db() as db:
            document = (
                db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
            )

            if not document:
                return False

            db.delete(document)
            db.commit()

            logger.info(f"{LOG_PREFIX} Deleted document {document_id} from database")

            return True

    @staticmethod
    def delete_failed_documents(collection_id: str) -> int:
        """Delete all failed documents in a collection.

        Args:
            collection_id: Collection ID
        Returns:
            Number of deleted documents
        """
        with get_db() as db:
            count = (
                db.query(DocumentModel)
                .filter(
                    DocumentModel.collection_id == collection_id,
                    DocumentModel.status == "failed",
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            logger.info(
                f"{LOG_PREFIX} Deleted {count} failed documents in collection {collection_id}"
            )
            return count

    @staticmethod
    def delete_chunks(document_id: str) -> int:
        """Delete all chunks for a document.

        Used when reprocessing a document with new chunking settings.

        Args:
            document_id: Document ID

        Returns:
            Number of deleted chunks
        """
        with get_db() as db:
            count = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == document_id)
                .delete(synchronize_session=False)
            )
            db.commit()

            logger.info(
                f"{LOG_PREFIX} Deleted {count} chunks for document {document_id}"
            )

            return count
