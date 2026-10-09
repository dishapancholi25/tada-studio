"""Node CRUD operation handlers.

This module provides handler functions for node create, read, update,
and delete operations.
"""

from datetime import datetime
from typing import Any, Dict
from urllib.parse import unquote

from backend.models.workflow import (
    AgentConfig,
    CheckpointConfig,
    CodeExecutorConfig,
    ConditionConfig,
    DatabaseInsertConfig,
    DatabaseQueryActionConfig,
    DatabaseQueryConfig,
    DocumentSearchConfig,
    EmailSendConfig,
    EmailSendToolConfig,
    EmailSendToolFieldConfig,
    EndNodeConfig,
    FileReadConfig,
    ForEachConfig,
    HttpRequestActionConfig,
    HttpRequestConfig,
    LLMConfig,
    MCPServerConfig,
    NodeType,
    Position,
    ToolConfig,
    WebSearchConfig,
)
from backend.services.config import get_logger
from backend.services.dependency_injection import get_graph_manager

from ..constants import (
    LOG_PREFIX,
    MSG_NODE_CONFIGURED,
    MSG_NODE_CREATED,
    MSG_NODE_DELETED,
    MSG_NODE_UPDATED,
    MSG_SUBAGENT_CREATED,
)
from ..dependencies import (
    deserialize_agent_config,
    deserialize_condition_config,
    get_graph_or_404,
    get_user_identifier,
)
from ..exceptions import InvalidRequestError, NodeNotFoundError
from ..models import (
    CreateNodeRequest,
    CreateSubAgentRequest,
    NodeConfigRequest,
    UpdateNodeRequest,
)


logger = get_logger(__name__)


def _parse_email_send_tool_config(config_dict: Dict[str, Any]) -> EmailSendToolConfig:
    """Parse email send tool config with nested field configs.

    Args:
        config_dict: Dictionary containing email send tool configuration

    Returns:
        EmailSendToolConfig instance with properly parsed nested field configs
    """
    config_data = config_dict.copy()
    for field_key in ["to_address", "subject", "body"]:
        if field_key in config_data and isinstance(config_data[field_key], dict):
            config_data[field_key] = EmailSendToolFieldConfig(**config_data[field_key])
    return EmailSendToolConfig(**config_data)


async def handle_create_node(
    request: CreateNodeRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a new node in a graph.

    Args:
        request: Create node request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, message, node, and graph data

    Raises:
        GraphNotFoundError: If graph not found
        InvalidRequestError: If node creation fails
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Creating node '{request.name}' "
        f"in graph '{request.graph_name}' for user '{user_identifier}'"
    )

    graph = get_graph_or_404(request.graph_name, user_identifier, reload=True)

    # Prepare position
    position = None
    if request.position:
        position = Position(
            x=request.position.get("x", 0), y=request.position.get("y", 0)
        )

    # Create node with additional parameters
    kwargs = {"description": request.description}

    if request.tool_template:
        kwargs["tool_template"] = request.tool_template

    if request.agent_template:
        kwargs["agent_template"] = request.agent_template

    # Handle subworkflow configuration
    if request.node_type == NodeType.SUBWORKFLOW and request.subworkflow_config:
        kwargs["subworkflow_config"] = request.subworkflow_config

    # Convert string node_type to NodeType enum if needed
    node_type_enum = (
        NodeType(request.node_type)
        if isinstance(request.node_type, str)
        else request.node_type
    )

    # Create node
    node = get_graph_manager().create_node(
        node_type=node_type_enum, name=request.name, position=position, **kwargs
    )

    # Handle custom LLM config for AGENT nodes
    if request.node_type == NodeType.AGENT and request.llm_type and request.model_name:
        if node.agent_config:
            custom_llm_config = LLMConfig(
                provider=request.llm_type, model_name=request.model_name
            )
            node.agent_config.llm_config = custom_llm_config

    # Handle node type-specific configurations
    _apply_node_config(node, request)

    # Add to graph
    logger.info(
        f"{LOG_PREFIX} Adding node '{request.name}' to graph '{request.graph_name}'"
    )
    success = get_graph_manager().add_node_to_graph(request.graph_name, node)
    if not success:
        logger.error(
            f"{LOG_PREFIX} Failed to add node '{request.name}' to graph '{request.graph_name}'"
        )
        raise InvalidRequestError("Failed to add node to graph")

    # Update graph timestamp
    logger.info(
        f"{LOG_PREFIX} Node '{request.name}' added successfully, updating graph timestamp"
    )
    graph.updated_at = datetime.now().isoformat()

    # Persist the change
    logger.info(f"{LOG_PREFIX} Saving graph '{request.graph_name}' to database")
    save_success = get_graph_manager().save_graph(graph, user_identifier)
    if not save_success:
        logger.warning(
            f"{LOG_PREFIX} Failed to persist graph '{request.graph_name}' "
            f"after node create; proceeding but cross-worker cache may be stale"
        )

    logger.info(f"{LOG_PREFIX} Node '{request.name}' created successfully")
    return {
        "success": True,
        "message": MSG_NODE_CREATED.format(node_name=request.name),
        "node": node.to_dict(),
        "graph": graph.to_dict(),
    }


