"""Workflow asset service for managing design-time assets.

Handles upload, retrieval, and deletion of assets (e.g., custom Word templates)
attached to workflow nodes.
"""

import io
import logging
from typing import Any, Dict, Optional, Tuple

from backend.models.workflows.workflow_asset import WorkflowAsset
from backend.services.database import get_db

logger = logging.getLogger(__name__)

# Allowed MIME types for template uploads
ALLOWED_TEMPLATE_MIMETYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_TEMPLATE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class WorkflowAssetService:
    """Service for managing workflow assets (e.g., custom document templates)."""

    def upload_template(
        self,
        workflow_id: str,
        node_id: str,
        filename: str,
        content: bytes,
    ) -> WorkflowAsset:
        """Upload a custom Word template for a FILE_WRITE node.

        Validates the file, extracts Jinja2 template variables,
        and stores the asset in the database. Replaces any existing
        template for the same node.

        Args:
            workflow_id: Parent workflow ID.
            node_id: The node's uniq_id within the graph.
            filename: Original filename (must be .docx).
            content: Binary file content.

        Returns:
            The created WorkflowAsset.

        Raises:
            ValueError: If the file is invalid or too large.
            RuntimeError: If template variable extraction fails.
        """
        # Validate file extension
        if not filename.lower().endswith(".docx"):
            raise ValueError("Only .docx files are accepted as templates")

        # Validate file size
        if len(content) > MAX_TEMPLATE_SIZE_BYTES:
            size_mb = len(content) / (1024 * 1024)
            raise ValueError(
                f"Template too large ({size_mb:.1f}MB). Maximum: "
                f"{MAX_TEMPLATE_SIZE_BYTES // (1024 * 1024)}MB"
            )

        # Extract template variables
        metadata = self.extract_template_variables(content)

        # Delete any existing template for this node
        self._delete_node_templates(workflow_id, node_id)

        # Store the asset
        from backend.models.base import generate_uuid

        asset = WorkflowAsset(
            id=generate_uuid(),
            workflow_id=workflow_id,
            node_id=node_id,
            asset_type="docx_template",
            filename=filename,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            file_size=len(content),
            content=content,
            metadata_json=metadata,
        )

        with get_db() as db:
            db.add(asset)
            db.commit()
            db.refresh(asset)

        logger.info(
            "[ASSET-SERVICE] Uploaded template '%s' for workflow=%s node=%s "
            "(size=%d, variables=%s)",
            filename,
            workflow_id,
            node_id,
            len(content),
            metadata.get("variables", []),
        )

        return asset

    def get_template_content(
        self, asset_id: str
    ) -> Optional[Tuple[bytes, str, Dict[str, Any]]]:
        """Retrieve template content by asset ID.

        Args:
            asset_id: The asset's UUID.

        Returns:
            Tuple of (content_bytes, filename, metadata_json) or None if not found.
        """
        with get_db() as db:
            asset = (
                db.query(WorkflowAsset)
                .filter(
                    WorkflowAsset.id == asset_id,
                    WorkflowAsset.asset_type == "docx_template",
                )
                .first()
            )

            if not asset:
                return None

            return asset.content, asset.filename, asset.metadata_json or {}

    def get_template_metadata(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve template metadata without loading binary content.

        Args:
            asset_id: The asset's UUID.

        Returns:
            Dict with id, filename, file_size, metadata_json, or None.
        """
        with get_db() as db:
            asset = (
                db.query(
                    WorkflowAsset.id,
                    WorkflowAsset.filename,
                    WorkflowAsset.file_size,
                    WorkflowAsset.metadata_json,
                    WorkflowAsset.created_at,
                )
                .filter(
                    WorkflowAsset.id == asset_id,
                    WorkflowAsset.asset_type == "docx_template",
                )
                .first()
            )

            if not asset:
                return None

            return {
                "id": asset.id,
                "filename": asset.filename,
                "file_size": asset.file_size,
                "metadata": asset.metadata_json or {},
                "created_at": asset.created_at.isoformat()
                if asset.created_at
                else None,
            }

    def delete_template(self, asset_id: str) -> bool:
        """Delete a template asset by ID.

        Args:
            asset_id: The asset's UUID.

        Returns:
            True if deleted, False if not found.
        """
        with get_db() as db:
            count = (
                db.query(WorkflowAsset)
                .filter(
                    WorkflowAsset.id == asset_id,
                    WorkflowAsset.asset_type == "docx_template",
                )
                .delete()
            )
            db.commit()

        if count > 0:
            logger.info("[ASSET-SERVICE] Deleted template asset_id=%s", asset_id)
            return True
        return False

    def _delete_node_templates(self, workflow_id: str, node_id: str) -> int:
        """Delete all template assets for a specific node.

        Args:
            workflow_id: Parent workflow ID.
            node_id: The node's uniq_id.

        Returns:
            Number of assets deleted.
        """
        with get_db() as db:
            count = (
                db.query(WorkflowAsset)
                .filter(
                    WorkflowAsset.workflow_id == workflow_id,
                    WorkflowAsset.node_id == node_id,
                    WorkflowAsset.asset_type == "docx_template",
                )
                .delete()
            )
            db.commit()
            return count

    @staticmethod
    def extract_template_variables(content: bytes) -> Dict[str, Any]:
        """Extract Jinja2 template variables from a .docx template.

        Uses docxtpl to parse the template and find all undeclared
        variables ({{ var }}, {% for item in items %}, etc.).

        Args:
            content: Binary content of the .docx file.

        Returns:
            Dict with "variables" list of variable names.

        Raises:
            RuntimeError: If the template cannot be parsed.
        """
        try:
            from docxtpl import DocxTemplate

            doc = DocxTemplate(io.BytesIO(content))
            variables = doc.get_undeclared_template_variables()

            return {"variables": sorted(list(variables))}

        except ImportError as e:
            logger.error("[ASSET-SERVICE] docxtpl not installed: %s", e)
            raise RuntimeError(
                "Template variable extraction requires docxtpl. "
                "Please install it with: pip install docxtpl"
            ) from e
        except Exception as e:
            logger.error("[ASSET-SERVICE] Failed to extract template variables: %s", e)
            raise RuntimeError(
                f"Failed to parse template: {str(e)}. "
                "Ensure the file is a valid .docx with Jinja2 template syntax."
            ) from e
