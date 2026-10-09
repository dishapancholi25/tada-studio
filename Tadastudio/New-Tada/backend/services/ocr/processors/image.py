"""Image processor for AI model Vision-based OCR."""

import logging

from ..base import OCRProcessor
from ..config import (
    DEFAULT_MAX_TOKENS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SYSTEM_PROMPT,
    get_default_prompt,
)
from ..models import OCRRequest, OCRResponse
from ..utils import build_error_response, build_success_response, encode_image


logger = logging.getLogger(__name__)


class ImageProcessor(OCRProcessor):
    """Processor for image files using AI model Vision."""

    def __init__(self, client, deployment_name: str, detail: str = "high"):
        """
        Initialize image processor.

        Args:
            client: Azure OpenAI client
            deployment_name: Model deployment name
            detail: Vision API detail level ("low", "auto", or "high")
        """
        super().__init__(client)
        self.deployment_name = deployment_name
        self.detail = detail

    def supports_file_type(self, file_ext: str) -> bool:
        """Check if this processor supports the given file type."""
        return file_ext in SUPPORTED_IMAGE_EXTENSIONS

    def process(self, request: OCRRequest) -> OCRResponse:
        """
        Process a single image using AI model Vision.

        Args:
            request: OCR request with image and configuration

        Returns:
            OCR response with extracted text and metadata
        """
        prompt = request.prompt or get_default_prompt(request.doc_type)
        max_tokens = request.max_tokens or DEFAULT_MAX_TOKENS

        try:
            # Encode image
            base64_image = encode_image(request.file_path, request.file_bytes)

            logger.info(
                "[OCR-IMAGE] Processing image with AI model Vision",
                extra={
                    "doc_type": request.doc_type,
                    "max_tokens": max_tokens,
                },
            )

            # Call AI model Vision API
            response = self._call_vision_api(base64_image, prompt, max_tokens)

            return build_success_response(
                text=response["text"],
                extraction_method="model_ocr_vision",
                tokens_used=response["tokens"],
                model=self.deployment_name,
            )

        except Exception as e:
            logger.error(f"[OCR-IMAGE] Error processing image: {e}", exc_info=True)
            return build_error_response(str(e), "model_ocr_vision")

    def _call_vision_api(self, base64_image: str, prompt: str, max_tokens: int) -> dict:
        """
        Call AI model Vision API.

        Args:
            base64_image: Base64 encoded image
            prompt: OCR prompt
            max_tokens: Maximum tokens for response

        Returns:
            Dictionary with text and tokens used
        """
        messages = self._build_messages(base64_image, prompt)

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
        )

        extracted_text = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.debug(
            f"[OCR-IMAGE] API call successful: {tokens_used} tokens, "
            f"{len(extracted_text)} chars"
        )

        return {"text": extracted_text, "tokens": tokens_used}

    def _build_messages(self, base64_image: str, prompt: str) -> list:
        """
        Build messages for Vision API.

        Args:
            base64_image: Base64 encoded image
            prompt: OCR prompt

        Returns:
            List of messages for API call
        """
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": self.detail,
                        },
                    },
                ],
            },
        ]
