"""Azure AI Document Intelligence extraction service.

Extracts text and structured content from documents using the Azure Document
Intelligence (formerly Form Recognizer) REST API.

Requires:
- AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT environment variable
- AZURE_DOCUMENT_INTELLIGENCE_KEY environment variable
  OR managed identity enabled via AZURE_DOCUMENT_INTELLIGENCE_MANAGED_IDENTITY=true

Supported file types: PDF, JPEG, PNG, BMP, TIFF, HEIF, DOCX, XLSX, PPTX, HTML
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AzureDocumentIntelligenceService:
    """Extracts document text using Azure AI Document Intelligence."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        use_managed_identity: Optional[bool] = None,
    ):
        self.endpoint = endpoint or os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", ""
        )
        self.api_key = api_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
        self.use_managed_identity = (
            use_managed_identity
            if use_managed_identity is not None
            else os.getenv(
                "AZURE_DOCUMENT_INTELLIGENCE_MANAGED_IDENTITY", "false"
            ).lower()
            == "true"
        )

        if not self.endpoint:
            raise ValueError(
                "Azure Document Intelligence endpoint not configured. "
                "Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT."
            )

        logger.info(
            f"[AZURE-DI] Initialised with endpoint: {self.endpoint}, "
            f"managed_identity={self.use_managed_identity}"
        )

    def _get_client(self):
        """Build an Azure Document Intelligence client."""
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:
            raise ImportError(
                "azure-ai-documentintelligence is not installed. "
                "Install it with: pip install azure-ai-documentintelligence"
            ) from exc

        if self.use_managed_identity or not self.api_key:
            credential = DefaultAzureCredential()
        else:
            credential = AzureKeyCredential(self.api_key)

        return DocumentIntelligenceClient(endpoint=self.endpoint, credential=credential)

    def extract_file(
        self,
        file_path: str,
        model_id: str = "prebuilt-read",
        **_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Extract text from a file using Azure Document Intelligence.

        Args:
            file_path: Absolute path to the document.
            model_id: Azure DI model to use (default: prebuilt-read).
            **kwargs: Ignored – accepted for interface compatibility.

        Returns:
            Standard extraction result dict.
        """
        path = Path(file_path)
        logger.info(f"[AZURE-DI] Extracting text from: {path.name}, model={model_id}")

        try:
            with open(file_path, "rb") as fh:
                file_bytes = fh.read()
            return self._analyze_bytes(file_bytes, path.name, model_id)
        except FileNotFoundError:
            return self._error_result(f"File not found: {file_path}")
        except Exception as exc:
            logger.error(
                f"[AZURE-DI] Extraction failed for {path.name}: {exc}", exc_info=True
            )
            return self._error_result(str(exc))

    def extract_bytes(
        self,
        file_bytes: bytes,
        filename: str = "document",
        model_id: str = "prebuilt-read",
        **_kwargs: Any,
    ) -> Dict[str, Any]:
        """Extract text from raw bytes using Azure Document Intelligence."""
        logger.info(f"[AZURE-DI] Extracting text from bytes ({len(file_bytes)} bytes)")
        try:
            return self._analyze_bytes(file_bytes, filename, model_id)
        except Exception as exc:
            logger.error(f"[AZURE-DI] Bytes extraction failed: {exc}", exc_info=True)
            return self._error_result(str(exc))

    def _analyze_bytes(
        self, file_bytes: bytes, filename: str, model_id: str
    ) -> Dict[str, Any]:
        """Submit bytes to Azure DI and collect the extracted text."""
        client = self._get_client()

        from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

        poller = client.begin_analyze_document(
            model_id,
            AnalyzeDocumentRequest(bytes_source=file_bytes),
        )
        result = poller.result()

        # Collect full content (paragraphs in reading order)
        content = result.content or ""
        page_count = len(result.pages) if result.pages else 0

        logger.info(
            f"[AZURE-DI] Extracted {len(content)} characters from {filename} "
            f"({page_count} pages)"
        )
        return {
            "success": True,
            "text": content,
            "extraction_method": "azure_document_intelligence",
            "page_count": page_count,
        }

    def test_connection(self) -> Dict[str, Any]:
        """Verify that the Azure DI endpoint is reachable and credentials work."""
        try:
            client = self._get_client()
            # List available models as a lightweight connectivity check
            models = list(client.list_models())
            return {
                "success": True,
                "endpoint": self.endpoint,
                "model_count": len(models),
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "endpoint": self.endpoint,
            }

    @staticmethod
    def _error_result(error: str) -> Dict[str, Any]:
        return {
            "success": False,
            "text": "",
            "extraction_method": "azure_document_intelligence",
            "error": error,
        }
