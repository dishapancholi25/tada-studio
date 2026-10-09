"""Utility functions for text splitting operations."""

import logging
from typing import List, Optional

from langchain_core.documents import Document

from .factory import TextSplitterFactory
from .optimizer import ChunkingOptimizer
from .postprocessor import ChunkPostProcessor


logger = logging.getLogger(__name__)


def create_optimized_chunks(
    text: str,
    strategy: str = "auto",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
    optimize: bool = True,
    add_context: bool = True,
) -> List[Document]:
    """
    Create optimized chunks from text using the specified or auto-detected strategy.

    Args:
        text: The text to split into chunks
        strategy: Splitting strategy or "auto" for automatic selection
        chunk_size: Target chunk size (auto-detected if None)
        chunk_overlap: Chunk overlap (auto-detected if None)
        optimize: Whether to optimize parameters based on document analysis
        add_context: Whether to add context markers to chunks

    Returns:
        List of optimized document chunks
    """
    # Analyze document if optimization is requested
    if optimize or strategy == "auto":
        analysis = ChunkingOptimizer.analyze_document(text)

        if strategy == "auto":
            strategy = analysis["recommended_strategy"]
        if chunk_size is None:
            chunk_size = analysis["recommended_chunk_size"]
        if chunk_overlap is None:
            chunk_overlap = analysis["recommended_overlap"]

    # Set defaults if not provided
    chunk_size = chunk_size or 1000
    chunk_overlap = chunk_overlap or 200

    # Validate parameters
    chunk_size, chunk_overlap = ChunkingOptimizer.validate_parameters(
        chunk_size, chunk_overlap
    )

    # Create splitter
    splitter = TextSplitterFactory.create_splitter(
        strategy=strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )

    # Create initial chunks
    chunks = splitter.create_documents([text])

    # Post-process chunks
    chunks = ChunkPostProcessor.merge_small_chunks(chunks)

    if add_context:
        chunks = ChunkPostProcessor.add_context_markers(chunks)

    # Add metadata about chunking strategy
    for chunk in chunks:
        chunk.metadata["chunking_strategy"] = strategy
        chunk.metadata["chunk_size_target"] = chunk_size
        chunk.metadata["chunk_overlap"] = chunk_overlap

    logger.info(f"Created {len(chunks)} chunks using {strategy} strategy")

    return chunks
