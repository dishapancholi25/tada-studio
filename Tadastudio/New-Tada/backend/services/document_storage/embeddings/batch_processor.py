"""Batch embedding processor with retry logic."""

import logging
from typing import List, Optional

from ..config import EMBEDDING_BATCH_SIZE, EMBEDDING_MAX_RETRIES, LOG_PREFIX
from ..models import BatchEmbeddingResult
from .cost_tracker import calculate_embedding_cost, count_tokens


logger = logging.getLogger(__name__)


class BatchEmbeddingProcessor:
    """Processes embeddings in batches with retry logic."""

    def __init__(
        self,
        embeddings,
        batch_size: int = EMBEDDING_BATCH_SIZE,
        max_retries: int = EMBEDDING_MAX_RETRIES,
        model_name: Optional[str] = None,
    ):
        """Initialize batch processor.

        Args:
            embeddings: Embeddings instance (e.g., AzureOpenAIEmbeddings)
            batch_size: Number of texts to embed in each batch
            max_retries: Maximum number of retries for failed batches
            model_name: Model identifier used for token counting and cost calculation
        """
        self.embeddings = embeddings
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.model_name = model_name or "text-embedding-3-small"

    def process_batch(self, texts: List[str]) -> BatchEmbeddingResult:
        """Process texts in batches and generate embeddings.

        Args:
            texts: List of text strings to embed

        Returns:
            BatchEmbeddingResult with embeddings and statistics
        """
        if not self.embeddings:
            logger.warning(f"{LOG_PREFIX} No embeddings instance available")
            return BatchEmbeddingResult(
                total=len(texts),
                successful=0,
                failed=len(texts),
                embeddings=[None] * len(texts),
                errors=["No embeddings instance available"] * len(texts),
            )

        embeddings_list: List[Optional[List[float]]] = [None] * len(texts)
        errors: List[Optional[str]] = [None] * len(texts)
        successful = 0
        failed = 0
        total_tokens = 0

        idx = 0
        while idx < len(texts):
            batch = texts[idx : idx + self.batch_size]
            batch_start = idx
            batch_end = idx + len(batch)

            logger.debug(
                f"{LOG_PREFIX} Processing batch {batch_start}-{batch_end} "
                f"({len(batch)} texts)"
            )

            # Try to embed the batch with retries
            batch_embeddings = self._embed_batch_with_retry(batch)

            if batch_embeddings is not None:
                # Count tokens for successfully embedded batch
                total_tokens += count_tokens(batch, self.model_name)

                # Success - store embeddings
                for j, emb in enumerate(batch_embeddings):
                    if emb is not None:
                        embeddings_list[idx + j] = (
                            emb if isinstance(emb, list) else emb.tolist()
                        )
                        successful += 1
                    else:
                        failed += 1
                        errors[idx + j] = "Embedding returned None"
            else:
                # Entire batch failed
                for j in range(len(batch)):
                    failed += 1
                    errors[idx + j] = "Batch embedding failed after retries"

            idx += self.batch_size

        # Calculate embedding cost
        embedding_cost = calculate_embedding_cost(total_tokens, self.model_name)

        logger.info(
            f"{LOG_PREFIX} Batch embedding complete: {successful}/{len(texts)} successful, "
            f"{failed} failed, {total_tokens} tokens, cost=${embedding_cost['cost']:.6f}"
        )

        return BatchEmbeddingResult(
            total=len(texts),
            successful=successful,
            failed=failed,
            embeddings=embeddings_list,
            errors=errors,
            token_count=total_tokens,
            embedding_cost=embedding_cost,
        )

    def _embed_batch_with_retry(
        self, batch: List[str]
    ) -> Optional[List[Optional[List[float]]]]:
        """Embed a batch of texts with retry logic.

        Args:
            batch: List of text strings

        Returns:
            List of embeddings or None if all retries failed
        """
        for attempt in range(self.max_retries):
            try:
                batch_embeddings = self.embeddings.embed_documents(batch)
                return batch_embeddings

            except Exception as e:
                logger.warning(
                    f"{LOG_PREFIX} Embedding batch failed on attempt {attempt + 1}/{self.max_retries}: {e}"
                )

                if attempt == self.max_retries - 1:
                    # Final retry failed
                    logger.error(
                        f"{LOG_PREFIX} Batch embedding failed after {self.max_retries} retries"
                    )
                    return None

        return None
