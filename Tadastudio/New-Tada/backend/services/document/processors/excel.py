"""Excel file processor using pandas."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from ..config import EXCEL_FILE_TYPES
from ..exceptions import DocumentProcessingError, ProcessorNotAvailableError
from .base import DocumentProcessor


logger = logging.getLogger(__name__)


class ExcelProcessor(DocumentProcessor):
    """Processor for Excel files using pandas."""

    def __init__(self):
        """Initialize Excel processor."""
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if pandas is available."""
        try:
            import pandas  # noqa: F401

            logger.debug("[DOC-EXCEL] pandas available")
        except ImportError:
            raise ProcessorNotAvailableError("excel", "pandas library not installed")

    def supports(self, file_type: str) -> bool:
        """Check if this processor supports the file type."""
        return file_type in EXCEL_FILE_TYPES

    def process(self, file_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an Excel file.

        Args:
            file_path: Path to Excel file
            config: Processing configuration

        Returns:
            Dictionary with extracted content
        """
        logger.info(f"[DOC-EXCEL] Processing Excel file: {file_path.name}")

        try:
            import pandas as pd

            excel_file = pd.ExcelFile(file_path)
            sheets_content = self._process_sheets(excel_file, config)

            output_format = config.get("output_format", "markdown")

            if output_format == "json":
                content = {"sheets": sheets_content}
            else:
                content = "\n\n".join(sheets_content)

            logger.debug(f"[DOC-EXCEL] Processed {len(excel_file.sheet_names)} sheets")

            return {
                "content": content,
                "extraction_method": "pandas",
                "sheet_count": len(excel_file.sheet_names),
            }

        except Exception as e:
            logger.error(f"[DOC-EXCEL] Excel extraction failed: {e}")
            raise DocumentProcessingError(
                f"Failed to process Excel file: {e}",
                file_path=str(file_path),
                processor="excel",
            )

    def _process_sheets(self, excel_file, config: Dict[str, Any]) -> List:
        """Process all sheets in Excel file."""
        import pandas as pd

        sheets_content = []
        output_format = config.get("output_format", "markdown")

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            if output_format == "json":
                sheet_content = {
                    "sheet_name": sheet_name,
                    "data": df.to_dict(orient="records"),
                }
            else:
                # Convert to markdown table
                sheet_content = f"## Sheet: {sheet_name}\n\n"
                sheet_content += df.to_markdown(index=False)

            sheets_content.append(sheet_content)

        return sheets_content
