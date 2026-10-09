"""Apache Tika document extraction service.

Extracts text from documents by posting them to a Tika REST server.
The server must be running and accessible at the configured TIKA_SERVER_URL.

Tika supports: PDF, DOCX, XLSX, PPTX, HTML, ODT, images (with Tesseract), and many more.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# Default Tika server URL (matches common Docker Compose service name)
DEFAULT_TIKA_URL = "http://tika:9998"

# MIME types that Tika handles well via its /tika endpoint
_TIKA_ACCEPT_PLAIN = "text/plain"


class TikaExtractionService:
    """Extracts document text using an Apache Tika REST server."""

    def __init__(self, server_url: Optional[str] = None, timeout: int = 60):
        self.server_url = (
            server_url or os.getenv("TIKA_SERVER_URL", DEFAULT_TIKA_URL)
        ).rstrip("/")
        self.timeout = timeout
        logger.info(f"[TIKA] Initialised with server: {self.server_url}")

    def extract_file(
        self,
        file_path: str,
        **_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Extract text from a file using Tika.

        Args:
            file_path: Absolute path to the document.
            **kwargs: Ignored – accepted for interface compatibility.

        Returns:
            Standard extraction result dict with keys:
            - success (bool)
            - text (str)
            - extraction_method (str)
            - error (str, only on failure)
        """
        path = Path(file_path)
        logger.info(f"[TIKA] Extracting text from: {path.name}")

        try:
            with open(file_path, "rb") as fh:
                file_bytes = fh.read()
            return self._post_to_tika(file_bytes, path.name)
        except FileNotFoundError:
            return self._error_result(f"File not found: {file_path}")
        except Exception as exc:
            logger.error(
                f"[TIKA] Extraction failed for {path.name}: {exc}", exc_info=True
            )
            return self._error_result(str(exc))

    def extract_bytes(
        self,
        file_bytes: bytes,
        filename: str = "document",
        **_kwargs: Any,
    ) -> Dict[str, Any]:
        """Extract text from raw bytes using Tika."""
        logger.info(f"[TIKA] Extracting text from bytes ({len(file_bytes)} bytes)")
        try:
            return self._post_to_tika(file_bytes, filename)
        except Exception as exc:
            logger.error(f"[TIKA] Bytes extraction failed: {exc}", exc_info=True)
            return self._error_result(str(exc))

    def _post_to_tika(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """POST file bytes to the Tika /tika endpoint and return plain text."""
        url = f"{self.server_url}/tika"
        headers = {
            "Accept": _TIKA_ACCEPT_PLAIN,
            "Content-Disposition": f'attachment; filename="{filename}"',
        }

        response = requests.put(
            url,
            data=file_bytes,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()

        extracted_text = response.text.strip()
        logger.info(
            f"[TIKA] Extracted {len(extracted_text)} characters from {filename}"
        )
        return {
            "success": True,
            "text": extracted_text,
            "extraction_method": "tika",
        }

    def test_connection(self) -> Dict[str, Any]:
        """Verify that the Tika server is reachable."""
        try:
            response = requests.get(
                f"{self.server_url}/tika",
                headers={"Accept": "text/plain"},
                timeout=10,
            )
            return {
                "success": response.status_code in (200, 204),
                "status_code": response.status_code,
                "server_url": self.server_url,
            }
        except requests.exceptions.ConnectionError as exc:
            return {
                "success": False,
                "error": f"Cannot connect to Tika server at {self.server_url}: {exc}",
                "server_url": self.server_url,
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "server_url": self.server_url,
            }

    @staticmethod
    def _error_result(error: str) -> Dict[str, Any]:
        return {
            "success": False,
            "text": "",
            "extraction_method": "tika",
            "error": error,
        }
