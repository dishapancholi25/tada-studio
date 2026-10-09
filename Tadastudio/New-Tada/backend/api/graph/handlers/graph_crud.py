"""Graph CRUD operation handlers.

This module provides handler functions for graph create, read, update,
and delete operations.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import unquote

from sqlalchemy.exc import IntegrityError as SQLAlchemyIntegrityError

from backend.models import GraphDefinition
from backend.models.workflow import EnhancedNodeData
from backend.services.authorization import require_workflow_access
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.dependency_injection import get_graph_manager
from backend.services.graph.storage import GraphStorageService
from backend.services.graph.storage.access_control import get_user_workflow_role

from ..constants import (
    LOG_PREFIX,
    MSG_BATCH_UPDATE_APPLIED,
    MSG_GRAPH_CREATED,
    MSG_GRAPH_DELETED,
    MSG_GRAPH_RELOADED,
    MSG_GRAPH_SAVED,
    MSG_WORKFLOW_IMPORTED,
)
from ..dependencies import get_user_identifier
from ..exceptions import (
    ForbiddenError,
    GraphAlreadyExistsError,
    GraphNotFoundError,
    InvalidRequestError,
)
from ..models import (
    CreateGraphRequest,
    DuplicateWorkflowRequest,
    ImportRawWorkflowRequest,
    UpdateWorkflowDescriptionRequest,
    UpdateWorkflowNameRequest,
)

logger = get_logger(__name__)


async def handle_list_graphs(current_user: Dict[str, Any]) -> Dict[str, Any]:
    """List graphs that belong to or are shared with the current user.

    Args:
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and list of graphs
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(f"{LOG_PREFIX} Listing graphs for user '{user_identifier}'")

    graphs = get_graph_manager().list_graphs(user_identifier)
    return {"success": True, "graphs": graphs}


async def handle_create_graph(
    request: CreateGraphRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new graph.

    Args:
        request: Create graph request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, message, and graph data

    Raises:
        GraphAlreadyExistsError: If graph with same name already exists
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Creating graph '{request.name}' for user '{user_identifier}'"
    )

    # Check if graph already exists
    existing_graphs = get_graph_manager().list_graphs(username=user_identifier)
    if any(g["name"] == request.name for g in existing_graphs):
        raise GraphAlreadyExistsError(request.name)

    graph = get_graph_manager().create_graph(
        name=request.name, description=request.description, username=user_identifier
    )

    logger.info(f"{LOG_PREFIX} Graph '{request.name}' created successfully")
    return {
        "success": True,
        "message": MSG_GRAPH_CREATED.format(graph_name=request.name),
        "graph": graph.to_dict(),
    }


async def handle_import_raw_workflow(
    request: ImportRawWorkflowRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Import a workflow by directly storing the raw JSON definition.

    Args:
        request: Import workflow request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, message, and workflow ID

    Raises:
        GraphAlreadyExistsError: If graph with same name already exists
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Importing raw workflow '{request.name}' for user '{user_identifier}'"
    )

    # Check if a workflow with this name already exists for this user.
    # Query the Workflow table directly — the unique constraint lives there,
    # not on GraphDefinition, so list_graphs() can miss the conflict.
    from backend.models.workflows.workflow import Workflow

    with get_db() as db:
        exists = (
            db.query(Workflow.id)
            .filter(
                Workflow.name == request.name,
                Workflow.created_by_user_id == user_identifier,
                Workflow.is_deleted == False,  # noqa: E712
            )
            .first()
        )
    if exists:
        raise GraphAlreadyExistsError(request.name)

    # Store the raw JSON directly in the database
    try:
        result = GraphStorageService.import_raw_workflow(
            name=request.name,
            description=request.description,
            workflow_json=request.workflow_json,
            workspace_id=user_identifier,
            user_identifier=user_identifier,
        )
    except SQLAlchemyIntegrityError:
        raise GraphAlreadyExistsError(request.name)

    if not result:
        raise InvalidRequestError("Failed to import workflow")

    workflow_id = result.get("workflow_id")
    warnings = result.get("warnings", [])

    logger.info(f"{LOG_PREFIX} Workflow '{request.name}' imported successfully")

    response = {
        "success": True,
        "message": MSG_WORKFLOW_IMPORTED.format(workflow_name=request.name),
        "workflow_id": workflow_id,
    }

    # Add warnings if any models were unavailable
    if warnings:
        response["warnings"] = warnings

    return response


