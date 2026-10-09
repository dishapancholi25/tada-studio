"""Markdown document loader using LangChain UnstructuredMarkdownLoader."""

import logging
from typing import List
from langchain_core.documents import Document
from ..exceptions import LoaderNotAvailableError
from .base import BaseLoader

logger = logging.getLogger(__name__)


class MarkdownLoader(BaseLoader):
    """Markdown document loader using UnstructuredMarkdownLoader."""

    SUPPORTED_EXTENSIONS = {".md"}

    def load(self, file_path: str) -> List[Document]:
        """Load markdown document using LangChain UnstructuredMarkdownLoader.

        Args:
            file_path: Path to markdown file

        Returns:
            List of Document objects

        Raises:
            LoaderNotAvailableError: If loader is not available
            Exception: If loading fails
        """
        try:
            from langchain_community.document_loaders import UnstructuredMarkdownLoader

            logger.info(
                "[MARKDOWN-LOADER] Loading markdown file with UnstructuredMarkdownLoader"
            )
            loader = UnstructuredMarkdownLoader(
                file_path, mode="single", strategy="fast"
            )
            return loader.load()
        except ImportError as e:
            logger.error(
                f"[MARKDOWN-LOADER] UnstructuredMarkdownLoader not available: {e}"
            )
            raise LoaderNotAvailableError(
                "UnstructuredMarkdownLoader",
                "pip install -qU langchain_community unstructured",
            )
        except Exception as e:
            logger.error(f"[MARKDOWN-LOADER] Failed to load markdown: {e}")
            raise

    @staticmethod
    def supports(file_extension: str) -> bool:
        """Check if markdown loader supports the file extension.

        Args:
            file_extension: File extension (e.g., '.md')

        Returns:
            True if extension is .md
        """
        return file_extension.lower() in MarkdownLoader.SUPPORTED_EXTENSIONS
