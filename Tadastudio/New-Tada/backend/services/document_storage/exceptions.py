"""Custom exceptions for document storage service."""


class DocumentStorageError(Exception):
    """Base exception for document storage errors."""

    pass


class UnsupportedFileTypeError(DocumentStorageError):
    """Raised when file type is not supported."""

    def __init__(self, file_type: str, supported_types: list = None):
        """Initialize exception.

        Args:
            file_type: The unsupported file type
            supported_types: List of supported file types
        """
        self.file_type = file_type
        self.supported_types = supported_types or []
        message = f"Unsupported file type: {file_type}"
        if supported_types:
            message += f". Supported types: {', '.join(supported_types)}"
        super().__init__(message)


class LoaderNotAvailableError(DocumentStorageError):
    """Raised when required loader is not available."""

    def __init__(self, loader_name: str, install_instruction: str = None):
        """Initialize exception.

        Args:
            loader_name: Name of the loader
            install_instruction: How to install missing dependencies
        """
        self.loader_name = loader_name
        message = f"Loader '{loader_name}' is not available"
        if install_instruction:
            message += f". Install with: {install_instruction}"
        super().__init__(message)


class ChunkingError(DocumentStorageError):
    """Raised when document chunking fails."""

    pass


class EmbeddingError(DocumentStorageError):
    """Raised when embedding generation fails."""

    pass


class FileStorageError(DocumentStorageError):
    """Raised when file storage operations fail."""

    pass


class CollectionNotFoundError(DocumentStorageError):
    """Raised when collection is not found."""

    def __init__(self, collection_id: str):
        """Initialize exception.

        Args:
            collection_id: The collection ID that was not found
        """
        self.collection_id = collection_id
        super().__init__(f"Collection not found: {collection_id}")


class DocumentNotFoundError(DocumentStorageError):
    """Raised when document is not found."""

    def __init__(self, document_id: str):
        """Initialize exception.

        Args:
            document_id: The document ID that was not found
        """
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")
