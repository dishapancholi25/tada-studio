"""
File Tools - File system operations for agents.

Provides safe file reading and writing capabilities with configurable
access restrictions and validation.
"""

import logging
from pathlib import Path
from typing import List, Optional

from langchain_core.tools import BaseTool
from pydantic import Field, validator


logger = logging.getLogger(__name__)


class FileReadTool(BaseTool):
    """Tool for reading files from the file system.

    Provides safe file reading with path validation and extension filtering.
    
    TEMPORARILY DISABLED: due to ISG security audit
    Will be re-enabled after fixes are implemented
    """

    name: str = "file_read"
    description: str = (
        "Read contents from a file. "
        "Input should be the file path. "
        "Returns the file contents as a string."
    )

    base_path: str = Field(
        default=".",
        description="Base directory path - all file operations are relative to this",
    )
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".txt", ".json", ".yaml", ".yml", ".md", ".csv"],
        description="List of allowed file extensions",
    )
    max_file_size_mb: int = Field(
        default=1024, description="Maximum file size in megabytes"
    )

    @validator("base_path")
    def validate_base_path(cls, v):
        """Ensure base path exists and is absolute."""
        path = Path(v).resolve()
        if not path.exists():
            logger.warning(f"[FILE-READ-TOOL] Base path does not exist: {path}")
        return str(path)

    def _validate_file_path(self, file_path: str) -> Path:
        """Validate and resolve file path.

        Args:
            file_path: File path to validate

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is invalid or unsafe
        """
        # Resolve the path
        base = Path(self.base_path).resolve()
        target = (base / file_path).resolve()

        # Security: Ensure target is within base_path
        try:
            target.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Access denied: File path '{file_path}' is outside base directory"
            )

        # Check file extension
        if self.allowed_extensions and target.suffix not in self.allowed_extensions:
            raise ValueError(
                f"File extension '{target.suffix}' not allowed. "
                f"Allowed: {', '.join(self.allowed_extensions)}"
            )

        # Check file exists
        if not target.exists():
            raise ValueError(f"File not found: {file_path}")

        # Check it's a file, not a directory
        if not target.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Check file size
        max_size_bytes = self.max_file_size_mb * 1024 * 1024
        if target.stat().st_size > max_size_bytes:
            raise ValueError(
                f"File too large: {target.stat().st_size / (1024 * 1024):.2f}MB "
                f"(max: {self.max_file_size_mb}MB)"
            )

        return target

    def _run(self, file_path: str) -> str:
        """Read a file from the file system.

        Args:
            file_path: Path to the file to read (relative to base_path)

        Returns:
            File contents as a string
        """
        # TEMPORARILY DISABLED: due to ISG security audit
        # Uncomment below code when fixes are implemented
        
        # logger.info(f"[FILE-READ-TOOL] Reading file: {file_path}")
        # try:
        #     # Validate path
        #     target = self._validate_file_path(file_path)
        #     # Read file
        #     with open(target, "r", encoding="utf-8") as f:
        #         content = f.read()
        #     logger.info(
        #         f"[FILE-READ-TOOL] Successfully read {len(content)} characters from {file_path}"
        #     )
        #     return content
        # except Exception as e:
        #     error_msg = f"Failed to read file '{file_path}': {str(e)}"
        #     logger.error(f"[FILE-READ-TOOL] {error_msg}")
        #     return f"Error: {error_msg}"
        
        # Return error while feature is disabled
        error_msg = (
            "File Read tool is temporarily unavailable due to security updates. "
            "This feature will be re-enabled after ISG fixes are implemented."
        )
        logger.warning(f"[FILE-READ-TOOL] {error_msg}")
        return f"Error: {error_msg}"

    async def _arun(self, file_path: str) -> str:
        """Async version of file read (delegates to sync)."""
        return self._run(file_path)


