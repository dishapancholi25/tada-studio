"""PPTX generation utilities for the file write tool.

Converts markdown content or structured JSON to professionally styled
PowerPoint presentations using python-pptx.
"""

import io
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# TEMPLATE PALETTES
# =============================================================================

TEMPLATE_PALETTES = {
    "modern": {
        "bg": "FFFFFF",
        "title_color": "111111",
        "subtitle_color": "666666",
        "body_color": "333333",
        "accent": "0066CC",
        "accent2": "E8F0FE",
        "divider": "E1E4E8",
        "cover_bg": "111111",
        "cover_fg": "FFFFFF",
        "table_header_bg": "2D2D2D",
        "table_header_fg": "FFFFFF",
        "table_alt_bg": "F6F8FA",
    },
    "executive": {
        "bg": "FFFFFF",
        "title_color": "1A3A5C",
        "subtitle_color": "718096",
        "body_color": "2D3748",
        "accent": "1A3A5C",
        "accent2": "F0F4F8",
        "divider": "D4DCE6",
        "cover_bg": "1A3A5C",
        "cover_fg": "FFFFFF",
        "table_header_bg": "1A3A5C",
        "table_header_fg": "FFFFFF",
        "table_alt_bg": "F0F4F8",
    },
    "report": {
        "bg": "FFFFFF",
        "title_color": "1E40AF",
        "subtitle_color": "6B7280",
        "body_color": "1F2937",
        "accent": "3B82F6",
        "accent2": "EFF6FF",
        "divider": "BFDBFE",
        "cover_bg": "1E40AF",
        "cover_fg": "FFFFFF",
        "table_header_bg": "1E40AF",
        "table_header_fg": "FFFFFF",
        "table_alt_bg": "EFF6FF",
    },
    "invoice": {
        "bg": "FFFFFF",
        "title_color": "111827",
        "subtitle_color": "6B7280",
        "body_color": "374151",
        "accent": "059669",
        "accent2": "ECFDF5",
        "divider": "E5E7EB",
        "cover_bg": "059669",
        "cover_fg": "FFFFFF",
        "table_header_bg": "059669",
        "table_header_fg": "FFFFFF",
        "table_alt_bg": "F9FAFB",
    },
    "minimal": {
        "bg": "FFFFFF",
        "title_color": "000000",
        "subtitle_color": "999999",
        "body_color": "333333",
        "accent": "333333",
        "accent2": "F5F5F5",
        "divider": "EEEEEE",
        "cover_bg": "000000",
        "cover_fg": "FFFFFF",
        "table_header_bg": "333333",
        "table_header_fg": "FFFFFF",
        "table_alt_bg": "FAFAFA",
    },
}


