"""Validation and export handlers.

This module provides handler functions for graph validation, export,
and structured output operations.
"""

from typing import Any, Dict, List
from urllib.parse import unquote

from backend.models.workflow import GraphData, NodeType
from backend.services.config import get_logger
from backend.services.dependency_injection import get_graph_manager
from backend.services.guardrails.resolver import LayeredPolicyResolver
from backend.services.guardrails.serialization import config_to_pipeline_entry
from backend.services.structured_output import StructuredOutputGenerator

from ..constants import LOG_PREFIX
from ..dependencies import get_graph_or_404, get_user_identifier
from ..exceptions import GraphNotFoundError


logger = get_logger(__name__)


def _resolve_guardrails_pipelines(graph: GraphData) -> Dict[str, List[Dict[str, Any]]]:
    """Resolve guardrails pipelines for each node that supports guardrails.

    Returns a mapping of node uniq_id to its serialized guardrails pipeline.
    Each pipeline entry is a decomposed dict with policy metadata and a
    ``guardrails`` list of individually named guardrail configs.

    Does NOT mutate graph nodes.

    Args:
        graph: The graph to resolve guardrails for

    Returns:
        Mapping of node_id → list of decomposed pipeline entry dicts
    """
    logger.debug(f"{LOG_PREFIX} Resolving guardrails pipelines for export in graph '{graph.name}'")

    # Node types that support guardrails
    supported_node_types = {
        NodeType.AGENT,
        NodeType.DATABASE_QUERY,
        NodeType.DATABASE_QUERY_ACTION,
        NodeType.HTTP_REQUEST,
        NodeType.HTTP_REQUEST_ACTION,
        NodeType.WEB_SEARCH,
        NodeType.MCP_SERVER,
        NodeType.EMAIL_SEND,
        NodeType.EMAIL_SEND_TOOL,
        NodeType.FILE_READ,
        NodeType.FILE_WRITE,
    }

    pipelines: Dict[str, List[Dict[str, Any]]] = {}

    for node in graph.nodes:
        if node.type not in supported_node_types:
            continue

        try:
            pipeline = LayeredPolicyResolver.resolve_as_pipeline(
                workflow_id=graph.workflow_id,
                node_id=node.uniq_id,
                model_id=None,
            )
            enabled = [cfg for cfg in pipeline if cfg.enabled]
            if enabled:
                pipelines[node.uniq_id] = [config_to_pipeline_entry(cfg) for cfg in enabled]
                logger.debug(
                    f"{LOG_PREFIX} Resolved {len(enabled)} guardrail(s) for node "
                    f"'{node.name}' ({node.type.value})"
                )

        except Exception as e:
            logger.warning(
                f"{LOG_PREFIX} Failed to resolve guardrails for node '{node.name}': {e}"
            )

    return pipelines


async def handle_validate_graph(
    graph_name: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate a graph for completeness and correctness.

    Args:
        graph_name: Name of the graph (URL-encoded)
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and validation result

    Raises:
        GraphNotFoundError: If graph not found
    """
    # URL decode the graph name
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Validating graph '{graph_name}' for user '{user_identifier}'"
    )

    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    # Use the enhanced validation from GraphData
    validation_result = graph.validate()

    # Add LLM-specific validation
    llm_validation = []
    for node in graph.nodes:
        if node.type == NodeType.AGENT:
            if not node.agent_config or not node.agent_config.llm_config:
                llm_validation.append(
                    f"Agent node '{node.name}' missing LLM configuration"
                )
            else:
                # Validate LLM config
                llm_config = node.agent_config.llm_config
                if not llm_config.provider:
                    llm_validation.append(
                        f"Agent node '{node.name}' missing LLM provider"
                    )
                if not llm_config.model_name:
                    llm_validation.append(
                        f"Agent node '{node.name}' missing model name"
                    )

    # Combine validations
    if llm_validation:
        validation_result["errors"].extend(llm_validation)
        validation_result["is_valid"] = False

    return {"success": True, "validation": validation_result}


async def handle_export_graph(
    graph_name: str, export_format: str, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Export graph in specified format.

    Args:
        graph_name: Name of the graph (URL-encoded)
        export_format: Format to export (langgraph, etc.)
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status, format, and exported data

    Raises:
        GraphNotFoundError: If graph not found
    """
    # URL decode the graph name
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Exporting graph '{graph_name}' in format '{export_format}' "
        f"for user '{user_identifier}'"
    )

    # Ensure latest graph is loaded before export
    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    # Resolve guardrails pipelines (does not mutate graph)
    guardrails_pipelines = _resolve_guardrails_pipelines(graph)

    if export_format == "langgraph":
        exported_data = get_graph_manager().export_to_langgraph_format(graph_name)
        if not exported_data:
            exported_data = graph.to_dict()
    else:
        # Default to full format
        exported_data = graph.to_dict()

    if not exported_data:
        raise GraphNotFoundError(graph_name)

    # Inject guardrails pipelines into exported nodes
    if guardrails_pipelines and isinstance(exported_data, dict):
        for node_dict in exported_data.get("nodes", []):
            node_id = node_dict.get("uniq_id")
            if node_id and node_id in guardrails_pipelines:
                node_dict["guardrails_pipeline"] = guardrails_pipelines[node_id]

    # Remove environment-specific metadata from export
    # workspace_id is tied to the source environment and should be set by the importer
    if isinstance(exported_data, dict) and "metadata" in exported_data:
        metadata = exported_data.get("metadata", {})
        if isinstance(metadata, dict):
            # Remove workspace_id as it's environment-specific
            metadata.pop("workspace_id", None)
            # Also remove other environment-specific fields
            metadata.pop("last_saved_by", None)
            metadata.pop("last_saved_at", None)
            metadata.pop("last_loaded_by", None)
            metadata.pop("last_loaded_at", None)

    return {"success": True, "format": export_format, "data": exported_data}


async def handle_validate_structured_output_schema(
    schema_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate a structured output schema.

    Args:
        schema_data: Schema data to validate

    Returns:
        Dictionary with success status and validation result
    """
    logger.info(f"{LOG_PREFIX} Validating structured output schema")

    try:
        result = StructuredOutputGenerator.validate_schema(schema_data)
        return {"success": True, "validation_result": result}
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Schema validation failed: {e}")
        return {
            "success": False,
            "error": "Schema validation failed. Check server logs for details.",
        }


async def handle_preview_structured_output_code(
    schema_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Preview the generated Pydantic model code for a schema.

    Args:
        schema_data: Schema data to preview

    Returns:
        Dictionary with success status and generated code
    """
    logger.info(f"{LOG_PREFIX} Previewing structured output code")

    try:
        validation_result = StructuredOutputGenerator.validate_schema(schema_data)
        if not validation_result["valid"]:
            return {"success": False, "errors": validation_result["errors"]}

        schema = validation_result["schema"]
        model_code = StructuredOutputGenerator._generate_model_code(schema)

        return {
            "success": True,
            "model_code": model_code,
            "tool_code": None,  # Tool code generation not needed
        }
    except Exception as e:
        logger.error(f"{LOG_PREFIX} Code preview failed: {e}")
        return {
            "success": False,
            "error": "Code preview failed. Check server logs for details.",
        }
