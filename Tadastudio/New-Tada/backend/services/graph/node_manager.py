"""Node management service.

This module provides node CRUD (Create, Read, Update, Delete) operations for workflow graphs,
including node creation, configuration, validation, and lifecycle management.

Example:
    >>> from backend.services.graph.node_manager import NodeManager
    >>> manager = NodeManager(model_service)
    >>> node = manager.create_node(NodeType.AGENT, "My Agent")
"""

import uuid
from dataclasses import asdict, fields
from datetime import datetime
from typing import Any, Dict, Optional

from backend.models.workflow import (
    AgentConfig,
    ConditionConfig,
    EnhancedNodeData,
    LLMConfig,
    NodeType,
    Position,
    SubWorkflowConfig,
    ToolConfig,
)
from backend.services.config import get_logger

from .constants import (
    DEFAULT_AGENT_SYSTEM_PROMPT,
    LOG_PREFIX_NODE_MANAGER,
)
from .exceptions import NodeNotFoundError


logger = get_logger(__name__)


class NodeManager:
    """Service for managing workflow nodes.

    This service handles all node-related operations including creation,
    updates, deletion, and configuration management.

    Methods:
        create_node: Create a new node with configuration
        update_node: Update existing node properties
        delete_node: Delete a node from a graph
        add_node_to_graph: Add a node to a graph
    """

    def __init__(self, model_service: Any = None):
        """Initialize node manager.

        Args:
            model_service: Model deployment service for LLM defaults
        """
        self.model_service = model_service
        logger.debug(f"{LOG_PREFIX_NODE_MANAGER} Initialized")

    def create_node(
        self,
        node_type: NodeType,
        name: str,
        position: Position = None,
        tool_template: Optional[str] = None,
        agent_template: Optional[str] = None,
        condition_prompt: Optional[str] = None,
        llm_config_override: Optional[str] = None,
        **kwargs,
    ) -> EnhancedNodeData:
        """Create a new node with the specified type and configuration.

        Args:
            node_type: Type of node to create
            name: Node name
            position: Node position (defaults to 0,0)
            tool_template: Deprecated tool template
            agent_template: Deprecated agent template
            condition_prompt: Condition prompt (for CONDITION nodes)
            llm_config_override: Deprecated LLM config override
            **kwargs: Additional node properties

        Returns:
            The created EnhancedNodeData node

        Example:
            >>> node = manager.create_node(
            ...     NodeType.AGENT,
            ...     "Customer Support Agent",
            ...     position=Position(100, 200)
            ... )
        """
        logger.debug(
            f"{LOG_PREFIX_NODE_MANAGER} Creating node: {name} (type: {node_type})"
        )

        node_id = str(uuid.uuid4())

        if position is None:
            position = Position(0, 0)

        now = datetime.now().isoformat()

        # Create base node
        node = EnhancedNodeData(
            uniq_id=node_id,
            name=name,
            type=node_type,
            position=position,
            created_at=now,
            updated_at=now,
            **kwargs,
        )

        # Configure node based on type
        self._configure_node_by_type(node, node_type, condition_prompt, **kwargs)

        logger.info(f"{LOG_PREFIX_NODE_MANAGER} Created node: {name} (ID: {node_id})")

        return node

    def _configure_node_by_type(
        self,
        node: EnhancedNodeData,
        node_type: NodeType,
        condition_prompt: Optional[str],
        **kwargs,
    ) -> None:
        """Configure node based on its type.

        Args:
            node: The node to configure
            node_type: Type of node
            condition_prompt: Optional condition prompt
            **kwargs: Additional configuration parameters
        """
        if node_type == NodeType.TOOL:
            node.tool_config = ToolConfig()

        elif node_type == NodeType.AGENT:
            self._configure_agent_node(node, **kwargs)

        elif node_type == NodeType.CONDITION:
            self._configure_condition_node(node, condition_prompt)

        elif node_type == NodeType.SUBWORKFLOW:
            self._configure_subworkflow_node(node, **kwargs)

        elif node_type == NodeType.FILE_WRITE:
            from backend.models.workflow import FileWriteConfig

            node.file_write_config = FileWriteConfig()

    def _configure_agent_node(self, node: EnhancedNodeData, **kwargs) -> None:
        """Configure an agent node with default LLM deployment.

        Args:
            node: The agent node to configure
            **kwargs: Additional configuration (description, etc.)
        """
        default_system_prompt = DEFAULT_AGENT_SYSTEM_PROMPT

        # Try to get default LLM deployment
        llm_config = None
        if self.model_service:
            default_deployment = self.model_service.get_default_deployment(
                model_type="llm"
            )

            if default_deployment:
                llm_config = LLMConfig(
                    provider=default_deployment["provider"],
                    model_name=default_deployment["model_name"],
                    model_deployment_id=default_deployment["id"],
                    display_name=default_deployment.get("display_name"),
                )
                logger.info(
                    f"{LOG_PREFIX_NODE_MANAGER} Created agent '{node.name}' "
                    f"with default LLM deployment: {default_deployment['name']}"
                )
            else:
                logger.debug(
                    f"{LOG_PREFIX_NODE_MANAGER} Created agent '{node.name}' "
                    "without LLM config - no default deployment set"
                )

        node.agent_config = AgentConfig(
            llm_config=llm_config, system_prompt=default_system_prompt
        )

    def _configure_condition_node(
        self, node: EnhancedNodeData, condition_prompt: Optional[str]
    ) -> None:
        """Configure a condition node with optional LLM deployment.

        Args:
            node: The condition node to configure
            condition_prompt: Condition evaluation prompt
        """
        prompt = condition_prompt if condition_prompt is not None else node.name

        # Try to get default LLM deployment for LLM-based conditions
        llm_config = None
        if self.model_service:
            default_deployment = self.model_service.get_default_deployment(
                model_type="llm"
            )

            if default_deployment:
                llm_config = LLMConfig(
                    provider=default_deployment["provider"],
                    model_name=default_deployment["model_name"],
                    model_deployment_id=default_deployment["id"],
                    display_name=default_deployment.get("display_name"),
                )
                logger.info(
                    f"{LOG_PREFIX_NODE_MANAGER} Created condition '{node.name}' "
                    f"with default LLM deployment: {default_deployment['name']}"
                )
            else:
                logger.debug(
                    f"{LOG_PREFIX_NODE_MANAGER} Created condition '{node.name}' "
                    "without LLM config - no default deployment set"
                )

        node.condition_config = ConditionConfig(
            condition_prompt=prompt, llm_config=llm_config
        )

    def _configure_subworkflow_node(self, node: EnhancedNodeData, **kwargs) -> None:
        """Configure a subworkflow node.

        Args:
            node: The subworkflow node to configure
            **kwargs: Configuration parameters (subworkflow_config, description)
        """
        if "subworkflow_config" in kwargs and isinstance(
            kwargs["subworkflow_config"], dict
        ):
            config_dict = kwargs.pop("subworkflow_config")
            node.subworkflow_config = SubWorkflowConfig(
                workflow_name=config_dict.get("workflow_name", node.name),
                delegation_description=config_dict.get("delegation_description", ""),
                input_schema=config_dict.get("input_schema", {}),
                output_schema=config_dict.get("output_schema", {}),
                input_description=config_dict.get("input_description", ""),
                output_description=config_dict.get("output_description", ""),
                timeout=config_dict.get("timeout", 600),
                share_context=config_dict.get("share_context", True),
                max_retries=config_dict.get("max_retries", 1),
                allow_parallel_execution=config_dict.get(
                    "allow_parallel_execution", False
                ),
                cache_results=config_dict.get("cache_results", False),
                cache_ttl=config_dict.get("cache_ttl", 3600),
            )
        else:
            # Create default subworkflow config
            node.subworkflow_config = SubWorkflowConfig(
                workflow_name=node.name,
                delegation_description=kwargs.get(
                    "description", f"Execute {node.name} workflow"
                ),
            )

    def update_node(self, graph: Any, node_id: str, updates: Dict[str, Any]) -> bool:
        """Update a node in the specified graph.

        Args:
            graph: The graph containing the node
            node_id: ID of the node to update
            updates: Dictionary of property updates

        Returns:
            True if update succeeded, False otherwise

        Raises:
            NodeNotFoundError: If the node doesn't exist

        Example:
            >>> success = manager.update_node(
            ...     graph,
            ...     "node-123",
            ...     {"name": "Updated Name", "description": "New description"}
            ... )
        """
        logger.debug(
            f"{LOG_PREFIX_NODE_MANAGER} Updating node: {node_id} in graph: {graph.name}"
        )

        node = graph.get_node_by_id(node_id)

        if not node:
            raise NodeNotFoundError(node_id, graph.name)

        # Update basic properties
        self._update_basic_properties(node, updates)

        # Update type-specific configurations
        self._update_type_specific_config(node, updates)

        node.updated_at = datetime.now().isoformat()

        logger.info(
            f"{LOG_PREFIX_NODE_MANAGER} Updated node: {node.name} (ID: {node_id})"
        )

        return True

    def _update_basic_properties(
        self, node: EnhancedNodeData, updates: Dict[str, Any]
    ) -> None:
        """Update basic node properties.

        Args:
            node: The node to update
            updates: Dictionary of updates
        """
        for key, value in updates.items():
            if key in [
                "name",
                "description",
                "prompt_template",
                "delegation_description",
            ]:
                setattr(node, key, value)
            elif key == "position" and isinstance(value, dict):
                node.position = Position(**value)

    def _update_type_specific_config(
        self, node: EnhancedNodeData, updates: Dict[str, Any]
    ) -> None:
        """Update type-specific node configuration.

        Args:
            node: The node to update
            updates: Dictionary of updates
        """
        # Tool configuration
        if "tool_config" in updates and node.type == NodeType.TOOL:
            if isinstance(updates["tool_config"], dict):
                node.tool_config = ToolConfig(**updates["tool_config"])

        # Agent configuration
        if "agent_config" in updates and node.type == NodeType.AGENT:
            self._update_agent_config(node, updates["agent_config"])

        # Condition configuration
        if "condition_config" in updates and node.type == NodeType.CONDITION:
            self._update_condition_config(node, updates["condition_config"])

        # Document search configuration
        if (
            "document_search_config" in updates
            and node.type == NodeType.DOCUMENT_SEARCH
        ):
            from backend.models.workflow import DocumentSearchConfig

            if isinstance(updates["document_search_config"], dict):
                node.document_search_config = DocumentSearchConfig(
                    **updates["document_search_config"]
                )

        # Database query configuration
        if "database_query_config" in updates and node.type == NodeType.DATABASE_QUERY:
            from backend.models.workflow import DatabaseQueryConfig

            if isinstance(updates["database_query_config"], dict):
                node.database_query_config = DatabaseQueryConfig(
                    **updates["database_query_config"]
                )

        # Web search configuration
        if "web_search_config" in updates and node.type == NodeType.WEB_SEARCH:
            from backend.models.workflow import WebSearchConfig
            from backend.services.execution.logging import redact_sensitive_data

            if isinstance(updates["web_search_config"], dict):
                redacted_config = redact_sensitive_data(updates["web_search_config"])
                logger.info(
                    f"[WEB_SEARCH_DEBUG] update_node - Updating web_search_config "
                    f"for node {node.uniq_id}: {redacted_config}"
                )
                node.web_search_config = WebSearchConfig(**updates["web_search_config"])

        # HTTP request configuration
        if "http_request_config" in updates and node.type == NodeType.HTTP_REQUEST:
            from backend.models.workflow import HttpRequestConfig

            if isinstance(updates["http_request_config"], dict):
                node.http_request_config = HttpRequestConfig(
                    **updates["http_request_config"]
                )

        # MCP server configuration
        if "mcp_server_config" in updates and node.type == NodeType.MCP_SERVER:
            from backend.models.workflow import MCPServerConfig

            if isinstance(updates["mcp_server_config"], dict):
                node.mcp_server_config = MCPServerConfig(**updates["mcp_server_config"])

        # Subworkflow configuration
        if "subworkflow_config" in updates and node.type == NodeType.SUBWORKFLOW:
            if isinstance(updates["subworkflow_config"], dict):
                node.subworkflow_config = SubWorkflowConfig(
                    **updates["subworkflow_config"]
                )

        # Database insert configuration
        if (
            "database_insert_config" in updates
            and node.type == NodeType.DATABASE_INSERT
        ):
            from backend.models.workflow import DatabaseInsertConfig

            if isinstance(updates["database_insert_config"], dict):
                node.database_insert_config = DatabaseInsertConfig(
                    **updates["database_insert_config"]
                )

        # Database query action configuration
        if (
            "database_query_action_config" in updates
            and node.type == NodeType.DATABASE_QUERY_ACTION
        ):
            from backend.models.workflow.configs import DatabaseQueryActionConfig

            if isinstance(updates["database_query_action_config"], dict):
                valid_fields = {
                    f.name for f in __import__("dataclasses").fields(DatabaseQueryActionConfig)
                }
                node.database_query_action_config = DatabaseQueryActionConfig(
                    **{k: v for k, v in updates["database_query_action_config"].items()
                       if k in valid_fields}
                )

        # Email send configuration
        if "email_send_config" in updates and node.type == NodeType.EMAIL_SEND:
            from backend.models.workflow import EmailSendConfig

            if isinstance(updates["email_send_config"], dict):
                node.email_send_config = EmailSendConfig(**updates["email_send_config"])

        # Email send tool configuration
        if (
            "email_send_tool_config" in updates
            and node.type == NodeType.EMAIL_SEND_TOOL
        ):
            from backend.models.workflow import (
                EmailSendToolConfig,
                EmailSendToolFieldConfig,
            )

            if isinstance(updates["email_send_tool_config"], dict):
                config_data = updates["email_send_tool_config"].copy()
                # Handle nested field configs (to_address, subject, body)
                for field_key in ["to_address", "subject", "body"]:
                    if field_key in config_data and isinstance(
                        config_data[field_key], dict
                    ):
                        config_data[field_key] = EmailSendToolFieldConfig(
                            **config_data[field_key]
                        )
                node.email_send_tool_config = EmailSendToolConfig(**config_data)

        # File read configuration
        if "file_read_config" in updates and node.type == NodeType.FILE_READ:
            from backend.models.workflow import FileReadConfig

            if isinstance(updates["file_read_config"], dict):
                node.file_read_config = FileReadConfig(**updates["file_read_config"])

        # File write configuration
        if "file_write_config" in updates and node.type == NodeType.FILE_WRITE:
            from backend.models.workflow import FileWriteConfig

            if isinstance(updates["file_write_config"], dict):
                node.file_write_config = FileWriteConfig(**updates["file_write_config"])

        # Checkpoint configuration
        if "checkpoint_config" in updates and node.type == NodeType.CHECKPOINT:
            from backend.models.workflow import CheckpointConfig

            if isinstance(updates["checkpoint_config"], dict):
                node.checkpoint_config = CheckpointConfig(
                    **updates["checkpoint_config"]
                )

        # HTTP request action configuration
        if (
            "http_request_action_config" in updates
            and node.type == NodeType.HTTP_REQUEST_ACTION
        ):
            from backend.models.workflow import HttpRequestActionConfig

            if isinstance(updates["http_request_action_config"], dict):
                import dataclasses
                valid_fields = {f.name for f in dataclasses.fields(HttpRequestActionConfig)}
                raw = updates["http_request_action_config"]
                if "request_body_template" in raw and "body_template" not in raw:
                    raw = {**raw, "body_template": raw["request_body_template"]}
                filtered = {k: v for k, v in raw.items() if k in valid_fields}
                node.http_request_action_config = HttpRequestActionConfig(**filtered)

        # END node configuration
        if "end_node_config" in updates and node.type == NodeType.END:
            from backend.models.workflow import EndNodeConfig

            logger.info(
                f"[END-NODE-DEBUG] Updating end_node_config for node {node.uniq_id}"
            )
            logger.info(f"[END-NODE-DEBUG] Config data: {updates['end_node_config']}")

            if isinstance(updates["end_node_config"], dict):
                node.end_node_config = EndNodeConfig(**updates["end_node_config"])
                logger.info(
                    f"[END-NODE-DEBUG] Successfully created EndNodeConfig: "
                    f"{node.end_node_config}"
                )

        # Document retrieve configuration
        if (
            "document_retrieve_config" in updates
            and node.type == NodeType.DOCUMENT_RETRIEVE
        ):
            from backend.models.workflow import DocumentRetrieveConfig

            if isinstance(updates["document_retrieve_config"], dict):
                node.document_retrieve_config = DocumentRetrieveConfig(
                    **updates["document_retrieve_config"]
                )

        # Document load configuration
        if "document_load_config" in updates and node.type == NodeType.DOCUMENT_LOAD:
            from backend.models.workflow import DocumentLoadConfig

            if isinstance(updates["document_load_config"], dict):
                node.document_load_config = DocumentLoadConfig(
                    **updates["document_load_config"]
                )

        # Input source configuration (can be attached to any node)
        if "input_source_config" in updates:
            from backend.models.workflow import InputSourceConfig

            if updates["input_source_config"] is None:
                # Allow clearing the input source config
                node.input_source_config = None
            elif isinstance(updates["input_source_config"], dict):
                node.input_source_config = InputSourceConfig(
                    **updates["input_source_config"]
                )

        # Code executor configuration
        # Handles CODE_EXECUTOR nodes that run Python/JavaScript code in workflows.
        # Config includes: language, code, timeout, memory_limit, input_variables, etc.
        if "code_executor_config" in updates and node.type == NodeType.CODE_EXECUTOR:
            from backend.models.workflow import CodeExecutorConfig

            if isinstance(updates["code_executor_config"], dict):
                node.code_executor_config = CodeExecutorConfig(
                    **updates["code_executor_config"]
                )

        # For Each configuration
        # Handles FOR_EACH nodes that iterate over an array from a source node.
        # Config includes: source_node_id, field_path, concurrency_limit, etc.
        if "for_each_config" in updates and node.type == NodeType.FOR_EACH:
            from backend.models.workflow import ForEachConfig

            if isinstance(updates["for_each_config"], dict):
                node.for_each_config = ForEachConfig(**updates["for_each_config"])

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Recursively merge *override* into *base*, returning a new dict.

        - Dict values are merged recursively so that nested keys not present
          in *override* are preserved from *base*.
        - Explicit ``None`` values in *override* **remove** the key from the
          result, allowing the frontend to clear a previously stored value
          (e.g. ``max_tokens``) so that deployment defaults apply at runtime.
        - All other value types in *override* replace the corresponding
          *base* value outright.
        """
        merged = dict(base)
        for key, value in override.items():
            if value is None:
                merged.pop(key, None)
            elif (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = NodeManager._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _update_agent_config(self, node: EnhancedNodeData, config_update: Any) -> None:
        """Update agent configuration with deep-merge logic.

        Nested dicts (e.g. ``llm_config``) are merged recursively so that
        a partial patch like ``{"llm_config": {"temperature": 0.3}}`` only
        touches the specified key and preserves all other fields.

        Args:
            node: The agent node to update
            config_update: Configuration updates
        """
        if isinstance(config_update, dict):
            if node.agent_config:
                existing_config = asdict(node.agent_config)
                merged = self._deep_merge(existing_config, config_update)
                logger.info(
                    "[AGENT_CONFIG_PATCH] config_update=%s merged_llm_config=%s",
                    config_update,
                    merged.get("llm_config"),
                )
                if "llm_config" in merged and isinstance(merged["llm_config"], dict):
                    merged["llm_config"] = LLMConfig(**merged["llm_config"])
                # Filter out removed fields for backward compatibility
                from dataclasses import fields as dc_fields

                valid = {f.name for f in dc_fields(AgentConfig)}
                node.agent_config = AgentConfig(**{k: v for k, v in merged.items() if k in valid})
            else:
                if "llm_config" in config_update and isinstance(
                    config_update["llm_config"], dict
                ):
                    config_update["llm_config"] = LLMConfig(
                        **config_update["llm_config"]
                    )
                from dataclasses import fields as dc_fields

                valid = {f.name for f in dc_fields(AgentConfig)}
                node.agent_config = AgentConfig(**{k: v for k, v in config_update.items() if k in valid})

    def _update_condition_config(
        self, node: EnhancedNodeData, config_update: Any
    ) -> None:
        """Update condition configuration.

        Args:
            node: The condition node to update
            config_update: Configuration updates
        """
        if isinstance(config_update, dict):
            # Handle nested LLM config updates
            if "llm_config" in config_update and isinstance(
                config_update["llm_config"], dict
            ):
                config_update["llm_config"] = LLMConfig(**config_update["llm_config"])
            # Strip unknown keys to avoid TypeError from frontend-only fields
            valid_fields = {f.name for f in fields(ConditionConfig)}
            filtered = {k: v for k, v in config_update.items() if k in valid_fields}
            node.condition_config = ConditionConfig(**filtered)

    def delete_node(self, graph: Any, node_id: str) -> bool:
        """Delete a node and all its connections.

        Args:
            graph: The graph containing the node
            node_id: ID of the node to delete

        Returns:
            True if deletion succeeded, False otherwise

        Raises:
            NodeNotFoundError: If the node doesn't exist

        Example:
            >>> success = manager.delete_node(graph, "node-123")
        """
        logger.debug(
            f"{LOG_PREFIX_NODE_MANAGER} Deleting node: {node_id} "
            f"from graph: {graph.name}"
        )

        node = graph.get_node_by_id(node_id)

        if not node:
            raise NodeNotFoundError(node_id, graph.name)

        # Remove all connections involving this node
        graph.connections = [
            conn
            for conn in graph.connections
            if conn.source_id != node_id and conn.target_id != node_id
        ]

        # Update other nodes' relationships
        self._cleanup_node_relationships(graph, node_id, node)

        # Remove the node
        graph.nodes = [n for n in graph.nodes if n.uniq_id != node_id]
        graph.updated_at = datetime.now().isoformat()

        logger.info(
            f"{LOG_PREFIX_NODE_MANAGER} Deleted node: {node.name} (ID: {node_id})"
        )

        return True

    def _cleanup_node_relationships(
        self, graph: Any, node_id: str, deleted_node: EnhancedNodeData
    ) -> None:
        """Clean up relationships when deleting a node.

        Args:
            graph: The graph
            node_id: ID of the deleted node
            deleted_node: The node being deleted
        """
        for other_node in graph.nodes:
            if node_id in other_node.nexts:
                other_node.nexts.remove(node_id)
            if node_id in other_node.inputs:
                other_node.inputs.remove(node_id)

            # Handle condition nodes
            if other_node.type == NodeType.CONDITION:
                if other_node.true_next == node_id:
                    other_node.true_next = None
                if other_node.false_next == node_id:
                    other_node.false_next = None

            # Special handling for agent nodes losing tool connections
            if (
                other_node.type == NodeType.AGENT
                and deleted_node.type == NodeType.TOOL
                and deleted_node.tool_config
                and deleted_node.tool_config.tool_name
                and other_node.agent_config
            ):
                tool_name = deleted_node.tool_config.tool_name
                if tool_name in other_node.agent_config.tools:
                    other_node.agent_config.tools.remove(tool_name)

    def add_node_to_graph(self, graph: Any, node: EnhancedNodeData) -> bool:
        """Add a node to a graph and auto-create any missing tools for agents.

        Args:
            graph: The graph to add the node to
            node: The node to add

        Returns:
            True if addition succeeded

        Example:
            >>> node = manager.create_node(NodeType.AGENT, "My Agent")
            >>> success = manager.add_node_to_graph(graph, node)
        """
        logger.debug(
            f"{LOG_PREFIX_NODE_MANAGER} Adding node: {node.name} to graph: {graph.name}"
        )

        # Dedup guard: prevent duplicate nodes with the same ID
        existing_ids = {n.uniq_id for n in graph.nodes}
        if node.uniq_id in existing_ids:
            logger.warning(
                f"{LOG_PREFIX_NODE_MANAGER} Node {node.uniq_id} ({node.name}) "
                f"already exists in graph {graph.name}, skipping duplicate"
            )
            return False

        graph.nodes.append(node)

        # Auto-create missing tools for agent nodes
        if node.type == NodeType.AGENT:
            self._ensure_agent_tools_exist(graph, node)

        logger.info(
            f"{LOG_PREFIX_NODE_MANAGER} Added node: {node.name} "
            f"(ID: {node.uniq_id}) to graph: {graph.name}"
        )

        return True

    def _ensure_agent_tools_exist(
        self, graph: Any, agent_node: EnhancedNodeData
    ) -> None:
        """Ensure all tools referenced by an agent exist as nodes in the graph.

        Note: Tool nodes are now explicitly connected via the graph UI.
        This is a placeholder for future auto-creation logic if needed.

        Args:
            graph: The graph
            agent_node: The agent node
        """
        if not agent_node.agent_config or not agent_node.agent_config.tools:
            return

        # Tool nodes are now explicitly connected via the graph UI
        # No auto-creation from templates