def _apply_node_config(node, request: CreateNodeRequest):
    """Apply node type-specific configuration.

    Args:
        node: Node object to configure
        request: Create node request with configuration
    """
    # Document search configuration
    if request.node_type == NodeType.DOCUMENT_SEARCH and request.document_search_config:
        node.document_search_config = DocumentSearchConfig(
            **request.document_search_config
        )

    # Database query configuration
    if request.node_type == NodeType.DATABASE_QUERY and request.database_query_config:
        node.database_query_config = DatabaseQueryConfig(
            **request.database_query_config
        )

    # HTTP request configuration
    if request.node_type == NodeType.HTTP_REQUEST and request.http_request_config:
        node.http_request_config = HttpRequestConfig(**request.http_request_config)

    # Web search configuration
    if request.node_type == NodeType.WEB_SEARCH and request.web_search_config:
        node.web_search_config = WebSearchConfig(**request.web_search_config)

    # MCP server configuration
    if request.node_type == NodeType.MCP_SERVER and request.mcp_server_config:
        node.mcp_server_config = MCPServerConfig(**request.mcp_server_config)

    # Agent configuration
    if request.node_type == NodeType.AGENT and request.agent_config:
        node.agent_config = deserialize_agent_config(request.agent_config)

    # Condition configuration
    if request.node_type == NodeType.CONDITION and request.condition_config:
        node.condition_config = deserialize_condition_config(request.condition_config)

    # Database insert configuration
    if request.node_type == NodeType.DATABASE_INSERT and request.database_insert_config:
        node.database_insert_config = DatabaseInsertConfig(
            **request.database_insert_config
        )
    if request.node_type == NodeType.DATABASE_QUERY_ACTION and request.database_query_action_config:
        valid_fields = {f.name for f in __import__("dataclasses").fields(DatabaseQueryActionConfig)}
        node.database_query_action_config = DatabaseQueryActionConfig(
            **{k: v for k, v in request.database_query_action_config.items() if k in valid_fields}
        )

    # Input source configuration (can be attached to any node)
    if request.input_source_config:
        from backend.models.workflow import InputSourceConfig

        node.input_source_config = InputSourceConfig(**request.input_source_config)

    # Email send configuration
    if request.node_type == NodeType.EMAIL_SEND and request.email_send_config:
        node.email_send_config = EmailSendConfig(**request.email_send_config)

    # Email send tool configuration
    if request.node_type == NodeType.EMAIL_SEND_TOOL and request.email_send_tool_config:
        node.email_send_tool_config = _parse_email_send_tool_config(
            request.email_send_tool_config
        )

    # File read configuration
    if request.node_type == NodeType.FILE_READ and request.file_read_config:
        node.file_read_config = FileReadConfig(**request.file_read_config)

    # Checkpoint configuration
    if request.node_type == NodeType.CHECKPOINT and request.checkpoint_config:
        node.checkpoint_config = CheckpointConfig(**request.checkpoint_config)

    # HTTP request action configuration
    if (
        request.node_type == NodeType.HTTP_REQUEST_ACTION
        and request.http_request_action_config
    ):
        import dataclasses
        valid_fields = {f.name for f in dataclasses.fields(HttpRequestActionConfig)}
        raw = request.http_request_action_config
        # Map request_body_template → body_template if present
        if "request_body_template" in raw and "body_template" not in raw:
            raw = {**raw, "body_template": raw["request_body_template"]}
        filtered = {k: v for k, v in raw.items() if k in valid_fields}
        node.http_request_action_config = HttpRequestActionConfig(**filtered)

    # End node configuration
    if request.node_type == NodeType.END and request.end_node_config:
        node.end_node_config = EndNodeConfig(**request.end_node_config)

    # For each configuration
    if request.node_type == NodeType.FOR_EACH and request.for_each_config:
        node.for_each_config = ForEachConfig(**request.for_each_config)

    # Code executor configuration
    if request.node_type == NodeType.CODE_EXECUTOR and request.code_executor_config:
        node.code_executor_config = CodeExecutorConfig(**request.code_executor_config)

    # Prompt template
    if request.prompt_template:
        node.prompt_template = request.prompt_template


