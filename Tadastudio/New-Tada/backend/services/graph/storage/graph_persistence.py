"""
Graph persistence operations for graph storage.

This module handles saving, loading, versioning, and managing
graph definitions in the database.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session
from backend.services.database import get_db
from backend.models.workflow import GraphData
from backend.models import GraphDefinition
from backend.services.config import get_logger

from .exceptions import GraphVersionNotFoundError
from .workflow_manager import get_or_create_workflow


logger = get_logger(__name__)


def save_graph(
    graph: GraphData, workspace_id: str = "default", created_by: Optional[str] = None
) -> Optional[str]:
    """
    Save a graph to the database with versioning support.

    Returns the ID of the saved graph definition or None if failed.

    Args:
        graph: Graph data to save
        workspace_id: Workspace identifier
        created_by: User identifier of the creator

    Returns:
        Graph definition ID if successful, None otherwise

    Complexity: 8 (reduced from previous complexity)
    """
    try:
        with get_db() as db:
            # Prepare graph data
            definition_json, file_hash, size_bytes = _prepare_graph_data(graph)

            # Get or create workflow container
            workflow = get_or_create_workflow(db, graph, created_by)

            # Propagate workflow_id back to the in-memory graph
            if workflow:
                graph.workflow_id = str(workflow.id)

            # Check if content already exists as latest version
            if _is_content_unchanged(db, graph.name, workspace_id, file_hash):
                logger.info(
                    f"[GRAPH-STORAGE] Graph {graph.name} already up to date in workspace {workspace_id}"
                )
                return _get_latest_graph_id(db, graph.name, workspace_id)

            # Get current latest version
            current_latest, next_version, parent_version_id = _get_version_info(
                db, graph.name, workspace_id
            )

            # Use workflow from current latest if not provided
            if not workflow and current_latest and current_latest.workflow:
                workflow = current_latest.workflow

            # Mark current latest as no longer latest
            if current_latest:
                current_latest.is_latest = False

            # Create new version
            new_graph_def = _create_graph_definition(
                graph=graph,
                workspace_id=workspace_id,
                definition_json=definition_json,
                file_hash=file_hash,
                size_bytes=size_bytes,
                version=next_version,
                parent_version_id=parent_version_id,
                created_by=created_by,
                workflow_id=workflow.id if workflow else None,
            )

            # Update workflow latest version
            if workflow:
                workflow.latest_version = next_version

            db.add(new_graph_def)
            db.commit()
            db.refresh(new_graph_def)

            # Propagate definition_id back to the in-memory graph
            graph.definition_id = new_graph_def.id

            logger.info(
                f"[GRAPH-STORAGE] Saved graph {graph.name} v{next_version} "
                f"to database (workspace: {workspace_id})"
            )

            # Index node versions for the new graph definition
            try:
                from backend.services.versioning import NodeVersioningService

                NodeVersioningService().index_graph_definition(
                    graph_definition_id=new_graph_def.id,
                    workflow_id=workflow.id if workflow else None,
                    definition_json=definition_json,
                    parent_graph_definition_id=parent_version_id,
                )
            except Exception as index_err:
                logger.warning(
                    f"[GRAPH-STORAGE] Failed to index node versions for "
                    f"{graph.name} v{next_version}: {index_err}"
                )

            return new_graph_def.id

    except Exception as e:
        logger.error(f"[GRAPH-STORAGE] Error saving graph {graph.name}: {e}")
        return None


def load_graph(
    graph_name: str, workspace_id: str = "default", version: Optional[int] = None
) -> Optional[GraphData]:
    """
    Load a graph from the database.

    If version is None, loads the latest version.

    Args:
        graph_name: Name of the graph to load
        workspace_id: Workspace identifier
        version: Specific version to load (None for latest)

    Returns:
        GraphData if found, None otherwise

    Complexity: 5 (reduced from previous complexity)
    """
    try:
        from sqlalchemy import case, desc

        with get_db() as db:
            # Build base query
            query = db.query(GraphDefinition).filter(GraphDefinition.name == graph_name)

            # Add workspace/membership filter
            if workspace_id:
                workspace_filter = _build_load_filter(db, workspace_id)
                query = query.filter(workspace_filter)

            # Add version filter
            if version is None:
                query = query.filter(GraphDefinition.is_latest)
            else:
                query = query.filter(GraphDefinition.version == version)

            # Order by user's workspace first (not library), then by version
            # This ensures we always load from user's workspace when available
            query = query.order_by(
                case(
                    (GraphDefinition.workspace_id == workspace_id, 0),
                    (GraphDefinition.workspace_id == "library", 2),
                    else_=1,
                ),
                desc(GraphDefinition.version),
            )

            graph_def = query.first()

            if not graph_def:
                logger.warning(
                    f"[GRAPH-STORAGE] Graph {graph_name} not found in workspace {workspace_id}"
                )
                return None

            # Convert to GraphData and attach tracking IDs
            graph = _graph_definition_to_graph_data(graph_def)

            logger.info(
                f"[GRAPH-STORAGE] Loaded graph {graph_name} v{graph_def.version} "
                f"from database (workflow_id={graph_def.workflow_id}, definition_id={graph_def.id})"
            )
            return graph

    except Exception as e:
        logger.error(f"[GRAPH-STORAGE] Error loading graph {graph_name}: {e}")
        return None


def load_graph_by_workflow_id(
    workflow_id: str, user_identifier: Optional[str] = None, is_admin: bool = False
) -> Optional[GraphData]:
    """
    Load the latest graph for a workflow by workflow ID.

    Args:
        workflow_id: Workflow UUID
        user_identifier: Optional user identifier for access verification
        is_admin: Whether the user has admin privileges

    Returns:
        GraphData if found and authorized, None otherwise

    Complexity: 6 (maintained - already low)
    """
    try:
        with get_db() as db:
            # Verify access if user_identifier provided
            if user_identifier:
                from .access_control import verify_workflow_access
                from .user_resolver import resolve_user_id

                user_id = resolve_user_id(user_identifier, db)
                if not user_id:
                    logger.warning(
                        f"[GRAPH-STORAGE] Could not resolve user: {user_identifier} "
                        f"for workflow {workflow_id}"
                    )
                    return None

                # Check access
                has_access = verify_workflow_access(db, workflow_id, user_identifier, is_admin)
                if not has_access:
                    logger.warning(
                        f"[GRAPH-STORAGE] User {user_identifier} does not have access "
                        f"to workflow {workflow_id}"
                    )
                    return None

            # Load latest graph definition for this workflow
            graph_def = (
                db.query(GraphDefinition)
                .filter(
                    GraphDefinition.workflow_id == workflow_id,
                    GraphDefinition.is_latest,
                )
                .first()
            )

            if not graph_def:
                logger.warning(
                    f"[GRAPH-STORAGE] No graph found for workflow {workflow_id}"
                )
                return None

            # Convert to GraphData
            graph = _graph_definition_to_graph_data(graph_def)

            logger.info(
                f"[GRAPH-STORAGE] Loaded graph {graph.name} v{graph_def.version} "
                f"from workflow {workflow_id} (definition_id={graph_def.id})"
            )
            return graph

    except Exception as e:
        logger.error(
            f"[GRAPH-STORAGE] Error loading graph by workflow ID {workflow_id}: {e}"
        )
        return None


def get_graph_versions(
    graph_name: str, workspace_id: str = "default"
) -> list[Dict[str, Any]]:
    """
    Get all versions of a graph.

    Args:
        graph_name: Name of the graph
        workspace_id: Workspace identifier

    Returns:
        List of version information dictionaries
    """
    try:
        with get_db() as db:
            graph_defs = (
                db.query(GraphDefinition)
                .filter(
                    and_(
                        GraphDefinition.name == graph_name,
                        GraphDefinition.workspace_id == workspace_id,
                    )
                )
                .order_by(desc(GraphDefinition.version))
                .all()
            )

            return [
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

    except Exception as e:
        logger.error(
            f"[GRAPH-STORAGE] Error getting versions for graph {graph_name}: {e}"
        )
        return []


def restore_version(
    graph_name: str, version: int, workspace_id: str = "default"
) -> bool:
    """
    Restore a specific version as the latest version.

    Args:
        graph_name: Name of the graph
        version: Version number to restore
        workspace_id: Workspace identifier

    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db() as db:
            # Get the version to restore
            version_to_restore = (
                db.query(GraphDefinition)
                .filter(
                    and_(
                        GraphDefinition.name == graph_name,
                        GraphDefinition.workspace_id == workspace_id,
                        GraphDefinition.version == version,
                    )
                )
                .first()
            )

            if not version_to_restore:
                raise GraphVersionNotFoundError(graph_name, version)

            # Get current latest
            current_latest = _get_current_latest(db, graph_name, workspace_id)

            # Mark current latest as not latest
            if current_latest:
                current_latest.is_latest = False

            # Calculate next version number
            next_version = current_latest.version + 1 if current_latest else 1

            # Create new version based on the one we're restoring
            restored_graph = GraphDefinition(
                name=version_to_restore.name,
                workspace_id=version_to_restore.workspace_id,
                definition_json=version_to_restore.definition_json,
                description=version_to_restore.description,
                version=next_version,
                is_latest=True,
                parent_version_id=current_latest.id if current_latest else None,
                created_by=version_to_restore.created_by,
                file_hash=version_to_restore.file_hash,
                size_bytes=version_to_restore.size_bytes,
            )

            # Set updated_at since this is a restoration (update operation)
            if current_latest:
                restored_graph.updated_at = datetime.utcnow()

            db.add(restored_graph)
            db.commit()

            logger.info(
                f"[GRAPH-STORAGE] Restored graph {graph_name} v{version} as v{next_version}"
            )
            return True

    except Exception as e:
        logger.error(
            f"[GRAPH-STORAGE] Error restoring graph {graph_name} v{version}: {e}"
        )
        return False