def _parse_markdown_to_slides(content: str) -> List[Dict[str, Any]]:
    """Parse markdown into slide structures.

    H1 = cover/title slide
    H2 = new content slide
    Bullet lists, tables, blockquotes become slide content
    --- = slide break
    """
    lines = content.split("\n")
    slides = []
    current_slide = None
    i = 0

    while i < len(lines):
        line = lines[i]

        # Slide break
        if re.match(r"^(-{3,}|\*{3,}|_{3,})\s*$", line.strip()):
            if current_slide:
                slides.append(current_slide)
                current_slide = None
            i += 1
            continue

        # H1 = Title/cover slide
        h1_match = re.match(r"^#\s+(.+)$", line)
        if h1_match:
            if current_slide:
                slides.append(current_slide)
            current_slide = {
                "type": "title",
                "title": h1_match.group(1).strip(),
                "subtitle": "",
                "content": [],
            }
            # Check if next non-empty line is subtitle text (not a heading or list)
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if (
                j < len(lines)
                and not re.match(r"^[#\-*+|>]", lines[j].strip())
                and not re.match(r"^\d+[.)]", lines[j].strip())
            ):
                current_slide["subtitle"] = lines[j].strip()
                i = j + 1
                continue
            i += 1
            continue

        # H2 = New content slide
        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            if current_slide:
                slides.append(current_slide)
            current_slide = {
                "type": "content",
                "title": h2_match.group(1).strip(),
                "content": [],
            }
            i += 1
            continue

        # H3+ = subsection within current slide
        h_match = re.match(r"^#{3,6}\s+(.+)$", line)
        if h_match:
            if not current_slide:
                current_slide = {"type": "content", "title": "", "content": []}
            current_slide["content"].append(
                {"type": "subheading", "text": h_match.group(1).strip()}
            )
            i += 1
            continue

        # Table
        if "|" in line and line.strip().startswith("|"):
            table_lines = []
            while (
                i < len(lines) and "|" in lines[i] and lines[i].strip().startswith("|")
            ):
                table_lines.append(lines[i])
                i += 1
            if len(table_lines) >= 2:
                headers = [
                    c.strip() for c in table_lines[0].strip().strip("|").split("|")
                ]
                rows = []
                for tl in table_lines[2:]:
                    if tl.strip():
                        rows.append(
                            [c.strip() for c in tl.strip().strip("|").split("|")]
                        )
                if not current_slide:
                    current_slide = {"type": "content", "title": "", "content": []}
                current_slide["content"].append(
                    {"type": "table", "headers": headers, "rows": rows}
                )
            continue

        # Bullet list
        list_match = re.match(r"^(\s*)([-*+])\s+(.+)$", line)
        if list_match:
            items = []
            while i < len(lines):
                item_match = re.match(r"^(\s*)([-*+])\s+(.+)$", lines[i])
                if item_match:
                    indent = len(item_match.group(1)) // 2
                    items.append({"text": item_match.group(3), "level": indent})
                    i += 1
                elif lines[i].strip() == "":
                    i += 1
                    break
                else:
                    break
            if not current_slide:
                current_slide = {"type": "content", "title": "", "content": []}
            current_slide["content"].append({"type": "bullets", "items": items})
            continue

        # Numbered list
        ol_match = re.match(r"^(\s*)\d+[.)]\s+(.+)$", line)
        if ol_match:
            items = []
            while i < len(lines):
                item_match = re.match(r"^(\s*)\d+[.)]\s+(.+)$", lines[i])
                if item_match:
                    indent = len(item_match.group(1)) // 2
                    items.append({"text": item_match.group(2), "level": indent})
                    i += 1
                elif lines[i].strip() == "":
                    i += 1
                    break
                else:
                    break
            if not current_slide:
                current_slide = {"type": "content", "title": "", "content": []}
            current_slide["content"].append({"type": "numbered", "items": items})
            continue

        # Blockquote
        if line.strip().startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            if not current_slide:
                current_slide = {"type": "content", "title": "", "content": []}
            current_slide["content"].append(
                {"type": "quote", "text": "\n".join(quote_lines)}
            )
            continue

        # Regular paragraph text
        if line.strip():
            if not current_slide:
                current_slide = {"type": "content", "title": "", "content": []}
            current_slide["content"].append({"type": "text", "text": line.strip()})

        i += 1

    if current_slide:
        slides.append(current_slide)

    return slides


