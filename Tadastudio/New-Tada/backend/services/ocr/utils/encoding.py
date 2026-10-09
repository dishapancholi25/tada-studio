"""Image encoding utilities for OCR services."""

import base64
import logging
from typing import Optional

from ..exceptions import InvalidInputError


logger = logging.getLogger(__name__)


def encode_image(
    image_path: Optional[str] = None, image_bytes: Optional[bytes] = None
) -> str:
    """
    Encode image to base64 string for API.

    Args:
        image_path: Path to image file
        image_bytes: Image data as bytes

    Returns:
        Base64 encoded image string

    Raises:
        InvalidInputError: If neither image_path nor image_bytes provided
        FileNotFoundError: If image_path does not exist
        OSError: If file cannot be read
    """
    if image_path:
        logger.debug(f"[OCR-ENCODING] Reading image from path: {image_path}")
        try:
            with open(image_path, "rb") as image_file:
                image_bytes = image_file.read()
        except FileNotFoundError:
            logger.error(f"[OCR-ENCODING] Image file not found: {image_path}")
            raise
        except OSError as e:
            logger.error(f"[OCR-ENCODING] Failed to read image file: {e}")
            raise

    if not image_bytes:
        raise InvalidInputError("Either image_path or image_bytes must be provided")

    logger.debug(f"[OCR-ENCODING] Encoding {len(image_bytes)} bytes to base64")
    return base64.b64encode(image_bytes).decode("utf-8")
