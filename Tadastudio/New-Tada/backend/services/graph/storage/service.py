"""
Main graph storage service.

This service provides the primary API for graph storage operations,
delegating to specialized modules for specific functionality.
"""

import hashlib
import json
import secrets
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session
from backend.services.database import get_db
from backend.models import GraphDefinition, Workflow, WorkflowMembership, WorkflowRole
from backend.models.workflow.graph import GraphData
from backend.services.config import get_logger

from .access_control import verify_workflow_access as _verify_workflow_access
from .graph_persistence import (
    get_graph_versions,
    graph_exists,
    load_graph,
    load_graph_by_workflow_id,
    restore_version,
    save_graph,
)
from .query_builder import get_workspace_membership_info

# Import specialized modules
from .user_resolver import resolve_user_id


logger = get_logger(__name__)


class GraphStorageService:
    """Service for managing graph storage in database with versioning support."""

    # Expose graph persistence operations as static methods
    save_graph = staticmethod(save_graph)
    load_graph = staticmethod(load_graph)
    load_graph_by_workflow_id = staticmethod(load_graph_by_workflow_id)
    get_graph_versions = staticmethod(get_graph_versions)
    restore_version = staticmethod(restore_version)
    graph_exists = staticmethod(graph_exists)

    @staticmethod
    def verify_workflow_access(workflow_id: str, user_identifier: str, is_admin: bool = False) -> bool:
        """
        Verify user has access to a workflow.

        Args:
            workflow_id: Workflow UUID
            user_identifier: Email (for AIPE users) or sub (for legacy Azure AD users)
            is_admin: Whether the user has admin privileges

        Returns:
            True if user has access, False otherwise
        """
        try:
            with get_db() as db:
                return _verify_workflow_access(db, workflow_id, user_identifier, is_admin)
        except Exception as e:
            logger.error(f"[GRAPH-STORAGE] Error verifying workflow access: {e}")
            return False

    @staticmethod
    def import_raw_workflow(
        name: str,
        description: str,
        workflow_json: Dict[str, Any],
        workspace_id: str,
        user_identifier: str,
    ) -> Optional[str]:
        """
        Import a workflow by directly storing raw JSON (no validation).

        Args:
            name: Workflow name
            description: Workflow description
            workflow_json: Complete workflow JSON definition
            workspace_id: Workspace identifier
            user_identifier: User identifier

        Returns:
            workflow_id if successful, None otherwise
        """
        try:
            with get_db() as db:
                # Resolve user ID
                user_id = resolve_user_id(user_identifier, db)

                # Validate and fix LLM configurations in agent nodes
                warnings = _validate_and_fix_agent_llm_configs(workflow_json)

                # Create workflow record
                workflow_id = str(uuid.uuid4())
                workflow = Workflow(
                    id=workflow_id,
                    name=name,
                    description=description,
                    created_by_user_id=user_id,
                    is_deleted=False,
                    http_trigger_token="wf_" + secrets.token_urlsafe(32),
                )
                db.add(workflow)
                db.flush()

                # Create owner membership so the workflow can be deleted later
                if user_id:
                    membership = WorkflowMembership(
                        workflow_id=workflow_id,
                        user_id=user_id,
                        role=WorkflowRole.OWNER,
                    )
                    db.add(membership)
                    logger.debug(
                        f"[GRAPH-STORAGE] Created owner membership for workflow: {workflow_id}"
                    )

                # Convert JSON to string
                definition_str = json.dumps(workflow_json)
                definition_bytes = definition_str.encode("utf-8")
                file_hash = hashlib.sha256(definition_bytes).hexdigest()

                # Create graph definition
                graph_def = GraphDefinition(
                    id=str(uuid.uuid4()),
                    name=name,
                    workspace_id=workspace_id,
                    workflow_id=workflow_id,
                    definition_json=definition_str,
                    description=description,
                    version=1,
                    is_latest=True,
                    parent_version_id=None,
                    created_by=user_identifier,
                    file_hash=file_hash,
                    size_bytes=len(definition_bytes),
                )
                db.add(graph_def)
                db.commit()

                logger.info(
                    f"[GRAPH-STORAGE] Raw workflow imported: {name} (workflow_id={workflow_id})"
                )
                return {"workflow_id": workflow_id, "warnings": warnings}

        except Exception as e:
            logger.error(f"[GRAPH-STORAGE] Error importing raw workflow: {e}")
            return None

    @staticmethod
    def duplicate_workflow(
        source_graph_name: str,
        new_name: str,
        workspace_id: str,
        user_identifier: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Duplicate an existing workflow with a new name.

        Creates a new Workflow, GraphDefinition, and WorkflowMembership
        by cloning the source workflow's latest definition.

        Args:
            source_graph_name: Name of the workflow to duplicate
            new_name: Name for the new workflow
            workspace_id: Workspace identifier (typically user email)
            user_identifier: User identifier

        Returns:
            Dict with workflow_id if successful, None if source not found.
            Raises on DB/serialization errors so the caller can map to the correct HTTP status.
        """
        with get_db() as db:
            # Resolve user ID
            user_id = resolve_user_id(user_identifier, db)

            # Get access info for the current user
            accessible_workflow_ids, _ = _get_access_info(workspace_id, db)

            # Find the source workflow's latest graph definition (with access control)
            source_query = (
                db.query(GraphDefinition)
                .join(Workflow, GraphDefinition.workflow_id == Workflow.id)
                .filter(
                    GraphDefinition.name == source_graph_name,
                    GraphDefinition.is_latest.is_(True),
                    Workflow.is_deleted.is_(False),
                )
            )
            source_query = _apply_access_filter(
                source_query, workspace_id, accessible_workflow_ids
            )
            source_def = source_query.first()

            if not source_def:
                logger.warning(
                    f"[GRAPH-STORAGE] Source workflow not found or not accessible: {source_graph_name}"
                )
                return None

            # Parse the definition and update the name
            definition_dict = (
                json.loads(source_def.definition_json)
                if isinstance(source_def.definition_json, str)
                else source_def.definition_json
            )
            graph_data = GraphData.from_dict(definition_dict)
            graph_data.name = new_name

            # Serialize updated definition
            updated_definition_dict = graph_data.to_dict()
            definition_str = json.dumps(updated_definition_dict)
            definition_bytes = definition_str.encode("utf-8")
            file_hash = hashlib.sha256(definition_bytes).hexdigest()

            # Create new workflow record
            new_workflow_id = str(uuid.uuid4())
            new_workflow = Workflow(
                id=new_workflow_id,
                name=new_name,
                description=source_def.description or "",
                created_by_user_id=user_id,
                is_deleted=False,
                http_trigger_token="wf_" + secrets.token_urlsafe(32),
            )
            db.add(new_workflow)
            db.flush()

            # Create owner membership
            if user_id:
                membership = WorkflowMembership(
                    workflow_id=new_workflow_id,
                    user_id=user_id,
                    role=WorkflowRole.OWNER,
                )
                db.add(membership)

            # Create new graph definition
            new_graph_def = GraphDefinition(
                id=str(uuid.uuid4()),
                name=new_name,
                workspace_id=workspace_id,
                workflow_id=new_workflow_id,
                definition_json=definition_str,
                description=source_def.description or "",
                version=1,
                is_latest=True,
                parent_version_id=None,
                created_by=user_identifier,
                file_hash=file_hash,
                size_bytes=len(definition_bytes),
            )
            db.add(new_graph_def)
            db.commit()

            logger.info(
                f"[GRAPH-STORAGE] Duplicated workflow '{source_graph_name}' -> '{new_name}' (workflow_id={new_workflow_id})"
            )
            return {"workflow_id": new_workflow_id}

    @staticmethod
    def list_graphs(
        workspace_id: str = "default", include_versions: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all graphs in a workspace.

        If include_versions is False, only returns latest versions.

        Args:
            workspace_id: Can be either email (for AIPE users) or user_id (legacy)
            include_versions: Whether to include all versions or just latest

        Returns:
            List of graph information dictionaries

        Complexity: 7 (reduced from 13)
        """
        try:
            with get_db() as db:
                # Build base query
                query = db.query(GraphDefinition)

                if not include_versions:
                    query = query.filter(GraphDefinition.is_latest)

                # Get membership information
                accessible_workflow_ids, membership_roles = _get_access_info(
                    workspace_id, db
                )

                # Apply access filter
                query = _apply_access_filter(
                    query, workspace_id, accessible_workflow_ids
                )

                # Execute query
                graph_defs = query.order_by(
                    GraphDefinition.name, desc(GraphDefinition.version)
                ).all()

                # Deduplicate by graph name (prefer non-library workspaces)
                graph_defs = _deduplicate_graphs(graph_defs, workspace_id)

                # Pre-fetch owner names and sharing info for all workflows
                workflow_ids = [
                    gd.workflow_id for gd in graph_defs if gd.workflow_id
                ]
                owner_names = _get_owner_names(workflow_ids, db)
                sharing_counts = _get_sharing_counts(workflow_ids, db)

                # Format results
                result = _format_graph_list(
                    graph_defs, membership_roles, owner_names, sharing_counts
                )

                logger.debug(
                    f"[GRAPH-STORAGE] Listed {len(result)} graphs for workspace {workspace_id}"
                )
                return result

        except Exception as e:
            logger.error(
                f"[GRAPH-STORAGE] Error listing graphs in workspace {workspace_id}: {e}"
            )
            return []

    @staticmethod
    def delete_graph(
        graph_name: str,
        workspace_id: str = "default",
        version: Optional[int] = None,
        user_identifier: Optional[str] = None,
        is_admin: bool = False,
    ) -> bool:
        """
        Delete a graph or specific version.

        If version is None, deletes all versions of the graph.

        Args:
            graph_name: Name of the graph to delete
            workspace_id: Workspace identifier
            version: Specific version to delete (None for all)
            user_identifier: User identifier for permission checking
            is_admin: Whether the user has admin privileges

        Returns:
            True if deletion successful, False otherwise

        Complexity: 9 (reduced from 19)
        """
        try:
            with get_db() as db:
                # Build delete query with access control
                query = _build_delete_query(
                    db, graph_name, workspace_id, user_identifier, is_admin
                )

                if version is not None:
                    # Delete specific version
                    return _delete_specific_version(db, query, version)
                else:
                    # Delete all versions
                    return _delete_all_versions(db, query, graph_name)

        except Exception as e:
            logger.error(f"[GRAPH-STORAGE] Error deleting graph {graph_name}: {e}")
            return False


# Private helper functions for list_graphs


def _get_access_info(
    workspace_id: str, db: Session
) -> tuple[List[str], Dict[str, str]]:
    """Get accessible workflow IDs and membership roles."""
    if not workspace_id:
        return ([], {})

    accessible_workflow_ids, membership_roles = get_workspace_membership_info(
        workspace_id, db
    )

    return (accessible_workflow_ids, membership_roles)


def _apply_access_filter(query, workspace_id: str, accessible_workflow_ids: List[str]):
    """Apply workspace and membership access filters to query."""
    if not workspace_id:
        return query

    ownership_condition = GraphDefinition.workspace_id == workspace_id

    if accessible_workflow_ids:
        membership_condition = GraphDefinition.workflow_id.in_(accessible_workflow_ids)
        return query.filter(or_(ownership_condition, membership_condition))
    else:
        return query.filter(ownership_condition)


def _deduplicate_graphs(
    graph_defs: List[GraphDefinition], workspace_id: str
) -> List[GraphDefinition]:
    """
    Deduplicate graph definitions by name, preferring user's workspace over library.

    When multiple workflows with the same name exist (e.g., original + library copy),
    this ensures only one is shown, preferring the user's workspace version.

    Args:
        graph_defs: List of graph definitions to deduplicate
        workspace_id: User's workspace ID to prioritize

    Returns:
        Deduplicated list of graph definitions
    """
    seen_names = {}

    for graph_def in graph_defs:
        name = graph_def.name
        if name not in seen_names:
            seen_names[name] = graph_def
        else:
            existing = seen_names[name]
            # Prefer user's workspace over library
            if (
                graph_def.workspace_id == workspace_id
                and existing.workspace_id != workspace_id
            ):
                seen_names[name] = graph_def
            # If both in same workspace type, prefer higher version (already sorted)
            elif (
                graph_def.workspace_id == existing.workspace_id
                and graph_def.version > existing.version
            ):
                seen_names[name] = graph_def

    return list(seen_names.values())


def _get_owner_names(workflow_ids: List[str], db: Session) -> Dict[str, str]:
    """Get owner display names for a list of workflow IDs.

    Tries to resolve via User.id first, then falls back to User.email
    for legacy workflows where created_by_user_id may store an email.
    """
    if not workflow_ids:
        return {}
    from backend.models import User

    # Try matching by user ID
    rows = (
        db.query(Workflow.id, User.name, User.email)
        .join(User, Workflow.created_by_user_id == User.id)
        .filter(Workflow.id.in_(workflow_ids))
        .all()
    )
    result = {}
    for wf_id, name, email in rows:
        display = name or email
        if display:
            result[wf_id] = display

    # For any workflows not resolved, try matching created_by_user_id as email
    missing = [wid for wid in workflow_ids if wid not in result]
    if missing:
        wf_rows = (
            db.query(Workflow.id, Workflow.created_by_user_id)
            .filter(Workflow.id.in_(missing), Workflow.created_by_user_id.isnot(None))
            .all()
        )
        owner_ids = {wf_id: uid for wf_id, uid in wf_rows}
        if owner_ids:
            email_matches = (
                db.query(User.email, User.name)
                .filter(User.email.in_(list(owner_ids.values())))
                .all()
            )
            email_to_display = {email: (name or email) for email, name in email_matches}
            for wf_id, uid in owner_ids.items():
                if wf_id not in result and uid in email_to_display:
                    result[wf_id] = email_to_display[uid]
                elif wf_id not in result and uid:
                    # Last resort: use the raw created_by_user_id value
                    result[wf_id] = uid

    return result


def _get_sharing_counts(workflow_ids: List[str], db: Session) -> Dict[str, int]:
    """Get count of non-owner memberships for each workflow (i.e. shared-with users)."""
    if not workflow_ids:
        return {}
    from sqlalchemy import func

    rows = (
        db.query(WorkflowMembership.workflow_id, func.count(WorkflowMembership.id))
        .filter(
            WorkflowMembership.workflow_id.in_(workflow_ids),
            WorkflowMembership.role != WorkflowRole.OWNER,
        )
        .group_by(WorkflowMembership.workflow_id)
        .all()
    )
    return {wf_id: cnt for wf_id, cnt in rows}


def _format_graph_list(
    graph_defs: List[GraphDefinition],
    membership_roles: Dict[str, str],
    owner_names: Dict[str, str],
    sharing_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Format graph definitions into result dictionaries."""
    result = []

    for graph_def in graph_defs:
        # Parse definition JSON
        definition = _parse_graph_definition(graph_def.definition_json)

        # Count nodes by type
        nodes = definition.get("nodes", [])
        agent_count = len([n for n in nodes if n.get("type") == "AGENT"])
        tool_count = len([n for n in nodes if n.get("type") == "TOOL"])

        wf_id = graph_def.workflow_id

        # Build result dictionary
        result.append(
            {
                "id": graph_def.id,
                "name": graph_def.name,
                "description": graph_def.description,
                "version": graph_def.version,
                "is_latest": graph_def.is_latest,
                "created_by": graph_def.created_by,
                "created_at": graph_def.created_at.isoformat()
                if graph_def.created_at
                else None,
                "updated_at": graph_def.updated_at.isoformat()
                if graph_def.updated_at
                else None,
                "size_bytes": graph_def.size_bytes,
                "node_count": len(nodes),
                "is_subgraph": definition.get("is_subgraph", False),
                "has_llm_config": definition.get("default_llm_config") is not None,
                "agent_count": agent_count,
                "tool_count": tool_count,
                "source": "database",
                "workflow_id": wf_id,
                "workflow_role": membership_roles.get(wf_id) if wf_id else None,
                "owner_user_id": graph_def.workflow.created_by_user_id
                if graph_def.workflow
                else graph_def.created_by,
                "owner_name": owner_names.get(wf_id) if wf_id else None,
                "is_shared": sharing_counts.get(wf_id, 0) > 0 if wf_id else False,
            }
        )

    return result


def _parse_graph_definition(definition_json) -> dict:
    """Parse graph definition JSON safely."""
    if isinstance(definition_json, str):
        try:
            return json.loads(definition_json)
        except Exception:
            return {}
    elif definition_json is None:
        return {}
    return definition_json


# Private helper functions for delete_graph


def _build_delete_query(
    db: Session,
    graph_name: str,
    workspace_id: str,
    user_identifier: Optional[str],
    is_admin: bool = False,
):
    """Build query for deleting graphs with access control."""
    # Admin users can delete any graph - skip access control
    if is_admin:
        logger.debug(
            f"[GRAPH-STORAGE] Admin delete access granted for '{graph_name}'"
        )
        return db.query(GraphDefinition).filter(GraphDefinition.name == graph_name)
    
    identifier = user_identifier or workspace_id
    resolved_user_id = resolve_user_id(identifier, db) if identifier else None

    # Get accessible workflows
    accessible_workflow_ids = []
    if resolved_user_id:
        from backend.models import WorkflowMembership

        memberships = (
            db.query(WorkflowMembership.workflow_id)
            .filter(WorkflowMembership.user_id == resolved_user_id)
            .all()
        )
        accessible_workflow_ids = [m.workflow_id for m in memberships if m.workflow_id]

    # Build access conditions
    conditions = _build_access_conditions(
        workspace_id, identifier, resolved_user_id, accessible_workflow_ids
    )

    # Build and return query
    query = db.query(GraphDefinition).filter(GraphDefinition.name == graph_name)

    if conditions:
        query = query.filter(or_(*conditions))

    return query


def _build_access_conditions(
    workspace_id: str,
    identifier: str,
    resolved_user_id: Optional[str],
    accessible_workflow_ids: List[str],
) -> List:
    """Build access control conditions for deletion."""
    conditions = []

    if workspace_id:
        conditions.append(GraphDefinition.workspace_id == workspace_id)

    if identifier and identifier != workspace_id:
        conditions.append(GraphDefinition.workspace_id == identifier)

    if resolved_user_id:
        conditions.append(GraphDefinition.workspace_id == resolved_user_id)
        conditions.append(
            GraphDefinition.workflow.has(
                Workflow.created_by_user_id == resolved_user_id
            )
        )

    if accessible_workflow_ids:
        conditions.append(GraphDefinition.workflow_id.in_(accessible_workflow_ids))

    return conditions


def _delete_specific_version(db: Session, query, version: int) -> bool:
    """Delete a specific version of a graph."""
    graph_def = query.filter(GraphDefinition.version == version).first()

    if not graph_def:
        return False

    # If deleting the latest version, promote the previous version
    if graph_def.is_latest and graph_def.parent_version_id:
        _promote_parent_version(db, graph_def.parent_version_id)

    db.delete(graph_def)
    db.commit()

    logger.info(f"[GRAPH-STORAGE] Deleted graph version: {graph_def.name} v{version}")
    return True


def _delete_all_versions(db: Session, query, graph_name: str) -> bool:
    """Delete all versions of a graph."""
    graph_defs = query.all()

    if not graph_defs:
        return False

    # Collect workflow IDs
    workflow_ids = {gd.workflow_id for gd in graph_defs if gd.workflow_id}

    # Delete all versions
    for graph_def in graph_defs:
        db.delete(graph_def)

    db.commit()

    # Soft delete orphaned workflows
    _soft_delete_orphaned_workflows(db, workflow_ids)

    logger.info(f"[GRAPH-STORAGE] Deleted all versions of graph: {graph_name}")
    return True


def _promote_parent_version(db: Session, parent_version_id: str) -> None:
    """Promote a parent version to be the latest."""
    parent = (
        db.query(GraphDefinition)
        .filter(GraphDefinition.id == parent_version_id)
        .first()
    )
    if parent:
        parent.is_latest = True


def _soft_delete_orphaned_workflows(db: Session, workflow_ids: set) -> None:
    """Mark workflows as deleted if they have no remaining graph definitions."""
    from backend.models import PublishedWorkflow

    for workflow_id in workflow_ids:
        remaining = (
            db.query(GraphDefinition)
            .filter(GraphDefinition.workflow_id == workflow_id)
            .count()
        )

        if remaining == 0:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            if workflow:
                workflow.is_deleted = True
                logger.debug(
                    f"[GRAPH-STORAGE] Soft-deleted orphaned workflow: {workflow_id}"
                )

                # Unpublish any published_workflows records linked to this workflow
                # Match by workflow_id OR graph_name to also clean up orphaned
                # records from a previous delete that happened before this fix
                updated = (
                    db.query(PublishedWorkflow)
                    .filter(
                        or_(
                            PublishedWorkflow.workflow_id == workflow_id,
                            PublishedWorkflow.graph_name == workflow.name,
                        )
                    )
                    .update({"is_published": False}, synchronize_session=False)
                )
                if updated:
                    logger.debug(
                        f"[GRAPH-STORAGE] Unpublished {updated} record(s) for deleted workflow: {workflow_id}"
                    )

    db.commit()


def _apply_provider_defaults(
    llm_config: Dict[str, Any], provider: str, model_name: str
) -> None:
    """
    Apply provider-specific defaults to LLM configuration.

    This uses the LLMConfig dataclass to ensure the same defaults are applied
    as when manually creating agents, maintaining consistency across the codebase.

    Args:
        llm_config: LLM configuration dict to update (modified in place)
        provider: Provider name (lowercase)
        model_name: Model name

    Note:
        Delegates to LLMConfig.__post_init__ which applies provider-specific
        validation requirements from models/workflow/validation/llm_validator.py
    """
    from backend.models.workflow.configs.llm import LLMConfig

    # Clear deployment reference and instance-specific fields
    llm_config["model_deployment_id"] = None
    llm_config["api_base"] = None

    # Create a new LLMConfig to get provider-specific defaults
    # This ensures consistency with manual agent creation (api/graph/handlers/node_crud.py:136)
    temp_config = LLMConfig(provider=provider, model_name=model_name)

    # Apply the defaults from the temp config
    llm_config["deployment_name"] = temp_config.deployment_name
    llm_config["api_version"] = temp_config.api_version
    llm_config["api_key_env_var"] = temp_config.api_key_env_var
    llm_config["base_url_env_var"] = temp_config.base_url_env_var


def _validate_and_fix_agent_llm_configs(workflow_json: Dict[str, Any]) -> List[str]:
    """
    Validate and fix LLM configurations in agent nodes during workflow import.

    This function checks if the LLM models configured for agents are available
    in the target Agentic Studio instance. It attempts to match agents with
    Model Deployments in the new instance so credentials are automatically
    pulled from the instance's configuration.

    Args:
        workflow_json: The workflow JSON definition to validate and fix

    Returns:
        List of warning messages for models that need reconfiguration
    """
    from backend.services.llm_models.constants import (
        AVAILABLE_MODELS,
        SUPPORTED_PROVIDERS,
    )
    from backend.services.model_deployment.service import ModelDeploymentService

    warnings = []
    nodes = workflow_json.get("nodes", [])

    # Get available model deployments in this instance
    deployment_service = ModelDeploymentService()
    deployments = deployment_service.list_deployments(model_type="llm")

    logger.debug(
        f"[GRAPH-STORAGE] Found {len(deployments)} Model Deployments in target instance"
    )

    # Build a lookup map: (provider, model_name) -> deployment_id
    deployment_map = {}
    for deployment in deployments:
        key = (deployment["provider"].lower(), deployment["model_name"])
        deployment_map[key] = deployment["id"]
        logger.debug(
            f"[GRAPH-STORAGE] Registered deployment: {deployment['name']} "
            f"(provider='{deployment['provider']}', model='{deployment['model_name']}') -> {deployment['id']}"
        )

    for node in nodes:
        # Only process agent nodes
        if node.get("type") != "AGENT":
            continue

        agent_config = node.get("agent_config")
        if not agent_config:
            continue

        llm_config = agent_config.get("llm_config")
        if not llm_config:
            continue

        provider = llm_config.get("provider", "").lower()
        model_name = llm_config.get("model_name", "")
        node_label = node.get("label", "Unnamed Agent")

        logger.debug(
            f"[GRAPH-STORAGE] Processing agent '{node_label}': "
            f"provider='{provider}', model='{model_name}'"
        )

        # Clear old model_deployment_id since it's from another instance
        old_deployment_id = llm_config.get("model_deployment_id")
        if old_deployment_id:
            logger.debug(
                f"[GRAPH-STORAGE] Agent '{node_label}': Clearing old deployment ID {old_deployment_id}"
            )

        # Check if provider is supported
        if provider not in SUPPORTED_PROVIDERS:
            warning_msg = (
                f"Agent '{node_label}': Provider '{provider}' is not available. "
                f"Please configure an LLM model manually."
            )
            warnings.append(warning_msg)
            agent_config["llm_config"] = None
            logger.warning(f"[GRAPH-STORAGE] {warning_msg}")
            continue

        # Try to find a matching Model Deployment in this instance FIRST
        # If a Model Deployment exists, it means the model is explicitly configured
        # and available, regardless of the AVAILABLE_MODELS constant
        deployment_key = (provider, model_name)
        matching_deployment_id = deployment_map.get(deployment_key)

        logger.debug(
            f"[GRAPH-STORAGE] Agent '{node_label}': Looking for deployment with key {deployment_key}. "
            f"Match found: {matching_deployment_id is not None}"
        )

        if matching_deployment_id:
            # Found a matching deployment! Use it and clear instance-specific fields
            llm_config["model_deployment_id"] = matching_deployment_id
            llm_config["deployment_name"] = None
            llm_config["api_base"] = None
            llm_config["api_key_env_var"] = None
            llm_config["base_url_env_var"] = None
            llm_config["api_version"] = None
            llm_config["credentials"] = {}

            logger.info(
                f"[GRAPH-STORAGE] Agent '{node_label}': Matched to deployment "
                f"{matching_deployment_id} for {provider}/{model_name}"
            )
        else:
            # No matching deployment found - check if model is in AVAILABLE_MODELS
            # for fallback with direct credentials
            available_models = AVAILABLE_MODELS.get(provider, [])
            if model_name not in available_models:
                warning_msg = (
                    f"Agent '{node_label}': Model '{model_name}' from provider '{provider}' "
                    f"is not available and no Model Deployment exists. "
                    f"Please configure an LLM model manually."
                )
                warnings.append(warning_msg)
                agent_config["llm_config"] = None
                logger.warning(f"[GRAPH-STORAGE] {warning_msg}")
                continue

            # Model is in AVAILABLE_MODELS, apply provider-specific defaults
            _apply_provider_defaults(llm_config, provider, model_name)

            logger.info(
                f"[GRAPH-STORAGE] Agent '{node_label}': No deployment found for "
                f"{provider}/{model_name}, using default credentials"
            )

    return warnings