async def handle_create_sub_agent(
    request: CreateSubAgentRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a sub-agent for an orchestrator.

    Args:
        request: Create sub-agent request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, message, sub-agent, and graph data

    Raises:
        GraphNotFoundError: If graph not found
        InvalidRequestError: If sub-agent creation fails
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Creating sub-agent for parent '{request.parent_agent_id}' "
        f"in graph '{request.graph_name}'"
    )

    # Ensure the graph is loaded
    graph = get_graph_or_404(request.graph_name, user_identifier, reload=True)

    # Prepare position
    position = None
    if request.position:
        position = Position(
            x=request.position.get("x", 0), y=request.position.get("y", 0)
        )

    # Create the sub-agent
    sub_agent = get_graph_manager().create_sub_agent(
        graph_name=request.graph_name,
        parent_agent_id=request.parent_agent_id,
        name=request.name,
        position=position,
        delegation_description=request.delegation_description,
        agent_template=request.agent_template,
    )

    if not sub_agent:
        raise InvalidRequestError("Failed to create sub-agent")

    # Get the updated graph
    graph = get_graph_manager().get_graph(request.graph_name)

    # Update graph timestamp
    logger.info(
        f"{LOG_PREFIX} Sub-agent '{sub_agent.name}' created, updating graph timestamp"
    )
    graph.updated_at = datetime.now().isoformat()

    # Persist the change to database
    logger.info(f"{LOG_PREFIX} Saving graph '{request.graph_name}' to database")
    save_success = get_graph_manager().save_graph(graph, user_identifier)
    if not save_success:
        logger.warning(
            f"{LOG_PREFIX} Failed to persist graph '{request.graph_name}' "
            f"after sub-agent create; proceeding but cross-worker cache may be stale"
        )

    logger.info(f"{LOG_PREFIX} Sub-agent '{sub_agent.name}' created successfully")
    return {
        "success": True,
        "message": MSG_SUBAGENT_CREATED.format(subagent_name=sub_agent.name),
        "sub_agent": sub_agent.to_dict(),
        "graph": graph.to_dict(),
    }


async def handle_update_node(
    request: UpdateNodeRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a node in a graph.

    Args:
        request: Update node request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and message

    Raises:
        GraphNotFoundError: If graph not found
        NodeNotFoundError: If node not found
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Updating node '{request.node_id}' "
        f"in graph '{request.graph_name}'"
    )

    # Ensure graph is loaded
    get_graph_or_404(request.graph_name, user_identifier, reload=True)

    success = get_graph_manager().update_node(
        request.graph_name, request.node_id, request.updates
    )

    if not success:
        raise NodeNotFoundError(request.node_id, request.graph_name)

    logger.info(f"{LOG_PREFIX} Node '{request.node_id}' updated successfully")
    return {"success": True, "message": MSG_NODE_UPDATED}


async def handle_delete_node(graph_name: str, node_id: str) -> Dict[str, Any]:
    """Delete a node from a graph.

    Args:
        graph_name: Name of the graph (URL-encoded)
        node_id: ID of the node to delete

    Returns:
        Dictionary with success status and message

    Raises:
        GraphNotFoundError: If graph not found
        NodeNotFoundError: If node not found
    """
    # URL decode the graph name
    graph_name = unquote(graph_name)
    logger.info(f"{LOG_PREFIX} Deleting node '{node_id}' from graph '{graph_name}'")

    # Check if graph exists
    graph = get_graph_manager().get_graph(graph_name)
    if not graph:
        # Try loading from disk
        graph = get_graph_manager().load_graph(graph_name)
        if not graph:
            from ..exceptions import GraphNotFoundError

            raise GraphNotFoundError(graph_name)

    # Check if node exists
    node = graph.get_node_by_id(node_id)
    if not node:
        raise NodeNotFoundError(node_id, graph_name)

    # Delete the node
    success = get_graph_manager().delete_node(graph_name, node_id)

    if not success:
        raise InvalidRequestError("Failed to delete node")

    logger.info(f"{LOG_PREFIX} Node '{node_id}' deleted successfully")
    return {"success": True, "message": MSG_NODE_DELETED}