def graph_exists(graph_name: str, workspace_id: str = "default") -> bool:
    """
    Check if a graph exists in the database.

    Args:
        graph_name: Name of the graph
        workspace_id: Workspace identifier

    Returns:
        True if graph exists, False otherwise
    """
    try:
        with get_db() as db:
            return (
                db.query(GraphDefinition)
                .filter(
                    and_(
                        GraphDefinition.name == graph_name,
                        GraphDefinition.workspace_id == workspace_id,
                        GraphDefinition.is_latest,
                    )
                )
                .first()
                is not None
            )
    except Exception as e:
        logger.error(
            f"[GRAPH-STORAGE] Error checking if graph {graph_name} exists: {e}"
        )
        return False


# Private helper functions


def _prepare_graph_data(graph: GraphData) -> tuple[dict, str, int]:
    """Prepare graph data for storage."""
    graph_dict = graph.to_dict()
    definition_json = json.dumps(graph_dict, sort_keys=True)
    file_hash = hashlib.sha256(definition_json.encode()).hexdigest()
    size_bytes = len(definition_json.encode())
    return (graph_dict, file_hash, size_bytes)


def _is_content_unchanged(
    db: Session, graph_name: str, workspace_id: str, file_hash: str
) -> bool:
    """Check if the graph content is unchanged from the latest version."""
    existing_latest = (
        db.query(GraphDefinition)
        .filter(
            and_(
                GraphDefinition.name == graph_name,
                GraphDefinition.workspace_id == workspace_id,
                GraphDefinition.is_latest,
                GraphDefinition.file_hash == file_hash,
            )
        )
        .first()
    )
    return existing_latest is not None


