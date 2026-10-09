"""PDF processor for AI model Vision-based OCR."""

import logging

import fitz  # PyMuPDF

from ..base import OCRProcessor
from ..config import DEFAULT_PDF_SCALE, SUPPORTED_PDF_EXTENSIONS, get_default_prompt
from ..exceptions import InvalidInputError
from ..models import OCRRequest, OCRResponse, PageResult
from ..utils import build_error_response, build_success_response
from .image import ImageProcessor


logger = logging.getLogger(__name__)


class PDFProcessor(OCRProcessor):
    """Processor for PDF files using AI model Vision."""

    def __init__(self, client, deployment_name: str, detail: str = "high"):
        """
        Initialize PDF processor.

        Args:
            client: Azure OpenAI client
            deployment_name: Model deployment name
            detail: Vision API detail level ("low", "auto", or "high")
        """
        super().__init__(client)
        self.deployment_name = deployment_name
        self.image_processor = ImageProcessor(client, deployment_name, detail=detail)

    def supports_file_type(self, file_ext: str) -> bool:
        """Check if this processor supports the given file type."""
        return file_ext in SUPPORTED_PDF_EXTENSIONS

    def process(self, request: OCRRequest) -> OCRResponse:
        """
        Process PDF document page by page using AI model Vision.

        Args:
            request: OCR request with PDF and configuration

        Returns:
            OCR response with extracted text and metadata
        """
        prompt = request.prompt or get_default_prompt(request.doc_type)

        try:
            # Open PDF document
            pdf_document = self._open_pdf(request)

            # Process pages
            page_results = self._process_pages(
                pdf_document, prompt, request.doc_type, request.max_pages
            )

            pdf_document.close()

            # Compile results
            total_tokens = sum(pr.tokens for pr in page_results)

            if request.chunk_by_page:
                return build_success_response(
                    text=page_results,
                    extraction_method="model_ocr_vision_pdf",
                    tokens_used=total_tokens,
                    model=self.deployment_name,
                    page_count=len(page_results),
                    pages=page_results,
                )
            else:
                combined_text = self._combine_page_results(page_results)
                return build_success_response(
                    text=combined_text,
                    extraction_method="model_ocr_vision_pdf",
                    tokens_used=total_tokens,
                    model=self.deployment_name,
                    page_count=len(page_results),
                )

        except Exception as e:
            logger.error(f"[OCR-PDF] Error processing PDF: {e}", exc_info=True)
            return build_error_response(str(e), "model_ocr_vision_pdf")

    def _open_pdf(self, request: OCRRequest):
        """Open PDF from path or bytes."""
        if request.file_path:
            return fitz.open(request.file_path)
        elif request.file_bytes:
            return fitz.open(stream=request.file_bytes, filetype="pdf")
        else:
            raise InvalidInputError("Either file_path or file_bytes must be provided")

    def _process_pages(
        self, pdf_document, prompt: str, doc_type: str, max_pages: int = None
    ) -> list:
        """Process PDF pages."""
        page_count = len(pdf_document)
        pages_to_process = min(page_count, max_pages) if max_pages else page_count

        logger.info(f"[OCR-PDF] Processing {pages_to_process} pages from PDF")

        page_results = []
        for page_num in range(pages_to_process):
            page_result = self._process_single_page(
                pdf_document, page_num, prompt, doc_type, pages_to_process
            )
            page_results.append(page_result)

        return page_results

    def _process_single_page(
        self, pdf_document, page_num: int, prompt: str, doc_type: str, total_pages: int
    ) -> PageResult:
        """Process a single PDF page."""
        try:
            # Convert page to image
            page = pdf_document[page_num]
            pix = page.get_pixmap(
                matrix=fitz.Matrix(DEFAULT_PDF_SCALE, DEFAULT_PDF_SCALE)
            )
            img_bytes = pix.tobytes("png")

            # Process page image
            page_prompt = f"Page {page_num + 1} of {total_pages}. {prompt}"
            page_request = OCRRequest(
                file_bytes=img_bytes, prompt=page_prompt, doc_type=doc_type
            )

            result = self.image_processor.process(page_request)

            if result.success:
                return PageResult(
                    page=page_num + 1, text=result.text, tokens=result.tokens_used
                )
            else:
                logger.warning(
                    f"[OCR-PDF] Failed to process page {page_num + 1}: {result.error}"
                )
                return PageResult(
                    page=page_num + 1, text="", tokens=0, error=result.error
                )

        except Exception as e:
            logger.error(
                f"[OCR-PDF] Error processing page {page_num + 1}: {e}", exc_info=True
            )
            return PageResult(page=page_num + 1, text="", tokens=0, error=str(e))

    def _combine_page_results(self, page_results: list) -> str:
        """Combine page results into single text."""
        combined_parts = []
        for pr in page_results:
            if pr.text:
                combined_parts.append(f"# Page {pr.page}\n\n{pr.text}")

        return "\n\n---\n\n".join(combined_parts)
