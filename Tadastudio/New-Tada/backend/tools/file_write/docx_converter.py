"""DOCX generation utilities for the file write tool.

Converts markdown content to professionally styled DOCX using python-docx.
Supports multiple templates with consistent branding.
"""

import io
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DOCX TEMPLATE STYLES
# =============================================================================

# Template color palettes: (primary, secondary, accent, light_bg, text, muted)
TEMPLATE_PALETTES = {
    "modern": {
        "primary": "111111",
        "secondary": "333333",
        "accent": "0066CC",
        "light_bg": "F6F8FA",
        "border": "E1E4E8",
        "text": "2D2D2D",
        "muted": "6B7280",
        "table_header_bg": "F8F9FA",
        "table_header_fg": "333333",
    },
    "executive": {
        "primary": "1A3A5C",
        "secondary": "2C5282",
        "accent": "1A3A5C",
        "light_bg": "F7FAFC",
        "border": "D4DCE6",
        "text": "2D3748",
        "muted": "718096",
        "table_header_bg": "1A3A5C",
        "table_header_fg": "FFFFFF",
    },
    "report": {
        "primary": "1E40AF",
        "secondary": "1E3A5F",
        "accent": "3B82F6",
        "light_bg": "EFF6FF",
        "border": "BFDBFE",
        "text": "1F2937",
        "muted": "6B7280",
        "table_header_bg": "1E40AF",
        "table_header_fg": "FFFFFF",
    },
    "invoice": {
        "primary": "111827",
        "secondary": "059669",
        "accent": "059669",
        "light_bg": "ECFDF5",
        "border": "E5E7EB",
        "text": "374151",
        "muted": "6B7280",
        "table_header_bg": "F9FAFB",
        "table_header_fg": "374151",
    },
    "minimal": {
        "primary": "000000",
        "secondary": "222222",
        "accent": "0055AA",
        "light_bg": "F5F5F5",
        "border": "EEEEEE",
        "text": "333333",
        "muted": "999999",
        "table_header_bg": "FFFFFF",
        "table_header_fg": "333333",
    },
}


def _parse_markdown_blocks(markdown_content: str) -> list:
    """Parse markdown into structured blocks for DOCX rendering.

    Returns a list of block dicts with type and content.
    """
    lines = markdown_content.split("\n")
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(
                {"type": "code", "content": "\n".join(code_lines), "language": lang}
            )
            i += 1
            continue

        # Table (line with pipes)
        if "|" in line and line.strip().startswith("|"):
            table_lines = []
            while (
                i < len(lines) and "|" in lines[i] and lines[i].strip().startswith("|")
            ):
                table_lines.append(lines[i])
                i += 1
            blocks.append({"type": "table", "lines": table_lines})
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            blocks.append(
                {
                    "type": "heading",
                    "level": level,
                    "content": heading_match.group(2).strip(),
                }
            )
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line.strip()):
            blocks.append({"type": "hr"})
            i += 1
            continue

        # Blockquote
        if line.strip().startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            blocks.append({"type": "blockquote", "content": "\n".join(quote_lines)})
            continue

        # Unordered list
        list_match = re.match(r"^(\s*)([-*+])\s+(.+)$", line)
        if list_match:
            items = []
            while i < len(lines):
                item_match = re.match(r"^(\s*)([-*+])\s+(.+)$", lines[i])
                if item_match:
                    indent = len(item_match.group(1))
                    items.append({"text": item_match.group(3), "indent": indent})
                    i += 1
                elif lines[i].strip() == "":
                    i += 1
                    break
                else:
                    break
            blocks.append({"type": "ul", "items": items})
            continue

        # Ordered list
        ol_match = re.match(r"^(\s*)\d+[.)]\s+(.+)$", line)
        if ol_match:
            items = []
            while i < len(lines):
                item_match = re.match(r"^(\s*)\d+[.)]\s+(.+)$", lines[i])
                if item_match:
                    indent = len(item_match.group(1))
                    items.append({"text": item_match.group(2), "indent": indent})
                    i += 1
                elif lines[i].strip() == "":
                    i += 1
                    break
                else:
                    break
            blocks.append({"type": "ol", "items": items})
            continue

        # Empty line
        if line.strip() == "":
            i += 1
            continue

        # Paragraph (collect consecutive non-empty lines)
        para_lines = []
        while (
            i < len(lines)
            and lines[i].strip() != ""
            and not lines[i].strip().startswith("#")
        ):
            # Break if next line is a list, table, code block, or heading
            if re.match(r"^(\s*)([-*+])\s+", lines[i]):
                break
            if re.match(r"^(\s*)\d+[.)]\s+", lines[i]):
                break
            if lines[i].strip().startswith("|") and "|" in lines[i]:
                break
            if lines[i].strip().startswith("```"):
                break
            if lines[i].strip().startswith(">"):
                break
            if re.match(r"^(#{1,6})\s+", lines[i]):
                break
            if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", lines[i].strip()):
                break
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            blocks.append({"type": "paragraph", "content": " ".join(para_lines)})

    return blocks


