"""File processing service for Graph API.

This module provides file upload validation and processing services.
"""

import base64
import json
import os
import secrets
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import IO, Any

try:
    import fcntl  # POSIX-only; enables cross-process registry locking.
except ImportError:  # Windows (local dev): fall back to the in-process lock.
    fcntl = None

from backend.services.config import get_logger

from ..constants import (
    ALLOWED_FILE_EXTENSIONS,
    LOG_PREFIX,
    MAX_FILE_SIZE_BYTES,
    MAX_FILE_SIZE_MB,
)
from ..exceptions import FileUploadError

logger = get_logger(__name__)

UPLOAD_DIR = Path("./workspace/uploads").resolve()
OWNERSHIP_REGISTRY_PATH = UPLOAD_DIR / ".upload_owners.json"
_ownership_lock = threading.Lock()


@contextmanager
def _locked_registry_file(registry_file: IO[str], exclusive: bool) -> Iterator[None]:
    """Hold a real flock on Unix; a no-op on Windows (in-process lock still applies)."""
    if fcntl is None:
        yield
        return
    fcntl.flock(registry_file.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
    try:
        yield
    finally:
        fcntl.flock(registry_file.fileno(), fcntl.LOCK_UN)


def _registry_key(file_path: str) -> str:
    """Return a stable key for ownership checks."""
    return os.path.realpath(file_path)


def _preserve_corrupt_registry(exc: json.JSONDecodeError) -> None:
    """Move a corrupt registry aside so ownership loss is visible and inspectable."""
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    corrupt_path = OWNERSHIP_REGISTRY_PATH.with_suffix(
        f"{OWNERSHIP_REGISTRY_PATH.suffix}.corrupt-{timestamp}"
    )
    try:
        os.rename(OWNERSHIP_REGISTRY_PATH, corrupt_path)
        logger.error(
            f"{LOG_PREFIX} Upload ownership registry is corrupt; moved to {corrupt_path}: {exc}"
        )
    except OSError as rename_exc:
        logger.error(
            f"{LOG_PREFIX} Upload ownership registry is corrupt and could not be preserved: "
            f"{exc}; preserve error: {rename_exc}"
        )


def _load_ownership_registry_from_file(registry_file: Any) -> dict[str, dict[str, Any]]:
    """Load the upload ownership registry from an already locked file."""
    registry_file.seek(0)
    try:
        raw_data = registry_file.read()
    except OSError as exc:
        logger.warning(f"{LOG_PREFIX} Could not read upload ownership registry: {exc}")
        return {}

    if not raw_data.strip():
        return {}

    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError as exc:
        _preserve_corrupt_registry(exc)
        return {}

    return data if isinstance(data, dict) else {}


def _load_ownership_registry() -> dict[str, dict[str, Any]]:
    """Load the upload ownership registry.

    A small JSON sidecar keeps this endpoint self-contained and avoids adding a
    schema migration for temporary graph uploads.
    """
    if not OWNERSHIP_REGISTRY_PATH.exists():
        return {}
    try:
        with (
            OWNERSHIP_REGISTRY_PATH.open("r", encoding="utf-8") as registry_file,
            _locked_registry_file(registry_file, exclusive=False),
        ):
            return _load_ownership_registry_from_file(registry_file)
    except OSError as exc:
        logger.warning(f"{LOG_PREFIX} Could not read upload ownership registry: {exc}")
        return {}


def _save_ownership_registry(registry: dict[str, dict[str, Any]]) -> None:
    """Persist the upload ownership registry with an atomic replace."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = OWNERSHIP_REGISTRY_PATH.with_suffix(".json.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as registry_file:
            json.dump(registry, registry_file, indent=2, sort_keys=True)
            registry_file.flush()
            os.fsync(registry_file.fileno())
        os.replace(tmp_path, OWNERSHIP_REGISTRY_PATH)

        try:
            dir_fd = os.open(UPLOAD_DIR, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError as exc:
            logger.warning(
                f"{LOG_PREFIX} Could not fsync upload ownership registry directory: {exc}"
            )
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError as cleanup_exc:
            logger.warning(
                f"{LOG_PREFIX} Could not remove temporary ownership registry file: {cleanup_exc}"
            )
        raise


def _save_ownership_registry_locked(registry: dict[str, dict[str, Any]]) -> None:
    """Persist the registry atomically while caller holds an exclusive file lock."""
    _save_ownership_registry(registry)


def _record_file_owner_locked(
    file_path: str, owner_identifier: str, filename: str
) -> None:
    """Read-modify-write the ownership registry under the registry file lock."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with (
        OWNERSHIP_REGISTRY_PATH.open("a+", encoding="utf-8") as registry_file,
        _locked_registry_file(registry_file, exclusive=True),
    ):
        registry = _load_ownership_registry_from_file(registry_file)
        registry[_registry_key(file_path)] = {
            "owner": owner_identifier,
            "filename": filename,
        }
        _save_ownership_registry_locked(registry)


