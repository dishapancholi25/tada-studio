"""Service helpers for agent templates in the global library."""

import copy
import hashlib
import json
import secrets
import uuid
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import desc, func, or_, cast, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import joinedload

from backend.models import (
    AgentTemplate,
    GraphDefinition,
    User,
    Workflow,
    WorkflowMembership,
    WorkflowRole,
)
from backend.models.workflow import (
    Connection,
    ConnectionType,
    EnhancedNodeData,
    GraphData,
    NodeType,
    Position,
)
from backend.services.config import get_logger
from backend.services.database import get_db
from backend.services.library.utils import strip_model_deployments

logger = get_logger(__name__)


class AgentLibraryService:
    """Service for managing standalone agent templates."""

    @staticmethod
    def count_agents(
        search: Optional[str] = None,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """
        Count agent templates with optional filtering.

        Args:
            search: Search term to match against name, description, or tags
            category: Filter by category
            complexity: Filter by complexity level
            tags: Filter by one or more tags

        Returns:
            Count of matching agent templates
        """
        try:
            with get_db() as db:
                query = db.query(AgentTemplate).filter(
                    AgentTemplate.is_active,
                    AgentTemplate.is_latest_version,
                )

                if category:
                    query = query.filter(
                        cast(AgentTemplate.category, JSONB).contains([category])
                    )

                if complexity:
                    query = query.filter(AgentTemplate.complexity == complexity)

                if tags:
                    for tag in tags:
                        query = query.filter(
                            cast(AgentTemplate.tags, JSONB).contains([tag])
                        )

                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.filter(
                        or_(
                            func.lower(AgentTemplate.name).like(search_term),
                            func.lower(AgentTemplate.description).like(search_term),
                            func.lower(cast(AgentTemplate.tags, String)).like(
                                search_term
                            ),
                        )
                    )

                count = query.count()
                logger.info(
                    f"[AGENT-LIBRARY] Counted {count} agents (search={search}, category={category})"
                )
                return count

        except Exception as exc:
            logger.error(f"[AGENT-LIBRARY] Error counting agents: {exc}")
            raise

    @staticmethod
    def list_agents(
        search: Optional[str] = None,
        category: Optional[str] = None,
        complexity: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """List agent templates with optional filtering."""
        try:
            with get_db() as db:
                query = (
                    db.query(AgentTemplate)
                    .filter(
                        AgentTemplate.is_active,
                        AgentTemplate.is_latest_version,
                    )
                    .options(
                        joinedload(AgentTemplate.creator),
                        joinedload(AgentTemplate.graph_definition),
                    )
                )

                if category:
                    query = query.filter(
                        cast(AgentTemplate.category, JSONB).contains([category])
                    )

                if complexity:
                    query = query.filter(AgentTemplate.complexity == complexity)

                if tags:
                    for tag in tags:
                        query = query.filter(
                            cast(AgentTemplate.tags, JSONB).contains([tag])
                        )

                if search:
                    search_term = f"%{search.lower()}%"
                    query = query.filter(
                        or_(
                            func.lower(AgentTemplate.name).like(search_term),
                            func.lower(AgentTemplate.description).like(search_term),
                            func.lower(cast(AgentTemplate.tags, String)).like(
                                search_term
                            ),
                        )
                    )

                sort_field_map = {
                    "created_at": AgentTemplate.created_at,
                    "name": AgentTemplate.name,
                    "category": AgentTemplate.category,
                    "complexity": AgentTemplate.complexity,
                    "usage_count": AgentTemplate.usage_count,
                }
                sort_field = sort_field_map.get(sort_by, AgentTemplate.created_at)
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_field))
                else:
                    query = query.order_by(sort_field)

                if limit:
                    query = query.limit(limit)

                agent_templates = query.all()
                return [
                    AgentLibraryService._serialize_agent_summary(agent)
                    for agent in agent_templates
                ]

        except Exception as exc:
            logger.error(f"[AGENT-LIBRARY] Error listing agents: {exc}")
            raise

    @staticmethod
    def get_agent_with_graph(agent_id: str) -> Optional[Dict[str, Any]]:
        """Return a single agent template plus its graph definition."""
        try:
            with get_db() as db:
                agent = (
                    db.query(AgentTemplate)
                    .options(
                        joinedload(AgentTemplate.creator),
                        joinedload(AgentTemplate.graph_definition),
                    )
                    .filter(AgentTemplate.id == agent_id)
                    .first()
                )

                if not agent or not agent.is_active:
                    logger.warning(
                        f"[AGENT-LIBRARY] Agent template not found: {agent_id}"
                    )
                    return None

                graph_def = agent.graph_definition
                if not graph_def:
                    logger.error(
                        f"[AGENT-LIBRARY] Graph definition missing for agent template {agent_id}"
                    )
                    return None

                definition = (
                    json.loads(graph_def.definition_json)
                    if isinstance(graph_def.definition_json, str)
                    else graph_def.definition_json
                )

                summary = AgentLibraryService._serialize_agent_summary(agent)
                summary["graph_definition"] = {
                    "id": graph_def.id,
                    "name": graph_def.name,
                    "workspace_id": graph_def.workspace_id,
                    "workflow_id": graph_def.workflow_id,
                    "description": graph_def.description,
                    "version": graph_def.version,
                    "is_latest": graph_def.is_latest,
                    "definition": definition,
                    "created_at": graph_def.created_at.isoformat()
                    if graph_def.created_at
                    else None,
                    "updated_at": graph_def.updated_at.isoformat()
                    if graph_def.updated_at
                    else None,
                }

                return summary

        except Exception as exc:
            logger.error(f"[AGENT-LIBRARY] Error retrieving agent template: {exc}")
            raise

    @staticmethod
    def add_agent_to_library(
        workflow_id: str,
        agent_node_id: str,
        name: str,
        description: str,
        category: List[str],
        tags: List[str],
        user_identifier: str,
        icon_color: Optional[str] = None,
    ) -> Optional[str]:
        """Persist a single agent node as a reusable template."""

        try:
            with get_db() as db:
                workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()

                if not workflow:
                    logger.error(
                        "[AGENT-LIBRARY] Workflow not found when publishing agent: %s",
                        workflow_id,
                    )
                    return None

                graph_def = (
                    db.query(GraphDefinition)
                    .filter(
                        GraphDefinition.workflow_id == workflow_id,
                        GraphDefinition.is_latest,
                    )
                    .order_by(desc(GraphDefinition.version))
                    .first()
                )

                if not graph_def:
                    logger.error(
                        "[AGENT-LIBRARY] Graph definition missing for workflow %s",
                        workflow_id,
                    )
                    return None

                definition = (
                    json.loads(graph_def.definition_json)
                    if isinstance(graph_def.definition_json, str)
                    else graph_def.definition_json
                )

                graph_data = GraphData.from_dict(definition)
                strip_model_deployments(graph_data)
                agent_node = graph_data.get_node_by_id(agent_node_id)

                if not agent_node or agent_node.type != NodeType.AGENT:
                    logger.error(
                        "[AGENT-LIBRARY] Agent node %s not found in workflow %s",
                        agent_node_id,
                        workflow_id,
                    )
                    return None

                # Prepare minimal graph containing this agent
                agent_graph_dict, primary_agent_node_id = (
                    AgentLibraryService._build_agent_graph(
                        graph_data=graph_data,
                        root_agent_id=agent_node_id,
                        template_name=name,
                        template_description=description,
                        source_workflow_id=workflow_id,
                    )
                )

                definition_str = json.dumps(agent_graph_dict)
                definition_bytes = definition_str.encode("utf-8")
                file_hash = hashlib.sha256(definition_bytes).hexdigest()

                # Resolve user
                user = (
                    db.query(User)
                    .filter(
                        or_(User.id == user_identifier, User.email == user_identifier)
                    )
                    .first()
                )
                user_id = user.id if user else None

                template_workflow_id = str(uuid.uuid4())
                template_workflow = Workflow(
                    id=template_workflow_id,
                    name=name,
                    description=description,
                    created_by_user_id=user_id,
                    latest_version=1,
                    is_deleted=False,
                    http_trigger_token="wf_" + secrets.token_urlsafe(32),
                )
                db.add(template_workflow)
                db.flush()

                template_graph_definition_id = str(uuid.uuid4())
                template_graph_definition = GraphDefinition(
                    id=template_graph_definition_id,
                    name=name,
                    workspace_id="agent-library",
                    workflow_id=template_workflow_id,
                    definition_json=definition_str,
                    description=description,
                    version=1,
                    is_latest=True,
                    parent_version_id=None,
                    created_by=user_identifier,
                    file_hash=file_hash,
                    size_bytes=len(definition_bytes),
                )
                db.add(template_graph_definition)
                db.flush()

                agent_template = AgentTemplate(
                    workflow_id=template_workflow_id,
                    graph_definition_id=template_graph_definition_id,
                    name=name,
                    description=description,
                    category=category,
                    tags=tags,
                    icon_color=icon_color,
                    created_by_user_id=user_id,
                    usage_count=0,
                    version=1,
                    parent_template_id=None,
                    is_latest_version=True,
                    is_active=True,
                    primary_agent_node_id=primary_agent_node_id,
                    primary_agent_label=agent_node.name or name,
                    agent_metadata=AgentLibraryService._build_agent_metadata(
                        agent_node,
                        workflow_id,
                        agent_node_id,
                    ),
                )
                db.add(agent_template)
                db.commit()

                logger.info(
                    "[AGENT-LIBRARY] Published agent %s from workflow %s as template %s",
                    agent_node_id,
                    workflow_id,
                    agent_template.id,
                )
                return agent_template.id

        except Exception as exc:
            logger.error("[AGENT-LIBRARY] Failed to publish agent: %s", exc)
            raise

        return None

    @staticmethod
    def clone_agent_template(
        agent_id: str,
        user_identifier: str,
        workspace_id: str,
        target_name: Optional[str] = None,
    ) -> Optional[str]:
        """Clone an agent template into a runnable workflow with START/END nodes."""

        try:
            with get_db() as db:
                agent_template = (
                    db.query(AgentTemplate)
                    .options(
                        joinedload(AgentTemplate.graph_definition),
                        joinedload(AgentTemplate.creator),
                    )
                    .filter(AgentTemplate.id == agent_id)
                    .first()
                )

                if not agent_template or not agent_template.is_active:
                    logger.error(
                        "[AGENT-LIBRARY] Agent template not found or inactive: %s",
                        agent_id,
                    )
                    return None

                graph_def = agent_template.graph_definition
                if not graph_def:
                    logger.error(
                        "[AGENT-LIBRARY] Graph definition missing for agent template %s",
                        agent_id,
                    )
                    return None

                definition = (
                    json.loads(graph_def.definition_json)
                    if isinstance(graph_def.definition_json, str)
                    else graph_def.definition_json
                )

                if "connections" not in definition and "edges" in definition:
                    definition["connections"] = definition.get("edges") or []

                graph_data = GraphData.from_dict(definition)

                primary_agent_id = agent_template.primary_agent_node_id
                if not primary_agent_id:
                    fallback_agent = next(
                        (
                            node.uniq_id
                            for node in graph_data.nodes
                            if node.type == NodeType.AGENT
                        ),
                        None,
                    )
                    if not fallback_agent:
                        logger.error(
                            "[AGENT-LIBRARY] No agent node found when cloning template %s",
                            agent_id,
                        )
                        return None
                    primary_agent_id = fallback_agent

                AgentLibraryService._wrap_agent_graph_with_boundaries(
                    graph_data,
                    primary_agent_id,
                )

                metadata = graph_data.metadata or {}
                metadata.update(
                    {
                        "origin": "agent_template_clone",
                        "source_agent_template_id": agent_template.id,
                        "source_agent_workflow_id": agent_template.workflow_id,
                    }
                )
                graph_data.metadata = metadata
                graph_data.name = target_name or agent_template.name
                graph_data.description = (
                    agent_template.description or graph_data.description
                )

                user = (
                    db.query(User)
                    .filter(
                        or_(User.id == user_identifier, User.email == user_identifier)
                    )
                    .first()
                )
                user_id = user.id if user else None

                target_workspace_id = workspace_id or user_identifier

                new_workflow_id = str(uuid.uuid4())
                new_workflow = Workflow(
                    id=new_workflow_id,
                    name=graph_data.name,
                    description=graph_data.description,
                    created_by_user_id=user_id,
                    latest_version=1,
                    is_deleted=False,
                    http_trigger_token="wf_" + secrets.token_urlsafe(32),
                )
                db.add(new_workflow)
                db.flush()

                if user_id:
                    db.add(
                        WorkflowMembership(
                            workflow_id=new_workflow_id,
                            user_id=user_id,
                            role=WorkflowRole.OWNER,
                        )
                    )

                graph_data.workflow_id = new_workflow_id
                graph_dict = graph_data.to_dict()
                definition_str = json.dumps(graph_dict)
                definition_bytes = definition_str.encode("utf-8")
                file_hash = hashlib.sha256(definition_bytes).hexdigest()

                new_graph_definition = GraphDefinition(
                    id=str(uuid.uuid4()),
                    name=graph_data.name,
                    workspace_id=target_workspace_id,
                    workflow_id=new_workflow_id,
                    definition_json=definition_str,
                    description=graph_data.description,
                    version=1,
                    is_latest=True,
                    parent_version_id=None,
                    created_by=user_identifier,
                    file_hash=file_hash,
                    size_bytes=len(definition_bytes),
                )
                db.add(new_graph_definition)

                agent_template.usage_count += 1

                db.commit()

                logger.info(
                    "[AGENT-LIBRARY] Cloned agent template %s into workflow %s",
                    agent_id,
                    new_workflow_id,
                )
                return new_workflow_id

        except Exception as exc:
            logger.error(
                "[AGENT-LIBRARY] Error cloning agent template %s: %s", agent_id, exc
            )
            raise

        return None

    @staticmethod
    def _build_agent_graph(
        graph_data: GraphData,
        root_agent_id: str,
        template_name: str,
        template_description: str,
        source_workflow_id: str,
    ) -> tuple[Dict[str, Any], str]:
        """Clone the agent node and all connected tools/subagents into a standalone graph."""

        TOOLISH_TYPES: Set[NodeType] = {
            NodeType.TOOL,
            NodeType.WEB_SEARCH,
            NodeType.DOCUMENT_SEARCH,
            NodeType.DATABASE_QUERY,
            NodeType.DATABASE_INSERT,
            NodeType.HTTP_REQUEST,
            NodeType.HTTP_REQUEST_ACTION,
            NodeType.MCP_SERVER,
            NodeType.EMAIL_SEND,
            NodeType.FILE_READ,
        }

        included_ids: Set[str] = set()
        queue: List[str] = []

        connections_by_source: Dict[str, List[Any]] = {}
        for conn in graph_data.connections:
            connections_by_source.setdefault(conn.source_id, []).append(conn)

        node_lookup = {node.uniq_id: node for node in graph_data.nodes}

        def enqueue(node_id: Optional[str]) -> None:
            if node_id and node_id not in included_ids:
                included_ids.add(node_id)
                queue.append(node_id)

        enqueue(root_agent_id)

        while queue:
            current_id = queue.pop(0)
            current_node = node_lookup.get(current_id)
            if not current_node:
                continue

            if current_node.type == NodeType.AGENT:
                # Include sub-agents referencing this node
                for node in graph_data.nodes:
                    if (
                        node.uniq_id not in included_ids
                        and node.type == NodeType.AGENT
                        and (
                            getattr(node, "parent_agent_id", None) == current_id
                            or getattr(
                                getattr(node, "agent_config", None),
                                "parent_agent_id",
                                None,
                            )
                            == current_id
                        )
                    ):
                        enqueue(node.uniq_id)

                # Include tools discovered via helper
                for tool_node in graph_data.get_tool_nodes_for_agent(current_id):
                    enqueue(tool_node.uniq_id)

                # Include nodes referencing this agent in configs
                for node in graph_data.nodes:
                    if node.uniq_id in included_ids:
                        continue
                    if AgentLibraryService._config_references_agent(node, current_id):
                        enqueue(node.uniq_id)

            # Include nodes connected via explicit edges (workflow/delegation/tool)
            for conn in connections_by_source.get(current_id, []):
                target = node_lookup.get(conn.target_id)
                if not target or target.uniq_id in included_ids:
                    continue
                if target.type == NodeType.AGENT or target.type in TOOLISH_TYPES:
                    enqueue(target.uniq_id)

        # Clone nodes with new IDs
        id_map: Dict[str, str] = {}
        cloned_nodes: Dict[str, Any] = {}
        remapped_nodes: List[Any] = []

        for original_id in included_ids:
            original_node = node_lookup.get(original_id)
            if not original_node:
                continue
            clone = copy.deepcopy(original_node)
            new_id = str(uuid.uuid4())
            clone.uniq_id = new_id
            id_map[original_id] = new_id
            cloned_nodes[original_id] = clone
            remapped_nodes.append(clone)

        if root_agent_id not in id_map:
            raise ValueError("Failed to clone root agent node")

        # Remap node relationships
        for original_id, clone in cloned_nodes.items():
            clone.inputs = [
                id_map[input_id] for input_id in clone.inputs if input_id in id_map
            ]
            clone.nexts = [
                id_map[next_id] for next_id in clone.nexts if next_id in id_map
            ]

            if getattr(clone, "parent_agent_id", None):
                clone.parent_agent_id = id_map.get(clone.parent_agent_id)

            AgentLibraryService._remap_config_parent_ids(clone, id_map)

            if hasattr(clone, "position") and clone.position:
                clone.position = copy.deepcopy(clone.position)

        # Remap connections
        remapped_connections: List[Connection] = []
        existing_edge_keys = set()
        for conn in graph_data.connections:
            if conn.source_id in id_map and conn.target_id in id_map:
                new_conn = copy.deepcopy(conn)
                new_conn.source_id = id_map[conn.source_id]
                new_conn.target_id = id_map[conn.target_id]
                remapped_connections.append(new_conn)
                existing_edge_keys.add(
                    (new_conn.source_id, new_conn.target_id, new_conn.connection_type)
                )

        # Ensure delegation edges exist for parent/sub-agent relationships
        for clone in remapped_nodes:
            clone_type_raw = getattr(clone, "type", None)
            if isinstance(clone_type_raw, NodeType):
                clone_type = clone_type_raw.value
            else:
                clone_type = (clone_type_raw or "").upper()

            if clone_type != NodeType.AGENT.value:
                continue

            parent_id = AgentLibraryService._extract_parent_agent_id(clone)
            if parent_id and parent_id in id_map.values():
                edge_key = (parent_id, clone.uniq_id, ConnectionType.DELEGATION)
                if edge_key not in existing_edge_keys:
                    remapped_connections.append(
                        Connection(
                            source_id=parent_id,
                            target_id=clone.uniq_id,
                            connection_type=ConnectionType.DELEGATION,
                        )
                    )
                    existing_edge_keys.add(edge_key)

        connection_summary: Dict[str, int] = {}
        for conn in remapped_connections:
            connection_summary[conn.connection_type.value] = (
                connection_summary.get(conn.connection_type.value, 0) + 1
            )

        agent_graph = GraphData(
            name=template_name,
            description=template_description,
            nodes=remapped_nodes,
            connections=remapped_connections,
            metadata={
                "template_kind": "agent",
                "source_workflow_id": source_workflow_id,
                "source_agent_node_id": root_agent_id,
                "included_nodes": list(included_ids),
            },
        )

        logger.debug(
            "[AGENT-LIBRARY] Built agent graph for %s with %d nodes, %d connections. Connection summary=%s Included IDs=%s",
            root_agent_id,
            len(remapped_nodes),
            len(remapped_connections),
            connection_summary,
            list(included_ids),
        )

        return agent_graph.to_dict(), id_map[root_agent_id]

    @staticmethod
    def _wrap_agent_graph_with_boundaries(
        graph_data: GraphData,
        primary_agent_id: str,
    ) -> None:
        """Ensure a graph has START/END nodes wired to the primary agent."""
        if not primary_agent_id:
            raise ValueError("Primary agent id is required to wrap agent graph")

        primary_agent = graph_data.get_node_by_id(primary_agent_id)
        if not primary_agent:
            raise ValueError(
                f"Primary agent node {primary_agent_id} not found in graph"
            )

        existing_start = next(
            (node for node in graph_data.nodes if node.type == NodeType.START), None
        )
        existing_end = next(
            (node for node in graph_data.nodes if node.type == NodeType.END), None
        )

        x_positions = [getattr(node.position, "x", 0.0) for node in graph_data.nodes]
        min_x = min(x_positions) if x_positions else 0.0
        max_x = max(x_positions) if x_positions else 0.0
        primary_y = getattr(primary_agent.position, "y", 0.0)

        start_node = existing_start or EnhancedNodeData(
            uniq_id=str(uuid.uuid4()),
            name="Start",
            type=NodeType.START,
            position=Position(x=min_x - 250.0, y=primary_y),
            nexts=[primary_agent.uniq_id],
            inputs=[],
            description="Workflow entry point",
        )

        end_node = existing_end or EnhancedNodeData(
            uniq_id=str(uuid.uuid4()),
            name="End",
            type=NodeType.END,
            position=Position(x=max_x + 250.0, y=primary_y),
            inputs=[primary_agent.uniq_id],
            description="Workflow completion",
        )

        if start_node.nexts is None:
            start_node.nexts = []
        if end_node.inputs is None:
            end_node.inputs = []

        if primary_agent.inputs is None:
            primary_agent.inputs = []
        if primary_agent.nexts is None:
            primary_agent.nexts = []

        if existing_start is None:
            graph_data.nodes.insert(0, start_node)
        if existing_end is None:
            graph_data.nodes.append(end_node)

        if primary_agent.uniq_id not in start_node.nexts:
            start_node.nexts.append(primary_agent.uniq_id)
        if start_node.uniq_id not in primary_agent.inputs:
            primary_agent.inputs.append(start_node.uniq_id)

        if end_node.uniq_id not in primary_agent.nexts:
            primary_agent.nexts.append(end_node.uniq_id)
        if primary_agent.uniq_id not in end_node.inputs:
            end_node.inputs.append(primary_agent.uniq_id)

        existing_edges = {
            (conn.source_id, conn.target_id, conn.connection_type)
            for conn in graph_data.connections
        }

        start_edge = (
            start_node.uniq_id,
            primary_agent.uniq_id,
            ConnectionType.WORKFLOW,
        )
        if start_edge not in existing_edges:
            graph_data.connections.append(
                Connection(
                    source_id=start_node.uniq_id,
                    target_id=primary_agent.uniq_id,
                    connection_type=ConnectionType.WORKFLOW,
                )
            )

        end_edge = (primary_agent.uniq_id, end_node.uniq_id, ConnectionType.WORKFLOW)
        if end_edge not in existing_edges:
            graph_data.connections.append(
                Connection(
                    source_id=primary_agent.uniq_id,
                    target_id=end_node.uniq_id,
                    connection_type=ConnectionType.WORKFLOW,
                )
            )

    @staticmethod
    def _remap_config_parent_ids(node: Any, id_map: Dict[str, str]) -> None:
        """Update parent_agent_id references inside known config objects."""
        config_attrs = [
            "agent_config",
            "tool_config",
            "web_search_config",
            "document_search_config",
            "database_query_config",
            "database_insert_config",
            "http_request_config",
            "http_request_action_config",
            "mcp_server_config",
            "email_send_config",
            "file_read_config",
            "subworkflow_config",
            "input_source_config",
        ]

        for attr in config_attrs:
            config = getattr(node, attr, None)
            if not config:
                continue
            if isinstance(config, dict):
                parent_id = config.get("parent_agent_id")
                if parent_id and parent_id in id_map:
                    config["parent_agent_id"] = id_map[parent_id]
            else:
                parent_id = getattr(config, "parent_agent_id", None)
                if parent_id and parent_id in id_map:
                    setattr(config, "parent_agent_id", id_map[parent_id])

    @staticmethod
    def _config_references_agent(node: Any, agent_id: str) -> bool:
        """Check if any config on the node points at the specified agent."""
        config_attrs = [
            "web_search_config",
            "document_search_config",
            "database_query_config",
            "database_insert_config",
            "http_request_config",
            "http_request_action_config",
            "mcp_server_config",
            "email_send_config",
            "file_read_config",
            "subworkflow_config",
            "input_source_config",
            "tool_config",
        ]

        if getattr(node, "parent_agent_id", None) == agent_id:
            return True

        for attr in config_attrs:
            config = getattr(node, attr, None)
            if not config:
                continue
            parent_id = None
            if isinstance(config, dict):
                parent_id = config.get("parent_agent_id")
            else:
                parent_id = getattr(config, "parent_agent_id", None)
            if parent_id == agent_id:
                return True

        return False

    @staticmethod
    def _extract_parent_agent_id(node: Any) -> Optional[str]:
        """Extract a parent agent id from node or its configs."""
        parent_id = getattr(node, "parent_agent_id", None)
        if parent_id:
            return parent_id

        config_attrs = [
            "agent_config",
            "tool_config",
            "web_search_config",
            "document_search_config",
            "database_query_config",
            "database_insert_config",
            "http_request_config",
            "http_request_action_config",
            "mcp_server_config",
            "email_send_config",
            "file_read_config",
            "subworkflow_config",
            "input_source_config",
        ]

        for attr in config_attrs:
            config = getattr(node, attr, None)
            if not config:
                continue
            if isinstance(config, dict):
                parent_id = config.get("parent_agent_id")
            else:
                parent_id = getattr(config, "parent_agent_id", None)
            if parent_id:
                return parent_id

        return None

    @staticmethod
    def _build_agent_metadata(
        agent_node,
        source_workflow_id: str,
        source_agent_node_id: str,
    ) -> Dict[str, Any]:
        """Create metadata payload stored with the agent template."""
        llm_config = getattr(agent_node.agent_config, "llm_config", None)

        metadata: Dict[str, Any] = {
            "source_workflow_id": source_workflow_id,
            "source_agent_node_id": source_agent_node_id,
        }

        if llm_config:
            metadata["model_provider"] = getattr(llm_config, "provider", None)
            metadata["model_name"] = getattr(llm_config, "model_name", None) or getattr(
                llm_config, "display_name", None
            )

        return metadata

    @staticmethod
    def can_delete_agent_template(template_id: str, user_identifier: str) -> bool:
        """Return True if the user can delete the specified agent template."""
        try:
            with get_db() as db:
                template = (
                    db.query(AgentTemplate)
                    .options(joinedload(AgentTemplate.creator))
                    .filter(AgentTemplate.id == template_id)
                    .first()
                )

                if not template or not template.creator:
                    return False

                creator_email = (template.creator.email or "").lower()
                creator_id = template.creator.id

                if creator_email and creator_email == user_identifier.lower():
                    return True
                if creator_id and creator_id == user_identifier:
                    return True

                return False
        except Exception as exc:
            logger.error("[AGENT-LIBRARY] Error checking delete permission: %s", exc)
            return False

    @staticmethod
    def deactivate_agent_template(template_id: str) -> bool:
        """Soft delete an agent template."""
        try:
            with get_db() as db:
                template = (
                    db.query(AgentTemplate)
                    .options(
                        joinedload(AgentTemplate.graph_definition),
                        joinedload(AgentTemplate.workflow),
                    )
                    .filter(AgentTemplate.id == template_id)
                    .first()
                )

                if not template:
                    logger.error(
                        "[AGENT-LIBRARY] Agent template not found: %s", template_id
                    )
                    return False

                # Soft delete the template entry
                graph_definition = template.graph_definition
                template_workflow = template.workflow

                db.delete(template)
                if graph_definition:
                    db.delete(graph_definition)
                if template_workflow:
                    db.delete(template_workflow)

                db.commit()
                logger.info(
                    "[AGENT-LIBRARY] Deactivated agent template: %s", template_id
                )
                return True
        except Exception as exc:
            logger.error("[AGENT-LIBRARY] Error deactivating agent template: %s", exc)
            return False

    @staticmethod
    def _create_tool_nodes_from_list(
        agent_node_id: str,
        tool_names: List[str],
        base_x: float,
        base_y: float,
    ) -> tuple[List[EnhancedNodeData], List[Connection]]:
        """Create tool nodes and connections from a list of tool names.

        Args:
            agent_node_id: ID of the parent agent node
            tool_names: List of tool names (e.g., ["document_search", "web_search"])
            base_x: Base X position for tool nodes
            base_y: Base Y position for tool nodes

        Returns:
            Tuple of (tool_nodes, connections) where:
                - tool_nodes: List of created tool node objects
                - connections: List of TOOL connections from agent to tools
        """
        from backend.models.workflow.configs import (
            DatabaseQueryConfig,
            DocumentSearchConfig,
            EmailSendConfig,
            FileReadConfig,
            HttpRequestConfig,
            MCPServerConfig,
            WebSearchConfig,
        )

        tool_nodes = []
        connections = []

        # Map tool names to node types and configs
        tool_type_map = {
            "document_search": NodeType.DOCUMENT_SEARCH,
            "web_search": NodeType.WEB_SEARCH,
            "database_query": NodeType.DATABASE_QUERY,
            "http_request": NodeType.HTTP_REQUEST,
            "mcp_server": NodeType.MCP_SERVER,
            "email_send": NodeType.EMAIL_SEND,
            "file_reader": NodeType.FILE_READ,
        }

        # Tool display names
        tool_display_names = {
            "document_search": "Document Search",
            "web_search": "Web Search",
            "database_query": "Database Query",
            "http_request": "HTTP Request",
            "mcp_server": "MCP Server",
            "email_send": "Email Send",
            # "file_reader": "File Reader",  # Temporarily disabled due to ISG security audit
        }
        
        # Blocked/disabled tools - TEMPORARILY COMMENTED
        # Will be re-enabled after ISG fixes are implemented
        # blocked_tools = {"file_reader"}  # Coming Soon due to security updates

        # Spacing for tool nodes
        x_offset = 0
        spacing = 200

        for tool_name in tool_names:
            # TEMPORARILY COMMENTED: file_reader blocking check
            # if tool_name in blocked_tools:
            #     logger.info(
            #         f"[AGENT-LIBRARY] Skipping blocked tool: {tool_name} (Coming Soon)"
            #     )
            #     continue

            node_type = tool_type_map.get(tool_name)
            if not node_type:
                logger.warning(
                    f"[AGENT-LIBRARY] Unknown tool name in import: {tool_name}"
                )
                continue

            tool_node_id = str(uuid.uuid4())
            display_name = tool_display_names.get(tool_name, tool_name)

            # Create the appropriate config based on tool type
            tool_config = None
            if node_type == NodeType.DOCUMENT_SEARCH:
                tool_config = DocumentSearchConfig(
                    parent_agent_id=agent_node_id,
                    search_k=5,
                    search_type="similarity",
                )
            elif node_type == NodeType.WEB_SEARCH:
                tool_config = WebSearchConfig(
                    parent_agent_id=agent_node_id,
                    max_results=5,
                )
            elif node_type == NodeType.DATABASE_QUERY:
                tool_config = DatabaseQueryConfig(parent_agent_id=agent_node_id)
            elif node_type == NodeType.HTTP_REQUEST:
                tool_config = HttpRequestConfig(parent_agent_id=agent_node_id)
            elif node_type == NodeType.MCP_SERVER:
                tool_config = MCPServerConfig(parent_agent_id=agent_node_id)
            elif node_type == NodeType.EMAIL_SEND:
                tool_config = EmailSendConfig()
            elif node_type == NodeType.FILE_READ:
                tool_config = FileReadConfig()

            # Position nodes horizontally below the agent
            position = Position(x=base_x + x_offset, y=base_y)
            x_offset += spacing

            # Create the tool node
            tool_node = EnhancedNodeData(
                uniq_id=tool_node_id,
                name=display_name,
                type=node_type,
                description=f"{display_name} tool",
                position=position,
            )

            # Set the appropriate config attribute
            if node_type == NodeType.DOCUMENT_SEARCH and tool_config:
                tool_node.document_search_config = tool_config
            elif node_type == NodeType.WEB_SEARCH and tool_config:
                tool_node.web_search_config = tool_config
            elif node_type == NodeType.DATABASE_QUERY and tool_config:
                tool_node.database_query_config = tool_config
            elif node_type == NodeType.HTTP_REQUEST and tool_config:
                tool_node.http_request_config = tool_config
            elif node_type == NodeType.MCP_SERVER and tool_config:
                tool_node.mcp_server_config = tool_config
            elif node_type == NodeType.EMAIL_SEND and tool_config:
                tool_node.email_send_config = tool_config
            elif node_type == NodeType.FILE_READ and tool_config:
                tool_node.file_read_config = tool_config

            tool_nodes.append(tool_node)

            # Create TOOL connection from agent to this tool
            connections.append(
                Connection(
                    source_id=agent_node_id,
                    target_id=tool_node_id,
                    connection_type=ConnectionType.TOOL,
                )
            )

        return tool_nodes, connections

    @staticmethod
    def _serialize_agent_summary(agent: AgentTemplate) -> Dict[str, Any]:
        """Serialize an agent template into a response payload."""
        graph_def = agent.graph_definition
        definition = {}
        if graph_def:
            definition = (
                json.loads(graph_def.definition_json)
                if isinstance(graph_def.definition_json, str)
                else graph_def.definition_json
            )

        nodes = definition.get("nodes", []) or []
        agent_nodes = [
            node for node in nodes if (node.get("type") or "").lower() == "agent"
        ]
        tool_count = sum(
            1 for node in nodes if (node.get("type") or "").lower() == "tool"
        )

        summary: Dict[str, Any] = {
            "id": agent.id,
            "workflow_id": agent.workflow_id,
            "graph_definition_id": agent.graph_definition_id,
            "name": agent.name,
            "description": agent.description,
            "category": agent.category,
            "tags": agent.tags,
            "complexity": agent.complexity,
            "icon_color": agent.icon_color,
            "usage_count": agent.usage_count,
            "version": agent.version,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "creator_name": agent.creator.name if agent.creator else "Unknown",
            "creator_email": agent.creator.email if agent.creator else None,
            "node_count": len(nodes),
            "agent_count": len(agent_nodes),
            "tool_count": tool_count,
            "primary_agent_node_id": agent.primary_agent_node_id,
            "primary_agent_label": agent.primary_agent_label,
            "agent_metadata": agent.agent_metadata or {},
        }

        return summary

    @staticmethod
    def import_agent_from_json(
        agent_data: Dict[str, Any],
        user_identifier: str,
        metadata_override: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Import an agent from JSON configuration.

        Args:
            agent_data: Validated agent import data
            user_identifier: User importing the agent
            metadata_override: Optional metadata to override from JSON

        Returns:
            Agent template ID if successful, None otherwise
        """
        from backend.api.library.import_schema import ImportAgentRequest
        from backend.models.workflow.configs import AgentConfig, LLMConfig

        try:
            # Validate the data using Pydantic
            import_request = ImportAgentRequest(**agent_data)

            # Get effective configurations
            metadata = import_request.get_effective_metadata()
            agent_config_data = import_request.get_effective_agent_config()

            # Apply metadata overrides if provided and re-validate
            if metadata_override:
                # Create a new metadata object with overrides to trigger validation
                from backend.api.library.import_schema import ImportAgentMetadata

                metadata_dict = {
                    "category": metadata_override.get("category", metadata.category),
                    "tags": metadata_override.get("tags", metadata.tags),
                    "complexity": metadata_override.get(
                        "complexity", metadata.complexity
                    ),
                    "icon_color": metadata_override.get(
                        "icon_color", metadata.icon_color
                    ),
                    "version": metadata.version,
                    "author": metadata.author,
                }
                # Re-validate through Pydantic model
                metadata = ImportAgentMetadata(**metadata_dict)

            # Build LLM configuration
            llm_config = None
            if import_request.llm_config:
                llm_data = import_request.llm_config
                llm_config = LLMConfig(
                    provider=llm_data.provider,
                    model_name=llm_data.model_name,
                    temperature=llm_data.temperature or 0.0,
                    max_tokens=llm_data.max_tokens,
                    api_key_env_var=llm_data.api_key_env_var or "AZURE_OPENAI_API_KEY",
                    base_url_env_var=llm_data.base_url_env_var
                    or "AZURE_OPENAI_ENDPOINT",
                    api_base=llm_data.api_base,
                    api_version=llm_data.api_version,
                    deployment_name=llm_data.deployment_name,
                    timeout=llm_data.timeout or 120,
                    max_retries=llm_data.max_retries or 3,
                )

            # Build agent configuration
            agent_config = AgentConfig(
                agent_type=agent_config_data.agent_type,
                system_prompt=import_request.system_prompt,
                max_iterations=agent_config_data.max_iterations,
                temperature=agent_config_data.temperature or 0.0,
                tools=agent_config_data.tools,
                memory_enabled=agent_config_data.memory_enabled,
                memory_window_size=agent_config_data.memory_window_size,
                memory_strategy=agent_config_data.memory_strategy,
                custom_instructions=agent_config_data.custom_instructions,
                structured_outputs=agent_config_data.structured_outputs,
                llm_config=llm_config,
                document_search_enabled=agent_config_data.document_search_enabled,
                document_collections=agent_config_data.document_collections,
                document_ids=agent_config_data.document_ids,
                search_k=agent_config_data.search_k,
                search_type=agent_config_data.search_type,
                citation_format=agent_config_data.citation_format,
                is_orchestrator=agent_config_data.is_orchestrator,
                orchestrator_mode=agent_config_data.orchestrator_mode,
                delegation_strategy=agent_config_data.delegation_strategy,
                delegated_agents=agent_config_data.delegated_agents,
            )

            # Create a minimal graph with the agent node
            agent_node_id = str(uuid.uuid4())
            agent_node = EnhancedNodeData(
                uniq_id=agent_node_id,
                name=import_request.name,
                type=NodeType.AGENT,
                description=import_request.description,
                agent_config=agent_config,
                position=Position(x=400.0, y=300.0),
            )

            # Create tool nodes from the tools list
            tool_nodes, tool_connections = (
                AgentLibraryService._create_tool_nodes_from_list(
                    agent_node_id=agent_node_id,
                    tool_names=agent_config_data.tools,
                    base_x=400.0,
                    base_y=500.0,
                )
            )

            # Create graph with agent and tool nodes
            all_nodes = [agent_node] + tool_nodes
            graph_data = GraphData(
                name=import_request.name,
                description=import_request.description,
                nodes=all_nodes,
                connections=tool_connections,
                metadata={
                    "imported": True,
                    "import_version": metadata.version or "1.0.0",
                },
            )

            # Wrap with START/END nodes
            AgentLibraryService._wrap_agent_graph_with_boundaries(
                graph_data, agent_node_id
            )

            # Serialize to JSON
            graph_dict = graph_data.to_dict()
            definition_str = json.dumps(graph_dict)
            definition_bytes = definition_str.encode("utf-8")
            file_hash = hashlib.sha256(definition_bytes).hexdigest()

            with get_db() as db:
                # Resolve user
                user = (
                    db.query(User)
                    .filter(
                        or_(User.id == user_identifier, User.email == user_identifier)
                    )
                    .first()
                )
                user_id = user.id if user else None

                # Create workflow
                template_workflow_id = str(uuid.uuid4())
                template_workflow = Workflow(
                    id=template_workflow_id,
                    name=import_request.name,
                    description=import_request.description,
                    created_by_user_id=user_id,
                    latest_version=1,
                    is_deleted=False,
                    http_trigger_token="wf_" + secrets.token_urlsafe(32),
                )
                db.add(template_workflow)
                db.flush()

                # Create graph definition
                template_graph_definition_id = str(uuid.uuid4())
                template_graph_definition = GraphDefinition(
                    id=template_graph_definition_id,
                    name=import_request.name,
                    workspace_id="agent-library",
                    workflow_id=template_workflow_id,
                    definition_json=definition_str,
                    description=import_request.description,
                    version=1,
                    is_latest=True,
                    parent_version_id=None,
                    created_by=user_identifier,
                    file_hash=file_hash,
                    size_bytes=len(definition_bytes),
                )
                db.add(template_graph_definition)
                db.flush()

                # Build agent metadata
                agent_metadata = {
                    "imported": True,
                    "import_version": metadata.version or "1.0.0",
                    "author": metadata.author,
                }
                if llm_config:
                    agent_metadata["model_provider"] = llm_config.provider
                    agent_metadata["model_name"] = llm_config.model_name

                # Create agent template
                agent_template = AgentTemplate(
                    workflow_id=template_workflow_id,
                    graph_definition_id=template_graph_definition_id,
                    name=import_request.name,
                    description=import_request.description,
                    category=metadata.category or [],
                    tags=metadata.tags or [],
                    icon_color=metadata.icon_color,
                    complexity=metadata.complexity,
                    created_by_user_id=user_id,
                    usage_count=0,
                    version=1,
                    parent_template_id=None,
                    is_latest_version=True,
                    is_active=True,
                    primary_agent_node_id=agent_node_id,
                    primary_agent_label=import_request.name,
                    agent_metadata=agent_metadata,
                )

                db.add(agent_template)
                db.commit()

                logger.info(
                    "[AGENT-LIBRARY] Imported agent template: %s (ID: %s)",
                    import_request.name,
                    agent_template.id,
                )
                return agent_template.id

        except Exception as exc:
            logger.error("[AGENT-LIBRARY] Error importing agent from JSON: %s", exc)
            raise
