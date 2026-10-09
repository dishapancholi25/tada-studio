"""PDF generation utilities for the file write tool.

Converts markdown content to PDF using weasyprint with professional template support.
"""

import logging
from typing import Optional

import markdown

logger = logging.getLogger(__name__)


# =============================================================================
# PDF TEMPLATES
# =============================================================================

# Shared base styles used across all templates
_BASE_STYLES = """
@page {
    size: A4;
    margin: 2.5cm 2cm;
}

body {
    font-family: 'Liberation Sans', 'Noto Sans', 'DejaVu Sans', sans-serif;
    font-size: 10.5pt;
    line-height: 1.7;
    color: #2d2d2d;
    -webkit-font-smoothing: antialiased;
}

/* Typography scale */
h1 { font-size: 26pt; margin-top: 0; margin-bottom: 0.6em; line-height: 1.2; }
h2 { font-size: 19pt; margin-top: 1.8em; margin-bottom: 0.5em; line-height: 1.3; }
h3 { font-size: 14pt; margin-top: 1.5em; margin-bottom: 0.4em; line-height: 1.4; }
h4 { font-size: 12pt; margin-top: 1.3em; margin-bottom: 0.3em; }
h5, h6 { font-size: 10.5pt; margin-top: 1em; margin-bottom: 0.3em; }

p { margin: 0.7em 0; orphans: 3; widows: 3; }

/* Lists */
ul, ol { margin: 0.8em 0; padding-left: 1.8em; }
li { margin: 0.25em 0; }
li > ul, li > ol { margin: 0.2em 0; }

/* Links */
a { text-decoration: none; }

/* Horizontal rule */
hr { border: none; margin: 2em 0; }

/* Images */
img { max-width: 100%; height: auto; }

/* Code */
code {
    font-family: 'Liberation Mono', 'DejaVu Sans Mono', monospace;
    font-size: 9.5pt;
    padding: 2px 5px;
    border-radius: 3px;
}

pre {
    font-family: 'Liberation Mono', 'DejaVu Sans Mono', monospace;
    font-size: 9pt;
    padding: 1em 1.2em;
    border-radius: 6px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-wrap: break-word;
    line-height: 1.5;
    margin: 1.2em 0;
}

pre code { background: none; padding: 0; border: none; font-size: inherit; }

/* Blockquotes */
blockquote {
    margin: 1.2em 0;
    padding: 0.8em 1.2em;
    font-style: italic;
    orphans: 3;
    widows: 3;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5em 0;
    font-size: 9.5pt;
    page-break-inside: auto;
}

tr { page-break-inside: avoid; page-break-after: auto; }

th, td {
    padding: 10px 14px;
    text-align: left;
    vertical-align: top;
}

th { font-weight: 600; }

/* Emphasis */
strong { font-weight: 600; }
em { font-style: italic; }
"""

TEMPLATE_MODERN = (
    _BASE_STYLES
    + """
/* Modern: clean, minimal, lots of whitespace */

@page {
    @bottom-center {
        content: counter(page);
        font-size: 8pt;
        color: #999;
    }
}

h1 {
    color: #111;
    font-weight: 700;
    letter-spacing: -0.5px;
    padding-bottom: 0.4em;
    border-bottom: 3px solid #111;
}

h2 {
    color: #333;
    font-weight: 600;
    letter-spacing: -0.3px;
}

h3 { color: #444; font-weight: 600; }
h4, h5, h6 { color: #555; font-weight: 600; }

a { color: #0066cc; }

hr { border-top: 1px solid #e5e5e5; }

code {
    background-color: #f6f8fa;
    border: 1px solid #e1e4e8;
    color: #24292e;
}

pre {
    background-color: #f6f8fa;
    border: 1px solid #e1e4e8;
}

blockquote {
    border-left: 4px solid #ddd;
    background-color: #fafafa;
    color: #555;
}

th {
    background-color: #f8f9fa;
    border-bottom: 2px solid #dee2e6;
    color: #333;
    text-transform: uppercase;
    font-size: 8.5pt;
    letter-spacing: 0.5px;
}

td { border-bottom: 1px solid #eee; }
tr:last-child td { border-bottom: 2px solid #dee2e6; }
"""
)

