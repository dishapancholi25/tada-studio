"""Thread-safe context variable storage for execution tracking.

This module provides the low-level ContextVar storage primitives used
throughout the execution system. These context variables are thread-safe
and work correctly with async/await patterns.
"""

from contextvars import ContextVar
from typing import Any, Dict, Optional


# Thread-safe context variables for execution tracking
current_execution_id: ContextVar[Optional[str]] = ContextVar(
    "current_execution_id", default=None
)
"""
Current execution ID for the workflow.

This is the thread_id used by LangGraph for checkpointing and state management.
"""


current_db_execution_id: ContextVar[Optional[str]] = ContextVar(
    "current_db_execution_id", default=None
)
"""
Current database execution ID.

This is the primary key of the graph_execution record in the database,
used for tracking and associating node executions.
"""


current_execution_data: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "current_execution_data", default=None
)
"""
Complete execution context data.

Contains:
    - execution_id: The thread/workflow execution ID
    - db_execution_id: The database execution record ID
    - node_execution_map: Mapping of node IDs to their execution record IDs
"""


current_execution_order: ContextVar[int] = ContextVar(
    "current_execution_order", default=0
)
"""
Current execution order counter.

Used to track the sequence of node executions within a workflow.
Increments as nodes are executed.
"""


current_user_access_token: ContextVar[Optional[str]] = ContextVar(
    "current_user_access_token", default=None
)
"""
Current user's JWT access token.

This token is used by MCP servers configured with oauth2 (User Identity) authentication
to authenticate requests using the user's credentials.
"""


current_user_id: ContextVar[Optional[str]] = ContextVar("current_user_id", default=None)
"""
Current user ID (email or identifier).

Used by MCP servers configured with mcp_oauth authentication to look up
stored OAuth tokens for the user.
"""
