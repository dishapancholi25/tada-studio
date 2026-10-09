"""Simple executor for delegation without execution tracking.

This executor is used when no execution context is available.
It performs simple agent execution without tracking or subgraph support.
"""

from langchain_core.messages import AIMessage

from backend.services.config import get_logger
from backend.services.delegation.models import DelegationRequest, DelegationResult

logger = get_logger("delegation.simple_executor")


class SimpleDelegationExecutor:
    """Executor for simple delegation without tracking.

    This executor is used when no execution context is available,
    providing basic agent execution without persistence or tracking.
    """

    def __init__(self, graph_manager):
        """Initialize the simple executor.

        Args:
            graph_manager: GraphManager instance for executing agents
        """
        self.graph_manager = graph_manager

    def execute(self, request: DelegationRequest) -> DelegationResult:
        """Execute delegation using simple chat execution.

        Args:
            request: The delegation request

        Returns:
            Delegation result
        """
        logger.info(
            f"Executing simple delegation to {request.agent_node.name} "
            "(no execution tracking)"
        )

        try:
            # Try to get database execution ID from context if available
            db_exec_id = (
                request.context.get("db_execution_id") if request.context else None
            )

            # Execute simple chat
            response = self.graph_manager.execute_simple_chat(
                request.agent_node, request.task_description, db_execution_id=db_exec_id
            )

            # Extract content from response
            if isinstance(response, AIMessage):
                result_content = response.content
            else:
                result_content = str(response)

            logger.info(f"Simple delegation to {request.agent_node.name} completed")
            logger.debug(f"Response preview: {result_content[:200]}...")

            return DelegationResult(
                success=True,
                response=result_content,
                metadata={
                    "agent_name": request.agent_node.name,
                    "agent_id": request.agent_node.uniq_id,
                    "execution_type": "simple",
                },
            )

        except Exception as e:
            logger.error(
                f"Simple delegation to {request.agent_node.name} failed: {e}",
                exc_info=True,
            )
            return DelegationResult(
                success=False,
                error=str(e),
                metadata={
                    "agent_name": request.agent_node.name,
                    "agent_id": request.agent_node.uniq_id,
                    "execution_type": "simple",
                },
            )