TEMPLATE_EXECUTIVE = (
    _BASE_STYLES
    + """
/* Executive: modern corporate, navy palette, strong visual hierarchy */

body {
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a2e;
}

@page {
    margin: 2.5cm 2.5cm 3cm 2.5cm;
    @top-right {
        content: string(doc-title);
        font-size: 7.5pt;
        color: #9aa5b4;
        letter-spacing: 0.3px;
    }
    @bottom-right {
        content: "Page " counter(page);
        font-size: 7.5pt;
        color: #9aa5b4;
    }
    @bottom-left {
        content: "Confidential";
        font-size: 7pt;
        color: #c4cdd8;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
}

h1 {
    string-set: doc-title content();
    color: #ffffff;
    background-color: #1a3a5c;
    font-weight: 700;
    font-size: 24pt;
    padding: 0.6em 0.8em;
    margin: 0 -2.5cm 1.2em -2.5cm;
    padding-left: 2.5cm;
    padding-right: 2.5cm;
    letter-spacing: -0.3px;
    border-bottom: 4px solid #2c5282;
}

h2 {
    color: #1a3a5c;
    font-weight: 700;
    font-size: 16pt;
    border-left: 4px solid #1a3a5c;
    padding-left: 0.6em;
    padding-bottom: 0.15em;
    margin-top: 2em;
    background-color: #f0f4f8;
    padding-top: 0.3em;
    padding-bottom: 0.3em;
}

h3 {
    color: #2c5282;
    font-weight: 700;
    font-size: 12pt;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    border-left: 3px solid #a3bfdb;
    padding-left: 0.5em;
    margin-top: 1.6em;
}

h4, h5, h6 {
    color: #3a5a7c;
    font-weight: 700;
}

a { color: #2c5282; }

hr {
    border-top: 2px solid #e2e8f0;
    margin: 2.5em 0;
}

/* Lists with navy accent bullets */
ul { list-style-type: none; padding-left: 1.2em; }
ul > li { padding-left: 0.6em; margin: 0.4em 0; }
ul > li::before {
    content: "\\2022";
    color: #1a3a5c;
    font-weight: 700;
    display: inline-block;
    width: 1em;
    margin-left: -1em;
}

ol > li { margin: 0.4em 0; }

code {
    background-color: #f0f4f8;
    border: 1px solid #d4dce6;
    color: #2d3748;
}

pre {
    background-color: #f0f4f8;
    border: 1px solid #d4dce6;
    border-left: 4px solid #1a3a5c;
}

blockquote {
    border-left: 4px solid #2c5282;
    background-color: #f0f4f8;
    color: #2d3748;
    padding: 1em 1.4em;
    margin: 1.5em 0;
    font-style: normal;
    border-radius: 0 4px 4px 0;
}

blockquote p { margin: 0.3em 0; }

/* Tables with refined header styling */
th {
    background-color: #2c5282;
    color: white;
    border: 1px solid #2c5282;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 12px 16px;
}

td {
    border: 1px solid #e2e8f0;
    padding: 10px 16px;
}

tr:nth-child(even) td {
    background-color: #f7fafc;
}

tr:nth-child(odd) td {
    background-color: #ffffff;
}

/* Strong text in navy for emphasis */
strong { color: #1a3a5c; }
"""
)

TEMPLATE_REPORT = (
    _BASE_STYLES
    + """
/* Report: structured technical report, numbered sections feel */

@page {
    margin: 2.5cm 2cm 3cm 2cm;
    @top-left {
        content: string(doc-title);
        font-size: 8pt;
        color: #666;
    }
    @top-right {
        content: string(doc-date);
        font-size: 8pt;
        color: #666;
    }
    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #666;
    }
}

@page :first {
    @top-left { content: none; }
    @top-right { content: none; }
    margin-top: 4cm;
}

h1 {
    string-set: doc-title content();
    color: #1e40af;
    font-weight: 700;
    padding-bottom: 0.3em;
    border-bottom: 3px solid #1e40af;
    margin-bottom: 0.8em;
}

h2 {
    color: #1e3a5f;
    font-weight: 600;
    padding-bottom: 0.2em;
    border-bottom: 1.5px solid #93c5fd;
}

h3 { color: #1e3a5f; font-weight: 600; }
h4, h5, h6 { color: #374151; font-weight: 600; }

a { color: #1e40af; }

hr { border-top: 1.5px solid #d1d5db; }

code {
    background-color: #eff6ff;
    border: 1px solid #bfdbfe;
    color: #1e3a8a;
}

pre {
    background-color: #1e293b;
    color: #e2e8f0;
    border: none;
    border-radius: 8px;
}

pre code { color: #e2e8f0; }

blockquote {
    border-left: 4px solid #3b82f6;
    background-color: #eff6ff;
    color: #1e3a5f;
    border-radius: 0 6px 6px 0;
}

th {
    background-color: #1e40af;
    color: white;
    border: 1px solid #1e40af;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

td {
    border: 1px solid #d1d5db;
}

tr:nth-child(even) td {
    background-color: #f8fafc;
}

tr:hover td {
    background-color: #eff6ff;
}
"""
)

