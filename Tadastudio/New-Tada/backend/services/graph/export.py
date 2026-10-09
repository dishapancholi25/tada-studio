"""Graph export services.

This module provides services for exporting graphs to various formats,
particularly the LangGraph execution format.

Example:
    >>> from backend.services.graph.export import ExportService
    >>> exporter = ExportService()
    >>> langgraph_format = exporter.export_to_langgraph_format(graph)
"""

from typing import Any, Dict

from backend.models.workflow import GraphData
from backend.services.config import get_logger

from .constants import LOG_PREFIX_EXPORT
from .exceptions import ExportError


logger = get_logger(__name__)


class ExportService:
    """Service for exporting graphs to different formats.

    This service handles conversion of internal graph representations
    to various export formats, primarily the LangGraph execution format.

    Methods:
        export_to_langgraph_format: Export to original LangGraph format
    """

    def export_to_langgraph_format(self, graph: GraphData) -> Dict[str, Any]:
        """Export graph to the original LangGraph format for execution.

        Returns the exact database representation of the graph using
        graph.to_dict() for a 1:1 copy of stored data.

        Args:
            graph: The graph to export

        Returns:
            Dictionary containing the complete graph data

        Raises:
            ExportError: If export fails

        Example:
            >>> exported = exporter.export_to_langgraph_format(graph)
            >>> print(f"Exported {len(exported['nodes'])} nodes")
        """
        logger.debug(
            f"{LOG_PREFIX_EXPORT} Exporting graph '{graph.name}' to LangGraph format"
        )

        try:
            result = graph.to_dict()

            logger.info(
                f"{LOG_PREFIX_EXPORT} Successfully exported graph '{graph.name}' "
                f"with {len(result.get('nodes', []))} nodes"
            )

            return result

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_EXPORT} Failed to export graph '{graph.name}': {e}"
            )
            raise ExportError(graph.name, "langgraph", str(e))
