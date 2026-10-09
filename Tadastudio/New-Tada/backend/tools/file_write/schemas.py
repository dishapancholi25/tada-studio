"""Schema definitions for file write tool inputs.

Defines the Pydantic models for tool input validation.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class FileWriteInput(BaseModel):
    """Input schema for file write tool.

    Attributes:
        filename: The name of the file to create (with extension)
        content: File content - text string OR base64-encoded binary
        content_type: Type of content - "text" for plain text, "base64" for binary
        subdirectory: Optional subdirectory within the output directory
        css: Optional custom CSS for PDF generation (only used for .pdf files)
        template: Optional template name for styled document generation
    """

    filename: str = Field(
        ...,
        description="Name of the file to create. The extension determines the output format: "
        ".pdf, .docx, .xlsx, .pptx for styled documents; .txt, .md, .json, .csv for text files.",
    )
    content: str = Field(
        ...,
        description=(
            "The content to write. Format depends on the file extension:\n\n"
            "**PDF (.pdf) / Word (.docx):** Provide well-structured markdown. Use # for title, "
            "## for sections, ### for subsections. Include markdown tables with | pipes |, "
            "bullet lists, numbered lists, **bold**, *italic*, `code`, and > blockquotes. "
            "All markdown elements will be professionally styled.\n\n"
            "**Excel (.xlsx):** Two options:\n"
            "  Option A - Markdown tables: Include one or more markdown tables. "
            "Each table becomes a sheet. Precede a table with a ## heading to name the sheet.\n"
            "  Option B - Structured JSON: "
            '{"sheets": [{"name": "Sales", "headers": ["Product", "Revenue", "Growth"], '
            '"rows": [["Widget A", "$1,234.56", "12.3%"], ["Widget B", "$987.65", "8.1%"]], '
            '"column_widths": [20, 15, 12], '
            '"number_formats": {"Revenue": "#,##0.00"}}]}\n"'
            "Numbers and percentages are auto-detected and formatted. "
            "Each sheet gets frozen headers, auto-filters, and alternating row colors.\n\n"
            "**PowerPoint (.pptx):** Provide markdown where:\n"
            "  # Heading = Title/cover slide (next plain text line becomes subtitle)\n"
            "  ## Heading = New content slide\n"
            "  - Bullet lists = Slide bullet points\n"
            "  | Tables | = Slide tables\n"
            "  > Blockquotes = Highlighted quote boxes\n"
            "  --- = Explicit slide break\n"
            "Example: '# Q1 Report\\nConfidential - April 2026\\n\\n"
            "## Revenue Overview\\n- Total revenue: $4.2M\\n- Growth: 23% YoY\\n\\n"
            "## Regional Breakdown\\n| Region | Revenue |\\n|---|---|\\n| NA | $2.1M |'\n\n"
            "**Text files (.txt, .md, .json, .csv, .yaml):** Provide content directly as text.\n\n"
            "**Binary files:** Provide base64-encoded content with content_type='base64'."
        ),
    )
    content_type: Literal["text", "base64"] = Field(
        default="text",
        description="Content type: 'text' for plain text and document files, 'base64' for binary files",
    )
    subdirectory: Optional[str] = Field(
        default=None,
        description="Optional subdirectory within the output directory",
    )
    css: Optional[str] = Field(
        default=None,
        description="Optional custom CSS for PDF styling. Only used for .pdf files. "
        "Overrides the template styles if provided.",
    )
    template: Optional[str] = Field(
        default=None,
        description=(
            "Style template for document generation (PDF, DOCX, XLSX, PPTX). Options:\n"
            "- 'modern': Clean and minimal. Dark headers, subtle borders, lots of whitespace. "
            "Best for general-purpose documents and reports.\n"
            "- 'executive': Formal and conservative. Navy blue palette, serif headings, "
            "'Confidential' footer. Best for board reports, executive summaries, formal proposals.\n"
            "- 'report': Technical report style. Blue accent, page numbers, dark code blocks, "
            "section headers with underlines. Best for technical docs, analysis reports.\n"
            "- 'invoice': Financial document style. Green accent, right-aligned numbers, "
            "bold totals row. Best for invoices, financial summaries, pricing tables.\n"
            "- 'minimal': Maximum readability. Wide margins, understated styling, no color. "
            "Best for letters, memos, simple documents.\n"
            "Defaults to 'modern' if not specified."
        ),
    )
