"""
Text splitting service for document chunking.

Provides multiple splitting algorithms optimized for different use cases.
"""

from .factory import TextSplitterFactory
from .optimizer import ChunkingOptimizer
from .postprocessor import ChunkPostProcessor
from .utils import create_optimized_chunks


__all__ = [
    "TextSplitterFactory",
    "ChunkingOptimizer",
    "ChunkPostProcessor",
    "create_optimized_chunks",
]
