"""Main document storage service orchestrator."""

import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import (
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
)

from ..database import get_db
from .chunking import ChunkingService
from .collections import CollectionService
from .config import (
    ALLOWED_EXTENSIONS,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    LOG_PREFIX,
)
from .embeddings import BatchEmbeddingProcessor, EmbeddingManager
from .loaders import LoaderFactory
from .models import DocumentInfo, UploadResult
from .storage import DocumentRepository


logger = logging.getLogger(__name__)


class DocumentStorageService:
    """Main service for document storage, chunking, and embedding operations."""

    def __init__(self):
        """Initialize document storage service."""
        # Initialize components
        self.repository = DocumentRepository()
        self.collection_service = CollectionService()
        self.embedding_manager = EmbeddingManager()
        self.chunking_service = ChunkingService()

        logger.info(f"{LOG_PREFIX} Document storage service initialized")

    @staticmethod
    def _is_blob_enabled() -> bool:
        """Return True when Azure Blob storage is configured."""
        return bool(
            os.getenv("AZURE_BLOB_CONNECTION_STRING")
            and os.getenv("AZURE_BLOB_CONTAINER_NAME")
        )

    @staticmethod
    def _get_blob_container_name() -> str:
        """Get Azure Blob container name from environment."""
        return os.getenv("AZURE_BLOB_CONTAINER_NAME", "").strip()

    @staticmethod
    def _build_blob_name(file_id: str, file_name: str) -> str:
        """Build a deterministic blob object name for uploaded document files."""
        file_extension = Path(file_name).suffix.lower()
        return f"documents/{file_id}{file_extension}"

    @staticmethod
    def _to_blob_ref(container: str, blob_name: str) -> str:
        """Convert container/blob to a canonical storage reference."""
        return f"azureblob://{container}/{blob_name}"

    @staticmethod
    def _parse_blob_ref(storage_path: str) -> Optional[tuple[str, str]]:
        """Parse a blob reference from storage_path.

        Supports:
        - azureblob://<container>/<blob_name>
        - https://<account>.blob.core.windows.net/<container>/<blob_name>
        """
        if not storage_path:
            return None

        if storage_path.startswith("azureblob://"):
            without_scheme = storage_path[len("azureblob://") :]
            parts = without_scheme.split("/", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]
            return None

        if storage_path.startswith("https://") and ".blob.core.windows.net/" in storage_path:
            parsed = urlparse(storage_path)
            path = parsed.path.lstrip("/")
            parts = path.split("/", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]

        return None

    @staticmethod
    def _read_connection_string_value(key: str) -> Optional[str]:
        """Read a key from AZURE_BLOB_CONNECTION_STRING."""
        conn = os.getenv("AZURE_BLOB_CONNECTION_STRING", "")
        if not conn:
            return None

        for segment in conn.split(";"):
            if "=" not in segment:
                continue
            segment_key, segment_value = segment.split("=", 1)
            if segment_key.strip().lower() == key.lower():
                return segment_value.strip()
        return None

    @staticmethod
    def _get_blob_service_client() -> Optional[BlobServiceClient]:
        """Create BlobServiceClient from environment settings."""
        connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        if not connection_string:
            logger.warning(
                "%s Azure Blob connection not established: AZURE_BLOB_CONNECTION_STRING is not set",
                LOG_PREFIX,
            )
            return None

        try:
            service_client = BlobServiceClient.from_connection_string(connection_string)
            account_name = DocumentStorageService._read_connection_string_value(
                "AccountName"
            )
            logger.info(
                "%s Azure Blob connection established (account=%s)",
                LOG_PREFIX,
                account_name or "<unknown>",
            )
            return service_client
        except Exception as connection_error:
            logger.error(
                "%s Failed to establish Azure Blob connection: %s",
                LOG_PREFIX,
                connection_error,
            )
            raise

    def _ensure_blob_container_exists(self) -> None:
        """Ensure target blob container exists before upload."""
        if not self._is_blob_enabled():
            return

        service_client = self._get_blob_service_client()
        if not service_client:
            return

        container_name = self._get_blob_container_name()
        if not container_name:
            return

        try:
            service_client.create_container(container_name)
        except ResourceExistsError:
            pass

    def _upload_to_blob(self, file_id: str, file_name: str, file_content: bytes) -> str:
        """Upload the original file bytes to Azure Blob and return storage reference."""
        logger.info(
            "%s Preparing Azure Blob upload for file_id=%s file_name=%s",
            LOG_PREFIX,
            file_id,
            file_name,
        )

        service_client = self._get_blob_service_client()
        container_name = self._get_blob_container_name()
        if not service_client or not container_name:
            logger.error(
                "%s Azure Blob storage is not configured (service_client=%s container_name=%r)",
                LOG_PREFIX,
                "available" if service_client else "unavailable",
                container_name,
            )
            raise RuntimeError("Azure Blob storage is not configured")

        logger.info(
            "%s Azure Blob connection available; container=%s",
            LOG_PREFIX,
            container_name,
        )

        self._ensure_blob_container_exists()

        blob_name = self._build_blob_name(file_id=file_id, file_name=file_name)
        blob_client = service_client.get_blob_client(container=container_name, blob=blob_name)

        sanitized_name = (file_name or f"{file_id}.bin").replace('"', "")
        content_settings = ContentSettings(
            content_type="application/octet-stream",
            content_disposition=f'attachment; filename="{sanitized_name}"',
        )
        blob_client.upload_blob(
            file_content,
            overwrite=True,
            content_settings=content_settings,
        )

        logger.info(
            "%s Successfully uploaded document to Azure Blob Storage: container=%s blob=%s file_id=%s",
            LOG_PREFIX,
            container_name,
            blob_name,
            file_id,
        )

        return self._to_blob_ref(container=container_name, blob_name=blob_name)

    def _delete_from_blob(self, storage_path: str) -> bool:
        """Delete document blob if storage_path points to Azure Blob."""
        parsed = self._parse_blob_ref(storage_path)
        if not parsed:
            return False

        container_name, blob_name = parsed
        service_client = self._get_blob_service_client()
        if not service_client:
            return False

        service_client.get_blob_client(container=container_name, blob=blob_name).delete_blob(
            delete_snapshots="include"
        )
        return True

    def find_blob_storage_path_by_document_id(
        self, document_id: str
    ) -> Optional[str]:
        """Locate an existing blob for a document_id when the DB row is missing.

        Scans the configured container for objects under ``documents/<id>`` and
        returns a canonical ``azureblob://<container>/<blob_name>`` reference if
        exactly one match is found. Returns ``None`` when Blob storage is not
        configured or no matching blob exists.

        NOTE: Callers are responsible for authorization. This method deliberately
        does no access control because the blob layout carries no owner metadata.
        """
        if not self._is_blob_enabled():
            logger.info(
                "%s find_blob probe skipped document_id=%s reason=blob_not_configured",
                LOG_PREFIX,
                document_id,
            )
            return None

        service_client = self._get_blob_service_client()
        container_name = self._get_blob_container_name()
        if not service_client or not container_name:
            logger.info(
                "%s find_blob probe skipped document_id=%s reason=no_client_or_container",
                LOG_PREFIX,
                document_id,
            )
            return None

        prefix = f"documents/{document_id}"
        try:
            container_client = service_client.get_container_client(container_name)
            matches = list(container_client.list_blobs(name_starts_with=prefix))
        except Exception as exc:  # pragma: no cover - network/service errors
            logger.warning(
                "%s find_blob probe failed document_id=%s container=%s prefix=%s error=%s",
                LOG_PREFIX,
                document_id,
                container_name,
                prefix,
                exc,
            )
            return None

        logger.info(
            "%s find_blob probe document_id=%s container=%s prefix=%s match_count=%d "
            "match_names=%s",
            LOG_PREFIX,
            document_id,
            container_name,
            prefix,
            len(matches),
            [b.name for b in matches[:5]],
        )

        if not matches:
            return None

        # Prefer exact-id match (documents/<id>.<ext>) over anything with the id
        # as a substring (defense against prefix collisions).
        exact = [
            b for b in matches
            if Path(b.name).stem == document_id
        ]
        chosen = exact[0] if exact else matches[0]
        logger.info(
            "%s find_blob chosen document_id=%s blob_name=%s exact_match=%s",
            LOG_PREFIX,
            document_id,
            chosen.name,
            bool(exact),
        )
        return self._to_blob_ref(container=container_name, blob_name=chosen.name)

    def resolve_document_download_url(
        self, storage_path: Optional[str], file_name: Optional[str] = None
    ) -> Optional[str]:
        """Resolve a direct downloadable URL for a document storage path.

        Returns a short-lived SAS URL for Azure Blob-backed documents.
        Returns None for local filesystem-backed documents.
        """
        if not storage_path:
            return None

        parsed = self._parse_blob_ref(storage_path)
        if not parsed:
            return None

        container_name, blob_name = parsed
        service_client = self._get_blob_service_client()
        if not service_client:
            return None

        blob_client = service_client.get_blob_client(container=container_name, blob=blob_name)

        # If account key is available, issue short-lived SAS URLs.
        account_name = self._read_connection_string_value("AccountName")
        account_key = self._read_connection_string_value("AccountKey")
        if account_name and account_key:
            ttl_minutes = int(os.getenv("AZURE_BLOB_SAS_TTL_MINUTES", "60"))
            download_name = (file_name or Path(blob_name).name).replace('"', "")
            sas_token = generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
                content_disposition=(
                    f'attachment; filename="{download_name}"'
                ),
                content_type="application/octet-stream",
            )
            return f"{blob_client.url}?{sas_token}"

        # Fallback to plain blob URL when SAS cannot be produced.
        logger.warning(
            "%s Falling back to plain blob URL because AccountKey is unavailable",
            LOG_PREFIX,
        )
        return blob_client.url

    def build_file_url(
        self,
        document_id: str,
        storage_path: Optional[str],
        file_name: Optional[str] = None,
    ) -> str:
        """Build the best file URL for API responses.

        Prefers direct blob URL when available, otherwise falls back to API download route.
        """
        direct_url = self.resolve_document_download_url(
            storage_path=storage_path,
            file_name=file_name,
        )
        if direct_url:
            logger.debug(
                "%s File URL mode=blob document_id=%s",
                LOG_PREFIX,
                document_id,
            )
            return direct_url

        logger.debug(
            "%s File URL mode=fallback document_id=%s",
            LOG_PREFIX,
            document_id,
        )
        return f"/api/documents/{document_id}/download"

    @staticmethod
    def _get_storage_root() -> Path:
        """Get root directory for persisted document files."""
        root = Path(os.getenv("DOCUMENT_STORAGE_ROOT", "workspace/documents"))
        root.mkdir(parents=True, exist_ok=True)
        return root.resolve()

    def _persist_uploaded_file(
        self, file_id: str, file_name: str, file_content: bytes
    ) -> str:
        """Persist an uploaded file and return a storage reference string."""
        if self._is_blob_enabled():
            blob_ref = self._upload_to_blob(
                file_id=file_id,
                file_name=file_name,
                file_content=file_content,
            )
            return blob_ref

        file_extension = Path(file_name).suffix.lower()
        stored_name = f"{file_id}{file_extension}"
        target_path = self._get_storage_root() / stored_name
        target_path.write_bytes(file_content)
        return str(target_path)

    @staticmethod
    def allowed_file(filename: str) -> bool:
        """Check if file extension is allowed.

        Args:
            filename: Filename to check

        Returns:
            True if extension is allowed
        """
        return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

    def get_embeddings(self, embedding_deployment_id: Optional[str] = None):
        """Get embeddings instance.

        Args:
            embedding_deployment_id: Optional embedding deployment ID

        Returns:
            Embeddings instance
        """
        return self.embedding_manager.get_embeddings(embedding_deployment_id)

    async def upload_document(
        self,
        file_name: str,
        file_content: bytes,
        collection_id: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        loader_mode: str = "single",
        strategy: str = "recursive",
        embedding_deployment_id: Optional[str] = None,
    ) -> UploadResult:
        """Upload and process a document.

        Args:
            file_name: Original filename
            file_content: File content as bytes
            collection_id: Collection ID to add document to
            chunk_size: Chunk size for text splitting
            chunk_overlap: Overlap between chunks
            loader_mode: Loader mode (legacy parameter)
            strategy: Chunking strategy
            embedding_deployment_id: Optional embedding deployment ID

        Returns:
            UploadResult with document info and chunks
        """
        try:
            # Generate unique document ID
            file_id = str(uuid.uuid4())
            file_extension = Path(file_name).suffix

            # Persist the original file for later download/retrieval.
            stored_file_path = self._persist_uploaded_file(
                file_id=file_id,
                file_name=file_name,
                file_content=file_content,
            )

            # Create database entry with persisted storage path.
            self.repository.create_document(
                file_id=file_id,
                collection_id=collection_id,
                file_name=file_name,
                file_type=file_extension[1:].upper() if file_extension else "",
                file_size=len(file_content),
                storage_path=stored_file_path,
            )

            # Write to temp file for processing (auto-cleanup)
            with tempfile.NamedTemporaryFile(
                suffix=file_extension, delete=False
            ) as tmp_file:
                tmp_file.write(file_content)
                tmp_file.flush()
                tmp_path = tmp_file.name

            try:
                # Process document from temp file
                chunks, metadata = self.process_document(
                    file_path=tmp_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    strategy=strategy,
                )

                # Get embeddings instance
                embeddings = self.embedding_manager.get_embeddings(
                    embedding_deployment_id
                )

                # Generate embeddings in batches
                embedding_results = None
                if embeddings and len(chunks) > 0:
                    texts = [c.page_content for c in chunks]
                    model_name = getattr(embeddings, "model", None) or getattr(
                        embeddings, "azure_deployment", "text-embedding-3-small"
                    )
                    batch_processor = BatchEmbeddingProcessor(
                        embeddings, model_name=model_name
                    )
                    embedding_results = batch_processor.process_batch(texts)

                    logger.info(
                        f"{LOG_PREFIX} Embedding complete: "
                        f"{embedding_results.successful}/{embedding_results.total} successful, "
                        f"{embedding_results.token_count} tokens, "
                        f"cost=${embedding_results.embedding_cost['cost']:.6f}"
                        if embedding_results.embedding_cost
                        else f"{LOG_PREFIX} Embedding complete: "
                        f"{embedding_results.successful}/{embedding_results.total} successful"
                    )

                # Extract full text
                full_text = "\n\n".join(chunk.page_content for chunk in chunks)

                # Prepare chunks for storage
                chunk_data = []
                for i, chunk in enumerate(chunks):
                    embedding = None
                    if embedding_results and i < len(embedding_results.embeddings):
                        embedding = embedding_results.embeddings[i]

                    # Add standard metadata
                    chunk.metadata.update(
                        {
                            "document_id": file_id,
                            "collection_id": collection_id,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "source": os.path.basename(file_name),
                            "file_type": Path(file_name).suffix.lower(),
                        }
                    )

                    chunk_data.append((chunk.page_content, embedding, chunk.metadata))

                # Resolve embedding metadata for persistence
                doc_embedding_tokens = (
                    embedding_results.token_count if embedding_results else 0
                )
                doc_embedding_cost = (
                    embedding_results.embedding_cost.get("cost")
                    if embedding_results and embedding_results.embedding_cost
                    else None
                )
                doc_embedding_model = (
                    embedding_results.embedding_cost.get("model")
                    if embedding_results and embedding_results.embedding_cost
                    else None
                )

                # Store chunks in database
                with get_db() as db:
                    stored_chunks = self.repository.store_chunks(
                        document_id=file_id, chunks=chunk_data, db_session=db
                    )

                    # Update document status with embedding cost data
                    self.repository.update_document_status(
                        document_id=file_id,
                        status="processed",
                        full_text=full_text,
                        embedding_tokens=doc_embedding_tokens,
                        embedding_cost=doc_embedding_cost,
                        embedding_model=doc_embedding_model,
                    )

                # Get updated document info
                doc_info = self.repository.get_document(file_id)

                logger.info(
                    f"{LOG_PREFIX} Successfully uploaded and processed document: {file_name}"
                )

                return UploadResult(
                    document=doc_info,
                    chunks=stored_chunks,
                    success=True,
                    message="Document uploaded and processed successfully",
                    embedding_tokens=doc_embedding_tokens,
                    embedding_cost=doc_embedding_cost,
                )

            except Exception as e:
                # Update status on error
                self.repository.update_document_status(
                    document_id=file_id, status="failed", error_message=str(e)
                )

                logger.error(f"{LOG_PREFIX} Error processing document {file_name}: {e}")

                # Return failed result with document info
                doc_info = self.repository.get_document(file_id)

                return UploadResult(
                    document=doc_info,
                    chunks=[],
                    success=False,
                    message=f"Processing failed: {str(e)}",
                )

            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Error uploading document: {e}")
            raise

    def process_document(
        self,
        file_path: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        strategy: str = "recursive",
    ) -> tuple:
        """Process document and split into chunks.

        Args:
            file_path: Path to document file
            chunk_size: Chunk size for text splitting
            chunk_overlap: Overlap between chunks
            strategy: Chunking strategy

        Returns:
            Tuple of (chunks, metadata)
        """
        try:
            # Load document
            loader = LoaderFactory.get_loader(file_path)
            documents = loader.load(file_path)

            logger.info(
                f"{LOG_PREFIX} Loaded {len(documents)} pages/sections from document"
            )

            # Chunk documents
            chunks, metadata = self.chunking_service.chunk_documents(
                documents=documents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                strategy=strategy,
            )

            logger.info(f"{LOG_PREFIX} Created {len(chunks)} chunks from document")

            return chunks, metadata

        except Exception as e:
            logger.error(f"{LOG_PREFIX} Error processing document {file_path}: {e}")
            raise

    def get_documents(
        self,
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
        return self.repository.get_documents(
            collection_id=collection_id,
            status=status,
            user_id=user_id,
            user_groups=user_groups,
            filter_type=filter_type,
        )

    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the database.

        Args:
            document_id: Document ID

        Returns:
            True if deleted successfully
        """
        try:
            doc_info = self.repository.get_document(document_id)
            if not doc_info:
                return False

            if doc_info.storage_path:
                try:
                    if not self._delete_from_blob(doc_info.storage_path):
                        Path(doc_info.storage_path).unlink(missing_ok=True)
                except Exception as file_error:
                    logger.warning(
                        f"{LOG_PREFIX} Could not remove stored file for document {document_id}: {file_error}"
                    )

            return self.repository.delete_document(document_id)
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Error deleting document {document_id}: {e}")
            return False

    # Collection operations (delegate to collection service)
    def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
        visible_to_groups: Optional[List[str]] = None,
    ):
        """Create a new document collection."""
        return self.collection_service.create_collection(
            name, description, user_id, visible_to_groups
        )

    def get_collections(self, user_id: str, filter_type: str = "owned"):
        """Get all document collections."""
        return self.collection_service.get_collections(user_id, filter_type)

    def get_collection(self, collection_id: str):
        """Get a specific collection by ID."""
        return self.collection_service.get_collection(collection_id)

    def update_collection(
        self,
        collection_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        embedding_deployment_id: Optional[str] = None,
    ):
        """Update collection name, description, and/or embedding model."""
        return self.collection_service.update_collection(
            collection_id,
            user_id,
            name=name,
            description=description,
            embedding_deployment_id=embedding_deployment_id,
        )

    def update_visibility(
        self, collection_id: str, visible_to_groups: List[str], user_id: str
    ):
        """Update collection visibility groups."""
        return self.collection_service.update_visibility(
            collection_id, visible_to_groups, user_id
        )

    def check_collection_access(self, collection_id: str, user_id: str) -> bool:
        """Check if a user has access to a collection."""
        return self.collection_service.check_collection_access(collection_id, user_id)

    def check_collection_references(self, collection_id: str):
        """Check documents, chunks, and workflows referencing a collection."""
        return self.collection_service.check_collection_references(collection_id)

    def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection and all its documents."""
        return self.collection_service.delete_collection(collection_id)

    def delete_failed_documents(self, collection_id: str) -> int:
        """Delete all failed documents in a collection."""
        return self.repository.delete_failed_documents(collection_id)

    async def reprocess_document(
        self,
        document_id: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        strategy: str = "recursive",
        embedding_deployment_id: Optional[str] = None,
    ) -> UploadResult:
        """Reprocess an existing document with new chunking settings.

        This allows users to re-chunk a document with different parameters
        (chunk size, overlap, strategy) without re-uploading the file.

        Args:
            document_id: Document ID to reprocess
            chunk_size: New chunk size for text splitting
            chunk_overlap: New overlap between chunks
            strategy: New chunking strategy
            embedding_deployment_id: Optional embedding deployment ID

        Returns:
            UploadResult with updated document info and new chunks
        """
        from langchain_core.documents import Document as LCDocument
        from ...models import Document as DocumentModel

        try:
            # Get document info
            doc_info = self.repository.get_document(document_id)
            if not doc_info:
                raise ValueError(f"Document not found: {document_id}")

            # Update status to processing
            self.repository.update_document_status(
                document_id=document_id, status="processing"
            )

            # Get full text content from database
            with get_db() as db:
                doc = (
                    db.query(DocumentModel)
                    .filter(DocumentModel.id == document_id)
                    .first()
                )
                full_text = doc.full_text_content if doc else None

            if not full_text:
                raise ValueError(
                    "Document has no stored content to reprocess. "
                    "The document may have been uploaded before full text storage was enabled."
                )

            # Delete existing chunks
            deleted_count = self.repository.delete_chunks(document_id)
            logger.info(
                f"{LOG_PREFIX} Deleted {deleted_count} existing chunks for reprocessing"
            )

            # Create a document for chunking
            # For reprocessing, we treat the full text as a single document
            documents = [LCDocument(page_content=full_text, metadata={"page": 0})]

            # Re-chunk with new settings
            chunks, metadata = self.chunking_service.chunk_documents(
                documents=documents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                strategy=strategy,
            )

            logger.info(
                f"{LOG_PREFIX} Reprocessing created {len(chunks)} chunks "
                f"with strategy={strategy}, size={chunk_size}, overlap={chunk_overlap}"
            )

            # Get embeddings instance
            embeddings = self.embedding_manager.get_embeddings(embedding_deployment_id)

            # Generate embeddings in batches
            embedding_results = None
            if embeddings and len(chunks) > 0:
                texts = [c.page_content for c in chunks]
                model_name = getattr(embeddings, "model", None) or getattr(
                    embeddings, "azure_deployment", "text-embedding-3-small"
                )
                batch_processor = BatchEmbeddingProcessor(
                    embeddings, model_name=model_name
                )
                embedding_results = batch_processor.process_batch(texts)

                logger.info(
                    f"{LOG_PREFIX} Embedding complete: "
                    f"{embedding_results.successful}/{embedding_results.total} successful"
                )

            # Prepare chunks for storage
            chunk_data = []
            for i, chunk in enumerate(chunks):
                embedding = None
                if embedding_results and i < len(embedding_results.embeddings):
                    embedding = embedding_results.embeddings[i]

                # Add standard metadata
                chunk.metadata.update(
                    {
                        "document_id": document_id,
                        "collection_id": doc_info.collection_id,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "source": doc_info.file_name,
                        "file_type": doc_info.file_type.lower(),
                        "reprocessed": True,
                        "chunking_strategy": strategy,
                    }
                )

                chunk_data.append((chunk.page_content, embedding, chunk.metadata))

            # Resolve embedding metadata for persistence
            reproc_embedding_tokens = (
                embedding_results.token_count if embedding_results else 0
            )
            reproc_embedding_cost = (
                embedding_results.embedding_cost.get("cost")
                if embedding_results and embedding_results.embedding_cost
                else None
            )
            reproc_embedding_model = (
                embedding_results.embedding_cost.get("model")
                if embedding_results and embedding_results.embedding_cost
                else None
            )

            # Store chunks in database
            with get_db() as db:
                stored_chunks = self.repository.store_chunks(
                    document_id=document_id, chunks=chunk_data, db_session=db
                )

                # Update document status with embedding cost data
                self.repository.update_document_status(
                    document_id=document_id,
                    status="processed",
                    embedding_tokens=reproc_embedding_tokens,
                    embedding_cost=reproc_embedding_cost,
                    embedding_model=reproc_embedding_model,
                )

            # Get updated document info
            updated_doc_info = self.repository.get_document(document_id)

            logger.info(
                f"{LOG_PREFIX} Successfully reprocessed document: {doc_info.file_name}"
            )

            return UploadResult(
                document=updated_doc_info,
                chunks=stored_chunks,
                success=True,
                message=f"Document reprocessed successfully with {len(chunks)} chunks",
                embedding_tokens=reproc_embedding_tokens,
                embedding_cost=reproc_embedding_cost,
            )

        except Exception as e:
            # Update status on error
            self.repository.update_document_status(
                document_id=document_id, status="failed", error_message=str(e)
            )

            logger.error(f"{LOG_PREFIX} Error reprocessing document {document_id}: {e}")

            # Get document info for response
            doc_info = self.repository.get_document(document_id)

            return UploadResult(
                document=doc_info,
                chunks=[],
                success=False,
                message=f"Reprocessing failed: {str(e)}",
            )
