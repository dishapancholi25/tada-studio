"""PDF document loader with multiple fallback options."""

import logging
from typing import List

from langchain_core.documents import Document

from ..exceptions import LoaderNotAvailableError
from .base import BaseLoader


logger = logging.getLogger(__name__)


class PDFLoader(BaseLoader):
    """PDF loader with fallback support (PyPDF → PyMuPDF → PDFMiner)."""

    SUPPORTED_EXTENSIONS = {".pdf"}

    def load(self, file_path: str) -> List[Document]:
        """Load PDF document with fallback loaders.

        Args:
            file_path: Path to PDF file

        Returns:
            List of Document objects (one per page)

        Raises:
            LoaderNotAvailableError: If no PDF loader is available
            Exception: If loading fails
        """
        # Try PyPDFLoader first (most common)
        try:
            from langchain_community.document_loaders import PyPDFLoader

            logger.info("[PDF-LOADER] Using PyPDFLoader")
            loader = PyPDFLoader(file_path)
            return loader.load()

        except ImportError as e:
            logger.warning(f"[PDF-LOADER] PyPDFLoader not available: {e}")
            # Continue to next fallback

        except Exception as e:
            logger.error(f"[PDF-LOADER] PyPDFLoader failed: {e}")
            raise

        # Try PyMuPDFLoader as secondary
        try:
            from langchain_community.document_loaders import PyMuPDFLoader

            logger.info("[PDF-LOADER] Using PyMuPDFLoader as fallback")
            loader = PyMuPDFLoader(file_path)
            return loader.load()

        except ImportError:
            logger.warning("[PDF-LOADER] PyMuPDFLoader not available")
            # Continue to next fallback

        except Exception as e:
            logger.error(f"[PDF-LOADER] PyMuPDFLoader failed: {e}")
            raise

        # Try PDFMinerLoader as final fallback
        try:
            from langchain_community.document_loaders import PDFMinerLoader

            logger.info("[PDF-LOADER] Using PDFMinerLoader as final fallback")
            loader = PDFMinerLoader(file_path)
            return loader.load()

        except ImportError:
            # All loaders failed
            error_msg = (
                "No PDF loader available. Please install one of the following:\n"
                "  - pip install pypdf (for PyPDFLoader)\n"
                "  - pip install pymupdf (for PyMuPDFLoader)\n"
                "  - pip install pdfminer.six (for PDFMinerLoader)"
            )
            logger.error(f"[PDF-LOADER] {error_msg}")
            raise LoaderNotAvailableError("PDF loader", error_msg)

        except Exception as e:
            logger.error(f"[PDF-LOADER] PDFMinerLoader failed: {e}")
            raise

    @staticmethod
    def supports(file_extension: str) -> bool:
        """Check if PDF loader supports the file extension.

        Args:
            file_extension: File extension (e.g., '.pdf')

        Returns:
            True if extension is .pdf
        """
        return file_extension.lower() in PDFLoader.SUPPORTED_EXTENSIONS
