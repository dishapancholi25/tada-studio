"""Document storage service with RAG support."""

from .chunking import ChunkingService, PageBoundaryTracker
from .collections import CollectionRepository, CollectionService
from .config import (
    ALLOWED_EXTENSIONS,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    EMBEDDING_BATCH_SIZE,
    LOG_PREFIX,
)
from .embeddings import BatchEmbeddingProcessor, EmbeddingManager
from .exceptions import (
    ChunkingError,
    CollectionNotFoundError,
    DocumentNotFoundError,
    DocumentStorageError,
    EmbeddingError,
    FileStorageError,
    LoaderNotAvailableError,
    UnsupportedFileTypeError,
)
from .loaders import (
    BaseLoader,
    CSVLoader,
    DOCXLoader,
    ExcelLoader,
    LoaderFactory,
    PDFLoader,
    TextLoader,
)
from .models import (
    BatchEmbeddingResult,
    ChunkInfo,
    ChunkMetadata,
    CollectionInfo,
    DocumentInfo,
    ProcessingMetadata,
    SearchResult,
    UploadResult,
)
from .search_service import (
    DocumentSearchService,
    document_search_service,
    get_document_search_service,
)
from .service import DocumentStorageService
from .storage import DocumentRepository


__all__ = [
    # Main service
    "DocumentStorageService",
    "DocumentSearchService",
    "document_search_service",
    "get_document_search_service",
    # Models
    "DocumentInfo",
    "ChunkInfo",
    "ChunkMetadata",
    "CollectionInfo",
    "UploadResult",
    "ProcessingMetadata",
    "SearchResult",
    "BatchEmbeddingResult",
    # Exceptions
    "DocumentStorageError",
    "UnsupportedFileTypeError",
    "LoaderNotAvailableError",
    "ChunkingError",
    "EmbeddingError",
    "FileStorageError",
    "CollectionNotFoundError",
    "DocumentNotFoundError",
    # Loaders
    "LoaderFactory",
    "BaseLoader",
    "PDFLoader",
    "DOCXLoader",
    "TextLoader",
    "CSVLoader",
    "ExcelLoader",
    # Chunking
    "ChunkingService",
    "PageBoundaryTracker",
    # Embeddings
    "EmbeddingManager",
    "BatchEmbeddingProcessor",
    # Storage
    "DocumentRepository",
    # Collections
    "CollectionService",
    "CollectionRepository",
    # Config
    "ALLOWED_EXTENSIONS",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "EMBEDDING_BATCH_SIZE",
    "LOG_PREFIX",
]


def create_document_storage_service() -> DocumentStorageService:
    """Create and configure document storage service.

    Returns:
        Configured DocumentStorageService instance
    """
    return DocumentStorageService()
