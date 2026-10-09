"""Main OCR service orchestrator."""

import logging
import os
from pathlib import Path
from typing import Dict, Optional

from openai import AzureOpenAI, OpenAI

from .config import ALL_SUPPORTED_EXTENSIONS, auto_detect_doc_type, get_default_prompt
from .exceptions import OCRConfigError, UnsupportedFileTypeError
from .models import AzureOpenAIConfig, OCRRequest
from .processors import (
    CSVProcessor,
    DOCXProcessor,
    ImageProcessor,
    PDFProcessor,
    TextProcessor,
)
from .utils import get_file_extension


logger = logging.getLogger(__name__)


class GPT4oOCRService:
    """Service for performing OCR using a configurable AI model Vision API."""

    def __init__(
        self,
        azure_config: Optional[Dict[str, str]] = None,
        model_config: Optional[Dict[str, any]] = None,
        detail: str = "high",
    ):
        """
        Initialize AI model OCR service with Azure OpenAI or general config.

        Args:
            azure_config: (Deprecated) Dictionary with Azure OpenAI configuration
                - api_key: Azure OpenAI API key
                - endpoint: Azure OpenAI endpoint
                - deployment_name: Model deployment name (gpt-4o-latest)
                - api_version: API version
            model_config: Dictionary with model configuration from deployment
                - provider: Provider name (azure, openai, etc.)
                - api_key: API key
                - endpoint/base_url: API endpoint
                - model_name: Model name
                - Other provider-specific settings
            detail: Vision API detail level ("low", "auto", or "high")

        Raises:
            OCRConfigError: If configuration is invalid
        """
        # Use model_config if provided, otherwise fall back to azure_config
        self.model_config = model_config
        self.detail = detail
        self.config = self._load_config(azure_config, model_config)
        self.client = self._initialize_client()
        self.processors = self._initialize_processors()

        deployment_name = (
            self.config.deployment_name
            if hasattr(self.config, "deployment_name")
            else self.model_config.get("model_name", "unknown")
        )
        logger.info(
            f"[OCR-SERVICE] AI Model OCR Service initialized with "
            f"deployment: {deployment_name}"
        )

    def _load_config(
        self,
        azure_config: Optional[Dict[str, str]],
        model_config: Optional[Dict[str, any]],
    ) -> Optional[AzureOpenAIConfig]:
        """Load and validate configuration."""
        # If model_config is provided, we'll use it directly and skip AzureOpenAIConfig
        if model_config is not None:
            return None  # We'll use model_config directly

        # Otherwise, use azure_config (backward compatibility)
        if azure_config is None:
            # Load from environment variables
            azure_config = {
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "deployment_name": os.getenv(
                    "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-latest"
                ),
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            }

        # If no API key, convert to model_config format to use managed identity
        if not azure_config.get("api_key"):
            logger.info(
                "[OCR-SERVICE] No API key found, converting to model_config for managed identity"
            )
            self.model_config = {
                "provider": "azure",
                "endpoint": azure_config.get("endpoint"),
                "model_name": azure_config.get("deployment_name", "gpt-4o-latest"),
                "api_version": azure_config.get("api_version", "2024-02-01"),
                "api_key": None,
                "use_managed_identity": True,
            }
            return None  # Will use model_config with managed identity

        try:
            return AzureOpenAIConfig(**azure_config)
        except Exception as e:
            logger.error(f"[OCR-SERVICE] Invalid Azure OpenAI configuration: {e}")
            raise OCRConfigError(f"Invalid Azure OpenAI configuration: {e}")

    def _get_token_provider(self, client_id: Optional[str] = None):
        """Get Azure AD token provider for managed identity authentication."""
        try:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            AZURE_COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
            credential = DefaultAzureCredential(managed_identity_client_id=client_id)
            token_provider = get_bearer_token_provider(
                credential, AZURE_COGNITIVE_SCOPE
            )
            logger.info("[OCR-SERVICE] Using Azure managed identity for authentication")
            return token_provider
        except Exception as e:
            logger.error(f"[OCR-SERVICE] Failed to create token provider: {e}")
            raise OCRConfigError(
                f"Failed to create Azure AD token provider for managed identity: {e}"
            )

    def _initialize_client(self):
        """Initialize OpenAI client based on provider."""
        if self.model_config:
            provider = (self.model_config.get("provider") or "").lower()
            api_key = self.model_config.get("api_key")
            use_managed_identity = self.model_config.get("use_managed_identity", False)
            client_id = self.model_config.get("managed_identity_client_id")

            if provider == "azure_openai_ptu":
                return self._initialize_gateway_client()

            if provider == "azure":
                # Use managed identity if explicitly enabled OR if no api_key provided
                if use_managed_identity or not api_key:
                    token_provider = self._get_token_provider(client_id)
                    return AzureOpenAI(
                        azure_ad_token_provider=token_provider,
                        api_version=self.model_config.get("api_version", "2024-02-01"),
                        azure_endpoint=self.model_config.get("endpoint"),
                    )
                else:
                    return AzureOpenAI(
                        api_key=api_key,
                        api_version=self.model_config.get("api_version", "2024-02-01"),
                        azure_endpoint=self.model_config.get("endpoint"),
                    )
            else:
                # Regular OpenAI or compatible providers
                return OpenAI(
                    api_key=api_key,
                    base_url=self.model_config.get("base_url")
                    or self.model_config.get("endpoint"),
                )
        else:
            # Backward compatibility with azure_config
            return AzureOpenAI(
                api_key=self.config.api_key,
                api_version=self.config.api_version,
                azure_endpoint=self.config.endpoint,
            )

    def _initialize_gateway_client(self) -> AzureOpenAI:
        """Initialize an ``AzureOpenAI`` client for the Mashreq gateway.

        Mirrors :class:`AzureOpenAIPTUProvider` for the OCR path:

        * fetches an OAuth ``client_credentials`` bearer token from the
          configured token endpoint (reusing the provider's process-wide
          token cache),
        * attaches the required gateway headers (``clientid``,
          ``X-USER-ID``, ``Content-Type``) via a custom ``httpx.Client``,
        * disables SSL verification when the deployment is configured that
          way (internal-CA certificates).

        Raises:
            OCRConfigError: If required PTU settings/credentials are missing.
        """
        import httpx
        import urllib3

        from backend.services.llm_models.providers.azure_openai_ptu import (
            AzureOpenAIPTUProvider,
        )

        cfg = self.model_config or {}
        token_url = cfg.get("token_url")
        client_id = cfg.get("client_id")
        client_secret = cfg.get("client_secret")
        scope = cfg.get("oauth_scope") or "CORP"
        grant_type = cfg.get("grant_type") or "client_credentials"
        verify_ssl = bool(cfg.get("verify_ssl", False))
        x_user_id = cfg.get("x_user_id") or "TADAUSER"
        endpoint = cfg.get("endpoint")
        api_version = cfg.get("api_version", "2024-02-01")
        deployment = cfg.get("model_name")

        missing = [
            name
            for name, value in (
                ("token_url", token_url),
                ("client_id", client_id),
                ("client_secret", client_secret),
                ("endpoint", endpoint),
            )
            if not value
        ]
        if missing:
            raise OCRConfigError(
                "Azure OpenAI PTU OCR deployment is missing required "
                f"fields: {', '.join(missing)}. Configure them on the model "
                "deployment before using it as the OCR model."
            )

        if not verify_ssl:
            urllib3.disable_warnings()

        def _token_provider() -> str:
            return AzureOpenAIPTUProvider.get_cached_token(
                token_url=token_url,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope,
                grant_type=grant_type,
                verify_ssl=verify_ssl,
                deployment=deployment,
            )

        http_client = httpx.Client(
            verify=verify_ssl,
            timeout=60.0,
            headers={
                "clientid": client_id,
                "X-USER-ID": x_user_id,
                "Content-Type": "application/json",
            },
        )

        logger.info(
            "[OCR-SERVICE] Initialized Azure OpenAI PTU (gateway) client "
            "(deployment=%s, endpoint=%s, verify_ssl=%s)",
            deployment,
            endpoint,
            verify_ssl,
        )

        return AzureOpenAI(
            azure_ad_token_provider=_token_provider,
            api_key=None,
            api_version=api_version,
            azure_endpoint=endpoint,
            http_client=http_client,
        )

    def _initialize_processors(self) -> dict:
        """Initialize OCR processors."""
        # Get model/deployment name
        if self.model_config:
            model_name = self.model_config.get("model_name", "gpt-4o")
        else:
            model_name = self.config.deployment_name

        return {
            "image": ImageProcessor(self.client, model_name, detail=self.detail),
            "pdf": PDFProcessor(self.client, model_name, detail=self.detail),
            "docx": DOCXProcessor(self.client, model_name, detail=self.detail),
            "text": TextProcessor(),
            "csv": CSVProcessor(),
        }

    @staticmethod
    def get_default_prompt(doc_type: str = "generic") -> str:
        """
        Get default OCR prompt for a document type.

        Args:
            doc_type: Type of document

        Returns:
            Default prompt string
        """
        return get_default_prompt(doc_type)

    def process_image(
        self,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        prompt: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> Dict:
        """
        Process a single image using AI model Vision.

        Args:
            image_path: Path to image file
            image_bytes: Image data as bytes
            prompt: Custom OCR prompt
            max_tokens: Maximum tokens for response

        Returns:
            Dictionary with extracted text and metadata
        """
        request = OCRRequest(
            file_path=image_path,
            file_bytes=image_bytes,
            prompt=prompt,
            max_tokens=max_tokens,
        )
        response = self.processors["image"].process(request)
        return response.model_dump()

    def process_pdf(
        self,
        pdf_path: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        prompt: Optional[str] = None,
        max_pages: Optional[int] = None,
        chunk_by_page: bool = False,
    ) -> Dict:
        """
        Process PDF document page by page using AI model Vision.

        Args:
            pdf_path: Path to PDF file
            pdf_bytes: PDF data as bytes
            prompt: Custom OCR prompt
            max_pages: Maximum number of pages to process
            chunk_by_page: Return results separated by page

        Returns:
            Dictionary with extracted text and metadata
        """
        request = OCRRequest(
            file_path=pdf_path,
            file_bytes=pdf_bytes,
            prompt=prompt,
            max_pages=max_pages,
            chunk_by_page=chunk_by_page,
        )
        response = self.processors["pdf"].process(request)
        return response.model_dump()

    def process_docx(
        self,
        docx_path: Optional[str] = None,
        docx_bytes: Optional[bytes] = None,
        prompt: Optional[str] = None,
    ) -> Dict:
        """
        Process DOCX document, extracting text and processing embedded images.

        Args:
            docx_path: Path to DOCX file
            docx_bytes: DOCX data as bytes
            prompt: Custom OCR prompt for images

        Returns:
            Dictionary with extracted text and metadata
        """
        request = OCRRequest(file_path=docx_path, file_bytes=docx_bytes, prompt=prompt)
        response = self.processors["docx"].process(request)
        return response.model_dump()

    def process_csv(
        self,
        csv_path: Optional[str] = None,
        csv_bytes: Optional[bytes] = None,
        delimiter: str = "auto",
        has_header: str = "auto",
        output_format: str = "markdown",
        max_rows: Optional[int] = None,
        chunk_size: int = 50,
        include_schema: bool = True,
        include_stats: bool = True,
        encoding: str = "auto",
    ) -> Dict:
        """
        Process CSV file with LLM-optimized output formatting.

        Args:
            csv_path: Path to CSV file
            csv_bytes: CSV data as bytes
            delimiter: Delimiter (auto, comma, semicolon, tab, pipe)
            has_header: Header detection (auto, true, false)
            output_format: Output format (markdown, json, row_by_row, summary)
            max_rows: Maximum rows to process
            chunk_size: Rows per chunk for large files
            include_schema: Include column type inference
            include_stats: Include basic statistics
            encoding: File encoding (auto or specific)

        Returns:
            Dictionary with formatted CSV data and metadata
        """
        request = OCRRequest(file_path=csv_path, file_bytes=csv_bytes)
        response = self.processors["csv"].process_with_config(
            request,
            delimiter=delimiter,
            has_header=has_header,
            output_format=output_format,
            max_rows=max_rows,
            chunk_size=chunk_size,
            include_schema=include_schema,
            include_stats=include_stats,
            encoding=encoding,
        )
        result = response.model_dump()

        # Add structured CSV data for downstream field extraction
        structured = self.processors["csv"].parse_structured(
            OCRRequest(file_path=csv_path, file_bytes=csv_bytes),
            delimiter=delimiter,
            has_header=has_header,
            max_rows=max_rows,
            encoding=encoding,
        )
        result.update(structured)

        return result

    def process_file(
        self,
        file_path: str,
        prompt: Optional[str] = None,
        doc_type: str = "auto",
        **kwargs,
    ) -> Dict:
        """
        Process any supported file type.

        Args:
            file_path: Path to file
            prompt: Custom OCR prompt
            doc_type: Document type for prompt selection
            **kwargs: Additional arguments for specific processors

        Returns:
            Dictionary with extracted text and metadata

        Raises:
            UnsupportedFileTypeError: If file type is not supported
        """
        file_ext = get_file_extension(file_path)

        # Validate file type
        if file_ext not in ALL_SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError(file_ext, ALL_SUPPORTED_EXTENSIONS)

        # Auto-detect document type if needed
        if doc_type == "auto":
            doc_type = auto_detect_doc_type(file_path)

        # Use appropriate prompt
        if not prompt:
            prompt = get_default_prompt(doc_type)

        # Get appropriate processor
        processor = self._get_processor_for_file(file_ext)

        # Build request
        request = OCRRequest(
            file_path=file_path,
            prompt=prompt,
            doc_type=doc_type,
            max_pages=kwargs.get("max_pages"),
            chunk_by_page=kwargs.get("chunk_by_page", False),
            max_tokens=kwargs.get("max_tokens", 4000),
        )

        # Process file
        logger.info(
            f"[OCR-SERVICE] Processing file: {Path(file_path).name}, "
            f"type: {file_ext}, doc_type: {doc_type}"
        )

        response = processor.process(request)
        return response.model_dump()

    def _get_processor_for_file(self, file_ext: str):
        """Get appropriate processor for file extension."""
        for processor in self.processors.values():
            if processor.supports_file_type(file_ext):
                return processor

        raise UnsupportedFileTypeError(file_ext, ALL_SUPPORTED_EXTENSIONS)
