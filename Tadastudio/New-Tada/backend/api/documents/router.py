"""API endpoints for document management and operations."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from ..auth.dependencies import get_current_user, require_active_user
from backend.services.auth.scope_enforcer import require_any_scope, require_scope
from ...services.database import get_db
from ...models import User
from ...models.documents.collection import DocumentCollection
from ...services.document_storage import DocumentStorageService, document_search_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/documents",
    tags=["documents"],
    dependencies=[Depends(require_active_user)],
)

# PAT-accessible router — mounted at /api/pat/documents
# Routes under this prefix bypass oauth2-proxy (Ingress routes /api/pat/ directly to backend-svc).
# Each endpoint must enforce its own PAT scope check via get_current_user + require_any_scope.
pat_router = APIRouter(
    prefix="/api/pat/documents",
    tags=["documents-pat"],
)


# Helper function to resolve user identifier to user_id
def get_user_id_from_claims(current_user: Dict[str, Any]) -> str:
    """Extract user_id from JWT claims.

    For OAuth users, uses sub directly or looks up by email.
    """
    email = current_user.get("email")
    sub = current_user.get("sub")

    with get_db() as db:
        # Try User by sub
        if sub:
            user = db.query(User).filter(User.id == sub).first()
            if user:
                return user.id

        # Try by email
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                return user.id

    raise HTTPException(status_code=401, detail="User not found")


# Initialize services

document_service = DocumentStorageService()


def _increment_search_counts(collection_ids: List[str]) -> None:
    """Increment search_count for the given collection IDs."""
    try:
        with get_db() as db:
            db.query(DocumentCollection).filter(
                DocumentCollection.id.in_(collection_ids)
            ).update(
                {DocumentCollection.search_count: DocumentCollection.search_count + 1},
                synchronize_session=False,
            )
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to increment search counts: {e}")


class CollectionCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    visible_to_groups: List[str] = Field(default_factory=list)


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    user_id: Optional[str]
    visible_to_groups: List[str]
    created_by_name: Optional[str]
    created_by_email: Optional[str]
    is_read_only: bool
    created_at: str
    updated_at: Optional[str]
    embedding_deployment_id: Optional[str] = None
    document_count: Optional[int] = None
    total_embedding_tokens: int = 0
    total_embedding_cost: float = 0.0
    search_count: int = 0


class CollectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    embedding_deployment_id: Optional[str] = None


class UpdateVisibilityRequest(BaseModel):
    visible_to_groups: List[str]


class CollectionReferencesResponse(BaseModel):
    document_count: int
    chunk_count: int
    documents: List[Dict[str, Any]] = Field(default_factory=list)
    workflow_count: int
    workflows: List[str] = Field(default_factory=list)


class DocumentResponse(BaseModel):
    id: str
    collection_id: str
    name: str
    type: str
    size: int
    status: str
    chunk_count: int
    upload_date: str
    error_message: Optional[str] = None
    embedding_tokens: Optional[int] = None
    embedding_cost: Optional[float] = None
    embedding_model: Optional[str] = None
    collection_name: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    is_read_only: bool = False


class SearchRequest(BaseModel):
    query: str
    collection_ids: List[str]
    document_ids: Optional[List[str]] = None  # Optional: filter by specific documents
    k: int = 4
    search_type: str = "similarity"
    include_metadata: bool = True
    # Hybrid search parameters
    hybrid_enabled: bool = False
    search_mode: str = "vector"  # vector, keyword, hybrid
    keyword_weight: float = 0.3
    rrf_k: int = 60
    text_config: str = "english"


class ChunkPreviewRequest(BaseModel):
    text: str
    strategy: str = "recursive"
    chunk_size: int = 1000
    chunk_overlap: int = 200


class ReprocessRequest(BaseModel):
    document_id: str
    chunk_size: int = 1000
    chunk_overlap: int = 200
    strategy: str = "recursive"
    embedding_deployment_id: Optional[str] = None


@router.post("/upload", dependencies=[Depends(require_scope("document:*:write"))])
async def upload_documents(
    files: List[UploadFile] = File(...),
    collection_id: str = Form(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    loader_mode: str = Form("single"),
    strategy: str = Form("recursive"),
    embedding_deployment_id: Optional[str] = Form(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Upload multiple documents to a collection."""

    try:
        user_id = get_user_id_from_claims(current_user)

        # Enforce owner-only access for uploads
        collection = document_service.get_collection(collection_id)
        if not collection or collection.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only the collection creator can upload documents to this collection",
            )

        # Validate embedding model consistency: once a collection has documents
        # embedded with a specific model, all subsequent uploads must use the same model
        if collection.embedding_deployment_id and embedding_deployment_id:
            if embedding_deployment_id != collection.embedding_deployment_id:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"This collection uses embedding model '{collection.embedding_deployment_id}'. "
                        "You must use the same embedding model for all uploads to this collection, "
                        "or re-vectorise all existing documents before switching models."
                    ),
                )

        uploaded_documents = []

        for file in files:
            # Check file type
            if not document_service.allowed_file(file.filename):
                logger.warning(f"Unsupported file type: {file.filename}")
                continue

            # Read file content
            content = await file.read()

            # Process and store document
            try:
                result = await document_service.upload_document(
                    file_name=file.filename,
                    file_content=content,
                    collection_id=collection_id,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    loader_mode=loader_mode,
                    strategy=strategy,
                    embedding_deployment_id=embedding_deployment_id,
                )

                # Chunks are now stored directly in PostgreSQL by document_service
                # No need to separately add to vector store
                # Note: We don't need to check for chunks attribute as they're already stored in DB

                uploaded_documents.append(
                    {
                        "id": str(result.document.id),
                        "name": result.document.name,
                        "status": result.document.status,
                        "chunk_count": result.document.chunk_count,
                        "error_message": result.document.error_message,
                        "embedding_tokens": result.embedding_tokens,
                        "embedding_cost": result.embedding_cost,
                    }
                )

            except Exception as e:
                logger.error(f"Error processing {file.filename}: {str(e)}")
                uploaded_documents.append(
                    {"name": file.filename, "status": "failed", "error_message": str(e)}
                )

        # Lock in the embedding model for this collection on first successful upload
        if embedding_deployment_id and not collection.embedding_deployment_id:
            document_service.collection_service.set_embedding_deployment_id(
                collection_id, embedding_deployment_id
            )

        total_embedding_tokens = sum(
            d.get("embedding_tokens", 0) or 0 for d in uploaded_documents
        )
        total_embedding_cost = sum(
            d.get("embedding_cost", 0) or 0 for d in uploaded_documents
        )

        return JSONResponse(
            content={
                "message": f"Processed {len(uploaded_documents)} documents",
                "documents": uploaded_documents,
                "embedding_tokens": total_embedding_tokens,
                "embedding_cost": total_embedding_cost,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in document upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", dependencies=[Depends(require_scope("document:*:read"))])
async def list_documents(
    collection_id: Optional[str] = None,
    status: Optional[str] = None,
    filter_type: Optional[str] = Query(None, regex="^(all|my|shared)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List documents with optional filtering."""
    try:
        user_id = get_user_id_from_claims(current_user)
        user_groups = []
        mapped_filter = None

        if filter_type:
            from ...services.groups.service import GroupService

            user_groups = GroupService().get_user_groups(user_id)
            mapped_filter = "owned" if filter_type == "my" else filter_type

        documents = document_service.get_documents(
            collection_id=collection_id,
            status=status,
            user_id=user_id,
            user_groups=user_groups,
            filter_type=mapped_filter,
        )

        return [
            DocumentResponse(
                id=str(doc.id),
                collection_id=str(doc.collection_id),
                name=doc.name,
                type=doc.file_type or "Unknown",
                size=doc.file_size or 0,
                status=doc.status,
                chunk_count=doc.chunk_count,
                upload_date=doc.uploaded_at.isoformat()
                if doc.uploaded_at and hasattr(doc.uploaded_at, "isoformat")
                else None,
                error_message=doc.error_message,
                embedding_tokens=doc.embedding_tokens,
                embedding_cost=doc.embedding_cost,
                embedding_model=doc.embedding_model,
                collection_name=doc.collection_name,
                owner_name=doc.owner_name,
                owner_email=doc.owner_email,
                is_read_only=doc.collection_user_id is not None
                and doc.collection_user_id != user_id,
            )
            for doc in documents
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}", dependencies=[Depends(require_scope("document:*:write"))])
async def delete_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Delete a document and its vectors. Only the collection owner can delete."""
    try:
        user_id = get_user_id_from_claims(current_user)

        # Look up the document to find its collection and verify ownership
        doc_info = document_service.repository.get_document(document_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")

        collection = document_service.get_collection(doc_info.collection_id)
        if not collection or collection.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only the collection owner can delete documents from this collection",
            )

        success = document_service.delete_document(document_id)

        if not success:
            raise HTTPException(status_code=404, detail="Document not found")

        return {"message": "Document deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reprocess")
async def reprocess_document(
    request: ReprocessRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Reprocess an existing document with new chunking settings.

    Only the collection owner can reprocess documents.
    This allows changing chunk size, overlap, or strategy without re-uploading.
    Useful for optimizing retrieval after initial upload.
    """
    try:
        user_id = get_user_id_from_claims(current_user)

        # Look up the document to find its collection and verify ownership
        doc_info = document_service.repository.get_document(request.document_id)
        if not doc_info:
            raise HTTPException(status_code=404, detail="Document not found")

        collection = document_service.get_collection(doc_info.collection_id)
        if not collection or collection.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only the collection owner can reprocess documents in this collection",
            )

        result = await document_service.reprocess_document(
            document_id=request.document_id,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            strategy=request.strategy,
            embedding_deployment_id=request.embedding_deployment_id,
        )

        if not result.success:
            raise HTTPException(status_code=400, detail=result.message)

        return {
            "success": True,
            "document_id": str(result.document.id),
            "name": result.document.name,
            "new_chunk_count": result.document.chunk_count,
            "message": result.message,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/chunks")
async def get_document_chunks(document_id: str, limit: int = 10):
    """Preview document chunks (for testing/debugging)."""
    try:
        # This would require querying the vector store directly
        # For now, return a placeholder
        return {
            "document_id": document_id,
            "message": "Chunk preview not yet implemented",
            "chunks": [],
        }

    except Exception as e:
        logger.error(f"Error getting document chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{document_id}/download",
    dependencies=[Depends(require_scope("document:*:read"))],
)
async def download_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Resolve a downloadable URL for the original uploaded file of a document.

    Returns a JSON response with the download URL rather than redirecting or
    streaming the file. Response shape::

        {
          "success": true,
          "document_id": "...",
          "file_name": "...",
          "url": "<presigned blob URL>" | null,
          "url_type": "presigned" | "local",
          "storage": "blob" | "local"
        }

    Resolution flow:
      1. Azure Blob Storage — direct prefix lookup by document_id (no DB needed),
         returns a short-lived presigned SAS URL.
      2. Database record — resolve blob SAS URL from stored storage_path.
      3. Local filesystem — file exists on disk but has no presigned URL, so
         ``url`` is null and ``storage`` is ``local``.
      4. 404 — none of the above succeeded.

    Access is granted to the collection owner and users with shared collection access.

    When the DB row is missing, falls back to probing Azure Blob for
    ``documents/{document_id}.*`` and returning its presigned URL. This preserves
    downloads across environments where DB and blob storage have drifted, at the
    cost of not enforcing collection-level authorization for orphan blobs
    (explicitly accepted trade-off; documented in security review).
    """
    try:
        user_id = get_user_id_from_claims(current_user)
        caller_email = current_user.get("email") or current_user.get("sub") or "unknown"
        logger.info(
            "[download] start document_id=%s user=%s",
            document_id,
            caller_email,
        )

        doc_info = document_service.repository.get_document(document_id)
        logger.info(
            "[download] db_lookup document_id=%s found=%s",
            document_id,
            bool(doc_info),
        )

        # ------------------------------------------------------------------
        # Blob-first-when-DB-misses fallback.
        # If the DB row is absent but the file exists in blob, serve it.
        # No collection_id is available, so this bypasses check_collection_access.
        # ------------------------------------------------------------------
        if not doc_info:
            logger.info(
                "[download] blob_fallback probing document_id=%s",
                document_id,
            )
            fallback_storage_path = document_service.find_blob_storage_path_by_document_id(
                document_id
            )
            logger.info(
                "[download] blob_fallback result document_id=%s storage_path=%s",
                document_id,
                fallback_storage_path,
            )
            if not fallback_storage_path:
                logger.warning(
                    "[download] not_found document_id=%s user=%s (no DB row, no blob)",
                    document_id,
                    caller_email,
                )
                raise HTTPException(status_code=404, detail="Document not found")

            logger.warning(
                "[AUDIT] Orphan-blob download document_id=%s user=%s "
                "storage_path=%s (no DB row; authorization skipped)",
                document_id,
                caller_email,
                fallback_storage_path,
            )

            download_name = f"{document_id}{Path(fallback_storage_path).suffix}"
            direct_url = document_service.resolve_document_download_url(
                storage_path=fallback_storage_path,
                file_name=download_name,
            )
            if direct_url:
                logger.info(
                    "[download] blob_fallback url document_id=%s user=%s",
                    document_id,
                    caller_email,
                )
                return {
                    "success": True,
                    "document_id": document_id,
                    "file_name": download_name,
                    "url": direct_url,
                    "url_type": "presigned",
                    "storage": "blob",
                }

            logger.warning(
                "[download] blob_fallback no_sas document_id=%s storage_path=%s",
                document_id,
                fallback_storage_path,
            )
            raise HTTPException(
                status_code=404,
                detail="Stored file not found",
            )

        if not document_service.check_collection_access(doc_info.collection_id, user_id):
            logger.warning(
                "[download] forbidden document_id=%s user=%s collection_id=%s",
                document_id,
                caller_email,
                doc_info.collection_id,
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this document",
            )

        if not doc_info.storage_path:
            logger.warning(
                "[download] missing_storage_path document_id=%s",
                document_id,
            )
            raise HTTPException(
                status_code=404,
                detail="Stored file path is not available for this document",
            )

        download_name = doc_info.file_name or doc_info.name or f"{document_id}.bin"

        # Prefer direct blob SAS download URLs when storage points to Azure Blob.
        direct_download_url = document_service.resolve_document_download_url(
            storage_path=doc_info.storage_path,
            file_name=download_name,
        )
        if direct_download_url:
            logger.info(
                "[download] blob_url document_id=%s user=%s",
                document_id,
                caller_email,
            )
            return {
                "success": True,
                "document_id": document_id,
                "file_name": download_name,
                "url": direct_download_url,
                "url_type": "presigned",
                "storage": "blob",
            }

        file_path = Path(doc_info.storage_path)
        if not file_path.exists() or not file_path.is_file():
            logger.warning(
                "[download] local_file_missing document_id=%s path=%s",
                document_id,
                doc_info.storage_path,
            )
            raise HTTPException(status_code=404, detail="Stored file not found")

        logger.info(
            "[download] local_no_url document_id=%s user=%s path=%s",
            document_id,
            caller_email,
            doc_info.storage_path,
        )
        return {
            "success": True,
            "document_id": document_id,
            "file_name": download_name,
            "url": None,
            "url_type": "local",
            "storage": "local",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "[download] error document_id=%s error=%s",
            document_id,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


def _view_response(
    *,
    redirect: bool,
    document_id: str,
    file_name: str,
    file_url: str,
):
    """Build the /view response: JSON with the fresh blob URL, or a 307 redirect."""
    if redirect:
        return RedirectResponse(url=file_url, status_code=307)

    ttl_minutes = int(os.getenv("AZURE_BLOB_SAS_TTL_MINUTES", "60"))
    return {
        "success": True,
        "document_id": document_id,
        "file_name": file_name,
        "file_url": file_url,
        "url": file_url,
        "url_type": "presigned",
        "storage": "blob",
        "expires_in_minutes": ttl_minutes,
    }


@router.get(
    "/{document_id}/view",
    dependencies=[Depends(require_any_scope(["document:*:read", "workflow:*:execute"]))],
)
async def view_document(
    document_id: str,
    redirect: bool = Query(
        False,
        description=(
            "When true, issue a 307 redirect to the blob URL (for opening directly "
            "in a browser). When false (default), return the fresh blob URL as JSON."
        ),
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return a freshly-minted blob URL for the original uploaded file.

    Each request generates a new short-lived Azure Blob SAS URL (default TTL
    ``AZURE_BLOB_SAS_TTL_MINUTES``, 60 minutes). Because a new URL is minted on
    every call, clients that receive an expired URL can simply re-request this
    endpoint to obtain a fresh one.

    Response modes:
      - Default (``redirect=false``): return the fresh blob URL as JSON, e.g.
        ``{"success": true, "file_url": "https://...", "url_type": "presigned"}``.
      - ``redirect=true``: issue an HTTP 307 redirect to the blob URL so the file
        opens/downloads directly in a browser.

    Resolution flow:
      1. Azure Blob Storage — direct prefix lookup by document_id (no DB needed),
         mint a short-lived presigned SAS URL.
      2. Database record — resolve blob SAS URL from stored storage_path.
      3. Local filesystem — stream the file from disk (no URL to return).
      4. 404 — none of the above succeeded.

    Access is granted to the collection owner and users with shared collection access.
    """
    try:
        user_id = get_user_id_from_claims(current_user)
        caller_email = current_user.get("email") or current_user.get("sub") or "unknown"
        logger.info(
            "[view] start document_id=%s user=%s",
            document_id,
            caller_email,
        )

        doc_info = document_service.repository.get_document(document_id)
        logger.info(
            "[view] db_lookup document_id=%s found=%s",
            document_id,
            bool(doc_info),
        )

        # Blob-first-when-DB-misses fallback (mirrors download_document).
        if not doc_info:
            fallback_storage_path = document_service.find_blob_storage_path_by_document_id(
                document_id
            )
            if not fallback_storage_path:
                logger.warning(
                    "[view] not_found document_id=%s user=%s (no DB row, no blob)",
                    document_id,
                    caller_email,
                )
                raise HTTPException(status_code=404, detail="Document not found")

            logger.warning(
                "[AUDIT] Orphan-blob view document_id=%s user=%s "
                "storage_path=%s (no DB row; authorization skipped)",
                document_id,
                caller_email,
                fallback_storage_path,
            )

            download_name = f"{document_id}{Path(fallback_storage_path).suffix}"
            direct_url = document_service.resolve_document_download_url(
                storage_path=fallback_storage_path,
                file_name=download_name,
            )
            if direct_url:
                logger.info(
                    "[view] blob_fallback document_id=%s user=%s redirect=%s",
                    document_id,
                    caller_email,
                    redirect,
                )
                return _view_response(
                    redirect=redirect,
                    document_id=document_id,
                    file_name=download_name,
                    file_url=direct_url,
                )

            raise HTTPException(status_code=404, detail="Stored file not found")

        if not document_service.check_collection_access(doc_info.collection_id, user_id):
            logger.warning(
                "[view] forbidden document_id=%s user=%s collection_id=%s",
                document_id,
                caller_email,
                doc_info.collection_id,
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this document",
            )

        if not doc_info.storage_path:
            raise HTTPException(
                status_code=404,
                detail="Stored file path is not available for this document",
            )

        download_name = doc_info.file_name or doc_info.name or f"{document_id}.bin"

        direct_download_url = document_service.resolve_document_download_url(
            storage_path=doc_info.storage_path,
            file_name=download_name,
        )
        if direct_download_url:
            logger.info(
                "[view] blob document_id=%s user=%s redirect=%s",
                document_id,
                caller_email,
                redirect,
            )
            return _view_response(
                redirect=redirect,
                document_id=document_id,
                file_name=download_name,
                file_url=direct_download_url,
            )

        file_path = Path(doc_info.storage_path)
        if not file_path.exists() or not file_path.is_file():
            logger.warning(
                "[view] local_file_missing document_id=%s path=%s",
                document_id,
                doc_info.storage_path,
            )
            raise HTTPException(status_code=404, detail="Stored file not found")

        logger.info(
            "[view] local_stream document_id=%s user=%s path=%s",
            document_id,
            caller_email,
            doc_info.storage_path,
        )
        return FileResponse(
            path=str(file_path),
            filename=download_name,
            media_type="application/octet-stream",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "[view] error document_id=%s error=%s",
            document_id,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


# PAT alias: /api/pat/documents/{document_id}/view
# Ingress routes /api/pat/ directly to backend-svc (no oauth2-proxy).
# Auth is enforced by get_current_user (PAT token) + require_any_scope below.
@pat_router.get(
    "/{document_id}/view",
    dependencies=[Depends(require_any_scope(["document:*:read", "workflow:*:execute"]))],
)
async def view_document_pat(
    document_id: str,
    redirect: bool = Query(False),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """PAT-accessible alias for /{document_id}/view — identical behaviour."""
    return await view_document(document_id=document_id, redirect=redirect, current_user=current_user)


@router.get("/collections", dependencies=[Depends(require_scope("document:*:read"))])
async def list_collections(
    filter_type: str = Query("all", regex="^(all|my|shared)$"),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List document collections for the authenticated user with group-based filtering."""
    try:
        user_id = get_user_id_from_claims(current_user)

        # Map 'my' to 'owned', default is 'all' (owned + shared)
        mapped_filter = "owned" if filter_type == "my" else filter_type

        collections = document_service.get_collections(
            user_id=user_id, filter_type=mapped_filter
        )

        return [
            CollectionResponse(
                id=str(col.id),
                name=col.name,
                description=col.description,
                user_id=col.user_id,
                visible_to_groups=col.visible_to_groups,
                created_by_name=col.created_by_name,
                created_by_email=col.created_by_email,
                is_read_only=col.is_read_only,
                created_at=col.created_at.isoformat()
                if hasattr(col.created_at, "isoformat")
                else str(col.created_at),
                updated_at=col.updated_at.isoformat()
                if col.updated_at and hasattr(col.updated_at, "isoformat")
                else str(col.updated_at)
                if col.updated_at
                else None,
                embedding_deployment_id=col.embedding_deployment_id,
                document_count=col.document_count,
                total_embedding_tokens=col.total_embedding_tokens,
                total_embedding_cost=col.total_embedding_cost,
                search_count=getattr(col, "search_count", 0) or 0,
            )
            for col in collections
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def _build_collections_with_documents_response(
    current_user: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build collection+document payload used by both internal and external routes."""
    user_id = get_user_id_from_claims(current_user)
    collections = document_service.get_collections(user_id=user_id, filter_type="all")
    result: List[Dict[str, Any]] = []

    for col in collections:
        documents = document_service.get_documents(collection_id=col.id)
        processed_count = 0
        failed_count = 0
        document_list = []

        for doc in documents:
            if doc.status == "processed":
                processed_count += 1
            elif doc.status == "failed":
                failed_count += 1

            document_list.append(
                {
                    "id": str(doc.id),
                    "name": doc.name,
                    "type": doc.file_type,
                    "size": doc.file_size,
                    "status": doc.status,
                    "chunk_count": doc.chunk_count,
                    "upload_date": doc.uploaded_at.isoformat()
                    if hasattr(doc.uploaded_at, "isoformat")
                    else str(doc.uploaded_at),
                    "blob_url": document_service.resolve_document_download_url(
                        storage_path=doc.storage_path,
                        file_name=doc.file_name or doc.name,
                    ),
                    "error_message": doc.error_message,
                    "embedding_tokens": doc.embedding_tokens,
                    "embedding_cost": doc.embedding_cost,
                    "embedding_model": doc.embedding_model,
                }
            )

        result.append(
            {
                "id": str(col.id),
                "name": col.name,
                "description": col.description,
                "document_count": processed_count,
                "unprocessed_count": failed_count,
                "documents": document_list,
                "is_read_only": col.is_read_only,
                "created_by_name": col.created_by_name,
                "created_by_email": col.created_by_email,
            }
        )

    return result


@router.get("/collections-with-documents")
async def list_collections_with_documents(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all collections with their documents and status counts for the authenticated user."""
    try:
        user_id = get_user_id_from_claims(current_user)
        collections = document_service.get_collections(
            user_id=user_id, filter_type="all"
        )
        result = []

        for col in collections:
            documents = document_service.get_documents(collection_id=col.id)
            processed_count = 0
            failed_count = 0
            document_list = []

            for doc in documents:
                if doc.status == "processed":
                    processed_count += 1
                elif doc.status == "failed":
                    failed_count += 1

                document_list.append(
                    {
                        "id": str(doc.id),
                        "name": doc.name,
                        "type": doc.file_type,
                        "size": doc.file_size,
                        "status": doc.status,
                        "chunk_count": doc.chunk_count,
                        "upload_date": doc.uploaded_at.isoformat()
                        if hasattr(doc.uploaded_at, "isoformat")
                        else str(doc.uploaded_at),
                        "blob_url": document_service.resolve_document_download_url(
                            storage_path=doc.storage_path,
                            file_name=doc.file_name or doc.name,
                        ),
                        "error_message": doc.error_message,
                        "embedding_tokens": doc.embedding_tokens,
                        "embedding_cost": doc.embedding_cost,
                        "embedding_model": doc.embedding_model,
                    }
                )

            result.append(
                {
                    "id": str(col.id),
                    "name": col.name,
                    "description": col.description,
                    "document_count": processed_count,
                    "unprocessed_count": failed_count,
                    "documents": document_list,
                    "is_read_only": col.is_read_only,
                    "created_by_name": col.created_by_name,
                    "created_by_email": col.created_by_email,
                }
            )

        return result
    except Exception as e:
        logger.error(f"Error listing collections with documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/external/collections-with-documents")
async def list_collections_with_documents_external(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """External alias for ingress-based direct backend access with bearer auth."""
    try:
        return _build_collections_with_documents_response(current_user)
    except Exception as e:
        logger.error(f"Error listing external collections with documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections", dependencies=[Depends(require_scope("document:*:write"))])
async def create_collection(
    collection: CollectionCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new document collection."""
    try:
        user_id = get_user_id_from_claims(current_user)
        new_collection = document_service.create_collection(
            name=collection.name,
            description=collection.description,
            user_id=user_id,
            visible_to_groups=collection.visible_to_groups,
        )

        return CollectionResponse(
            id=str(new_collection.id),
            name=new_collection.name,
            description=new_collection.description,
            user_id=new_collection.user_id,
            visible_to_groups=new_collection.visible_to_groups,
            created_by_name=new_collection.created_by_name,
            created_by_email=new_collection.created_by_email,
            is_read_only=False,
            created_at=new_collection.created_at.isoformat(),
            updated_at=new_collection.updated_at.isoformat()
            if new_collection.updated_at
            else None,
            embedding_deployment_id=new_collection.embedding_deployment_id,
        )

    except ValueError as e:
        logger.warning(
            f"Validation error creating collection '{collection.name}': {str(e)}"
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Error creating collection '{collection.name}': {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/collections/{collection_id}")
async def update_collection(
    collection_id: str,
    request: CollectionUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update collection name and/or description. Only the collection creator can update."""
    try:
        user_id = get_user_id_from_claims(current_user)
        updated = document_service.update_collection(
            collection_id=collection_id,
            user_id=user_id,
            name=request.name,
            description=request.description,
            embedding_deployment_id=request.embedding_deployment_id,
        )

        return CollectionResponse(
            id=str(updated.id),
            name=updated.name,
            description=updated.description,
            user_id=updated.user_id,
            visible_to_groups=updated.visible_to_groups,
            created_by_name=updated.created_by_name,
            created_by_email=updated.created_by_email,
            is_read_only=False,
            created_at=updated.created_at.isoformat()
            if hasattr(updated.created_at, "isoformat")
            else str(updated.created_at),
            updated_at=updated.updated_at.isoformat()
            if updated.updated_at and hasattr(updated.updated_at, "isoformat")
            else str(updated.updated_at)
            if updated.updated_at
            else None,
            embedding_deployment_id=updated.embedding_deployment_id,
        )

    except PermissionError:
        raise HTTPException(
            status_code=403, detail="Only the creator can edit this collection"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections/{collection_id}/reprocess")
async def reprocess_collection(
    collection_id: str,
    request: ReprocessRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Reprocess all documents in a collection with new chunking/embedding settings."""
    try:
        user_id = get_user_id_from_claims(current_user)
        collection = document_service.get_collection(collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        if collection.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="Only the creator can reprocess this collection"
            )

        documents = document_service.get_documents(
            user_id=user_id, collection_id=collection_id
        )
        results = []
        failed = []
        for doc in documents:
            try:
                result = await document_service.reprocess_document(
                    document_id=str(doc.id),
                    chunk_size=request.chunk_size,
                    chunk_overlap=request.chunk_overlap,
                    strategy=request.strategy,
                    embedding_deployment_id=request.embedding_deployment_id,
                )
                if result.success:
                    results.append(str(doc.id))
                else:
                    failed.append(
                        {"id": str(doc.id), "name": doc.name, "error": result.message}
                    )
            except Exception as e:
                failed.append({"id": str(doc.id), "name": doc.name, "error": str(e)})

        return {
            "success": True,
            "reprocessed": len(results),
            "failed": len(failed),
            "failures": failed,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reprocessing collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a collection and all its documents."""
    try:
        user_id = get_user_id_from_claims(current_user)

        # Verify ownership before deletion
        collection = document_service.get_collection(collection_id)
        if not collection or collection.user_id != user_id:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this collection"
            )

        # Check for references before deletion
        references = document_service.check_collection_references(collection_id)

        # Defensive check - ensure references is a dict
        if not isinstance(references, dict):
            logger.error(
                f"check_collection_references returned non-dict type: {type(references)}, value: {references}"
            )
            references = {
                "document_count": 0,
                "chunk_count": 0,
                "documents": [],
                "workflow_count": 0,
                "workflows": [],
            }

        has_references = (
            references.get("document_count", 0) > 0
            or references.get("workflow_count", 0) > 0
        )

        # Delete from database (this will cascade delete documents and chunks)
        success = document_service.delete_collection(collection_id)

        if not success:
            raise HTTPException(status_code=404, detail="Collection not found")

        response = {"message": "Collection deleted successfully"}
        if has_references:
            response["warning"] = (
                f"Collection had {references.get('document_count', 0)} documents, "
                f"{references.get('chunk_count', 0)} chunks, and was referenced by "
                f"{references.get('workflow_count', 0)} workflows"
            )
            response["references"] = references

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting collection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/collections/{collection_id}/visibility")
async def update_collection_visibility(
    collection_id: str,
    request: UpdateVisibilityRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update collection visibility groups. Only the collection creator can change visibility."""
    try:
        user_id = get_user_id_from_claims(current_user)
        updated = document_service.update_visibility(
            collection_id=collection_id,
            visible_to_groups=request.visible_to_groups,
            user_id=user_id,
        )

        return CollectionResponse(
            id=str(updated.id),
            name=updated.name,
            description=updated.description,
            user_id=updated.user_id,
            visible_to_groups=updated.visible_to_groups,
            created_by_name=updated.created_by_name,
            created_by_email=updated.created_by_email,
            is_read_only=False,
            created_at=updated.created_at.isoformat()
            if hasattr(updated.created_at, "isoformat")
            else str(updated.created_at),
            updated_at=updated.updated_at.isoformat()
            if updated.updated_at and hasattr(updated.updated_at, "isoformat")
            else str(updated.updated_at)
            if updated.updated_at
            else None,
            embedding_deployment_id=updated.embedding_deployment_id,
        )

    except PermissionError:
        raise HTTPException(
            status_code=403, detail="Only the creator can change visibility"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating collection visibility: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections/{collection_id}/references")
async def get_collection_references(
    collection_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get documents, chunks, and workflows referencing a collection."""
    try:
        user_id = get_user_id_from_claims(current_user)

        # Verify the requesting user has access to this collection before
        # exposing its references (ISG Finding 6430 - BOLA).
        if not document_service.check_collection_access(collection_id, user_id):
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this collection",
            )

        references = document_service.check_collection_references(collection_id)
        return CollectionReferencesResponse(
            document_count=references["document_count"],
            chunk_count=references["chunk_count"],
            documents=references["documents"],
            workflow_count=references["workflow_count"],
            workflows=references["workflows"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection references: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_documents(
    search_request: SearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Test document search functionality with optional hybrid search."""
    try:
        user_id = get_user_id_from_claims(current_user)

        # Verify the requesting user has access to every collection being
        # searched before running the query (ISG Finding 6430 - BOLA).
        for collection_id in search_request.collection_ids or []:
            if not document_service.check_collection_access(collection_id, user_id):
                raise HTTPException(
                    status_code=403,
                    detail=f"You do not have access to collection {collection_id}",
                )

        results = []

        # Use our custom search service
        if search_request.hybrid_enabled or search_request.search_type == "hybrid":
            # Hybrid search
            results = document_search_service.search_multiple_collections(
                collection_ids=search_request.collection_ids,
                query=search_request.query,
                k=search_request.k,
                search_type="hybrid",
                document_ids=search_request.document_ids,
                alpha=1 - search_request.keyword_weight
                if hasattr(search_request, "keyword_weight")
                else 0.5,
                include_metadata=search_request.include_metadata,
            )

        elif search_request.search_type == "similarity":
            # Vector search
            results = document_search_service.search_multiple_collections(
                collection_ids=search_request.collection_ids,
                query=search_request.query,
                k=search_request.k,
                search_type="similarity",
                document_ids=search_request.document_ids,
                include_metadata=search_request.include_metadata,
            )

        elif search_request.search_type == "text":
            # Text search
            results = document_search_service.search_multiple_collections(
                collection_ids=search_request.collection_ids,
                query=search_request.query,
                k=search_request.k,
                search_type="text",
                document_ids=search_request.document_ids,
                include_metadata=search_request.include_metadata,
            )

        else:
            # Default to vector search
            results = document_search_service.search_multiple_collections(
                collection_ids=search_request.collection_ids,
                query=search_request.query,
                k=search_request.k,
                search_type="similarity",
                document_ids=search_request.document_ids,
                include_metadata=search_request.include_metadata,
            )

        # Increment search count for each searched collection
        if search_request.collection_ids:
            _increment_search_counts(search_request.collection_ids)

        return {
            "query": search_request.query,
            "results": results,
            "total_results": len(results),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-chunks")
async def preview_chunks(request: ChunkPreviewRequest):
    """Preview how text will be chunked with given settings."""
    try:
        from ...services.text_splitting import ChunkingOptimizer, TextSplitterFactory

        # Validate parameters
        chunk_size, chunk_overlap = ChunkingOptimizer.validate_parameters(
            request.chunk_size, request.chunk_overlap
        )

        # Create splitter
        splitter = TextSplitterFactory.create_splitter(
            strategy=request.strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # Split the text
        chunks = splitter.split_text(request.text)

        # Prepare preview data
        preview_data = []
        for i, chunk in enumerate(chunks[:5]):  # Limit to first 5 chunks for preview
            preview_data.append(
                {
                    "index": i,
                    "content": chunk,
                    "length": len(chunk),
                    "start_position": request.text.find(chunk),
                    "has_overlap": i > 0 and chunk_overlap > 0,
                }
            )

        # Analyze the text for recommendations
        if request.strategy == "auto":
            analysis = ChunkingOptimizer.analyze_document(request.text)
            recommended_strategy = analysis.get("recommended_strategy", "recursive")
            recommended_size = analysis.get("recommended_chunk_size", 1000)
            recommended_overlap = analysis.get("recommended_overlap", 200)
        else:
            recommended_strategy = request.strategy
            recommended_size = chunk_size
            recommended_overlap = chunk_overlap

        return {
            "chunks": preview_data,
            "total_chunks": len(chunks),
            "avg_chunk_size": sum(len(c) for c in chunks) / len(chunks)
            if chunks
            else 0,
            "recommendations": {
                "strategy": recommended_strategy,
                "chunk_size": recommended_size,
                "chunk_overlap": recommended_overlap,
            },
        }

    except Exception as e:
        logger.error(f"Error previewing chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{collection_id}/failed-documents")
async def delete_failed_documents(
    collection_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete all failed documents in a collection."""
    try:
        user_id = get_user_id_from_claims(current_user)

        # Enforce owner-only access for failed doc deletion
        collection = document_service.get_collection(collection_id)
        if not collection or collection.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Only the collection creator can delete failed documents from this collection",
            )

        deleted_count = document_service.delete_failed_documents(collection_id)
        return {"message": f"Deleted {deleted_count} failed documents."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting failed documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
