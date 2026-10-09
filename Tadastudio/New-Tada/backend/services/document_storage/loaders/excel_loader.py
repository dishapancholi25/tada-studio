"""Excel document loader."""

import logging
from typing import List

from langchain_core.documents import Document

from ..exceptions import LoaderNotAvailableError
from .base import BaseLoader


logger = logging.getLogger(__name__)


class ExcelLoader(BaseLoader):
    """Excel document loader (.xlsx files)."""

    SUPPORTED_EXTENSIONS = {".xlsx"}

    def load(self, file_path: str) -> List[Document]:
        """Load Excel document and convert to markdown tables.

        Args:
            file_path: Path to Excel file

        Returns:
            List of Document objects (one per sheet)

        Raises:
            LoaderNotAvailableError: If pandas/openpyxl not installed
            Exception: If loading fails
        """
        try:
            import pandas as pd

            logger.info("[EXCEL-LOADER] Using pandas to read Excel file")

            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            documents = []

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)

                # Convert DataFrame to markdown table
                text = f"# Sheet: {sheet_name}\n\n"

                # Add column headers
                text += "| " + " | ".join(str(col) for col in df.columns) + " |\n"
                text += "|" + " --- |" * len(df.columns) + "\n"

                # Add data rows
                for _, row in df.iterrows():
                    text += (
                        "| "
                        + " | ".join(str(val) if pd.notna(val) else "" for val in row)
                        + " |\n"
                    )

                # Create Document object
                doc = Document(
                    page_content=text,
                    metadata={
                        "source": file_path,
                        "sheet_name": sheet_name,
                        "row_count": len(df),
                        "column_count": len(df.columns),
                    },
                )
                documents.append(doc)

            logger.info(
                f"[EXCEL-LOADER] Loaded {len(documents)} sheets from Excel file"
            )
            return documents

        except ImportError:
            error_msg = "pip install pandas openpyxl"
            logger.error(
                f"[EXCEL-LOADER] pandas/openpyxl not available. Install with: {error_msg}"
            )
            raise LoaderNotAvailableError("Excel loader", error_msg)

        except Exception as e:
            logger.error(f"[EXCEL-LOADER] Error reading Excel file: {e}")
            raise

    @staticmethod
    def supports(file_extension: str) -> bool:
        """Check if Excel loader supports the file extension.

        Args:
            file_extension: File extension (e.g., '.xlsx')

        Returns:
            True if extension is .xlsx
        """
        return file_extension.lower() in ExcelLoader.SUPPORTED_EXTENSIONS
