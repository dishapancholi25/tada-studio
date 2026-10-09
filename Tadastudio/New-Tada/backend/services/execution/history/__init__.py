"""Execution history service package.

This package provides comprehensive execution tracking for workflow and graph executions.
It is organized into focused modules for maintainability and testability.

Modules:
    - service: Main ExecutionHistoryService facade (public API)
    - graph_execution: Graph execution CRUD operations
    - node_execution: Node execution CRUD operations
    - queries: Complex queries and formatted results
    - formatters: ORM to dictionary conversion
    - serialization: JSON serialization utilities

Usage:
    >>> from backend.services.execution.history import ExecutionHistoryService
    >>> exec_data = ExecutionHistoryService.create_graph_execution(
    ...     graph_id="my_graph",
    ...     graph_name="My Workflow",
    ...     graph_definition={}
    ... )
"""

from .service import ExecutionHistoryService


__all__ = ["ExecutionHistoryService"]
