"""Document extraction factory.

Selects and returns the configured extraction backend.

Provider is read from the system_settings DB table (set by admins via the
settings UI) so that changes take effect immediately for any workflow triggered
after the save, without requiring a process restart.  Environment variables are
used as the fallback when no DB record exists.

Supported providers:
- model_ocr (default): AI model OCR – handled by the configured model deployment
- tika:                 Apache Tika REST server
- azure_document_intelligence: Azure AI Document Intelligence
"""

import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PROVIDER_MODEL_OCR = "model_ocr"
PROVIDER_TIKA = "tika"
PROVIDER_AZURE_DI = "azure_document_intelligence"

VALID_PROVIDERS = {PROVIDER_MODEL_OCR, PROVIDER_TIKA, PROVIDER_AZURE_DI}


def _read_db_setting(key: str, default: str) -> str:
    """Read a single value from the system_settings table.

    Falls back to *default* if the table doesn't exist yet, the key is absent,
    or any other DB error occurs.  Intentionally avoids importing
    ConfigurationService to keep the dependency footprint small.
    """
    try:
        from sqlalchemy import text as sa_text

        from backend.services.database.session import get_db

        with get_db() as db:
            row = db.execute(
                sa_text("SELECT value FROM system_settings WHERE key = :key"),
                {"key": key},
            ).fetchone()
            if row is not None:
                return str(row[0])
    except Exception:
        pass
    return default


def get_extraction_provider() -> str:
    """Return the active extraction provider, reading live from the DB.

    Reads system_settings first so that admin changes via the UI take effect
    immediately without a process restart.  Falls back to the
    DOCUMENT_EXTRACTION_PROVIDER environment variable if no DB record exists.
    """
    provider = (
        _read_db_setting(
            "DOCUMENT_EXTRACTION_PROVIDER",
            os.getenv("DOCUMENT_EXTRACTION_PROVIDER", PROVIDER_MODEL_OCR),
        )
        .lower()
        .strip()
    )

    if provider not in VALID_PROVIDERS:
        logger.warning(
            f"[DOC-EXTRACT] Unknown provider '{provider}', falling back to '{PROVIDER_MODEL_OCR}'"
        )
        return PROVIDER_MODEL_OCR
    return provider


class DocumentExtractionFactory:
    """Factory that routes document extraction to the configured backend."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or get_extraction_provider()
        logger.debug(f"[DOC-EXTRACT] Using provider: {self.provider}")

    def extract_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Extract text from a file using the configured provider.

        Args:
            file_path: Absolute path to the document.
            **kwargs: Provider-specific options (e.g. prompt, max_pages for model_ocr).

        Returns:
            Standard result dict:
              - success (bool)
              - text (str)
              - extraction_method (str)
              - error (str, only on failure)
        """
        if self.provider == PROVIDER_TIKA:
            return self._extract_with_tika(file_path, **kwargs)
        elif self.provider == PROVIDER_AZURE_DI:
            return self._extract_with_azure_di(file_path, **kwargs)
        else:
            # model_ocr – callers should use GPT4oOCRService directly; this path
            # is a fallback in case the factory is called without checking first.
            return {
                "success": False,
                "text": "",
                "extraction_method": "model_ocr",
                "error": (
                    "model_ocr provider does not go through DocumentExtractionFactory. "
                    "Use GPT4oOCRService directly."
                ),
            }

    def _extract_with_tika(self, file_path: str, **kwargs) -> Dict[str, Any]:
        from .tika_service import TikaExtractionService
        from backend.services.configuration.system_external_service_service import (
            SystemExternalServiceService,
        )

        try:
            # Read live from DB so admin changes apply immediately
            server_url: Optional[str] = os.getenv("TIKA_SERVER_URL")
            timeout = int(os.getenv("TIKA_TIMEOUT_SECONDS", "60"))

            tika_svc = SystemExternalServiceService.get_service("tika")
            if tika_svc:
                server_url = tika_svc.service_url or server_url
                timeout = int((tika_svc.settings or {}).get("timeout_seconds", timeout))

            svc = TikaExtractionService(server_url=server_url, timeout=timeout)
            return svc.extract_file(file_path, **kwargs)
        except Exception as exc:
            logger.error(f"[DOC-EXTRACT] Tika extraction error: {exc}", exc_info=True)
            return {
                "success": False,
                "text": "",
                "extraction_method": "tika",
                "error": str(exc),
            }

    def _extract_with_azure_di(self, file_path: str, **kwargs) -> Dict[str, Any]:
        from .azure_di_service import AzureDocumentIntelligenceService
        from backend.services.configuration.system_external_service_service import (
            SystemExternalServiceService,
        )

        try:
            # Start with env-var defaults, then overlay live DB values
            endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
            api_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY", "")
            use_managed_identity = (
                os.getenv(
                    "AZURE_DOCUMENT_INTELLIGENCE_MANAGED_IDENTITY", "false"
                ).lower()
                == "true"
            )
            model_id = os.getenv("AZURE_DI_MODEL_ID", "prebuilt-read")

            azure_svc = SystemExternalServiceService.get_service(
                "azure_document_intelligence"
            )
            if azure_svc:
                endpoint = azure_svc.service_url or endpoint
                settings = azure_svc.settings or {}
                use_managed_identity = bool(
                    settings.get("use_managed_identity", use_managed_identity)
                )
                model_id = settings.get("model_id", model_id)
                creds = SystemExternalServiceService.get_decrypted_credentials(
                    "azure_document_intelligence"
                )
                if creds:
                    api_key = creds.get("api_key", api_key)

            svc = AzureDocumentIntelligenceService(
                endpoint=endpoint,
                api_key=api_key,
                use_managed_identity=use_managed_identity,
            )
            return svc.extract_file(file_path, model_id=model_id, **kwargs)
        except Exception as exc:
            logger.error(
                f"[DOC-EXTRACT] Azure DI extraction error: {exc}", exc_info=True
            )
            return {
                "success": False,
                "text": "",
                "extraction_method": "azure_document_intelligence",
                "error": str(exc),
            }

    def is_model_ocr(self) -> bool:
        """Return True when the configured provider is model_ocr."""
        return self.provider == PROVIDER_MODEL_OCR
