"""Factory for creating file write tool instances.

Creates StructuredTool instances for AI agents to write files.
Files are stored in PostgreSQL database.
"""

import base64
import json
import logging
from pathlib import Path
from typing import Callable, List, Optional

from langchain_core.tools import StructuredTool

from .schemas import FileWriteInput


logger = logging.getLogger(__name__)

# Supported document formats for auto-conversion
_DOCUMENT_FORMATS = {".pdf", ".docx", ".xlsx", ".pptx"}


def create_file_write_tool(
    allowed_extensions: List[str],
    max_file_size_mb: int = 1024,
    node_id: Optional[str] = None,
    node_name: Optional[str] = None,
    tool_name: str = "file_write",
    description_prefix: Optional[str] = None,
    node_execution_id: Optional[str] = None,
    node_execution_id_provider: Optional[Callable[[], Optional[str]]] = None,
    default_template: Optional[str] = None,
    custom_template_asset_id: Optional[str] = None,
    custom_template_variables: Optional[List[str]] = None,
) -> StructuredTool:
    """Create a file write tool for agents.

    Args:
        allowed_extensions: List of allowed file extensions
        max_file_size_mb: Maximum file size in MB
        node_id: Node ID for tracking
        node_name: Node name for tracking
        tool_name: Name of the tool
        description_prefix: Optional prefix for tool description
        node_execution_id: Optional static node execution ID for DB storage
        node_execution_id_provider: Optional callback to get node_execution_id at runtime
        default_template: Default template for styled document generation
        custom_template_asset_id: Asset ID of a custom docxtpl Word template
        custom_template_variables: List of Jinja2 variable names in the template

    Returns:
        Configured StructuredTool instance
    """
    # Build description
    ext_list = ", ".join(allowed_extensions)

    # Custom template mode: agent outputs JSON instead of markdown for .docx
    has_custom_template = bool(custom_template_asset_id and custom_template_variables)

    doc_formats = [
        ext for ext in [".pdf", ".docx", ".xlsx", ".pptx"] if ext in allowed_extensions
    ]

    if has_custom_template:
        var_list = ", ".join(custom_template_variables)
        base_description = (
            f"Write content to a file with professional styling. "
            f"Supported extensions: {ext_list}. "
            f"IMPORTANT: For Word documents (.docx), a custom branded template is attached. "
            f"You MUST provide the content as a JSON object with these template variables: "
            f"{var_list}. "
            f"The template preserves all Word formatting, branding, logos, and layout. "
            f"For other document formats, see each parameter's description."
        )
    elif doc_formats:
        doc_list = ", ".join(doc_formats)
        base_description = (
            f"Write content to a file with professional styling. "
            f"Supported extensions: {ext_list}. "
            f"Document formats ({doc_list}) are auto-generated from markdown or structured JSON "
            f"with professional templates. Choose a template via the 'template' parameter. "
            f"See each parameter's description for format-specific guidance and examples."
        )
    else:
        base_description = (
            f"Write content to a file. Supported extensions: {ext_list}. "
            f"For binary files, provide base64-encoded content with content_type='base64'."
        )

    if description_prefix:
        description = f"{description_prefix}. {base_description}"
    else:
        description = base_description

    def write_file(
        filename: str,
        content: str,
        content_type: str = "text",
        subdirectory: Optional[str] = None,
        css: Optional[str] = None,
        template: Optional[str] = None,
    ) -> str:
        """Write content to a file stored in the database.

        Args:
            filename: Name of the file to create
            content: File content (text, base64, or markdown for document formats)
            content_type: "text" or "base64"
            subdirectory: Optional subdirectory (for organization)
            css: Optional custom CSS for PDF styling
            template: Optional template name for styled documents

        Returns:
            Success message with file_id or error message
        """
        logger.info("[FILE-WRITE-TOOL] Writing file: %s", filename)

        # Keep original text content for search/preview
        original_text_content = content if content_type == "text" else None

        # Resolve template: explicit > default > "modern"
        resolved_template = template or default_template

        try:
            # Validate extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in allowed_extensions:
                return json.dumps(
                    {
                        "success": False,
                        "error": f"File extension '{file_ext}' not allowed. Allowed: {', '.join(allowed_extensions)}",
                        "filename": filename,
                    }
                )

            # Handle PDF generation: convert markdown to PDF
            is_document = file_ext in _DOCUMENT_FORMATS
            if file_ext == ".pdf" and content_type != "base64":
                logger.info(
                    "[FILE-WRITE-TOOL] Converting markdown to PDF (template=%s)",
                    resolved_template,
                )
                try:
                    from .pdf_converter import markdown_to_pdf

                    pdf_bytes = markdown_to_pdf(
                        content, custom_css=css, template=resolved_template
                    )
                    content = pdf_bytes
                    content_type = "binary"
                    logger.info(
                        "[FILE-WRITE-TOOL] PDF generated (%d bytes)", len(pdf_bytes)
                    )
                except Exception as e:
                    logger.error("[FILE-WRITE-TOOL] PDF generation failed: %s", e)
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"PDF generation failed: {str(e)}",
                            "filename": filename,
                        }
                    )

            # Handle DOCX generation
            elif file_ext == ".docx" and content_type != "base64":
                if has_custom_template:
                    # Custom template mode: parse JSON and render via docxtpl
                    logger.info(
                        "[FILE-WRITE-TOOL] Rendering custom docxtpl template "
                        "(asset_id=%s)",
                        custom_template_asset_id,
                    )
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError as e:
                        return json.dumps(
                            {
                                "success": False,
                                "error": (
                                    "Content must be valid JSON when using a custom "
                                    f"Word template: {str(e)}"
                                ),
                                "filename": filename,
                            }
                        )

                    try:
                        from backend.services.workflow.asset_service import (
                            WorkflowAssetService,
                        )

                        asset_service = WorkflowAssetService()
                        result = asset_service.get_template_content(
                            custom_template_asset_id
                        )
                        if not result:
                            return json.dumps(
                                {
                                    "success": False,
                                    "error": (
                                        "Custom template not found — it may "
                                        "have been deleted"
                                    ),
                                    "filename": filename,
                                }
                            )

                        template_bytes, _, _ = result

                        from .docxtpl_renderer import render_docx_template

                        docx_bytes = render_docx_template(template_bytes, data)
                        content = docx_bytes
                        content_type = "binary"
                        logger.info(
                            "[FILE-WRITE-TOOL] Custom template rendered (%d bytes)",
                            len(docx_bytes),
                        )
                    except Exception as e:
                        logger.error(
                            "[FILE-WRITE-TOOL] Custom template render failed: %s", e
                        )
                        return json.dumps(
                            {
                                "success": False,
                                "error": f"Template rendering failed: {str(e)}",
                                "filename": filename,
                            }
                        )
                else:
                    # Standard mode: convert markdown to DOCX
                    logger.info(
                        "[FILE-WRITE-TOOL] Converting markdown to DOCX (template=%s)",
                        resolved_template,
                    )
                    try:
                        from .docx_converter import markdown_to_docx

                        docx_bytes = markdown_to_docx(
                            content, template=resolved_template
                        )
                        content = docx_bytes
                        content_type = "binary"
                        logger.info(
                            "[FILE-WRITE-TOOL] DOCX generated (%d bytes)",
                            len(docx_bytes),
                        )
                    except Exception as e:
                        logger.error("[FILE-WRITE-TOOL] DOCX generation failed: %s", e)
                        return json.dumps(
                            {
                                "success": False,
                                "error": f"DOCX generation failed: {str(e)}",
                                "filename": filename,
                            }
                        )

            # Handle XLSX generation: convert markdown tables or JSON to Excel
            elif file_ext == ".xlsx" and content_type != "base64":
                logger.info(
                    "[FILE-WRITE-TOOL] Converting content to XLSX (template=%s)",
                    resolved_template,
                )
                try:
                    from .xlsx_converter import markdown_to_xlsx

                    xlsx_bytes = markdown_to_xlsx(content, template=resolved_template)
                    content = xlsx_bytes
                    content_type = "binary"
                    logger.info(
                        "[FILE-WRITE-TOOL] XLSX generated (%d bytes)", len(xlsx_bytes)
                    )
                except Exception as e:
                    logger.error("[FILE-WRITE-TOOL] XLSX generation failed: %s", e)
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"XLSX generation failed: {str(e)}",
                            "filename": filename,
                        }
                    )

            # Handle PPTX generation: convert markdown or JSON to PowerPoint
            elif file_ext == ".pptx" and content_type != "base64":
                logger.info(
                    "[FILE-WRITE-TOOL] Converting content to PPTX (template=%s)",
                    resolved_template,
                )
                try:
                    from .pptx_converter import markdown_to_pptx

                    pptx_bytes = markdown_to_pptx(content, template=resolved_template)
                    content = pptx_bytes
                    content_type = "binary"
                    logger.info(
                        "[FILE-WRITE-TOOL] PPTX generated (%d bytes)", len(pptx_bytes)
                    )
                except Exception as e:
                    logger.error("[FILE-WRITE-TOOL] PPTX generation failed: %s", e)
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"PPTX generation failed: {str(e)}",
                            "filename": filename,
                        }
                    )

            # Sanitize filename to prevent path traversal
            safe_filename = Path(filename).name
            if safe_filename != filename:
                logger.warning(
                    "[FILE-WRITE-TOOL] Sanitized filename from '%s' to '%s'",
                    filename,
                    safe_filename,
                )
                filename = safe_filename

            # Process content based on type
            if content_type == "binary":
                # Already binary (e.g., from document generation)
                file_content = content
            elif content_type == "base64":
                try:
                    file_content = base64.b64decode(content)
                except Exception as e:
                    logger.error("[FILE-WRITE-TOOL] Base64 decode error: %s", e)
                    return json.dumps(
                        {
                            "success": False,
                            "error": f"Invalid base64 content - {str(e)}",
                            "filename": filename,
                        }
                    )
            else:
                # Text content - convert to bytes for storage
                file_content = content.encode("utf-8")

            # Check content size
            content_size_bytes = len(file_content)
            max_size_bytes = max_file_size_mb * 1024 * 1024

            if content_size_bytes > max_size_bytes:
                size_mb = content_size_bytes / (1024 * 1024)
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Content too large ({size_mb:.2f}MB). Maximum: {max_file_size_mb}MB",
                        "filename": filename,
                    }
                )

            # Get node_execution_id for database storage
            exec_id = node_execution_id
            if exec_id is None and node_execution_id_provider:
                exec_id = node_execution_id_provider()

            if not exec_id:
                logger.error(
                    "[FILE-WRITE-TOOL] No node_execution_id available for file storage"
                )
                return json.dumps(
                    {
                        "success": False,
                        "error": "File storage unavailable - no execution context",
                        "filename": filename,
                    }
                )

            # Store file in database
            from backend.services.execution.files import (
                ExecutionFileService,
                FileSizeLimitExceeded,
            )

            try:
                file_service = ExecutionFileService()
                execution_file = file_service.store_file(
                    node_execution_id=exec_id,
                    filename=filename,
                    content=file_content,
                    subdirectory=subdirectory,
                    text_content=original_text_content,
                )

                logger.info(
                    "[FILE-WRITE-TOOL] Stored file in database: id=%s, size=%s",
                    execution_file.id,
                    execution_file.file_size,
                )

                # Build result with file_id for frontend
                reported_content_type = (
                    "base64" if is_document or content_type == "base64" else "text"
                )
                result = {
                    "success": True,
                    "message": f"Successfully wrote file: {filename}",
                    "filename": filename,
                    "file_id": execution_file.id,
                    "file_url": f"/api/files/{execution_file.id}",
                    "file_size": execution_file.file_size,
                    "content_type": reported_content_type,
                    "subdirectory": subdirectory,
                    "status": "success",
                }

                if resolved_template:
                    result["template"] = resolved_template

                # Include content for text files (for preview in UI)
                if original_text_content and not is_document:
                    result["content"] = original_text_content

                return json.dumps(result)

            except FileSizeLimitExceeded as e:
                return json.dumps(
                    {
                        "success": False,
                        "error": str(e),
                        "filename": filename,
                    }
                )

        except Exception as e:
            error_msg = f"Failed to write file '{filename}': {str(e)}"
            logger.error("[FILE-WRITE-TOOL] %s", error_msg)
            return json.dumps(
                {
                    "success": False,
                    "error": error_msg,
                    "filename": filename,
                }
            )

    tool = StructuredTool.from_function(
        func=write_file,
        name=tool_name,
        description=description,
        args_schema=FileWriteInput,
    )

    # Attach node_id for tracking
    if node_id:
        tool.metadata = {"node_id": node_id, "node_name": node_name}

    return tool
