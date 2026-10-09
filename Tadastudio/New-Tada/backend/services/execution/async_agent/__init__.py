"""Async agent execution services.

This module provides asynchronous agent execution capabilities with modular,
testable components for LLM building, memory management, tool execution,
and more.

Example usage:
    ```python
    # Create executor
    executor = create_async_agent_executor(
        llm_factory=llm_factory,
        model_service=model_service,
        get_tools_callback=graph_manager.get_tools,
    )

    # Execute agent
    config = ExecutionConfig(
        db_execution_id="exec_123",
        return_token_counts=True,
    )
    result = await executor.execute_agent(agent_node, user_message, config)

    # Access results
    print(result.response)
    print(result.token_counts)
    ```
"""

from typing import TYPE_CHECKING, Optional

from .exceptions import (
    AsyncAgentExecutionError,
    LLMBuildError,
    MemoryOperationError,
    MessageBuildError,
    StructuredOutputError,
    TokenCountError,
    ToolExecutionError,
)
from .executor import AsyncAgentExecutor
from .models import ExecutionConfig, ExecutionResult, TokenCounts, ToolExecutionRecord

if TYPE_CHECKING:
    from backend.services.llm_models import LLMFactory
    from backend.services.model_deployment import ModelDeploymentService


def create_async_agent_executor(
    llm_factory: "LLMFactory",
    model_service: "ModelDeploymentService",
    get_tools_callback: Optional[callable] = None,
) -> AsyncAgentExecutor:
    """Factory function to create AsyncAgentExecutor with dependencies.

    This is the recommended way to create an AsyncAgentExecutor instance
    as it ensures all dependencies are properly injected.

    Args:
        llm_factory: Factory for creating LLM instances
        model_service: Service for model deployment management
        get_tools_callback: Optional callback to get tools for an agent.
            Should have signature: (tool_list, agent_config, agent_node_id) -> List[Tool]

    Returns:
        Configured AsyncAgentExecutor instance

    Example:
        ```python
        from backend.services.llm_models import LLMFactory
        from backend.services.model_deployment import ModelDeploymentService
        from backend.services.execution.async_agent import create_async_agent_executor

        # Create executor
        executor = create_async_agent_executor(
            llm_factory=LLMFactory(...),
            model_service=ModelDeploymentService(),
            get_tools_callback=my_get_tools_function,
        )
        ```
    """
    return AsyncAgentExecutor(
        llm_factory=llm_factory,
        model_service=model_service,
        get_tools_callback=get_tools_callback,
    )


__all__ = [
    # Main executor
    "AsyncAgentExecutor",
    "create_async_agent_executor",
    # Models
    "ExecutionConfig",
    "ExecutionResult",
    "TokenCounts",
    "ToolExecutionRecord",
    # Exceptions
    "AsyncAgentExecutionError",
    "LLMBuildError",
    "MemoryOperationError",
    "MessageBuildError",
    "StructuredOutputError",
    "TokenCountError",
    "ToolExecutionError",
]
