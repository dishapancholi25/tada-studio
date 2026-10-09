"""Helper functions for workflow publishing."""

from datetime import datetime

from fastapi import HTTPException

from backend.models.workflow.publication import WorkflowPublicationConfig
from ....services.config import get_logger
from ....services.dependency_injection import get_graph_manager


logger = get_logger(__name__)


def load_graph(graph_name: str, user_identifier: str = "default"):
    """Load a graph from memory or disk."""
    graph_manager = get_graph_manager()
    graph = graph_manager.get_graph(graph_name)
    if not graph:
        graph = graph_manager.load_graph(graph_name, user_identifier)
    return graph


def load_and_validate_published_graph(
    graph_name: str, user_identifier: str = "default"
):
    """Load and validate that a graph exists and is published."""
    graph = load_graph(graph_name, user_identifier)

    if not graph:
        raise HTTPException(
            status_code=404, detail=f"Workflow '{graph_name}' not found"
        )

    if not graph.publication_config or not graph.publication_config.is_published:
        raise HTTPException(
            status_code=400, detail=f"Workflow '{graph_name}' is not published"
        )

    return graph


def load_and_validate_unpublished_graph(
    graph_name: str, user_identifier: str = "default"
):
    """Load and validate that a graph exists for publishing."""
    graph = load_graph(graph_name, user_identifier)

    if not graph:
        raise HTTPException(
            status_code=404, detail=f"Workflow '{graph_name}' not found"
        )

    return graph


def validate_graph_for_publishing(graph):
    """Validate a graph is ready for publishing."""
    validation_result = graph.validate()
    if not validation_result["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot publish invalid workflow. Errors: {validation_result['errors']}",
        )


def save_graph_with_warning(graph, user_identifier="default"):
    """Save a graph and log warning if it fails."""
    graph_manager = get_graph_manager()
    success = graph_manager.save_graph(graph, user_identifier)
    if not success:
        logger.warning(
            f"Failed to save graph file for '{graph.name}' (database operations may have succeeded)"
        )
    return success


def ensure_publication_config(graph):
    """Ensure a graph has a publication config object."""
    if not graph.publication_config:
        graph.publication_config = WorkflowPublicationConfig()
    return graph.publication_config


def update_graph_timestamps(graph):
    """Update graph timestamps."""
    graph.updated_at = datetime.now().isoformat()
    if graph.publication_config:
        graph.publication_config.published_at = datetime.now().isoformat()
