"""Template upload handlers for FILE_WRITE nodes.

Handles uploading and deleting custom Word templates (.docx) that are
used by docxtpl to generate branded documents.
"""

import logging
from typing import Any, Dict

from fastapi import UploadFile

from backend.models.workflow.enums import NodeType
from backend.services.authorization import require_workflow_access
from backend.services.dependency_injection import get_graph_manager

logger = logging.getLogger(__name__)


async def handle_upload_node_template(
    graph_name: str,
    node_id: str,
    file: UploadFile,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    """Upload a custom Word template for a FILE_WRITE node.

    Validates the file, extracts template variables, stores the asset,
    and updates the node's file_write_config with the asset reference.

    Args:
        graph_name: Name of the graph/workflow.
        node_id: The FILE_WRITE node's uniq_id.
        file: The uploaded .docx template file.
        current_user: Current authenticated user.

    Returns:
        Success response with asset_id, filename, variables.
    """
    require_workflow_access(current_user, graph_name)

    from backend.api.graph.dependencies import get_graph_or_404, get_user_identifier

    user_id = get_user_identifier(current_user)

    # Validate file extension
    if not file.filename or not file.filename.lower().endswith(".docx"):
        return {
            "success": False,
            "error": "Only .docx files are accepted as templates",
        }

    # Read file content
    content = await file.read()

    if not content:
        return {"success": False, "error": "Uploaded file is empty"}

    # Get the workflow (load from DB if not cached)
    try:
        graph = get_graph_or_404(graph_name, user_id)
    except Exception:
        return {"success": False, "error": f"Workflow '{graph_name}' not found"}

    # Verify the node exists and is a FILE_WRITE node
    node = graph.get_node_by_id(node_id)
    if not node:
        return {"success": False, "error": f"Node '{node_id}' not found"}

    if node.type != NodeType.FILE_WRITE:
        return {
            "success": False,
            "error": f"Node '{node_id}' is type '{node.type}', not FILE_WRITE",
        }

    # Get workflow_id from the graph object
    workflow_id = graph.workflow_id
    if not workflow_id:
        return {"success": False, "error": "Could not determine workflow ID"}

    # Upload the template
    try:
        from backend.services.workflow.asset_service import WorkflowAssetService

        asset_service = WorkflowAssetService()
        asset = asset_service.upload_template(
            workflow_id=workflow_id,
            node_id=node_id,
            filename=file.filename,
            content=content,
        )

        variables = (asset.metadata_json or {}).get("variables", [])

        # Build updated file_write_config with the asset reference
        existing_config = node.file_write_config or {}
        if isinstance(existing_config, dict):
            updated_config = {**existing_config}
        else:
            # Handle dataclass/object config by converting to dict
            try:
                from dataclasses import asdict
                updated_config = asdict(existing_config)
            except Exception:
                updated_config = {}

        updated_config["custom_template_asset_id"] = asset.id
        updated_config["custom_template_variables"] = variables
        updated_config["custom_template_filename"] = file.filename

        # Save the updated node config
        graph_manager = get_graph_manager()
        graph_manager.update_node(
            graph_name,
            node_id,
            {"file_write_config": updated_config},
        )

        logger.info(
            "[TEMPLATE-UPLOAD] Uploaded template '%s' to node '%s' in '%s' "
            "(asset_id=%s, variables=%s)",
            file.filename,
            node_id,
            graph_name,
            asset.id,
            variables,
        )

        return {
            "success": True,
            "asset_id": asset.id,
            "filename": file.filename,
            "file_size": asset.file_size,
            "variables": variables,
        }

    except ValueError as e:
        return {"success": False, "error": str(e)}
    except RuntimeError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("[TEMPLATE-UPLOAD] Upload failed: %s", e)
        return {"success": False, "error": f"Template upload failed: {str(e)}"}


async def handle_delete_node_template(
    graph_name: str,
    node_id: str,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    """Delete the custom Word template from a FILE_WRITE node.

    Removes the asset from the database and clears the template
    reference from the node's file_write_config.

    Args:
        graph_name: Name of the graph/workflow.
        node_id: The FILE_WRITE node's uniq_id.
        current_user: Current authenticated user.

    Returns:
        Success response.
    """
    require_workflow_access(current_user, graph_name)

    from backend.api.graph.dependencies import get_graph_or_404, get_user_identifier

    user_id = get_user_identifier(current_user)

    # Get the workflow (load from DB if not cached)
    try:
        graph = get_graph_or_404(graph_name, user_id)
    except Exception:
        return {"success": False, "error": f"Workflow '{graph_name}' not found"}

    # Find the node
    node = graph.get_node_by_id(node_id)
    if not node:
        return {"success": False, "error": f"Node '{node_id}' not found"}

    # Get the current asset_id from the node's config
    config = node.file_write_config or {}
    if isinstance(config, dict):
        asset_id = config.get("custom_template_asset_id")
    else:
        asset_id = getattr(config, "custom_template_asset_id", None)

    if asset_id:
        try:
            from backend.services.workflow.asset_service import WorkflowAssetService

            asset_service = WorkflowAssetService()
            asset_service.delete_template(asset_id)
        except Exception as e:
            logger.warning(
                "[TEMPLATE-UPLOAD] Failed to delete asset %s: %s", asset_id, e
            )

    # Build cleared config without template fields
    if isinstance(config, dict):
        updated_config = {
            k: v
            for k, v in config.items()
            if k not in {
                "custom_template_asset_id",
                "custom_template_variables",
                "custom_template_filename",
            }
        }
    else:
        try:
            from dataclasses import asdict
            updated_config = {
                k: v
                for k, v in asdict(config).items()
                if k not in {
                    "custom_template_asset_id",
                    "custom_template_variables",
                    "custom_template_filename",
                }
            }
        except Exception:
            updated_config = {}

    graph_manager = get_graph_manager()
    graph_manager.update_node(
        graph_name,
        node_id,
        {"file_write_config": updated_config},
    )

    logger.info(
        "[TEMPLATE-UPLOAD] Deleted template from node '%s' in '%s'",
        node_id,
        graph_name,
    )

    return {"success": True, "message": "Template removed"}
