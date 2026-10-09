"""DOCX document loader."""

import logging
from typing import List

from langchain_core.documents import Document

from ..exceptions import LoaderNotAvailableError
from .base import BaseLoader


logger = logging.getLogger(__name__)


class DOCXLoader(BaseLoader):
    """DOCX document loader."""

    SUPPORTED_EXTENSIONS = {".docx"}

    def load(self, file_path: str) -> List[Document]:
        """Load DOCX document.

        Args:
            file_path: Path to DOCX file

        Returns:
            List of Document objects

        Raises:
            LoaderNotAvailableError: If docx2txt is not installed
            Exception: If loading fails
        """
        try:
            from langchain_community.document_loaders import Docx2txtLoader

            logger.info("[DOCX-LOADER] Using Docx2txtLoader")
            loader = Docx2txtLoader(file_path)
            return loader.load()

        except ImportError:
            error_msg = "pip install docx2txt"
            logger.error(
                f"[DOCX-LOADER] docx2txt not available. Install with: {error_msg}"
            )
            raise LoaderNotAvailableError("DOCX loader", error_msg)

        except Exception as e:
            logger.error(f"[DOCX-LOADER] Failed to load DOCX: {e}")
            raise

    @staticmethod
    def supports(file_extension: str) -> bool:
        """Check if DOCX loader supports the file extension.

        Args:
            file_extension: File extension (e.g., '.docx')

        Returns:
            True if extension is .docx
        """
        return file_extension.lower() in DOCXLoader.SUPPORTED_EXTENSIONS
