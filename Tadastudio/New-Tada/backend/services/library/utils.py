"""Helpers for normalizing library assets before persistence."""

from typing import Any

from backend.models.workflow import GraphData


def strip_model_deployments(graph_data: GraphData) -> None:
    """Remove model deployment bindings so templates are unconfigured by default."""

    def _clear_llm_config(config: Any) -> None:
        """Completely remove LLM config from the given config object."""
        if not config:
            return

        # Handle dict-based configs
        if isinstance(config, dict):
            if "llm_config" in config:
                config["llm_config"] = None
            return

        # Handle object-based configs
        if hasattr(config, "llm_config"):
            setattr(config, "llm_config", None)

    if not graph_data:
        return

    # Drop saved metadata that is user-specific
    graph_data.metadata = {}

    # Strip graph-level default LLM config
    graph_data.default_llm_config = None

    # Strip LLM config from all node configs
    for node in graph_data.nodes:
        _clear_llm_config(getattr(node, "agent_config", None))
        _clear_llm_config(getattr(node, "condition_config", None))
        _clear_llm_config(getattr(node, "file_read_config", None))
