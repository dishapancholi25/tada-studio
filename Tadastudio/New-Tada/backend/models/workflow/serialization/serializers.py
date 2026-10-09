"""Serialization logic for workflow models.

This module provides serialization (to_dict) functionality for
converting workflow models to dictionary representations with
selective field inclusion based on node type.
"""

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from ..enums import NodeType

if TYPE_CHECKING:
    from ..configs import AgentConfig
    from ..node import EnhancedNodeData


# Config fields relevant to each node type
NODE_TYPE_CONFIGS: dict[NodeType, list[str]] = {
    NodeType.START: [],
    NodeType.END: ["end_node_config"],
    NodeType.AGENT: ["agent_config"],
    NodeType.CONDITION: ["condition_config"],
    NodeType.TOOL: ["tool_config"],
    NodeType.DOCUMENT_SEARCH: ["document_search_config"],
    NodeType.DATABASE_QUERY: ["database_query_config"],
    NodeType.DATABASE_QUERY_ACTION: ["database_query_action_config"],
    NodeType.DATABASE_INSERT: ["database_insert_config"],
    NodeType.HTTP_REQUEST: ["http_request_config"],
    NodeType.HTTP_REQUEST_ACTION: ["http_request_action_config"],
    NodeType.WEB_SEARCH: ["web_search_config"],
    NodeType.MCP_SERVER: ["mcp_server_config"],
    NodeType.CHECKPOINT: ["checkpoint_config"],
    NodeType.EMAIL_SEND: ["email_send_config"],
    NodeType.EMAIL_SEND_TOOL: ["email_send_tool_config"],
    NodeType.FILE_READ: ["file_read_config"],
    NodeType.FILE_WRITE: ["file_write_config"],
    NodeType.SUBWORKFLOW: ["subworkflow_config"],
    NodeType.FOR_EACH: ["for_each_config"],
    NodeType.DOCUMENT_RETRIEVE: ["document_retrieve_config"],
    NodeType.DOCUMENT_LOAD: ["document_load_config"],
    NodeType.CODE_EXECUTOR: ["code_executor_config"],
    NodeType.SUBGRAPH: [],
    NodeType.STEP: [],
    NodeType.INFO: [],
    NodeType.REVIEW: [],
}

# All config field names that can be excluded
ALL_CONFIG_FIELDS: set[str] = {
    "tool_config",
    "agent_config",
    "condition_config",
    "document_search_config",
    "database_query_config",
    "database_query_action_config",
    "database_insert_config",
    "http_request_config",
    "http_request_action_config",
    "web_search_config",
    "mcp_server_config",
    "end_node_config",
    "checkpoint_config",
    "email_send_config",
    "email_send_tool_config",
    "file_read_config",
    "file_write_config",
    "subworkflow_config",
    "for_each_config",
    "document_retrieve_config",
    "document_load_config",
    "code_executor_config",
}

# Node types that can use input_source_config
NODES_WITH_INPUT_SOURCE: set[NodeType] = {
    NodeType.AGENT,
    NodeType.CONDITION,
    NodeType.STEP,
    NodeType.REVIEW,
    NodeType.DOCUMENT_SEARCH,
    NodeType.DATABASE_QUERY,
    NodeType.DATABASE_INSERT,
    NodeType.HTTP_REQUEST,
    NodeType.HTTP_REQUEST_ACTION,
    NodeType.WEB_SEARCH,
    NodeType.MCP_SERVER,
    NodeType.CHECKPOINT,
    NodeType.EMAIL_SEND,
    NodeType.EMAIL_SEND_TOOL,
    NodeType.FILE_READ,
    NodeType.FILE_WRITE,
    NodeType.SUBWORKFLOW,
    NodeType.FOR_EACH,
    NodeType.DOCUMENT_RETRIEVE,
    NodeType.DOCUMENT_LOAD,
    NodeType.CODE_EXECUTOR,
}

# Fields to exclude when at their default value
FIELD_DEFAULTS: dict[str, Any] = {
    "description": "",
    "prompt_template": "",
    "ext": {},
    "is_enabled": True,
    "execution_timeout": 300,
    "retry_count": 0,
    "max_retries": 3,
    "validation_errors": [],
    "is_valid": True,
    "is_sub_agent": False,
    "is_subworkflow": False,
    "parent_agent_id": None,
    "delegation_description": "",
    "subgraph_name": None,
    "true_next": None,
    "false_next": None,
    "inputs": [],
}

# ============================================================================
# AgentConfig Serialization Constants
# ============================================================================

# Document search fields - exclude when document_search_enabled=false
AGENT_DOC_SEARCH_FIELDS: set[str] = {
    "document_collections",
    "document_ids",
    "search_k",
    "search_type",
    "similarity_threshold",
    "distance_strategy",
    "include_metadata",
    "citation_format",
    "hybrid_search_enabled",
    "search_mode",
    "keyword_weight",
    "rrf_k",
    "full_text_config",
    "min_keyword_relevance",
    "use_reranking",
    "rerank_top_k",
}

# Orchestration fields - exclude when is_orchestrator=false
AGENT_ORCHESTRATION_FIELDS: set[str] = {
    "orchestrator_mode",
    "delegated_agents",
    "delegation_strategy",
    "include_delegation_tools",
    "handoff_pattern",
    "share_context",
    "max_delegation_depth",
    "delegation_timeout",
}

