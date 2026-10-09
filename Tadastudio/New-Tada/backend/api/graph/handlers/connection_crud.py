"""Connection CRUD operation handlers.

This module provides handler functions for connection create and delete operations.
"""

from typing import Any, Dict

from backend.models.workflow import ConnectionType
from backend.services.config import get_logger
from backend.services.dependency_injection import get_graph_manager

from ..constants import LOG_PREFIX, MSG_CONNECTION_CREATED, MSG_CONNECTION_DELETED
from ..dependencies import get_graph_or_404, get_user_identifier
from ..exceptions import ConnectionNotFoundError
from ..models import CreateConnectionRequest, DeleteConnectionRequest


logger = get_logger(__name__)


async def handle_create_connection(
    request: CreateConnectionRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Create a connection between two nodes.

    Args:
        request: Create connection request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and message

    Raises:
        GraphNotFoundError: If graph not found
        NodeNotFoundError: If source or target node not found
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Creating connection from '{request.source_id}' "
        f"to '{request.target_id}' in graph '{request.graph_name}'"
    )

    # Ensure the graph is available
    get_graph_or_404(request.graph_name, user_identifier, reload=True)

    # Map string to ConnectionType enum
    connection_type = ConnectionType.WORKFLOW  # default
    if request.connection_type:
        if request.connection_type.lower() == "tool":
            connection_type = ConnectionType.TOOL
        elif request.connection_type.lower() == "delegation":
            connection_type = ConnectionType.DELEGATION
        elif request.connection_type.lower() == "workflow":
            connection_type = ConnectionType.WORKFLOW

    # Determine true_condition from source_handle for condition nodes
    true_condition = False
    if request.source_handle and "true" in request.source_handle.lower():
        true_condition = True

    success = get_graph_manager().add_connection(
        request.graph_name,
        request.source_id,
        request.target_id,
        request.source_handle,
        request.target_handle,
        connection_type,
        request.label or "",
        true_condition,
    )

    if not success:
        from ..exceptions import InvalidRequestError

        raise InvalidRequestError("Graph or nodes not found")

    logger.info(f"{LOG_PREFIX} Connection created successfully")
    return {"success": True, "message": MSG_CONNECTION_CREATED}


async def handle_delete_connection(
    request: DeleteConnectionRequest, current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """Delete a connection between two nodes.

    Args:
        request: Delete connection request
        current_user: Current user from JWT token

    Returns:
        Dictionary with success status and message

    Raises:
        GraphNotFoundError: If graph not found
        ConnectionNotFoundError: If connection not found
    """
    user_identifier = get_user_identifier(current_user)
    logger.info(
        f"{LOG_PREFIX} Deleting connection from '{request.source_id}' "
        f"to '{request.target_id}' in graph '{request.graph_name}'"
    )

    get_graph_or_404(request.graph_name, user_identifier, reload=True)

    success = get_graph_manager().remove_connection(
        request.graph_name, request.source_id, request.target_id
    )

    if not success:
        raise ConnectionNotFoundError(request.source_id, request.target_id)

    logger.info(f"{LOG_PREFIX} Connection deleted successfully")
    return {"success": True, "message": MSG_CONNECTION_DELETED}