async def handle_get_node(
    graph_name: str, node_id: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Get a specific node from a graph.

    Args:
        graph_name: Name of the graph (URL-encoded)
        node_id: ID of the node
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and node data

    Raises:
        GraphNotFoundError: If graph not found
        NodeNotFoundError: If node not found
    """
    # URL decode the graph name
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Getting node '{node_id}' from graph '{graph_name}' "
        f"for user '{user_identifier}'"
    )

    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    node = graph.get_node_by_id(node_id)
    if not node:
        raise NodeNotFoundError(node_id, graph_name)

    return {"success": True, "node": node.to_dict()}


async def handle_configure_node(request: NodeConfigRequest) -> Dict[str, Any]:
    """Configure node-specific settings.

    Args:
        request: Node configuration request

    Returns:
        Dictionary with success status, message, and node data

    Raises:
        GraphNotFoundError: If graph not found
        NodeNotFoundError: If node not found
    """
    from ..exceptions import GraphNotFoundError

    logger.info(
        f"{LOG_PREFIX} Configuring node '{request.node_id}' "
        f"in graph '{request.graph_name}'"
    )

    graph = get_graph_manager().get_graph(request.graph_name)
    if not graph:
        raise GraphNotFoundError(request.graph_name)

    node = graph.get_node_by_id(request.node_id)
    if not node:
        raise NodeNotFoundError(request.node_id, request.graph_name)

    # Apply configuration based on node type
    if node.type == NodeType.TOOL:
        if "tool_config" in request.config:
            node.tool_config = ToolConfig(**request.config["tool_config"])

    elif node.type == NodeType.AGENT:
        if "agent_config" in request.config:
            from dataclasses import fields as dc_fields

            ac_data = request.config["agent_config"]
            valid_fields = {f.name for f in dc_fields(AgentConfig)}
            node.agent_config = AgentConfig(**{k: v for k, v in ac_data.items() if k in valid_fields})

    elif node.type == NodeType.CONDITION:
        if "condition_config" in request.config:
            node.condition_config = ConditionConfig(
                **request.config["condition_config"]
            )

    # Update other properties
    for key, value in request.config.items():
        if key not in ["tool_config", "agent_config", "condition_config"]:
            if hasattr(node, key):
                setattr(node, key, value)

    node.updated_at = datetime.now().isoformat()
    graph.updated_at = datetime.now().isoformat()

    logger.info(f"{LOG_PREFIX} Node '{request.node_id}' configured successfully")
    return {
        "success": True,
        "message": MSG_NODE_CONFIGURED,
        "node": node.to_dict(),
    }


async def handle_get_graph_agents(graph_name: str) -> Dict[str, Any]:
    """Get all agent nodes in a graph with their LLM configurations.

    Args:
        graph_name: Name of the graph (URL-encoded)

    Returns:
        Dictionary with success status, graph name, and list of agents

    Raises:
        GraphNotFoundError: If graph not found
    """
    from ..exceptions import GraphNotFoundError

    # URL decode the graph name
    graph_name = unquote(graph_name)
    logger.info(f"{LOG_PREFIX} Getting agents from graph '{graph_name}'")

    graph = get_graph_manager().get_graph(graph_name)
    if not graph:
        raise GraphNotFoundError(graph_name)

    agents = []
    for node in graph.nodes:
        if node.type == NodeType.AGENT:
            agent_info = {
                "id": node.uniq_id,
                "name": node.name,
                "description": node.description,
                "has_llm_config": bool(
                    node.agent_config and node.agent_config.llm_config
                ),
                "llm_config": None,
            }

            if node.agent_config and node.agent_config.llm_config:
                agent_info["llm_config"] = node.agent_config.llm_config.to_dict()

            agents.append(agent_info)

    return {"success": True, "graph_name": graph_name, "agents": agents}


async def handle_get_graph_state(
    graph_name: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Get current graph state for real-time GUI updates.

    Args:
        graph_name: Name of the graph (URL-encoded)
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and graph state

    Raises:
        GraphNotFoundError: If graph not found
    """
    # URL decode the graph name
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Getting graph state for '{graph_name}' "
        f"for user '{user_identifier}'"
    )

    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    return {
        "success": True,
        "graph": graph.to_dict(),
        "last_updated": graph.updated_at,
        "node_count": len(graph.nodes),
        "connection_count": len(graph.connections),
    }
