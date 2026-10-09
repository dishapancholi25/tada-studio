"""Deserialization logic for workflow models.

This module provides deserialization (from_dict) functionality for
converting dictionaries to workflow model instances, with reduced complexity.
"""

from dataclasses import fields
from typing import Any, Dict

from ..base import InputSourceConfig, Position
from ..configs import (
    AgentConfig,
    BranchConfig,
    CheckpointConfig,
    CodeExecutorConfig,
    ConditionConfig,
    DatabaseInsertConfig,
    DatabaseQueryActionConfig,
    DatabaseQueryConfig,
    DocumentLoadConfig,
    DocumentRetrieveConfig,
    DocumentSearchConfig,
    EmailCheckpointConfig,
    EmailSendConfig,
    EmailSendToolConfig,
    EmailSendToolFieldConfig,
    EndNodeConfig,
    FileReadConfig,
    FileWriteConfig,
    ForEachConfig,
    HttpRequestActionConfig,
    HttpRequestConfig,
    LLMConfig,
    MCPServerConfig,
    SubWorkflowConfig,
    ToolConfig,
    WebSearchConfig,
)
from ..enums import NodeType


class NodeDeserializer:
    """Handles deserialization of dictionaries to workflow nodes."""

    @staticmethod
    def deserialize_node_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize node data from dictionary.

        This method modifies the data dict in place, converting
        nested dictionaries to their appropriate dataclass instances.

        Args:
            data: Dictionary data to deserialize

        Returns:
            Modified data dictionary ready for node construction
        """
        # Handle field name aliasing (frontend uses different field names)
        if "node_type" in data:
            data["type"] = data.pop("node_type")
        if "id" in data:
            if "uniq_id" not in data:
                data["uniq_id"] = data["id"]
            del data["id"]

        # Handle enum conversion
        if "type" in data and isinstance(data["type"], str):
            data["type"] = NodeType(data["type"])

        # Handle base structures
        NodeDeserializer._deserialize_base_structures(data)

        # Handle config objects
        NodeDeserializer._deserialize_configs(data)

        return data

    @staticmethod
    def _deserialize_base_structures(data: Dict[str, Any]) -> None:
        """Deserialize base structures (position, input_source).

        Args:
            data: Dictionary data to modify
        """
        if "position" in data and isinstance(data["position"], dict):
            data["position"] = Position(**data["position"])

        # Remove style field if present (no longer used)
        data.pop("style", None)

        if "input_source_config" in data and data["input_source_config"]:
            if isinstance(data["input_source_config"], dict):
                config_data = data["input_source_config"].copy()
                valid_fields = {field.name for field in fields(InputSourceConfig)}
                filtered_data = {
                    k: v for k, v in config_data.items() if k in valid_fields
                }
                data["input_source_config"] = InputSourceConfig(**filtered_data)

    @staticmethod
    def _deserialize_configs(data: Dict[str, Any]) -> None:
        """Deserialize all configuration objects.

        Args:
            data: Dictionary data to modify
        """
        # Complex configs with special handling
        NodeDeserializer._deserialize_complex_configs(data)

        # Simple configs with field filtering
        NodeDeserializer._deserialize_simple_configs(data)

    @staticmethod
    def _deserialize_complex_configs(data: Dict[str, Any]) -> None:
        """Deserialize complex configurations requiring special handling.

        Args:
            data: Dictionary data to modify
        """
        if "tool_config" in data and data["tool_config"]:
            NodeDeserializer._deserialize_tool_config(data)

        if "agent_config" in data and data["agent_config"]:
            NodeDeserializer._deserialize_agent_config(data)

        if "condition_config" in data and data["condition_config"]:
            NodeDeserializer._deserialize_condition_config(data)

        if "web_search_config" in data and data["web_search_config"]:
            NodeDeserializer._deserialize_web_search_config(data)

        if "checkpoint_config" in data and data["checkpoint_config"]:
            NodeDeserializer._deserialize_checkpoint_config(data)

        if "email_send_tool_config" in data and data["email_send_tool_config"]:
            NodeDeserializer._deserialize_email_send_tool_config(data)

    @staticmethod
    def _deserialize_simple_configs(data: Dict[str, Any]) -> None:
        """Deserialize simple configurations with field filtering.

        Args:
            data: Dictionary data to modify
        """
        simple_config_map = {
            "code_executor_config": CodeExecutorConfig,
            "document_search_config": DocumentSearchConfig,
            "database_query_config": DatabaseQueryConfig,
            "database_query_action_config": DatabaseQueryActionConfig,
            "database_insert_config": DatabaseInsertConfig,
            "http_request_config": HttpRequestConfig,
            "http_request_action_config": HttpRequestActionConfig,
            "email_send_config": EmailSendConfig,
            "file_read_config": FileReadConfig,
            "mcp_server_config": MCPServerConfig,
            "subworkflow_config": SubWorkflowConfig,
            "for_each_config": ForEachConfig,
            "end_node_config": EndNodeConfig,
            "document_retrieve_config": DocumentRetrieveConfig,
            "document_load_config": DocumentLoadConfig,
            "file_write_config": FileWriteConfig,
        }

        for config_key, config_class in simple_config_map.items():
            if config_key in data and data[config_key]:
                NodeDeserializer._deserialize_simple_config(
                    data, config_key, config_class
                )

    @staticmethod
    def _deserialize_tool_config(data: Dict[str, Any]) -> None:
        """Deserialize tool configuration.

        Args:
            data: Dictionary data to modify
        """
        if isinstance(data["tool_config"], dict):
            data["tool_config"] = ToolConfig(**data["tool_config"])

    @staticmethod
    def _deserialize_agent_config(data: Dict[str, Any]) -> None:
        """Deserialize agent configuration with LLM config.

        Args:
            data: Dictionary data to modify
        """
        if not isinstance(data["agent_config"], dict):
            return

        agent_data = data["agent_config"].copy()

        # Handle nested LLM config
        if "llm_config" in agent_data and agent_data["llm_config"]:
            if isinstance(agent_data["llm_config"], dict):
                agent_data["llm_config"] = LLMConfig(**agent_data["llm_config"])

        # Filter out unknown fields for backward compatibility
        valid_fields = {field.name for field in fields(AgentConfig)}
        filtered_agent_data = {k: v for k, v in agent_data.items() if k in valid_fields}

        # Handle deprecated chunk_size field
        if "chunk_size" in agent_data and "chunk_size" not in valid_fields:
            print("Warning: Ignoring deprecated 'chunk_size' field in agent_config")

        data["agent_config"] = AgentConfig(**filtered_agent_data)

    @staticmethod
    def _deserialize_condition_config(data: Dict[str, Any]) -> None:
        """Deserialize condition configuration with LLM and branches.

        Args:
            data: Dictionary data to modify
        """
        if not isinstance(data["condition_config"], dict):
            return

        condition_data = data["condition_config"].copy()

        # Handle nested LLM config
        if "llm_config" in condition_data and condition_data["llm_config"]:
            if isinstance(condition_data["llm_config"], dict):
                condition_data["llm_config"] = LLMConfig(**condition_data["llm_config"])

        # Handle branches array
        if "branches" in condition_data and isinstance(
            condition_data["branches"], list
        ):
            branches = []
            for branch_data in condition_data["branches"]:
                if isinstance(branch_data, dict):
                    branch = BranchConfig(
                        label=branch_data.get("label", ""),
                        color=branch_data.get("color", "#8b5cf6"),
                        handle_id=branch_data.get("handle_id", ""),
                        condition=branch_data.get("condition", {}),
                    )
                    branches.append(branch)
                elif isinstance(branch_data, BranchConfig):
                    branches.append(branch_data)
            condition_data["branches"] = branches

        # Filter out unknown fields
        valid_fields = {field.name for field in fields(ConditionConfig)}
        filtered_data = {k: v for k, v in condition_data.items() if k in valid_fields}

        data["condition_config"] = ConditionConfig(**filtered_data)

    @staticmethod
    def _deserialize_checkpoint_config(data: Dict[str, Any]) -> None:
        """Deserialize checkpoint configuration with email config.

        Args:
            data: Dictionary data to modify
        """
        if not isinstance(data["checkpoint_config"], dict):
            return

        config_data = data["checkpoint_config"].copy()

        # Handle nested email config
        if "email_config" in config_data and config_data["email_config"]:
            if isinstance(config_data["email_config"], dict):
                email_config_data = config_data["email_config"].copy()
                valid_email_fields = {
                    field.name for field in fields(EmailCheckpointConfig)
                }
                filtered_email_data = {
                    k: v
                    for k, v in email_config_data.items()
                    if k in valid_email_fields
                }
                config_data["email_config"] = EmailCheckpointConfig(
                    **filtered_email_data
                )

        # Filter out unknown fields
        valid_fields = {field.name for field in fields(CheckpointConfig)}
        filtered_data = {k: v for k, v in config_data.items() if k in valid_fields}

        data["checkpoint_config"] = CheckpointConfig(**filtered_data)

    @staticmethod
    def _deserialize_web_search_config(data: Dict[str, Any]) -> None:
        """Deserialize web search configuration with debug logging.

        Args:
            data: Dictionary data to modify
        """
        if not isinstance(data["web_search_config"], dict):
            return

        config_data = data["web_search_config"].copy()
        valid_fields = {field.name for field in fields(WebSearchConfig)}
        filtered_data = {k: v for k, v in config_data.items() if k in valid_fields}

        from backend.services.config import get_logger
        from backend.services.execution.logging import redact_sensitive_data

        logger = get_logger(__name__)
        logger.info("[WEB_SEARCH_DEBUG] from_dict - Deserializing web_search_config")
        logger.info(
            f"[WEB_SEARCH_DEBUG] from_dict - Raw data: {redact_sensitive_data(config_data)}"
        )
        logger.info(
            f"[WEB_SEARCH_DEBUG] from_dict - Filtered data: {redact_sensitive_data(filtered_data)}"
        )

        data["web_search_config"] = WebSearchConfig(**filtered_data)
        logger.info(
            f"[WEB_SEARCH_DEBUG] from_dict - Created config: {redact_sensitive_data(data['web_search_config'])}"
        )

    @staticmethod
    def _deserialize_email_send_tool_config(data: Dict[str, Any]) -> None:
        """Deserialize email send tool configuration with nested field configs.

        Args:
            data: Dictionary data to modify
        """
        if not isinstance(data["email_send_tool_config"], dict):
            return

        config_data = data["email_send_tool_config"].copy()

        # Handle nested field configs (to_address, subject, body)
        for field_key in ["to_address", "subject", "body"]:
            if field_key in config_data and isinstance(config_data[field_key], dict):
                field_data = config_data[field_key].copy()
                valid_fields = {f.name for f in fields(EmailSendToolFieldConfig)}
                filtered_field_data = {
                    k: v for k, v in field_data.items() if k in valid_fields
                }
                config_data[field_key] = EmailSendToolFieldConfig(**filtered_field_data)

        valid_fields = {f.name for f in fields(EmailSendToolConfig)}
        filtered_data = {k: v for k, v in config_data.items() if k in valid_fields}

        data["email_send_tool_config"] = EmailSendToolConfig(**filtered_data)

    @staticmethod
    def _deserialize_simple_config(
        data: Dict[str, Any], config_key: str, config_class: type
    ) -> None:
        """Deserialize a simple config with field filtering.

        Args:
            data: Dictionary data to modify
            config_key: Key in data dict for this config
            config_class: Dataclass to instantiate
        """
        if not isinstance(data[config_key], dict):
            return

        config_data = data[config_key].copy()
        valid_fields = {field.name for field in fields(config_class)}
        filtered_data = {k: v for k, v in config_data.items() if k in valid_fields}
        data[config_key] = config_class(**filtered_data)