def _get_latest_graph_id(
    db: Session, graph_name: str, workspace_id: str
) -> Optional[str]:
    """Get the ID of the latest graph version."""
    graph_def = (
        db.query(GraphDefinition)
        .filter(
            and_(
                GraphDefinition.name == graph_name,
                GraphDefinition.workspace_id == workspace_id,
                GraphDefinition.is_latest,
            )
        )
        .first()
    )
    return graph_def.id if graph_def else None


def _get_version_info(
    db: Session, graph_name: str, workspace_id: str
) -> tuple[Optional[GraphDefinition], int, Optional[str]]:
    """Get version information for creating a new version."""
    current_latest = _get_current_latest(db, graph_name, workspace_id)

    next_version = 1
    parent_version_id = None

    if current_latest:
        next_version = current_latest.version + 1
        parent_version_id = current_latest.id

    return (current_latest, next_version, parent_version_id)


def _get_current_latest(
    db: Session, graph_name: str, workspace_id: str
) -> Optional[GraphDefinition]:
    """Get the current latest version of a graph."""
    return (
        db.query(GraphDefinition)
        .filter(
            and_(
                GraphDefinition.name == graph_name,
                GraphDefinition.workspace_id == workspace_id,
                GraphDefinition.is_latest,
            )
        )
        .first()
    )