# Memory detail fields - exclude when memory_enabled=false
AGENT_MEMORY_DETAIL_FIELDS: set[str] = {
    "memory_window_size",
    "memory_strategy",
    "memory_persistence",
    "cross_execution_memory",
    "memory_summarization_enabled",
    "memory_summarization_threshold",
}

# AgentConfig fields to exclude at default values
AGENT_CONFIG_DEFAULTS: dict[str, Any] = {
    "agent_type": "conversational",
    "max_iterations": 10,
    "temperature": 0.0,
    "tools": [],
    "custom_instructions": "",
    "tool_binding_mode": "none",
    "tool_choice": "auto",
    "parallel_tool_calls": False,
    "max_tool_calls_per_iteration": 5,
    "tool_call_timeout": 30,
    "structured_outputs": [],
}


class AgentConfigSerializer:
    """Handles serialization of agent configuration with selective field inclusion."""

    @staticmethod
    def config_to_dict(config: "AgentConfig") -> dict[str, Any]:
        """Convert agent config to dictionary with selective field inclusion.

        Excludes fields based on feature flags:
        1. Document search fields when document_search_enabled=false
        2. Orchestration fields when is_orchestrator=false
        3. Memory detail fields when memory_enabled=false
        4. Guardrails config when not present or disabled
        5. Fields at their default values

        Args:
            config: AgentConfig to serialize

        Returns:
            Dictionary representation with minimal fields
        """
        result = asdict(config)

        # 1. Remove document search fields if feature disabled
        if not config.document_search_enabled:
            for field in AGENT_DOC_SEARCH_FIELDS:
                result.pop(field, None)

        # 2. Remove orchestration fields if not orchestrating
        if not config.is_orchestrator:
            for field in AGENT_ORCHESTRATION_FIELDS:
                result.pop(field, None)

        # 3. Remove memory detail fields if memory disabled
        if not config.memory_enabled:
            for field in AGENT_MEMORY_DETAIL_FIELDS:
                result.pop(field, None)

        # 4. Remove guardrails_config if not present or not enabled
        if "guardrails_config" in result:
            guardrails_cfg = result.get("guardrails_config")
            if guardrails_cfg is None or (isinstance(guardrails_cfg, dict) and not guardrails_cfg.get("enabled", False)):
                result.pop("guardrails_config", None)

        # 5. Remove fields at default values
        for field_name, default_value in AGENT_CONFIG_DEFAULTS.items():
            if field_name in result and result[field_name] == default_value:
                del result[field_name]

        return result


class NodeSerializer:
    """Handles serialization of workflow nodes to dictionaries."""

    @staticmethod
    def node_to_dict(node: "EnhancedNodeData") -> dict[str, Any]:
        """Convert node to dictionary with proper serialization.

        Performs selective field inclusion:
        1. Only includes config fields relevant to the node type
        2. Excludes input_source_config for nodes that don't use it
        3. Excludes fields that are at their default values
        4. Applies selective serialization to agent_config (excludes disabled features)

        Args:
            node: Node to serialize

        Returns:
            Dictionary representation of the node with minimal fields
        """
        result = asdict(node)

        # Get node type (handle both enum and string cases)
        node_type = (
            node.type if isinstance(node.type, NodeType) else NodeType(node.type)
        )
        result["type"] = node_type.value

        # 1. Remove irrelevant config fields based on node type
        relevant_configs = NODE_TYPE_CONFIGS.get(node_type, [])
        for config_field in ALL_CONFIG_FIELDS:
            if config_field not in relevant_configs:
                result.pop(config_field, None)

        # 2. Remove input_source_config if not applicable to this node type
        if node_type not in NODES_WITH_INPUT_SOURCE:
            result.pop("input_source_config", None)

        # 3. Remove fields that are at their default values
        for field_name, default_value in FIELD_DEFAULTS.items():
            if field_name in result and result[field_name] == default_value:
                del result[field_name]

        # 4. Apply selective serialization to agent_config
        if "agent_config" in result and node.agent_config is not None:
            result["agent_config"] = AgentConfigSerializer.config_to_dict(
                node.agent_config
            )

        # 5. Apply selective serialization to tool configs (remove guardrails if not enabled)
        tool_config_fields = [
            "database_query_config",
            "database_query_action_config",
            "database_insert_config",
            "http_request_config",
            "http_request_action_config",
            "web_search_config",
            "mcp_server_config",
            "email_send_config",
            "email_send_tool_config",
            "file_read_config",
            "file_write_config",
        ]
        for config_field in tool_config_fields:
            if config_field in result and result[config_field] is not None:
                config_dict = result[config_field]
                if isinstance(config_dict, dict) and "guardrails_config" in config_dict:
                    guardrails_cfg = config_dict.get("guardrails_config")
                    if guardrails_cfg is None or (isinstance(guardrails_cfg, dict) and not guardrails_cfg.get("enabled", False)):
                        config_dict.pop("guardrails_config", None)

        # Debug logging for web search nodes
        if node_type == NodeType.WEB_SEARCH:
            from backend.services.config import get_logger
            from backend.services.execution.logging import redact_sensitive_data

            logger = get_logger(__name__)
            redacted_node_config = redact_sensitive_data(node.web_search_config)
            redacted_result_config = redact_sensitive_data(
                result.get("web_search_config")
            )
            logger.info(
                f"[WEB_SEARCH_DEBUG] to_dict - Node {node.uniq_id} "
                f"web_search_config: {redacted_node_config}"
            )
            logger.info(
                f"[WEB_SEARCH_DEBUG] to_dict - Result web_search_config: "
                f"{redacted_result_config}"
            )

        return result