def _parse_structured_json(content: str) -> Optional[List[Dict[str, Any]]]:
    """Try to parse content as structured JSON for presentation generation.

    Expected format:
    {
        "slides": [
            {
                "type": "title",  // or "content", "section", "two_column"
                "title": "Slide Title",
                "subtitle": "Optional subtitle",
                "content": [
                    {"type": "bullets", "items": [{"text": "...", "level": 0}]},
                    {"type": "table", "headers": [...], "rows": [...]},
                    {"type": "text", "text": "Paragraph text"},
                    {"type": "quote", "text": "Quote text"}
                ]
            }
        ]
    }
    """
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "slides" in data:
            return data["slides"]
        if (
            isinstance(data, list)
            and len(data) > 0
            and isinstance(data[0], dict)
            and "title" in data[0]
        ):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def markdown_to_pptx(
    content: str,
    template: Optional[str] = None,
) -> bytes:
    """Convert markdown or structured JSON to a styled PPTX presentation.

    Markdown mapping:
    - # H1 = Title/cover slide
    - ## H2 = New content slide title
    - Bullet lists = Slide bullet content
    - Tables = Slide table content
    - --- = Explicit slide break
    - > Blockquotes = Highlighted quote boxes

    Args:
        content: Markdown content or structured JSON.
        template: Template name ('modern', 'executive', 'report', 'invoice', 'minimal').

    Returns:
        PPTX file content as bytes.

    Raises:
        ValueError: If no slide content found.
        RuntimeError: If PPTX generation fails.
    """
    if not content or not content.strip():
        raise ValueError("Content cannot be empty")

    template_name = template if template in TEMPLATE_PALETTES else "modern"
    palette = TEMPLATE_PALETTES[template_name]

    logger.info(
        "[PPTX-CONVERTER] Converting content to PPTX (template=%s)", template_name
    )

    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        from pptx.util import Inches, Pt

        prs = Presentation()
        # Set 16:9 widescreen
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        # Parse content
        structured = _parse_structured_json(content)
        slides_data = structured if structured else _parse_markdown_to_slides(content)

        if not slides_data:
            raise ValueError("No slide content found in the provided content.")

        slide_width = prs.slide_width
        slide_height = prs.slide_height

        def _hex_to_rgb(hex_str):
            return RGBColor(
                int(hex_str[:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
            )

        def _add_shape(slide, left, top, width, height, fill_color=None):
            from pptx.enum.shapes import MSO_SHAPE

            shape = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, left, top, width, height
            )
            shape.line.fill.background()
            if fill_color:
                shape.fill.solid()
                shape.fill.fore_color.rgb = _hex_to_rgb(fill_color)
            return shape

        def _clean_inline_md(text):
            """Strip markdown inline formatting for plain text."""
            text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
            text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            text = re.sub(r"\*(.+?)\*", r"\1", text)
            text = re.sub(r"`(.+?)`", r"\1", text)
            text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
            return text

        for slide_data in slides_data:
            slide_type = slide_data.get("type", "content")
            blank_layout = prs.slide_layouts[6]  # Blank layout
            slide = prs.slides.add_slide(blank_layout)

            if slide_type == "title":
                # --- TITLE / COVER SLIDE ---
                # Full-color background
                _add_shape(slide, 0, 0, slide_width, slide_height, palette["cover_bg"])

                # Accent bar at top
                _add_shape(slide, 0, 0, slide_width, Inches(0.08), palette["accent"])

                # Title text
                title_left = Inches(1.5)
                title_top = Inches(2.2)
                title_width = Inches(10)
                title_height = Inches(2)

                txBox = slide.shapes.add_textbox(
                    title_left, title_top, title_width, title_height
                )
                tf = txBox.text_frame
                tf.word_wrap = True
                p = tf.paragraphs[0]
                p.text = _clean_inline_md(slide_data.get("title", ""))
                p.font.size = Pt(44)
                p.font.bold = True
                p.font.color.rgb = _hex_to_rgb(palette["cover_fg"])
                p.alignment = PP_ALIGN.LEFT

                # Subtitle
                subtitle = slide_data.get("subtitle", "")
                if subtitle:
                    sub_top = Inches(4.5)
                    sub_box = slide.shapes.add_textbox(
                        title_left, sub_top, title_width, Inches(1)
                    )
                    stf = sub_box.text_frame
                    stf.word_wrap = True
                    sp = stf.paragraphs[0]
                    sp.text = _clean_inline_md(subtitle)
                    sp.font.size = Pt(20)
                    sp.font.color.rgb = _hex_to_rgb(palette["cover_fg"])
                    sp.font.bold = False
                    sp.alignment = PP_ALIGN.LEFT

            else:
                # --- CONTENT SLIDE ---
                # White background with accent bar
                _add_shape(slide, 0, 0, slide_width, Inches(0.06), palette["accent"])

                # Slide title
                title_text = slide_data.get("title", "")
                if title_text:
                    t_box = slide.shapes.add_textbox(
                        Inches(0.8), Inches(0.4), Inches(11.5), Inches(0.8)
                    )
                    tf = t_box.text_frame
                    tf.word_wrap = True
                    p = tf.paragraphs[0]
                    p.text = _clean_inline_md(title_text)
                    p.font.size = Pt(28)
                    p.font.bold = True
                    p.font.color.rgb = _hex_to_rgb(palette["title_color"])
                    p.alignment = PP_ALIGN.LEFT

                    # Divider line under title
                    _add_shape(
                        slide,
                        Inches(0.8),
                        Inches(1.25),
                        Inches(11.5),
                        Pt(2),
                        palette["divider"],
                    )

                # Render content blocks
                content_items = slide_data.get("content", [])
                y_pos = Inches(1.5) if title_text else Inches(0.5)
                content_left = Inches(0.8)
                content_width = Inches(11.5)

                for block in content_items:
                    block_type = block.get("type", "text")

                    if block_type == "text":
                        box = slide.shapes.add_textbox(
                            content_left, y_pos, content_width, Inches(0.6)
                        )
                        tf = box.text_frame
                        tf.word_wrap = True
                        p = tf.paragraphs[0]
                        p.text = _clean_inline_md(block.get("text", ""))
                        p.font.size = Pt(16)
                        p.font.color.rgb = _hex_to_rgb(palette["body_color"])
                        y_pos += Inches(0.6)

                    elif block_type == "subheading":
                        box = slide.shapes.add_textbox(
                            content_left, y_pos, content_width, Inches(0.5)
                        )
                        tf = box.text_frame
                        tf.word_wrap = True
                        p = tf.paragraphs[0]
                        p.text = _clean_inline_md(block.get("text", ""))
                        p.font.size = Pt(20)
                        p.font.bold = True
                        p.font.color.rgb = _hex_to_rgb(palette["accent"])
                        y_pos += Inches(0.6)

                    elif block_type in ("bullets", "numbered"):
                        items = block.get("items", [])
                        # Estimate height: ~0.35 inches per item
                        box_height = max(Inches(0.5), Inches(0.35 * len(items)))
                        box = slide.shapes.add_textbox(
                            content_left, y_pos, content_width, box_height
                        )
                        tf = box.text_frame
                        tf.word_wrap = True

                        for idx, item in enumerate(items):
                            if idx == 0:
                                p = tf.paragraphs[0]
                            else:
                                p = tf.add_paragraph()

                            level = item.get("level", 0)
                            prefix = (
                                f"{'    ' * level}\u2022 "
                                if block_type == "bullets"
                                else f"{'    ' * level}{idx + 1}. "
                            )
                            p.text = prefix + _clean_inline_md(item.get("text", ""))
                            p.font.size = Pt(15)
                            p.font.color.rgb = _hex_to_rgb(palette["body_color"])
                            p.space_after = Pt(4)
                            if level > 0:
                                p.font.size = Pt(13)

                        y_pos += box_height + Inches(0.2)

                    elif block_type == "table":
                        headers = block.get("headers", [])
                        rows_data = block.get("rows", [])
                        if not headers:
                            continue

                        num_cols = len(headers)
                        num_rows = len(rows_data) + 1  # +1 for header

                        # Calculate table dimensions
                        table_width = min(content_width, Inches(11.5))
                        row_height = Inches(0.4)
                        table_height = row_height * num_rows

                        table = slide.shapes.add_table(
                            num_rows,
                            num_cols,
                            content_left,
                            y_pos,
                            table_width,
                            table_height,
                        ).table

                        # Style header row
                        for col_idx, header in enumerate(headers):
                            cell = table.cell(0, col_idx)
                            cell.text = _clean_inline_md(header)
                            cell.fill.solid()
                            cell.fill.fore_color.rgb = _hex_to_rgb(
                                palette["table_header_bg"]
                            )
                            for paragraph in cell.text_frame.paragraphs:
                                paragraph.font.size = Pt(11)
                                paragraph.font.bold = True
                                paragraph.font.color.rgb = _hex_to_rgb(
                                    palette["table_header_fg"]
                                )
                                paragraph.alignment = PP_ALIGN.LEFT

                        # Style data rows
                        for row_idx, row_data in enumerate(rows_data):
                            for col_idx, value in enumerate(row_data):
                                if col_idx >= num_cols:
                                    break
                                cell = table.cell(row_idx + 1, col_idx)
                                cell.text = _clean_inline_md(str(value))

                                # Alternating rows
                                if row_idx % 2 == 1:
                                    cell.fill.solid()
                                    cell.fill.fore_color.rgb = _hex_to_rgb(
                                        palette["table_alt_bg"]
                                    )

                                for paragraph in cell.text_frame.paragraphs:
                                    paragraph.font.size = Pt(10)
                                    paragraph.font.color.rgb = _hex_to_rgb(
                                        palette["body_color"]
                                    )

                        y_pos += table_height + Inches(0.3)

                    elif block_type == "quote":
                        # Quote with accent background
                        quote_height = Inches(0.8)
                        _add_shape(
                            slide,
                            content_left,
                            y_pos,
                            content_width,
                            quote_height,
                            palette["accent2"],
                        )

                        # Accent left bar
                        _add_shape(
                            slide,
                            content_left,
                            y_pos,
                            Inches(0.06),
                            quote_height,
                            palette["accent"],
                        )

                        # Quote text
                        box = slide.shapes.add_textbox(
                            content_left + Inches(0.3),
                            y_pos + Inches(0.1),
                            content_width - Inches(0.5),
                            quote_height - Inches(0.2),
                        )
                        tf = box.text_frame
                        tf.word_wrap = True
                        p = tf.paragraphs[0]
                        p.text = _clean_inline_md(block.get("text", ""))
                        p.font.size = Pt(14)
                        p.font.italic = True
                        p.font.color.rgb = _hex_to_rgb(palette["body_color"])

                        y_pos += quote_height + Inches(0.2)

                # Slide number at bottom right
                sn_box = slide.shapes.add_textbox(
                    slide_width - Inches(1.2),
                    slide_height - Inches(0.5),
                    Inches(0.8),
                    Inches(0.3),
                )
                stf = sn_box.text_frame
                sp = stf.paragraphs[0]
                sp.text = str(prs.slides.index(slide) + 1)
                sp.font.size = Pt(10)
                sp.font.color.rgb = _hex_to_rgb(palette["subtitle_color"])
                sp.alignment = PP_ALIGN.RIGHT

        # Save to bytes
        buffer = io.BytesIO()
        prs.save(buffer)
        pptx_bytes = buffer.getvalue()

        logger.info(
            "[PPTX-CONVERTER] Successfully generated PPTX (%d bytes, %d slides, template=%s)",
            len(pptx_bytes),
            len(slides_data),
            template_name,
        )

        return pptx_bytes

    except ImportError as e:
        logger.error("[PPTX-CONVERTER] python-pptx not installed: %s", e)
        raise RuntimeError(
            "PPTX generation requires python-pptx. "
            "Please install it with: pip install python-pptx"
        ) from e
    except ValueError:
        raise
    except Exception as e:
        logger.error("[PPTX-CONVERTER] PPTX generation failed: %s", e)
        raise RuntimeError(f"Failed to generate PPTX: {str(e)}") from e