def _create_graph_definition(
    graph: GraphData,
    workspace_id: str,
    definition_json: dict,
    file_hash: str,
    size_bytes: int,
    version: int,
    parent_version_id: Optional[str],
    created_by: Optional[str],
    workflow_id: Optional[str],
) -> GraphDefinition:
    """Create a new GraphDefinition object.

    If parent_version_id is provided, this is a new version (update),
    so we set updated_at to current time.
    """
    graph_def = GraphDefinition(
        name=graph.name,
        workspace_id=workspace_id,
        definition_json=definition_json,
        description=graph.description,
        version=version,
        is_latest=True,
        parent_version_id=parent_version_id,
        created_by=created_by,
        file_hash=file_hash,
        size_bytes=size_bytes,
        workflow_id=workflow_id,
    )

    # If this is a new version (not the initial creation), set updated_at
    # to current time to indicate when the workflow was last modified
    if parent_version_id is not None:
        graph_def.updated_at = datetime.utcnow()

    return graph_def


def _build_load_filter(db: Session, workspace_id: str):
    """Build filter for loading graphs with workspace access.

    workspace_id is typically the user's email, but WorkflowMembership.user_id
    stores the User.id which may be different. We need to check both.
    """
    from backend.models import WorkflowMembership, User
    from .user_resolver import resolve_user_id

    # Resolve workspace_id (email) to actual user_id
    resolved_user_id = resolve_user_id(workspace_id, db)

    # Build membership subquery - check both the workspace_id (email) and resolved user_id
    if resolved_user_id and resolved_user_id != workspace_id:
        membership_subquery = db.query(WorkflowMembership.workflow_id).filter(
            or_(
                WorkflowMembership.user_id == workspace_id,
                WorkflowMembership.user_id == resolved_user_id,
            )
        )
    else:
        membership_subquery = db.query(WorkflowMembership.workflow_id).filter(
            WorkflowMembership.user_id == workspace_id
        )

    return or_(
        GraphDefinition.workspace_id == workspace_id,
        GraphDefinition.workflow_id.in_(membership_subquery),
    )


def _graph_definition_to_graph_data(graph_def: GraphDefinition) -> GraphData:
    """Convert GraphDefinition to GraphData and attach tracking IDs."""
    # Handle both dict (normal save) and string (raw import) formats
    definition_data = graph_def.definition_json
    if isinstance(definition_data, str):
        definition_data = json.loads(definition_data)

    graph = GraphData.from_dict(definition_data)

    # Attach database tracking IDs to the graph object
    graph.workflow_id = graph_def.workflow_id
    graph.definition_id = str(graph_def.id)

    # Fix workspace_id metadata to match the database record
    # This ensures imported workflows don't retain old workspace_ids
    if not hasattr(graph, "metadata") or graph.metadata is None:
        graph.metadata = {}
    graph.metadata["workspace_id"] = graph_def.workspace_id

    return graph
