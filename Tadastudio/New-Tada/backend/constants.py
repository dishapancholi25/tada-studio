"""Global constants that must remain free of heavy imports to avoid circular dependencies."""

import os

# Embedding dimensions - configurable via environment variable
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
