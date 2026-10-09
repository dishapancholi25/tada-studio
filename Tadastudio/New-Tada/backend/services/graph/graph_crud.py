"""Graph CRUD operations service.

This module provides create, read, update, and delete operations for workflow graphs,
including persistence, loading, and lifecycle management.

Example:
    >>> from backend.services.graph.graph_crud import GraphCRUDService
    >>> service = GraphCRUDService()
    >>> graph = service.create_graph("my-workflow", "A sample workflow")
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.models.workflow import GraphData, NodeType, Position
from backend.services.config import get_logger
from backend.services.execution.logging import redact_sensitive_data

from .constants import (
    DEFAULT_START_NODE_X,
    DEFAULT_START_NODE_Y,
    LOG_PREFIX_GRAPH_CRUD,
    METADATA_LAST_LOADED_AT,
    METADATA_LAST_LOADED_BY,
    METADATA_LAST_SAVED_AT,
    METADATA_LAST_SAVED_BY,
    METADATA_WORKSPACE_ID,
)
from .storage import GraphStorageService


logger = get_logger(__name__)


class GraphCRUDService:
    """Service for graph CRUD (Create, Read, Update, Delete) operations.

    This service manages the lifecycle of workflow graphs, including
    creation, retrieval, persistence, and deletion. It coordinates
    between in-memory storage and database persistence.

    Attributes:
        workspace_dir: Directory for workspace files
        active_graphs: In-memory cache of loaded graphs

    Methods:
        create_graph: Create a new graph
        get_graph: Get a graph from active graphs
        list_graphs: List all graphs for a user
        save_graph: Save a graph to storage
        load_graph: Load a graph from storage
        load_graph_by_workflow_id: Load graph by UUID
    """

    def __init__(self, workspace_dir: str = "./workspace"):
        """Initialize graph CRUD service.

        Args:
            workspace_dir: Directory for workspace files
        """
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)

        # In-memory storage for active graphs
        self.active_graphs: Dict[str, GraphData] = {}

        logger.debug(
            f"{LOG_PREFIX_GRAPH_CRUD} Initialized with workspace: {workspace_dir}"
        )

    def create_graph(
        self,
        name: str,
        description: str = "",
        username: str = "default",
        default_llm_config: Optional[
            str
        ] = None,  # Deprecated, kept for API compatibility
        node_manager: Optional[Any] = None,  # For creating START node
    ) -> GraphData:
        """Create a new graph with default START node.

        Args:
            name: Graph name
            description: Graph description
            username: User creating the graph
            default_llm_config: Deprecated parameter (ignored)
            node_manager: NodeManager instance for creating nodes

        Returns:
            The created GraphData object

        Example:
            >>> graph = service.create_graph("my-workflow", "A test workflow")
            >>> print(f"Created graph: {graph.name}")
        """
        logger.info(
            f"{LOG_PREFIX_GRAPH_CRUD} Creating new graph: {name} for user: {username}"
        )

        # Create graph instance
        graph = GraphData(
            name=name,
            description=description,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            default_llm_config=None,  # No longer using hardcoded defaults
        )

        # Set metadata
        if not getattr(graph, "metadata", None):
            graph.metadata = {}
        graph.metadata.setdefault(METADATA_WORKSPACE_ID, username)
        graph.metadata[METADATA_LAST_SAVED_BY] = username
        graph.metadata[METADATA_LAST_SAVED_AT] = datetime.now().isoformat()

        # Add default START node
        if node_manager:
            start_node = node_manager.create_node(
                node_type=NodeType.START,
                name="Start",
                position=Position(DEFAULT_START_NODE_X, DEFAULT_START_NODE_Y),
            )
            graph.nodes.append(start_node)
        else:
            logger.warning(
                f"{LOG_PREFIX_GRAPH_CRUD} No node_manager provided, "
                "START node not created"
            )

        # Store in active graphs and save
        self.active_graphs[name] = graph
        self.save_graph(graph, username)

        logger.info(f"{LOG_PREFIX_GRAPH_CRUD} Successfully created graph: {name}")

        return graph

    def get_graph(self, graph_name: str) -> Optional[GraphData]:
        """Get a graph from active graphs (in-memory).

        Args:
            graph_name: Name of the graph to retrieve

        Returns:
            GraphData if found, None otherwise

        Example:
            >>> graph = service.get_graph("my-workflow")
            >>> if graph:
            ...     print(f"Found graph with {len(graph.nodes)} nodes")
        """
        graph = self.active_graphs.get(graph_name)

        if graph:
            logger.debug(
                f"{LOG_PREFIX_GRAPH_CRUD} Retrieved graph from memory: {graph_name}"
            )
        else:
            logger.debug(f"{LOG_PREFIX_GRAPH_CRUD} Graph not in memory: {graph_name}")

        return graph

    def list_graphs(self, username: str = "default") -> List[Dict[str, Any]]:
        """List all graphs for a user from database storage.

        Args:
            username: User identifier

        Returns:
            List of graph metadata dictionaries

        Example:
            >>> graphs = service.list_graphs("user@example.com")
            >>> for graph_info in graphs:
            ...     print(f"Graph: {graph_info['name']}")
        """
        logger.debug(f"{LOG_PREFIX_GRAPH_CRUD} Listing graphs for user: {username}")

        graphs = []

        try:
            db_graphs = GraphStorageService.list_graphs(workspace_id=username)
            for db_graph in db_graphs:
                # Parse the definition to get additional stats
                definition = (
                    db_graph.get("definition_json", {})
                    if isinstance(db_graph.get("definition_json"), dict)
                    else {}
                )
                nodes = definition.get("nodes", [])

                graphs.append(
                    {
                        "name": db_graph.get("name", ""),
                        "workflow_id": db_graph.get("workflow_id"),
                        "description": db_graph.get("description", ""),
                        "created_at": db_graph.get("created_at"),
                        "updated_at": db_graph.get("updated_at"),
                        "version": db_graph.get("version", 1),
                        "node_count": len(nodes),
                        "is_subgraph": definition.get("is_subgraph", False),
                        "has_llm_config": definition.get("default_llm_config")
                        is not None,
                        "agent_count": len(
                            [n for n in nodes if n.get("type") == "AGENT"]
                        ),
                        "tool_count": len(
                            [n for n in nodes if n.get("type") == "TOOL"]
                        ),
                        "source": "database",
                        "workflow_role": db_graph.get("workflow_role"),
                        "owner_name": db_graph.get("owner_name"),
                        "is_shared": db_graph.get("is_shared", False),
                    }
                )

            logger.info(
                f"{LOG_PREFIX_GRAPH_CRUD} Listed {len(graphs)} graphs "
                f"from database for user {username}"
            )
            return graphs

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_GRAPH_CRUD} Database list failed for user {username}: {e}"
            )
            return []

    def save_graph(self, graph: GraphData, username: str = "default") -> bool:
        """Save a graph to database storage.

        Args:
            graph: The graph to save
            username: User performing the save

        Returns:
            True if save succeeded, False otherwise

        Example:
            >>> success = service.save_graph(graph, "user@example.com")
            >>> if success:
            ...     print("Graph saved successfully")
        """
        try:
            # Log web_search nodes before serialization (redact sensitive data)
            for node in graph.nodes:
                if node.type == NodeType.WEB_SEARCH:
                    redacted_config = redact_sensitive_data(node.web_search_config)
                    logger.debug(
                        f"[WEB_SEARCH_DEBUG] save_graph - Node {node.uniq_id} "
                        f"web_search_config: {redacted_config}"
                    )

            if not getattr(graph, "metadata", None):
                graph.metadata = {}

            workspace_id = graph.metadata.get(METADATA_WORKSPACE_ID) or username
            graph.metadata[METADATA_WORKSPACE_ID] = workspace_id
            graph.metadata[METADATA_LAST_SAVED_BY] = username
            graph.metadata[METADATA_LAST_SAVED_AT] = datetime.now().isoformat()

            graph_id = GraphStorageService.save_graph(
                graph, workspace_id=workspace_id, created_by=username
            )

            if graph_id:
                logger.info(
                    f"{LOG_PREFIX_GRAPH_CRUD} Successfully saved graph {graph.name} "
                    f"to database (ID: {graph_id})"
                )
                return True
            else:
                logger.warning(
                    f"{LOG_PREFIX_GRAPH_CRUD} Failed to save graph {graph.name} "
                    "to database"
                )
                return False

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_GRAPH_CRUD} Database save failed for graph {graph.name}: {e}"
            )
            return False

    def load_graph(
        self,
        graph_name: str,
        username: str = "default",
        orchestrator_manager: Optional[Any] = None,
    ) -> Optional[GraphData]:
        """Load a graph from database storage.

        Args:
            graph_name: Name of the graph to load
            username: User loading the graph
            orchestrator_manager: Optional orchestrator manager for auto-detection

        Returns:
            GraphData if found, None otherwise

        Example:
            >>> graph = service.load_graph("my-workflow", "user@example.com")
            >>> if graph:
            ...     print(f"Loaded graph with {len(graph.nodes)} nodes")
        """
        logger.debug(
            f"{LOG_PREFIX_GRAPH_CRUD} Loading graph: {graph_name} for user: {username}"
        )

        try:
            graph = GraphStorageService.load_graph(graph_name, workspace_id=username)

            if graph:
                # Set metadata
                if not getattr(graph, "metadata", None):
                    graph.metadata = {}
                graph.metadata.setdefault(METADATA_WORKSPACE_ID, username)
                graph.metadata[METADATA_LAST_LOADED_BY] = username
                graph.metadata[METADATA_LAST_LOADED_AT] = datetime.now().isoformat()

                # Store in active graphs
                self.active_graphs[graph_name] = graph

                # Detect and configure orchestrators
                if orchestrator_manager:
                    orchestrator_manager.detect_and_configure_orchestrators(graph)

                logger.info(
                    f"{LOG_PREFIX_GRAPH_CRUD} Loaded graph {graph_name} from database"
                )
                return graph
            else:
                logger.warning(
                    f"{LOG_PREFIX_GRAPH_CRUD} Graph {graph_name} not found in database"
                )
                return None

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_GRAPH_CRUD} Database load failed for graph {graph_name}: {e}"
            )
            return None

    def load_graph_by_workflow_id(
        self,
        workflow_id: str,
        username: str = "default",
        orchestrator_manager: Optional[Any] = None,
    ) -> Optional[GraphData]:
        """Load a graph from database by workflow ID (UUID).

        Args:
            workflow_id: UUID of the workflow
            username: User loading the graph
            orchestrator_manager: Optional orchestrator manager for auto-detection

        Returns:
            GraphData if found, None otherwise

        Example:
            >>> graph = service.load_graph_by_workflow_id(
            ...     "550e8400-e29b-41d4-a716-446655440000",
            ...     "user@example.com"
            ... )
        """
        logger.debug(
            f"{LOG_PREFIX_GRAPH_CRUD} Loading graph by workflow ID: {workflow_id} "
            f"for user: {username}"
        )

        try:
            graph = GraphStorageService.load_graph_by_workflow_id(
                workflow_id, user_identifier=username
            )

            if graph:
                # Set metadata
                if not getattr(graph, "metadata", None):
                    graph.metadata = {}
                graph.metadata.setdefault(METADATA_WORKSPACE_ID, username)
                graph.metadata[METADATA_LAST_LOADED_BY] = username
                graph.metadata[METADATA_LAST_LOADED_AT] = datetime.now().isoformat()

                # Store in active graphs
                self.active_graphs[graph.name] = graph

                # Detect and configure orchestrators
                if orchestrator_manager:
                    orchestrator_manager.detect_and_configure_orchestrators(graph)

                logger.info(
                    f"{LOG_PREFIX_GRAPH_CRUD} Loaded graph by workflow ID {workflow_id} "
                    "from database"
                )
                return graph
            else:
                logger.warning(
                    f"{LOG_PREFIX_GRAPH_CRUD} Graph with workflow ID {workflow_id} "
                    "not found in database"
                )
                return None

        except Exception as e:
            logger.error(
                f"{LOG_PREFIX_GRAPH_CRUD} Database load failed for workflow ID "
                f"{workflow_id}: {e}"
            )
            return None
