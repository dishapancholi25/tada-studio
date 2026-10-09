"""Send node states during reconnection."""

from typing import List

from ....models import NodeExecution
from ....services.config import get_logger


logger = get_logger("websocket_reconnection")


async def send_all_node_states(
    manager, execution_id: str, node_executions: List[NodeExecution]
):
    """
    Send all node execution states to reconnecting client.

    Args:
        manager: ConnectionManager instance
        execution_id: Execution ID
        node_executions: List of node executions to send
    """
    for node in node_executions:
        await manager.send_node_update(
            execution_id=execution_id,
            node_id=node.node_id,
            node_name=node.node_name,
            status=node.status,
            output=node.output_data,
            error=node.error_message,
            node_type=node.node_type,
            duration_seconds=node.duration_seconds,
            input_data=node.input_data,
            start_time=node.start_time.isoformat() if node.start_time else None,
            end_time=node.end_time.isoformat() if node.end_time else None,
            input_tokens=node.input_tokens,
            output_tokens=node.output_tokens,
            total_tokens=node.total_tokens,
            is_sub_agent=node.is_sub_agent,
            parent_agent_id=node.parent_agent_id,
            database_node_id=node.id,
        )
