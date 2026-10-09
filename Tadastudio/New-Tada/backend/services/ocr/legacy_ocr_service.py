"""Modern OCR Service with multiple library support."""

import io
import logging
from typing import Any, Dict, Optional

import numpy as np
from PIL import Image


logger = logging.getLogger(__name__)


class OCRService:
    """Service for performing OCR with multiple library support."""

    def __init__(self, library: str = "easyocr", language: str = "en"):
        """
        Initialize OCR service with specified library.

        Args:
            library: OCR library to use (easyocr, paddleocr, doctr, surya, tesseract)
            language: Language code for OCR
        """
        self.library = library
        self.language = language
        self.reader = None
        self._init_ocr_engine()

    def _init_ocr_engine(self):
        """Initialize the selected OCR engine."""
        try:
            if self.library == "easyocr":
                self._init_easyocr()
            elif self.library == "paddleocr":
                self._init_paddleocr()
            elif self.library == "doctr":
                self._init_doctr()
            elif self.library == "surya":
                self._init_surya()
            elif self.library == "tesseract":
                self._init_tesseract()
            else:
                logger.warning(
                    f"Unknown OCR library: {self.library}, falling back to EasyOCR"
                )
                self.library = "easyocr"
                self._init_easyocr()
        except ImportError as e:
            logger.error(f"Failed to initialize {self.library}: {e}")
            # Fallback to a simpler option
            if self.library != "tesseract":
                logger.info("Falling back to Tesseract")
                self.library = "tesseract"
                self._init_tesseract()

    def _init_easyocr(self):
        """Initialize EasyOCR."""
        try:
            import easyocr

            # Map language codes
            lang_map = {
                "en": ["en"],
                "es": ["es"],
                "fr": ["fr"],
                "de": ["de"],
                "zh": ["ch_sim"],
            }
            languages = lang_map.get(self.language, ["en"])
            self.reader = easyocr.Reader(languages, gpu=False)
            logger.info(f"EasyOCR initialized with languages: {languages}")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise

    def _init_paddleocr(self):
        """Initialize PaddleOCR."""
        try:
            from paddleocr import PaddleOCR

            # Map language codes
            lang_map = {
                "en": "en",
                "es": "es",
                "fr": "french",
                "de": "german",
                "zh": "ch",
            }
            lang = lang_map.get(self.language, "en")
            self.reader = PaddleOCR(use_angle_cls=True, lang=lang, use_gpu=False)
            logger.info(f"PaddleOCR initialized with language: {lang}")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise

    def _init_doctr(self):
        """Initialize docTR."""
        try:
            from doctr.models import ocr_predictor

            self.reader = ocr_predictor(pretrained=True)
            logger.info("docTR initialized")
        except Exception as e:
            logger.error(f"Failed to initialize docTR: {e}")
            raise

    def _init_surya(self):
        """Initialize Surya OCR."""
        try:
            # Surya is relatively new, may not be available
            import surya

            self.reader = surya.load_model()
            logger.info("Surya OCR initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Surya: {e}")
            raise

    def _init_tesseract(self):
        """Initialize Tesseract OCR."""
        try:
            import pytesseract

            # Test if Tesseract is installed
            pytesseract.get_tesseract_version()
            self.reader = "tesseract"
            logger.info("Tesseract OCR initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Tesseract: {e}")
            raise

    def extract_text_from_image(
        self,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        confidence_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Extract text from an image using the configured OCR engine.

        Args:
            image_path: Path to image file
            image_bytes: Image data as bytes
            confidence_threshold: Minimum confidence score for results

        Returns:
            Dictionary containing extracted text and metadata
        """
        if not image_path and not image_bytes:
            raise ValueError("Either image_path or image_bytes must be provided")

        # Load image
        if image_path:
            image = Image.open(image_path)
        else:
            image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Perform OCR based on library
        if self.library == "easyocr":
            return self._ocr_with_easyocr(image, confidence_threshold)
        elif self.library == "paddleocr":
            return self._ocr_with_paddleocr(image, confidence_threshold)
        elif self.library == "doctr":
            return self._ocr_with_doctr(image, confidence_threshold)
        elif self.library == "surya":
            return self._ocr_with_surya(image, confidence_threshold)
        else:  # tesseract
            return self._ocr_with_tesseract(image, confidence_threshold)

    def _ocr_with_easyocr(
        self, image: Image.Image, confidence_threshold: float
    ) -> Dict[str, Any]:
        """Perform OCR using EasyOCR."""
        # Convert PIL Image to numpy array
        img_array = np.array(image)

        # Perform OCR
        results = self.reader.readtext(img_array)

        # Process results
        text_blocks = []
        full_text = []
        total_confidence = 0
        count = 0

        for bbox, text, confidence in results:
            if confidence >= confidence_threshold:
                text_blocks.append(
                    {"text": text, "confidence": confidence, "bbox": bbox}
                )
                full_text.append(text)
                total_confidence += confidence
                count += 1

        avg_confidence = total_confidence / count if count > 0 else 0

        return {
            "text": " ".join(full_text),
            "blocks": text_blocks,
            "average_confidence": avg_confidence,
            "extraction_method": "easyocr",
            "language": self.language,
        }

    def _ocr_with_paddleocr(
        self, image: Image.Image, confidence_threshold: float
    ) -> Dict[str, Any]:
        """Perform OCR using PaddleOCR."""
        # Convert PIL Image to numpy array
        img_array = np.array(image)

        # Perform OCR
        result = self.reader.ocr(img_array, cls=True)

        # Process results
        text_blocks = []
        full_text = []
        total_confidence = 0
        count = 0

        if result and result[0]:
            for line in result[0]:
                bbox, (text, confidence) = line
                if confidence >= confidence_threshold:
                    text_blocks.append(
                        {"text": text, "confidence": confidence, "bbox": bbox}
                    )
                    full_text.append(text)
                    total_confidence += confidence
                    count += 1

        avg_confidence = total_confidence / count if count > 0 else 0

        return {
            "text": " ".join(full_text),
            "blocks": text_blocks,
            "average_confidence": avg_confidence,
            "extraction_method": "paddleocr",
            "language": self.language,
        }

    def _ocr_with_doctr(
        self, image: Image.Image, confidence_threshold: float
    ) -> Dict[str, Any]:
        """Perform OCR using docTR."""
        # Save image temporarily
        import tempfile

        from doctr.io import DocumentFile

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp.name)
            doc = DocumentFile.from_images(tmp.name)

        # Perform OCR
        result = self.reader(doc)

        # Process results
        text_blocks = []
        full_text = []

        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        if word.confidence >= confidence_threshold:
                            text_blocks.append(
                                {
                                    "text": word.value,
                                    "confidence": word.confidence,
                                    "bbox": word.geometry,
                                }
                            )
                            full_text.append(word.value)

        # Clean up temp file
        import os

        os.unlink(tmp.name)

        return {
            "text": " ".join(full_text),
            "blocks": text_blocks,
            "average_confidence": sum(b["confidence"] for b in text_blocks)
            / len(text_blocks)
            if text_blocks
            else 0,
            "extraction_method": "doctr",
            "language": self.language,
        }

    def _ocr_with_surya(
        self, image: Image.Image, confidence_threshold: float
    ) -> Dict[str, Any]:
        """Perform OCR using Surya."""
        # Surya implementation would go here
        # For now, fall back to tesseract
        logger.warning("Surya OCR not fully implemented, falling back to Tesseract")
        return self._ocr_with_tesseract(image, confidence_threshold)

    def _ocr_with_tesseract(
        self, image: Image.Image, confidence_threshold: float
    ) -> Dict[str, Any]:
        """Perform OCR using Tesseract."""
        import pytesseract

        # Get text with confidence scores
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Process results
        text_blocks = []
        full_text = []
        total_confidence = 0
        count = 0

        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])

            if (
                text and conf >= confidence_threshold * 100
            ):  # Tesseract uses 0-100 scale
                text_blocks.append(
                    {
                        "text": text,
                        "confidence": conf / 100,  # Normalize to 0-1
                        "bbox": [
                            data["left"][i],
                            data["top"][i],
                            data["left"][i] + data["width"][i],
                            data["top"][i] + data["height"][i],
                        ],
                    }
                )
                full_text.append(text)
                total_confidence += conf / 100
                count += 1

        avg_confidence = total_confidence / count if count > 0 else 0

        return {
            "text": " ".join(full_text),
            "blocks": text_blocks,
            "average_confidence": avg_confidence,
            "extraction_method": "tesseract",
            "language": self.language,
        }

    def extract_text_from_pdf_page(
        self, pdf_path: str, page_num: int, confidence_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Extract text from a specific PDF page using OCR.

        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            confidence_threshold: Minimum confidence score

        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            import pdf2image

            # Convert PDF page to image
            images = pdf2image.convert_from_path(
                pdf_path, first_page=page_num + 1, last_page=page_num + 1, dpi=300
            )

            if not images:
                return {
                    "text": "",
                    "blocks": [],
                    "average_confidence": 0,
                    "extraction_method": self.library,
                    "error": f"Could not convert page {page_num} to image",
                }

            # Perform OCR on the page image
            return self.extract_text_from_image(
                image_bytes=images[0].tobytes()
                if hasattr(images[0], "tobytes")
                else None,
                confidence_threshold=confidence_threshold,
            )

        except Exception as e:
            logger.error(f"Error extracting text from PDF page {page_num}: {e}")
            return {
                "text": "",
                "blocks": [],
                "average_confidence": 0,
                "extraction_method": self.library,
                "error": str(e),
            }
