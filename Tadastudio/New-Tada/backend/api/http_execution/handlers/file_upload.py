"""File upload handler for HTTP execution API.

This module handles file uploads for HTTP-triggered executions,
processing files for use by FILE_READ nodes in workflows.
"""

import base64
import os
from typing import Any, Dict

from fastapi import UploadFile
from backend.services.config import get_logger

from ..exceptions import FileProcessingException, InvalidInputException
from ..models import FileUploadData
from ..utils.constants import ALLOWED_FILE_EXTENSIONS, MAX_FILE_SIZE


logger = get_logger(__name__)


class FileUploadHandler:
    """Handler for processing uploaded files in HTTP execution requests.

    This handler validates and processes uploaded files, converting them to
    a format suitable for FILE_READ nodes in workflows.
    """

    @staticmethod
    async def process_uploaded_file(file: UploadFile) -> FileUploadData:
        """Process an uploaded file and return it in a format suitable for FILE_READ nodes.

        This function:
        1. Validates the file (size, extension)
        2. Reads the file content
        3. Encodes to base64 for safe transport
        4. Returns structured file data

        Args:
            file: FastAPI UploadFile object

        Returns:
            FileUploadData dictionary with base64, extension, name, type, and size

        Raises:
            FileProcessingException: If file processing fails
            InvalidInputException: If file validation fails

        Example:
            >>> from fastapi import UploadFile
            >>> file = UploadFile(...)
            >>> file_data = await FileUploadHandler.process_uploaded_file(file)
            >>> print(f"Processed {file_data['name']}: {file_data['size']} bytes")
        """
        filename = file.filename or "unknown"
        logger.info(f"[FILE-UPLOAD] Processing uploaded file: {filename}")

        try:
            # Validate filename
            if not file.filename:
                logger.warning("[FILE-UPLOAD] Upload has no filename")
                raise InvalidInputException("Uploaded file must have a filename")

            # Get and validate file extension
            file_extension = os.path.splitext(file.filename)[1].lower()
            if not file_extension:
                file_extension = ".tmp"
                logger.debug("[FILE-UPLOAD] No extension found, using .tmp")

            # Validate extension (optional - can be disabled)
            if (
                ALLOWED_FILE_EXTENSIONS
                and file_extension not in ALLOWED_FILE_EXTENSIONS
            ):
                logger.warning(
                    f"[FILE-UPLOAD] Unsupported file extension: {file_extension}"
                )
                # Log warning but allow - some workflows may need any file type
                logger.info(
                    f"[FILE-UPLOAD] Allowing unsupported extension {file_extension}"
                )

            # Read file content
            logger.debug(f"[FILE-UPLOAD] Reading file content for {filename}")
            content = await file.read()
            content_size = len(content)

            logger.debug(f"[FILE-UPLOAD] Read {content_size} bytes from {filename}")

            # Validate file size
            if content_size > MAX_FILE_SIZE:
                logger.error(
                    f"[FILE-UPLOAD] File {filename} exceeds size limit: "
                    f"{content_size} > {MAX_FILE_SIZE}"
                )
                raise InvalidInputException(
                    f"File size ({content_size} bytes) exceeds maximum allowed "
                    f"size ({MAX_FILE_SIZE} bytes)"
                )

            if content_size == 0:
                logger.warning(f"[FILE-UPLOAD] File {filename} is empty")
                raise InvalidInputException("Uploaded file is empty")

            # Encode to base64 for safe transport
            logger.debug(f"[FILE-UPLOAD] Encoding {filename} to base64")
            file_base64 = base64.b64encode(content).decode("utf-8")

            # Get MIME type
            content_type = file.content_type or "application/octet-stream"
            logger.debug(f"[FILE-UPLOAD] Content type: {content_type}")

            # Prepare file data in the format expected by FILE_READ node
            file_data: FileUploadData = {
                "base64": file_base64,
                "extension": file_extension,
                "name": file.filename,
                "type": content_type,
                "size": content_size,
            }

            logger.info(
                f"[FILE-UPLOAD] Successfully processed {filename} "
                f"({content_size} bytes, {file_extension})"
            )

            return file_data

        except InvalidInputException:
            # Re-raise validation exceptions
            raise

        except Exception as e:
            logger.error(f"[FILE-UPLOAD] Error processing file {filename}: {e}")
            raise FileProcessingException(filename, str(e))

    @staticmethod
    def validate_file_input(message: Any, file_data: Any) -> None:
        """Validate that either message or file is provided, but not both.

        Args:
            message: Text message input
            file_data: File data input

        Raises:
            InvalidInputException: If validation fails

        Example:
            >>> FileUploadHandler.validate_file_input("Hello", None)  # OK
            >>> FileUploadHandler.validate_file_input(None, {...})     # OK
            >>> FileUploadHandler.validate_file_input("Hello", {...})  # Raises exception
        """
        if not message and not file_data:
            logger.warning("[FILE-UPLOAD] Neither message nor file provided")
            raise InvalidInputException("Either message or file must be provided")

        if message and file_data:
            logger.warning("[FILE-UPLOAD] Both message and file provided")
            raise InvalidInputException("Provide either message or file, not both")

        logger.debug(
            f"[FILE-UPLOAD] Input validation passed "
            f"(message: {bool(message)}, file: {bool(file_data)})"
        )

    @staticmethod
    def prepare_execution_input(message: Any, file_data: Any) -> Dict[str, Any]:
        """Prepare input data for workflow execution.

        Combines message and file data into the format expected by the execution engine.

        Args:
            message: Optional text message
            file_data: Optional file data

        Returns:
            Dictionary with 'message' and/or 'file_info' keys

        Example:
            >>> input_data = FileUploadHandler.prepare_execution_input("Hello", None)
            >>> print(input_data)  # {"message": "Hello"}
            >>>
            >>> input_data = FileUploadHandler.prepare_execution_input(None, {...})
            >>> print(input_data)  # {"file_info": {...}}
        """
        input_data: Dict[str, Any] = {}

        if message:
            input_data["message"] = message
            logger.debug("[FILE-UPLOAD] Added message to execution input")

        if file_data:
            # Use file_info key for FILE_READ node compatibility
            input_data["file_info"] = file_data
            logger.debug(
                f"[FILE-UPLOAD] Added file_info to execution input: "
                f"{file_data.get('name', 'unknown')}"
            )

        return input_data


# Singleton instance
file_upload_handler = FileUploadHandler()


def get_file_upload_handler() -> FileUploadHandler:
    """Get the file upload handler instance.

    Returns:
        FileUploadHandler instance

    Example:
        >>> from backend.api.http_execution.handlers.file_upload import get_file_upload_handler
        >>> handler = get_file_upload_handler()
        >>> file_data = await handler.process_uploaded_file(uploaded_file)
    """
    return file_upload_handler
