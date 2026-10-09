"""
Mock Embeddings - Test/fallback embeddings implementation.

Provides a simple embeddings implementation for testing and development
when no actual embeddings service is configured.
"""

import hashlib
import logging
from typing import List

from langchain_core.embeddings import Embeddings

from .document_storage.config import EMBEDDING_DIMENSIONS


logger = logging.getLogger(__name__)


class MockEmbeddings(Embeddings):
    """Mock embeddings implementation for testing.

    This class provides deterministic fake embeddings based on text hashing.
    It should ONLY be used for testing or when no real embeddings service
    is available.

    Warning:
        These embeddings have no semantic meaning and should not be used
        in production environments.
    """

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS):
        """Initialize mock embeddings.

        Args:
            dimensions: Number of dimensions for embedding vectors (default: EMBEDDING_DIMENSIONS)
        """
        self.dimensions = dimensions
        logger.warning(
            "[MOCK-EMBEDDINGS] Using mock embeddings - these are for testing only "
            "and have no semantic meaning!"
        )

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding from text.

        Uses text hashing to create a reproducible but meaningless embedding.

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the mock embedding
        """
        # Create a hash of the text
        text_hash = hashlib.sha256(text.encode()).digest()

        # Generate deterministic "random" values from the hash
        embedding = []
        for i in range(self.dimensions):
            # Use different parts of the hash for different dimensions
            byte_idx = (i * 2) % len(text_hash)
            # Convert bytes to a float between -1 and 1
            value = (
                int.from_bytes(text_hash[byte_idx : byte_idx + 2], "big") / 32768.0
                - 1.0
            )
            embedding.append(value)

        # Normalize the vector (make it unit length)
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents.

        Args:
            texts: List of documents to embed

        Returns:
            List of embedding vectors
        """
        logger.debug(f"[MOCK-EMBEDDINGS] Embedding {len(texts)} documents")
        return [self._generate_mock_embedding(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query text.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        logger.debug(f"[MOCK-EMBEDDINGS] Embedding query: {text[:50]}...")
        return self._generate_mock_embedding(text)

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async version of embed_documents.

        Args:
            texts: List of documents to embed

        Returns:
            List of embedding vectors
        """
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        """Async version of embed_query.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        return self.embed_query(text)


def create_mock_embeddings(dimensions: int = EMBEDDING_DIMENSIONS) -> MockEmbeddings:
    """Factory function to create mock embeddings.

    Args:
        dimensions: Number of dimensions for embedding vectors (default: EMBEDDING_DIMENSIONS)

    Returns:
        MockEmbeddings instance
    """
    return MockEmbeddings(dimensions=dimensions)


__all__ = [
    "MockEmbeddings",
    "create_mock_embeddings",
]
