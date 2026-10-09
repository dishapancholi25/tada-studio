"""Execution management services."""

# Non-circular imports (safe to import at module level)
from .async_agent import (
    AsyncAgentExecutor,
    create_async_agent_executor,
    ExecutionConfig as AsyncExecutionConfig,
    ExecutionResult as AsyncExecutionResult,
    TokenCounts,
    ToolExecutionRecord,
    AsyncAgentExecutionError,
    LLMBuildError,
    MemoryOperationError,
    MessageBuildError,
    StructuredOutputError,
    TokenCountError,
    ToolExecutionError,
)
from .checkpoint_adapter import AsyncCheckpointerAdapter
from .checkpointer import build_postgres_connection_string, initialize_checkpointer
from .checkpointer_manager import (
    ThreadLocalCheckpointerManager,
    get_checkpointer_manager,
    get_thread_checkpointer,
)

# Context management
from .context import (
    ExecutionContext,
    clear_execution_context,
    get_current_db_execution_id,
    get_current_execution_id,
    set_execution_context,
)
from .exceptions import (
    CheckpointError,
    CheckpointResumeError,
    ConditionEvaluationError,
    ExecutionError,
    GraphBuildError,
    NodeExecutionError,
    TimeoutError,
    ValidationError,
)
from .logging import ExecutionLogger, timing_decorator
from .paused.service import PausedExecutionService
from .resume_handler import ResumeHandler
from .state import StateExecutionTracker
from .types import (
    CheckpointMetadata,
    ExecutionConfig,
    ExecutionResult,
    ExecutionStatus,
    NodeExecutionContext,
)
from .workflow_executor import WorkflowExecutor

# Lazy imports for modules that may cause circular dependencies
_lazy_imports = {
    "ExecutionEngine": ".engine",
    "get_executor": ".engine",
    "initialize_executor": ".engine",
    "ResumeHandler": ".resume_handler",
    "WorkflowExecutor": ".workflow_executor",
}


def __getattr__(name: str):
    """Lazy import to avoid circular dependencies."""
    if name in _lazy_imports:
        from importlib import import_module

        module = import_module(_lazy_imports[name], __package__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Engine
    "ExecutionEngine",
    "initialize_executor",
    "get_executor",
    # Context
    "ExecutionContext",
    "get_current_execution_id",
    "get_current_db_execution_id",
    "set_execution_context",
    "clear_execution_context",
    # Async Agent Execution
    "AsyncAgentExecutor",
    "create_async_agent_executor",
    "AsyncExecutionConfig",
    "AsyncExecutionResult",
    "TokenCounts",
    "ToolExecutionRecord",
    "AsyncAgentExecutionError",
    "LLMBuildError",
    "MemoryOperationError",
    "MessageBuildError",
    "StructuredOutputError",
    "TokenCountError",
    "ToolExecutionError",
    # Existing
    "PausedExecutionService",
    "StateExecutionTracker",
    # Checkpoint
    "AsyncCheckpointerAdapter",
    "initialize_checkpointer",
    "build_postgres_connection_string",
    "ThreadLocalCheckpointerManager",
    "get_checkpointer_manager",
    "get_thread_checkpointer",
    "ResumeHandler",
    "WorkflowExecutor",
    # Types
    "ExecutionConfig",
    "ExecutionResult",
    "ExecutionStatus",
    "NodeExecutionContext",
    "CheckpointMetadata",
    # Exceptions
    "ExecutionError",
    "NodeExecutionError",
    "CheckpointError",
    "CheckpointResumeError",
    "GraphBuildError",
    "ConditionEvaluationError",
    "ValidationError",
    "TimeoutError",
    # Logging
    "ExecutionLogger",
    "timing_decorator",
]
