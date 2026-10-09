"""Custom exceptions for document processing services."""


class DocumentException(Exception):
    """Base exception for all document processing errors."""

    pass


class DocumentConfigError(DocumentException):
    """Raised when document processing configuration is invalid."""

    pass


class DocumentProcessingError(DocumentException):
    """Raised when document processing fails."""

    def __init__(self, message: str, file_path: str = None, processor: str = None):
        """
        Initialize document processing error.

        Args:
            message: Error message
            file_path: Path to file that failed processing
            processor: Name of processor that failed
        """
        self.file_path = file_path
        self.processor = processor
        super().__init__(message)


class UnsupportedFileTypeError(DocumentException):
    """Raised when attempting to process an unsupported file type."""

    def __init__(self, file_type: str, supported_types: list = None):
        """
        Initialize unsupported file type error.

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


class ProcessorNotAvailableError(DocumentException):
    """Raised when a required processor is not available."""

    def __init__(self, processor_name: str, reason: str = None):
        """
        Initialize processor not available error.

        Args:
            processor_name: Name of the unavailable processor
            reason: Optional reason for unavailability
        """
        self.processor_name = processor_name
        self.reason = reason
        message = f"Processor not available: {processor_name}"
        if reason:
            message += f". Reason: {reason}"
        super().__init__(message)


class CacheError(DocumentException):
    """Raised when cache operations fail."""

    pass
