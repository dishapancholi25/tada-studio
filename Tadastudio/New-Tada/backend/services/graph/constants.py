"""Constants and default values for graph operations.

This module centralizes all default values and magic constants used
throughout graph management operations.
"""

# Default node sizes
DEFAULT_NODE_WIDTH = 200
DEFAULT_NODE_HEIGHT = 100
SUB_AGENT_NODE_WIDTH = 150
SUB_AGENT_NODE_HEIGHT = 80


# Default positioning
DEFAULT_START_NODE_X = 100
DEFAULT_START_NODE_Y = 100
SUB_AGENT_OFFSET_X_BASE = 150
SUB_AGENT_OFFSET_X_INCREMENT = 150
SUB_AGENT_OFFSET_Y = 200


# Default system prompts
DEFAULT_AGENT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. "
    "Please respond to the user's message thoughtfully and accurately."
)


# LLM Configuration defaults
DEFAULT_LLM_TEMPERATURE = 0.7
DEFAULT_LLM_MAX_TOKENS = None
DEFAULT_LLM_TIMEOUT = 60


# Validation limits
MAX_TEMPERATURE = 2.0
MIN_TEMPERATURE = 0.0
MIN_TIMEOUT = 1
MAX_GRAPH_NODES = 1000  # Sanity limit
MAX_CONNECTIONS_PER_NODE = 100  # Sanity limit


# Subworkflow configuration defaults
DEFAULT_SUBWORKFLOW_TIMEOUT = 600
DEFAULT_SUBWORKFLOW_MAX_RETRIES = 1
DEFAULT_SUBWORKFLOW_CACHE_TTL = 3600


# Compilation defaults
DEFAULT_LAZY_COMPILE = True


# Metadata keys
METADATA_WORKSPACE_ID = "workspace_id"
METADATA_LAST_SAVED_BY = "last_saved_by"
METADATA_LAST_SAVED_AT = "last_saved_at"
METADATA_LAST_LOADED_BY = "last_loaded_by"
METADATA_LAST_LOADED_AT = "last_loaded_at"


# Logging prefixes for structured logging
LOG_PREFIX_NODE_MANAGER = "[NODE-MANAGER]"
LOG_PREFIX_CONNECTION_MANAGER = "[CONNECTION-MANAGER]"
LOG_PREFIX_GRAPH_CRUD = "[GRAPH-CRUD]"
LOG_PREFIX_ORCHESTRATOR = "[ORCHESTRATOR]"
LOG_PREFIX_VALIDATION = "[VALIDATION]"
LOG_PREFIX_EXPORT = "[EXPORT]"
LOG_PREFIX_COMPILATION = "[COMPILATION]"
LOG_PREFIX_GRAPH_MANAGER = "[GRAPH-MANAGER]"