def _parse_table(table_lines: list) -> tuple:
    """Parse markdown table lines into headers and rows.

    Returns (headers: list[str], rows: list[list[str]]).
    """
    if len(table_lines) < 2:
        return [], []

    def split_row(line):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        return cells

    headers = split_row(table_lines[0])
    # Skip separator line (line with dashes)
    rows = []
    for line in table_lines[2:]:
        if line.strip():
            rows.append(split_row(line))

    return headers, rows


def _add_formatted_text(paragraph, text: str, palette: dict):
    """Add text with inline markdown formatting (bold, italic, code, links) to a paragraph."""
    from docx.shared import Pt, RGBColor

    # Split text by inline formatting patterns
    # Process: **bold**, *italic*, `code`, [link](url)
    pattern = r"(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\[(.+?)\]\((.+?)\))"
    parts = re.split(pattern, text)

    i = 0
    while i < len(parts):
        part = parts[i]
        if part is None:
            i += 1
            continue

        # Check if this is a full match group
        if i + 7 < len(parts):
            full_match = parts[i]
            bold_italic = parts[i + 1] if i + 1 < len(parts) else None
            bold = parts[i + 2] if i + 2 < len(parts) else None
            italic = parts[i + 3] if i + 3 < len(parts) else None
            code = parts[i + 4] if i + 4 < len(parts) else None
            link_text = parts[i + 5] if i + 5 < len(parts) else None

            if full_match and (bold_italic or bold or italic or code or link_text):
                if bold_italic:
                    run = paragraph.add_run(bold_italic)
                    run.bold = True
                    run.italic = True
                elif bold:
                    run = paragraph.add_run(bold)
                    run.bold = True
                elif italic:
                    run = paragraph.add_run(italic)
                    run.italic = True
                elif code:
                    run = paragraph.add_run(code)
                    run.font.name = "Consolas"
                    run.font.size = Pt(9)
                    run.font.color.rgb = RGBColor.from_string(palette["text"])
                elif link_text:
                    run = paragraph.add_run(link_text)
                    run.font.color.rgb = RGBColor.from_string(palette["accent"])
                    run.underline = True
                i += 7
                continue

        # Plain text
        if part and not re.match(pattern, part):
            paragraph.add_run(part)
        i += 1


