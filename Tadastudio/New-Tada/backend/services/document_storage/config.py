"""Configuration constants for document storage service."""

# Embedding dimensions - re-exported from constants for backward compatibility
from ...constants import EMBEDDING_DIMENSIONS  # noqa: F401

# Allowed file types for document upload
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".md"}

# Chunking defaults
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 4000
MIN_CHUNK_OVERLAP = 0
MAX_CHUNK_OVERLAP = 500

# Embedding defaults
EMBEDDING_BATCH_SIZE = 64
EMBEDDING_MAX_RETRIES = 3
EMBEDDING_RETRY_DELAY = 1.0  # seconds

# Azure OpenAI
AZURE_API_VERSION = "2024-02-15-preview"  # Updated to match LLM provider for better managed identity support
AZURE_COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"

# Fallback embedding deployments (tried in order)
FALLBACK_EMBEDDING_DEPLOYMENTS = [
    "text-embedding-3-large",
    "text-embedding-3-small",
    "text-embedding-ada-002",
    "embedding",
]

# Logging
LOG_PREFIX = "[DOC-STORAGE]"
