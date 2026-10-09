"""docxtpl template renderer for the file write tool.

Merges structured data into a custom Word template using docxtpl,
preserving all original formatting, branding, logos, and layout.
"""

import io
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def render_docx_template(template_bytes: bytes, data: Dict[str, Any]) -> bytes:
    """Render a docxtpl Word template with the given data context.

    Args:
        template_bytes: The .docx template file content (with Jinja2 placeholders).
        data: Dictionary of template variable values.

    Returns:
        Rendered .docx file as bytes.

    Raises:
        RuntimeError: If rendering fails.
    """
    try:
        from docxtpl import DocxTemplate

        doc = DocxTemplate(io.BytesIO(template_bytes))
        doc.render(data)

        buffer = io.BytesIO()
        doc.save(buffer)
        result = buffer.getvalue()

        logger.info(
            "[DOCXTPL-RENDERER] Rendered template (%d bytes, %d variables)",
            len(result),
            len(data),
        )

        return result

    except ImportError as e:
        logger.error("[DOCXTPL-RENDERER] docxtpl not installed: %s", e)
        raise RuntimeError(
            "Template rendering requires docxtpl. "
            "Please install it with: pip install docxtpl"
        ) from e
    except Exception as e:
        logger.error("[DOCXTPL-RENDERER] Template rendering failed: %s", e)
        raise RuntimeError(f"Failed to render template: {str(e)}") from e
