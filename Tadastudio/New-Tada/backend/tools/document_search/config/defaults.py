"""Default configurations for common document search use cases.

Provides preset configurations for typical search scenarios:
- Similarity search (vector only)
- Hybrid search (vector + keyword)
- Full document retrieval
"""

from ..schemas import DocumentSearchConfig


# Default configurations for common use cases
DEFAULT_SIMILARITY_CONFIG = DocumentSearchConfig(
    search_k=3,
    search_type="similarity",
    similarity_threshold=0.5,
    citation_format="structured",
    hybrid_search_enabled=False,
    search_mode="vector",
)

DEFAULT_HYBRID_CONFIG = DocumentSearchConfig(
    search_k=3,
    search_type="similarity",
    similarity_threshold=0.5,
    citation_format="structured",
    hybrid_search_enabled=True,
    search_mode="hybrid",
    keyword_weight=0.5,
    rrf_k=60,
)

DEFAULT_FULL_DOCUMENT_CONFIG = DocumentSearchConfig(
    search_k=1,
    return_full_document=True,
    citation_format="structured",
    hybrid_search_enabled=False,
)