def record_file_owner(file_path: str, owner_identifier: str, filename: str) -> None:
    """Record the user who uploaded a stored graph file."""
    with _ownership_lock:
        _record_file_owner_locked(file_path, owner_identifier, filename)


def get_file_owner(file_path: str) -> str | None:
    """Return the recorded owner for a stored graph file, if any."""
    with _ownership_lock:
        registry = _load_ownership_registry()
    entry = registry.get(_registry_key(file_path))
    if isinstance(entry, dict):
        owner = entry.get("owner")
        return owner if isinstance(owner, str) else None
    return None


class FileProcessorService:
    """Service for processing uploaded files.

    This service handles file validation, temporary storage, and
    metadata extraction for uploaded files.
    """

    @staticmethod
    def validate_file_size(file_size_bytes: int) -> None:
        """Validate file size against maximum limit.

        Args:
            file_size_bytes: File size in bytes

        Raises:
            FileUploadError: If file exceeds maximum size
        """
        if file_size_bytes > MAX_FILE_SIZE_BYTES:
            file_size_mb = file_size_bytes / (1024 * 1024)
            raise FileUploadError(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum ({MAX_FILE_SIZE_MB} MB)"
            )

    @staticmethod
    def validate_file_extension(file_extension: str) -> None:
        """Validate file extension against allowed extensions.

        Args:
            file_extension: File extension (e.g., '.pdf')

        Raises:
            FileUploadError: If file extension is not allowed
        """
        if file_extension.lower() not in ALLOWED_FILE_EXTENSIONS:
            raise FileUploadError(
                f"File type {file_extension} not allowed. "
                f"Allowed types: {ALLOWED_FILE_EXTENSIONS}"
            )

    @staticmethod
    def create_temp_file(contents: bytes, file_extension: str) -> str:
        """Create a stored upload file with the given contents.

        Args:
            contents: File contents as bytes
            file_extension: File extension (e.g., '.pdf')

        Returns:
            Path to the created upload file
        """
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        while True:
            candidate = UPLOAD_DIR / f"{secrets.token_urlsafe(16)}{file_extension}"
            try:
                with candidate.open("xb") as upload_file:
                    upload_file.write(contents)
                logger.debug(f"{LOG_PREFIX} Created upload file: {candidate}")
                return str(candidate)
            except FileExistsError:
                continue

    @staticmethod
    def create_file_info(
        temp_path: str,
        filename: str,
        file_extension: str,
        file_size_mb: float,
        contents: bytes,
    ) -> dict[str, Any]:
        """Create file info dictionary.

        Args:
            temp_path: Path to temporary file
            filename: Original filename
            file_extension: File extension
            file_size_mb: File size in MB
            contents: File contents as bytes

        Returns:
            Dictionary containing file information
        """
        return {
            "path": temp_path,
            "filename": filename,
            "extension": file_extension,
            "size_mb": file_size_mb,
            "base64": base64.b64encode(contents).decode("utf-8"),
        }

    @classmethod
    async def process_upload(
        cls, filename: str, contents: bytes, owner_identifier: str | None = None
    ) -> dict[str, Any]:
        """Process an uploaded file.

        This method validates the file, creates a temporary file,
        and returns file information.

        Args:
            filename: Original filename
            contents: File contents as bytes
            owner_identifier: Optional authenticated uploader identifier

        Returns:
            Dictionary containing file information

        Raises:
            FileUploadError: If validation fails
        """
        # Validate file size
        file_size_bytes = len(contents)
        cls.validate_file_size(file_size_bytes)
        file_size_mb = file_size_bytes / (1024 * 1024)

        # Get and validate file extension
        file_extension = os.path.splitext(filename)[1].lower()
        cls.validate_file_extension(file_extension)

        # Create temporary file
        temp_path = cls.create_temp_file(contents, file_extension)

        # Create file info
        file_info = cls.create_file_info(
            temp_path, filename, file_extension, file_size_mb, contents
        )

        if owner_identifier:
            record_file_owner(temp_path, owner_identifier, filename)

        logger.info(
            f"{LOG_PREFIX} Processed file upload: {filename} ({file_size_mb:.2f} MB)"
        )

        return file_info
