"""Constants for Graph API.

This module defines constants used throughout the Graph API,
including file size limits, timeouts, and other configuration values.
"""

import os

# Logging prefix
LOG_PREFIX = "[GRAPH-API]"

# File upload limits
MAX_FILE_SIZE_MB = 1024
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Allowed file extensions for upload
ALLOWED_FILE_EXTENSIONS = [
    ".pdf",
    ".txt",
    ".docx",
    ".xlsx",
    ".csv",
    ".png",
    ".jpg",
    ".jpeg",
    ".html",
    ".md",
]

# Execution configuration
DEFAULT_EXECUTION_TIMEOUT = 300  # 5 minutes in seconds
EXECUTION_POLL_INTERVAL = 0.5  # seconds
EXECUTION_ID_PREFIX = "exec_"
EXECUTION_ID_DATE_FORMAT = "%Y%m%d_%H%M%S"

# Thread pool configuration
# Read worker count from the THREAD_POOL_MAX_WORKERS env var if set; otherwise default to 10.
try:
    THREAD_POOL_MAX_WORKERS = int(os.getenv("THREAD_POOL_MAX_WORKERS", "10"))
except ValueError:
    THREAD_POOL_MAX_WORKERS = 10
THREAD_POOL_NAME_PREFIX = "GraphExec"

# Default values
DEFAULT_USERNAME = "default"
DEFAULT_WORKSPACE = "default"

# API response messages
MSG_GRAPH_CREATED = "Graph '{graph_name}' created successfully"
MSG_GRAPH_DELETED = "Graph '{graph_name}' deleted successfully"
MSG_GRAPH_SAVED = "Graph '{graph_name}' saved successfully"
MSG_GRAPH_RELOADED = "Graph '{graph_name}' reloaded from disk"
MSG_NODE_CREATED = "Node '{node_name}' created successfully"
MSG_NODE_UPDATED = "Node updated successfully"
MSG_NODE_DELETED = "Node deleted successfully"
MSG_NODE_CONFIGURED = "Node configured successfully"
MSG_CONNECTION_CREATED = "Connection created successfully"
MSG_CONNECTION_DELETED = "Connection deleted successfully"
MSG_EXECUTION_STARTED = "Graph '{graph_name}' execution started"
MSG_EXECUTION_COMPLETED = "Graph '{graph_name}' execution completed"
MSG_EXECUTION_CANCELLED = "Execution '{execution_id}' cancelled successfully"
MSG_LLM_CONFIG_UPDATED = "LLM configuration updated successfully"
MSG_SUBAGENT_CREATED = "Sub-agent '{subagent_name}' created successfully"
MSG_BATCH_UPDATE_APPLIED = "Applied {count} changes to {graph_name}"
MSG_WORKFLOW_IMPORTED = "Workflow '{workflow_name}' imported successfully"

# Node type descriptions
NODE_TYPE_DESCRIPTIONS = {
    "START": "Starting point of the workflow",
    "STEP": "General processing step",
    "TOOL": "Tool execution node",
    "AGENT": "AI agent node",
    "CONDITION": "Conditional branching node",
    "INFO": "Information/documentation node",
    "SUBGRAPH": "Nested workflow node",
    "END": "End point of the workflow",
}

# Health check configuration
HEALTH_CHECK_FIELDS = [
    "status",
    "timestamp",
    "active_graphs",
    "active_executions",
    "total_executions",
]
