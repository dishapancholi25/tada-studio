"""Python export handler.

Handles exporting a workflow graph as a self-contained Python file.
"""

from typing import Any, Dict
from urllib.parse import unquote

from fastapi.responses import Response

from backend.api.model_deployments.dependencies import get_model_deployment_service
from backend.models.workflow import GraphData, NodeType
from backend.services.config import get_logger
from backend.services.export import get_python_exporter

from ..constants import LOG_PREFIX
from ..dependencies import get_graph_or_404, get_user_identifier

logger = get_logger(__name__)

# Standard env var names per provider (matches llm_generator.py fallback defaults)
_PROVIDER_ENV_DEFAULTS: Dict[str, tuple] = {
    "azure_openai": ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT"),
    "openai": ("OPENAI_API_KEY", ""),
    "anthropic": ("ANTHROPIC_API_KEY", ""),
    "google": ("GOOGLE_API_KEY", ""),
}


def _enrich_llm_configs_for_export(graph: GraphData) -> None:
    """Enrich LLM configs that use managed deployments.

    Resolves deployment settings from the database and resets env var names
    to standard provider defaults. Clears credentials to prevent leakage.
    Mutates the graph nodes in-place.
    """
    service = get_model_deployment_service()

    for node in graph.nodes:
        if node.type != NodeType.AGENT:
            continue
        if not node.agent_config or not node.agent_config.llm_config:
            continue

        llm = node.agent_config.llm_config
        if not llm.model_deployment_id:
            continue

        try:
            enriched = service.enrich_llm_config(llm)
        except Exception:
            logger.warning(
                "%s Failed to enrich LLM config for node '%s' "
                "(deployment_id=%s), using raw config",
                LOG_PREFIX,
                node.name,
                llm.model_deployment_id,
            )
            continue

        # Reset env var names to standard provider defaults
        provider = (enriched.provider or "openai").lower()
        api_key_default, base_url_default = _PROVIDER_ENV_DEFAULTS.get(
            provider, ("OPENAI_API_KEY", "")
        )
        enriched.api_key_env_var = api_key_default
        enriched.base_url_env_var = base_url_default

        # Clear decrypted credentials — must never appear in generated code
        enriched.credentials = {}

        node.agent_config.llm_config = enriched


async def handle_export_python(
    graph_name: str, current_user: Dict[str, Any]
) -> Response:
    """Export a graph as a self-contained Python file.

    Args:
        graph_name: Name of the graph (URL-encoded)
        current_user: Current user from JWT token

    Returns:
        Response with Python file content

    Raises:
        GraphNotFoundError: If graph not found
    """
    graph_name = unquote(graph_name)
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Exporting graph '{graph_name}' as Python for user '{user_identifier}'"
    )

    graph = get_graph_or_404(graph_name, user_identifier, reload=True)

    # Enrich managed deployment configs before export
    _enrich_llm_configs_for_export(graph)

    exporter = get_python_exporter()
    python_code = exporter.export(graph)

    # Sanitize filename
    safe_filename = "".join(
        c if c.isalnum() or c in ("_", "-") else "_" for c in graph_name
    )

    return Response(
        content=python_code,
        media_type="text/x-python",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}_workflow.py"'
        },
    )
