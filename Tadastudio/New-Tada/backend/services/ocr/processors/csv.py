"""CSV processor for structured data extraction optimized for LLM consumption."""

import csv
import io
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from ..base import OCRProcessor
from ..config import (
    CSV_DELIMITERS,
    CSV_LARGE_FILE_THRESHOLD_ROWS,
    DEFAULT_CSV_CHUNK_SIZE,
    MAX_CSV_ROWS_FOR_FULL_OUTPUT,
    SUPPORTED_CSV_EXTENSIONS,
)
from ..models import CSVColumnInfo, CSVMetadata, OCRRequest, OCRResponse
from ..utils import build_error_response, build_success_response


logger = logging.getLogger(__name__)


class CSVProcessor(OCRProcessor):
    """Processor for CSV files optimized for LLM consumption."""

    def __init__(self):
        """Initialize CSV processor (no AI client needed)."""
        super().__init__(client=None)

    def supports_file_type(self, file_ext: str) -> bool:
        """Check if this processor supports the given file type."""
        return file_ext.lower() in SUPPORTED_CSV_EXTENSIONS

    def process(self, request: OCRRequest) -> OCRResponse:
        """
        Process CSV file and return LLM-optimized output.

        Args:
            request: OCR request with CSV file

        Returns:
            OCR response with formatted CSV content
        """
        try:
            # Read file content
            file_bytes, file_path = self._get_file_content(request)
            filename = os.path.basename(file_path) if file_path else "data.csv"

            # Detect encoding
            encoding = self._detect_encoding(file_bytes)
            content = file_bytes.decode(encoding)

            # Detect delimiter
            delimiter = self._detect_delimiter(content)

            # Parse CSV
            rows = self._parse_csv(content, delimiter)
            if not rows:
                return build_error_response("CSV file is empty", "csv_processor")

            # Detect header
            has_header = self._detect_header(rows)
            if has_header:
                headers = rows[0]
                data_rows = rows[1:]
            else:
                headers = [f"Column_{i + 1}" for i in range(len(rows[0]))]
                data_rows = rows

            # Infer column types and gather statistics
            column_info = self._analyze_columns(headers, data_rows)

            # Build metadata
            metadata = CSVMetadata(
                filename=filename,
                row_count=len(data_rows),
                column_count=len(headers),
                columns=column_info,
                has_header=has_header,
                detected_delimiter=delimiter,
                detected_encoding=encoding,
                file_size_bytes=len(file_bytes),
                is_chunked=len(data_rows) > MAX_CSV_ROWS_FOR_FULL_OUTPUT,
            )

            # Format output (default to markdown)
            output = self._format_output(
                headers=headers,
                rows=data_rows,
                metadata=metadata,
                output_format="markdown",
                include_schema=True,
                include_stats=True,
            )

            logger.info(
                f"[CSV] Processed {filename}: {metadata.row_count} rows, "
                f"{metadata.column_count} columns, delimiter='{delimiter}'"
            )

            return build_success_response(
                text=output,
                extraction_method="csv_processor",
                tokens_used=0,
            )

        except Exception as e:
            logger.error(f"[CSV] Error processing CSV: {e}", exc_info=True)
            return build_error_response(str(e), "csv_processor")

    def process_with_config(
        self,
        request: OCRRequest,
        delimiter: str = "auto",
        has_header: str = "auto",
        output_format: str = "markdown",
        max_rows: Optional[int] = None,
        chunk_size: int = DEFAULT_CSV_CHUNK_SIZE,
        include_schema: bool = True,
        include_stats: bool = True,
        encoding: str = "auto",
    ) -> OCRResponse:
        """
        Process CSV file with custom configuration.

        Args:
            request: OCR request with CSV file
            delimiter: Delimiter (auto, comma, semicolon, tab, pipe)
            has_header: Header detection (auto, true, false)
            output_format: Output format (markdown, json, row_by_row, summary)
            max_rows: Maximum rows to process
            chunk_size: Rows per chunk for large files
            include_schema: Include column type inference
            include_stats: Include basic statistics
            encoding: File encoding (auto or specific)

        Returns:
            OCR response with formatted CSV content
        """
        try:
            # Read file content
            file_bytes, file_path = self._get_file_content(request)
            filename = os.path.basename(file_path) if file_path else "data.csv"

            # Detect or use specified encoding
            if encoding == "auto":
                encoding = self._detect_encoding(file_bytes)
            content = self._decode_content(file_bytes, encoding)

            # Detect or use specified delimiter
            if delimiter == "auto":
                detected_delimiter = self._detect_delimiter(content)
            else:
                detected_delimiter = CSV_DELIMITERS.get(delimiter, delimiter)

            # Parse CSV
            rows = self._parse_csv(content, detected_delimiter)
            if not rows:
                return build_error_response("CSV file is empty", "csv_processor")

            # Detect or use specified header setting
            if has_header == "auto":
                detected_header = self._detect_header(rows)
            else:
                detected_header = has_header.lower() == "true"

            if detected_header:
                headers = rows[0]
                data_rows = rows[1:]
            else:
                headers = [f"Column_{i + 1}" for i in range(len(rows[0]))]
                data_rows = rows

            # Apply max_rows limit
            if max_rows is not None:
                data_rows = data_rows[:max_rows]

            # Analyze columns
            column_info = (
                self._analyze_columns(headers, data_rows) if include_schema else []
            )

            # Build metadata
            total_rows = len(rows) - (1 if detected_header else 0)
            is_chunked = len(data_rows) > MAX_CSV_ROWS_FOR_FULL_OUTPUT
            metadata = CSVMetadata(
                filename=filename,
                row_count=total_rows,
                column_count=len(headers),
                columns=column_info,
                has_header=detected_header,
                detected_delimiter=detected_delimiter,
                detected_encoding=encoding,
                file_size_bytes=len(file_bytes),
                is_chunked=is_chunked,
                total_chunks=(total_rows // chunk_size) + 1 if is_chunked else None,
            )

            # Auto-select summary format for very large files
            if (
                output_format == "markdown"
                and total_rows > CSV_LARGE_FILE_THRESHOLD_ROWS
            ):
                logger.info(
                    f"[CSV] Large file ({total_rows} rows), switching to summary format"
                )
                output_format = "summary"

            # Format output
            output = self._format_output(
                headers=headers,
                rows=data_rows,
                metadata=metadata,
                output_format=output_format,
                include_schema=include_schema,
                include_stats=include_stats,
                chunk_size=chunk_size,
            )

            logger.info(
                f"[CSV] Processed {filename}: {metadata.row_count} rows, "
                f"{metadata.column_count} columns, format={output_format}"
            )

            return build_success_response(
                text=output,
                extraction_method="csv_processor",
                tokens_used=0,
            )

        except Exception as e:
            logger.error(f"[CSV] Error processing CSV: {e}", exc_info=True)
            return build_error_response(str(e), "csv_processor")

    def _get_file_content(self, request: OCRRequest) -> Tuple[bytes, Optional[str]]:
        """Get file content from request."""
        if request.file_path:
            with open(request.file_path, "rb") as f:
                return f.read(), request.file_path
        elif request.file_bytes:
            return request.file_bytes, None
        else:
            raise ValueError("Either file_path or file_bytes must be provided")

    def _detect_encoding(self, file_bytes: bytes) -> str:
        """Detect file encoding using chardet or fallback."""
        try:
            import chardet

            # Sample first 100KB for large files
            sample = file_bytes[:102400] if len(file_bytes) > 102400 else file_bytes
            result = chardet.detect(sample)
            encoding = result.get("encoding", "utf-8") or "utf-8"
            confidence = result.get("confidence", 0.0)

            logger.debug(
                f"[CSV] Detected encoding: {encoding} (confidence: {confidence:.2f})"
            )

            # Normalize common encoding names
            encoding_map = {
                "ascii": "utf-8",
                "ISO-8859-1": "latin-1",
                "Windows-1252": "cp1252",
            }
            return encoding_map.get(encoding, encoding)

        except ImportError:
            logger.debug("[CSV] chardet not available, defaulting to utf-8")
            return "utf-8"
        except Exception as e:
            logger.warning(f"[CSV] Encoding detection failed: {e}, defaulting to utf-8")
            return "utf-8"

    def _decode_content(self, file_bytes: bytes, encoding: str) -> str:
        """Decode file bytes with fallback chain."""
        encodings_to_try = [encoding, "utf-8", "latin-1", "cp1252"]
        for enc in encodings_to_try:
            try:
                return file_bytes.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        # Last resort: decode with errors replaced
        return file_bytes.decode("utf-8", errors="replace")

    def _detect_delimiter(self, content: str) -> str:
        """Detect CSV delimiter using csv.Sniffer."""
        try:
            # Use first 8KB for sniffing
            sample = content[:8192]
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=",;\t|")
            logger.debug(f"[CSV] Detected delimiter: '{dialect.delimiter}'")
            return dialect.delimiter
        except csv.Error:
            # Default to comma if sniffing fails
            logger.debug("[CSV] Delimiter detection failed, defaulting to comma")
            return ","

    def _parse_csv(self, content: str, delimiter: str) -> List[List[str]]:
        """Parse CSV content into rows."""
        rows = []
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        for row in reader:
            # Skip completely empty rows
            if any(cell.strip() for cell in row):
                rows.append(row)
        return rows

    def _detect_header(self, rows: List[List[str]]) -> bool:
        """Detect if first row is a header using heuristics."""
        if len(rows) < 2:
            return False

        first_row = rows[0]
        second_row = rows[1]

        # Heuristic 1: First row has more non-numeric values than second row
        first_row_numeric = sum(1 for cell in first_row if self._is_numeric(cell))
        second_row_numeric = sum(1 for cell in second_row if self._is_numeric(cell))

        if first_row_numeric < second_row_numeric:
            return True

        # Heuristic 2: First row values are all unique
        if len(set(first_row)) == len(first_row) and len(first_row) > 1:
            # Check if second row has duplicates (common in data)
            if len(set(second_row)) < len(second_row):
                return True

        # Heuristic 3: First row looks like headers (short, no special chars)
        avg_first_len = sum(len(cell) for cell in first_row) / len(first_row)
        avg_other_len = sum(len(cell) for row in rows[1:6] for cell in row) / max(
            sum(len(row) for row in rows[1:6]), 1
        )
        if avg_first_len < avg_other_len * 0.5:
            return True

        return False

    def _is_numeric(self, value: str) -> bool:
        """Check if a value is numeric."""
        value = value.strip()
        if not value:
            return False
        try:
            float(value.replace(",", ""))
            return True
        except ValueError:
            return False

    def _infer_type(self, values: List[str]) -> str:
        """Infer column type from values."""
        non_empty = [v.strip() for v in values if v.strip()]
        if not non_empty:
            return "string"

        # Sample up to 100 values
        sample = non_empty[:100]

        # Check for boolean
        bool_values = {"true", "false", "yes", "no", "1", "0", "t", "f", "y", "n"}
        if all(v.lower() in bool_values for v in sample):
            return "boolean"

        # Check for integer
        int_count = 0
        for v in sample:
            try:
                int(v.replace(",", ""))
                int_count += 1
            except ValueError:
                pass
        if int_count == len(sample):
            return "integer"

        # Check for decimal
        decimal_count = 0
        for v in sample:
            try:
                float(v.replace(",", ""))
                decimal_count += 1
            except ValueError:
                pass
        if decimal_count == len(sample):
            return "decimal"

        # Check for date
        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}",  # ISO date
            r"^\d{2}/\d{2}/\d{4}",  # MM/DD/YYYY
            r"^\d{2}-\d{2}-\d{4}",  # MM-DD-YYYY
        ]
        date_count = sum(
            1 for v in sample if any(re.match(p, v) for p in date_patterns)
        )
        if date_count > len(sample) * 0.8:
            return "date"

        return "string"

    def _analyze_columns(
        self, headers: List[str], rows: List[List[str]]
    ) -> List[CSVColumnInfo]:
        """Analyze columns for type, samples, and statistics."""
        column_info = []

        for i, header in enumerate(headers):
            values = [row[i] if i < len(row) else "" for row in rows]
            non_empty = [v for v in values if v.strip()]

            # Get sample values (up to 3 unique)
            unique_samples = list(dict.fromkeys(non_empty[:20]))[:3]

            column_info.append(
                CSVColumnInfo(
                    name=header,
                    inferred_type=self._infer_type(values),
                    sample_values=unique_samples,
                    null_count=len(values) - len(non_empty),
                    unique_count=len(set(non_empty))
                    if len(non_empty) <= 1000
                    else None,
                )
            )

        return column_info

    def parse_structured(
        self,
        request: OCRRequest,
        delimiter: str = "auto",
        has_header: str = "auto",
        max_rows: Optional[int] = None,
        encoding: str = "auto",
    ) -> Dict[str, Any]:
        """
        Parse CSV and return structured data for field extraction.

        Returns a dict with:
        - parsed_rows: List of dicts (header -> value) for each row
        - parsed_columns: Dict of header -> value for the first data row
        - column_names: List of header names

        Args:
            request: OCR request with CSV file
            delimiter: Delimiter (auto or specific)
            has_header: Header detection (auto, true, false)
            max_rows: Maximum rows to parse
            encoding: File encoding (auto or specific)

        Returns:
            Dictionary with structured CSV data
        """
        try:
            file_bytes, _ = self._get_file_content(request)

            if encoding == "auto":
                encoding = self._detect_encoding(file_bytes)
            content = self._decode_content(file_bytes, encoding)

            if delimiter == "auto":
                detected_delimiter = self._detect_delimiter(content)
            else:
                detected_delimiter = CSV_DELIMITERS.get(delimiter, delimiter)

            rows = self._parse_csv(content, detected_delimiter)
            if not rows:
                return {"parsed_rows": [], "parsed_columns": {}, "column_names": []}

            if has_header == "auto":
                detected_header = self._detect_header(rows)
            else:
                detected_header = has_header.lower() == "true"

            if detected_header:
                headers = rows[0]
                data_rows = rows[1:]
            else:
                headers = [f"Column_{i + 1}" for i in range(len(rows[0]))]
                data_rows = rows

            if max_rows is not None:
                data_rows = data_rows[:max_rows]

            parsed_rows = [
                {
                    headers[i]: row[i] if i < len(row) else ""
                    for i in range(len(headers))
                }
                for row in data_rows
            ]
            parsed_columns = parsed_rows[0] if parsed_rows else {}

            return {
                "parsed_rows": parsed_rows,
                "parsed_columns": parsed_columns,
                "column_names": headers,
            }

        except Exception as e:
            logger.error(f"[CSV] Error parsing structured data: {e}", exc_info=True)
            return {"parsed_rows": [], "parsed_columns": {}, "column_names": []}

    def _format_output(
        self,
        headers: List[str],
        rows: List[List[str]],
        metadata: CSVMetadata,
        output_format: str,
        include_schema: bool,
        include_stats: bool,
        chunk_size: int = DEFAULT_CSV_CHUNK_SIZE,
    ) -> str:
        """Format CSV data for LLM consumption."""
        if output_format == "json":
            return self._format_as_json(headers, rows, metadata, include_schema)
        elif output_format == "row_by_row":
            return self._format_row_by_row(headers, rows, metadata, chunk_size)
        elif output_format == "summary":
            return self._format_as_summary(headers, rows, metadata, include_stats)
        elif output_format == "raw":
            return self._format_as_raw(headers, rows, metadata)
        else:  # markdown (default)
            return self._format_as_markdown(
                headers, rows, metadata, include_schema, include_stats
            )

    def _format_as_markdown(
        self,
        headers: List[str],
        rows: List[List[str]],
        metadata: CSVMetadata,
        include_schema: bool,
        include_stats: bool,
    ) -> str:
        """Format as markdown table (best for general use)."""
        output_parts = []

        # Header section
        output_parts.append(f"## CSV Data: {metadata.filename or 'data.csv'}\n")

        # File info
        output_parts.append("### File Information")
        output_parts.append(f"- **Rows:** {metadata.row_count}")
        output_parts.append(f"- **Columns:** {metadata.column_count}")
        output_parts.append(f"- **Encoding:** {metadata.detected_encoding}")
        delimiter_name = {",": "Comma", ";": "Semicolon", "\t": "Tab", "|": "Pipe"}.get(
            metadata.detected_delimiter, metadata.detected_delimiter
        )
        output_parts.append(f"- **Delimiter:** {delimiter_name}")
        output_parts.append("")

        # Schema section
        if include_schema and metadata.columns:
            output_parts.append("### Schema")
            output_parts.append("| Column | Type | Sample Values |")
            output_parts.append("|--------|------|---------------|")
            for col in metadata.columns:
                samples = ", ".join(col.sample_values[:2]) if col.sample_values else "-"
                output_parts.append(f"| {col.name} | {col.inferred_type} | {samples} |")
            output_parts.append("")

        # Data section
        output_parts.append("### Data")

        # Limit rows for markdown output
        display_rows = rows[:MAX_CSV_ROWS_FOR_FULL_OUTPUT]
        truncated = len(rows) > MAX_CSV_ROWS_FOR_FULL_OUTPUT

        # Build table
        output_parts.append("| " + " | ".join(headers) + " |")
        output_parts.append("|" + "|".join(["---"] * len(headers)) + "|")

        for row in display_rows:
            # Pad row if needed
            padded_row = row + [""] * (len(headers) - len(row))
            # Escape pipe characters in cells
            escaped_row = [
                cell.replace("|", "\\|") for cell in padded_row[: len(headers)]
            ]
            output_parts.append("| " + " | ".join(escaped_row) + " |")

        if truncated:
            output_parts.append("")
            output_parts.append(
                f"*... showing {MAX_CSV_ROWS_FOR_FULL_OUTPUT} of {len(rows)} rows. "
                f"Use `row_by_row` or `summary` format for full data.*"
            )

        return "\n".join(output_parts)

    def _format_as_json(
        self,
        headers: List[str],
        rows: List[List[str]],
        metadata: CSVMetadata,
        include_schema: bool,
    ) -> str:
        """Format as JSON (best for programmatic LLM tasks)."""
        output: Dict[str, Any] = {
            "metadata": {
                "filename": metadata.filename,
                "row_count": metadata.row_count,
                "column_count": metadata.column_count,
                "encoding": metadata.detected_encoding,
                "delimiter": metadata.detected_delimiter,
                "has_header": metadata.has_header,
            }
        }

        if include_schema and metadata.columns:
            output["metadata"]["columns"] = [
                {
                    "name": col.name,
                    "type": col.inferred_type,
                    "null_count": col.null_count,
                    "unique_count": col.unique_count,
                }
                for col in metadata.columns
            ]

        # Convert rows to list of dicts
        data = []
        for row in rows[:MAX_CSV_ROWS_FOR_FULL_OUTPUT]:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i] if i < len(row) else ""
            data.append(row_dict)

        output["data"] = data

        if len(rows) > MAX_CSV_ROWS_FOR_FULL_OUTPUT:
            output["metadata"]["truncated"] = True
            output["metadata"]["rows_shown"] = MAX_CSV_ROWS_FOR_FULL_OUTPUT

        return json.dumps(output, indent=2)

    def _format_row_by_row(
        self,
        headers: List[str],
        rows: List[List[str]],
        metadata: CSVMetadata,
        chunk_size: int,
    ) -> str:
        """Format row by row with headers repeated (best for large files)."""
        output_parts = []

        output_parts.append(
            f"## CSV Data: {metadata.filename or 'data.csv'} (Row-by-Row Format)\n"
        )
        output_parts.append(
            f"**Total Rows:** {metadata.row_count} | **Columns:** {', '.join(headers)}\n"
        )
        output_parts.append("---\n")

        # Process up to chunk_size rows
        display_rows = rows[:chunk_size]

        for idx, row in enumerate(display_rows, start=1):
            output_parts.append(f"**Row {idx}:**")
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ""
                output_parts.append(f"- {header}: {value}")
            output_parts.append("")

        if len(rows) > chunk_size:
            output_parts.append("---")
            output_parts.append(
                f"*Showing rows 1-{chunk_size} of {len(rows)}. "
                f"Adjust chunk_size for more rows.*"
            )

        return "\n".join(output_parts)

    def _format_as_summary(
        self,
        headers: List[str],
        rows: List[List[str]],
        metadata: CSVMetadata,
        include_stats: bool,
    ) -> str:
        """Format as summary (best for very large files)."""
        output_parts = []

        output_parts.append(f"## CSV Summary: {metadata.filename or 'data.csv'}\n")

        # Overview
        output_parts.append("### Overview")
        output_parts.append(f"- **Total Rows:** {metadata.row_count:,}")
        output_parts.append(f"- **Total Columns:** {metadata.column_count}")
        output_parts.append(
            f"- **File Size:** {metadata.file_size_bytes / 1024:.1f} KB"
        )
        output_parts.append(f"- **Encoding:** {metadata.detected_encoding}")
        output_parts.append("")

        # Column schema
        output_parts.append("### Column Schema")
        output_parts.append("| # | Column Name | Type | Non-Null | Sample Values |")
        output_parts.append("|---|-------------|------|----------|---------------|")

        for i, col in enumerate(metadata.columns, start=1):
            non_null_pct = (
                ((metadata.row_count - col.null_count) / metadata.row_count * 100)
                if metadata.row_count > 0
                else 0
            )
            samples = ", ".join(col.sample_values[:2]) if col.sample_values else "-"
            output_parts.append(
                f"| {i} | {col.name} | {col.inferred_type} | {non_null_pct:.0f}% | {samples} |"
            )
        output_parts.append("")

        # Statistics for numeric columns
        if include_stats:
            numeric_cols = [
                col
                for col in metadata.columns
                if col.inferred_type in ("integer", "decimal")
            ]
            if numeric_cols:
                output_parts.append("### Numeric Column Statistics")
                output_parts.append("| Column | Min | Max | Sample Mean |")
                output_parts.append("|--------|-----|-----|-------------|")

                for col in numeric_cols:
                    col_idx = headers.index(col.name)
                    values = []
                    for row in rows:
                        if col_idx < len(row) and row[col_idx].strip():
                            try:
                                values.append(float(row[col_idx].replace(",", "")))
                            except ValueError:
                                pass
                    if values:
                        min_val = min(values)
                        max_val = max(values)
                        mean_val = sum(values) / len(values)
                        output_parts.append(
                            f"| {col.name} | {min_val:,.2f} | {max_val:,.2f} | {mean_val:,.2f} |"
                        )
                output_parts.append("")

        # Sample data (first 5 rows)
        output_parts.append("### Sample Data (First 5 Rows)")
        output_parts.append("| " + " | ".join(headers) + " |")
        output_parts.append("|" + "|".join(["---"] * len(headers)) + "|")

        for row in rows[:5]:
            padded_row = row + [""] * (len(headers) - len(row))
            escaped_row = [
                cell.replace("|", "\\|") for cell in padded_row[: len(headers)]
            ]
            output_parts.append("| " + " | ".join(escaped_row) + " |")

        output_parts.append("")

        # Last 5 rows
        if len(rows) > 10:
            output_parts.append("### Sample Data (Last 5 Rows)")
            output_parts.append("| " + " | ".join(headers) + " |")
            output_parts.append("|" + "|".join(["---"] * len(headers)) + "|")

            for row in rows[-5:]:
                padded_row = row + [""] * (len(headers) - len(row))
                escaped_row = [
                    cell.replace("|", "\\|") for cell in padded_row[: len(headers)]
                ]
                output_parts.append("| " + " | ".join(escaped_row) + " |")

        output_parts.append("")
        output_parts.append(
            "*This is a summary view. Use `row_by_row` format with chunking for full data access.*"
        )

        return "\n".join(output_parts)

    def _format_as_raw(
        self,
        headers: List[str],
        rows: List[List[str]],
        metadata: CSVMetadata,
    ) -> str:
        """Format as raw CSV content with no additional formatting or metadata."""
        output_parts = []
        delimiter = metadata.detected_delimiter

        # Include header row if present
        if metadata.has_header:
            output_parts.append(delimiter.join(headers))

        # Include data rows
        for row in rows:
            padded_row = row + [""] * (len(headers) - len(row))
            output_parts.append(delimiter.join(padded_row[: len(headers)]))

        return "\n".join(output_parts)