class FileWriteTool(BaseTool):
    """Tool for writing files to the file system.

    Provides safe file writing with path validation and extension filtering.
    """

    name: str = "file_write"
    description: str = (
        "Write content to a file. "
        "Input should be a JSON with 'file_path' and 'content' keys. "
        "Returns success message or error."
    )

    base_path: str = Field(
        default=".",
        description="Base directory path - all file operations are relative to this",
    )
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".txt", ".json", ".yaml", ".yml", ".md", ".csv"],
        description="List of allowed file extensions",
    )
    max_content_size_mb: int = Field(
        default=10, description="Maximum content size in megabytes"
    )
    create_directories: bool = Field(
        default=True,
        description="Whether to create parent directories if they don't exist",
    )

    @validator("base_path")
    def validate_base_path(cls, v):
        """Ensure base path exists and is absolute."""
        path = Path(v).resolve()
        if not path.exists():
            logger.warning(f"[FILE-WRITE-TOOL] Base path does not exist: {path}")
            path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _validate_file_path(self, file_path: str) -> Path:
        """Validate and resolve file path.

        Args:
            file_path: File path to validate

        Returns:
            Resolved Path object

        Raises:
            ValueError: If path is invalid or unsafe
        """
        # Resolve the path
        base = Path(self.base_path).resolve()
        target = (base / file_path).resolve()

        # Security: Ensure target is within base_path
        try:
            target.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Access denied: File path '{file_path}' is outside base directory"
            )

        # Check file extension
        if self.allowed_extensions and target.suffix not in self.allowed_extensions:
            raise ValueError(
                f"File extension '{target.suffix}' not allowed. "
                f"Allowed: {', '.join(self.allowed_extensions)}"
            )

        # Check if target is not a directory
        if target.exists() and target.is_dir():
            raise ValueError(f"Path is a directory, not a file: {file_path}")

        return target

    def _run(self, file_path: str, content: str) -> str:
        """Write content to a file.

        Args:
            file_path: Path to the file to write (relative to base_path)
            content: Content to write to the file

        Returns:
            Success message or error
        """
        logger.info(f"[FILE-WRITE-TOOL] Writing to file: {file_path}")

        try:
            # Validate content size
            content_size_mb = len(content.encode("utf-8")) / (1024 * 1024)
            if content_size_mb > self.max_content_size_mb:
                raise ValueError(
                    f"Content too large: {content_size_mb:.2f}MB "
                    f"(max: {self.max_content_size_mb}MB)"
                )

            # Validate path
            target = self._validate_file_path(file_path)

            # Create parent directories if needed
            if self.create_directories:
                target.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(
                f"[FILE-WRITE-TOOL] Successfully wrote {len(content)} characters to {file_path}"
            )
            return f"Successfully wrote {len(content)} characters to {file_path}"

        except Exception as e:
            error_msg = f"Failed to write file '{file_path}': {str(e)}"
            logger.error(f"[FILE-WRITE-TOOL] {error_msg}")
            return f"Error: {error_msg}"

    async def _arun(self, file_path: str, content: str) -> str:
        """Async version of file write (delegates to sync)."""
        return self._run(file_path, content)


def create_file_read_tool(
    base_path: str = ".",
    allowed_extensions: Optional[List[str]] = None,
    max_file_size_mb: int = 1024,
) -> FileReadTool:
    """Factory function to create a file read tool.

    Args:
        base_path: Base directory for file operations
        allowed_extensions: List of allowed file extensions
        max_file_size_mb: Maximum file size in MB

    Returns:
        Configured FileReadTool instance
    """
    if allowed_extensions is None:
        allowed_extensions = [".txt", ".json", ".yaml", ".yml", ".md", ".csv"]

    return FileReadTool(
        base_path=base_path,
        allowed_extensions=allowed_extensions,
        max_file_size_mb=max_file_size_mb,
    )


def create_file_write_tool(
    base_path: str = ".",
    allowed_extensions: Optional[List[str]] = None,
    max_content_size_mb: int = 10,
    create_directories: bool = True,
) -> FileWriteTool:
    """Factory function to create a file write tool.

    Args:
        base_path: Base directory for file operations
        allowed_extensions: List of allowed file extensions
        max_content_size_mb: Maximum content size in MB
        create_directories: Whether to create parent directories

    Returns:
        Configured FileWriteTool instance
    """
    if allowed_extensions is None:
        allowed_extensions = [".txt", ".json", ".yaml", ".yml", ".md", ".csv"]

    return FileWriteTool(
        base_path=base_path,
        allowed_extensions=allowed_extensions,
        max_content_size_mb=max_content_size_mb,
        create_directories=create_directories,
    )


__all__ = [
    "FileReadTool",
    "FileWriteTool",
    "create_file_read_tool",
    "create_file_write_tool",
]
