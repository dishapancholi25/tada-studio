"""Custom exceptions for OCR services."""


class OCRException(Exception):
    """Base exception for all OCR-related errors."""

    pass


class OCRConfigError(OCRException):
    """Raised when OCR configuration is invalid or missing."""

    pass


class OCRProcessingError(OCRException):
    """Raised when OCR processing fails."""

    def __init__(self, message: str, file_path: str = None, page_num: int = None):
        """
        Initialize OCR processing error.

        Args:
            message: Error message
            file_path: Path to file that failed processing
            page_num: Page number that failed (for multi-page documents)
        """
        self.file_path = file_path
        self.page_num = page_num
        super().__init__(message)


class UnsupportedFileTypeError(OCRException):
    """Raised when attempting to process an unsupported file type."""

    def __init__(self, file_ext: str, supported_types: list = None):
        """
        Initialize unsupported file type error.

        Args:
            file_ext: The unsupported file extension
            supported_types: List of supported file extensions
        """
        self.file_ext = file_ext
        self.supported_types = supported_types or []
        message = f"Unsupported file type: {file_ext}"
        if supported_types:
            message += f". Supported types: {', '.join(supported_types)}"
        super().__init__(message)


class FileSizeExceededError(OCRException):
    """Raised when file size exceeds maximum allowed size."""

    def __init__(self, file_size_mb: float, max_size_mb: float):
        """
        Initialize file size exceeded error.

        Args:
            file_size_mb: Actual file size in MB
            max_size_mb: Maximum allowed file size in MB
        """
        self.file_size_mb = file_size_mb
        self.max_size_mb = max_size_mb
        message = (
            f"File size ({file_size_mb:.2f} MB) exceeds maximum "
            f"allowed size ({max_size_mb} MB)"
        )
        super().__init__(message)


class FileNotFoundError(OCRException):
    """Raised when a file cannot be found."""

    def __init__(self, file_path: str):
        """
        Initialize file not found error.

        Args:
            file_path: Path to the missing file
        """
        self.file_path = file_path
        super().__init__(f"File not found: {file_path}")


class InvalidInputError(OCRException):
    """Raised when input parameters are invalid."""

    pass
