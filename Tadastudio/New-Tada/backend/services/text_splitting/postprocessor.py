"""Post-processing utilities for document chunks."""

from typing import List

from langchain_core.documents import Document


class ChunkPostProcessor:
    """Post-processing utilities for document chunks."""

    @staticmethod
    def add_context_markers(
        chunks: List[Document], context_window: int = 50
    ) -> List[Document]:
        """
        Add context markers to chunks to indicate continuation.

        Args:
            chunks: List of document chunks
            context_window: Number of characters to include as context

        Returns:
            List of chunks with context markers added
        """
        processed_chunks = []

        for i, chunk in enumerate(chunks):
            # Add continuation markers
            if i > 0:
                chunk.metadata["has_previous"] = True
                chunk.metadata["previous_context"] = chunks[i - 1].page_content[
                    -context_window:
                ]
            else:
                chunk.metadata["has_previous"] = False

            if i < len(chunks) - 1:
                chunk.metadata["has_next"] = True
                chunk.metadata["next_context"] = chunks[i + 1].page_content[
                    :context_window
                ]
            else:
                chunk.metadata["has_next"] = False

            processed_chunks.append(chunk)

        return processed_chunks

    @staticmethod
    def merge_small_chunks(
        chunks: List[Document], min_size: int = 100
    ) -> List[Document]:
        """
        Merge chunks that are too small with adjacent chunks.

        Args:
            chunks: List of document chunks
            min_size: Minimum size for a chunk

        Returns:
            List of chunks with small chunks merged
        """
        if not chunks:
            return chunks

        merged_chunks = []
        current_chunk = chunks[0]

        for next_chunk in chunks[1:]:
            if len(current_chunk.page_content) < min_size:
                # Merge with next chunk
                current_chunk.page_content += "\n" + next_chunk.page_content
                current_chunk.metadata["merged"] = True
            else:
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk

        # Don't forget the last chunk
        merged_chunks.append(current_chunk)

        return merged_chunks
