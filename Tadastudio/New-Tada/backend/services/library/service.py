"""
Library service for managing workflow templates.

This service handles operations for the global workflow library including
listing, adding, cloning, updating, and managing workflow templates.
"""

import csv
import hashlib
import io
import json
import secrets
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, or_, cast, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import joinedload

from backend.models import (
    DocumentCollection,
    GraphDefinition,
    User,
    Workflow,
    WorkflowMembership,
    WorkflowRole,
    WorkflowTemplate,
)
from backend.models.workflow import GraphData
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.groups.service import GroupService
from backend.services.library.utils import strip_model_deployments

logger = get_logger(__name__)


class LibraryService:
    """Service for managing workflow templates in the global library."""

    @staticmethod
    def count_templates(
        search: Optional[str] = None,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """
        Count workflow templates with optional filtering.

        Args:
            search: Search term to match against name, description, or tags
            category: Filter by category
            complexity: Filter by complexity level
            tags: Filter by one or more tags

        Returns:
            Count of matching templates
        """
        try:
            with get_db() as db:
                # Base query - only active, latest versions
                query = db.query(WorkflowTemplate).filter(
                    WorkflowTemplate.is_active,
                    WorkflowTemplate.is_latest_version,
                )

                # Apply category filter - check if category exists in JSON array
                if category:
                    query = query.filter(
                        cast(WorkflowTemplate.category, JSONB).contains([category])
                    )

                # Apply complexity filter
                if complexity:
                    query = query.filter(WorkflowTemplate.complexity == complexity)

                # Apply tag filters
                if tags:
                    for tag in tags:
                        query = query.filter(
                            cast(WorkflowTemplate.tags, JSONB).contains([tag])
                        )

                # Apply search filter (search in name, description, tags)
                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.filter(
                        or_(
                            func.lower(WorkflowTemplate.name).like(search_term),
                            func.lower(WorkflowTemplate.description).like(search_term),
                            func.lower(cast(WorkflowTemplate.tags, String)).like(
                                search_term
                            ),
                        )
                    )

                count = query.count()
                logger.info(
                    f"[LIBRARY] Counted {count} templates (search={search}, category={category})"
                )
                return count

        except Exception as e:
            logger.error(f"[LIBRARY] Error counting templates: {e}")
            raise

    @staticmethod
    def list_templates(
        search: Optional[str] = None,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        List workflow templates with optional filtering, searching, and sorting.

        Args:
            search: Search term to match against name, description, or tags
            category: Filter by category
            complexity: Filter by complexity level
            tags: Filter by one or more tags
            sort_by: Field to sort by (created_at, name, category, complexity, usage_count)
            sort_order: Sort order (asc or desc)
            limit: Maximum number of results to return

        Returns:
            List of template dictionaries with metadata
        """
        try:
            with get_db() as db:
                # Base query - only active, latest versions
                query = (
                    db.query(WorkflowTemplate)
                    .filter(
                        WorkflowTemplate.is_active,
                        WorkflowTemplate.is_latest_version,
                    )
                    .options(
                        joinedload(WorkflowTemplate.creator),
                        joinedload(WorkflowTemplate.workflow),
                        joinedload(WorkflowTemplate.graph_definition),
                    )
                )

                # Apply category filter - check if category exists in JSON array
                if category:
                    query = query.filter(
                        cast(WorkflowTemplate.category, JSONB).contains([category])
                    )

                # Apply complexity filter
                if complexity:
                    query = query.filter(WorkflowTemplate.complexity == complexity)

                # Apply tag filters
                if tags:
                    for tag in tags:
                        query = query.filter(
                            cast(WorkflowTemplate.tags, JSONB).contains([tag])
                        )

                # Apply search filter (search in name, description, tags)
                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.filter(
                        or_(
                            func.lower(WorkflowTemplate.name).like(search_term),
                            func.lower(WorkflowTemplate.description).like(search_term),
                            func.lower(cast(WorkflowTemplate.tags, String)).like(
                                search_term
                            ),
                        )
                    )

                # Apply sorting
                sort_field_map = {
                    "created_at": WorkflowTemplate.created_at,
                    "name": WorkflowTemplate.name,
                    "category": WorkflowTemplate.category,
                    "complexity": WorkflowTemplate.complexity,
                    "usage_count": WorkflowTemplate.usage_count,
                }

                sort_field = sort_field_map.get(sort_by, WorkflowTemplate.created_at)
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_field))
                else:
                    query = query.order_by(sort_field)

                # Apply limit
                if limit:
                    query = query.limit(limit)

                templates = query.all()

                # Format results
                results = []
                for template in templates:
                    # Parse graph definition to get metadata
                    graph_def = template.graph_definition
                    definition = (
                        json.loads(graph_def.definition_json)
                        if isinstance(graph_def.definition_json, str)
                        else graph_def.definition_json
                    )
                    nodes = definition.get("nodes", [])
                    agent_count = sum(
                        1 for node in nodes if node.get("type") == "agent"
                    )
                    tool_count = sum(1 for node in nodes if node.get("type") == "tool")

                    results.append(
                        {
                            "id": template.id,
                            "workflow_id": template.workflow_id,
                            "graph_definition_id": template.graph_definition_id,
                            "name": template.name,
                            "description": template.description,
                            "category": template.category,
                            "tags": template.tags,
                            "complexity": template.complexity,
                            "icon_color": template.icon_color,
                            "usage_count": template.usage_count,
                            "version": template.version,
                            "created_at": template.created_at.isoformat()
                            if template.created_at
                            else None,
                            "creator_name": template.creator.name
                            if template.creator
                            else "Unknown",
                            "creator_email": template.creator.email
                            if template.creator
                            else None,
                            "node_count": len(nodes),
                            "agent_count": agent_count,
                            "tool_count": tool_count,
                        }
                    )

                logger.info(
                    f"[LIBRARY] Listed {len(results)} templates (search={search}, category={category})"
                )
                return results

        except Exception as e:
            logger.error(f"[LIBRARY] Error listing templates: {e}")
            raise

    @staticmethod
    def find_template_by_workflow_name(workflow_name: str) -> Optional[Dict[str, Any]]:
        """
        Find an existing library template by checking if a workflow with the given name
        exists in the library workspace.

        This uses the same logic as add_to_library to determine if a template already exists.

        Args:
            workflow_name: Name of the workflow to search for in the library

        Returns:
            Template metadata if found, None otherwise
        """
        try:
            with get_db() as db:
                # Check if a graph definition with this name exists in the library workspace
                library_graph = (
                    db.query(GraphDefinition)
                    .filter(
                        GraphDefinition.name == workflow_name,
                        GraphDefinition.workspace_id == "library",
                    )
                    .first()
                )

                if not library_graph:
                    logger.info(
                        f"[LIBRARY] No library template found for workflow name: {workflow_name}"
                    )
                    return None

                # Find the active, latest version template for this graph definition
                template = (
                    db.query(WorkflowTemplate)
                    .filter(
                        WorkflowTemplate.graph_definition_id == library_graph.id,
                        WorkflowTemplate.is_active,
                        WorkflowTemplate.is_latest_version,
                    )
                    .first()
                )

                if not template:
                    logger.info(
                        f"[LIBRARY] Graph found but no active template for workflow name: {workflow_name}"
                    )
                    return None

                # Return template metadata
                result = {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "tags": template.tags,
                    "complexity": template.complexity,
                    "icon_color": template.icon_color,
                    "version": template.version,
                }

                logger.info(
                    f"[LIBRARY] Found existing template for workflow '{workflow_name}': {template.id}"
                )
                return result

        except Exception as e:
            logger.error(f"[LIBRARY] Error finding template by workflow name: {e}")
            return None

    @staticmethod
    def add_to_library(
        workflow_id: str,
        name: str,
        description: str,
        category: List[str],
        tags: List[str],
        user_identifier: str,
        complexity: Optional[str] = None,
        icon_color: Optional[str] = None,
    ) -> Optional[str]:
        """
        Add a workflow to the library by creating a copy with global access.

        Creates a new workflow and graph definition copy with a library-specific
        workspace_id, and creates a template record with metadata.

        If a template with this name already exists in the library, updates it
        instead of creating a duplicate.

        Args:
            workflow_id: ID of the workflow to add to library
            name: Display name for the template in the library
            description: Template description
            category: List of template categories
            tags: List of tags
            user_identifier: User adding the template
            complexity: Complexity level (optional)
            icon_color: Icon color (optional)

        Returns:
            Template ID if successful, None otherwise
        """
        try:
            with get_db() as db:
                # Get the original workflow and its latest graph definition
                workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
                if not workflow:
                    logger.error(f"[LIBRARY] Workflow not found: {workflow_id}")
                    return None

                graph_def = (
                    db.query(GraphDefinition)
                    .filter(
                        GraphDefinition.workflow_id == workflow_id,
                        GraphDefinition.is_latest,
                    )
                    .first()
                )

                if not graph_def:
                    logger.error(
                        f"[LIBRARY] No graph definition found for workflow: {workflow_id}"
                    )
                    return None

                # Resolve user
                user = (
                    db.query(User)
                    .filter(
                        or_(User.id == user_identifier, User.email == user_identifier)
                    )
                    .first()
                )
                user_id = user.id if user else None

                # Check if a graph definition with this name already exists in the library
                existing_library_graph = (
                    db.query(GraphDefinition)
                    .filter(
                        GraphDefinition.name == name,
                        GraphDefinition.workspace_id == "library",
                    )
                    .first()
                )

                if existing_library_graph:
                    # Find the existing template for this graph definition
                    existing_template = (
                        db.query(WorkflowTemplate)
                        .filter(
                            WorkflowTemplate.graph_definition_id
                            == existing_library_graph.id,
                            WorkflowTemplate.is_active,
                            WorkflowTemplate.is_latest_version,
                        )
                        .first()
                    )

                    if existing_template:
                        # Update the existing template instead of creating a new one
                        logger.info(
                            f"[LIBRARY] Template with name '{name}' already exists. Updating existing template."
                        )

                        # Mark current template as not latest
                        existing_template.is_latest_version = False

                        # Create new version of the template
                        new_template = WorkflowTemplate(
                            workflow_id=existing_template.workflow_id,
                            graph_definition_id=existing_template.graph_definition_id,
                            name=name,
                            description=description,
                            category=category,
                            tags=tags,
                            complexity=complexity or existing_template.complexity,
                            icon_color=icon_color or existing_template.icon_color,
                            created_by_user_id=user_id,
                            usage_count=existing_template.usage_count,
                            version=existing_template.version + 1,
                            parent_template_id=existing_template.id,
                            is_latest_version=True,
                            is_active=True,
                        )
                        db.add(new_template)
                        db.commit()

                        logger.info(
                            f"[LIBRARY] Updated template: {name} (new version={new_template.version}, template_id={new_template.id})"
                        )
                        return new_template.id

                # Create a copy of the workflow with library identifier
                # Use a dedicated "library" owner to avoid unique constraint
                # conflicts with the user's original workflow (name + user must be unique)
                library_workflow_id = str(uuid.uuid4())
                library_workflow = Workflow(
                    id=library_workflow_id,
                    name=name,  # Use the template name provided by user
                    description=description,
                    created_by_user_id=None,
                    latest_version=1,
                    is_deleted=False,
                    http_trigger_token="wf_" + secrets.token_urlsafe(32),
                )
                db.add(library_workflow)
                db.flush()

                # Create a copy of the graph definition and update internal name/description
                # Parse the definition to update internal name and description
                definition_dict = (
                    json.loads(graph_def.definition_json)
                    if isinstance(graph_def.definition_json, str)
                    else graph_def.definition_json
                )

                # Use GraphData to update name and description fields
                graph_data = GraphData.from_dict(definition_dict)
                graph_data.name = name  # Use the template name provided by user
                graph_data.description = (
                    description  # Use the provided description parameter
                )
                strip_model_deployments(graph_data)

                # Convert back to dict and serialize
                updated_definition_dict = graph_data.to_dict()
                definition_str = json.dumps(updated_definition_dict)
                definition_bytes = definition_str.encode("utf-8")
                file_hash = hashlib.sha256(definition_bytes).hexdigest()

                library_graph_def_id = str(uuid.uuid4())
                library_graph_def = GraphDefinition(
                    id=library_graph_def_id,
                    name=name,  # Use the template name provided by user
                    workspace_id="library",  # Global library workspace
                    workflow_id=library_workflow_id,
                    definition_json=definition_str,
                    description=description,
                    version=1,
                    is_latest=True,
                    parent_version_id=None,
                    created_by=user_identifier,
                    file_hash=file_hash,
                    size_bytes=len(definition_bytes),
                )
                db.add(library_graph_def)
                db.flush()

                # Create the template record
                template = WorkflowTemplate(
                    workflow_id=library_workflow_id,
                    graph_definition_id=library_graph_def_id,
                    name=name,
                    description=description,
                    category=category,
                    tags=tags,
                    complexity=complexity,
                    icon_color=icon_color,
                    created_by_user_id=user_id,
                    usage_count=0,
                    version=1,
                    parent_template_id=None,
                    is_latest_version=True,
                    is_active=True,
                )
                db.add(template)
                db.commit()

                logger.info(
                    f"[LIBRARY] Added template: {name} (template_id={template.id})"
                )
                return template.id

        except Exception as e:
            logger.error(f"[LIBRARY] Error adding template: {e}")
            raise

    @staticmethod
    def clone_template(
        template_id: str,
        user_identifier: str,
        workspace_id: str,
        target_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Clone a template to a user's workspace.

        Creates a new workflow and graph definition in the user's workspace
        based on the template, and increments the template's usage count.

        Args:
            template_id: ID of the template to clone
            user_identifier: User cloning the template
            workspace_id: Target workspace ID
            target_name: Custom name for the cloned workflow (optional, defaults to template name)

        Returns:
            New workflow ID if successful, None otherwise
        """
        try:
            with get_db() as db:
                # Get the template
                template = (
                    db.query(WorkflowTemplate)
                    .filter(WorkflowTemplate.id == template_id)
                    .first()
                )

                if not template or not template.is_active:
                    logger.error(
                        f"[LIBRARY] Template not found or inactive: {template_id}"
                    )
                    return None

                # Get the template's graph definition
                graph_def = template.graph_definition

                # Resolve user
                user = (
                    db.query(User)
                    .filter(
                        or_(User.id == user_identifier, User.email == user_identifier)
                    )
                    .first()
                )
                user_id = user.id if user else None

                # Create new workflow in user's workspace
                # Use target_name if provided, otherwise use template name
                workflow_name = target_name if target_name else template.name
                new_workflow_id = str(uuid.uuid4())
                new_workflow = Workflow(
                    id=new_workflow_id,
                    name=workflow_name,
                    description=template.description,
                    created_by_user_id=user_id,
                    latest_version=1,
                    is_deleted=False,
                    http_trigger_token="wf_" + secrets.token_urlsafe(32),
                )
                db.add(new_workflow)
                db.flush()

                # Create workflow membership
                if user_id:
                    membership = WorkflowMembership(
                        workflow_id=new_workflow_id,
                        user_id=user_id,
                        role=WorkflowRole.OWNER,
                    )
                    db.add(membership)

                # Clone graph definition and update internal name/description
                # Parse the definition to update internal name and description
                definition_dict = (
                    json.loads(graph_def.definition_json)
                    if isinstance(graph_def.definition_json, str)
                    else graph_def.definition_json
                )

                # Use GraphData to update name and description fields
                graph_data = GraphData.from_dict(definition_dict)
                graph_data.name = workflow_name
                graph_data.description = template.description

                # Convert back to dict and serialize
                updated_definition_dict = graph_data.to_dict()
                definition_str = json.dumps(updated_definition_dict)
                definition_bytes = definition_str.encode("utf-8")
                file_hash = hashlib.sha256(definition_bytes).hexdigest()

                new_graph_def = GraphDefinition(
                    id=str(uuid.uuid4()),
                    name=workflow_name,
                    workspace_id=workspace_id,
                    workflow_id=new_workflow_id,
                    definition_json=definition_str,
                    description=template.description,
                    version=1,
                    is_latest=True,
                    parent_version_id=None,
                    created_by=user_identifier,
                    file_hash=file_hash,
                    size_bytes=len(definition_bytes),
                )
                db.add(new_graph_def)

                # Increment usage count
                template.usage_count += 1

                db.commit()

                logger.info(
                    f"[LIBRARY] Cloned template {template_id} to workflow {new_workflow_id}"
                )
                return new_workflow_id

        except Exception as e:
            logger.error(f"[LIBRARY] Error cloning template: {e}")
            raise

    @staticmethod
    def get_template_with_graph(template_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single template with its associated graph definition.

        Args:
            template_id: The ID of the template to retrieve

        Returns:
            Template metadata combined with graph definition details.
        """
        try:
            with get_db() as db:
                template = (
                    db.query(WorkflowTemplate)
                    .options(
                        joinedload(WorkflowTemplate.creator),
                        joinedload(WorkflowTemplate.workflow),
                        joinedload(WorkflowTemplate.graph_definition),
                    )
                    .filter(WorkflowTemplate.id == template_id)
                    .first()
                )

                if not template or not template.is_active:
                    logger.warning(
                        f"[LIBRARY] Template not found or inactive: {template_id}"
                    )
                    return None

                graph_def = template.graph_definition
                if not graph_def:
                    logger.error(
                        f"[LIBRARY] Graph definition missing for template: {template_id}"
                    )
                    return None

                definition = (
                    json.loads(graph_def.definition_json)
                    if isinstance(graph_def.definition_json, str)
                    else graph_def.definition_json
                )

                nodes = definition.get("nodes", []) or []
                connections = (
                    definition.get("connections") or definition.get("edges") or []
                )

                agent_count = sum(
                    1 for node in nodes if (node.get("type") or "").upper() == "AGENT"
                )
                tool_count = sum(
                    1 for node in nodes if (node.get("type") or "").upper() == "TOOL"
                )

                template_data: Dict[str, Any] = {
                    "id": template.id,
                    "workflow_id": template.workflow_id,
                    "graph_definition_id": template.graph_definition_id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "tags": template.tags,
                    "complexity": template.complexity,
                    "icon_color": template.icon_color,
                    "usage_count": template.usage_count,
                    "version": template.version,
                    "created_at": template.created_at.isoformat()
                    if template.created_at
                    else None,
                    "creator_name": template.creator.name
                    if template.creator
                    else "Unknown",
                    "creator_email": template.creator.email
                    if template.creator
                    else None,
                    "node_count": len(nodes),
                    "agent_count": agent_count,
                    "tool_count": tool_count,
                    "graph_definition": {
                        "id": graph_def.id,
                        "name": graph_def.name,
                        "workspace_id": graph_def.workspace_id,
                        "workflow_id": graph_def.workflow_id,
                        "description": graph_def.description,
                        "version": graph_def.version,
                        "is_latest": graph_def.is_latest,
                        "definition": {
                            "nodes": nodes,
                            "connections": connections,
                            **{
                                key: value
                                for key, value in definition.items()
                                if key not in {"nodes", "connections", "edges"}
                            },
                        },
                        "created_at": graph_def.created_at.isoformat()
                        if graph_def.created_at
                        else None,
                        "updated_at": graph_def.updated_at.isoformat()
                        if graph_def.updated_at
                        else None,
                    },
                }

                logger.info(f"[LIBRARY] Retrieved template details: {template_id}")
                return template_data

        except Exception as e:
            logger.error(f"[LIBRARY] Error retrieving template {template_id}: {e}")
            raise

    @staticmethod
    def update_template(
        template_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        complexity: Optional[str] = None,
        icon_color: Optional[str] = None,
    ) -> Optional[str]:
        """
        Update template metadata by creating a new version.

        Args:
            template_id: ID of the template to update
            name: New name (optional)
            description: New description (optional)
            category: New category (optional)
            tags: New tags (optional)
            complexity: New complexity (optional)
            icon_color: New icon color (optional)

        Returns:
            New template version ID if successful, None otherwise
        """
        try:
            with get_db() as db:
                # Get the current template
                current_template = (
                    db.query(WorkflowTemplate)
                    .filter(WorkflowTemplate.id == template_id)
                    .first()
                )

                if not current_template:
                    logger.error(f"[LIBRARY] Template not found: {template_id}")
                    return None

                # Mark current as not latest
                current_template.is_latest_version = False

                # Create new version
                new_template = WorkflowTemplate(
                    workflow_id=current_template.workflow_id,
                    graph_definition_id=current_template.graph_definition_id,
                    name=name or current_template.name,
                    description=description or current_template.description,
                    category=category or current_template.category,
                    tags=tags if tags is not None else current_template.tags,
                    complexity=complexity or current_template.complexity,
                    icon_color=icon_color or current_template.icon_color,
                    created_by_user_id=current_template.created_by_user_id,
                    usage_count=current_template.usage_count,
                    version=current_template.version + 1,
                    parent_template_id=template_id,
                    is_latest_version=True,
                    is_active=True,
                )
                db.add(new_template)
                db.commit()

                logger.info(
                    f"[LIBRARY] Created template version {new_template.version} (id={new_template.id})"
                )
                return new_template.id

        except Exception as e:
            logger.error(f"[LIBRARY] Error updating template: {e}")
            raise

    @staticmethod
    def can_delete_template(template_id: str, user_identifier: str) -> bool:
        """
        Check if a user has permission to delete a template.

        Only the template creator can delete their own templates.

        Args:
            template_id: ID of the template
            user_identifier: User email or ID

        Returns:
            True if user can delete, False otherwise
        """
        try:
            with get_db() as db:
                template = (
                    db.query(WorkflowTemplate)
                    .options(joinedload(WorkflowTemplate.creator))
                    .filter(WorkflowTemplate.id == template_id)
                    .first()
                )

                if not template:
                    logger.error(f"[LIBRARY] Template not found: {template_id}")
                    return False

                # Check if user is the creator
                if template.creator:
                    creator_email = template.creator.email
                    creator_id = template.creator.id

                    # Match by email or ID
                    is_creator = (
                        creator_email
                        and creator_email.lower() == user_identifier.lower()
                    ) or (creator_id and creator_id == user_identifier)

                    return is_creator
                else:
                    # No creator set, deny deletion
                    return False

        except Exception as e:
            logger.error(f"[LIBRARY] Error checking delete permission: {e}")
            return False

    @staticmethod
    def deactivate_template(template_id: str) -> bool:
        """
        Soft delete a template by marking it as inactive.

        Args:
            template_id: ID of the template to deactivate

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db() as db:
                template = (
                    db.query(WorkflowTemplate)
                    .filter(WorkflowTemplate.id == template_id)
                    .first()
                )

                if not template:
                    logger.error(f"[LIBRARY] Template not found: {template_id}")
                    return False

                template.is_active = False
                db.commit()

                logger.info(f"[LIBRARY] Deactivated template: {template_id}")
                return True

        except Exception as e:
            logger.error(f"[LIBRARY] Error deactivating template: {e}")
            return False

    @staticmethod
    def _parse_json_column(value: str) -> Any:
        """Parse a JSON column value from CSV (may be string-serialized JSON)."""
        if not value or value.strip() == "":
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    @staticmethod
    def import_templates_from_csv(
        workflows_csv_content: str,
        graph_definitions_csv_content: str,
        workflow_templates_csv_content: str,
    ) -> Dict[str, Any]:
        """Import workflow templates from CSV file contents.

        Accepts CSV content strings for the three related tables and inserts
        non-duplicate templates into the library. Duplicates are detected by
        matching on (name, tags).

        New UUIDs are generated for all records. FK relationships are remapped
        internally. User FKs and version chains are not carried over.

        Args:
            workflows_csv_content: CSV string for the workflows table.
            graph_definitions_csv_content: CSV string for the graph_definitions table.
            workflow_templates_csv_content: CSV string for the workflow_templates table.

        Returns:
            Summary dict with inserted/skipped counts and any errors.
        """
        result: Dict[str, Any] = {
            "total_templates": 0,
            "inserted": 0,
            "skipped_duplicates": 0,
            "skipped_names": [],
            "errors": [],
        }

        try:
            # Allow large fields (definition_json can exceed the 128KB default)
            csv.field_size_limit(10 * 1024 * 1024)  # 10 MB

            # 1. Parse all three CSVs
            workflows_rows = list(csv.DictReader(io.StringIO(workflows_csv_content)))
            graph_defs_rows = list(
                csv.DictReader(io.StringIO(graph_definitions_csv_content))
            )
            templates_rows = list(
                csv.DictReader(io.StringIO(workflow_templates_csv_content))
            )

            result["total_templates"] = len(templates_rows)

            if not templates_rows:
                logger.info("[LIBRARY CSV] No templates found in CSV")
                return result

            # 2. Build ID remap dicts: old_id -> new_uuid
            workflow_id_map: Dict[str, str] = {
                row["id"]: str(uuid.uuid4()) for row in workflows_rows
            }
            graph_def_id_map: Dict[str, str] = {
                row["id"]: str(uuid.uuid4()) for row in graph_defs_rows
            }

            # Index source rows by old ID for lookup
            workflows_by_id = {row["id"]: row for row in workflows_rows}
            graph_defs_by_id = {row["id"]: row for row in graph_defs_rows}

            with get_db() as db:
                # 3. Build existing duplicate key set: (name, sorted_tags_tuple)
                existing_templates = (
                    db.query(WorkflowTemplate)
                    .filter(
                        WorkflowTemplate.is_active.is_(True),
                        WorkflowTemplate.is_latest_version.is_(True),
                    )
                    .all()
                )
                existing_keys: set[Tuple[str, Tuple[str, ...]]] = set()
                for tmpl in existing_templates:
                    tags = tuple(sorted(tmpl.tags)) if tmpl.tags else ()
                    existing_keys.add((tmpl.name, tags))

                # 4. Determine which templates to import vs skip
                templates_to_import = []
                for row in templates_rows:
                    tags = LibraryService._parse_json_column(row.get("tags", "[]"))
                    if not isinstance(tags, list):
                        tags = []
                    tags_key = tuple(sorted(tags))
                    name = row.get("name", "").strip()

                    if (name, tags_key) in existing_keys:
                        result["skipped_duplicates"] += 1
                        result["skipped_names"].append(name)
                    else:
                        templates_to_import.append(row)

                if not templates_to_import:
                    logger.info(
                        "[LIBRARY CSV] All templates already exist, nothing to import"
                    )
                    return result

                # 5. Insert workflows (only those needed by non-skipped templates)
                needed_workflow_ids = {
                    row["workflow_id"] for row in templates_to_import
                }
                for old_wf_id in needed_workflow_ids:
                    wf_row = workflows_by_id.get(old_wf_id)
                    if not wf_row:
                        result["errors"].append(
                            f"Workflow {old_wf_id} referenced by template but not found in workflows CSV"
                        )
                        continue
                    workflow = Workflow(
                        id=workflow_id_map[old_wf_id],
                        name=wf_row.get("name", ""),
                        description=wf_row.get("description"),
                        created_by_user_id=None,
                        latest_version=int(wf_row.get("latest_version") or 1),
                        is_deleted=False,
                        http_trigger_token="wf_" + secrets.token_urlsafe(32),
                    )
                    db.add(workflow)
                db.flush()

                # 6. Insert graph_definitions (only those needed)
                needed_graph_def_ids = {
                    row["graph_definition_id"] for row in templates_to_import
                }
                for old_gd_id in needed_graph_def_ids:
                    gd_row = graph_defs_by_id.get(old_gd_id)
                    if not gd_row:
                        result["errors"].append(
                            f"GraphDefinition {old_gd_id} referenced by template but not found in graph_definitions CSV"
                        )
                        continue

                    definition_json = LibraryService._parse_json_column(
                        gd_row.get("definition_json", "{}")
                    )
                    definition_str = (
                        json.dumps(definition_json)
                        if not isinstance(definition_json, str)
                        else definition_json
                    )
                    definition_bytes = definition_str.encode("utf-8")
                    file_hash = hashlib.sha256(definition_bytes).hexdigest()

                    old_wf_id = gd_row.get("workflow_id")
                    new_wf_id = workflow_id_map.get(old_wf_id) if old_wf_id else None

                    graph_def = GraphDefinition(
                        id=graph_def_id_map[old_gd_id],
                        name=gd_row.get("name", ""),
                        workspace_id="library",
                        workflow_id=new_wf_id,
                        definition_json=definition_str,
                        description=gd_row.get("description"),
                        version=1,
                        is_latest=True,
                        parent_version_id=None,
                        created_by=gd_row.get("created_by"),
                        file_hash=file_hash,
                        size_bytes=len(definition_bytes),
                    )
                    db.add(graph_def)
                db.flush()

                # 7. Insert workflow_templates
                for row in templates_to_import:
                    category = LibraryService._parse_json_column(
                        row.get("category", "[]")
                    )
                    tags = LibraryService._parse_json_column(row.get("tags", "[]"))

                    new_wf_id = workflow_id_map.get(row.get("workflow_id"))
                    new_gd_id = graph_def_id_map.get(row.get("graph_definition_id"))

                    if not new_wf_id or not new_gd_id:
                        result["errors"].append(
                            f"Skipping template '{row.get('name')}': missing mapped workflow or graph_definition ID"
                        )
                        continue

                    template = WorkflowTemplate(
                        workflow_id=new_wf_id,
                        graph_definition_id=new_gd_id,
                        name=row.get("name", ""),
                        description=row.get("description", ""),
                        category=category if isinstance(category, list) else [],
                        tags=tags if isinstance(tags, list) else [],
                        complexity=row.get("complexity") or None,
                        icon_color=row.get("icon_color") or None,
                        created_by_user_id=None,
                        usage_count=0,
                        version=1,
                        parent_template_id=None,
                        is_latest_version=True,
                        is_active=True,
                    )
                    db.add(template)
                    result["inserted"] += 1

                db.commit()

                logger.info(
                    f"[LIBRARY CSV] Import complete: {result['inserted']} inserted, "
                    f"{result['skipped_duplicates']} skipped"
                )

        except Exception as e:
            logger.error(f"[LIBRARY CSV] Error importing templates from CSV: {e}")
            result["errors"].append(str(e))
            raise

        return result

    @staticmethod
    def _determine_access_reason(
        collection: "DocumentCollection",
        user_id: str,
        user_groups: List[str],
    ) -> Tuple[bool, str]:
        """Determine whether a user has access to a collection and why.

        Args:
            collection: The DocumentCollection object.
            user_id: The user's identifier (email).
            user_groups: List of group names the user belongs to.

        Returns:
            Tuple of (has_access, access_reason).
        """
        if collection.user_id == user_id:
            return True, "owner"

        visible_groups = collection.visible_to_groups or []

        if not visible_groups:
            return False, "no access"

        if "__all__" in visible_groups:
            return True, "global"

        for group in visible_groups:
            if group in user_groups:
                return True, f"group: {group}"

        return False, "no access"

    @staticmethod
    def get_template_dependencies(
        template_id: str, user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract collection dependencies from a workflow template.

        Parses the GraphDefinition JSON to find collection names referenced by
        DocumentSearchNode types and determines the current user's access to
        each collection.

        Args:
            template_id: The ID of the workflow template.
            user_id: The current user's identifier (email).

        Returns:
            List of dependency dicts with collection info and access status,
            or None if the template is not found or inactive.
        """
        # Get user groups upfront
        user_groups = GroupService().get_user_groups(user_id)

        with get_db() as db:
            # Load template with graph definition
            template = (
                db.query(WorkflowTemplate)
                .options(joinedload(WorkflowTemplate.graph_definition))
                .filter(WorkflowTemplate.id == template_id)
                .first()
            )

            if not template or not template.is_active:
                logger.warning(
                    f"[LIBRARY] Template not found or inactive: {template_id}"
                )
                return None

            graph_def = template.graph_definition
            if not graph_def:
                logger.warning(
                    f"[LIBRARY] Graph definition missing for template: {template_id}"
                )
                return None

            # Parse definition JSON
            definition = (
                json.loads(graph_def.definition_json)
                if isinstance(graph_def.definition_json, str)
                else graph_def.definition_json
            )

            # Extract collection IDs from all nodes
            collection_ids: set = set()
            for node in definition.get("nodes", []):
                config = node.get("data", {}).get("document_search_config", {})
                if not config:
                    continue
                doc_collections = config.get("document_collections", [])
                if isinstance(doc_collections, str):
                    doc_collections = [doc_collections]
                if isinstance(doc_collections, list):
                    for coll_id in doc_collections:
                        if coll_id:
                            collection_ids.add(coll_id)

            logger.info(
                f"[LIBRARY] Extracted {len(collection_ids)} collection dependencies from template {template_id}"
            )

            if not collection_ids:
                return []

            # Batch query all collections by ID, joining with User for creator name
            collections = (
                db.query(DocumentCollection, User)
                .outerjoin(User, DocumentCollection.user_id == User.email)
                .filter(DocumentCollection.id.in_(collection_ids))
                .all()
            )

            # Index by collection ID
            collection_map: Dict[str, Tuple] = {}
            for coll, creator_user in collections:
                collection_map[str(coll.id)] = (coll, creator_user)

            # Build dependency list
            dependencies: List[Dict[str, Any]] = []
            for coll_id in sorted(collection_ids):
                if coll_id in collection_map:
                    coll, creator_user = collection_map[coll_id]
                    has_access, access_reason = LibraryService._determine_access_reason(
                        coll, user_id, user_groups
                    )
                    dependencies.append(
                        {
                            "collection_id": coll.id,
                            "collection_name": coll.name,
                            "visible_to_groups": coll.visible_to_groups or [],
                            "has_access": has_access,
                            "access_reason": access_reason,
                            "created_by_name": creator_user.name
                            if creator_user
                            else None,
                        }
                    )
                else:
                    logger.warning(
                        f"[LIBRARY] Collection '{coll_id}' referenced by template {template_id} not found"
                    )
                    dependencies.append(
                        {
                            "collection_id": None,
                            "collection_name": coll_id,
                            "visible_to_groups": [],
                            "has_access": False,
                            "access_reason": "no access",
                            "created_by_name": None,
                        }
                    )

            return dependencies