def markdown_to_docx(
    markdown_content: str,
    template: Optional[str] = None,
) -> bytes:
    """Convert markdown content to a professionally styled DOCX binary.

    Args:
        markdown_content: The markdown text to convert.
        template: Optional template name ('modern', 'executive', 'report',
                 'invoice', 'minimal'). Defaults to 'modern'.

    Returns:
        DOCX file content as bytes.

    Raises:
        ValueError: If markdown content is empty.
        RuntimeError: If DOCX generation fails.
    """
    if not markdown_content or not markdown_content.strip():
        raise ValueError("Markdown content cannot be empty")

    template_name = template if template in TEMPLATE_PALETTES else "modern"
    palette = TEMPLATE_PALETTES[template_name]

    logger.info(
        "[DOCX-CONVERTER] Converting markdown to DOCX (template=%s)", template_name
    )

    try:
        from docx import Document
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.shared import Cm, Pt, RGBColor

        doc = Document()

        # --- Configure default styles ---
        style = doc.styles["Normal"]
        font = style.font
        font.name = "Calibri"
        font.size = Pt(10.5)
        font.color.rgb = RGBColor.from_string(palette["text"])
        para_format = style.paragraph_format
        para_format.space_after = Pt(6)
        para_format.line_spacing = 1.15

        # Configure heading styles
        heading_configs = [
            ("Heading 1", Pt(24), palette["primary"], True, Pt(0), Pt(12)),
            ("Heading 2", Pt(18), palette["secondary"], True, Pt(18), Pt(8)),
            ("Heading 3", Pt(14), palette["secondary"], True, Pt(14), Pt(6)),
            ("Heading 4", Pt(12), palette["text"], True, Pt(12), Pt(4)),
        ]

        for style_name, size, color, bold, space_before, space_after in heading_configs:
            if style_name in doc.styles:
                h_style = doc.styles[style_name]
                h_style.font.name = "Calibri"
                h_style.font.size = size
                h_style.font.color.rgb = RGBColor.from_string(color)
                h_style.font.bold = bold
                h_style.paragraph_format.space_before = space_before
                h_style.paragraph_format.space_after = space_after

        # --- Page setup ---
        section = doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)

        # --- Parse and render blocks ---
        blocks = _parse_markdown_blocks(markdown_content)

        for block in blocks:
            btype = block["type"]

            if btype == "heading":
                level = min(block["level"], 4)
                heading = doc.add_heading(level=level)
                _add_formatted_text(heading, block["content"], palette)

            elif btype == "paragraph":
                para = doc.add_paragraph()
                _add_formatted_text(para, block["content"], palette)

            elif btype == "code":
                para = doc.add_paragraph()
                para.paragraph_format.space_before = Pt(8)
                para.paragraph_format.space_after = Pt(8)

                # Add shading
                pPr = para._element.get_or_add_pPr()
                shd = pPr.makeelement(
                    qn("w:shd"),
                    {
                        qn("w:val"): "clear",
                        qn("w:color"): "auto",
                        qn("w:fill"): palette["light_bg"],
                    },
                )
                pPr.append(shd)

                # Add left indent for code block appearance
                para.paragraph_format.left_indent = Cm(0.5)
                para.paragraph_format.right_indent = Cm(0.5)

                run = para.add_run(block["content"])
                run.font.name = "Consolas"
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor.from_string(palette["text"])

            elif btype == "table":
                headers, rows = _parse_table(block["lines"])
                if not headers:
                    continue

                num_cols = len(headers)
                table = doc.add_table(rows=1 + len(rows), cols=num_cols)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                table.autofit = True

                # Style table with borders and colors
                tbl = table._tbl
                tblPr = (
                    tbl.tblPr
                    if tbl.tblPr is not None
                    else tbl.makeelement(qn("w:tblPr"), {})
                )

                # Add borders
                borders = tblPr.makeelement(qn("w:tblBorders"), {})
                for border_name in [
                    "top",
                    "left",
                    "bottom",
                    "right",
                    "insideH",
                    "insideV",
                ]:
                    border_el = borders.makeelement(
                        qn(f"w:{border_name}"),
                        {
                            qn("w:val"): "single",
                            qn("w:sz"): "4",
                            qn("w:space"): "0",
                            qn("w:color"): palette["border"],
                        },
                    )
                    borders.append(border_el)
                tblPr.append(borders)

                # Header row
                header_row = table.rows[0]
                for j, header_text in enumerate(headers):
                    cell = header_row.cells[j]
                    cell.text = ""
                    para = cell.paragraphs[0]
                    run = para.add_run(header_text)
                    run.bold = True
                    run.font.size = Pt(9)
                    run.font.color.rgb = RGBColor.from_string(
                        palette["table_header_fg"]
                    )
                    para.alignment = WD_ALIGN_PARAGRAPH.LEFT

                    # Header cell shading
                    tc = cell._tc
                    tcPr = tc.get_or_add_tcPr()
                    shd = tcPr.makeelement(
                        qn("w:shd"),
                        {
                            qn("w:val"): "clear",
                            qn("w:color"): "auto",
                            qn("w:fill"): palette["table_header_bg"],
                        },
                    )
                    tcPr.append(shd)

                # Data rows
                for i, row_data in enumerate(rows):
                    row = table.rows[i + 1]
                    for j, cell_text in enumerate(row_data):
                        if j < num_cols:
                            cell = row.cells[j]
                            cell.text = ""
                            para = cell.paragraphs[0]
                            run = para.add_run(cell_text)
                            run.font.size = Pt(9.5)
                            run.font.color.rgb = RGBColor.from_string(palette["text"])

                    # Alternating row shading
                    if i % 2 == 1:
                        for j in range(num_cols):
                            if j < len(row.cells):
                                tc = row.cells[j]._tc
                                tcPr = tc.get_or_add_tcPr()
                                shd = tcPr.makeelement(
                                    qn("w:shd"),
                                    {
                                        qn("w:val"): "clear",
                                        qn("w:color"): "auto",
                                        qn("w:fill"): palette["light_bg"],
                                    },
                                )
                                tcPr.append(shd)

                # Add spacing after table
                para = doc.add_paragraph()
                para.paragraph_format.space_before = Pt(4)

            elif btype == "ul":
                for item in block["items"]:
                    para = doc.add_paragraph(style="List Bullet")
                    if item["indent"] > 0:
                        para.paragraph_format.left_indent = Cm(
                            1.0 + item["indent"] * 0.5
                        )
                    _add_formatted_text(para, item["text"], palette)

            elif btype == "ol":
                for item in block["items"]:
                    para = doc.add_paragraph(style="List Number")
                    if item["indent"] > 0:
                        para.paragraph_format.left_indent = Cm(
                            1.0 + item["indent"] * 0.5
                        )
                    _add_formatted_text(para, item["text"], palette)

            elif btype == "blockquote":
                para = doc.add_paragraph()
                para.paragraph_format.left_indent = Cm(1.5)
                para.paragraph_format.space_before = Pt(8)
                para.paragraph_format.space_after = Pt(8)

                # Add left border shading
                pPr = para._element.get_or_add_pPr()
                shd = pPr.makeelement(
                    qn("w:shd"),
                    {
                        qn("w:val"): "clear",
                        qn("w:color"): "auto",
                        qn("w:fill"): palette["light_bg"],
                    },
                )
                pPr.append(shd)

                run = para.add_run(block["content"])
                run.italic = True
                run.font.color.rgb = RGBColor.from_string(palette["muted"])

            elif btype == "hr":
                para = doc.add_paragraph()
                para.paragraph_format.space_before = Pt(12)
                para.paragraph_format.space_after = Pt(12)
                # Add a bottom border to simulate HR
                pPr = para._element.get_or_add_pPr()
                pBdr = pPr.makeelement(qn("w:pBdr"), {})
                bottom = pBdr.makeelement(
                    qn("w:bottom"),
                    {
                        qn("w:val"): "single",
                        qn("w:sz"): "6",
                        qn("w:space"): "1",
                        qn("w:color"): palette["border"],
                    },
                )
                pBdr.append(bottom)
                pPr.append(pBdr)

        # Save to bytes
        buffer = io.BytesIO()
        doc.save(buffer)
        docx_bytes = buffer.getvalue()

        logger.info(
            "[DOCX-CONVERTER] Successfully generated DOCX (%d bytes, template=%s)",
            len(docx_bytes),
            template_name,
        )

        return docx_bytes

    except ImportError as e:
        logger.error("[DOCX-CONVERTER] python-docx not installed: %s", e)
        raise RuntimeError(
            "DOCX generation requires python-docx. "
            "Please install it with: pip install python-docx"
        ) from e
    except ValueError:
        raise
    except Exception as e:
        logger.error("[DOCX-CONVERTER] DOCX generation failed: %s", e)
        raise RuntimeError(f"Failed to generate DOCX: {str(e)}") from e