async def handle_get_graph(
    graph_name: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Get a specific graph.

    Args:
        graph_name: Name of the graph (URL-encoded)
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and graph data

    Raises:
        GraphNotFoundError: If graph not found
        ForbiddenError: If user doesn't have access to graph
    """
    # URL decode the graph name
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Getting graph '{graph_name}' for user '{user_identifier}'"
    )

    require_workflow_access(current_user, graph_name)

    graph = get_graph_manager().get_graph(graph_name)
    if not graph:
        # Try loading from disk
        graph = get_graph_manager().load_graph(graph_name, username=user_identifier)

    if not graph:
        # Check if graph exists but user doesn't have access
        try:
            with get_db() as db:
                graph_exists = (
                    db.query(GraphDefinition.id)
                    .filter(GraphDefinition.name == graph_name)
                    .first()
                )
                if graph_exists:
                    raise ForbiddenError("You do not have access to this workflow")
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(
                f"{LOG_PREFIX} Error verifying access for graph '{graph_name}': {e}"
            )

        raise GraphNotFoundError(graph_name)

    # Get workflow_role for the user
    workflow_role = None
    workflow_id = getattr(graph, 'workflow_id', None)
    if workflow_id:
        with get_db() as db:
            workflow_role = get_user_workflow_role(db, workflow_id, user_identifier)

    return {
        "success": True,
        "graph": graph.to_dict(),
        "workflow_role": workflow_role,
    }


async def handle_get_graph_by_id(
    workflow_id: str,
    current_user: Dict[str, Any],
    version: Optional[int] = None,
    graph_definition_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get a graph by workflow ID instead of name.

    Args:
        workflow_id: Workflow ID
        current_user: Current user from JWT token
        version: Optional specific version number to load
        graph_definition_id: Optional specific graph definition ID to load

    Returns:
        Dictionary with success status, graph data, workflow ID, and version info

    Raises:
        ForbiddenError: If user doesn't have access
        GraphNotFoundError: If workflow not found
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Getting graph by ID '{workflow_id}' for user '{user_identifier}'"
        f" (version={version}, graph_definition_id={graph_definition_id})"
    )

    # Verify access
    is_admin = current_user.get("is_admin", False)
    if not GraphStorageService.verify_workflow_access(workflow_id, user_identifier, is_admin):
        raise ForbiddenError("Not authorized to access this workflow")

    # Load specific version if requested
    loaded_version = None
    is_latest = True

    if graph_definition_id:
        graph = _load_graph_by_definition_id(graph_definition_id, workflow_id)
        if graph:
            loaded_version, is_latest = _resolve_version_info(graph_definition_id)
    elif version is not None:
        graph = _load_graph_by_version(workflow_id, version, user_identifier)
        if graph:
            loaded_version = version
            is_latest = False  # Will be corrected below if it is latest
            # Check if this version is actually the latest
            with get_db() as db:
                latest = (
                    db.query(GraphDefinition)
                    .filter(
                        GraphDefinition.workflow_id == workflow_id,
                        GraphDefinition.is_latest == True,  # noqa: E712
                    )
                    .first()
                )
                if latest and latest.version == version:
                    is_latest = True
    else:
        graph = GraphStorageService.load_graph_by_workflow_id(
            workflow_id, user_identifier, is_admin
        )
        # Resolve version number for the latest version
        if graph:
            try:
                with get_db() as db:
                    latest = (
                        db.query(GraphDefinition)
                        .filter(
                            GraphDefinition.workflow_id == workflow_id,
                            GraphDefinition.is_latest == True,  # noqa: E712
                        )
                        .first()
                    )
                    if latest:
                        loaded_version = latest.version
                        is_latest = True
            except Exception:
                pass

    if not graph:
        raise GraphNotFoundError(f"workflow_id:{workflow_id}")

    # Store in graph manager's active graphs
    get_graph_manager().active_graphs[graph.name] = graph

    # Get user's role for this workflow
    workflow_role = None
    with get_db() as db:
        workflow_role = get_user_workflow_role(db, workflow_id, user_identifier)

    result = {
        "success": True,
        "graph": graph.to_dict(),
        "workflow_id": workflow_id,
        "workflow_role": workflow_role,
    }
    if loaded_version is not None:
        result["loaded_version"] = loaded_version
        result["is_latest"] = is_latest
    return result


def _load_graph_by_definition_id(
    graph_definition_id: str, workflow_id: str
) -> Optional[Any]:
    """Load a graph by specific graph definition ID."""
    from backend.models.workflow import GraphData

    try:
        with get_db() as db:
            graph_def = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.id == graph_definition_id,
                    GraphDefinition.workflow_id == workflow_id,
                )
                .first()
            )
            if not graph_def:
                return None

            import json

            definition_data = graph_def.definition_json
            if isinstance(definition_data, str):
                definition_data = json.loads(definition_data)

            graph = GraphData.from_dict(definition_data)
            graph.workflow_id = graph_def.workflow_id
            graph.definition_id = str(graph_def.id)
            if not hasattr(graph, "metadata") or graph.metadata is None:
                graph.metadata = {}
            graph.metadata["workspace_id"] = graph_def.workspace_id
            return graph
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error loading graph by definition ID: {e}")
        return None


def _load_graph_by_version(
    workflow_id: str, version: int, user_identifier: str
) -> Optional[Any]:
    """Load a specific version of a graph by workflow ID and version number."""
    from backend.models.workflow import GraphData

    try:
        with get_db() as db:
            graph_def = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.workflow_id == workflow_id,
                    GraphDefinition.version == version,
                )
                .first()
            )
            if not graph_def:
                return None

            import json

            definition_data = graph_def.definition_json
            if isinstance(definition_data, str):
                definition_data = json.loads(definition_data)

            graph = GraphData.from_dict(definition_data)
            graph.workflow_id = graph_def.workflow_id
            graph.definition_id = str(graph_def.id)
            if not hasattr(graph, "metadata") or graph.metadata is None:
                graph.metadata = {}
            graph.metadata["workspace_id"] = graph_def.workspace_id
            return graph
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error loading graph version {version}: {e}")
        return None


def _resolve_version_info(graph_definition_id: str) -> tuple:
    """Resolve version number and is_latest from a graph definition ID."""
    try:
        with get_db() as db:
            graph_def = (
                db.query(GraphDefinition)
                .filter(GraphDefinition.id == graph_definition_id)
                .first()
            )
            if graph_def:
                return graph_def.version, graph_def.is_latest
    except Exception:
        pass
    return None, True


async def handle_get_workflow_versions(
    workflow_id: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Get all versions of a workflow.

    Args:
        workflow_id: Workflow ID
        current_user: Current user from JWT token

    Returns:
        Dictionary with version list

    Raises:
        ForbiddenError: If user doesn't have access
    """
    from sqlalchemy import desc

    user_identifier = get_user_identifier(current_user)

    # Verify access
    is_admin = current_user.get("is_admin", False)
    if not GraphStorageService.verify_workflow_access(workflow_id, user_identifier, is_admin):
        raise ForbiddenError("Not authorized to access this workflow")

    with get_db() as db:
        graph_defs = (
            db.query(GraphDefinition)
            .filter(GraphDefinition.workflow_id == workflow_id)
            .order_by(desc(GraphDefinition.version))
            .all()
        )

        versions = [
            {
                "id": gd.id,
                "version": gd.version,
                "is_latest": gd.is_latest,
                "created_by": gd.created_by,
                "created_at": gd.created_at.isoformat() if gd.created_at else None,
                "file_hash": gd.file_hash,
                "size_bytes": gd.size_bytes,
            }
            for gd in graph_defs
        ]

    return {"success": True, "versions": versions, "workflow_id": workflow_id}


async def handle_delete_graph(
    graph_name: str, username: Optional[str], current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Delete a graph from both database and file system.

    Args:
        graph_name: Name of the graph (URL-encoded)
        username: Optional username override
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and deletion details

    Raises:
        GraphNotFoundError: If graph not found
    """
    # URL decode the graph name
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    is_admin = current_user.get("is_admin", False)
    logger.info(
        f"{LOG_PREFIX} Deleting graph '{graph_name}' for user '{user_identifier}' (admin={is_admin})"
    )

    require_workflow_access(current_user, graph_name)

    # Remove from memory
    if graph_name in get_graph_manager().active_graphs:
        del get_graph_manager().active_graphs[graph_name]

    # Clean up any published workflow record so it doesn't linger
    try:
        from backend.models import PublishedWorkflow

        with get_db() as db:
            db.query(PublishedWorkflow).filter(
                PublishedWorkflow.graph_name == graph_name,
            ).delete()
            db.commit()
    except Exception as e:
        logger.warning(
            f"{LOG_PREFIX} Failed to clean up publication for '{graph_name}': {e}"
        )

    db_deleted = False
    file_deleted = False

    # Remove from database
    try:
        db_deleted = GraphStorageService.delete_graph(
            graph_name,
            workspace_id=user_identifier,
            user_identifier=user_identifier,
            is_admin=is_admin,
        )
        if db_deleted:
            logger.info(f"{LOG_PREFIX} Graph '{graph_name}' deleted from database")
    except Exception as e:
        logger.error(
            f"{LOG_PREFIX} Failed to delete graph '{graph_name}' from database: {e}"
        )

    # Remove from disk (file backup)
    file_workspace = user_identifier or "default"
    user_dir = get_graph_manager().workspace_dir / file_workspace
    file_path = user_dir / f"{graph_name}.json"

    if file_path.exists():
        os.remove(file_path)
        file_deleted = True
        logger.info(f"{LOG_PREFIX} Graph '{graph_name}' deleted from file system")

    if db_deleted or file_deleted:
        return {
            "success": True,
            "message": MSG_GRAPH_DELETED.format(graph_name=graph_name),
            "deleted_from": {"database": db_deleted, "file": file_deleted},
        }

    raise GraphNotFoundError(graph_name)


async def handle_save_graph(
    graph_name: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Save a graph to disk.

    Args:
        graph_name: Name of the graph (URL-encoded)
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and message

    Raises:
        GraphNotFoundError: If graph not found
    """
    from ..dependencies import get_graph_or_404

    # URL decode the graph name
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Saving graph '{graph_name}' for user '{user_identifier}'"
    )

    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    # Perform database save synchronously (fast)
    success = get_graph_manager().save_graph(graph, user_identifier)

    if not success:
        raise InvalidRequestError("Failed to save graph")

    logger.info(f"{LOG_PREFIX} Graph '{graph_name}' saved successfully")

    # Fire evaluation trigger on modify (non-blocking, best-effort)
    try:
        import asyncio

        from backend.services.evaluation.trigger import EvaluationTriggerService

        workflow_id = getattr(graph, "workflow_id", None)
        if workflow_id:
            trigger_service = EvaluationTriggerService()
            asyncio.create_task(
                trigger_service.trigger_on_modify(
                    workflow_id=str(workflow_id),
                    revision=None,
                    user_id=user_identifier,
                )
            )
    except Exception as e:
        logger.warning("Failed to trigger evaluation on modify (save): %s", e)

    return {
        "success": True,
        "message": MSG_GRAPH_SAVED.format(graph_name=graph_name),
    }


async def handle_reload_graph(
    graph_name: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Force reload a graph from disk, bypassing cache.

    Args:
        graph_name: Name of the graph (URL-encoded)
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, message, and graph data

    Raises:
        GraphNotFoundError: If graph not found on disk
    """
    # URL decode the graph name
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Reloading graph '{graph_name}' from disk for user '{user_identifier}'"
    )

    require_workflow_access(current_user, graph_name)

    # Remove from cache if present
    if graph_name in get_graph_manager().active_graphs:
        del get_graph_manager().active_graphs[graph_name]
    # Load fresh from disk
    # Load fresh from disk
    graph = get_graph_manager().load_graph(graph_name, user_identifier)

    if not graph:
        raise GraphNotFoundError(graph_name)

    logger.info(f"{LOG_PREFIX} Graph '{graph_name}' reloaded successfully")
    return {
        "success": True,
        "message": MSG_GRAPH_RELOADED.format(graph_name=graph_name),
        "graph": graph.to_dict(),
    }


async def handle_batch_update(
    request: Dict[str, Any], current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Apply multiple graph changes in a single transaction.

    Args:
        request: Batch update request dictionary
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, message, and updated graph

    Raises:
        InvalidRequestError: If request is invalid
        GraphNotFoundError: If graph not found
    """
    from backend.models.workflow import ConnectionType

    from ..dependencies import get_graph_or_404

    user_identifier = get_user_identifier(current_user)

    graph_name = request.get("graph_name")
    changes = request.get("changes", [])

    if not graph_name:
        raise InvalidRequestError("graph_name is required")

    logger.info(
        f"{LOG_PREFIX} Batch update: {len(changes)} changes for graph '{graph_name}'"
    )

    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    # Apply all changes in order, with error isolation per change.
    # A single failed change (e.g. temp ID not found) must not crash the entire batch.
    errors = []
    applied_count = 0
    for change in changes:
        change_type = change.get("type")
        change_data = change.get("data", {})

        try:
            if change_type == "UPDATE_NODE_POSITION":
                get_graph_manager().update_node(
                    graph_name,
                    change_data.get("nodeId"),
                    {"position": change_data.get("position")},
                )

            elif change_type == "UPDATE_NODE":
                get_graph_manager().update_node(
                    graph_name, change_data.get("nodeId"), change_data.get("updates", {})
                )

            elif change_type == "ADD_NODE":
                # Handle pasted/created nodes
                node_data = change_data.get("node", {})
                if node_data:
                    # Create EnhancedNodeData from the dict
                    node = EnhancedNodeData.from_dict(node_data)
                    # Dedup guard: skip if a node with the same ID already exists
                    existing_ids = {n.uniq_id for n in graph.nodes}
                    if node.uniq_id not in existing_ids:
                        get_graph_manager().add_node_to_graph(graph_name, node)
                        logger.debug(
                            f"{LOG_PREFIX} Added node '{node.name}' to graph '{graph_name}'"
                        )
                    else:
                        logger.warning(
                            f"{LOG_PREFIX} Skipping duplicate ADD_NODE for '{node.name}' "
                            f"(ID: {node.uniq_id}) in graph '{graph_name}'"
                        )

            elif change_type == "DELETE_NODE":
                get_graph_manager().delete_node(graph_name, change_data.get("nodeId"))

            elif change_type == "ADD_CONNECTION":
                connection_type_str = change_data.get("connectionType", "workflow")
                connection_type = ConnectionType.WORKFLOW
                if connection_type_str == "tool":
                    connection_type = ConnectionType.TOOL
                elif connection_type_str == "delegation":
                    connection_type = ConnectionType.DELEGATION

                # Determine true_condition from source_handle for condition nodes
                true_condition = False
                source_handle = change_data.get("sourceHandle")
                if source_handle and "true" in source_handle.lower():
                    true_condition = True

                get_graph_manager().add_connection(
                    graph_name,
                    change_data.get("sourceId"),
                    change_data.get("targetId"),
                    source_handle,
                    change_data.get("targetHandle"),
                    connection_type,
                    change_data.get("label") or "",
                    true_condition,
                )

            elif change_type == "DELETE_CONNECTION":
                get_graph_manager().remove_connection(
                    graph_name, change_data.get("sourceId"), change_data.get("targetId")
                )

            applied_count += 1
        except Exception as e:
            logger.warning(
                f"{LOG_PREFIX} Batch change {change_type} failed for graph '{graph_name}': {e}"
            )
            errors.append({"type": change_type, "error": str(e), "data": change_data})

    # Save graph once after all changes
    graph = get_graph_manager().get_graph(graph_name)
    graph.updated_at = datetime.now().isoformat()

    # Save to database
    success = get_graph_manager().save_graph(graph, user_identifier)

    if not success:
        raise InvalidRequestError("Failed to save changes")

    if errors:
        logger.warning(
            f"{LOG_PREFIX} Applied {applied_count}/{len(changes)} changes to {graph_name} "
            f"({len(errors)} failed: {[e['type'] for e in errors]})"
        )
    else:
        logger.info(
            f"{LOG_PREFIX} Successfully applied {len(changes)} changes to {graph_name}"
        )

    # Fire evaluation trigger on modify (non-blocking, best-effort)
    try:
        import asyncio

        from backend.services.evaluation.trigger import EvaluationTriggerService

        workflow_id = getattr(graph, "workflow_id", None)
        if workflow_id:
            trigger_service = EvaluationTriggerService()
            asyncio.create_task(
                trigger_service.trigger_on_modify(
                    workflow_id=str(workflow_id),
                    revision=None,
                    user_id=user_identifier,
                )
            )
    except Exception as e:
        logger.warning("Failed to trigger evaluation on modify (batch): %s", e)

    # Resolve current version number
    current_version = None
    workflow_id_val = getattr(graph, "workflow_id", None)
    if workflow_id_val:
        try:
            with get_db() as db:
                latest_def = (
                    db.query(GraphDefinition)
                    .filter(
                        GraphDefinition.workflow_id == str(workflow_id_val),
                        GraphDefinition.is_latest == True,  # noqa: E712
                    )
                    .first()
                )
                if latest_def:
                    current_version = latest_def.version
        except Exception:
            pass

    result = {
        "success": True,
        "message": MSG_BATCH_UPDATE_APPLIED.format(
            count=applied_count, graph_name=graph_name
        ),
        "graph": graph.to_dict(),
        "version": current_version,
    }
    if errors:
        result["errors"] = errors
        result["applied"] = applied_count
        result["total"] = len(changes)
    return result


async def handle_update_workflow_name(
    graph_name: str, request: UpdateWorkflowNameRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a workflow's name.

    Args:
        graph_name: Current name of the graph (URL-encoded)
        request: Update workflow name request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, message, and updated graph data

    Raises:
        GraphNotFoundError: If graph not found
        GraphAlreadyExistsError: If new name already exists
        ForbiddenError: If user doesn't have access to graph
    """
    from sqlalchemy.exc import IntegrityError

    from ..dependencies import get_graph_or_404

    # URL decode the graph name
    graph_name = unquote(graph_name)
    new_name = request.new_name.strip()
    user_identifier = get_user_identifier(current_user)

    logger.info(
        f"{LOG_PREFIX} Updating workflow name from '{graph_name}' to '{new_name}' for user '{user_identifier}'"
    )

    # Validate new name
    if not new_name:
        raise InvalidRequestError("New name cannot be empty")

    if graph_name == new_name:
        raise InvalidRequestError("New name must be different from current name")

    # Get the current graph and verify access
    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    # Store old name for rollback
    old_name = graph.name

    # Prepare file paths (but don't modify files yet)
    file_workspace = user_identifier or "default"
    user_dir = get_graph_manager().workspace_dir / file_workspace
    # Sanitize old_name to prevent path traversal
    safe_old_name = os.path.basename(old_name)
    old_file_path = user_dir / f"{safe_old_name}.json"
    # Sanitize new_name to prevent path traversal
    safe_new_name = os.path.basename(new_name)
    new_file_path = user_dir / f"{safe_new_name}.json"

    # Track state for rollback
    db_session = None
    db_updated = False
    file_created = False

    try:
        # Update in-memory graph (will be rolled back on failure)
        graph.name = new_name
        graph.updated_at = datetime.now().isoformat()

        # Update active graphs cache (will be rolled back on failure)
        if old_name in get_graph_manager().active_graphs:
            del get_graph_manager().active_graphs[old_name]
        get_graph_manager().active_graphs[new_name] = graph

        # Update workflow name in database
        # This updates the Workflow table name AND all GraphDefinition records
        db_session = get_db().__enter__()

        # Find the workflow by the graph's workflow_id
        if hasattr(graph, "workflow_id") and graph.workflow_id:
            from backend.models.workflows.workflow import Workflow

            # Use row-level locking to prevent race conditions
            workflow = (
                db_session.query(Workflow)
                .filter(Workflow.id == graph.workflow_id)
                .with_for_update()  # Lock the row for update
                .first()
            )
            if workflow:
                # Check for name conflicts with user scope filtering
                # This ensures User A can have a workflow named "Analysis" even if User B has one too
                existing_workflow = (
                    db_session.query(Workflow)
                    .filter(
                        Workflow.name == new_name,
                        Workflow.id != workflow.id,
                        Workflow.created_by_user_id
                        == workflow.created_by_user_id,  # Same user scope
                    )
                    .first()
                )
                if existing_workflow:
                    raise GraphAlreadyExistsError(new_name)

                # Update workflow name
                workflow.name = new_name
                workflow.updated_at = datetime.now()

                # Update all graph definitions for this workflow to use the new name
                db_session.query(GraphDefinition).filter(
                    GraphDefinition.workflow_id == workflow.id
                ).update({"name": new_name}, synchronize_session=False)

                # Update published_workflows.graph_name so publish/unpublish lookups remain accurate
                from backend.models.workflows.publishing.published_workflow import (
                    PublishedWorkflow,
                )

                db_session.query(PublishedWorkflow).filter(
                    PublishedWorkflow.workflow_id == workflow.id
                ).update({"graph_name": new_name}, synchronize_session=False)

                # Commit database transaction
                db_session.commit()
                db_updated = True
                logger.info(
                    f"{LOG_PREFIX} Updated workflow and all graph definitions to new name '{new_name}'"
                )

        # Database transaction successful - now perform file operations
        # Save the updated graph (creates new file with new name)
        success = get_graph_manager().save_graph(graph, user_identifier)

        if not success:
            raise InvalidRequestError("Failed to save updated graph to file")

        file_created = True
        logger.info(f"{LOG_PREFIX} Created new workflow file: {new_file_path}")

        # Delete old file only after new file is successfully created
        if old_file_path.exists() and old_file_path != new_file_path:
            try:
                os.remove(old_file_path)
                logger.info(f"{LOG_PREFIX} Removed old file: {old_file_path}")
            except Exception as e:
                # Log but don't fail - new file is already created
                logger.warning(
                    f"{LOG_PREFIX} Failed to delete old file (non-critical): {e}"
                )

        logger.info(
            f"{LOG_PREFIX} Workflow name updated from '{old_name}' to '{new_name}' successfully"
        )

        return {
            "success": True,
            "message": f"Workflow renamed from '{old_name}' to '{new_name}'",
            "graph": graph.to_dict(),
            "old_name": old_name,
            "new_name": new_name,
        }

    except GraphAlreadyExistsError:
        # Rollback: restore in-memory state, rollback DB, clean up files
        logger.warning(f"{LOG_PREFIX} Name conflict detected, rolling back changes")

        # Restore in-memory state
        graph.name = old_name
        get_graph_manager().active_graphs[old_name] = graph
        if new_name in get_graph_manager().active_graphs:
            del get_graph_manager().active_graphs[new_name]

        # Rollback database if needed
        if db_session and db_updated:
            try:
                db_session.rollback()
                logger.info(f"{LOG_PREFIX} Database rollback completed")
            except Exception as rb_error:
                logger.error(f"{LOG_PREFIX} Database rollback failed: {rb_error}")

        # Clean up new file if it was created
        if file_created and new_file_path.exists():
            try:
                os.remove(new_file_path)
                logger.info(
                    f"{LOG_PREFIX} Removed new file during rollback: {new_file_path}"
                )
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to remove new file during rollback: {e}"
                )

        raise

    except IntegrityError as e:
        # Handle race condition: another request created the same name
        logger.error(f"{LOG_PREFIX} Database integrity error during rename: {e}")

        # Rollback: restore in-memory state, rollback DB, clean up files
        graph.name = old_name
        get_graph_manager().active_graphs[old_name] = graph
        if new_name in get_graph_manager().active_graphs:
            del get_graph_manager().active_graphs[new_name]

        # Rollback database if needed
        if db_session and db_updated:
            try:
                db_session.rollback()
                logger.info(f"{LOG_PREFIX} Database rollback completed")
            except Exception as rb_error:
                logger.error(f"{LOG_PREFIX} Database rollback failed: {rb_error}")

        # Clean up new file if it was created
        if file_created and new_file_path.exists():
            try:
                os.remove(new_file_path)
                logger.info(
                    f"{LOG_PREFIX} Removed new file during rollback: {new_file_path}"
                )
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to remove new file during rollback: {e}"
                )

        raise GraphAlreadyExistsError(new_name)

    except Exception as e:
        # Rollback: restore in-memory state, rollback DB, clean up files
        logger.error(f"{LOG_PREFIX} Error updating workflow name: {e}")

        graph.name = old_name
        get_graph_manager().active_graphs[old_name] = graph
        if new_name in get_graph_manager().active_graphs:
            del get_graph_manager().active_graphs[new_name]

        # Rollback database if needed
        if db_session and db_updated:
            try:
                db_session.rollback()
                logger.info(f"{LOG_PREFIX} Database rollback completed")
            except Exception as rb_error:
                logger.error(f"{LOG_PREFIX} Database rollback failed: {rb_error}")

        # Clean up new file if it was created
        if file_created and new_file_path.exists():
            try:
                os.remove(new_file_path)
                logger.info(
                    f"{LOG_PREFIX} Removed new file during rollback: {new_file_path}"
                )
            except Exception as e:
                logger.error(
                    f"{LOG_PREFIX} Failed to remove new file during rollback: {e}"
                )

        raise InvalidRequestError(f"Failed to update workflow name: {e}")

    finally:
        # Ensure database session is properly closed
        if db_session:
            try:
                db_session.close()
            except Exception as e:
                logger.error(f"{LOG_PREFIX} Error closing database session: {e}")


async def handle_duplicate_workflow(
    graph_name: str, request: DuplicateWorkflowRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Duplicate a workflow with a new name.

    Args:
        graph_name: Name of the source workflow (URL-encoded)
        request: Duplicate workflow request with new name
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, workflow_id, and message

    Raises:
        GraphAlreadyExistsError: If a workflow with the new name already exists
        GraphNotFoundError: If the source workflow is not found
    """
    graph_name = unquote(graph_name)
    new_name = request.new_name.strip()
    user_identifier = get_user_identifier(current_user)

    logger.info(
        f"{LOG_PREFIX} Duplicating workflow '{graph_name}' as '{new_name}' for user '{user_identifier}'"
    )

    if not new_name:
        raise InvalidRequestError("New name cannot be empty")

    # Check if a workflow with the new name already exists (fast path)
    existing_graphs = get_graph_manager().list_graphs(username=user_identifier)
    if any(g["name"] == new_name for g in existing_graphs):
        raise GraphAlreadyExistsError(new_name)

    try:
        result = GraphStorageService.duplicate_workflow(
            source_graph_name=graph_name,
            new_name=new_name,
            workspace_id=user_identifier,
            user_identifier=user_identifier,
        )
    except SQLAlchemyIntegrityError:
        raise GraphAlreadyExistsError(new_name)
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Error duplicating workflow: {e}")
        raise InvalidRequestError(f"Failed to duplicate workflow: {e}")

    if not result:
        raise GraphNotFoundError(graph_name)

    workflow_id = result["workflow_id"]

    logger.info(
        f"{LOG_PREFIX} Workflow '{graph_name}' duplicated as '{new_name}' (workflow_id={workflow_id})"
    )
    return {
        "success": True,
        "workflow_id": workflow_id,
        "message": f"Workflow duplicated as '{new_name}'",
    }


async def handle_update_workflow_description(
    graph_name: str,
    request: UpdateWorkflowDescriptionRequest,
    current_user: Dict[str, Any],
) -> Dict[str, Any]:
    """Update a workflow's description.

    Args:
        graph_name: Name of the graph (URL-encoded)
        request: Update workflow description request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and message

    Raises:
        GraphNotFoundError: If graph not found
    """
    from ..dependencies import get_graph_or_404

    graph_name = unquote(graph_name)
    new_description = request.description
    user_identifier = get_user_identifier(current_user)

    logger.info(
        f"{LOG_PREFIX} Updating description for workflow '{graph_name}' for user '{user_identifier}'"
    )

    # Get the current graph and verify access
    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    # Update in-memory graph
    graph.description = new_description
    graph.updated_at = datetime.now().isoformat()

    # Update database records
    with get_db() as db:
        if hasattr(graph, "workflow_id") and graph.workflow_id:
            from backend.models.workflows.workflow import Workflow

            workflow = (
                db.query(Workflow).filter(Workflow.id == graph.workflow_id).first()
            )
            if workflow:
                workflow.description = new_description
                workflow.updated_at = datetime.now()

            # Update the latest graph definition description
            db.query(GraphDefinition).filter(
                GraphDefinition.workflow_id == graph.workflow_id,
                GraphDefinition.is_latest == True,  # noqa: E712
            ).update({"description": new_description}, synchronize_session=False)

            db.commit()

    # Save updated graph to file
    get_graph_manager().save_graph(graph, user_identifier)

    logger.info(f"{LOG_PREFIX} Description updated for workflow '{graph_name}'")

    return {
        "success": True,
        "message": f"Workflow description updated for '{graph_name}'",
    }