TEMPLATE_INVOICE = (
    _BASE_STYLES
    + """
/* Invoice: clean financial document, prominent tables and numbers */

@page {
    margin: 2cm;
    @bottom-center {
        content: counter(page);
        font-size: 8pt;
        color: #999;
    }
}

body {
    font-size: 10pt;
    color: #374151;
}

h1 {
    color: #111827;
    font-weight: 800;
    font-size: 30pt;
    text-transform: uppercase;
    letter-spacing: 2px;
    border-bottom: none;
    margin-bottom: 0.3em;
}

h2 {
    color: #059669;
    font-weight: 700;
    font-size: 14pt;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 2em;
    padding-bottom: 0.3em;
    border-bottom: 2px solid #059669;
}

h3 {
    color: #374151;
    font-weight: 600;
    font-size: 12pt;
}

h4, h5, h6 { color: #6b7280; font-weight: 600; }

a { color: #059669; }

hr { border-top: 2px solid #e5e7eb; }

code {
    background-color: #f3f4f6;
    border: 1px solid #e5e7eb;
    color: #1f2937;
}

pre {
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
}

blockquote {
    border-left: 4px solid #059669;
    background-color: #ecfdf5;
    color: #064e3b;
}

table {
    font-size: 10pt;
}

th {
    background-color: #f9fafb;
    color: #374151;
    border-bottom: 2px solid #d1d5db;
    border-top: 2px solid #374151;
    font-size: 8.5pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 12px 14px;
}

td {
    border-bottom: 1px solid #e5e7eb;
    padding: 10px 14px;
}

tr:last-child td {
    border-bottom: 2px solid #374151;
    font-weight: 600;
}

/* Make numbers right-aligned in tables for financial docs */
td:last-child, th:last-child {
    text-align: right;
}

strong { color: #111827; }
"""
)

TEMPLATE_MINIMAL = (
    _BASE_STYLES
    + """
/* Minimal: distraction-free, maximum readability */

@page {
    margin: 3cm 3cm;
    @bottom-center {
        content: counter(page);
        font-size: 8pt;
        color: #ccc;
    }
}

body {
    font-size: 11pt;
    line-height: 1.8;
    color: #333;
    max-width: 42em;
}

h1 {
    color: #000;
    font-weight: 800;
    margin-bottom: 0.8em;
    border-bottom: none;
}

h2 {
    color: #222;
    font-weight: 700;
    margin-top: 2em;
}

h3 { color: #333; font-weight: 600; }
h4, h5, h6 { color: #444; font-weight: 600; }

a { color: #0055aa; }

hr { border-top: 1px solid #eee; margin: 2.5em 0; }

code {
    background-color: #f5f5f5;
    border: none;
    color: #333;
}

pre {
    background-color: #f5f5f5;
    border: none;
    padding: 1.2em 1.5em;
    border-radius: 4px;
}

blockquote {
    border-left: 3px solid #ddd;
    background: none;
    color: #666;
    padding: 0.3em 1em;
}

th {
    border-bottom: 2px solid #333;
    background: none;
    color: #333;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

td { border-bottom: 1px solid #eee; }
tr:last-child td { border-bottom: 1px solid #333; }
"""
)

# Template registry
PDF_TEMPLATES = {
    "modern": TEMPLATE_MODERN,
    "executive": TEMPLATE_EXECUTIVE,
    "report": TEMPLATE_REPORT,
    "invoice": TEMPLATE_INVOICE,
    "minimal": TEMPLATE_MINIMAL,
}

# Default template fallback (same as legacy behavior but improved)
DEFAULT_PDF_CSS = TEMPLATE_MODERN


def markdown_to_pdf(
    markdown_content: str,
    custom_css: Optional[str] = None,
    template: Optional[str] = None,
) -> bytes:
    """Convert markdown content to PDF binary.

    Args:
        markdown_content: The markdown text to convert.
        custom_css: Optional custom CSS to style the PDF.
                   If not provided, uses the selected template or default styling.
        template: Optional template name ('modern', 'executive', 'report',
                 'invoice', 'minimal'). Overridden by custom_css if both provided.

    Returns:
        PDF file content as bytes.

    Raises:
        ValueError: If markdown content is empty.
        RuntimeError: If PDF generation fails.
    """
    if not markdown_content or not markdown_content.strip():
        raise ValueError("Markdown content cannot be empty")

    logger.info("[PDF-CONVERTER] Converting markdown to PDF (template=%s)", template)

    try:
        # Convert markdown to HTML with extensions for tables, code, etc.
        html_content = markdown.markdown(
            markdown_content,
            extensions=[
                "tables",
                "fenced_code",
                "toc",
                "nl2br",
                "sane_lists",
                "smarty",
                "attr_list",
            ],
        )

        # Resolve CSS: custom > template > default
        if custom_css:
            css = custom_css
        elif template and template in PDF_TEMPLATES:
            css = PDF_TEMPLATES[template]
        else:
            css = DEFAULT_PDF_CSS

        # Build full HTML document
        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
{css}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

        # Import weasyprint here to avoid import errors if not installed
        from weasyprint import HTML

        # Generate PDF
        pdf_bytes = HTML(string=full_html).write_pdf()

        logger.info(
            "[PDF-CONVERTER] Successfully generated PDF (%d bytes, template=%s)",
            len(pdf_bytes),
            template or "default",
        )

        return pdf_bytes

    except ImportError as e:
        logger.error("[PDF-CONVERTER] weasyprint not installed: %s", e)
        raise RuntimeError(
            "PDF generation requires weasyprint. "
            "Please install it with: pip install weasyprint"
        ) from e
    except Exception as e:
        logger.error("[PDF-CONVERTER] PDF generation failed: %s", e)
        raise RuntimeError(f"Failed to generate PDF: {str(e)}") from e
