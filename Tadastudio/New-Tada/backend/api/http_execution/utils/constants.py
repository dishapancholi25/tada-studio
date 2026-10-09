"""Constants and configuration for HTTP execution API.

This module centralizes configuration values that control HTTP execution behavior,
making them easy to adjust and maintain.
"""

import re

# Execution timeouts
DEFAULT_EXECUTION_TIMEOUT = 300  # 5 minutes in seconds
MIN_EXECUTION_TIMEOUT = 10  # Minimum timeout (10 seconds)
MAX_EXECUTION_TIMEOUT = 3600  # Maximum timeout (1 hour)

# Polling intervals
EXECUTION_POLL_INTERVAL = 0.5  # Poll every 0.5 seconds
SSE_POLL_INTERVAL = 0.5  # SSE stream poll interval

# File upload limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_FILE_EXTENSIONS = {
    # Documents
    ".txt",
    ".pdf",
    ".doc",
    ".docx",
    ".rtf",
    # Spreadsheets
    ".csv",
    ".xls",
    ".xlsx",
    # Data
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".svg",
    # Code
    ".py",
    ".js",
    ".html",
    ".css",
    ".md",
    # Archives
    ".zip",
    ".tar",
    ".gz",
    # Other
    ".tmp",
}

# Token expiration
TOKEN_DEFAULT_EXPIRY_DAYS = 90  # Legacy tokens valid for 90 days

# Execution ID format
EXECUTION_ID_PREFIX = "exec_"
EXECUTION_ID_DATE_FORMAT = "%Y%m%d_%H%M%S"


def sanitize_graph_name(name: str) -> str:
    """Replace non-URL-safe characters with underscores for use in execution IDs."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


# WebSocket broadcast settings
ENABLE_WEBSOCKET_BROADCAST = True

# Logging
LOG_REQUEST_DETAILS = True
LOG_EXECUTION_CONTEXT = True

# SSE settings
SSE_HEARTBEAT_INTERVAL = 15  # Send heartbeat every 15 seconds
SSE_MAX_CONNECTION_TIME = 3600  # Max 1 hour for SSE connections

# WebSocket message buffering for connection resilience
MESSAGE_BUFFER_SIZE = 1000  # Max messages per execution to buffer for replay
MESSAGE_BUFFER_TTL = (
    900  # Time-to-live for buffered messages (15 minutes for longer workflows)
)

# Rate limiting
RATE_LIMIT_LOG_HITS = True
RATE_LIMIT_INCLUDE_HEADERS = True
